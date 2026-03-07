"""
관리자 페이지 — 사용자 관리 + 페이지별 권한 부여
pages/9_👑_관리자.py 로 저장하세요
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.design import inject_css, apply_plotly_theme, section_title, page_header
from utils.auth import require_permission, render_sidebar_user, PAGES, get_allowed_domains
from utils.db import get_db

st.set_page_config(page_title="관리자", page_icon="👑", layout="wide")
inject_css()
apply_plotly_theme()
render_sidebar_user()
require_permission("admin")

page_header("👑", "관리자", "사용자 계정 관리 및 페이지별 권한 부여")

tab_users, tab_perms, tab_domains = st.tabs(["👥 사용자 목록", "🔑 권한 관리", "🌐 허용 도메인"])

# ══════════════════════════════════════════════════════
#  탭 1 — 사용자 목록
# ══════════════════════════════════════════════════════
with tab_users:
    section_title("전체 사용자")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.email, u.name, u.department,
               u.is_admin, u.is_active, u.last_login, u.created_at,
               COUNT(p.page_key) AS perm_count
        FROM users u
        LEFT JOIN user_permissions p ON p.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """)
    users = c.fetchall()
    conn.close()

    if not users:
        st.info("등록된 사용자가 없습니다.")
    else:
        for u in users:
            active_color = "#0f9960" if u["is_active"] else "#d44c47"
            admin_badge  = '<span style="background:#e8f3fd;color:#2383e2;font-size:0.68rem;padding:2px 8px;border-radius:4px;font-weight:600;margin-left:6px">관리자</span>' if u["is_admin"] else ""
            last = u["last_login"].strftime("%Y-%m-%d %H:%M") if u["last_login"] else "미로그인"

            with st.expander(f"{'🟢' if u['is_active'] else '🔴'} {u['name']}  ({u['email']})  권한 {u['perm_count']}개"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("부서", u["department"] or "-")
                c2.metric("권한 페이지 수", u["perm_count"])
                c3.metric("마지막 로그인", last)
                c4.metric("상태", "활성" if u["is_active"] else "비활성")

                col_a, col_b, col_c = st.columns(3)

                # 활성/비활성 토글
                with col_a:
                    btn_label = "🚫 비활성화" if u["is_active"] else "✅ 활성화"
                    if st.button(btn_label, key=f"toggle_{u['id']}"):
                        conn2 = get_db()
                        c2_ = conn2.cursor()
                        c2_.execute("UPDATE users SET is_active=%s WHERE id=%s",
                                    (0 if u["is_active"] else 1, u["id"]))
                        conn2.commit()
                        conn2.close()
                        st.rerun()

                # 관리자 권한 토글
                with col_b:
                    adm_label = "👤 일반사용자로" if u["is_admin"] else "👑 관리자로"
                    if st.button(adm_label, key=f"admin_{u['id']}"):
                        conn2 = get_db()
                        c2_ = conn2.cursor()
                        c2_.execute("UPDATE users SET is_admin=%s WHERE id=%s",
                                    (0 if u["is_admin"] else 1, u["id"]))
                        conn2.commit()
                        conn2.close()
                        st.rerun()

                # 비밀번호 초기화
                with col_c:
                    if st.button("🔑 비밀번호 초기화", key=f"pw_{u['id']}"):
                        import bcrypt
                        new_pw = bcrypt.hashpw("scm1234!".encode(), bcrypt.gensalt()).decode()
                        conn2 = get_db()
                        c2_ = conn2.cursor()
                        c2_.execute("UPDATE users SET password=%s WHERE id=%s",
                                    (new_pw, u["id"]))
                        conn2.commit()
                        conn2.close()
                        st.success(f"비밀번호가 'scm1234!'로 초기화되었습니다.")

# ══════════════════════════════════════════════════════
#  탭 2 — 권한 관리
# ══════════════════════════════════════════════════════
with tab_perms:
    section_title("페이지별 권한 부여")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, email, department FROM users WHERE is_active=1 AND is_admin=0 ORDER BY name")
    normal_users = c.fetchall()
    conn.close()

    if not normal_users:
        st.info("권한 관리 대상 일반 사용자가 없습니다.")
    else:
        # 사용자 선택
        user_options = {f"{u['name']} ({u['email']}) - {u['department'] or '부서없음'}": u["id"]
                        for u in normal_users}
        selected_label = st.selectbox("권한을 설정할 사용자 선택",
                                      list(user_options.keys()),
                                      label_visibility="collapsed")
        selected_user_id = user_options[selected_label]

        # 현재 권한 조회
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT page_key, can_read, can_write FROM user_permissions WHERE user_id=%s",
                  (selected_user_id,))
        current_perms = {r["page_key"]: r for r in c.fetchall()}
        conn.close()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.72rem;font-weight:600;color:#9b9b9b;
                    letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px">
            페이지별 권한 설정
        </div>""", unsafe_allow_html=True)

        # 권한 테이블 UI
        new_perms = {}
        header = st.columns([3, 1, 1])
        header[0].markdown("**페이지**")
        header[1].markdown("**읽기**")
        header[2].markdown("**쓰기**")
        st.markdown("<hr style='margin:4px 0 8px'>", unsafe_allow_html=True)

        for page_key, page_info in PAGES.items():
            if page_key == "admin":
                continue  # 관리자 페이지는 is_admin 플래그로 제어
            cur = current_perms.get(page_key, {})
            row = st.columns([3, 1, 1])
            row[0].markdown(f"{page_info['icon']} {page_info['label']}")
            can_read  = row[1].checkbox("", value=bool(cur.get("can_read", 0)),
                                         key=f"read_{selected_user_id}_{page_key}")
            can_write = row[2].checkbox("", value=bool(cur.get("can_write", 0)),
                                         key=f"write_{selected_user_id}_{page_key}",
                                         disabled=not can_read)
            if can_read:
                new_perms[page_key] = (can_read, can_write)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("💾 권한 저장", type="primary", use_container_width=True):
            conn = get_db()
            c = conn.cursor()
            # 기존 권한 삭제 후 재삽입
            c.execute("DELETE FROM user_permissions WHERE user_id=%s", (selected_user_id,))
            for page_key, (r, w) in new_perms.items():
                c.execute("""INSERT INTO user_permissions
                             (user_id, page_key, can_read, can_write)
                             VALUES (%s, %s, %s, %s)""",
                          (selected_user_id, page_key, int(r), int(w)))
            conn.commit()
            conn.close()
            st.success(f"✅ 권한이 저장되었습니다. ({len(new_perms)}개 페이지)")
            st.rerun()

        # 현재 권한 요약
        if current_perms:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            section_title("현재 부여된 권한")
            cols = st.columns(4)
            for i, (pk, pv) in enumerate(current_perms.items()):
                page_info = PAGES.get(pk, {"icon": "📄", "label": pk})
                rw = []
                if pv.get("can_read"):  rw.append("읽기")
                if pv.get("can_write"): rw.append("쓰기")
                cols[i % 4].markdown(f"""
                <div style="background:#f7f7f5;border:1px solid #e9e9e7;border-radius:8px;
                            padding:10px 12px;margin-bottom:8px">
                    <div style="font-size:1rem">{page_info['icon']}</div>
                    <div style="font-size:0.78rem;font-weight:600;color:#1a1a1a">{page_info['label']}</div>
                    <div style="font-size:0.7rem;color:#2383e2;margin-top:2px">{' · '.join(rw)}</div>
                </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  탭 3 — 허용 도메인 관리
