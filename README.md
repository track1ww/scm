# SCM 통합관리 시스템

SAP 물류·SCM 모듈 기반의 Streamlit 웹 애플리케이션입니다.  
MM · SD · PP · QM · WM · TM 6개 모듈을 SQLite 단일 DB로 통합 운영합니다.

---

## 목차

1. [프로젝트 구조](#프로젝트-구조)
2. [설치 및 실행](#설치-및-실행)
3. [모듈 개요](#모듈-개요)
4. [DB 스키마](#db-스키마)
5. [디자인 시스템](#디자인-시스템)
6. [알려진 제한사항](#알려진-제한사항)

---

## 프로젝트 구조

```
scm_sap/
├── app.py                      # 메인 대시보드
├── scm.db                      # SQLite DB (첫 실행 시 자동 생성)
├── fix_db.py                   # DB 스키마 수동 보정 스크립트
├── pages/
│   ├── 1_🛒_MM_자재관리.py
│   ├── 2_🛍️_SD_판매출하.py
│   ├── 3_🏭_PP_생산계획.py
│   ├── 4_🔬_QM_품질관리.py
│   ├── 5_📦_WM_창고관리.py
│   └── 6_🚢_TM_운송관리.py
└── utils/
    ├── __init__.py
    ├── db.py                   # DB 초기화 및 공통 쿼리
    ├── design.py               # 글로벌 CSS · Plotly 테마
    └── api_client.py           # 한국은행 · 관세청 API 연동
```

---

## 설치 및 실행

### 요구사항

- Python 3.9 이상

### 설치

```bash
pip install streamlit pandas plotly requests
```

### 실행

```bash
cd scm_sap
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

> `scm.db` 파일이 없으면 첫 실행 시 자동으로 생성됩니다.

---

## 모듈 개요

### 🛒 MM — Materials Management (자재관리)

구매 프로세스 전 단계를 관리합니다.

| 대분류 | 세부 기능 |
|--------|-----------|
| 공급사·자재 | 공급사 등록/평가, 자재 마스터, 대체자재, PIR(구매정보레코드) |
| 구매 프로세스 | PR → 품의서 → RFQ → 견적비교 → 계약 → 블랭킷PO → PO |
| 입출고 | 입고(GR), 반품(RTV), 이동평균단가 관리 |
| 정산·분석 | 송장검증(IV), 세금계산서, 지급관리, KPI 분석 |
| 고급 기능 | **ROP 자동발주**, **VMI(공급사 관리 재고)** |

---

### 🛍️ SD — Sales & Distribution (판매/출하/청구)

수주부터 대금 회수까지 O2C 프로세스를 커버합니다.

| 대분류 | 세부 기능 |
|--------|-----------|
| 고객·가격 | 고객 마스터, **신용한도 관리**, 가격 조건표 |
| 수주 프로세스 | 견적 → SO → **ATP 가용확인** → 상태관리 → PP 생산연동 |
| 출하·배송 | 출하/피킹, 부분출하, 배송추적, **납기약속(CRD)**, 반품, 포장명세서, **AS 접수** |
| 청구·채권 | 청구서, 매출세금계산서, 수금, **선수금 관리**, 채권 Aging |
| 영업관리 | **영업사원 등록 · 실적 분석** |
| 영업 분석 | 매출 목표, 추이, 고객·품목, 반품, 수익성 BI |

---

### 🏭 PP — Production Planning (생산계획)

생산 계획부터 실적까지 제조 전 과정을 관리합니다.

| 대분류 | 세부 기능 |
|--------|-----------|
| 기준정보 | BOM, 공정 라우팅, 작업장, **외주(Subcontracting)** |
| 생산계획·WO | 생산계획, 작업지시(WO), 생산실적, 진행 현황, **S&OP** |
| MRP | MRP 소요량 계산, 발주요청, 다단계 BOM 전개 |
| 생산 분석 | 생산 추이, 작업장 부하, 품질·불량, 간트차트, CRP, OEE |

---

### 🔬 QM — Quality Management (품질관리)

입고/공정/출하 검사와 부적합 관리를 담당합니다.

| 대분류 | 세부 기능 |
|--------|-----------|
| 검사 기준 | 검사 계획, 검사 스펙 |
| 품질검사 | 검사 등록, 성적서(COA), 검사 이력 |
| 부적합·CAPA | NC 등록, CAPA 관리, **8D 리포트**, 부적합 현황 |
| 고객 클레임 | 클레임 접수·처리 |
| 교정 관리 | 측정기기 교정 계획·이력 |
| **공급사 감사** | 감사 계획 → 실시 → 결과 분석 |
| 품질 분석 | 합격률, SPC, 불량 파레토, 공급사별 품질 |

---

### 📦 WM — Warehouse Management (창고관리)

입출고, 재고, 실사, 예측까지 창고 전 업무를 처리합니다.

| 대분류 | 세부 기능 |
|--------|-----------|
| 기준정보 | 창고·빈 마스터, **Putaway 위치최적화(ABC 룰)** |
| 입출고 | ASN, 입하검사, 출하(Delivery), **피킹 웨이브(Wave Picking)** |
| 재고 관리 | 재고 조회, 이동, 가격 재평가, 예약 |
| 실사·폐기 | 재고 실사, 차이 조정, 폐기 처리 |
| 분석·예측 | 재고 현황 BI, ABC 분석, 수요 예측 |

---

### 🚢 TM — Transportation & Trade Management (운송/수출입)

국제 물류와 무역 관련 업무를 통합 처리합니다.

| 대분류 | 세부 기능 |
|--------|-----------|
| 기준·설정 | API 설정(한국은행/관세청), 환율 관리, HS Code, FTA, 포워더 |
| 수출입 업무 | CI/B·L, 수입신고, 수출면장, 수출 P/L, 수입요건, 전략물자, 원산지(C/O) |
| 운송·결제 | L/C, 컨테이너, 화물 추적, 관세 납부, 무역결제, 보험, 수출환급금 |
| 무역 분석 | 환율 분석, 국가별 통계, 통관 BI |

---

## DB 스키마

SQLite 단일 파일(`scm.db`)에 **59개 테이블**이 저장됩니다.

### 주요 컬럼 주의사항

| 테이블 | 컬럼명 | 주의 |
|--------|--------|------|
| `suppliers` | `name` | `supplier_name` 아님 |
| `exchange_rates` | `rate_to_krw` | `rate` 아님 |
| `exchange_rates` | `rate_date` | `created_at` 아님 |
| `export_declarations` | `decl_number` | `export_declaration_number` 아님 |
| `import_declarations` | `invoice_value` | `cif_value` 아님 |
| `export_declarations` | `invoice_value` | `fob_value` 아님 |

### 테이블 분류

**MM** — suppliers, materials, purchase_requests, quotations, supplier_contracts, purchase_orders, goods_receipts, invoice_verifications, supplier_evaluations, purchase_info_records, blanket_orders, blanket_order_releases, vmi_agreements, vmi_replenishments, purchase_tax_invoices, payment_schedule, po_change_log, po_receipt_summary, alternative_materials, return_to_vendor, moving_avg_price, purchase_approvals

**SD** — customers, sd_quotations, sales_orders, deliveries, invoices, returns, prepayments, as_requests, sales_reps, price_conditions, partial_deliveries

**PP** — production_plans, bom, mrp_requests, work_orders, production_results, subcon_orders, sop_plans, routing, work_centers

**QM** — quality_inspections, nonconformance, instruments, d8_reports, supplier_audits, audit_findings, capa, claims, inspection_plans

**WM** — warehouses, storage_bins, inventory, stock_movements, asn, inbound_inspection, disposal, putaway_rules, putaway_tasks, pick_waves, pick_wave_lines

**TM** — logistics, freight_orders, commercial_invoices, import_declarations, export_declarations, exchange_rates, hs_codes, fta_agreements, letters_of_credit, containers, shipment_events, trade_payments, trade_insurance, export_refunds, forwarders, customs_payments, origin_certificates, import_requirements, strategic_goods_checks, tax_invoices, settlements

---

## 디자인 시스템

`utils/design.py`에서 전역 관리합니다.

### 테마

- **스타일**: Notion 라이트 (화이트 배경 + 그레이 보더)
- **폰트**: `Inter` (숫자·영문) + `Noto Sans KR` (한글)

### 색상 팔레트

| 용도 | 값 |
|------|----|
| Primary Blue | `#2383e2` |
| Success Green | `#0f9960` |
| Warning Orange | `#cb912f` |
| Danger Red | `#d44c47` |
| Purple | `#9065b0` |
| 배경 | `#ffffff` / `#f7f7f5` |
| 보더 | `#e9e9e7` / `#d3d3cf` |

### 주요 함수

```python
from utils.design import inject_css, apply_plotly_theme, section_title, kpi_card

inject_css()             # 전역 CSS 주입
apply_plotly_theme()     # Plotly notion_light 테마 적용
section_title("레이블")  # 섹션 구분 헤더
kpi_card(icon, label, value, sub, badge, badge_type)  # KPI 카드 HTML
```

> **필수** 각 페이지에서 `st.title()` 바로 다음에 아래 두 줄을 반드시 호출해야 합니다.
> ```python
> inject_css()
> apply_plotly_theme()
> ```

### Plotly 주의사항

- `bgcolor='transparent'` 사용 불가 → `'rgba(0,0,0,0)'` 사용
- `fillgradient` 구버전 미지원 → `fillcolor='rgba(...)'` 사용
- SQL 별칭에 `/` 포함 시 반드시 큰따옴표로 감싸야 함  
  예: `` AS "C/O번호" ``

---

## 외부 API 연동

| API | 용도 | 설정 위치 |
|-----|------|-----------|
| 한국은행 Open API | 실시간 환율 조회 | TM → 기준·설정 → API 설정 |
| 관세청 UNI-PASS | 과세환율·통관 정보 | TM → 기준·설정 → API 설정 |

---

## 알려진 제한사항

- SQLite 특성상 **동시 다중 사용자 환경에는 적합하지 않습니다**.  
  운영 환경에서는 PostgreSQL 전환을 권장합니다.
- `scm.db`를 삭제하면 모든 데이터가 초기화됩니다.  
  운영 데이터는 별도 백업이 필요합니다.
- 일부 BI 차트는 데이터가 없을 때 샘플 데이터로 표시됩니다.
