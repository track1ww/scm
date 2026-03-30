# SCM2 ERP 고도화 프로젝트 계획서
**프로젝트명:** SCM2 ERP 모듈 고도화 (40~45% → 80% 수준)
**기간:** 2026년 3월 28일 ~ 2026년 9월 30일 (26주)
**팀 규모:** 12명 (코어 개발 7명 + 언어 전문가 5명)
**목표:** 9개 모듈 완전 기능화로 상용 ERP 80% 수준 달성

---

## 1. Phase 구분 (Wave 1~4)

### Wave 1: 아키텍처 설계 + 공통 인프라 (5주, 2026년 3월 28일 ~ 4월 30일)

#### 1.1 공통 모듈 구축 (필수 기반)
| 구성요소 | 설명 | 담당 | 예상 기간 |
|---------|------|------|---------|
| **승인 워크플로우** | 결재선(결재자), 조건부 라우팅, 재결재, 위임 | backend-developer, fullstack-developer | 2주 |
| **RBAC 권한 체계** | 역할기반 접근제어, 모듈별 권한, 필드별 권한 | backend-developer, api-designer | 1.5주 |
| **알림 시스템** | WebSocket 실시간 알림, 메일/SMS 백업, 알림 그룹핑 | websocket-engineer, backend-developer | 1.5주 |
| **감사 로그** | 모든 변경 기록, 사용자/시간/변경내용, 조회/다운로드 | backend-developer, sql-pro | 1주 |
| **다품목 주문(Order Line)** | 단일 주문에 여러 상품, 라인별 상태관리 | api-designer, backend-developer | 1주 |
| **Excel 출력 엔진** | 템플릿 기반 동적 생성, 서식 유지, 대용량 처리 | backend-developer, python-pro | 1주 |

#### 1.2 아키텍처 및 DB 스키마 설계
| 항목 | 담당 | 산출물 |
|------|------|--------|
| 데이터베이스 마이그레이션 전략 | sql-pro, microservices-architect | ERD, 마이그레이션 스크립트 |
| API 게이트웨이 / 마이크로서비스 구조 | microservices-architect, api-designer | 아키텍처 다이어그램 |
| 프론트엔드 상태관리 구조(Redux/Context) | react-specialist, typescript-pro | UI 컴포넌트 라이브러리 설계 |
| 로깅 및 모니터링 전략 | backend-developer, microservices-architect | 로깅 표준, 메트릭 정의 |

#### 1.3 공통 UI/UX 표준화
| 항목 | 담당 | 산출물 |
|------|------|--------|
| 디자인 시스템 (컬러, 타이포그래피) | ui-designer, frontend-developer | 디자인 가이드 |
| 폼 컴포넌트 라이브러리 | ui-designer, react-specialist | Storybook 컴포넌트 |
| 그리드/테이블 표준 | ui-designer, frontend-developer | 재사용 가능 컴포넌트 |
| 워크플로우 UI 패턴 | ui-designer, fullstack-developer | 결재/승인 화면 템플릿 |

**Wave 1 산출물:**
- [x] 공통 워크플로우 API & DB 스키마
- [x] RBAC 권한 시스템 구현
- [x] WebSocket 알림 서버 배포
- [x] 감사 로그 인프라
- [x] 프론트엔드 컴포넌트 라이브러리 v1.0
- [x] 아키텍처 문서 & 개발 가이드

---

### Wave 2: 각 모듈 백엔드 신규 모델 + API (8주, 2026년 5월 1일 ~ 6월 25일)

#### 2.1 모듈별 개발 로드맵

