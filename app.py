import streamlit as st
import pandas as pd
import sys, os
import random
from datetime import datetime, timedelta, date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.db import get_db, init_db
from utils.design import inject_css, apply_plotly_theme, section_title
from utils.auth import is_logged_in, render_sidebar_user

st.set_page_config(
    page_title="SCM 통합관리",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
init_db()
inject_css()
apply_plotly_theme()

# ── 로그인 체크 ───────────────────────────────────────
if not is_logged_in():
    from utils.auth import login_user, register_user, get_allowed_domains

    # 사이드바 숨기기
    st.markdown("""<style>
    [data-testid="stSidebar"] {display:none}
    [data-testid="collapsedControl"] {display:none}
    </style>""", unsafe_allow_html=True)

    # 중앙 로그인 UI
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center;padding:48px 0 28px">
            <div style="font-size:2.8rem;margin-bottom:10px">⛓</div>
            <div style="font-size:1.55rem;font-weight:800;color:#1a1a1a;
                        letter-spacing:-.03em">SCM 통합관리 시스템</div>
            <div style="font-size:0.82rem;color:#9b9b9b;margin-top:6px">
                사내 이메일로 로그인하세요
            </div>
        </div>""", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 로그인", "✏️ 회원가입"])

        with tab_login:
            with st.form("main_login"):
                email    = st.text_input("이메일", placeholder="you@company.com")
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
            if submitted:
                if not email or not password:
                    st.error("이메일과 비밀번호를 입력하세요.")
                else:
                    ok, msg = login_user(email, password)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_register:
            domains = get_allowed_domains()
            if domains:
                st.info(f"가입 가능 도메인: {', '.join(['@'+d for d in domains])}")
            with st.form("main_register"):
                r_name = st.text_input("이름")
                r_email = st.text_input("사내 이메일", placeholder="you@company.com")
                r_dept  = st.text_input("부서 (선택)")
                r_pw    = st.text_input("비밀번호 (8자 이상)", type="password")
                r_pw2   = st.text_input("비밀번호 확인", type="password")
                submitted_r = st.form_submit_button("가입 신청", use_container_width=True, type="primary")
            if submitted_r:
                if not all([r_name, r_email, r_pw, r_pw2]):
                    st.error("모든 항목을 입력하세요.")
                elif r_pw != r_pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    ok, msg = register_user(r_email, r_name, r_pw, r_dept)
                    st.success(msg) if ok else st.error(msg)

    st.stop()

# ── 사이드바 사용자 정보 ──────────────────────────────
render_sidebar_user()

try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PL = True
except ImportError:
    HAS_PL = False

# ── 데이터 조회 ───────────────────────────────────────
conn = get_db()
def q(sql, default=0):
    try: return conn.execute(sql).fetchone()[0] or default
    except: return default

mm_po_cnt     = q("SELECT COUNT(*) FROM purchase_orders WHERE status NOT IN ('입고완료','취소')")
mm_suppliers  = q("SELECT COUNT(*) FROM suppliers")
mm_materials  = q("SELECT COUNT(*) FROM materials")
mm_pr_pending = q("SELECT COUNT(*) FROM purchase_requests WHERE status='요청'")

sd_orders     = q("SELECT COUNT(*) FROM sales_orders WHERE status NOT IN ('배송완료','취소')")
sd_revenue    = q("SELECT COALESCE(SUM(quantity*unit_price),0) FROM sales_orders")
sd_returns    = q("SELECT COUNT(*) FROM returns WHERE status='반품접수'")
sd_done       = q("SELECT COUNT(*) FROM sales_orders WHERE status='배송완료'")
sd_total      = q("SELECT COUNT(*) FROM sales_orders WHERE status!='취소'")

pp_plans      = q("SELECT COUNT(*) FROM production_plans WHERE status IN ('확정','진행중')")
pp_mrp        = q("SELECT COUNT(*) FROM mrp_requests WHERE status='요청'")
pp_done_qty   = q("SELECT COALESCE(SUM(actual_qty),0) FROM production_results")
pp_plan_qty   = q("SELECT COALESCE(SUM(planned_qty),0) FROM production_plans")

qm_nc         = q("SELECT COUNT(*) FROM nonconformance WHERE status NOT IN ('종결')")
qm_fail       = q("SELECT COUNT(*) FROM quality_inspections WHERE result='불합격'")
qm_total      = q("SELECT COUNT(*) FROM quality_inspections")
qm_pass       = q("SELECT COUNT(*) FROM quality_inspections WHERE result='합격'")

wm_low_stock  = q("SELECT COUNT(*) FROM inventory WHERE stock_qty <= min_stock AND min_stock > 0")
wm_inventory  = q("SELECT COUNT(*) FROM inventory")
wm_asn        = q("SELECT COUNT(*) FROM asn WHERE status='예정'")

tm_transit    = q("SELECT COUNT(*) FROM logistics WHERE status='운송중'")
tm_customs    = q("SELECT COUNT(*) FROM logistics WHERE status='통관중'")
tm_container  = q("SELECT COUNT(*) FROM containers WHERE status NOT IN ('반납완료')")

# 월별 수주 트렌드 (최근 12개월 시뮬 or 실데이터)
try:
    df_monthly = pd.read_sql_query("""
        SELECT substr(ordered_at,1,7) AS ym,
               COUNT(*) AS cnt,
               COALESCE(SUM(quantity*unit_price),0) AS revenue
        FROM sales_orders
        WHERE ordered_at IS NOT NULL
        GROUP BY ym ORDER BY ym DESC LIMIT 12""", conn)
    df_monthly = df_monthly.sort_values('ym')
except: df_monthly = pd.DataFrame()

# 공급사별 PO 현황
try:
    df_sup_po = pd.read_sql_query("""
        SELECT COALESCE(s.name,'기타') AS 공급사, COUNT(p.id) AS PO수,
               COALESCE(SUM(p.quantity*p.unit_price),0) AS 금액
        FROM purchase_orders p LEFT JOIN suppliers s ON p.supplier_id=s.id
        WHERE p.status NOT IN ('취소')
        GROUP BY s.name ORDER BY 금액 DESC LIMIT 6""", conn)
except: df_sup_po = pd.DataFrame()

# 품질 검사 결과 분포
try:
    df_qm_dist = pd.read_sql_query("""
        SELECT result AS 결과, COUNT(*) AS 건수
        FROM quality_inspections GROUP BY result""", conn)
except: df_qm_dist = pd.DataFrame()

# WM 재고 현황 상위
try:
    df_inv_top = pd.read_sql_query("""
        SELECT item_name AS 품목, stock_qty AS 재고,
               min_stock AS 최소재고
        FROM inventory ORDER BY stock_qty DESC LIMIT 8""", conn)
except: df_inv_top = pd.DataFrame()

# 최근 입출고 추이
try:
    df_gr = pd.read_sql_query("""
        SELECT substr(created_at,1,10) AS dt,
               COUNT(*) AS cnt
        FROM goods_receipt
        WHERE created_at >= date('now','-30 days')
        GROUP BY dt ORDER BY dt""", conn)
except: df_gr = pd.DataFrame()

conn.close()

# ── 더미 스파크라인 데이터 (실데이터 없을 때) ─────────
import random; random.seed(42)
def spark(base, n=15, vol=0.15):
    v = base
    out = []
    for _ in range(n):
        v = max(0, v * (1 + random.uniform(-vol, vol)))
        out.append(round(v))
    return out

spark_po  = spark(mm_po_cnt  or 12)
spark_so  = spark(sd_orders  or 35)
spark_pp  = spark(pp_plans   or 8)
spark_wm  = spark(wm_inventory or 120)

# ── 페이지 헤더 ───────────────────────────────────────
today_str = datetime.now().strftime("%Y년 %m월 %d일")
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding-bottom:20px;border-bottom:1px solid #e9e9e7;margin-bottom:4px">
    <div>
        <div style="font-size:1.45rem;font-weight:700;color:#1a1a1a;letter-spacing:-.025em">
            SCM 통합관리 대시보드</div>
        <div style="font-size:0.78rem;color:#9b9b9b;margin-top:3px">{today_str} 기준</div>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
        <span style="font-size:0.75rem;background:#f1f1ef;color:#6b6b6b;
                     padding:4px 12px;border-radius:20px;border:1px solid #e9e9e7">
            MM · SD · PP · QM · WM · TM
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  섹션 1 — KPI 카드 4개 (이미지 상단 행)
# ══════════════════════════════════════════════════════
section_title("Sales Overview")

def kpi_block(col, icon, icon_bg, label, value, sub_label, sub_val, sub_color, spark_data):
    """이미지 스타일 KPI 카드 with 스파크라인"""
    with col:
        # 스파크라인 미니 차트
        if HAS_PL and spark_data:
            fig_sp = go.Figure(go.Scatter(
                y=spark_data, mode='lines',
                line=dict(color=icon_bg, width=1.5),
                fill='tozeroy',
                fillcolor=f"rgba({','.join(str(int(icon_bg.lstrip('#')[i:i+2],16)) for i in (0,2,4))},.08)" if icon_bg.startswith('#') else "rgba(35,131,226,.08)"
            ))
            fig_sp.update_layout(
                height=44, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                showlegend=False
            )
            spark_html = ""
        else:
            fig_sp = None

        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;
                    padding:16px 18px 12px;transition:box-shadow .15s;
                    box-shadow:0 1px 3px rgba(0,0,0,.05)">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px">
                <div style="width:36px;height:36px;border-radius:8px;background:{icon_bg}22;
                            display:flex;align-items:center;justify-content:center;font-size:1.1rem">
                    {icon}
                </div>
                <span style="font-size:0.7rem;color:#9b9b9b;font-weight:500">{label}</span>
            </div>
            <div style="font-size:1.8rem;font-weight:700;color:#1a1a1a;
                        font-family:'Inter',sans-serif;letter-spacing:-.02em;line-height:1">
                {value}
            </div>
            <div style="margin-top:8px;font-size:0.72rem;color:#9b9b9b">
                <span style="color:{sub_color};font-weight:600">{sub_val}</span>
                &nbsp;{sub_label}
            </div>
        </div>""", unsafe_allow_html=True)

        if fig_sp:
            st.plotly_chart(fig_sp, use_container_width=True, config={'staticPlot':True})

