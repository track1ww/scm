"""
scm_core.utils — 공통 유틸리티

다른 앱에서 감사 로그를 기록할 때 사용합니다.

사용 예시:
    from scm_core.utils import log_audit

    log_audit(
        request=request,
        action='CREATE',
        module='mm',
        model_name='PurchaseOrder',
        object_id=po.pk,
        object_repr=str(po),
        changes={'items': after_data},
    )
"""
import logging

logger = logging.getLogger('scm_core.audit')


def get_client_ip(request):
    """요청에서 실제 클라이언트 IP를 추출합니다."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit(
    request,
    action: str,
    module: str,
    model_name: str,
    object_id: int,
    object_repr: str = '',
    changes: dict = None,
    company=None,
):
    """
    감사 로그를 비동기 없이 즉시 기록합니다.

    :param request:     Django HttpRequest (user, IP 추출)
    :param action:      'CREATE' | 'UPDATE' | 'DELETE'
    :param module:      앱 모듈명 ('mm', 'sd', 'hr', ...)
    :param model_name:  모델 클래스명 ('PurchaseOrder', ...)
    :param object_id:   대상 레코드 PK
    :param object_repr: str(instance) 결과 (선택)
    :param changes:     변경 내역 dict (선택)
    :param company:     Company 인스턴스 (없으면 request.user.company 사용)
    """
    # 순환 임포트 방지를 위해 함수 내부에서 임포트
    from .models import AuditLog

    user = getattr(request, 'user', None)
    if user and not user.is_authenticated:
        user = None

    resolved_company = company
    if resolved_company is None and user and hasattr(user, 'company'):
        resolved_company = user.company

    if resolved_company is None:
        logger.warning(
            'log_audit: company 를 확인할 수 없어 감사 로그를 건너뜁니다. '
            'module=%s model=%s object_id=%s', module, model_name, object_id
        )
        return None

    try:
        log_entry = AuditLog.objects.create(
            company=resolved_company,
            user=user,
            action=action,
            module=module,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr[:200] if object_repr else '',
            changes=changes or {},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        return log_entry
    except Exception as exc:
        logger.error(
            'log_audit: 감사 로그 기록 실패. module=%s model=%s object_id=%s error=%s',
            module, model_name, object_id, exc
        )
        return None