##### **MM (자재관리) - 우선순위 1**
**목표:** 40% → 80% (RFQ, 견적 비교, 3-way matching, 공급업체 평가)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| RFQ(견적요청) | RFQ, RFQLine | POST /rfq, GET /rfq/{id}, PUT /rfq/{id}/status | backend-developer | 1주 | Wave 1 |
| 견적 비교 분석 | QuotationAnalysis | GET /rfq/{id}/quotes/compare | backend-developer, sql-pro | 0.5주 | RFQ |
| 3-way Matching | MatchingRecord | POST /matching/3way, GET /matching/result | fullstack-developer | 1주 | RFQ, PO, GR |
| 공급업체 평가 | SupplierScorecard | GET /supplier/{id}/scorecard, POST /scorecard/evaluate | backend-developer | 0.5주 | Wave 1 |
| ABC 자재분류 | MaterialABC, ABCClassification | POST /material/abc/classify | sql-pro, python-pro | 0.5주 | Material |
| 재주문점 자동발주 | ReorderPoint, AutoPO | POST /material/{id}/reorder-check | backend-developer | 1주 | Material, PO |
| 자재 단가 관리 | MaterialPrice, PriceHistory | GET /material/{id}/price-history | backend-developer, sql-pro | 1주 | RFQ |

---

##### **SD (영업관리) - 우선순위 2**
**목표:** 40% → 80% (다품목 수주, 가격정책, RMA, AR, ATP)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| 다품목 수주(SO Line) | SalesOrder, SalesOrderLine | POST /so, GET /so/{id}, PUT /so/{id}/lines | fullstack-developer | 1.5주 | Wave 1 |
| 가격 정책 엔진 | PricingPolicy, VolumeDiscount | GET /pricing/calculate | backend-developer, python-pro | 1.5주 | Customer |
| 반품/RMA | RMA, RMALine | POST /rma, GET /rma/{id}/status | fullstack-developer | 1주 | SO |
| AR(미수금) 관리 | AccountsReceivable, ARDocument | GET /ar/aging, GET /customer/{id}/ar | sql-pro | 1주 | SO |
| ATP(가용재고) 확인 | AvailableToPromise | GET /atp/check/{material_id} | backend-developer, sql-pro | 1주 | Inventory, SO |

---

##### **HR (인사관리) - 우선순위 3**
**목표:** 35% → 80% (근태, 휴가, 성과평가, 발령, 교육)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| 근태 관리 | Attendance, AttendanceRecord | POST /attendance/checkin, POST /attendance/checkout | backend-developer | 1주 | Wave 1 |
| 휴가 관리 | Leave, LeaveBalance, LeaveRequest | POST /leave/request, GET /leave/{emp_id}/balance | fullstack-developer | 1주 | Attendance |
| 성과평가 | PerformanceReview, ReviewCriteria | POST /review, GET /review/{emp_id}/history | backend-developer | 1주 | Workflow |
| 인사발령 | Assignment, JobHistory | POST /assignment, GET /emp/{id}/job-history | fullstack-developer | 0.5주 | Employee |
| 교육이력 | Training, TrainingRecord | POST /training, GET /emp/{id}/training-history | backend-developer | 0.5주 | Employee |

---

##### **PP (생산계획) - 우선순위 4**
**목표:** 35% → 80% (CRP, Routing, 스크랩/재작업, 로트 추적)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| CRP(작업장 능력계획) | CapacityPlan, WorkCenter | GET /capacity/plan, POST /capacity/check | sql-pro, python-pro | 1.5주 | WI, BOM |
| 공정순서(Routing) | Routing, RoutingLine, WorkCenter | POST /routing, GET /routing/{product_id} | backend-developer | 1주 | Product |
| 스크랩/재작업 | ScrapRecord, ReworkOrder | POST /scrap, POST /rework | fullstack-developer | 1주 | ManufacturingOrder |
| 로트 추적 | Lot, LotTracking | GET /lot/{lot_id}/trace | backend-developer, sql-pro | 1주 | ManufacturingOrder |

---

##### **WM (창고관리) - 우선순위 5**
**목표:** 30% → 80% (Picking, Putaway, Bin, 재고실사, 로트/유통기한, 연동)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| Picking | Pick, PickLine | POST /pick/create, PUT /pick/{id}/status | fullstack-developer | 1.5주 | SO, Inventory |
| Putaway | Putaway, PutawayLine | POST /putaway/create, PUT /putaway/{id}/assign-bin | fullstack-developer | 1주 | GR, Bin |
| Bin 위치관리 | Bin, BinInventory | POST /bin, GET /bin/available, PUT /bin/{id}/location | backend-developer | 1주 | Warehouse |
| 재고실사 | InventoryCount, CountDetail | POST /count/create, POST /count/{id}/confirm | fullstack-developer, sql-pro | 1주 | Inventory |
| 로트/유통기한 자동화 | LotExpiry, ExpiryTracking | GET /lot/expiry-soon, POST /expiry-alert | backend-developer, python-pro | 1주 | Lot |
| SD/MM 연동 | InventoryReservation | GET /inventory/reserved-qty, POST /reserve | backend-developer, sql-pro | 1주 | SD, MM |

