"""
SCM 통합관리 시스템 — Notion Style Design System
클린 화이트 + 그레이 계열의 노션 스타일 테마
"""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

:root {
    --bg:           #ffffff;
    --bg-secondary: #f7f7f5;
    --bg-hover:     #f1f1ef;
    --bg-selected:  #e9e9e7;
    --border:       #e9e9e7;
    --border-strong:#d3d3cf;

    --text-primary:  #1a1a1a;
    --text-secondary:#6b6b6b;
    --text-muted:    #9b9b9b;
    --text-placeholder: #c2c2c2;

    --accent:       #2383e2;
    --accent-light: #e8f3fd;
    --accent-green: #0f9960;
    --accent-red:   #d44c47;
    --accent-orange:#c9711c;
    --accent-purple:#9065b0;
    --accent-yellow:#cb912f;

    --radius-xs: 4px;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;

    --shadow-xs: 0 1px 2px rgba(0,0,0,.05);
    --shadow-sm: 0 1px 4px rgba(0,0,0,.08), 0 0 0 1px rgba(0,0,0,.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,.08), 0 0 0 1px rgba(0,0,0,.04);
}

/* ── 전체 기반 ─────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main {
    background: var(--bg) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
}
[data-testid="block-container"] {
    padding: 2rem 3rem 4rem !important;
    max-width: 1400px !important;
}

/* ── 사이드바 ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}
[data-testid="stSidebarNav"] a {
    border-radius: var(--radius-sm) !important;
    margin: 1px 8px !important;
    padding: 6px 10px !important;
    font-size: 0.85rem !important;
    color: var(--text-secondary) !important;
    transition: background .12s !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: var(--bg-hover) !important;
    color: var(--text-primary) !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: var(--bg-selected) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

/* ── 탭 ───────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0 !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    margin-bottom: -1px !important;
    transition: all .12s !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background: var(--bg-hover) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid var(--text-primary) !important;
    background: transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── 버튼 ──────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: var(--bg) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 5px 14px !important;
    transition: all .12s !important;
    box-shadow: var(--shadow-xs) !important;
}
[data-testid="stButton"] > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--border-strong) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: #c9b8e8 !important;
    color: #3d2b6b !important;
    border: none !important;
    font-weight: 600 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #b8a4de !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ── 폼 ────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 20px !important;
}
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
    background: var(--bg) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    transition: border-color .12s, box-shadow .12s !important;
}
[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within,
[data-baseweb="select"] > div:focus-within {
    border-color: var(--text-primary) !important;
    box-shadow: 0 0 0 2px rgba(0,0,0,.08) !important;
}
input, textarea, select {
    color: var(--text-primary) !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
}
label {
    color: var(--text-secondary) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
}

/* ── 데이터프레임 ───────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-xs) !important;
}
[data-testid="stDataFrame"] table {
    background: var(--bg) !important;
    font-size: 0.82rem !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
}
[data-testid="stDataFrame"] th {
    background: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    letter-spacing: .02em !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 8px 12px !important;
}
[data-testid="stDataFrame"] td {
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
    padding: 7px 12px !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: var(--bg-hover) !important;
}

/* ── 메트릭 ────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 16px 18px !important;
    box-shadow: var(--shadow-xs) !important;
    transition: box-shadow .12s !important;
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── 알림 ──────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border-width: 1px !important;
    font-size: 0.84rem !important;
    border-left-width: 3px !important;
}

/* ── 제목 ──────────────────────────────────────────── */
h1 {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -.02em !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
}
h2 {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
}
h3 {
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
}
p, li {
    color: var(--text-primary) !important;
    font-size: 0.9rem !important;
}

/* ── Divider ───────────────────────────────────────── */
hr {
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}

/* ── 스크롤바 ──────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }

/* ── 노션 커스텀 컴포넌트 ──────────────────────────── */

/* 페이지 헤더 */
.notion-page-header {
    padding: 8px 0 24px 0;
    margin-bottom: 8px;
}
.notion-page-icon {
    font-size: 2.4rem;
    margin-bottom: 8px;
    display: block;
}
.notion-page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -.03em;
    line-height: 1.3;
}
.notion-page-desc {
    font-size: 0.84rem;
    color: var(--text-muted);
    margin-top: 4px;
}

