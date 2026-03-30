from django.apps import AppConfig


class WmConfig(AppConfig):
    name = 'scm_wm'

    def ready(self):
        import scm_wm.signals  # noqa: F401 — registers all cross-module signal handlers