---

##### **QM (품질관리) - 우선순위 6**
**목표:** 30% → 80% (SPC, Cpk, NCR 워크플로우, 공급업체 품질 스코어)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| SPC/관리도 | SPC, SPCData, ControlChart | POST /spc/data, GET /spc/chart | python-pro, sql-pro | 1.5주 | QualityCheck |
| Cpk 계산 | CPKCalculation | GET /quality/{product_id}/cpk | python-pro, sql-pro | 1주 | SPC |
| NCR(부적합보고) | NCR, NCRDetail | POST /ncr, GET /ncr/{id}/status | fullstack-developer | 1주 | Wave 1 (Workflow) |
| 공급업체 품질 스코어카드 | SupplierQualityScore | GET /supplier/{id}/quality-scorecard | backend-developer, sql-pro | 0.5주 | MM, QualityCheck |

---

##### **FI (재무관리) - 우선순위 7**
**목표:** 40% → 80% (AR/AP Aging, 예산관리, 현금흐름, 감가상각, 은행조회)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| AR/AP Aging | ARDocument, APDocument | GET /aging-report | sql-pro | 1주 | MM, SD |
| 예산관리 | Budget, BudgetAllocation | POST /budget, GET /budget/{id}/variance | backend-developer, sql-pro | 1.5주 | Wave 1 |
| 현금흐름 예측 | CashFlowForecast | GET /cash-flow/forecast | python-pro, sql-pro | 1.5주 | AR, AP, PO |
| 고정자산 감가상각 | FixedAsset, Depreciation | POST /depreciation/calculate, GET /depreciation/schedule | backend-developer, sql-pro | 1주 | Asset |
| 은행조회 | BankReconciliation, BankStatement | POST /bank-reconciliation, GET /reconciliation/status | backend-developer | 0.5주 | Journal |

---

##### **TM (물류관리) - 우선순위 8**
**목표:** 30% → 80% (GPS 추적, 경로 최적화, POD, SD 자동 연계)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| GPS 실시간 추적 | Shipment, Location, GPSTrack | GET /shipment/{id}/location | websocket-engineer, backend-developer | 1.5주 | SO |
| 경로 최적화 | Route, RouteOptimization | POST /route/optimize | python-pro, backend-developer | 1.5주 | Shipment |
| POD(배송증명) | POD, PODPhoto | POST /pod/attach-photo, GET /shipment/{id}/pod | fullstack-developer | 1주 | Shipment |
| SD 수주 자동 연계 | DeliverySchedule | GET /delivery/upcoming | backend-developer, sql-pro | 0.5주 | SO |

---

##### **WI (작업지시) - 우선순위 9**
**목표:** 25% → 80% (PP 연동, 실작업 시간, 간트/칸반, 모바일 입력)

| 기능 | DB 모델 | API 엔드포인트 | 담당 | 기간 | 의존성 |
|------|--------|--------------|------|------|--------|
| PP 연동 | WorkInstruction, ManufacturingOrder | POST /wi/create-from-mo, GET /wi/{id} | fullstack-developer | 1.5주 | PP |
| 실작업 시간 | TimeLog, ShiftProduction | POST /time-log/checkin, POST /time-log/checkout | backend-developer | 1주 | WI |
| 간트/칸반 | WIStatus, KanbanBoard | GET /wi/gantt/{period}, GET /wi/kanban | backend-developer, sql-pro | 1.5주 | WI |
| 모바일 현장입력 | MobileTimeEntry | POST /mobile/time-entry, GET /mobile/wi-list | fullstack-developer, react-specialist | 1.5주 | WI, TimeLog |

