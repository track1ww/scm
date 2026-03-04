"""
SCM 통합관리 시스템 — 글로벌 디자인 시스템
다크 네이비 + 골드 액센트의 프리미엄 엔터프라이즈 테마
"""

GLOBAL_CSS = """
<style>
/* ── Google Fonts ───────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,300&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── CSS Variables ──────────────────────────────────── */
:root {
    --bg-base:       #0d1117;
    --bg-surface:    #161b22;
    --bg-elevated:   #1c2128;
    --bg-hover:      #21262d;
    --border:        #30363d;
    --border-subtle: #21262d;

    --text-primary:  #e6edf3;
    --text-secondary:#8b949e;
    --text-muted:    #484f58;

    --accent-gold:   #d4a843;
    --accent-gold-dim:#9a7a32;
    --accent-blue:   #388bfd;
    --accent-green:  #3fb950;
    --accent-red:    #f85149;
    --accent-orange: #f0883e;
    --accent-purple: #a371f7;
    --accent-teal:   #39d353;

    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-xl: 22px;

    --shadow-sm: 0 1px 3px rgba(0,0,0,.4);
    --shadow-md: 0 4px 16px rgba(0,0,0,.5);
    --shadow-lg: 0 8px 32px rgba(0,0,0,.6);
    --shadow-gold: 0 0 20px rgba(212,168,67,.15);
}

/* ── 전체 기반 ──────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: 'Noto Sans KR', 'DM Sans', sans-serif !important;
}

/* 메인 컨텐츠 영역 */
[data-testid="stMain"] {
    background: var(--bg-base) !important;
}
[data-testid="block-container"] {
    padding: 1.5rem 2.5rem 3rem !important;
    max-width: 1600px !important;
}

/* ── 사이드바 ───────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}
[data-testid="stSidebarNav"] a {
    border-radius: var(--radius-sm) !important;
    margin: 2px 0 !important;
    transition: background .15s !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: var(--bg-hover) !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: linear-gradient(90deg, rgba(212,168,67,.2), transparent) !important;
    border-left: 3px solid var(--accent-gold) !important;
}

/* ── 탭 ──────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: var(--bg-surface) !important;
    border-radius: var(--radius-md) !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    transition: all .15s !important;
    border: none !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background: var(--bg-hover) !important;
    color: var(--text-primary) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-dim)) !important;
    color: #0d1117 !important;
    font-weight: 700 !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── 버튼 ─────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Noto Sans KR', sans-serif !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    transition: all .15s !important;
}
[data-testid="stButton"] > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--accent-gold) !important;
    color: var(--accent-gold) !important;
    transform: translateY(-1px) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-dim)) !important;
    color: #0d1117 !important;
    border: none !important;
    font-weight: 700 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #e8bc55, var(--accent-gold)) !important;
    color: #0d1117 !important;
    box-shadow: var(--shadow-gold) !important;
    transform: translateY(-1px) !important;
}

/* ── 폼 / 입력 ──────────────────────────────────────── */
[data-testid="stForm"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 20px !important;
}
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    transition: border-color .15s !important;
}
[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within,
[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent-gold) !important;
    box-shadow: 0 0 0 2px rgba(212,168,67,.15) !important;
}
input, textarea, select {
    color: var(--text-primary) !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
label {
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: .03em !important;
    text-transform: uppercase !important;
}

/* ── 체크박스 / 슬라이더 ────────────────────────────── */
[data-baseweb="checkbox"] span {
    border-color: var(--border) !important;
    background: var(--bg-elevated) !important;
}
[data-baseweb="checkbox"] [aria-checked="true"] span {
    background: var(--accent-gold) !important;
    border-color: var(--accent-gold) !important;
}
[data-baseweb="slider"] [role="slider"] {
    background: var(--accent-gold) !important;
    border-color: var(--accent-gold) !important;
}

/* ── 데이터프레임 ────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] table {
    background: var(--bg-surface) !important;
    font-size: 0.8rem !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
[data-testid="stDataFrame"] th {
    background: var(--bg-elevated) !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    letter-spacing: .04em !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 8px 12px !important;
}
[data-testid="stDataFrame"] td {
    color: var(--text-primary) !important;
    border-color: var(--border-subtle) !important;
    padding: 7px 12px !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: var(--bg-hover) !important;
}

/* ── 메트릭 카드 ─────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 14px 18px !important;
    transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stMetric"]:hover {
    border-color: var(--accent-gold-dim) !important;
    box-shadow: var(--shadow-gold) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: .06em !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* ── 알림 박스 ───────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border-width: 1px !important;
    font-size: 0.83rem !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="info"] {
    background: rgba(56,139,253,.08) !important;
    border-color: rgba(56,139,253,.3) !important;
    color: #79b8ff !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {
    background: rgba(63,185,80,.08) !important;
    border-color: rgba(63,185,80,.3) !important;
    color: #56d364 !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="warning"] {
    background: rgba(210,153,34,.08) !important;
    border-color: rgba(210,153,34,.3) !important;
    color: #e3b341 !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="error"] {
    background: rgba(248,81,73,.08) !important;
    border-color: rgba(248,81,73,.3) !important;
    color: #ff7b72 !important;
}

/* ── divider ─────────────────────────────────────────── */
hr {
    border-color: var(--border) !important;
    margin: 1.2rem 0 !important;
}

/* ── 제목 계층 ───────────────────────────────────────── */
h1 {
    font-family: 'DM Sans', 'Noto Sans KR', sans-serif !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -.02em !important;
}
h2 {
    font-family: 'DM Sans', 'Noto Sans KR', sans-serif !important;
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 8px !important;
    margin-bottom: 16px !important;
}
h3 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
}

/* ── 코드 ────────────────────────────────────────────── */
code, [data-testid="stCode"] {
    font-family: 'JetBrains Mono', monospace !important;
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--accent-gold) !important;
    font-size: 0.78rem !important;
}

/* ── selectbox 드롭다운 ──────────────────────────────── */
[data-baseweb="popover"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
}
[data-baseweb="menu"] li {
    color: var(--text-primary) !important;
    font-size: 0.83rem !important;
}
[data-baseweb="menu"] li:hover {
    background: var(--bg-hover) !important;
}

/* ── 스크롤바 ─────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ── 커스텀 컴포넌트 ─────────────────────────────────── */
.scm-page-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 0 20px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
}
.scm-page-header .icon {
    font-size: 2rem;
    width: 52px; height: 52px;
    display: flex; align-items: center; justify-content: center;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
}
.scm-page-header .title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); }
.scm-page-header .subtitle { font-size: 0.78rem; color: var(--text-secondary); margin-top: 2px; }

.scm-section {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--accent-gold);
    letter-spacing: .1em;
    text-transform: uppercase;
    margin: 20px 0 10px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.scm-section::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

.kpi-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    transition: all .2s;
}
.kpi-card:hover {
    border-color: var(--accent-gold-dim);
    box-shadow: var(--shadow-gold);
    transform: translateY(-2px);
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.kpi-mm::before  { background: linear-gradient(90deg,#388bfd,transparent); }
.kpi-sd::before  { background: linear-gradient(90deg,#3fb950,transparent); }
.kpi-pp::before  { background: linear-gradient(90deg,#d4a843,transparent); }
.kpi-qm::before  { background: linear-gradient(90deg,#f85149,transparent); }
.kpi-wm::before  { background: linear-gradient(90deg,#a371f7,transparent); }
.kpi-tm::before  { background: linear-gradient(90deg,#39d353,transparent); }
.kpi-card .kpi-icon { font-size: 1.5rem; margin-bottom: 8px; }
.kpi-card .kpi-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;
}
.kpi-card .kpi-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 2rem; font-weight: 700; color: var(--text-primary);
    line-height: 1;
}
.kpi-card .kpi-sub {
    font-size: 0.72rem; color: var(--text-secondary); margin-top: 4px;
}
.kpi-card .kpi-badge {
    display: inline-block;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-top: 8px;
}
.badge-alert { background: rgba(248,81,73,.1)!important; border-color: rgba(248,81,73,.3)!important; color: #f85149!important; }
.badge-warn  { background: rgba(210,153,34,.1)!important; border-color: rgba(210,153,34,.3)!important; color: #e3b341!important; }
.badge-ok    { background: rgba(63,185,80,.1)!important;  border-color: rgba(63,185,80,.3)!important;  color: #3fb950!important; }

.dash-table-wrap {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
}
.dash-table-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
}
.dash-table-header .dth-title {
    font-size: 0.78rem; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase;
    color: var(--text-secondary);
}

/* ── Plotly 배경 강제 투명 ─────────────────────────── */
.js-plotly-plot .plotly, .js-plotly-plot .plotly .svg-container {
    background: transparent !important;
}
</style>
"""