# ══════════════════════════════════════════════════════
with tab_domains:
    section_title("허용 이메일 도메인")
    st.caption("이 도메인의 이메일만 회원가입이 가능합니다.")

    domains = get_allowed_domains()
    for d in domains:
        col1, col2 = st.columns([4, 1])
        col1.markdown(f"""
        <div style="background:#f7f7f5;border:1px solid #e9e9e7;border-radius:8px;
                    padding:10px 16px;font-weight:600;color:#1a1a1a">
            @{d}
        </div>""", unsafe_allow_html=True)
        if col2.button("삭제", key=f"del_domain_{d}"):
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM allowed_domains WHERE domain=%s", (d,))
            conn.commit()
            conn.close()
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_title("도메인 추가")
    with st.form("add_domain"):
        new_domain = st.text_input("도메인 입력", placeholder="company.com (@제외)")
        if st.form_submit_button("➕ 추가", type="primary"):
            domain_clean = new_domain.strip().lstrip("@").lower()
            if domain_clean:
                conn = get_db()
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO allowed_domains (domain) VALUES (%s)", (domain_clean,))
                    conn.commit()
                    st.success(f"@{domain_clean} 추가됨")
                except:
                    st.error("이미 등록된 도메인입니다.")
                conn.close()
                st.rerun()
