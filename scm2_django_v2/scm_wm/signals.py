"""
Cross-module inventory signals + FI 자동전기 (Auto Journal Posting).

Signal overview
---------------
mm_receipt_to_wm      : PurchaseOrder '입고완료' → WM IN  + FI 매입전표
sd_delivery_from_wm   : SalesOrder '배송완료'   → WM OUT + FI 매출전표 + COGS
pp_completion_consume  : ProductionOrder '완료'  → BOM OUT + FG IN + FI 생산원가전표

FI 자동전표 계정과목 (K-GAAP)
-------------------------------
  1400  재고자산     ASSET
  1100  매출채권     ASSET
  2510  매입채무     LIABILITY
  4000  매출        REVENUE
  5000  매출원가     EXPENSE
  5100  생산원가     EXPENSE
"""
from decimal import Decimal

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone


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
# SD → WM (+ FI 매출전표 + COGS)
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='scm_sd.SalesOrder')
def sd_delivery_from_wm(sender, instance, **kwargs):
    """
    SalesOrder → '배송완료' 전환 시:
      1. WM 재고 OUT
      2. FI 매출전표: DR 매출채권 / CR 매출  (금액 = total_amount)
      3. FI COGS전표: DR 매출원가 / CR 재고자산  (금액 = 재고원가 추정)
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
    except Exception:
        revenue_amount = float(instance.quantity) * float(instance.unit_price or 0)

    item_code, item_name = _resolve_material(instance.company, instance.item_name)

    # 재고원가: MaterialPriceHistory 최근 단가 → 없으면 revenue * 0.7 추정
    cost_amount = _estimate_inventory_cost(
        instance.company, item_code, instance.quantity, revenue_amount
    )

    _adjust_inventory(
        company=instance.company,
        item_code=item_code,
        item_name=item_name,
        quantity=int(instance.quantity),
        movement_type='OUT',
        reference_type='SO',
        reference_document=instance.order_number,
        monetary_amount=revenue_amount,
        cost_amount=cost_amount,
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
      3. FI 생산원가전표: DR 재고자산(완제품) / CR 생산원가  (BOM 자재단가 합산)
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
    production_cost = Decimal('0')

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

                # 자재 단가 합산으로 생산원가 추정
                unit_cost = _get_material_unit_cost(instance.company, line.material_code)
                production_cost += unit_cost * Decimal(str(gross_qty))
        except Exception:
            pass

    # 완제품 입고
    fg_code, fg_name = _resolve_material(instance.company, instance.product_name)
    _adjust_inventory(
        company=instance.company,
        item_code=fg_code,
        item_name=fg_name,
        quantity=int(qty_multiplier),
        movement_type='IN',
        reference_type='PP',
        reference_document=instance.order_number,
        monetary_amount=float(production_cost),
        is_production=True,
    )


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
            except Exception:
                pass  # 자동전기 실패 시 재고 이동 유지


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
    import uuid

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
    import uuid

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
# 헬퍼: 자재 단가 조회
# ---------------------------------------------------------------------------

def _get_material_unit_cost(company, material_code):
    """MaterialPriceHistory 최근 단가 → 없으면 0 반환."""
    try:
        from scm_mm.models import MaterialPriceHistory
        latest = (MaterialPriceHistory.objects
                  .filter(company=company, material__material_code=material_code)
                  .order_by('-effective_date')
                  .first())
        if latest:
            return Decimal(str(latest.unit_price))
    except Exception:
        pass
    return Decimal('0')


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
    except Exception:
        pass
    return (normalized, normalized)
