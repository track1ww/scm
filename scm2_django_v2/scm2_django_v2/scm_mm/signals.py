"""
scm_mm/signals.py
=================
MM 모듈 Signal 핸들러 - 입고 확정 시 WM/FI 자동 연계

연계 흐름:
  GoodsReceipt(status='completed') 저장
      ├── [WM] Inventory 재고 수량 증가
      ├── [WM] StockMovement 이력 생성 (movement_type='IN')
      └── [FI] AccountMove 매입 전표 자동 생성
               ├── 차변: 재고자산 14000
               └── 대변: 매입채무 25100
"""

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import GoodsReceipt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------

def _get_or_create_inventory(gr: GoodsReceipt):
    """
    GoodsReceipt 정보를 기반으로 Inventory 레코드를 조회하거나 생성합니다.
    warehouse 필드가 문자열이므로 Warehouse 객체 탐색 후 fallback 처리.
    """
    from scm_wm.models import Inventory, Warehouse

    warehouse_obj = None
    if gr.warehouse:
        warehouse_obj = (
            Warehouse.objects
            .filter(
                company=gr.company,
                warehouse_code=gr.warehouse,
            )
            .first()
            or Warehouse.objects
            .filter(
                company=gr.company,
                warehouse_name=gr.warehouse,
            )
            .first()
        )

    # item_code: GR의 gr_number 기반으로 PO 연결 자재코드 우선 사용,
    # 없으면 item_name 을 code 로 활용 (데이터 정합성 허용)
    item_code = gr.item_name  # 현재 모델에 material_code 직접 FK 없음
    if gr.po and gr.po.item_name:
        item_code = gr.po.item_name

    inventory, created = Inventory.objects.select_for_update().get_or_create(
        company=gr.company,
        item_code=item_code,
        warehouse=warehouse_obj,
        lot_number='',
        defaults={
            'item_name': gr.item_name,
            'stock_qty': 0,
            'system_qty': 0,
            'unit_price': gr.po.unit_price if gr.po else Decimal('0'),
        },
    )
    return inventory, warehouse_obj, item_code


def _get_or_create_account(company, code: str, name: str, account_type: str):
    """계정과목을 조회하거나 자동 생성합니다."""
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

@receiver(post_save, sender=GoodsReceipt)
def on_goods_receipt_completed(
    sender,
    instance: GoodsReceipt,
    created: bool,
    **kwargs,
) -> None:
    """
    GoodsReceipt status='completed' 저장 시
    WM 재고 증가 + StockMovement 이력 + FI 매입 전표를 하나의 트랜잭션으로 처리.

    무한 루프 방지: update_fields 가 ['status'] 외의 필드를 포함하지 않도록
    하위 처리에서 instance 를 직접 수정하지 않습니다.
    """
    # 입고완료 상태가 아니면 스킵
    if instance.status != 'completed':
        return

    # update_fields 가 지정됐을 때 status 가 포함된 경우만 처리
    # (이미 처리된 레코드의 다른 필드 업데이트 시 중복 실행 방지)
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'status' not in update_fields:
        return

    logger.info(
        "[MM-Signal] GoodsReceipt 입고확정 처리 시작: %s (qty=%s)",
        instance.gr_number, instance.received_qty,
    )

    try:
        with transaction.atomic():
            _process_wm_inbound(instance)
            _process_fi_purchase_entry(instance)
    except Exception as exc:
        logger.exception(
            "[MM-Signal] GoodsReceipt %s 연계 처리 실패: %s",
            instance.gr_number, exc,
        )
        raise


def _process_wm_inbound(gr: GoodsReceipt) -> None:
    """WM: Inventory 재고 증가 + StockMovement IN 이력 생성."""
    from scm_wm.models import Inventory, StockMovement

    inventory, warehouse_obj, item_code = _get_or_create_inventory(gr)

    before_qty = Decimal(str(inventory.stock_qty))
    received   = Decimal(str(gr.received_qty))
    after_qty  = before_qty + received

    # select_for_update() 로 잠긴 레코드를 직접 업데이트 (F() 사용 불가 + lock 유지)
    Inventory.objects.filter(pk=inventory.pk).update(
        stock_qty=int(after_qty),
        system_qty=int(after_qty),
    )

    StockMovement.objects.create(
        company=gr.company,
        warehouse=warehouse_obj,
        material_code=item_code,
        material_name=gr.item_name,
        movement_type='IN',
        quantity=received,
        before_qty=before_qty,
        after_qty=after_qty,
        reference_document=gr.gr_number,
        reference_type='PO',
        note=f"발주번호: {gr.po.po_number if gr.po else '-'}",
        created_by=gr.receiver or 'SYSTEM',
    )

    logger.info(
        "[WM] Inventory 증가 완료: %s %s -> %s (warehouse=%s)",
        item_code, before_qty, after_qty, warehouse_obj,
    )


def _process_fi_purchase_entry(gr: GoodsReceipt) -> None:
    """FI: 매입 전표(AccountMove) 자동 생성 - 재고자산 차변 / 매입채무 대변."""
    from scm_fi.models import Account, AccountMove, AccountMoveLine

    # 단가: PO 연결 시 PO 단가 사용, 없으면 0
    unit_price = gr.po.unit_price if gr.po else Decimal('0')
    amount     = Decimal(str(gr.received_qty)) * unit_price

    if amount <= 0:
        logger.warning(
            "[FI] GoodsReceipt %s: 금액이 0 이하(%s)이므로 전표 생성 생략.",
            gr.gr_number, amount,
        )
        return

    # 계정과목 조회/자동 생성
    account_inventory = _get_or_create_account(
        company=gr.company,
        code='14000',
        name='재고자산',
        account_type='ASSET',
    )
    account_payable = _get_or_create_account(
        company=gr.company,
        code='25100',
        name='매입채무',
        account_type='LIABILITY',
    )

    move_number = _generate_move_number('PUR')

    move = AccountMove.objects.create(
        company=gr.company,
        move_number=move_number,
        move_type='PURCHASE',
        posting_date=date.today(),
        ref=gr.gr_number,
        state='POSTED',
        total_debit=amount,
        total_credit=amount,
        created_by='SYSTEM',
    )

    # 차변: 재고자산 증가
    AccountMoveLine.objects.create(
        move=move,
        account=account_inventory,
        name=f"입고 재고자산 인식 - {gr.item_name}",
        debit=amount,
        credit=Decimal('0'),
    )
    # 대변: 매입채무 증가
    AccountMoveLine.objects.create(
        move=move,
        account=account_payable,
        name=f"매입채무 발생 - {gr.gr_number}",
        debit=Decimal('0'),
        credit=amount,
    )

    logger.info(
        "[FI] 매입 전표 생성 완료: %s (금액=%s, GR=%s)",
        move_number, amount, gr.gr_number,
    )
