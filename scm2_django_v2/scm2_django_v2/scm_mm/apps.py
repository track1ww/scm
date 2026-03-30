from django.apps import AppConfig


class MmConfig(AppConfig):
    name = 'scm_mm'

    def ready(self):
        import scm_mm.signals  # noqa: F401  Signal 핸들러 등록