c1, c2, c3, c4 = st.columns(4)

revenue_fmt = f"₩{sd_revenue/1e6:.1f}M" if sd_revenue >= 1e6 else f"₩{sd_revenue:,.0f}"
pass_rate   = round(qm_pass/max(qm_total,1)*100, 1)
done_rate   = round(sd_done/max(sd_total,1)*100, 1)

with c1:
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;padding:16px 18px 14px;
                box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.7rem;color:#9b9b9b;font-weight:500;margin-bottom:8px">💰 총 매출</div>
        <div style="font-size:1.75rem;font-weight:700;color:#1a1a1a;
                    font-family:'Inter',sans-serif;letter-spacing:-.02em">{revenue_fmt}</div>
        <div style="margin-top:8px;font-size:0.72rem;color:#9b9b9b">
            <span style="color:#0f9960;font-weight:600">활성 수주 {sd_orders}건</span>
        </div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;padding:16px 18px 14px;
                box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.7rem;color:#9b9b9b;font-weight:500;margin-bottom:8px">📦 발주 현황</div>
        <div style="font-size:1.75rem;font-weight:700;color:#1a1a1a;
                    font-family:'Inter',sans-serif;letter-spacing:-.02em">{mm_po_cnt}</div>
        <div style="margin-top:8px;font-size:0.72rem;color:#9b9b9b">
            <span style="color:#2383e2;font-weight:600">PR대기 {mm_pr_pending}건</span>
            &nbsp;· 공급사 {mm_suppliers}개
        </div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;padding:16px 18px 14px;
                box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.7rem;color:#9b9b9b;font-weight:500;margin-bottom:8px">🔬 품질 합격률</div>
        <div style="font-size:1.75rem;font-weight:700;color:#1a1a1a;
                    font-family:'Inter',sans-serif;letter-spacing:-.02em">{pass_rate}%</div>
        <div style="margin-top:8px;font-size:0.72rem;color:#9b9b9b">
            <span style="color:{'#d44c47' if qm_nc > 0 else '#0f9960'};font-weight:600">
                미결NC {qm_nc}건</span>
            &nbsp;· 불합격 {qm_fail}건
        </div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;padding:16px 18px 14px;
                box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.7rem;color:#9b9b9b;font-weight:500;margin-bottom:8px">🚚 배송 완료율</div>
        <div style="font-size:1.75rem;font-weight:700;color:#1a1a1a;
                    font-family:'Inter',sans-serif;letter-spacing:-.02em">{done_rate}%</div>
        <div style="margin-top:8px;font-size:0.72rem;color:#9b9b9b">
            <span style="color:#cb912f;font-weight:600">운송중 {tm_transit}건</span>
            &nbsp;· 통관중 {tm_customs}건
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  섹션 2 — 영역 차트 (좌) + 도넛 차트 (우)
# ══════════════════════════════════════════════════════
section_title("Orders Overview · Sale Analytics")

