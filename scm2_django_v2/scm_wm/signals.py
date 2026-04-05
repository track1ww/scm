"""
Cross-module inventory signals + FI 자동전기 (Auto Journal Posting).

Signal overview
---------------
mm_receipt_to_wm       : PurchaseOrder '입고완료' → WM IN  + FI 매입전표
sd_delivery_from_wm    : SalesOrder '배송완료'   → FI 매출전표 + COGS  (재고 OUT은 TM 완료 시점으로 이동)
pp_completion_consume  : ProductionOrder '완료'  → BOM OUT + FG IN + FI 생산원가전표
tm_freight_settlement  : TransportOrder '완료'   → WM OUT + FI 운반비전표

TM/SD 타이밍 설계 원칙
----------------------
SD '배송완료' 시점에서는 FI 매출·COGS 전표만 생성한다.
실제 출하(트럭 출발)는 TM이 담당하므로, WM 재고 OUT은
TransportOrder → '완료' 전환 시점에 처리한다.

FI 자동전표 계정과목 (K-GAAP)
-------------------------------
  1400  재고자산     ASSET
  1100  매출채권     ASSET
  2510  매입채무     LIABILITY
  4000  매출        REVENUE
  5000  매출원가     EXPENSE
  5100  생산원가     EXPENSE
  6100  운반비       EXPENSE
  2520  미지급운임   LIABILITY
"""
import logging
import uuid
from decimal import Decimal

from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# K-GAAP 표준 계정과목 매핑
# ---------------------------------------------------------------------------

_ACCOUNTS = {
    'inventory':        ('1400', '재고자산',  'ASSET'),
    'ar':               ('1100', '매출채권',  'ASSET'),
    'ap':               ('2510', '매입채무',  'LIABILITY'),
    'revenue':          ('4000', '매출',      'REVENUE'),
    'cogs':             ('5000', '매출원가',  'EXPENSE'),
    'production_cost':  ('5100', '생산원가',  'EXPENSE'),
    'freight_expense':  ('6100', '운반비',    'EXPENSE'),
    'accrued_freight':  ('2520', '미지급운임', 'LIABILITY'),
}


def _get_or_create_account(company, key):
    """K-GAAP 표준 계정과목을 가져오거나 없으면 자동 생성."""
    from scm_fi.models import Account
    code, name, atype = _ACCOUNTS[key]
    acc, _ = Account.objects.get_or_create(
        company=company, code=code,
        defaults={'name': name, 'account_type': atype, 'is_active': True},
    )
    return acc


# ---------------------------------------------------------------------------
# MM → WM (+ FI 매입전표)
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='scm_mm.PurchaseOrder')
def mm_receipt_to_wm(sender, instance, **kwargs):
    """
    PurchaseOrder → '입고완료' 전환 시:
      1. WM 재고 IN
      2. FI 매입전표: DR 재고자산 / CR 매입채무  (금액 = qty × unit_price)
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.status == '입고완료' or instance.status != '입고완료':
        return

    monetary_amount = float(instance.quantity) * float(instance.unit_price or 0)
    item_code, item_name = _resolve_material(instance.company, instance.item_name)

    _adjust_inventory(
        company=instance.company,
        item_code=item_code,
        item_name=item_name,
        quantity=int(instance.quantity),
        movement_type='IN',
        reference_type='PO',
        reference_document=instance.po_number,
        monetary_amount=monetary_amount,
    )


# ---------------------------------------------------------------------------
# SD → FI 매출전표 + COGS  (재고 OUT은 TM 완료 시 처리)
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='scm_sd.SalesOrder')
def sd_delivery_from_wm(sender, instance, **kwargs):
    """
    SalesOrder → '배송완료' 전환 시:
      FI 매출전표: DR 매출채권 / CR 매출  (금액 = total_amount)
      FI COGS전표: DR 매출원가 / CR 재고자산  (금액 = 재고원가 추정)

    NOTE: WM 재고 OUT은 이 시점에서 처리하지 않는다.
    실제 출하는 TM TransportOrder → '완료' 전환 시 처리된다.
    (TM/SD 타이밍 분리: SD = 수익 인식, TM = 물리적 출하)
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.status == '배송완료' or instance.status != '배송완료':
        return

    # total_amount 는 SalesOrder property (할인율 반영)
    try:
        revenue_amount = float(instance.total_amount)
    except Exception as e:
        logger.warning('sd_delivery_from_wm: total_amount 조회 실패, unit_price 기반으로 폴백: %s', e, exc_info=True)
        revenue_amount = float(instance.quantity) * float(instance.unit_price or 0)

    item_code, item_name = _resolve_material(instance.company, instance.item_name)

    # 재고원가: MaterialPriceHistory 최근 단가 → 없으면 revenue * 0.7 추정
    cost_amount = _estimate_inventory_cost(
        instance.company, item_code, instance.quantity, revenue_amount
    )

    # FI 전표만 생성 — 재고 OUT 없음 (TM 완료 시 처리)
    try:
        _auto_post_fi(
            company=instance.company,
            movement_type='OUT',
            reference_type='SO',
            reference_document=instance.order_number,
            item_name=item_name,
            monetary_amount=revenue_amount,
            cost_amount=cost_amount,
        )
    except Exception as e:
        logger.warning(
            'sd_delivery_from_wm: FI 자동전기 실패 (order=%s): %s',
            instance.order_number, e, exc_info=True,
        )


