import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from django.utils import timezone
from decimal import Decimal
import uuid, traceback

TODAY = timezone.localdate()
UID = uuid.uuid4().hex[:6].upper()
ok_c = warn_c = fail_c = 0

def log(icon, sect, msg):
    global ok_c, warn_c, fail_c
    line = f'  [{icon}] [{sect}] {msg}'
    print(line)
    if icon == 'OK': ok_c += 1
    elif icon == 'WRN': warn_c += 1
    elif icon == 'ERR': fail_c += 1

from scm_accounts.models import Company, User
company = Company.objects.first()
user = User.objects.filter(company=company).first()
log('OK', 'BASE', f'company={company} user={user.email}')

# ── 1. WM Warehouse ──────────────────────────────────────────
print('\n--- 1. WM Warehouse ---')
from scm_wm.models import Warehouse, Inventory, StockMovement
try:
    wh, _ = Warehouse.objects.get_or_create(
        company=company, warehouse_code='WH-TEST',
        defaults={'warehouse_name': '테스트창고', 'location': '서울'})
    log('OK', 'WM', f'창고: {wh.warehouse_name}')
except Exception as e:
    log('ERR', 'WM', f'창고: {e}')
    wh = None

# ── 2. MM Supplier / Material ────────────────────────────────
print('\n--- 2. MM Supplier / Material ---')
from scm_mm.models import Supplier, Material, PurchaseOrder
from scm_fi.models import AccountMove
try:
    sup, _ = Supplier.objects.get_or_create(
        company=company, name='테스트공급사',
        defaults={'email': 'sup@test.com', 'phone': '02-0000-0000', 'status': '활성'})
    log('OK', 'MM', f'공급업체: {sup.name}')
except Exception as e:
    log('ERR', 'MM', f'공급업체: {e}')
    sup = None

try:
    mat, _ = Material.objects.get_or_create(
        company=company, material_code=f'M-{UID}',
        defaults={'material_name': '테스트자재', 'material_type': '원재료',
                  'unit': 'EA', 'min_stock': 5, 'lead_time_days': 7})
    log('OK', 'MM', f'자재: {mat.material_code}')
except Exception as e:
    log('ERR', 'MM', f'자재: {e}')
    mat = None

# ── 3. PP BOM + Order ────────────────────────────────────────
print('\n--- 3. PP BOM / Order ---')
from scm_pp.models import BillOfMaterial, BomLine, ProductionOrder
bom = None
pp = None
try:
    bom, _ = BillOfMaterial.objects.get_or_create(
        company=company, bom_code=f'BOM-{UID}',
        defaults={'product_name': '테스트완제품', 'version': '1.0', 'is_active': True})
    if mat:
        BomLine.objects.get_or_create(
            bom=bom, material_code=mat.material_code,
            defaults={'material_name': mat.material_name,
                      'quantity': Decimal('2'), 'unit': 'EA', 'scrap_rate': Decimal('5')})
    log('OK', 'PP', f'BOM: {bom.bom_code} ({bom.lines.count()}라인)')
except Exception as e:
    log('ERR', 'PP', f'BOM: {e}')

try:
    pp, _ = ProductionOrder.objects.get_or_create(
        company=company, order_number=f'PP-{UID}',
        defaults={'bom': bom, 'product_name': '테스트완제품',
                  'planned_qty': 10, 'status': '계획',
                  'planned_start': TODAY, 'planned_end': TODAY,
                  'work_center': '테스트라인'})
    log('OK', 'PP', f'생산오더: {pp.order_number}')
except Exception as e:
    log('ERR', 'PP', f'생산오더: {e}')

# ── 4. MM PO 입고완료 → WM IN + FI 매입전표 ──────────────────
print('\n--- 4. MM PO 입고완료 -> WM / FI ---')
try:
    item_nm = mat.material_name if mat else '테스트자재'
    po = PurchaseOrder.objects.create(
        company=company, po_number=f'PO-{UID}', supplier=sup,
        item_name=item_nm, quantity=20, unit_price=Decimal('5000'),
        currency='KRW', delivery_date=TODAY, status='발주확정')
    log('OK', 'MM', f'발주서: {po.po_number}')

    po.status = '입고완료'
    po.save()

    sm = StockMovement.objects.filter(company=company, reference_document=po.po_number).first()
    log('OK' if sm else 'WRN', 'WM', f'재고이동: {sm.movement_type if sm else "없음"}')
    fi = AccountMove.objects.filter(company=company, ref=po.po_number).first()
    log('OK' if fi else 'WRN', 'FI', f'매입전표: {fi.move_number if fi else "없음"}')
except Exception as e:
    log('ERR', 'MM->WM->FI', f'{e}')
    traceback.print_exc()