/* 섹션 헤더 */
.notion-section {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-muted);
    letter-spacing: .08em;
    text-transform: uppercase;
    margin: 24px 0 10px 0;
}

/* 프로퍼티 뱃지 */
.n-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 500;
    background: var(--bg-selected);
    color: var(--text-secondary);
}
.n-badge-blue   { background:#e8f3fd; color:#2383e2; }
.n-badge-green  { background:#e6f4ed; color:#0f9960; }
.n-badge-red    { background:#fdecea; color:#d44c47; }
.n-badge-orange { background:#fdf0e4; color:#c9711c; }
.n-badge-purple { background:#f3eef8; color:#9065b0; }
.n-badge-gray   { background:#f1f1ef; color:#6b6b6b; }

/* KPI 카드 */
.notion-kpi {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 18px 20px;
    transition: box-shadow .15s;
    cursor: default;
}
.notion-kpi:hover {
    box-shadow: var(--shadow-sm);
}
.notion-kpi-label {
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text-muted);
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.notion-kpi-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    line-height: 1;
}
.notion-kpi-sub {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 6px;
}

/* 테이블 카드 래퍼 */
.notion-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
}
.notion-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px 10px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
}
.notion-card-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
}
</style>
"""

def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

def apply_plotly_theme():
    try:
        import plotly.io as pio
        import plotly.graph_objects as go
        pio.templates["notion_light"] = go.layout.Template(
            layout=go.Layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#f7f7f5",
                font=dict(family="Inter, Noto Sans KR, sans-serif",
                          color="#6b6b6b", size=11),
                title=dict(font=dict(color="#1a1a1a", size=13,
                                     family="Inter, Noto Sans KR")),
                xaxis=dict(gridcolor="#e9e9e7", linecolor="#d3d3cf",
                           tickcolor="#9b9b9b", zerolinecolor="#e9e9e7"),
                yaxis=dict(gridcolor="#e9e9e7", linecolor="#d3d3cf",
                           tickcolor="#9b9b9b", zerolinecolor="#e9e9e7"),
                legend=dict(bgcolor="rgba(255,255,255,0.9)",
                            bordercolor="#e9e9e7", borderwidth=1,
                            font=dict(color="#6b6b6b", size=10)),
                colorway=["#2383e2","#0f9960","#cb912f","#d44c47",
                          "#9065b0","#448361","#c9711c","#3f88c5"],
                margin=dict(l=8, r=8, t=36, b=8),
                hoverlabel=dict(bgcolor="#fff", bordercolor="#e9e9e7",
                                font=dict(color="#1a1a1a", size=11)),
            )
        )
        pio.templates.default = "notion_light"
    except Exception:
        pass

def page_header(icon: str, title: str, desc: str = ""):
    import streamlit as st
    st.markdown(f"""
    <div class="notion-page-header">
        <span class="notion-page-icon">{icon}</span>
        <div class="notion-page-title">{title}</div>
        {'<div class="notion-page-desc">'+desc+'</div>' if desc else ''}
    </div>""", unsafe_allow_html=True)

def section_title(label: str):
    import streamlit as st
    st.markdown(f'<div class="notion-section">{label}</div>',
                unsafe_allow_html=True)

def kpi_card(icon: str, label: str, value, sub: str = "",
             badge: str = "", badge_type: str = "gray"):
    badge_html = (f'<span class="n-badge n-badge-{badge_type}">{badge}</span>'
                  if badge else "")
    return f"""
    <div class="notion-kpi">
        <div class="notion-kpi-label">{icon} {label} {badge_html}</div>
        <div class="notion-kpi-value">{value}</div>
        {'<div class="notion-kpi-sub">'+sub+'</div>' if sub else ''}
    </div>"""

def card_header(icon: str, title: str, tag: str = "", tag_type: str = "gray"):
    tag_html = (f'<span class="n-badge n-badge-{tag_type}">{tag}</span>'
                if tag else "")
    import streamlit as st
    st.markdown(f"""
    <div class="notion-card-header">
        <span class="notion-card-title">{icon} {title}</span>
        {tag_html}
    </div>""", unsafe_allow_html=True)
