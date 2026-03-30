from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    name = 'scm_workflow'
    verbose_name = '승인 워크플로우'

    def ready(self):
        import scm_workflow.signals  # noqa: F401
