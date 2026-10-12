from __future__ import annotations
import json
import os
import sys
from datetime import date
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "data"
REPORT_DIR = ROOT / "docs" / "reports"
API = "https://opendart.fss.or.kr/api"
API_KEY = os.getenv("DART_API_KEY", "").strip()
COMPANY = os.getenv("TARGET_COMPANY", "당근").strip()
START_YEAR = int(os.getenv("START_YEAR", "2010"))
TODAY = date.today()
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def api_get(endpoint, params=None, timeout=45):
    if not API_KEY:
        raise RuntimeError("DART_API_KEY secret is missing. Add it in GitHub Settings > Secrets and variables > Actions.")
    q = dict(params or {})
    q["crtfc_key"] = API_KEY
    response = requests.get(f"{API}/{endpoint}", params=q, timeout=timeout)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"OpenDART returned non-JSON response for {endpoint}") from exc
    status = str(data.get("status", ""))
    if status not in ("000", "013"):
        raise RuntimeError(f"OpenDART {endpoint} status={status}: {data.get('message', 'unknown error')}")
    return data

def get_corp_code():
    # Official corporation-code API returns a ZIP containing CORPCODE.xml.
    import io, zipfile, xml.etree.ElementTree as ET
    response = requests.get(f"{API}/corpCode.xml", params={"crtfc_key": API_KEY}, timeout=90)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        xml_name = next((n for n in zf.namelist() if n.lower().endswith(".xml")), None)
        if not xml_name:
            raise RuntimeError("The corporation-code ZIP did not contain an XML file.")
        root = ET.fromstring(zf.read(xml_name))
    candidates = []
    for item in root.findall(".//list"):
        name = (item.findtext("corp_name") or "").strip()
        code = (item.findtext("corp_code") or "").strip()
        stock = (item.findtext("stock_code") or "").strip()
        if name and code and (COMPANY in name or name in COMPANY):
            candidates.append({"corp_name": name, "corp_code": code, "stock_code": stock})
    # Prefer exact normalized name, then the shortest matching name to avoid a random subsidiary.
    candidates.sort(key=lambda x: (x["corp_name"] != COMPANY, len(x["corp_name"])))
    save_json(DATA_DIR / "company_matches.json", candidates)
    if not candidates:
        return None
    exact = next((c for c in candidates if c["corp_name"] == COMPANY), None)
    return exact or candidates[0]

def find_filings(corp_code):
    filings = []
    # list.json searches by receipt date; query each calendar year to support long historical windows.
    for year in range(START_YEAR, TODAY.year + 1):
        start, end = f"{year}0101", f"{year}1231"
        page = 1
        while True:
            data = api_get("list.json", {
                "corp_code": corp_code, "bgn_de": start, "end_de": end,
                "pblntf_ty": "A", "page_no": page, "page_count": 100,
                "sort": "date", "sort_mth": "asc", "last_reprt_at": "Y"
            })
            rows = data.get("list", []) or []
            for row in rows:
                report_name = row.get("report_nm", "")
                if any(term in report_name for term in ("사업보고서", "반기보고서", "분기보고서")):
                    filings.append(row)
            total_page = int(data.get("total_page", 1) or 1)
            if page >= total_page or not rows:
                break
            page += 1
    unique = {}
    for f in filings:
        unique[f.get("rcept_no")] = f
    return sorted(unique.values(), key=lambda x: (x.get("rcept_dt", ""), x.get("report_nm", "")))

def download_originals(filings):
    # Preserve original DART disclosure ZIPs where available. One folder per receipt number.
    import io, zipfile
    for f in filings:
        rcp = f.get("rcept_no", "")
        if not rcp:
            continue
        target = REPORT_DIR / f"{rcp}.zip"
        if target.exists():
            continue
        try:
            response = requests.get(f"{API}/document.xml",
                params={"crtfc_key": API_KEY, "rcept_no": rcp}, timeout=90)
            response.raise_for_status()
            # DART returns a ZIP payload; validate it before writing.
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                if not zf.namelist():
                    continue
            target.write_bytes(response.content)
        except Exception as exc:
            print(f"WARNING: original report download skipped for {rcp}: {exc}")