# ── 5. SD 수주 생성 → MTO + 배송완료 → FI ───────────────────
print('\n--- 5. SD 수주 -> MTO / FI ---')
from scm_sd.models import Customer, SalesOrder
import time
try:
    cust, _ = Customer.objects.get_or_create(
        company=company, customer_code=f'C-{UID}',
        defaults={'customer_name': '테스트고객', 'email': 'c@test.com',
                  'credit_limit': Decimal('10000000'),
                  'payment_terms': '30일', 'status': '활성'})
    log('OK', 'SD', f'고객: {cust.customer_name}')

    so = SalesOrder.objects.create(
        company=company, order_number=f'SO-{UID}',
        customer=cust, customer_name=cust.customer_name,
        item_name='테스트완제품', quantity=5,
        unit_price=Decimal('15000'), discount_rate=Decimal('0'),
        status='주문접수')
    log('OK', 'SD', f'수주 생성: {so.order_number}')

    time.sleep(0.3)
    mto = ProductionOrder.objects.filter(
        company=company, order_number=f'MTO-{so.order_number}').first()
    log('OK' if mto else 'WRN', 'SD->PP',
        f'MTO: {mto.order_number + " qty=" + str(mto.planned_qty) if mto else "없음 (재고 충분)"}')

    so.status = '배송완료'
    so.save()
    fi_sale = AccountMove.objects.filter(company=company, ref=so.order_number).first()
    log('OK' if fi_sale else 'WRN', 'SD->FI',
        f'매출전표: {fi_sale.move_number if fi_sale else "없음"}')
except Exception as e:
    log('ERR', 'SD->FI', f'{e}')
    traceback.print_exc()

# ── 6. PP 완료 → BOM 소비 + FI 생산원가 ─────────────────────
print('\n--- 6. PP 완료 -> WM / FI ---')
try:
    if pp:
        pp.status = '생산중'
        pp.save()
        sm_b = StockMovement.objects.filter(
            company=company, reference_document=pp.order_number).count()

        pp.status = '완료'
        pp.actual_start = TODAY
        pp.actual_end = TODAY
        pp.save()

        sm_a = StockMovement.objects.filter(
            company=company, reference_document=pp.order_number).count()
        log('OK' if sm_a > sm_b else 'WRN', 'PP->WM',
            f'BOM 소비: {sm_a - sm_b}건 추가')

        pp.refresh_from_db()
        fi_pp = AccountMove.objects.filter(company=company, ref=pp.order_number).first()
        log('OK' if fi_pp else 'WRN', 'PP->FI',
            f'생산원가전표: {fi_pp.move_number if fi_pp else "없음"}'
            f' (원가={float(pp.total_cost):,.0f}원)')
    else:
        log('WRN', 'PP', '생산오더 없음 - 스킵')
except Exception as e:
    log('ERR', 'PP->WM->FI', f'{e}')
    traceback.print_exc()

# ── 7. QM 불합격 → PP 재작업 ────────────────────────────────
print('\n--- 7. QM 불합격 -> PP 재작업 ---')
from scm_qm.models import InspectionPlan, InspectionResult
try:
    plan, _ = InspectionPlan.objects.get_or_create(
        company=company, plan_code=f'QP-{UID}',
        defaults={'plan_name': '테스트검사', 'inspection_type': '수입검사',
                  'target_item': '테스트자재', 'is_active': True})
    log('OK', 'QM', f'검사계획: {plan.plan_code}')

    qr = InspectionResult.objects.create(
        company=company, result_number=f'QR-{UID}', plan=plan,
        item_name='테스트자재', lot_number=f'LOT-{UID}',
        inspected_qty=10, passed_qty=10, failed_qty=0,
        result='합격', inspector='테스터', inspected_at=timezone.now())
    log('OK', 'QM', f'검사결과 생성: {qr.result_number}')

    qr.passed_qty = 7
    qr.failed_qty = 3
    qr.result = '불합격'
    qr.save()
    log('OK', 'QM', '불합격 전환')

    rw = ProductionOrder.objects.filter(
        company=company, order_number=f'RW-{qr.result_number}').first()
    log('OK' if rw else 'ERR', 'QM->PP',
        f'재작업오더: {rw.order_number + " qty=" + str(rw.planned_qty) if rw else "없음"}')
except Exception as e:
    log('ERR', 'QM->PP', f'{e}')
    traceback.print_exc()

# ── 8. HR 급여확정 → FI 인건비 ──────────────────────────────
print('\n--- 8. HR 급여확정 -> FI ---')
from scm_hr.models import Department, Employee, Payroll
try:
    dept, _ = Department.objects.get_or_create(
        company=company, dept_code=f'D-{UID}',
        defaults={'dept_name': '생산부', 'is_active': True})
    emp, _ = Employee.objects.get_or_create(
        company=company, emp_code=f'E-{UID}',
        defaults={'name': '테스트직원', 'dept': dept,
                  'position': '사원', 'hire_date': TODAY,
                  'email': f'e{UID}@test.com', 'phone': '010-0000-0000',
                  'base_salary': Decimal('3000000')})
    log('OK', 'HR', f'직원: {emp.name}')

    payroll = Payroll.objects.create(
        company=company, employee=emp,
        payroll_number=f'PAY-{UID}',
        pay_year=TODAY.year, pay_month=TODAY.month,
        base_salary=Decimal('3500000'),
        gross_pay=Decimal('3500000'),
        net_pay=Decimal('3000000'),
        state='DRAFT', payment_date=TODAY)
    log('OK', 'HR', f'급여초안: {payroll.payroll_number}')

    payroll.state = '확정'
    payroll.save()

    fi_hr = AccountMove.objects.filter(
        company=company,
        move_number=f'AUTO-HR-{payroll.payroll_number}').first()
    log('OK' if fi_hr else 'ERR', 'HR->FI',
        f'인건비전표: {fi_hr.move_number + " " + str(fi_hr.total_debit) if fi_hr else "없음"}')
