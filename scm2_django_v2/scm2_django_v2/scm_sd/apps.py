from django.apps import AppConfig


class SdConfig(AppConfig):
    name = 'scm_sd'

    def ready(self):
        import scm_sd.signals  # noqa: F401  Signal 핸들러 등록
