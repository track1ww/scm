from django.apps import AppConfig


class QmConfig(AppConfig):
    name = 'scm_qm'

    def ready(self):
        import scm_qm.signals  # noqa: F401
