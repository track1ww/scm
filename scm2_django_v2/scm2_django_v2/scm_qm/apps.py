from django.apps import AppConfig


class QmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'scm_qm'
    verbose_name       = '품질관리(QM)'
