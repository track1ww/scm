import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.db import get_db, init_db

st.set_page_config(
    page_title="SCM 통합관리",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

st.markdown("""
<style>
.module-card {
    padding: 18px 20px; border-radius: 12px; color: white;
    text-align: center; margin: 4px;
}
.module-card h3 { font-size: 1.6rem; margin: 4px 0 2px 0; }
.module-card p  { margin: 0; opacity: 0.88; font-size: 0.85rem; }
.card-mm   { background: linear-gradient(135deg,#1a6bcc,#00c6fb); }
.card-sd   { background: linear-gradient(135deg,#11998e,#38ef7d); color:#1a1a1a; }
.card-pp   { background: linear-gradient(135deg,#f7971e,#ffd200); color:#1a1a1a; }
.card-qm   { background: linear-gradient(135deg,#cb2d3e,#ef473a); }
.card-wm   { background: linear-gradient(135deg,#667eea,#764ba2); }
.card-tm   { background: linear-gradient(135deg,#3a7bd5,#3a6073); }
.section-title {
    font-size:1.2rem; font-weight:700; color:#1f2937;
    border-left:4px solid #667eea; padding-left:10px;
    margin: 18px 0 10px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🏢 SCM 통합관리 시스템")
st.caption("물류/SCM 모듈 기반 · MM · SD · PP · QM · WM · TM")

# ── 데이터 조회 ──────────────────────────────────────────
conn = get_db()
def q(sql):
    try: return conn.execute(sql).fetchone()[0] or 0
    except: return 0

# MM
mm_suppliers  = q("SELECT COUNT(*) FROM suppliers")
mm_po_cnt     = q("SELECT COUNT(*) FROM purchase_orders WHERE status NOT IN ('입고완료','취소')")
mm_materials  = q("SELECT COUNT(*) FROM materials")
# SD
sd_orders     = q("SELECT COUNT(*) FROM sales_orders WHERE status NOT IN ('배송완료','취소')")
sd_revenue    = q("SELECT SUM(quantity*unit_price) FROM sales_orders")
sd_returns    = q("SELECT COUNT(*) FROM returns WHERE status='반품접수'")
# PP
pp_plans      = q("SELECT COUNT(*) FROM production_plans WHERE status IN ('확정','진행중')")
pp_mrp        = q("SELECT COUNT(*) FROM mrp_requests WHERE status='요청'")
# QM
qm_fail       = q("SELECT COUNT(*) FROM quality_inspections WHERE result='불합격'")
qm_nc         = q("SELECT COUNT(*) FROM nonconformance WHERE status NOT IN ('종결')")
# WM
wm_inventory  = q("SELECT COUNT(*) FROM inventory")
wm_low_stock  = q("SELECT COUNT(*) FROM inventory WHERE stock_qty <= min_stock AND min_stock > 0")
wm_asn        = q("SELECT COUNT(*) FROM asn WHERE status='예정'")
# TM
tm_transit    = q("SELECT COUNT(*) FROM logistics WHERE status='운송중'")
tm_customs    = q("SELECT COUNT(*) FROM logistics WHERE status='통관중'")
tm_fo         = q("SELECT COUNT(*) FROM freight_orders WHERE status='운송중'")
conn.close()

# ── 모듈별 KPI 카드 ──────────────────────────────────────────
st.markdown('<div class="section-title">📊 모듈별 현황</div>', unsafe_allow_html=True)

cols = st.columns(6)
modules = [
    ("card-mm", "🛒 MM", "자재관리", mm_po_cnt, "진행중 PO"),
    ("card-sd", "🛍️ SD", "판매/출하", sd_orders, "활성 주문"),
    ("card-pp", "🏭 PP", "생산계획", pp_plans, "진행중 계획"),
    ("card-qm", "🔬 QM", "품질관리", qm_nc, "미결 부적합"),
    ("card-wm", "📦 WM", "창고관리", wm_low_stock, "재고부족"),
    ("card-tm", "🚢 TM", "운송관리", tm_transit, "운송중"),
]
for col, (cls, icon, label, val, sub) in zip(cols, modules):
    with col:
        st.markdown(f"""
        <div class="module-card {cls}">
            <p>{icon} {label}</p>
            <h3>{val}</h3>
            <p>{sub}</p>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── 상세 현황 ──────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="section-title">🛒 MM – 발주 현황</div>', unsafe_allow_html=True)
    conn = get_db()
    df_po = pd.read_sql_query("""
        SELECT p.po_number AS 발주번호, s.name AS 공급사,
               p.item_name AS 품목, p.quantity AS 수량,
               p.status AS 상태, p.delivery_date AS 납기일
        FROM purchase_orders p LEFT JOIN suppliers s ON p.supplier_id=s.id
        ORDER BY p.id DESC LIMIT 6""", conn)
    conn.close()
    if not df_po.empty:
        st.dataframe(df_po, use_container_width=True, hide_index=True)
    else:
        st.info("발주 없음")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("공급사", mm_suppliers)
    col_b.metric("자재코드", mm_materials)
    col_c.metric("진행 PO", mm_po_cnt)

with col2:
    st.markdown('<div class="section-title">🛍️ SD – 판매 현황</div>', unsafe_allow_html=True)
    conn = get_db()
    df_so = pd.read_sql_query("""
        SELECT order_number AS 주문번호, platform AS 채널,
               item_name AS 품목, quantity AS 수량,
               status AS 상태, ordered_at AS 주문일
        FROM sales_orders ORDER BY id DESC LIMIT 6""", conn)
    conn.close()
    if not df_so.empty:
        st.dataframe(df_so, use_container_width=True, hide_index=True)
    else:
        st.info("주문 없음")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("활성주문", sd_orders)
    col_b.metric("총매출", f"₩{sd_revenue:,.0f}" if sd_revenue else "₩0")
    col_c.metric("반품접수", sd_returns)

with col3:
    st.markdown('<div class="section-title">🚢 TM – 운송 현황</div>', unsafe_allow_html=True)
    conn = get_db()
    df_log = pd.read_sql_query("""
        SELECT bl_number AS BL번호, transport_type AS 방식,
               carrier AS 운송사, arrival_date AS 도착예정, status AS 상태
        FROM logistics ORDER BY id DESC LIMIT 6""", conn)
    conn.close()
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.info("운송 없음")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("해외운송중", tm_transit)
    col_b.metric("통관중", tm_customs)
    col_c.metric("국내운송중", tm_fo)

st.divider()

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown('<div class="section-title">🏭 PP – 생산계획</div>', unsafe_allow_html=True)
    conn = get_db()
    df_pp = pd.read_sql_query("""
        SELECT plan_number AS 계획번호, product_name AS 품목,
               planned_qty AS 계획수량, status AS 상태,
               end_date AS 완료예정
        FROM production_plans ORDER BY id DESC LIMIT 6""", conn)
    conn.close()
    if not df_pp.empty:
        st.dataframe(df_pp, use_container_width=True, hide_index=True)
    else:
        st.info("생산계획 없음")
    col_a, col_b = st.columns(2)
    col_a.metric("진행중 계획", pp_plans)
    col_b.metric("MRP 대기", pp_mrp)

with col5:
    st.markdown('<div class="section-title">🔬 QM – 품질 현황</div>', unsafe_allow_html=True)
    conn = get_db()
    df_qm = pd.read_sql_query("""
        SELECT inspection_number AS 검사번호, item_name AS 품목,
               inspection_type AS 유형, result AS 결과,
               inspected_at AS 검사일
        FROM quality_inspections ORDER BY id DESC LIMIT 6""", conn)
    conn.close()
    if not df_qm.empty:
        st.dataframe(df_qm, use_container_width=True, hide_index=True)
    else:
        st.info("검사 없음")
    col_a, col_b = st.columns(2)
    col_a.metric("불합격 건수", qm_fail, delta_color="inverse")
    col_b.metric("미결 부적합", qm_nc, delta_color="inverse")

with col6:
    st.markdown('<div class="section-title">📦 WM – 재고 현황</div>', unsafe_allow_html=True)
    conn = get_db()
    df_inv = pd.read_sql_query("""
        SELECT item_code AS 품목코드, item_name AS 품목명,
               warehouse AS 창고, stock_qty AS 재고,
               min_stock AS 최소재고
        FROM inventory WHERE stock_qty <= min_stock AND min_stock > 0
        ORDER BY stock_qty ASC LIMIT 6""", conn)
    conn.close()
    if df_inv.empty:
        st.success("✅ 재고부족 품목 없음")
    else:
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("재고품목", wm_inventory)
    col_b.metric("⚠️ 재고부족", wm_low_stock, delta_color="inverse")
    col_c.metric("입고예정", wm_asn)