# ---------------------------------------------------------------------------
# PP → WM (+ FI 생산원가전표)
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='scm_pp.ProductionOrder')
def pp_completion_consume_bom(sender, instance, **kwargs):
    """
    ProductionOrder → '완료' 전환 시:
      1. BOM 구성자재 WM OUT
      2. 완제품 WM IN
      3. 원가 계산: 자재원가 + 공정비(기계+간접) + 인건비 (WorkCenterCost 조회)
      4. FI 생산원가전표: DR 재고자산(완제품) / CR 생산원가
      5. ProductionOrder 원가 필드 업데이트
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.status == '완료' or instance.status != '완료':
        return

    qty_multiplier = instance.planned_qty or 1
    material_cost = Decimal('0')

    # BOM 구성자재 소비
    if instance.bom_id:
        try:
            for line in instance.bom.lines.all():
                scrap_factor = float(line.scrap_rate or 0) / 100
                if scrap_factor >= 1:
                    scrap_factor = 0
                gross_qty = float(line.quantity) * qty_multiplier
                if scrap_factor:
                    gross_qty /= (1 - scrap_factor)

                _adjust_inventory(
                    company=instance.company,
                    item_code=line.material_code,
                    item_name=line.material_name,
                    quantity=gross_qty,
                    movement_type='OUT',
                    reference_type='PP',
                    reference_document=instance.order_number,
                )

                unit_cost = _get_material_unit_cost(instance.company, line.material_code)
                material_cost += unit_cost * Decimal(str(gross_qty))
        except Exception as e:
            logger.warning(
                'pp_completion_consume_bom: BOM 자재 소비 처리 실패 (order=%s): %s',
                instance.order_number, e, exc_info=True,
            )

    # 공정비 + 인건비: WorkCenterCost × actual_hours (없으면 planned_hours)
    process_cost = Decimal('0')
    labor_cost   = Decimal('0')
    if instance.work_center:
        wcc = _get_work_center_cost(instance.company, instance.work_center)
        if wcc:
            hours = Decimal(str(instance.actual_hours or instance.planned_hours or 0))
            process_cost = (wcc.machine_rate + wcc.overhead_rate) * hours
            labor_cost   = wcc.labor_rate * hours

    total_cost = material_cost + process_cost + labor_cost

    # ProductionOrder 원가 필드 업데이트 (pre_save 내이므로 update_fields 로 별도 저장 불필요)
    instance.material_cost = material_cost
    instance.process_cost  = process_cost
    instance.labor_cost    = labor_cost
    instance.total_cost    = total_cost

    # 완제품 입고 + FI 전표
    fg_code, fg_name = _resolve_material(instance.company, instance.product_name)
    _adjust_inventory(
        company=instance.company,
        item_code=fg_code,
        item_name=fg_name,
        quantity=int(qty_multiplier),
        movement_type='IN',
        reference_type='PP',
        reference_document=instance.order_number,
        monetary_amount=float(total_cost),
        is_production=True,
    )


# ---------------------------------------------------------------------------
# TM → WM OUT + FI (운임 자동정산 + 재고 출하)
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='scm_tm.TransportOrder')
def tm_freight_settlement(sender, instance, **kwargs):
    """
    TransportOrder → '완료' 전환 시:
      1. WM 재고 OUT — 운송 화물에 해당하는 재고 출하 처리
         TransportOrder.item_description 을 기준으로 자재 식별.
         NOTE: TransportOrder에 SalesOrder FK가 없으므로 item_description으로
               최선의 매칭을 수행한다. 향후 TransportOrder에 sales_order FK 추가 시
               직접 참조로 교체 권장.
      2. FreightRate 조회 → freight_cost 자동 계산
         계산식: max(min_charge, weight_kg × rate_per_kg + volume_cbm × rate_per_cbm)
      3. FI 운반비전표: DR 운반비(6100) / CR 미지급운임(2520)
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.status == '완료' or instance.status != '완료':
        return

    # --- WM 재고 OUT ---
    # item_description 으로 자재 매칭. 수량은 weight_kg 기준 정수값 사용.
    # 직접 FK 없으므로, item_description 이 비어 있으면 재고 조정을 건너뜀.
    if instance.item_description:
        try:
            item_code, item_name = _resolve_material(instance.company, instance.item_description)
            # weight_kg 이 있으면 그 정수값을, 없으면 1을 수량으로 사용.
            # (TransportOrder에 SalesOrder FK가 없어 정확한 주문 수량을 알 수 없으므로
            #  weight_kg 정수 근사값을 사용한다. 향후 order_ref/FK 추가 시 교체 필요.)
            deduct_qty = max(1, int(float(instance.weight_kg or 0)))
            _adjust_inventory(
                company=instance.company,
                item_code=item_code,
                item_name=item_name,
                quantity=deduct_qty,
                movement_type='OUT',
                reference_type='TM',
                reference_document=instance.transport_number,
            )
        except Exception as e:
            logger.warning(
                'tm_freight_settlement: WM 재고 OUT 처리 실패 (transport=%s): %s',
                instance.transport_number, e, exc_info=True,
            )
    else:
        logger.warning(
            'tm_freight_settlement: item_description 없음 — 재고 OUT 건너뜀 (transport=%s). '
            'TransportOrder에 SalesOrder FK 추가 시 정확한 수량 처리 가능.',
            instance.transport_number,
        )

    # --- 운임 계산 ---
    freight_cost = _calculate_freight_cost(instance)
    if freight_cost > 0:
        instance.freight_cost = Decimal(str(freight_cost))

    if freight_cost > 0:
        try:
            _auto_post_freight(
                company=instance.company,
                transport_number=instance.transport_number,
                freight_cost=freight_cost,
            )
        except Exception as e:
            logger.warning(
                'tm_freight_settlement: FI 운반비 자동전기 실패 (transport=%s): %s',
                instance.transport_number, e, exc_info=True,
            )


