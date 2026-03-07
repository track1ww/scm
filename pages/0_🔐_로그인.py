"""
로그인 / 회원가입 페이지
pages/0_🔐_로그인.py 로 저장하세요
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.design import inject_css, apply_plotly_theme
from utils.auth import login_user, register_user, is_logged_in, get_allowed_domains

st.set_page_config(page_title="SCM 로그인", page_icon="🔐", layout="centered")
inject_css()
apply_plotly_theme()

# 이미 로그인된 경우
if is_logged_in():
    st.success("✅ 이미 로그인되어 있습니다.")
    st.page_link("app.py", label="대시보드로 이동 →")
    st.stop()

# ── 헤더 ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:40px 0 24px">
    <div style="font-size:2.8rem;margin-bottom:8px">⛓</div>
    <div style="font-size:1.6rem;font-weight:800;color:#1a1a1a;letter-spacing:-.03em">
        SCM 통합관리 시스템
    </div>
    <div style="font-size:0.85rem;color:#9b9b9b;margin-top:4px">
        사내 이메일로 로그인하세요
    </div>
</div>""", unsafe_allow_html=True)

# ── 탭: 로그인 / 회원가입 ────────────────────────────
tab_login, tab_register = st.tabs(["🔑 로그인", "✏️ 회원가입"])

with tab_login:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.form("login_form"):
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
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # 허용 도메인 안내
    domains = get_allowed_domains()
    if domains:
        st.info(f"💡 가입 가능 도메인: {', '.join(['@'+d for d in domains])}")

    with st.form("register_form"):
        r_name  = st.text_input("이름")
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
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("""
    <div style="margin-top:16px;padding:12px 16px;background:#f7f7f5;
                border-radius:8px;font-size:0.78rem;color:#6b6b6b">
        가입 후 관리자가 페이지별 권한을 부여해야 이용할 수 있습니다.
    </div>""", unsafe_allow_html=True)
