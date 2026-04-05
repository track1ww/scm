from django.apps import AppConfig

class ScmExternalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scm_external'
    verbose_name = '외부 API 연동'
