"""
SCM 통합관리 시스템 — 인증 / 권한 관리
utils/auth.py 로 저장하세요

pip install bcrypt
"""
import streamlit as st
import bcrypt
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.db import get_db
except ImportError:
    from db import get_db

# ── 페이지 정의 ───────────────────────────────────────
PAGES = {
    "mm":   {"label": "MM 자재관리",   "icon": "🛒"},
    "sd":   {"label": "SD 판매출하",   "icon": "🛍️"},
    "pp":   {"label": "PP 생산계획",   "icon": "🏭"},
    "qm":   {"label": "QM 품질관리",   "icon": "🔬"},
    "wm":   {"label": "WM 창고관리",   "icon": "📦"},
    "tm":   {"label": "TM 운송관리",   "icon": "🚢"},
    "calc": {"label": "SCM 공식계산기","icon": "📐"},
    "ai":   {"label": "AI 수요예측",   "icon": "🤖"},
    "admin":{"label": "관리자",        "icon": "👑"},
}

# ── 도메인 검증 ───────────────────────────────────────
def get_allowed_domains():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT domain FROM allowed_domains")
        rows = c.fetchall()
        conn.close()
        return [r["domain"] for r in rows]
    except:
        return []

def is_allowed_email(email: str) -> bool:
    domains = get_allowed_domains()
    if not domains:
        return True  # 도메인 미설정 시 전체 허용
    domain = email.split("@")[-1].lower() if "@" in email else ""
    return domain in [d.lower() for d in domains]

# ── 비밀번호 ─────────────────────────────────────────
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except:
        return False

# ── 회원가입 ─────────────────────────────────────────
def register_user(email, name, password, department="") -> tuple[bool, str]:
    email = email.strip().lower()

    if not re.match(r"^[\w.+-]+@[\w-]+\.[a-z]{2,}$", email):
        return False, "이메일 형식이 올바르지 않습니다."
    if not is_allowed_email(email):
        domains = get_allowed_domains()
        return False, f"허용된 도메인이 아닙니다. ({', '.join(['@'+d for d in domains])})"
    if len(password) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다."

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=%s", (email,))
        if c.fetchone():
            conn.close()
            return False, "이미 가입된 이메일입니다."

        pw_hash = hash_password(password)
        c.execute("""INSERT INTO users (email, name, password, department)
                     VALUES (%s, %s, %s, %s)""",
                  (email, name, pw_hash, department))
        conn.commit()
        conn.close()
        return True, "가입 완료! 관리자가 권한을 부여하면 이용할 수 있습니다."
    except Exception as e:
        return False, f"오류: {e}"

# ── 로그인 ───────────────────────────────────────────
def login_user(email, password) -> tuple[bool, str]:
    email = email.strip().lower()
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=%s AND is_active=1", (email,))
        user = c.fetchone()
        if not user:
            conn.close()
            return False, "이메일 또는 비밀번호가 올바르지 않습니다."
        if not verify_password(password, user["password"]):
            conn.close()
            return False, "이메일 또는 비밀번호가 올바르지 않습니다."

        # 권한 조회
        c.execute("SELECT page_key, can_read, can_write FROM user_permissions WHERE user_id=%s",
                  (user["id"],))
        perms = {r["page_key"]: {"read": bool(r["can_read"]), "write": bool(r["can_write"])}
                 for r in c.fetchall()}

        # 관리자는 전체 권한
        if user["is_admin"]:
            perms = {k: {"read": True, "write": True} for k in PAGES}

        # last_login 업데이트
        c.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user["id"],))
        conn.commit()
        conn.close()

        # 세션 저장
        st.session_state["user"] = {
            "id":         user["id"],
            "email":      user["email"],
            "name":       user["name"],
            "department": user["department"],
            "is_admin":   bool(user["is_admin"]),
            "perms":      perms,
        }
        return True, f"{user['name']}님 환영합니다!"
    except Exception as e:
        return False, f"로그인 오류: {e}"

# ── 세션 체크 ─────────────────────────────────────────
def get_current_user():
    return st.session_state.get("user", None)

def is_logged_in() -> bool:
    return get_current_user() is not None

def logout():
    st.session_state.pop("user", None)

# ── 권한 체크 ─────────────────────────────────────────
def has_permission(page_key: str, write: bool = False) -> bool:
    user = get_current_user()
    if not user:
        return False
    if user["is_admin"]:
        return True
    perm = user["perms"].get(page_key, {})
    if write:
        return perm.get("write", False)
    return perm.get("read", False)

def require_permission(page_key: str, write: bool = False):
    """페이지 상단에 호출 — 권한 없으면 경고 후 st.stop()"""
    if not is_logged_in():
        st.warning("🔐 로그인이 필요합니다.")
        st.stop()
    if not has_permission(page_key, write):
        st.error(f"🚫 이 페이지에 대한 {'쓰기' if write else '읽기'} 권한이 없습니다.")
        st.info("관리자에게 권한 부여를 요청하세요.")
        st.stop()

# ── 사이드바 사용자 정보 ──────────────────────────────
def render_sidebar_user():
    user = get_current_user()
    if not user:
        return
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"""
        <div style="padding:10px 0">
            <div style="font-size:0.75rem;color:#9b9b9b">로그인 중</div>
            <div style="font-weight:700;color:#1a1a1a;margin-top:2px">{user['name']}</div>
            <div style="font-size:0.75rem;color:#6b6b6b">{user['email']}</div>
            <div style="font-size:0.72rem;color:#9b9b9b;margin-top:2px">{user.get('department','')}</div>
            {'<span style="background:#e8f3fd;color:#2383e2;font-size:0.68rem;padding:2px 8px;border-radius:4px;font-weight:600">관리자</span>' if user['is_admin'] else ''}
        </div>""", unsafe_allow_html=True)
        if st.button("로그아웃", use_container_width=True):
            logout()
            st.rerun()
