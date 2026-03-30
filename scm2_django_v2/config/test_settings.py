"""테스트 전용 설정 — SQLite 인메모리 DB 사용으로 PostgreSQL 의존성 제거."""

from .settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Channels: 테스트 시 InMemoryChannelLayer 강제 사용
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# 테스트 속도 향상 — 해시 라운드 최소화
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Celery: 테스트에서 즉시 실행
CELERY_TASK_ALWAYS_EAGER = True
