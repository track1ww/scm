from django.apps import AppConfig


class TmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'scm_tm'
    verbose_name       = '운송관리(TM)'
