from django.apps import AppConfig


class WiConfig(AppConfig):
    name = 'scm_wi'

    def ready(self):
        import scm_wi.signals  # noqa: F401 — registers signal receivers
