"""
Cross-module signal: WI(작업지시) 완료 → PP(생산오더) produced_qty 자동 누계.

Signal overview
---------------
wi_completion_to_pp : WorkInstruction '완료' 전환 시
    1. 동일 company + work_center 인 진행 중인 ProductionOrder 조회
    2. ProductionOrder.produced_qty += WorkInstruction.actual_qty
    3. produced_qty >= planned_qty 이면 ProductionOrder.status → '완료' 자동전환
    4. PP 자동완료 시 해당 company 의 모든 사용자에게 시스템 알림 생성
"""
import logging

from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='scm_wi.WorkInstruction')
def wi_completion_to_pp(sender, instance, **kwargs):
    """
    WorkInstruction → '완료' 전환 시 PP produced_qty 자동 누계.

    - 신규 레코드(pk 없음)는 무시.
    - 이미 '완료' 였거나, 새 상태가 '완료'가 아니면 무시 (멱등성 보장).
    - work_center 와 company 로 관련 ProductionOrder 를 식별한다.
      (WI 모델에 PP FK 가 없으므로 work_center 매칭으로 연결)
    - actual_qty 가 0 이하이면 재고 누계 불필요 → 조기 반환.
    """
    if not instance.pk:
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # 상태 전환 감지: 이전이 '완료'이거나, 새 상태가 '완료'가 아니면 처리 불필요
    if old.status == '완료' or instance.status != '완료':
        return

    qty_to_add = instance.actual_qty or 0
    if qty_to_add <= 0:
        logger.debug(
            'wi_completion_to_pp: WI %s completed with actual_qty=%s — skipping PP update.',
            instance.wi_number, qty_to_add,
        )
        return

    if not instance.work_center:
        logger.debug(
            'wi_completion_to_pp: WI %s has no work_center — cannot resolve PP.',
            instance.wi_number,
        )
        return

    _update_production_order(instance, qty_to_add)


def _update_production_order(wi_instance, qty_to_add: int) -> None:
    """
    ProductionOrder 를 work_center + company 로 찾아 produced_qty 를 누계한다.

    select_for_update() 로 동시성 경쟁 조건(race condition)을 방지한다.
    PP 자동완료 발생 시 알림을 생성한다.
    """
    from scm_pp.models import ProductionOrder

    # 같은 작업장의 '계획' / '확정' / '생산중' 오더를 대상으로 한다.
    # 완료·취소된 오더는 누계에서 제외.
    active_statuses = ('계획', '확정', '생산중')

    try:
        with transaction.atomic():
            orders = (
                ProductionOrder.objects
                .select_for_update()
                .filter(
                    company=wi_instance.company,
                    work_center=wi_instance.work_center,
                    status__in=active_statuses,
                )
                .order_by('planned_end', 'pk')  # 가장 오래된/마감 임박 오더 우선
            )

            if not orders.exists():
                logger.debug(
                    'wi_completion_to_pp: no active ProductionOrder found for '
                    'company=%s work_center=%s',
                    wi_instance.company_id, wi_instance.work_center,
                )
                return

            # 첫 번째 대상 오더에 전량 누계 (단일 작업지시 → 단일 오더 매핑 기준)
            pp_order = orders.first()
            prev_produced = pp_order.produced_qty or 0
            pp_order.produced_qty = prev_produced + qty_to_add

            pp_auto_completed = False
            if (
                pp_order.status != '완료'
                and pp_order.planned_qty > 0
                and pp_order.produced_qty >= pp_order.planned_qty
            ):
                pp_order.status = '완료'
                pp_auto_completed = True
                logger.info(
                    'wi_completion_to_pp: ProductionOrder %s auto-completed '
                    '(produced_qty=%s >= planned_qty=%s) triggered by WI %s.',
                    pp_order.order_number,
                    pp_order.produced_qty,
                    pp_order.planned_qty,
                    wi_instance.wi_number,
                )

            pp_order.save(update_fields=['produced_qty', 'status'])

            if pp_auto_completed:
                _notify_pp_auto_completed(wi_instance, pp_order)

    except Exception:
        logger.exception(
            'wi_completion_to_pp: unexpected error while updating ProductionOrder '
            'for WI %s (company=%s, work_center=%s).',
            wi_instance.wi_number,
            wi_instance.company_id,
            wi_instance.work_center,
        )


def _notify_pp_auto_completed(wi_instance, pp_order) -> None:
    """
    PP 오더 자동완료 시 해당 company 의 모든 활성 사용자에게 시스템 알림을 생성한다.
    WebSocket push 는 best-effort 로 시도한다.
    """
    try:
        from django.contrib.auth import get_user_model
        from scm_notifications.models import Notification
        from scm_notifications.push import push_notification
        from django.utils import timezone

        User = get_user_model()

        title = f'생산오더 자동완료: {pp_order.order_number}'
        message = (
            f'작업지시 {wi_instance.wi_number} 완료로 인해 '
            f'생산오더 {pp_order.order_number} ({pp_order.product_name})이 '
            f'자동 완료 처리되었습니다. '
            f'생산수량: {pp_order.produced_qty} / {pp_order.planned_qty}'
        )

        recipients = User.objects.filter(
            company=wi_instance.company,
            is_active=True,
        ).values_list('pk', flat=True)

        notifications = [
            Notification(
                company=wi_instance.company,
                recipient_id=user_pk,
                notification_type='system',
                title=title,
                message=message,
                ref_module='scm_pp',
                ref_id=pp_order.pk,
            )
            for user_pk in recipients
        ]
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)

        now_iso = timezone.now().isoformat()
        for notif in notifications:
            push_notification(
                user_id=notif.recipient_id,
                notification_data={
                    'id': None,  # bulk_create may not return PKs on all backends
                    'message': message,
                    'notification_type': 'system',
                    'is_read': False,
                    'created_at': now_iso,
                },
            )

    except Exception:
        logger.exception(
            '_notify_pp_auto_completed: failed to create notifications for '
            'ProductionOrder %s.',
            pp_order.order_number,
        )