except Exception as e:
    log('ERR', 'HR->FI', f'{e}')
    traceback.print_exc()

# ── 9. TM 운송완료 → FI 운반비 ──────────────────────────────
print('\n--- 9. TM 운송완료 -> FI ---')
from scm_tm.models import Carrier, TransportOrder
try:
    carrier, _ = Carrier.objects.get_or_create(
        company=company, carrier_code='CAR-TEST',
        defaults={'carrier_name': '테스트운송사', 'phone': '02-0000-1111'})
    tm_fields = {f.name for f in TransportOrder._meta.get_fields()}
    tm_data = {
        'company': company,
        'transport_number': f'TM-{UID}',
        'carrier': carrier,
        'status': '운송중',
    }
    for fld, val in [('origin', '서울'), ('destination', '부산'),
                     ('weight_kg', Decimal('500')), ('volume_cbm', Decimal('2'))]:
        if fld in tm_fields:
            tm_data[fld] = val
    tm = TransportOrder.objects.create(**tm_data)
    log('OK', 'TM', f'운송오더: {tm.transport_number}')
    tm.status = '완료'
    tm.save()
    fi_tm = AccountMove.objects.filter(company=company, ref=tm.transport_number).first()
    log('OK' if fi_tm else 'WRN', 'TM->FI',
        f'운반비전표: {fi_tm.move_number if fi_tm else "없음 (FreightRate 없으면 정상)"}')
except Exception as e:
    log('ERR', 'TM->FI', f'{e}')
    traceback.print_exc()

# ── 10. WM min_stock → 자동발주 ─────────────────────────────
print('\n--- 10. WM min_stock -> 자동발주 ---')
try:
    inv_t = Inventory.objects.create(
        company=company, item_code=f'AU-{UID}',
        warehouse=wh, lot_number='',
        item_name='자동발주테스트', stock_qty=100,
        system_qty=100, min_stock=10)
    inv_t.stock_qty = 3
    inv_t.save()

    today_str = TODAY.strftime('%Y-%m-%d')
    expected_po = f'AUTO-PO-AU-{UID}-{today_str}'
    auto_po = PurchaseOrder.objects.filter(
        company=company, po_number=expected_po).first()
    log('OK' if auto_po else 'ERR', 'WM->MM',
        f'자동발주: {auto_po.po_number if auto_po else "없음 (expected: " + expected_po + ")"}')
except Exception as e:
    log('ERR', 'WM->MM', f'{e}')
    traceback.print_exc()

# ── 11. WI 완료 → PP produced_qty ────────────────────────────
print('\n--- 11. WI 완료 -> PP produced_qty ---')
from scm_wi.models import WorkInstruction
try:
    pp2, _ = ProductionOrder.objects.get_or_create(
        company=company, order_number=f'PP2-{UID}',
        defaults={'product_name': '테스트완제품2',
                  'planned_qty': 10, 'produced_qty': 0,
                  'status': '생산중', 'work_center': '테스트라인'})
    qty_b = pp2.produced_qty

    wi = WorkInstruction.objects.create(
        company=company,
        wi_number=f'WI-{UID}',
        title='테스트작업지시',
        description='테스트설명',
        work_center='테스트라인',
        assigned_to='담당자',
        priority='보통',
        status='대기',
        planned_qty=5,
        actual_qty=5,
        planned_start=timezone.now(),
        planned_end=timezone.now())
    log('OK', 'WI', f'작업지시 생성: {wi.wi_number}')

    wi.status = '완료'
    wi.save()

    pp2.refresh_from_db()
    qty_a = pp2.produced_qty
    log('OK' if qty_a > qty_b else 'WRN', 'WI->PP',
        f'produced_qty: {qty_b} -> {qty_a}')
except Exception as e:
    log('ERR', 'WI->PP', f'{e}')
    traceback.print_exc()

# ── 최종 요약 ────────────────────────────────────────────────
print('\n' + '=' * 55)
print(f'  결과:  OK={ok_c}  WRN={warn_c}  ERR={fail_c}')
print('=' * 55)

print('\n[AUTO FI 전표 목록]')
for m in AccountMove.objects.filter(
        company=company,
        move_number__startswith='AUTO-').order_by('-id')[:12]:
    print(f'  {m.move_number:<42s} {float(m.total_debit):>12,.0f}원')