col_area, col_donut = st.columns([3, 1])

with col_area:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;
                padding:16px 20px 4px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.78rem;font-weight:600;color:#1a1a1a;margin-bottom:2px">수주 추이</div>
        <div style="font-size:0.7rem;color:#9b9b9b">월별 수주 건수 · 매출액</div>
    </div>""", unsafe_allow_html=True)

    if HAS_PL:
        # 실 데이터 or 스파크 시뮬
        if not df_monthly.empty and len(df_monthly) >= 2:
            x_vals = df_monthly['ym'].tolist()
            y_cnt  = df_monthly['cnt'].tolist()
            y_rev  = (df_monthly['revenue'] / 1e6).round(1).tolist()
        else:
            months = [(datetime.now() - timedelta(days=30*i)).strftime('%Y-%m') for i in range(11,-1,-1)]
            x_vals = months
            y_cnt  = [random.randint(8,45) for _ in range(12)]
            y_rev  = [round(random.uniform(5,80),1) for _ in range(12)]

        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=x_vals, y=y_cnt, name='수주건수',
            mode='lines', line=dict(color='#2383e2', width=2),
            fill='tozeroy',
            fillcolor='rgba(35,131,226,.15)',
        ))
        fig_area.add_trace(go.Scatter(
            x=x_vals, y=y_rev, name='매출(M₩)', yaxis='y2',
            mode='lines', line=dict(color='#9065b0', width=1.5, dash='dot'),
        ))
        fig_area.update_layout(
            height=220,
            margin=dict(l=0,r=0,t=12,b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, tickfont=dict(size=10,color='#9b9b9b'),
                       linecolor='#e9e9e7'),
            yaxis=dict(showgrid=True, gridcolor='#f1f1ef',
                       tickfont=dict(size=10,color='#9b9b9b'), title=''),
            yaxis2=dict(overlaying='y', side='right',
                        showgrid=False, tickfont=dict(size=10,color='#9065b0'),
                        title=''),
            legend=dict(orientation='h', y=1.12, x=0, bgcolor='rgba(0,0,0,0)',
                        font=dict(size=10,color='#6b6b6b')),
            hovermode='x unified',
        )
        st.plotly_chart(fig_area, use_container_width=True, config={'displayModeBar':False})

with col_donut:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;
                padding:16px 20px 4px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.78rem;font-weight:600;color:#1a1a1a;margin-bottom:2px">품질 현황</div>
        <div style="font-size:0.7rem;color:#9b9b9b">합격 · 불합격 · 보류</div>
    </div>""", unsafe_allow_html=True)

    if HAS_PL:
        if not df_qm_dist.empty:
            labels = df_qm_dist['결과'].tolist()
            vals   = df_qm_dist['건수'].tolist()
        else:
            labels = ['합격','불합격','보류']
            vals   = [max(qm_pass,1), max(qm_fail,0), max(qm_total-qm_pass-qm_fail,0)]
            if sum(vals) == 0: vals = [70, 20, 10]

        color_map = {'합격':'#0f9960','불합격':'#d44c47','보류':'#cb912f',
                     '조건부합격':'#2383e2','재검사':'#9065b0'}
        colors = [color_map.get(l,'#9b9b9b') for l in labels]

        center_val = f"{round(vals[0]/max(sum(vals),1)*100)}%" if vals else "—"

        fig_donut = go.Figure(go.Pie(
            labels=labels, values=vals,
            hole=0.68,
            marker=dict(colors=colors, line=dict(color='#fff', width=2)),
            textinfo='none',
            hovertemplate='%{label}: %{value}건 (%{percent})<extra></extra>',
        ))
        fig_donut.add_annotation(
            text=f"<b>{center_val}</b>", x=0.5, y=0.52,
            font=dict(size=22, color='#1a1a1a', family='Inter'),
            showarrow=False
        )
        fig_donut.add_annotation(
            text="합격률", x=0.5, y=0.38,
            font=dict(size=10, color='#9b9b9b'), showarrow=False
        )
        fig_donut.update_layout(
            height=210, margin=dict(l=0,r=0,t=12,b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            legend=dict(orientation='v', x=0.5, xanchor='center', y=-0.05,
                        font=dict(size=9,color='#6b6b6b'), bgcolor='rgba(0,0,0,0)'),
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar':False})

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  섹션 3 — 하단 : 스파크라인 미니패널 (좌) + 바차트 (우)
# ══════════════════════════════════════════════════════
section_title("Sale Overview · Purchase Analytics")

col_spark, col_bar = st.columns([1, 1])

# ── 좌: 스파크라인 4개 미니 패널 ──────────────────────
with col_spark:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;
                padding:16px 20px 8px;box-shadow:0 1px 3px rgba(0,0,0,.05);margin-bottom:4px">
        <div style="font-size:0.78rem;font-weight:600;color:#1a1a1a">모듈별 미니 현황</div>
    </div>""", unsafe_allow_html=True)

    if HAS_PL:
        mini_items = [
            ("MM 발주", mm_po_cnt,    spark_po, "#2383e2"),
            ("SD 수주", sd_orders,    spark_so, "#0f9960"),
            ("PP 계획", pp_plans,     spark_pp, "#cb912f"),
            ("WM 재고", wm_inventory, spark_wm, "#9065b0"),
        ]
        for label, val, spk, color in mini_items:
            fig_mini = go.Figure(go.Scatter(
                y=spk, mode='lines',
                line=dict(color=color, width=1.5),
                fill='tozeroy',
                fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},.1)"
            ))
            fig_mini.update_layout(
                height=48, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                showlegend=False
            )
            mc1, mc2, mc3 = st.columns([2,3,2])
            mc1.markdown(f"<div style='font-size:.72rem;color:#6b6b6b;padding-top:14px'>{label}</div>",unsafe_allow_html=True)
            mc2.plotly_chart(fig_mini, use_container_width=True, config={'staticPlot':True})
            mc3.markdown(f"<div style='font-size:1.1rem;font-weight:700;color:#1a1a1a;text-align:right;padding-top:12px'>{val}</div>",unsafe_allow_html=True)

# ── 우: 공급사별 PO 바 차트 ───────────────────────────
with col_bar:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;
                padding:16px 20px 4px;box-shadow:0 1px 3px rgba(0,0,0,.05)">
        <div style="font-size:0.78rem;font-weight:600;color:#1a1a1a;margin-bottom:2px">공급사별 발주 현황</div>
        <div style="font-size:0.7rem;color:#9b9b9b">PO 건수 · 발주 금액</div>
    </div>""", unsafe_allow_html=True)

    if HAS_PL:
        if not df_sup_po.empty and len(df_sup_po) >= 1:
            sups   = df_sup_po['공급사'].tolist()
            po_cnt_list = df_sup_po['PO수'].tolist()
            po_amt_list = (df_sup_po['금액'] / 1e6).round(1).tolist()
        else:
            sups        = ['공급사A','공급사B','공급사C','공급사D','공급사E','공급사F']
            po_cnt_list = [random.randint(2,20) for _ in sups]
            po_amt_list = [round(random.uniform(1,30),1) for _ in sups]

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name='PO건수', x=sups, y=po_cnt_list,
            marker_color='#2383e2', opacity=0.85,
            text=po_cnt_list, textposition='outside',
            textfont=dict(size=9, color='#6b6b6b'),
        ))
        fig_bar.add_trace(go.Bar(
            name='금액(M₩)', x=sups, y=po_amt_list,
            marker_color='#9065b0', opacity=0.7,
            yaxis='y2',
        ))
        fig_bar.update_layout(
            barmode='group', height=220,
            margin=dict(l=0,r=0,t=12,b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickfont=dict(size=9,color='#9b9b9b'), linecolor='#e9e9e7', showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f1f1ef',
                       tickfont=dict(size=9,color='#9b9b9b'), title=''),
            yaxis2=dict(overlaying='y', side='right', showgrid=False,
                        tickfont=dict(size=9,color='#9065b0'), title=''),
            legend=dict(orientation='h', y=1.12, x=0, bgcolor='rgba(0,0,0,0)',
                        font=dict(size=9,color='#6b6b6b')),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar':False})

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  섹션 4 — 하단 테이블 2개
# ══════════════════════════════════════════════════════
section_title("Recent Activity")

ct1, ct2 = st.columns(2)

with ct1:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;overflow:hidden;
                box-shadow:0 1px 3px rgba(0,0,0,.05)">
      <div style="padding:12px 16px;border-bottom:1px solid #e9e9e7;background:#fafafa;
                  font-size:0.78rem;font-weight:600;color:#1a1a1a">🛍️ 최근 수주</div>
    </div>""", unsafe_allow_html=True)
    conn = get_db()
    df_so = pd.read_sql_query("""
        SELECT order_number AS 주문번호, customer_name AS 고객,
               item_name AS 품목, quantity AS 수량, status AS 상태
        FROM sales_orders ORDER BY id DESC LIMIT 6""", conn)
    conn.close()
    if not df_so.empty: st.dataframe(df_so, use_container_width=True, hide_index=True, height=210)
    else: st.info("주문 없음")

with ct2:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e9e9e7;border-radius:10px;overflow:hidden;
                box-shadow:0 1px 3px rgba(0,0,0,.05)">
      <div style="padding:12px 16px;border-bottom:1px solid #e9e9e7;background:#fafafa;
                  font-size:0.78rem;font-weight:600;color:#1a1a1a">🛒 최근 발주</div>
    </div>""", unsafe_allow_html=True)
    conn = get_db()
    df_po = pd.read_sql_query("""
        SELECT p.po_number AS 발주번호,
               COALESCE(s.name,'—') AS 공급사,
               p.item_name AS 품목, p.quantity AS 수량, p.status AS 상태
        FROM purchase_orders p LEFT JOIN suppliers s ON p.supplier_id=s.id
        ORDER BY p.id DESC LIMIT 6""", conn)
    conn.close()
    if not df_po.empty: st.dataframe(df_po, use_container_width=True, hide_index=True, height=210)
    else: st.info("발주 없음")

# ── 하단 서명 ─────────────────────────────────────────
st.markdown("""
<div style="margin-top:32px;padding-top:14px;border-top:1px solid #e9e9e7;
            display:flex;justify-content:space-between;align-items:center">
    <span style="font-size:.68rem;color:#c2c2c2">SCM ENTERPRISE · MM · SD · PP · QM · WM · TM</span>
    <span style="font-size:.68rem;color:#c2c2c2">Powered by Streamlit</span>
</div>
""", unsafe_allow_html=True)
