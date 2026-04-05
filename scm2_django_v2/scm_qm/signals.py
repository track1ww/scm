"""
QM cross-module signal.

Signal overview
---------------
qm_fail_to_pp_rework : InspectionResult '불합격' 전환 시
                         → PP ProductionOrder 재작업 오더 자동생성
                         → 회사 사용자 전체에 인앱 알림 + WebSocket push
"""
import logging

from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='scm_qm.InspectionResult')
def qm_fail_to_pp_rework(sender, instance, **kwargs):
    """
    InspectionResult → '불합격' 전환 감지.

    신규 레코드(pk 없음)이거나 이전 result 가 이미 '불합격'이었으면 무시.
    전환이 확인되면 transaction.atomic() 내에서:
      1. PP ProductionOrder 재작업 오더 생성 (중복 방지 포함)
      2. Notification DB 레코드 생성 + WebSocket push
    """
    # 신규 레코드 → 비교 대상 없음
    if not instance.pk:
        return

    # 저장 후 상태가 '불합격'이 아니면 무관
    if instance.result != '불합격':
        return

    # 이전 상태 조회
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # 이미 불합격이었으면 재처리 불필요
    if old.result == '불합격':
        return

    # ── 이 시점: 불합격으로 전환되는 순간 ────────────────────────────────
    _create_rework_order_and_notify(instance)


def _create_rework_order_and_notify(inspection_result):
    """재작업 오더 생성 + 알림 발송 (오류 발생 시 로그만 남기고 저장 흐름 유지)."""
    try:
        with transaction.atomic():
            order_number = _create_rework_order(inspection_result)
            _notify_company_users(inspection_result, order_number)
    except Exception as exc:
        logger.error(
            'QM→PP 재작업 오더 자동생성 실패 | result_number=%s | error=%s',
            inspection_result.result_number,
            exc,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# PP 재작업 오더 생성
# ---------------------------------------------------------------------------

def _create_rework_order(inspection_result):
    """
    PP ProductionOrder 재작업 오더를 생성하고 order_number 를 반환.
    이미 동일 order_number 가 존재하면 생성을 건너뛰고 기존 번호를 반환.
    """
    from scm_pp.models import ProductionOrder

    order_number = f'RW-{inspection_result.result_number}'

    # 중복 방지
    if ProductionOrder.objects.filter(order_number=order_number).exists():
        logger.info(
            'QM→PP 재작업 오더 이미 존재, 건너뜀 | order_number=%s', order_number
        )
        return order_number

    planned_qty = (
        inspection_result.failed_qty
        if inspection_result.failed_qty
        else inspection_result.inspected_qty
    )

    ProductionOrder.objects.create(
        company=inspection_result.company,
        order_number=order_number,
        product_name=f'[재작업] {inspection_result.item_name}',
        planned_qty=planned_qty,
        status='계획',
        note=(
            f'QM 불합격으로 자동생성. '
            f'검사번호: {inspection_result.result_number}'
        ),
    )

    logger.info(
        'QM→PP 재작업 오더 생성 완료 | order_number=%s | planned_qty=%s',
        order_number,
        planned_qty,
    )
    return order_number


# ---------------------------------------------------------------------------
# 알림 발송
# ---------------------------------------------------------------------------

def _notify_company_users(inspection_result, order_number):
    """
    해당 회사의 모든 활성 사용자에게 DB 알림 레코드를 생성하고
    WebSocket push_notification 을 전송한다.
    """
    from scm_accounts.models import User
    from scm_notifications.models import Notification
    from scm_notifications.push import push_notification

    company = inspection_result.company
    if not company:
        return

    failed_qty = (
        inspection_result.failed_qty
        if inspection_result.failed_qty
        else inspection_result.inspected_qty
    )
    item_name = inspection_result.item_name

    title = '불합격 검사 - 재작업 오더 생성'
    message = (
        f'{item_name} 불합격 ({failed_qty}개). '
        f'재작업 오더 {order_number} 자동생성.'
    )

    recipients = User.objects.filter(company=company, is_active=True)

    notifications = [
        Notification(
            company=company,
            recipient=user,
            notification_type='inspection_result',
            title=title,
            message=message,
            ref_module='scm_qm',
            ref_id=inspection_result.pk,
        )
        for user in recipients
    ]

    created = Notification.objects.bulk_create(notifications)

    # WebSocket push (best-effort; push_notification 내부에서 예외 억제됨)
    for notif in created:
        push_notification(
            user_id=notif.recipient_id,
            notification_data={
                'id': notif.pk,
                'title': notif.title,
                'message': notif.message,
                'notification_type': notif.notification_type,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat() if notif.created_at else None,
            },
        )

    logger.info(
        'QM 불합격 알림 발송 완료 | result_number=%s | recipients=%d',
        inspection_result.result_number,
        len(created),
    )