def _calculate_freight_cost(transport_order):
    """FreightRate 테이블에서 운임 자동계산."""
    try:
        from scm_tm.models import FreightRate
        today = timezone.localdate()

        rate = (FreightRate.objects
                .filter(
                    company=transport_order.company,
                    carrier=transport_order.carrier,
                    origin__iexact=transport_order.origin,
                    destination__iexact=transport_order.destination,
                    is_active=True,
                    valid_from__lte=today,
                )
                .filter(
                    models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=today)
                )
                .order_by('-valid_from')
                .first())

        if not rate:
            return 0

        weight = float(transport_order.weight_kg or 0)
        volume = float(transport_order.volume_cbm or 0)
        calculated = (weight * float(rate.rate_per_kg)
                      + volume * float(rate.rate_per_cbm))
        return max(float(rate.min_charge), calculated)

    except Exception as e:
        logger.warning('_calculate_freight_cost: 운임 계산 실패: %s', e, exc_info=True)
        return 0


def _auto_post_freight(company, transport_number, freight_cost):
    """운반비 FI 전표: DR 운반비(6100) / CR 미지급운임(2520)."""
    from scm_fi.models import AccountMove, AccountMoveLine

    move_number = f'AUTO-TM-{transport_number or uuid.uuid4().hex[:8]}'
    if AccountMove.objects.filter(company=company, move_number=move_number).exists():
        return

    today = timezone.localdate()
    acc_freight  = _get_or_create_account(company, 'freight_expense')
    acc_accrued  = _get_or_create_account(company, 'accrued_freight')
    label        = f'자동전기-운반비: {transport_number}'

    move = AccountMove.objects.create(
        company=company, move_number=move_number, move_type='ENTRY',
        posting_date=today, ref=transport_number or '',
        state='DRAFT', total_debit=freight_cost, total_credit=freight_cost,
        created_by='system',
    )
    AccountMoveLine.objects.create(move=move, account=acc_freight,
                                    name=label, debit=freight_cost, credit=0)
    AccountMoveLine.objects.create(move=move, account=acc_accrued,
                                    name=label, debit=0, credit=freight_cost)