**Wave 2 산출물:**
- [x] 각 모듈별 DB 스키마 & 마이그레이션 스크립트
- [x] 모듈별 REST API (명세서 포함)
- [x] 단위 테스트 (>80% 커버리지)
- [x] API 문서 (Swagger)
- [x] 데이터 무결성 검증

---

### Wave 3: 프론트엔드 고도화 (6주, 2026년 6월 26일 ~ 8월 6일)

#### 3.1 프론트엔드 개발 전략

**기술 스택:**
- React 18+ with TypeScript
- Redux Toolkit for State Management
- React Query for Data Fetching
- Ant Design or Material-UI
- WebSocket for Real-time Features

#### 3.2 모듈별 UI 개발

| 모듈 | 주요 화면 | 담당 | 기간 | 의존성 |
|------|---------|------|------|--------|
| **MM** | RFQ 생성/승인, 견적 비교, 공급업체 평가 | react-specialist, ui-designer | 1주 | Wave 2 MM API |
| **SD** | SO 생성/확인, 가격 책정, RMA 관리, AR 조회 | react-specialist, frontend-developer | 1.5주 | Wave 2 SD API |
| **HR** | 근태 기록, 휴가 신청, 성과평가, 발령 | frontend-developer, react-specialist | 1주 | Wave 2 HR API |
| **PP** | 능력계획 조회, Routing 설계, 로트 추적 | frontend-developer, ui-designer | 1.5주 | Wave 2 PP API |
| **WM** | Picking 지시, Putaway 할당, 재고 실사 | fullstack-developer, react-specialist | 1.5주 | Wave 2 WM API |
| **QM** | SPC 차트, NCR 워크플로우, 품질 스코어카드 | frontend-developer, python-pro | 1주 | Wave 2 QM API |
| **FI** | Aging 보고서, 예산 관리, 현금흐름 예측 | frontend-developer, react-specialist | 1주 | Wave 2 FI API |
| **TM** | 배송 추적(Map), 경로 최적화, POD 업로드 | fullstack-developer, frontend-developer | 1.5주 | Wave 2 TM API |
| **WI** | 간트/칸반 보드, 모바일 시간 기록 | react-specialist, frontend-developer | 1.5주 | Wave 2 WI API |

#### 3.3 공통 UI 요소 개발

| 요소 | 설명 | 담당 | 기간 |
|------|------|------|------|
| 결재 워크플로우 UI | 결재 대기/승인/반려 화면 | ui-designer, frontend-developer | 0.5주 |
| RBAC 권한 관리 UI | 사용자/역할/권한 설정 | frontend-developer, react-specialist | 0.5주 |
| 알림 시스템 UI | 실시간 알림 토스트, 벨 아이콘, 알림함 | frontend-developer, websocket-engineer | 0.5주 |
| 감사 로그 뷰어 | 변경 이력 조회, 필터링, 다운로드 | frontend-developer, react-specialist | 0.5주 |
| 동적 폼 빌더 | 조건부 필드, 유효성 검사, 다국어 | ui-designer, react-specialist | 1주 |
| 대시보드 프레임워크 | 위젯 기반 대시보드, 차트, 실시간 업데이트 | frontend-developer, react-specialist | 1주 |

**Wave 3 산출물:**
- [x] 완전한 프론트엔드 UI (9개 모듈)
- [x] 반응형 디자인 검증
- [x] 성능 벤치마크 (Lighthouse >90)
- [x] 사용성 테스트 (5명 대상)
- [x] 모바일 앱 준비 (PWA 호환)

---

### Wave 4: 모듈 간 연동 + 통합 테스트 (4주, 2026년 8월 7일 ~ 9월 3일)

#### 4.1 주요 통합 시나리오

