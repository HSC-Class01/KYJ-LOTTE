# 당근 DART 재무 데이터 Agent

[![🔗 대시보드 바로가기](https://img.shields.io/badge/🔗%20대시보드-바로가기-2563eb?style=for-the-badge)](https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPOSITORY/)

DART(OpenDART)에서 당근 관련 정기공시를 확인하고, 재무제표 수치·재무비율을 정리해 GitHub Pages 대시보드에 표시하는 프로젝트입니다.

> **중요한 데이터 한계:** 당근은 비상장사이며, DART에 사업보고서 제출 대상 법인으로 등록되어 있지 않거나 원하는 연도의 정기보고서가 없을 수 있습니다. 이 도구는 DART의 공식 법인 목록과 공시 API를 확인합니다. 자료가 없으면 값을 만들어내지 않고 `no filings found` 상태를 표시합니다. 자료가 없는 기간은 분석 가능한 것으로 간주하지 마세요.

## 기능

- 2010년부터 사업보고서·반기보고서·분기보고서 검색
- 재무제표 계정 수집 및 CSV/JSON 저장
- 매출액, 영업이익, 당기순이익, 자산, 부채, 자본, 영업이익률, 순이익률, 부채비율, ROA, ROE 계산
- Annual / Half-year / Quarterly 테이블 분리
- 매월 1일 자동 실행 + GitHub Actions 수동 실행
- 원문 XML ZIP 보관(해당 공시가 DART에서 제공되는 경우)
- 국내 peer firms 목록과 자료 출처 링크 표시

## 설정

### 1. OpenDART API 키 발급
1. https://opendart.fss.or.kr/ 접속 후 회원가입/로그인
2. 오픈API 이용신청에서 인증키 발급
3. GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
4. Name을 `DART_API_KEY`, Secret을 발급받은 40자리 인증키로 설정

API 키를 코드나 README에 직접 입력하거나 공개하지 마세요.

### 2. GitHub Pages 활성화
1. 저장소에 이 ZIP의 파일을 업로드합니다. `.github/workflows/update-dart.yml` 경로를 그대로 유지하세요.
2. **Settings → Pages → Build and deployment → Deploy from a branch**
3. Branch: `main`, Folder: `/docs` 선택 후 Save
4. `README.md` 배지의 `YOUR_GITHUB_USERNAME`과 `YOUR_REPOSITORY`를 실제 값으로 바꿉니다.
5. 저장소 오른쪽 **About → Edit**에서 Website에 `https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPOSITORY/` 입력

### 3. 첫 실행
Actions → `Update DART financial data` → `Run workflow`를 실행합니다. 실행 로그를 확인하고 `docs/data/`가 갱신되는지 확인하세요.

## 업데이트 일정
워크플로는 매월 1일 00:15 UTC(한국시간 09:15)에 실행되도록 설정되어 있습니다. GitHub Actions는 예약 실행 시각을 지연할 수 있으므로 정확히 09:15 실행을 보장하지 않습니다. 수동 실행도 가능합니다.

## 데이터 정의와 주의사항
- DART API의 계정명은 회사·회계기준·보고서별로 달라질 수 있습니다. 계정명 매핑은 `scripts/analyze.py`에서 관리합니다.
- 반기/분기 손익은 API가 누적 금액을 반환하는 경우가 있어 단순히 보고서끼리 비교하면 왜곡될 수 있습니다. 현재 버전은 보고서에 반환된 수치를 그대로 보존하고, 비율은 해당 보고서의 손익 수치 기준으로 계산합니다. 분기 단독 수치가 필요한 경우 누적값 차감 로직을 추가 검증해야 합니다.
- 비상장사 또는 DART 제출 대상이 아닌 회사는 보고서/재무 데이터가 없을 수 있습니다.
- Peer firms는 사업 모델이 유사한 국내 기업의 참고 목록이며, 당근과 동일한 사업 구조라고 단정하지 않습니다.

## 기본 재무 항목
- 손익: 매출액, 영업이익, 당기순이익
- 재무상태: 자산총계, 부채총계, 자본총계
- 비율: 영업이익률, 순이익률, 부채비율, ROA, ROE

## 공식 자료
- OpenDART: https://opendart.fss.or.kr/
- 공시검색 API 가이드: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
- 단일회사 전체 재무제표 API 가이드: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019021
