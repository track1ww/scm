from django.apps import AppConfig


class HrConfig(AppConfig):
    name = 'scm_hr'

    def ready(self):
        import scm_hr.signals  # noqa: F401