| 시나리오 | 모듈 | 프로세스 | 담당 | 기간 |
|---------|------|--------|------|------|
| **E2E 구매-입고** | MM → WM → FI | RFQ → PO → GR → 재고 → AP | backend-developer, fullstack-developer | 1주 |
| **E2E 판매-배송** | SD → WM → TM → FI | SO → Pick → Putaway → Ship → AR | fullstack-developer, backend-developer | 1.5주 |
| **E2E 생산-지시** | PP → WI → WM → QM | MRP → Routing → Work Instruction → Quality Check | backend-developer, fullstack-developer | 1주 |
| **실시간 알림 통합** | Workflow → Notification → WI, HR | 결재 완료 → 작업 할당 → 현장 알림 | websocket-engineer, backend-developer | 0.5주 |
| **보고서 & 대시보드** | FI, MM, SD, WM, PP, QM | 수익성, 재고, 판매, 품질 | sql-pro, python-pro, frontend-developer | 1주 |

#### 4.2 통합 테스트 전략

**Test Pyramid:**
```
                  E2E (10%)
              통합 테스트 (30%)
          단위 테스트 (60%)
```

| 테스트 유형 | 범위 | 담당 | 기간 |
|------------|------|------|------|
| **Smoke Test** | 모든 모듈 기본 기능 | fullstack-developer | 0.5주 |
| **Integration Test** | 모듈 간 데이터 흐름 | backend-developer, fullstack-developer | 1주 |
| **Performance Test** | 1000명 동시 사용자, 응답시간 <2s | microservices-architect, sql-pro | 1주 |
| **Security Test** | SQL Injection, XSS, CSRF, 권한 검증 | api-designer, backend-developer | 1주 |
| **User Acceptance Test** | 실제 사용자 시나리오 (30시간) | fullstack-developer | 1주 |

**Wave 4 산출물:**
- [x] 통합 테스트 보고서 (Pass Rate >95%)
- [x] 마이그레이션 검증 리포트
- [x] 배포 매뉴얼 & Runbook
- [x] 모니터링 대시보드
- [x] 사용자 교육 완료
- [x] Go-Live 체크리스트

---

## 2. 에이전트별 담당 과제 매트릭스

### 2.1 12명 에이전트 배정

| 역할 | 에이전트명 | 전문성 | Wave 1 | Wave 2 | Wave 3 | Wave 4 |
|------|----------|--------|--------|--------|--------|--------|
| **API 설계** | api-designer | REST, 보안, 확장성 | RBAC, Workflow API | 모든 모듈 API 명세 | API 최적화 | 통합 API 테스트 |
| **백엔드** | backend-developer | Django, DB 설계 | 공통 모델(Workflow, Audit) | MM, SD, FI 백엔드 | 데이터 일관성 | 성능 튜닝 |
| **풀스택** | fullstack-developer | 전 스택 통합 | 아키텍처 설계 | SD, HR, WM, WI 백엔드 | UI 통합 | E2E 테스트 |
| **프론트엔드** | frontend-developer | React, 화면 설계 | UI 컴포넌트 라이브러리 | MM, SD, HR, QM, FI, TM 프론트엔드 | 반응형 최적화 | 사용성 테스트 |
| **WebSocket** | websocket-engineer | 실시간 통신 | 알림 서버(WebSocket) | TM 실시간 추적, WI 모바일 | 실시간 성능 | 부하 테스트 |
| **마이크로서비스** | microservices-architect | 아키텍처 | API Gateway, 마이크로서비스 구조 | 모듈 간 메시지 큐 | 배포 준비 | CI/CD, 모니터링 |
| **UI/UX** | ui-designer | 디자인 시스템 | 컴포넌트 라이브러리, 가이드 | 모든 모듈 UI 디자인 | 반응형 검증 | 사용성 피드백 |
| **Django 전문** | django-developer | ORM, 마이그레이션 | DB 마이그레이션 전략 | 모든 모듈 모델 | ORM 최적화 | 성능 리뷰 |
| **React 전문** | react-specialist | React Hooks, 상태관리 | 상태관리 구조 설계(Redux) | 복잡한 UI(PP, WM, WI) | 성능 최적화 | 테스트 코드 |
| **Python 전문** | python-pro | 계산, 알고리즘 | 유틸리티 | ABC 분류, CRP, 경로 최적화, Cpk, CF 예측 | 대시보드 로직 | 성능 벤치마크 |
| **SQL 전문** | sql-pro | 쿼리, DB 최적화 | DB 스키마 설계 | ATP, AR/AP, Aging, ABC, 재고 실사 | 쿼리 최적화 | 성능 튜닝 |
| **TypeScript 전문** | typescript-pro | 타입 안전성, 라이브러리 | TS 설정, 타입 정의 | 모든 프론트엔드 타입 검증 | 타입 강화 | 빌드 최적화 |