def get_financials(corp_code):
    records = []
    reprt_codes = {
        "11011": ("annual", "사업보고서"),
        "11012": ("half-year", "반기보고서"),
        "11013": ("quarterly", "1분기보고서"),
        "11014": ("quarterly", "3분기보고서"),
    }
    # OpenDART's standard financial statement API provides annual, half-year, Q1 and Q3 report codes.
    # Interim statements may contain cumulative income statement figures.
    for year in range(START_YEAR, TODAY.year + 1):
        for code, (category, label) in reprt_codes.items():
            try:
                data = api_get("fnlttSinglAcntAll.json", {
                    "corp_code": corp_code, "bsns_year": str(year),
                    "reprt_code": code, "fs_div": "CFS"
                })
                rows = data.get("list", []) or []
                if not rows:
                    data = api_get("fnlttSinglAcntAll.json", {
                        "corp_code": corp_code, "bsns_year": str(year),
                        "reprt_code": code, "fs_div": "OFS"
                    })
                    rows = data.get("list", []) or []
                for row in rows:
                    records.append({
                        "year": year, "report_code": code, "category": category,
                        "report_label": label, "fs_div": row.get("fs_div", ""),
                        "sj_div": row.get("sj_div", ""), "account_id": row.get("account_id", ""),
                        "account_nm": row.get("account_nm", ""),
                        "thstrm_nm": row.get("thstrm_nm", ""),
                        "thstrm_amount": row.get("thstrm_amount", ""),
                        "frmtrm_nm": row.get("frmtrm_nm", ""),
                        "frmtrm_amount": row.get("frmtrm_amount", ""),
                        "currency": row.get("currency", ""),
                    })
            except Exception as exc:
                print(f"INFO: no financial data for {year}/{code}: {exc}")
    return records

def main():
    status = {
        "company_query": COMPANY, "start_year": START_YEAR,
        "updated_at": date.today().isoformat(), "status": "started",
        "notes": []
    }
    try:
        corp = get_corp_code()
        if not corp:
            status.update(status="no_dart_company_match", notes=[
                f"공식 DART 법인 목록에서 '{COMPANY}'와 일치하는 법인을 찾지 못했습니다.",
                "당근이 DART 정기보고서 제출 대상이 아니면 재무 수치와 원문 보고서가 제공되지 않습니다.",
                "정확한 법인명/종속회사명을 확인한 뒤 TARGET_COMPANY를 수정하세요. 임의의 수치를 생성하지 않았습니다."
            ])
            save_json(DATA_DIR / "status.json", status)
            save_json(DATA_DIR / "financials.json", [])
            pd.DataFrame().to_csv(DATA_DIR / "financials.csv", index=False)
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return
        status["company"] = corp
        filings = find_filings(corp["corp_code"])
        save_json(DATA_DIR / "filings.json", filings)
        download_originals(filings)
        records = get_financials(corp["corp_code"])
        save_json(DATA_DIR / "financials.json", records)
        pd.DataFrame(records).to_csv(DATA_DIR / "financials.csv", index=False, encoding="utf-8-sig")
        status.update(status="ok" if records else "company_found_no_financials",
                      filing_count=len(filings), financial_record_count=len(records))
        if not records:
            status["notes"] = ["법인은 확인했지만 지정 기간의 API 재무 데이터가 없습니다. 제출 여부와 API 제공 범위를 확인하세요."]
    except Exception as exc:
        status.update(status="error", error=str(exc))
        save_json(DATA_DIR / "status.json", status)
        raise
    save_json(DATA_DIR / "status.json", status)
    print(json.dumps(status, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
