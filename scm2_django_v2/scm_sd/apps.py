from django.apps import AppConfig


class SdConfig(AppConfig):
    name = 'scm_sd'

    def ready(self):
        import scm_sd.signals  # noqa: F401  — registers post_save signal handlers