---

## 3. 우선순위 기준 (비즈니스 임팩트 + 의존성)

### 3.1 모듈 우선순위 매트릭스

**우선순위 점수 계산:**
점수 = (비즈니스임팩트 × 2) + (의존성도 × 1.5) + (구현난이도 × 0.5)

| 순위 | 모듈 | 임팩트 | 의존성 | 난이도 | 점수 | 근거 |
|------|------|--------|--------|--------|------|------|
| 1 | **MM** | 9/10 | 높음 | 중간 | 28 | 구매 프로세스 기반, 다른 모듈 의존 |
| 2 | **SD** | 10/10 | 높음 | 높음 | 33 | 핵심 수익 프로세스, WM/FI 의존 |
| 3 | **HR** | 7/10 | 낮음 | 중간 | 17 | 조직 기본, 독립적 |
| 4 | **PP** | 9/10 | 높음 | 높음 | 34 | 생산 최적화 핵심, WI/WM/QM 의존 |
| 5 | **FI** | 8/10 | 높음 | 중간 | 27 | 재무 투명성, MM/SD/PP 의존 |
| 6 | **WM** | 8/10 | 중간 | 중간 | 22 | 효율성 핵심, MM/SD/PP 의존 |
| 7 | **QM** | 6/10 | 중간 | 중간 | 17 | 품질 보증, MM/PP/WM 의존 |
| 8 | **TM** | 5/10 | 중간 | 중간 | 15 | 고객 만족도, SD 의존 |
| 9 | **WI** | 7/10 | 높음 | 높음 | 27 | 생산 실행, PP/WM/QM 의존 |

### 3.2 의존성 맵

**의존성 순서:**
1. **독립적:** HR (자체 완성)
2. **Phase 1:** MM (자재 기반)
3. **Phase 2:** SD, FI (MM 의존), PP (기본 라우팅)
4. **Phase 3:** WM (MM/SD 의존), QM (기본 검사)
5. **Phase 4:** TM (SD 의존), WI (PP/WM 의존)

---

## 4. 리스크 요인 분석

### 4.1 주요 리스크 레지스터

| ID | 위험요소 | 영향도 | 발생확률 | 우선순위 | 대응방안 |
|----|---------|----|--------|---------|---------|
| **R1** | 파일/코드 충돌 (병렬 개발) | 높음 | 중간 | **높음** | Git 브랜치 전략, 코드 리뷰, PR 자동화 |
| **R2** | 의존성 순서 오류 (Phase 순서) | 높음 | 중간 | **높음** | 의존성 맵 검증, 마일스톤 게이트 |
| **R3** | DB 마이그레이션 실패 | 높음 | 낮음 | **높음** | 리허설, 백업/롤백 계획, 테스트 환경 |
| **R4** | 성능 저하 (1000명 동시 사용) | 중간 | 중간 | **높음** | 조기 성능 테스트, 캐싱, DB 인덱싱 |
| **R5** | 기술 채용 어려움 | 중간 | 낮음 | 중간 | 프리랜서 네트워크, 외부 컨설팅 |
| **R6** | 요구사항 변경 | 중간 | 높음 | **높음** | 변경 통제 프로세스, 스코프 잠금 |
| **R7** | 테스트 자동화 부족 | 중간 | 중간 | 중간 | 지속적 테스트 작성, CI/CD 강화 |
| **R8** | 보안 취약점 | 높음 | 낮음 | **높음** | 보안 리뷰, 침투 테스트, OWASP 준수 |
| **R9** | 사용자 수용도 낮음 | 중간 | 중간 | 중간 | 초기 사용자 피드백, 교육, 변화 관리 |
| **R10** | 팀 성원 이탈 | 높음 | 낮음 | 높음 | 문서화, 지식 공유, 팀 동기 부여 |

---

## 5. 완료 기준 체크리스트

