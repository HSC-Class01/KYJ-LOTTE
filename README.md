# LOTTE DART Financial Intelligence

[![대시보드 바로가기](https://img.shields.io/badge/LOTTE-대시보드%20바로가기-B31B34?style=for-the-badge)](https://hsc-class01.github.io/KYJ-LOTTE/)

롯데지주(주식코드 `004990`)의 DART 사업·반기·분기보고서 재무 데이터를 수집하고, 재무비율을 계산해 GitHub Pages 대시보드로 제공합니다.

> 최초 설정 후 `DART_API_KEY`를 GitHub Actions Secrets에 등록해야 합니다. 실제 수집은 워크플로 실행 후 생성되는 `data/` 결과를 기준으로 합니다. DART API 응답과 공시별 제공 항목에 따라 일부 기간은 값이 없을 수 있습니다.

## 기능
- 2010년부터 DART 사업보고서(11011), 반기보고서(11012), 1분기보고서(11013), 3분기보고서(11014) 수집
- 연결재무제표(CFS)를 우선 사용하고, 연결 데이터가 없으면 별도재무제표(OFS) 사용
- 매월 1일 자동 실행(UTC 00:20, 한국시간 09:20) 및 수동 실행
- 매출액, 영업이익, 당기순이익, 자산, 부채, 자본, 현금흐름 등 주요 수치와 유동비율, 부채비율, 영업이익률, 순이익률, ROA, ROE 계산
- 연간(annual), 반기(Half-year), 분기(quarterly) 표와 시각화, 국내 비교기업(peer firms) 목록 제공

## GitHub 설정 (처음 한 번)
1. ZIP을 풀고 파일들을 `HSC-Class01/KYJ-LOTTE` 저장소 루트에 업로드합니다.
2. `github-workflows-template/update-dart.yml` 파일을 `.github/workflows/update-dart.yml` 경로로 복사합니다. GitHub 웹에서 `.github/workflows` 폴더를 만들고 파일을 올려도 됩니다.
3. GitHub 저장소의 **Settings → Secrets and variables → Actions → New repository secret**에서 `DART_API_KEY` 이름으로 OpenDART 인증키를 등록합니다.
4. **Settings → Pages**에서 Source를 **GitHub Actions**로 설정합니다.
5. **Settings → Actions → General → Workflow permissions**에서 `Read and write permissions`를 허용합니다.
6. 기본 브랜치가 `main`인지 확인합니다. 다른 브랜치면 workflow의 `main` 값을 변경하세요.
7. `Actions → Update LOTTE DART data → Run workflow`로 첫 실행을 시작합니다. 첫 실행은 2010년부터 데이터를 순차 수집하므로 다소 시간이 걸릴 수 있습니다.
8. 저장소 **Settings → Pages** 또는 Actions의 Pages 배포 작업에서 배포 상태를 확인합니다.

## DART API 키 입력
OpenDART에서 인증키를 발급한 다음 GitHub Secrets에 저장합니다. 키를 Python 파일이나 README에 직접 입력하지 마세요. 로컬 테스트는 환경변수 `DART_API_KEY`로 전달합니다.

## 파일 구조
- `index.html`: GitHub Pages 대시보드
- `scripts/update_dart.py`: DART 데이터 수집 및 지표 계산
- `data/financials.csv`, `data/financials.json`: 수집 결과
- `github-workflows-template/update-dart.yml`: 숨김 폴더 없이 ZIP에 포함한 워크플로 템플릿
- `.github/workflows/update-dart.yml`: GitHub에서 실행되도록 사용자가 복사할 실제 경로

## 지표 정의
- 유동비율 = 유동자산 / 유동부채 × 100
- 부채비율 = 부채총계 / 자본총계 × 100
- 영업이익률 = 영업이익 / 매출액 × 100
- 순이익률 = 당기순이익 / 매출액 × 100
- ROA = 당기순이익 / 총자산 × 100
- ROE = 당기순이익 / 자본총계 × 100

재무비율은 공시 재무제표 계정과목을 기반으로 계산한 참고 지표이며, 계정과목명이 다른 보고서는 일부 항목이 누락될 수 있습니다. ROA/ROE는 평균자산·평균자본이 아니라 기말 잔액 기준입니다.

## 국내 peer firms
롯데지주와 사업 포트폴리오가 완전히 동일한 상장사는 없으므로, 아래 기업은 국내 주요 복합기업/지주·유통 사업 비교를 위한 참고 peer group입니다. 사업구조가 다르므로 단순 수치 비교에는 주의가 필요합니다.

| 기업 | 종목코드 | 비교 관점 |
|---|---:|---|
| CJ(주) | 001040 | 복합기업·지주 |
| GS(주) | 078930 | 지주·유통/에너지 포트폴리오 |
| 신세계 | 004170 | 유통 |
| 현대백화점 | 069960 | 백화점·유통 |
| 한화 | 000880 | 복합기업·지주 |
| SK(주) | 034730 | 지주·복합기업 |

## Troubleshooting
- **API 인증 오류**: Secret 이름이 정확히 `DART_API_KEY`인지 확인하고 키 재발급 여부를 확인합니다.
- **Pages가 배포되지 않음**: Pages Source가 `GitHub Actions`인지, Actions 권한이 설정됐는지 확인합니다.
- **워크플로 파일이 보이지 않음**: `.github/workflows/update-dart.yml` 경로에 파일이 있는지 확인합니다. ZIP에는 숨김 파일이 없도록 템플릿을 별도 폴더에 넣었습니다.
- **일부 값이 비어 있음**: 보고서의 계정과목/재무제표 유형/공시 상태에 따라 API가 해당 값을 반환하지 않을 수 있습니다.
