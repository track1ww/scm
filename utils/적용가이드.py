# ══════════════════════════════════════════════════════
#  SCM 인증/권한 시스템 — 적용 가이드
# ══════════════════════════════════════════════════════

# ── 1. 패키지 설치 ────────────────────────────────────
# pip install pymysql bcrypt


# ── 2. 파일 배치 ─────────────────────────────────────
# scm_sap/
# ├── app.py                     ← 수정 필요 (아래 참고)
# ├── utils/
# │   ├── db.py                  ← MySQL 버전으로 교체
# │   ├── auth.py                ← 신규 추가
# │   └── design.py              ← 기존 유지
# └── pages/
#     ├── 0_🔐_로그인.py         ← 신규 추가
#     ├── 1_🛒_MM_자재관리.py    ← 권한 체크 추가 (아래 참고)
#     ├── ...
#     └── 9_👑_관리자.py         ← 신규 추가


# ── 3. 환경변수 설정 (.env 또는 서버 환경변수) ─────────
# SCM_DB_HOST=192.168.x.x       # 사내 MySQL 서버 IP
# SCM_DB_PORT=3306
# SCM_DB_USER=scm_user
# SCM_DB_PASS=your_password
# SCM_DB_NAME=scm_db


# ── 4. MySQL DB 초기화 (최초 1회) ─────────────────────
# python -c "from utils.db import init_db, insert_default_data; init_db(); insert_default_data()"
# → 초기 관리자 계정: admin@company.com / admin1234


# ── 5. app.py 상단에 추가할 코드 ─────────────────────
APP_PY_SNIPPET = """
from utils.auth import is_logged_in, render_sidebar_user, get_current_user

# 로그인 체크 — 로그인 안 된 경우 로그인 페이지로 유도
if not is_logged_in():
    st.warning("🔐 로그인이 필요합니다.")
    st.page_link("pages/0_🔐_로그인.py", label="→ 로그인 페이지로 이동")
    st.stop()

# 사이드바 사용자 정보 + 로그아웃 버튼
render_sidebar_user()
"""


# ── 6. 각 페이지 상단에 추가할 코드 ───────────────────
# page_key: mm / sd / pp / qm / wm / tm / calc / ai

PAGE_SNIPPET = """
from utils.auth import require_permission, render_sidebar_user

render_sidebar_user()

# 읽기 권한 체크 (페이지 접근)
require_permission("mm")           # mm 자리에 해당 페이지 키 입력

# 쓰기 권한이 필요한 버튼/폼 앞에서 체크
# if not has_permission("mm", write=True):
#     st.warning("쓰기 권한이 없습니다.")
#     st.stop()
"""

# 페이지별 키 매핑
PAGE_KEYS = {
    "1_🛒_MM_자재관리.py":    "mm",
    "2_🛍️_SD_판매출하.py":   "sd",
    "3_🏭_PP_생산계획.py":    "pp",
    "4_🔬_QM_품질관리.py":    "qm",
    "5_📦_WM_창고관리.py":    "wm",
    "6_🚢_TM_운송관리.py":    "tm",
    "7_📐_SCM_공식계산기.py": "calc",
    "8_🤖_AI_수요예측.py":    "ai",
}

# ── 7. 쓰기 권한 적용 예시 (각 페이지 내 폼/버튼) ────
WRITE_PERM_EXAMPLE = """
from utils.auth import has_permission

# 저장/수정/삭제 버튼 앞에 체크
can_write = has_permission("mm", write=True)

with st.form("add_po"):
    ...
    submitted = st.form_submit_button("저장", disabled=not can_write)

if submitted and can_write:
    # DB 저장 로직
    ...
elif submitted:
    st.warning("쓰기 권한이 없습니다.")
"""

if __name__ == "__main__":
    print("=" * 60)
    print("SCM 인증/권한 시스템 적용 가이드")
    print("=" * 60)
    print("\n[app.py 추가 코드]")
    print(APP_PY_SNIPPET)
    print("\n[각 페이지 상단 추가 코드]")
    print(PAGE_SNIPPET)
    print("\n[페이지별 page_key 매핑]")
    for f, k in PAGE_KEYS.items():
        print(f"  {f} → '{k}'")
