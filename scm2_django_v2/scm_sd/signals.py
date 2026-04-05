"""
scm_sd/signals.py
=================
SD 수주(SalesOrder) 접수 → WM 재고 확인 → 부족 시 PP 생산오더 자동제안 (MTO)

Signal overview
---------------
sd_sales_order_mto_check : SalesOrder 신규 생성(created=True) & status='주문접수' 시
    1. WM Inventory 재고 조회 (item_name iexact 또는 material_code 매칭)
    2. 가용재고 < 주문수량 → PP ProductionOrder 자동 생성 (MTO)
    3. 해당 company 의 모든 활성 사용자에게 'low_stock' 알림 생성 + WebSocket push
    4. 재고 충분 시 DEBUG 로그만 남기고 종료 (아무 작업 없음)

MTO 생산오더 번호 패턴
  order_number = 'MTO-{sales_order.order_number}'

중복 방지
  생성 전 .exists() 체크 → 동일 order_number 의 PP 오더가 이미 있으면 skip
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------

@receiver(post_save, sender='scm_sd.SalesOrder')
def sd_sales_order_mto_check(sender, instance, created, **kwargs):
    """
    SalesOrder 신규 생성 & status='주문접수' 일 때 WM 재고를 확인하고
    재고 부족 시 PP MTO 생산오더를 자동 제안한다.

    - created=False (수정) 는 완전히 무시한다.
    - status 가 '주문접수' 가 아니면 무시한다.
    - 예외 발생 시 로그를 남기되 수주 저장 자체를 방해하지 않는다.
    """
    if not created:
        return

    if instance.status != '주문접수':
        logger.debug(
            'sd_sales_order_mto_check: SalesOrder %s status=%s — skipping MTO check.',
            instance.order_number, instance.status,
        )
        return

    try:
        with transaction.atomic():
            _check_stock_and_create_mto(instance)
    except Exception:
        logger.exception(
            'sd_sales_order_mto_check: unexpected error for SalesOrder %s.',
            instance.order_number,
        )


# ---------------------------------------------------------------------------
# Core business logic
# ---------------------------------------------------------------------------

def _check_stock_and_create_mto(sales_order) -> None:
    """
    WM 재고를 확인하고 부족 시 PP MTO 생산오더를 생성한다.

    재고 조회 우선순위:
      1. item_name iexact 매칭 (item_code 도 item_name 과 동일할 수 있음)
      2. item_code 필드가 item_name 과 동일한 경우도 포함 (WM _resolve_material 과 일치)
      → 같은 company 내에서 stock_qty 합산
    """
    from scm_wm.models import Inventory

    company    = sales_order.company
    item_name  = sales_order.item_name
    order_qty  = sales_order.quantity

    # 자재 코드 해석 (scm_wm.signals._resolve_material 과 동일 로직)
    material_code = _resolve_material_code(company, item_name)

    # WM 재고 조회: item_name iexact OR item_code 매칭
    from django.db.models import Q

    inv_qs = Inventory.objects.filter(company=company).filter(
        # item_name iexact 를 우선으로 하되 item_code 매칭도 포함
        # (WM _resolve_material 과 동일 패턴: item_code 는 material_code 또는 item_name 자체)
        Q(item_name__iexact=item_name)
        | Q(item_code=material_code)
    )

    available_qty = sum(inv.stock_qty for inv in inv_qs) if inv_qs.exists() else 0

    if available_qty >= order_qty:
        logger.debug(
            'sd_sales_order_mto_check: SalesOrder %s — sufficient stock '
            '(%s >= %s) for %s. No MTO action needed.',
            sales_order.order_number, available_qty, order_qty, item_name,
        )
        return

    # 재고 부족 → MTO 생산오더 자동 생성
    logger.info(
        'sd_sales_order_mto_check: SalesOrder %s — stock shortage '
        '(%s < %s) for %s. Initiating MTO.',
        sales_order.order_number, available_qty, order_qty, item_name,
    )
    pp_order = _create_mto_production_order(sales_order, available_qty)
    if pp_order is not None:
        _notify_mto_created(sales_order, pp_order, available_qty)


def _resolve_material_code(company, item_name: str) -> str:
    """
    item_name → material_code.
    scm_mm.Material 에서 조회하고 없으면 item_name 자체를 코드로 사용.
    scm_wm.signals._resolve_material 과 동일한 패턴.
    """
    if not item_name:
        return 'UNKNOWN'
    normalized = item_name.strip()
    try:
        from scm_mm.models import Material
        mat = Material.objects.filter(
            company=company,
            material_name__iexact=normalized,
        ).first()
        if mat:
            return mat.material_code
    except Exception:
        pass
    return normalized


def _create_mto_production_order(sales_order, available_qty: int):
    """
    PP ProductionOrder 를 MTO 방식으로 자동 생성한다.

    - order_number 중복이 있으면 생성을 skip 하고 None 을 반환한다.
    - planned_qty = order.quantity - max(available_qty, 0)  (부족분만 생산)
    """
    from scm_pp.models import ProductionOrder

    mto_order_number = f'MTO-{sales_order.order_number}'
    shortage_qty     = sales_order.quantity - max(available_qty, 0)

    # 중복 방지
    if ProductionOrder.objects.filter(order_number=mto_order_number).exists():
        logger.warning(
            '_create_mto_production_order: ProductionOrder %s already exists — skipping.',
            mto_order_number,
        )
        return None

    note_text = (
        f'수주 {sales_order.order_number} MTO 자동생성. '
        f'재고부족: {available_qty}/{sales_order.quantity}'
    )

    pp_order = ProductionOrder.objects.create(
        company=sales_order.company,
        order_number=mto_order_number,
        product_name=sales_order.item_name,
        planned_qty=shortage_qty,
        status='계획',
        note=note_text,
    )

    logger.info(
        '_create_mto_production_order: Created MTO ProductionOrder %s '
        '(planned_qty=%s) for SalesOrder %s.',
        pp_order.order_number, pp_order.planned_qty, sales_order.order_number,
    )
    return pp_order


# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------

def _notify_mto_created(sales_order, pp_order, available_qty: int) -> None:
    """
    MTO 생산오더 자동생성 알림을 해당 company 의 모든 활성 사용자에게 전송한다.

    - Notification 레코드 bulk_create (ignore_conflicts=True)
    - WebSocket push (best-effort, 실패해도 예외 전파 없음)
    """
    try:
        from django.contrib.auth import get_user_model
        from scm_notifications.models import Notification
        from scm_notifications.push import push_notification
        from scm_notifications.serializers import NotificationSerializer

        User = get_user_model()

        title   = 'MTO 생산오더 자동생성'
        message = (
            f'{sales_order.item_name} 재고 부족 '
            f'({available_qty}/{sales_order.quantity}). '
            f'생산오더 {pp_order.order_number} 자동생성.'
        )

        recipient_pks = list(
            User.objects.filter(
                company=sales_order.company,
                is_active=True,
            ).values_list('pk', flat=True)
        )

        if not recipient_pks:
            logger.debug(
                '_notify_mto_created: no active users for company=%s — skipping push.',
                sales_order.company_id,
            )
            return

        notifications = [
            Notification(
                company=sales_order.company,
                recipient_id=user_pk,
                notification_type='low_stock',
                title=title,
                message=message,
                ref_module='scm_pp',
                ref_id=pp_order.pk,
            )
            for user_pk in recipient_pks
        ]
        created_notifications = Notification.objects.bulk_create(
            notifications, ignore_conflicts=True
        )

        now_iso = timezone.now().isoformat()
        notification_data = {
            'id': None,  # bulk_create may not populate PKs on all DB backends
            'title': title,
            'message': message,
            'notification_type': 'low_stock',
            'is_read': False,
            'created_at': now_iso,
        }
        for user_pk in recipient_pks:
            push_notification(user_id=user_pk, notification_data=notification_data)

        logger.info(
            '_notify_mto_created: Sent MTO notifications to %s user(s) '
            'for SalesOrder %s → ProductionOrder %s.',
            len(recipient_pks), sales_order.order_number, pp_order.order_number,
        )

    except Exception:
        logger.exception(
            '_notify_mto_created: failed to send notifications for '
            'ProductionOrder %s.',
            pp_order.order_number,
        )