### 5.1 프로젝트 완료 기준 (전체)

#### **기능 완료도**
- [ ] 9개 모듈 모두 80% 이상 기능 구현
- [ ] 공통 인프라 (Workflow, RBAC, Notification, Audit) 완료
- [ ] 모듈 간 E2E 연동 완료

#### **품질 기준**
- [ ] 백엔드 코드 커버리지 >= 80%
- [ ] 프론트엔드 코드 커버리지 >= 70%
- [ ] 버그 제로 정책 (Critical/High 버그 없음)
- [ ] 성능: 응답시간 <2초, 1000명 동시 사용자 지원
- [ ] Lighthouse Score >= 90

#### **보안 기준**
- [ ] 보안 감사 통과 (OWASP Top 10)
- [ ] 침투 테스트 통과
- [ ] 데이터 암호화 (전송/저장)
- [ ] 접근 제어 검증 완료

#### **운영 기준**
- [ ] 배포 파이프라인 완성 (자동화 95% 이상)
- [ ] 모니터링 대시보드 구성
- [ ] Runbook 완성 (20개 시나리오)
- [ ] 24/7 지원 체계 준비

#### **문서화**
- [ ] API 문서 (Swagger) 완성
- [ ] 사용자 매뉴얼 (각 모듈)
- [ ] 개발자 가이드
- [ ] 운영 가이드

#### **사용자 만족도**
- [ ] 사용자 승인 (UAT Pass Rate >= 95%)
- [ ] 교육 완료 (100% 직원)
- [ ] 피드백 > 4/5 점수

---

## 6. 프로젝트 거버넌스

### 6.1 회의 체계

| 회의 | 주기 | 참석자 | 주제 |
|------|------|--------|------|
| Daily Standup | 매일 10:00 | 팀 리드 | 진행, 블로커, 계획 |
| Weekly Sprint | 매주 월요일 | 개발자 | Sprint 목표, 할당 |
| Weekly Sync | 매주 금요일 | 팀 리드 | 진행도, 리스크, 이슈 |
| Bi-weekly Review | 격주 금요일 | PM + 스테이크홀더 | 진행도, 의사결정 |
| Monthly Planning | 매월 1주차 | 전체 팀 | 월간 목표, 조정 |

### 6.2 성과 지표 (KPI)

| KPI | 목표 | 측정 방법 |
|-----|------|----------|
| **일정 준수율** | >= 90% | 계획 vs 실제 완료 |
| **예산 집행률** | 95-105% | 예산 vs 실제 비용 |
| **버그 밀도** | < 2/1000 LOC | 테스트 결과 |
| **코드 품질** | >= 80% | SonarQube 커버리지 |
| **배포 성공률** | 100% | 배포 횟수 vs 실패 |
| **팀 만족도** | >= 4/5 | 주간 설문 |

---

## 7. 예산 및 자원

### 7.1 인력 투입 계획

| 기간 | 투입 규모 | 구성 | 비용 |
|------|----------|------|------|
| **Wave 1 (5주)** | 12명 풀타임 | 전체 팀 | $150K |
| **Wave 2 (8주)** | 12명 풀타임 | 전체 팀 | $240K |
| **Wave 3 (6주)** | 12명 풀타임 | 전체 팀 | $180K |
| **Wave 4 (4주)** | 10명 풀타임 | 코어 팀 | $100K |
| **예비/지원** | 2명 | 프리랜서 | $40K |
| **총계** | - | - | **$710K** |

### 7.2 기술 인프라 비용

| 항목 | 월 비용 | 기간 | 합계 |
|------|--------|------|------|
| Cloud (AWS) | $5K | 6개월 | $30K |
| Database 라이선스 | $2K | 6개월 | $12K |
| 모니터링 (NewRelic, DataDog) | $2K | 6개월 | $12K |
| 개발 도구 (IDE, 라이브러리) | $1K | 6개월 | $6K |
| 테스트/보안 도구 | $1.5K | 6개월 | $9K |
| **기술 비용 합계** | - | - | **$69K** |

**전체 프로젝트 비용: $779K**

---

**문서 버전:** v1.0
**작성일:** 2026년 3월 28일
