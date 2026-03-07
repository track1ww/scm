# ⛓ SCM 통합관리 시스템

사내 공급망 전 영역(구매 → 생산 → 품질 → 창고 → 운송 → 판매)을 하나의 웹 애플리케이션에서 관리하는 **경량화 SCM 솔루션**입니다.  
Streamlit + MySQL 기반으로 별도 서버 없이 사내 배포가 가능합니다.

---

## 📁 프로젝트 구조

```
scm_sap/
├── app.py                        # 메인 대시보드 (로그인 통합)
├── utils/
│   ├── db.py                     # MySQL 연결 및 DB 초기화
│   ├── auth.py                   # 인증 / 권한 관리
│   └── design.py                 # Notion 스타일 디자인 시스템
├── pages/
│   ├── 0_🔐_로그인.py
│   ├── 1_🛒_MM_자재관리.py
│   ├── 2_🛍️_SD_판매출하.py
│   ├── 3_🏭_PP_생산계획.py
│   ├── 4_🔬_QM_품질관리.py
│   ├── 5_📦_WM_창고관리.py
│   ├── 6_🚢_TM_운송관리.py
│   ├── 7_📐_SCM_공식계산기.py
│   └── 9_👑_관리자.py
├── fix_db.py                     # DB 마이그레이션 스크립트
├── api_client.py                 # 외부 API 연동 모듈
└── scm.db                        # SQLite 개발용 DB (운영은 MySQL)
```

---

## 🚀 빠른 시작

### 1. 패키지 설치

```bash
pip install streamlit pymysql bcrypt pandas plotly
```

### 2. 환경변수 설정

`.env` 파일 또는 서버 환경변수에 아래 값을 설정합니다.

```env
SCM_DB_HOST=192.168.x.x      # 사내 MySQL 서버 IP
SCM_DB_PORT=3306
SCM_DB_USER=scm_user
SCM_DB_PASS=your_password
SCM_DB_NAME=scm_db
```

### 3. DB 초기화 (최초 1회)

```bash
python -c "from utils.db import init_db, insert_default_data; init_db(); insert_default_data()"
```

> 초기 관리자 계정: `admin@company.com` / `admin1234`

### 4. 앱 실행

```bash
streamlit run app.py
```

---

## 📦 모듈 소개

### 🛒 MM — 자재관리 (Materials Management)
공급사 관리, 자재 마스터, 구매요청(PR), 견적(RFQ), 발주서(PO), 입고(GR), 송장검증, 지급관리, 블랭킷 PO, 대체자재, 이동평균단가, 구매 KPI 등 구매 전 프로세스를 포괄합니다.

### 🛍️ SD — 판매출하 (Sales & Distribution)
고객 마스터, 신용한도, 가격조건표, 판매주문(SO), ATP 가용확인, 출하/피킹, 배송추적, 반품, 청구서, 매출세금계산서, 수금관리, 채권 Aging, 영업사원 실적을 관리합니다.

### 🏭 PP — 생산계획 (Production Planning)
수요계획, MRP, 생산오더, 작업지시, 자재소요계획, PP-SD 연동을 지원합니다.

### 🔬 QM — 품질관리 (Quality Management)
입고 검사, 공정 품질, 불량 분석, 협력사 품질 평가를 관리합니다.

### 📦 WM — 창고관리 (Warehouse Management)
입출고, 재고 실사, Bin 관리, 로트 추적, 창고 분석을 포함합니다.

### 🚢 TM — 운송관리 (Trade & Transportation)
수출입 CI/B/L, 수입신고, 수출면장, L/C 신용장, T/T·D/A 결제, 운송오더, 컨테이너 관리, 환율 관리, FTA 협정세율, 전략물자 판정, 수출환급금 관리를 지원합니다.

### 📐 SCM 공식계산기
EOQ, 안전재고, 재주문점, 리드타임 분석 등 공급망 핵심 공식을 인터랙티브하게 계산하고 시각화합니다.