# ---------------------------------------------------------------------------
# 재고 조정 헬퍼
# ---------------------------------------------------------------------------

def _adjust_inventory(company, item_code, item_name, quantity, movement_type,
                       reference_type='', reference_document='',
                       monetary_amount=None, cost_amount=None, is_production=False):
    """
    WM 재고 수량 조정 + StockMovement 기록 + FI 자동전기.

    monetary_amount : 수익 인식 금액 (매입: 취득원가, 매출: 판매가)
    cost_amount     : 매출원가 (매출 시 재고자산 감소분, OUT 전용)
    is_production   : True → FI 생산원가전표 생성
    """
    if not item_code or not quantity:
        return

    from scm_wm.models import Inventory, StockMovement

    with transaction.atomic():
        inv, _ = Inventory.objects.get_or_create(
            company=company,
            item_code=str(item_code),
            warehouse=None,
            lot_number='',
            defaults={
                'item_name': item_name or str(item_code),
                'stock_qty': 0,
                'system_qty': 0,
                'min_stock': 0,
            },
        )

        if movement_type == 'IN':
            inv.stock_qty = (inv.stock_qty or 0) + int(quantity)
        elif movement_type == 'OUT':
            inv.stock_qty = max(0, (inv.stock_qty or 0) - int(quantity))
        inv.save(update_fields=['stock_qty'])

        StockMovement.objects.create(
            company=company,
            warehouse=None,
            movement_type=movement_type,
            material_code=str(item_code),
            material_name=item_name or str(item_code),
            quantity=quantity,
            reference_type=reference_type,
            reference_document=reference_document,
        )

        # FI 자동전기 (금액이 있을 때만)
        if monetary_amount and monetary_amount > 0:
            try:
                if is_production:
                    _auto_post_production(
                        company=company,
                        reference_document=reference_document,
                        item_name=item_name or str(item_code),
                        production_cost=monetary_amount,
                    )
                else:
                    _auto_post_fi(
                        company=company,
                        movement_type=movement_type,
                        reference_type=reference_type,
                        reference_document=reference_document,
                        item_name=item_name or str(item_code),
                        monetary_amount=monetary_amount,
                        cost_amount=cost_amount,
                    )
            except Exception as e:
                # 자동전기 실패 시 재고 이동은 유지 (FI는 나중에 수동 처리 가능)
                logger.warning(
                    '_adjust_inventory: FI 자동전기 실패 (ref=%s %s): %s',
                    reference_type, reference_document, e, exc_info=True,
                )


# ---------------------------------------------------------------------------
# FI 자동전기 — 매입 / 매출 + COGS
# ---------------------------------------------------------------------------

