# 🏢 SCM 통합관리 시스템 –  물류/SCM 모듈 기반

Python + Streamlit + SQLite 기반의 경량 SCM 시스템 (모듈 구조 반영)


제목은 생성형 ai를 활용한 scm 관리 프로그램으로 하겠습니다. 근데 약간의 수정을 곁들인..
---
<img width="1720" height="908" alt="Image" src="https://github.com/user-attachments/assets/41d3bde3-89c5-4503-bb19-b995d966c046" />
## 📁 폴더 구조

```
scm/
├── app.py                      ← 메인 대시보드 (모듈별 현황)
├── pages/
│   ├── 1_🛒_MM_자재관리.py     ← 공급사, 자재마스터, 견적서, 발주서(PO)
│   ├── 2_🛍️_SD_판매출하.py     ← 고객마스터, 판매주문(SO), 출하, 청구서, 반품
│   ├── 3_🏭_PP_생산계획.py     ← BOM, 생산계획, MRP 소요량계산
│   ├── 4_🔬_QM_품질관리.py     ← 품질검사, 부적합(NC) 관리, 품질 KPI
│   ├── 5_📦_WM_창고관리.py     ← 창고/Bin 등록, ASN/입고검수, 재고현황, 이동, 실사
│   └── 6_🚢_TM_운송관리.py     ← CI(상업송장), BL(선하증권), 운송오더(FO)
├── utils/
│   ├── __init__.py
│   └── db.py                   ← DB 연결, 초기화, 헬퍼
└── scm.db                      ← 실행 후 자동 생성 (SQLite)
```

---

## 🚀 실행 방법

```bash
# 패키지 설치
pip install streamlit pandas

# scm 폴더에서 실행
streamlit run app.py
```

---

## 📋 모듈 → 기능 매핑

| 모듈 | 주요 기능 |
|----------|-----------|
| 🛒 MM (Materials Management) | 공급사, 자재마스터, 견적서, 발주서(PO) |
| 🛍️ SD (Sales & Distribution) | 고객마스터, 판매주문, 출하, 청구서, 반품 |
| 🏭 PP (Production Planning) | BOM, 생산계획, MRP 자재소요량 계산 |
| 🔬 QM (Quality Management) | 수입/공정/출하 검사, 부적합(NC) 관리 |
| 📦 WM/EWM (Warehouse Mgmt) | 창고/Bin 관리, ASN, 입고검수, 재고이동, 실사 |
| 🚢 TM (Transportation Mgmt) | 상업송장(CI), 선하증권(BL), 운송오더(FO) |