### 👑 관리자
사용자 계정 활성화/비활성화, 관리자 권한 부여, 페이지별 읽기·쓰기 권한 관리, 허용 이메일 도메인 설정을 담당합니다.

---

## 🔐 인증 및 권한 체계

| 구분 | 설명 |
|------|------|
| 회원가입 | 허용된 사내 도메인 이메일만 가입 가능 |
| 로그인 | bcrypt 암호화 · 세션 기반 인증 |
| 권한 | 관리자가 사용자별로 페이지 읽기/쓰기 권한 개별 부여 |
| 관리자 | `is_admin=1`인 계정은 전 페이지 전체 권한 자동 부여 |
| 비밀번호 초기화 | 관리자 페이지에서 `scm1234!`로 초기화 가능 |

**페이지 키 매핑**

| 파일 | page_key |
|------|----------|
| MM 자재관리 | `mm` |
| SD 판매출하 | `sd` |
| PP 생산계획 | `pp` |
| QM 품질관리 | `qm` |
| WM 창고관리 | `wm` |
| TM 운송관리 | `tm` |
| SCM 공식계산기 | `calc` |
| AI 수요예측 | `ai` |

---

## 🌐 외부 API 연동 (`api_client.py`)

| API | 용도 |
|-----|------|
| 한국은행 ECOS | 일별 환율 조회 |
| 관세청 UNI-PASS | 과세환율 · HS Code 세율 · 화물 통관진행 조회 |
| 전략물자관리원 YESTRADE | 전략물자 해당 여부 판정 |
| 관세청 FTA 포털 | FTA 협정세율 조회 |

API 키는 관리자 페이지 → TM 모듈의 **API 설정** 탭에서 DB에 저장하여 관리합니다.

---

## 🗄️ DB 마이그레이션

기존 `scm.db`(SQLite)에서 운영 MySQL로 전환하거나 스키마를 업데이트할 때 사용합니다.

```bash
python fix_db.py
```

주요 마이그레이션 항목: `invoice_verifications`, `supplier_evaluations`, `purchase_tax_invoices`, `materials`, `purchase_orders`, `goods_receipts`, 신규 테이블(`blanket_orders`, `purchase_approvals`, `po_change_log`, `purchase_info_records` 등)

---

## 🎨 디자인 시스템

`utils/design.py`의 Notion 스타일 테마를 전 페이지에 일관 적용합니다.

```python
from utils.design import inject_css, apply_plotly_theme, page_header, section_title, kpi_card

inject_css()           # 전역 CSS 주입
apply_plotly_theme()   # Plotly 차트 테마 적용
page_header("🛒", "MM 자재관리", "구매·조달 전 프로세스 관리")
section_title("구매요청 목록")
```

---

## 🛠️ 각 페이지에 권한 체크 추가하는 방법

```python
from utils.auth import require_permission, has_permission, render_sidebar_user

render_sidebar_user()        # 사이드바 사용자 정보 + 로그아웃
require_permission("mm")     # 읽기 권한 없으면 자동 차단

# 쓰기 권한이 필요한 폼/버튼
can_write = has_permission("mm", write=True)
submitted = st.form_submit_button("저장", disabled=not can_write)
```

---

## 📋 기술 스택

| 구분 | 사용 기술 |
|------|-----------|
| Frontend / UI | Streamlit, Plotly, Inter / Noto Sans KR 폰트 |
| Backend / DB | Python 3.10+, MySQL (운영) / SQLite (개발) |
| 인증 | bcrypt, Streamlit session_state |
| 외부 연동 | requests, xml.etree (한국은행·관세청·전략물자관리원 API) |
| 패키지 | pymysql, pandas, bcrypt, plotly |

---

## ⚠️ 주의사항

- 운영 환경에서는 반드시 환경변수로 DB 접속 정보를 관리하고, 소스코드에 직접 기재하지 마세요.
- 신규 사용자는 가입 후 관리자가 권한을 부여해야 페이지에 접근할 수 있습니다.
