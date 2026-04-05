# ERP 통합관리 시스템

중소기업을 위한 웹 기반 ERP(Enterprise Resource Planning) 통합관리 시스템입니다.
Django REST Framework + React로 구성된 풀스택 애플리케이션으로, 사내 서버에 설치하여 PC 브라우저에서 사용합니다.

---

## 주요 기능

| 모듈 | 설명 |
|------|------|
| **MM** 자재관리 | 자재 등록·조회, 발주 관리 |
| **SD** 판매출하 | 수주, 출하 관리 |
| **PP** 생산계획 | 생산 오더, BOM(자재명세서) 관리 |
| **QM** 품질관리 | 검사 기준, 검사 결과 관리 |
| **WM** 창고관리 | 창고·위치·재고 입출고 관리 |
| **TM** 운송관리 | 운송 계획, 운송사 관리, 배송·통관 추적 |
| **FI** 재무회계 | 전표, 예산, 원가 관리 |
| **HR** 인사관리 | 직원, 근태, 급여, 휴가 관리 |
| **관리자** | 사용자 권한 관리, 외부 API 설정 |
| **대시보드** | 모듈별 KPI 요약, 실시간 환율 위젯 |

---

## 기술 스택

### 백엔드
- Python 3.11 / Django 4.2
- Django REST Framework (JWT 인증)
- PostgreSQL (데이터베이스)
- Redis + Django Channels (WebSocket·실시간 알림)
- Daphne (ASGI 서버)

### 프론트엔드
- React 18 (Vite)
- React Query (서버 상태 관리)
- Tailwind CSS + Inline Styles
- Lucide React (아이콘)

---

## 시스템 구조

```
브라우저 (Chrome/Edge)
    │
    ▼
Nginx (80포트)
    ├── /        → React 정적 파일 (dist/)
    ├── /api/    → Daphne (Django, 8000포트)
    └── /ws/     → WebSocket (Daphne)
                        │
                   PostgreSQL
                   Redis
```

---

## 로컬 개발 환경 실행

### 사전 준비
- Python 3.11+
- Node.js 20+
- PostgreSQL
- Redis

### 백엔드

```bash
cd scm2_django_v2
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# DB 생성 후
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 프론트엔드

```bash
cd scm2-frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

---

## 서버 배포

### 환경변수 (.env)

```ini
DJANGO_SECRET_KEY=50자_이상_랜덤_문자열
DEBUG=False
ALLOWED_HOSTS=서버IP,도메인
DB_NAME=scm2_db
DB_USER=scm2_user
DB_PASSWORD=패스워드
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

### 배포 순서

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 정적 파일 수집
python manage.py collectstatic --noinput

# 3. DB 마이그레이션
python manage.py migrate

# 4. 프론트엔드 빌드
cd scm2-frontend && npm run build

# 5. Daphne 실행 (systemd 등록 권장)
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Nginx 및 systemd 설정은 프로젝트 Wiki 또는 배포 가이드를 참고하세요.

---

## 외부 API 연동

관리자 페이지 → **외부 API 관리** 탭에서 API 키를 등록하면 아래 기능이 활성화됩니다.

| 기능 | 설명 |
|------|------|
| 실시간 환율 | 대시보드 환율 위젯 표시 |
| 배송 추적 | TM > 운송 추적 탭에서 운송장 번호로 조회 |
| 통관 조회 | TM > 운송 추적 탭에서 B/L 번호로 조회 |

API 키는 서버 DB에만 저장되며 브라우저에 노출되지 않습니다.

---

## 계정 및 권한

- 회원가입 시 회사 코드로 동일 회사 계정 그룹 생성
- 관리자(`is_admin=True`) 계정만 사용자 권한 및 API 설정 가능
- 모듈별 읽기·쓰기·삭제 권한 개별 설정 가능

---

## 디렉토리 구조

```
scm2_django_v2/          # Django 백엔드
├── config/              # 설정 (settings, urls, asgi)
├── scm_accounts/        # 인증·사용자 관리
├── scm_mm/              # 자재관리
├── scm_sd/              # 판매출하
├── scm_pp/              # 생산계획
├── scm_qm/              # 품질관리
├── scm_wm/              # 창고관리
├── scm_tm/              # 운송관리
├── scm_fi/              # 재무회계
├── scm_hr/              # 인사관리
├── scm_external/        # 외부 API 연동
├── scm_dashboard/       # 대시보드 집계
└── requirements.txt

scm2-frontend/           # React 프론트엔드
├── src/
│   ├── pages/           # 각 모듈 페이지
│   ├── components/      # 공통 컴포넌트 (Layout, Sidebar 등)
│   └── api/             # API 클라이언트
└── package.json
```
