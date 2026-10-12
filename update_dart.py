#!/usr/bin/env python3
"""Download LOTTE holding company financial statement values from OpenDART."""
import io, os, sys, time, zipfile, json
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd

API_KEY = os.environ.get("DART_API_KEY", "").strip()
BASE = "https://opendart.fss.or.kr/api"
OUT = Path("data")
START_YEAR = int(os.environ.get("START_YEAR", "2010"))
END_YEAR = int(os.environ.get("END_YEAR", str(datetime.now().year)))
STOCK_CODE = os.environ.get("STOCK_CODE", "004990")
REPORTS = [
    ("annual", "사업보고서", "11011"),
    ("Half-year", "반기보고서", "11012"),
    ("quarterly", "1분기보고서", "11013"),
    ("quarterly", "3분기보고서", "11014"),
]

def api_get(endpoint, params, timeout=45):
    p = dict(params, crtfc_key=API_KEY)
    r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=timeout)
    r.raise_for_status()
    try:
        payload = r.json()
    except ValueError:
        raise RuntimeError(f"OpenDART returned non-JSON for {endpoint}: HTTP {r.status_code}")
    status = payload.get("status")
    if status not in (None, "000", "013"):
        raise RuntimeError(f"OpenDART {endpoint}: {payload.get('status')} {payload.get('message')}")
    return payload

def get_corp_code():
    cache = OUT / "corp_code.json"
    if cache.exists():
        try:
            val = json.loads(cache.read_text(encoding="utf-8"))
            if val.get("stock_code") == STOCK_CODE and val.get("corp_code"):
                return val["corp_code"]
        except Exception:
            pass
    p = {"crtfc_key": API_KEY}
    r = requests.get(f"{BASE}/corpCode.xml", params=p, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml_name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
        from xml.etree import ElementTree as ET
        tree = ET.fromstring(z.read(xml_name))
    corp_code = None
    for item in tree.findall(".//list"):
        stock = (item.findtext("stock_code") or "").strip()
        if stock == STOCK_CODE:
            corp_code = (item.findtext("corp_code") or "").strip()
            break
    if not corp_code:
        raise RuntimeError(f"Could not find DART corp_code for stock code {STOCK_CODE}")
    cache.write_text(json.dumps({"stock_code": STOCK_CODE, "corp_code": corp_code}, ensure_ascii=False, indent=2), encoding="utf-8")
    return corp_code

def num(value):
    if value is None:
        return None
    s = str(value).replace(",", "").strip()
    if not s or s in ("-", "–", "－"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def fetch_statement(corp_code, year, reprt_code):
    params = {"corp_code": corp_code, "bsns_year": str(year), "reprt_code": reprt_code}
    # Consolidated first; use separate statements only if consolidated data is not available.
    for fs_div in ("CFS", "OFS"):
        try:
            data = api_get("fnlttSinglAcntAll.json", dict(params, fs_div=fs_div))
        except Exception as e:
            print(f"Warning: {year}/{reprt_code}/{fs_div}: {e}", file=sys.stderr)
            continue
        rows = data.get("list") or []
        if rows:
            return rows, fs_div
        time.sleep(0.15)
    return [], None

def pick_amount(rows, labels, amount_key):
    # Prefer exact account name, then common variants.
    for label in labels:
        candidates = [r for r in rows if (r.get("account_nm") or "").strip() == label]
        for r in candidates:
            value = num(r.get(amount_key))
            if value is not None:
                return value
    for label in labels:
        candidates = [r for r in rows if label in (r.get("account_nm") or "")]
        for r in candidates:
            value = num(r.get(amount_key))
            if value is not None:
                return value
    return None

def amount_for(rows, labels):
    # Annual values use current-year annual amount; interim reports use current-period amount.
    # API uses thstrm_amount for the current reporting period.
    return pick_amount(rows, labels, "thstrm_amount")

def parse_rows(rows, year, category, report_name, reprt_code, fs_div):
    # Current period balance-sheet and income-statement accounts share the same response.
    labels = {
        "revenue": ["매출액", "수익(매출액)", "영업수익"],
        "operating_income": ["영업이익", "영업이익(손실)"],
        "net_income": ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"],
        "assets": ["자산총계"],
        "liabilities": ["부채총계"],
        "equity": ["자본총계"],
        "current_assets": ["유동자산"],
        "current_liabilities": ["유동부채"],
        "cashflow_operating": ["영업활동현금흐름"],
        "cashflow_investing": ["투자활동현금흐름"],
        "cashflow_financing": ["재무활동현금흐름"],
    }
    out = {
        "year": year, "category": category, "report": report_name,
        "report_code": reprt_code, "fs_div": fs_div,
        "currency_unit": "KRW (DART 원 단위)", "source": "OpenDART",
    }
    # Use thstrm_amount for flows, thstrm_amount for period-end balances as exposed by API.
    for key, variants in labels.items():
        out[key] = amount_for(rows, variants)
    # Some interim income statement values are year-to-date. Keep as reported and make this explicit.
    def ratio(a, b):
        return round(a / b * 100, 2) if a is not None and b not in (None, 0) else None
    out["current_ratio_pct"] = ratio(out["current_assets"], out["current_liabilities"])
    out["debt_to_equity_pct"] = ratio(out["liabilities"], out["equity"])
    out["operating_margin_pct"] = ratio(out["operating_income"], out["revenue"])
    out["net_margin_pct"] = ratio(out["net_income"], out["revenue"])
    out["roa_pct"] = ratio(out["net_income"], out["assets"])
    out["roe_pct"] = ratio(out["net_income"], out["equity"])
    return out

def main():
    if not API_KEY:
        raise SystemExit("Missing DART_API_KEY environment variable. Set it in GitHub Actions Secrets.")
    OUT.mkdir(parents=True, exist_ok=True)
    corp_code = get_corp_code()
    results = []
    for year in range(START_YEAR, END_YEAR + 1):
        for category, report_name, code in REPORTS:
            # Reports not yet published for the current year are expected to be absent.
            try:
                rows, fs_div = fetch_statement(corp_code, year, code)
                if rows and fs_div:
                    results.append(parse_rows(rows, year, category, report_name, code, fs_div))
                    print(f"OK {year} {report_name}: {len(rows)} accounts ({fs_div})")
                else:
                    print(f"No data: {year} {report_name}")
            except Exception as e:
                print(f"Warning: skipped {year} {report_name}: {e}", file=sys.stderr)
            time.sleep(0.12)
    df = pd.DataFrame(results)
    if df.empty:
        raise SystemExit("No financial data retrieved. Check API key, DART API status, and stock code.")
    df = df.drop_duplicates(subset=["year", "report_code"], keep="last").sort_values(["year", "report_code"])
    df.to_csv(OUT / "financials.csv", index=False, encoding="utf-8-sig")
    (OUT / "financials.json").write_text(json.dumps(df.where(pd.notnull(df), None).to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {"company": "롯데지주", "stock_code": STOCK_CODE, "corp_code": corp_code, "updated_at": datetime.now().astimezone().isoformat(), "start_year": START_YEAR, "end_year": END_YEAR, "rows": len(df)}
    (OUT / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(df)} rows")

if __name__ == "__main__":
    main()
