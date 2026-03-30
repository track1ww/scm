"""
scm_sd/signals.py
=================
SD 모듈 Signal 핸들러 - 출하 확정 시 WM/FI 자동 연계

연계 흐름:
  Delivery(status='delivered') 저장
      ├── [WM] Inventory 재고 수량 차감 (부족 시 경고만, 차단 안 함)
      ├── [WM] StockMovement 이력 생성 (movement_type='OUT')
      └── [FI] AccountMove 매출 전표 자동 생성
               ├── 차변: 매출채권 11000
               └── 대변: 매출 41000
"""

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Delivery

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------

def _get_inventory_for_delivery(delivery: Delivery):
    """
    Delivery 의 item_name 을 기반으로 Inventory 를 탐색합니다.
    SalesOrder 의 company 와 item_name 으로 일치하는 재고를 반환.
    창고가 복수인 경우 stock_qty 합산이 아닌 최초 매칭 창고 기준으로 처리.
    """
    from scm_wm.models import Inventory

    company = delivery.company
    item_key = delivery.item_name
    if delivery.order:
        item_key = delivery.order.item_name

    inventories = (
        Inventory.objects
        .select_for_update()
        .filter(company=company, item_code=item_key)
        .order_by('-stock_qty')
    )
    return inventories, item_key


def _get_or_create_account(company, code: str, name: str, account_type: str):
    """계정과목 조회 또는 자동 생성."""
    from scm_fi.models import Account

    account, created = Account.objects.get_or_create(
        company=company,
        code=code,
        defaults={
            'name':         name,
            'account_type': account_type,
            'root_type':    account_type,
            'is_group':     False,
            'is_active':    True,
        },
    )
    if created:
        logger.info(
            "[FI] 계정과목 자동 생성: %s %s (company=%s)",
            code, name, company,
        )
    return account


def _generate_move_number(prefix: str) -> str:
    """전표번호 자동 채번 (PREFIX-YYYYMMDD-NNNN)."""
    from scm_fi.models import AccountMove

    today_str = date.today().strftime('%Y%m%d')
    base      = f"{prefix}-{today_str}-"
    last = (
        AccountMove.objects
        .filter(move_number__startswith=base)
        .order_by('-move_number')
        .values_list('move_number', flat=True)
        .first()
    )
    if last:
        try:
            seq = int(last.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{base}{seq:04d}"


# ---------------------------------------------------------------------------
# Signal 핸들러
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Delivery)
def on_delivery_completed(
    sender,
    instance: Delivery,
    created: bool,
    **kwargs,
) -> None:
    """
    Delivery status='delivered' 저장 시
    WM 재고 차감 + StockMovement 이력 + FI 매출 전표를 하나의 트랜잭션으로 처리.

    재고 부족 시 경고 로그를 남기고 처리를 계속 진행합니다 (차단 없음).
    """
    if instance.status != 'delivered':
        return

    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'status' not in update_fields:
        return

    logger.info(
        "[SD-Signal] Delivery 출하확정 처리 시작: %s (qty=%s)",
        instance.delivery_number, instance.delivery_qty,
    )

    try:
        with transaction.atomic():
            _process_wm_outbound(instance)
            _process_fi_sale_entry(instance)
    except Exception as exc:
        logger.exception(
            "[SD-Signal] Delivery %s 연계 처리 실패: %s",
            instance.delivery_number, exc,
        )
        raise


