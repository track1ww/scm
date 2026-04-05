from rest_framework.exceptions import PermissionDenied
from .utils import log_audit


class AuditLogMixin:
    """
    ViewSet에 믹스인하면 CREATE/UPDATE/DELETE 성공 시 AuditLog를 자동 기록합니다.
    perform_create 오버라이드를 건드리지 않고 상위 create/update/destroy 에서 후킹합니다.

    서브클래스에서 audit_module 을 지정하세요 (기본값: 앱 레이블에서 자동 추출).
    예) audit_module = 'mm'
    """
    audit_module: str = ''

    def _audit_module(self):
        if self.audit_module:
            return self.audit_module
        try:
            return self.queryset.model._meta.app_label.replace('scm_', '')
        except Exception:
            return 'unknown'

    def _model_name(self):
        try:
            qs = self.queryset if getattr(self, 'queryset', None) is not None else self.get_queryset()
            return qs.model.__name__
        except Exception:
            return ''

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        obj_id = (response.data or {}).get('id')
        if obj_id:
            log_audit(
                request=request,
                action='CREATE',
                module=self._audit_module(),
                model_name=self._model_name(),
                object_id=obj_id,
                changes={k: v for k, v in (response.data or {}).items()
                         if k not in ('id', 'created_at', 'updated_at')},
            )
        return response

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().update(request, *args, **kwargs)
        log_audit(
            request=request,
            action='UPDATE',
            module=self._audit_module(),
            model_name=self._model_name(),
            object_id=instance.pk,
            object_repr=str(instance),
            changes=request.data if hasattr(request, 'data') else {},
        )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        obj_id, obj_repr = instance.pk, str(instance)
        response = super().destroy(request, *args, **kwargs)
        log_audit(
            request=request,
            action='DELETE',
            module=self._audit_module(),
            model_name=self._model_name(),
            object_id=obj_id,
            object_repr=obj_repr,
        )
        return response


class StateLockMixin:
    """
    Prevent update/destroy on records in a locked state.

    Subclasses must define:
        locked_states: list[str]  — field values that lock the record
        state_field: str          — model field name (default 'status')
    """
    locked_states: list = []
    state_field: str = 'status'

    def _check_state_lock(self, instance):
        val = getattr(instance, self.state_field, None)
        if val in self.locked_states:
            raise PermissionDenied(
                f"이 레코드는 '{val}' 상태이므로 수정/삭제할 수 없습니다."
            )

    def update(self, request, *args, **kwargs):
        self._check_state_lock(self.get_object())
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._check_state_lock(self.get_object())
        return super().destroy(request, *args, **kwargs)
