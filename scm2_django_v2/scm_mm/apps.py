from django.apps import AppConfig


class MmConfig(AppConfig):
    name = 'scm_mm'
    verbose_name = 'MM (자재관리)'

    def ready(self):
        # Signal handlers can be imported here in the future.
        pass