def _process_wm_outbound(delivery: Delivery) -> None:
    """WM: Inventory 재고 차감 + StockMovement OUT 이력 생성."""
    from scm_wm.models import Inventory, StockMovement

    inventories, item_code = _get_inventory_for_delivery(delivery)
    delivery_qty = Decimal(str(delivery.delivery_qty))

    # 가용 재고 체크
    total_stock = sum(
        Decimal(str(inv.stock_qty)) for inv in inventories
    )
    if total_stock < delivery_qty:
        logger.warning(
            "[WM] 재고 부족 경고: %s 요청=%s, 보유=%s (delivery=%s). "
            "재고 부족 상태로 출고 처리 계속 진행.",
            item_code, delivery_qty, total_stock, delivery.delivery_number,
        )

    # 재고를 보유량이 많은 창고부터 차감 (FEFO/FIFO 없이 단순 처리)
    remaining  = delivery_qty
    first_inv  = None
    warehouse_obj = None

    for inv in inventories:
        if remaining <= 0:
            break

        inv_qty    = Decimal(str(inv.stock_qty))
        deduct     = min(inv_qty, remaining)
        before_qty = inv_qty
        after_qty  = max(inv_qty - deduct, Decimal('0'))

        Inventory.objects.filter(pk=inv.pk).update(
            stock_qty=int(after_qty),
            system_qty=int(after_qty),
        )

        if first_inv is None:
            first_inv     = inv
            warehouse_obj = inv.warehouse

        StockMovement.objects.create(
            company=delivery.company,
            warehouse=inv.warehouse,
            material_code=item_code,
            material_name=delivery.item_name,
            movement_type='OUT',
            quantity=deduct,
            before_qty=before_qty,
            after_qty=after_qty,
            reference_document=delivery.delivery_number,
            reference_type='SO',
            note=(
                f"판매주문: {delivery.order.order_number if delivery.order else '-'}"
            ),
            created_by='SYSTEM',
        )

        remaining -= deduct
        logger.info(
            "[WM] 재고 차감: %s %s -> %s (warehouse=%s)",
            item_code, before_qty, after_qty, inv.warehouse,
        )

    # 재고가 없어서 차감을 전혀 못한 경우: 음수 재고 방지용 더미 이력 생성
    if first_inv is None:
        StockMovement.objects.create(
            company=delivery.company,
            warehouse=None,
            material_code=item_code,
            material_name=delivery.item_name,
            movement_type='OUT',
            quantity=delivery_qty,
            before_qty=Decimal('0'),
            after_qty=Decimal('0'),
            reference_document=delivery.delivery_number,
            reference_type='SO',
            note=(
                f"재고 없음 - 판매주문: "
                f"{delivery.order.order_number if delivery.order else '-'}"
            ),
            created_by='SYSTEM',
        )
        logger.warning(
            "[WM] 재고 없음으로 이력만 생성 (qty=0): %s",
            delivery.delivery_number,
        )


def _process_fi_sale_entry(delivery: Delivery) -> None:
    """FI: 매출 전표(AccountMove) 자동 생성 - 매출채권 차변 / 매출 대변."""
    from scm_fi.models import AccountMove, AccountMoveLine

    # 금액 계산: SalesOrder 단가 * 출하수량 * (1 - 할인율)
    order      = delivery.order
    unit_price = Decimal('0')
    discount   = Decimal('0')
    if order:
        unit_price = order.unit_price
        discount   = order.discount_rate

    delivery_qty = Decimal(str(delivery.delivery_qty))
    amount       = delivery_qty * unit_price * (1 - discount / 100)

    if amount <= 0:
        logger.warning(
            "[FI] Delivery %s: 금액이 0 이하(%s)이므로 전표 생성 생략.",
            delivery.delivery_number, amount,
        )
        return

    # 계정과목 조회/자동 생성
    account_receivable = _get_or_create_account(
        company=delivery.company,
        code='11000',
        name='매출채권',
        account_type='ASSET',
    )
    account_revenue = _get_or_create_account(
        company=delivery.company,
        code='41000',
        name='매출',
        account_type='REVENUE',
    )

    move_number = _generate_move_number('SAL')

    move = AccountMove.objects.create(
        company=delivery.company,
        move_number=move_number,
        move_type='SALE',
        posting_date=date.today(),
        ref=delivery.delivery_number,
        state='POSTED',
        total_debit=amount,
        total_credit=amount,
        created_by='SYSTEM',
    )

    # 차변: 매출채권 증가
    AccountMoveLine.objects.create(
        move=move,
        account=account_receivable,
        name=f"매출채권 발생 - {delivery.delivery_number}",
        debit=amount,
        credit=Decimal('0'),
        due_date=(
            delivery.delivery_date
            if delivery.delivery_date
            else date.today()
        ),
    )
    # 대변: 매출 인식
    AccountMoveLine.objects.create(
        move=move,
        account=account_revenue,
        name=f"매출 인식 - {delivery.item_name}",
        debit=Decimal('0'),
        credit=amount,
    )

    logger.info(
        "[FI] 매출 전표 생성 완료: %s (금액=%s, Delivery=%s)",
        move_number, amount, delivery.delivery_number,
    )