def _auto_post_fi(company, movement_type, reference_type, reference_document,
                  item_name, monetary_amount, cost_amount=None):
    """
    매입(IN) 또는 매출(OUT) 자동전표 생성.

    매입 (PO 입고):
        DR 재고자산   monetary_amount
        CR 매입채무   monetary_amount

    매출 (SO 출하):
        DR 매출채권   monetary_amount  (판매가)
        CR 매출       monetary_amount
        DR 매출원가   cost_amount      (원가 ← 추정값이면 괜찮음)
        CR 재고자산   cost_amount
    """
    from scm_fi.models import AccountMove, AccountMoveLine

    today = timezone.localdate()

    move_number = f'AUTO-{reference_type}-{reference_document or uuid.uuid4().hex[:8]}'
    if AccountMove.objects.filter(company=company, move_number=move_number).exists():
        return  # 중복 방지

    if movement_type == 'IN':
        # 매입전표
        move_type   = 'PURCHASE'
        debit_acc   = _get_or_create_account(company, 'inventory')
        credit_acc  = _get_or_create_account(company, 'ap')
        label       = f'자동전기-매입: {item_name}'
        total_dr    = monetary_amount
        total_cr    = monetary_amount

        move = AccountMove.objects.create(
            company=company, move_number=move_number, move_type=move_type,
            posting_date=today, ref=reference_document or '',
            state='DRAFT', total_debit=total_dr, total_credit=total_cr,
            created_by='system',
        )
        AccountMoveLine.objects.create(move=move, account=debit_acc,
                                        name=label, debit=monetary_amount, credit=0)
        AccountMoveLine.objects.create(move=move, account=credit_acc,
                                        name=label, debit=0, credit=monetary_amount)

    else:  # OUT — 매출 + COGS
        ca = float(cost_amount or monetary_amount * 0.7)  # 원가 없으면 70% 추정

        acc_ar       = _get_or_create_account(company, 'ar')
        acc_revenue  = _get_or_create_account(company, 'revenue')
        acc_cogs     = _get_or_create_account(company, 'cogs')
        acc_inv      = _get_or_create_account(company, 'inventory')

        total_dr = monetary_amount + ca
        total_cr = monetary_amount + ca
        label    = f'자동전기-매출: {item_name}'

        move = AccountMove.objects.create(
            company=company, move_number=move_number, move_type='SALE',
            posting_date=today, ref=reference_document or '',
            state='DRAFT', total_debit=total_dr, total_credit=total_cr,
            created_by='system',
        )
        # 수익 인식
        AccountMoveLine.objects.create(move=move, account=acc_ar,
                                        name=label, debit=monetary_amount, credit=0)
        AccountMoveLine.objects.create(move=move, account=acc_revenue,
                                        name=label, debit=0, credit=monetary_amount)
        # 원가 인식
        AccountMoveLine.objects.create(move=move, account=acc_cogs,
                                        name=f'자동전기-매출원가: {item_name}',
                                        debit=ca, credit=0)
        AccountMoveLine.objects.create(move=move, account=acc_inv,
                                        name=f'자동전기-재고감소: {item_name}',
                                        debit=0, credit=ca)


# ---------------------------------------------------------------------------
# FI 자동전기 — 생산원가
# ---------------------------------------------------------------------------

def _auto_post_production(company, reference_document, item_name, production_cost):
    """
    생산오더 완료 시 생산원가 전표.
        DR 재고자산(완제품)  production_cost
        CR 생산원가         production_cost
    """
    from scm_fi.models import AccountMove, AccountMoveLine

    if production_cost <= 0:
        return

    move_number = f'AUTO-PP-{reference_document or uuid.uuid4().hex[:8]}'
    if AccountMove.objects.filter(company=company, move_number=move_number).exists():
        return

    today = timezone.localdate()
    acc_inv  = _get_or_create_account(company, 'inventory')
    acc_prod = _get_or_create_account(company, 'production_cost')
    label    = f'자동전기-생산원가: {item_name}'

    move = AccountMove.objects.create(
        company=company, move_number=move_number, move_type='ENTRY',
        posting_date=today, ref=reference_document or '',
        state='DRAFT', total_debit=production_cost, total_credit=production_cost,
        created_by='system',
    )
    AccountMoveLine.objects.create(move=move, account=acc_inv,
                                    name=label, debit=production_cost, credit=0)
    AccountMoveLine.objects.create(move=move, account=acc_prod,
                                    name=label, debit=0, credit=production_cost)


# ---------------------------------------------------------------------------
# 재고 부족 모니터링 — min_stock 알림 + 자동 발주
# ---------------------------------------------------------------------------