def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

def page_header(icon: str, title: str, subtitle: str = ""):
    import streamlit as st
    st.markdown(f"""
    <div class="scm-page-header">
        <div class="icon">{icon}</div>
        <div>
            <div class="title">{title}</div>
            {'<div class="subtitle">'+subtitle+'</div>' if subtitle else ''}
        </div>
    </div>""", unsafe_allow_html=True)

def section_title(label: str):
    import streamlit as st
    st.markdown(f'<div class="scm-section">{label}</div>', unsafe_allow_html=True)

def kpi_card(icon: str, label: str, value, sub: str = "", badge: str = "", badge_type: str = "ok", css_class: str = ""):
    badge_html = f'<div class="kpi-badge badge-{badge_type}">{badge}</div>' if badge else ""
    return f"""
    <div class="kpi-card {css_class}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {'<div class="kpi-sub">'+sub+'</div>' if sub else ''}
        {badge_html}
    </div>"""

def apply_plotly_theme():
    """Plotly 차트에 다크 테마 전역 적용"""
    try:
        import plotly.io as pio
        import plotly.graph_objects as go

        pio.templates["scm_dark"] = go.layout.Template(
            layout=go.Layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#161b22",
                font=dict(family="Noto Sans KR, DM Sans, sans-serif",
                          color="#8b949e", size=11),
                title=dict(font=dict(color="#e6edf3", size=14, family="DM Sans")),
                xaxis=dict(
                    gridcolor="#21262d", linecolor="#30363d",
                    tickcolor="#484f58", zerolinecolor="#30363d",
                ),
                yaxis=dict(
                    gridcolor="#21262d", linecolor="#30363d",
                    tickcolor="#484f58", zerolinecolor="#30363d",
                ),
                legend=dict(
                    bgcolor="rgba(22,27,34,0.9)",
                    bordercolor="#30363d", borderwidth=1,
                    font=dict(color="#8b949e", size=10),
                ),
                colorway=["#388bfd","#3fb950","#d4a843","#f85149","#a371f7","#39d353","#f0883e","#58a6ff"],
                margin=dict(l=8, r=8, t=40, b=8),
                hoverlabel=dict(
                    bgcolor="#1c2128", bordercolor="#30363d",
                    font=dict(color="#e6edf3", size=11),
                ),
            )
        )
        pio.templates.default = "scm_dark"
    except Exception:
        pass