@receiver(post_save, sender='scm_wm.Inventory')
def check_min_stock_alert(sender, instance, **kwargs):
    """
    Inventory 저장 시 stock_qty < min_stock 이면:
      1. 해당 회사의 모든 유저에게 재고 부족 알림 발송
      2. MM PurchaseOrder 자동 발주 초안 생성 (중복 방지)
    """
    # min_stock 이 0 이하이면 모니터링 대상 아님
    if not instance.min_stock or instance.min_stock <= 0:
        return

    stock_qty = instance.stock_qty or 0
    if stock_qty >= instance.min_stock:
        return

    company = instance.company

    # --- 1. 알림 발송 ---
    try:
        from scm_notifications.models import Notification
        from scm_accounts.models import User

        title = '재고 부족 경고'
        message = (
            f'{instance.item_name} 재고 부족: '
            f'현재 {stock_qty} / 최소 {instance.min_stock}'
        )

        users = User.objects.filter(company=company, is_active=True)
        notifications = [
            Notification(
                company=company,
                recipient=user,
                notification_type='system',
                title=title,
                message=message,
                ref_module='wm',
                ref_id=instance.pk,
            )
            for user in users
        ]
        if notifications:
            Notification.objects.bulk_create(notifications, ignore_conflicts=True)
            logger.info(
                'check_min_stock_alert: 재고 부족 알림 %d건 발송 (item=%s, stock=%s, min=%s)',
                len(notifications), instance.item_code, stock_qty, instance.min_stock,
            )
    except Exception as e:
        logger.warning(
            'check_min_stock_alert: 재고 부족 알림 발송 실패 (item=%s): %s',
            instance.item_code, e, exc_info=True,
        )

    # --- 2. MM 자동 발주 생성 ---
    try:
        from scm_mm.models import PurchaseOrder as MMPurchaseOrder

        today = timezone.localdate()
        po_number = f'AUTO-PO-{instance.item_code}-{today}'

        if MMPurchaseOrder.objects.filter(po_number=po_number).exists():
            logger.info(
                'check_min_stock_alert: 자동발주 이미 존재함, 건너뜀 (po_number=%s)', po_number,
            )
            return

        # 발주 수량: 최소재고의 2배까지 채우는 양, 최소 1
        order_qty = max(instance.min_stock * 2 - stock_qty, 1)

        MMPurchaseOrder.objects.create(
            company=company,
            po_number=po_number,
            supplier=None,
            item_name=instance.item_name,
            quantity=order_qty,
            unit_price=Decimal('0'),
            status='발주확정',
            note=f'재고 부족 자동생성: {instance.item_name} (현재 {stock_qty} / 최소 {instance.min_stock})',
        )
        logger.info(
            'check_min_stock_alert: 자동발주 생성 완료 (po_number=%s, qty=%s)',
            po_number, order_qty,
        )
    except Exception as e:
        logger.warning(
            'check_min_stock_alert: 자동발주 생성 실패 (item=%s): %s',
            instance.item_code, e, exc_info=True,
        )


# ---------------------------------------------------------------------------
# 헬퍼: 자재 단가 조회
# ---------------------------------------------------------------------------

def _get_material_unit_cost(company, material_code):
    """MaterialPriceHistory 최근 단가 → 없으면 0 반환."""
    try:
        from scm_mm.models import MaterialPriceHistory
        latest = (MaterialPriceHistory.objects
                  .filter(company=company, material__material_code=material_code)
                  .order_by('-effective_from')
                  .first())
        if latest:
            return Decimal(str(latest.unit_price))
    except Exception as e:
        logger.warning(
            '_get_material_unit_cost: 단가 조회 실패 (code=%s): %s',
            material_code, e, exc_info=True,
        )
    return Decimal('0')


def _get_work_center_cost(company, work_center):
    """WorkCenterCost 최신 단가 조회 (없으면 None)."""
    try:
        from scm_pp.models import WorkCenterCost
        today = timezone.localdate()
        wcc = (WorkCenterCost.objects
               .filter(company=company, work_center=work_center,
                       effective_from__lte=today)
               .filter(models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today))
               .order_by('-effective_from')
               .first())
        return wcc
    except Exception as e:
        logger.warning(
            '_get_work_center_cost: WorkCenterCost 조회 실패: %s', e, exc_info=True,
        )
        return None


def _estimate_inventory_cost(company, item_code, quantity, revenue_amount):
    """
    재고원가 추정.
    1순위: MaterialPriceHistory 최근 매입단가 × 수량
    2순위: revenue_amount × 70% (gross margin 30% 가정)
    """
    unit_cost = _get_material_unit_cost(company, item_code)
    if unit_cost > 0:
        return float(unit_cost) * float(quantity)
    return revenue_amount * 0.7


# ---------------------------------------------------------------------------
# 헬퍼: Material 코드 해석
# ---------------------------------------------------------------------------

def _resolve_material(company, item_name):
    """item_name → (material_code, material_name)"""
    if not item_name:
        return ('UNKNOWN', 'UNKNOWN')
    normalized = item_name.strip()
    try:
        from scm_mm.models import Material
        mat = Material.objects.filter(
            company=company, material_name__iexact=normalized,
        ).first()
        if mat:
            return (mat.material_code, mat.material_name)
    except Exception as e:
        logger.warning(
            '_resolve_material: Material 조회 실패 (item_name=%s): %s',
            item_name, e, exc_info=True,
        )
    return (normalized, normalized)
