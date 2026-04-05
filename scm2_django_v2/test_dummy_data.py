"""
더미 데이터 + 크로스 모듈 연동 통합 테스트
실행: python manage.py shell < test_dummy_data.py
"""
import os, sys, traceback, uuid
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.utils import timezone
from django.db import transaction
from decimal import Decimal

TODAY = timezone.localdate()
UID   = uuid.uuid4().hex[:6].upper()

PASS  = '✓'
FAIL  = '✗'
WARN  = '!'
results = []

def log(icon, section, msg):
    line = f'  {icon}  [{section}] {msg}'
    results.append(line)
    print(line)

def section(title):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print('='*60)

# ─── 공통: 회사/유저 ──────────────────────────────────────────
from scm_accounts.models import Company, User
company = Company.objects.first()
user    = User.objects.filter(company=company).first()
if not company or not user:
    print('ERROR: company/user 없음. 먼저 회원가입하세요.')
    sys.exit(1)

section('0. 기준 정보')
log(PASS, 'BASE', f'company={company}, user={user.email}')

# ─── 1. WM 창고 ───────────────────────────────────────────────
section('1. WM 창고 생성')
from scm_wm.models import Warehouse, Inventory, StockMovement
try:
    wh, _ = Warehouse.objects.get_or_create(
        company=company, name='더미창고A',
        defaults={'location': '서울 강남구', 'capacity': 10000}
    )
    log(PASS, 'WM', f'창고 생성: {wh.name}')
except Exception as e:
    log(FAIL, 'WM', f'창고 생성 실패: {e}')
    wh = None

# ─── 2. MM 공급업체 + 자재 ────────────────────────────────────
section('2. MM 공급업체 / 자재 생성')
from scm_mm.models import Supplier, Material, PurchaseOrder, GoodsReceipt
try:
    supplier, _ = Supplier.objects.get_or_create(
        company=company, name='더미공급사',
        defaults={'contact': '김공급', 'email': 'sup@test.com', 'phone': '02-1234-5678', 'payment_terms': '30일', 'status': '활성'}
    )
    log(PASS, 'MM', f'공급업체: {supplier.name}')
except Exception as e:
    log(FAIL, 'MM', f'공급업체 실패: {e}'); supplier = None

try:
    mat_code = f'MAT-{UID}'
    material, _ = Material.objects.get_or_create(
        company=company, material_code=mat_code,
        defaults={'material_name': '더미원자재', 'material_type': '원재료', 'unit': 'EA', 'min_stock': 5, 'lead_time_days': 7}
    )
    log(PASS, 'MM', f'자재: {material.material_code} / min_stock={material.min_stock}')
except Exception as e:
    log(FAIL, 'MM', f'자재 생성 실패: {e}'); material = None

# ─── 3. PP BOM + 생산오더 ─────────────────────────────────────
section('3. PP BOM / 생산오더 생성')
from scm_pp.models import BillOfMaterial, BomLine, ProductionOrder, MrpRun
try:
    bom, _ = BillOfMaterial.objects.get_or_create(
        company=company, bom_code=f'BOM-{UID}',
        defaults={'product_name': '더미완제품', 'version': '1.0', 'is_active': True}
    )
    if material:
        BomLine.objects.get_or_create(
            bom=bom, material_code=material.material_code,
            defaults={'material_name': material.material_name, 'quantity': Decimal('2.000'), 'unit': 'EA', 'scrap_rate': Decimal('5.00')}
        )
    log(PASS, 'PP', f'BOM: {bom.bom_code} (라인 {bom.lines.count()}개)')
except Exception as e:
    log(FAIL, 'PP', f'BOM 실패: {e}'); bom = None

try:
    pp_order, _ = ProductionOrder.objects.get_or_create(
        company=company, order_number=f'PP-{UID}',
        defaults={
            'bom': bom, 'product_name': '더미완제품', 'planned_qty': 10,
            'status': '계획', 'planned_start': TODAY, 'planned_end': TODAY,
            'work_center': '조립라인1', 'note': '더미테스트',
        }
    )
    log(PASS, 'PP', f'생산오더: {pp_order.order_number} / status={pp_order.status}')
except Exception as e:
    log(FAIL, 'PP', f'생산오더 실패: {e}'); pp_order = None

# ─── 4. MM 발주서 생성 → 입고완료 (WM IN + FI 매입전표) ────────
section('4. MM 발주 → 입고완료 → WM/FI 연동 테스트')
try:
    po_num = f'PO-{UID}'
    po = PurchaseOrder.objects.create(
        company=company,
        po_number=po_num,
        supplier=supplier,
        item_name=material.material_name if material else '더미원자재',
        quantity=20,
        unit_price=Decimal('5000.00'),
        currency='KRW',
        delivery_date=TODAY,
        status='발주확정',
        note='더미 발주서',
    )
    log(PASS, 'MM', f'발주서 생성: {po.po_number}')

    # 입고완료로 전환 → WM IN + FI 매입전표 발생
    inv_before = Inventory.objects.filter(company=company, item_name__iexact=material.material_name if material else '').first()
    stock_before = inv_before.stock_qty if inv_before else 0

    po.status = '입고완료'
    po.save()
    log(PASS, 'MM', f'발주서 입고완료 전환')

    # WM 재고 확인
    inv_after = Inventory.objects.filter(company=company).order_by('-id').first()
    sm = StockMovement.objects.filter(company=company, reference_document=po_num).first()
    if sm:
        log(PASS, 'WM', f'재고이동 생성: {sm.movement_type} {sm.quantity}개 ({sm.material_name})')
    else:
        log(WARN, 'WM', '재고이동 레코드 없음 (자재명 매칭 실패 가능성)')

    # FI 전표 확인
    from scm_fi.models import AccountMove
    fi_move = AccountMove.objects.filter(company=company, move_number__startswith=f'AUTO-PO-{po_num}').first()
    if not fi_move:
        fi_move = AccountMove.objects.filter(company=company, ref=po_num).first()
    if fi_move:
        log(PASS, 'FI', f'매입전표 자동생성: {fi_move.move_number} / {fi_move.total_debit:,.0f}원')
    else:
        log(WARN, 'FI', f'매입전표 없음 (move_number prefix=AUTO-PO-{po_num})')

except Exception as e:
    log(FAIL, 'MM→WM→FI', f'오류: {e}')
    traceback.print_exc()

# ─── 5. SD 고객 + 수주 생성 → 배송완료 (WM OUT + FI) ──────────
section('5. SD 수주 → 배송완료 → WM/FI 연동 테스트')
from scm_sd.models import Customer, SalesOrder, Delivery
try:
    cust_code = f'C-{UID}'
    customer_obj, _ = Customer.objects.get_or_create(
        company=company, customer_code=cust_code,
        defaults={'customer_name': '더미고객사', 'contact': '이고객', 'email': 'cust@test.com',
                  'credit_limit': Decimal('10000000'), 'payment_terms': '30일', 'status': '활성'}
    )
    log(PASS, 'SD', f'고객: {customer_obj.customer_name}')

    so = SalesOrder.objects.create(
        company=company,
        order_number=f'SO-{UID}',
        customer=customer_obj,
        customer_name=customer_obj.customer_name,
        item_name='더미완제품',
        quantity=5,
        unit_price=Decimal('15000.00'),
        discount_rate=Decimal('0'),
        status='주문접수',
    )
    log(PASS, 'SD', f'수주 생성: {so.order_number}')

    # MTO 신호 확인 (post_save on 주문접수)
    import time; time.sleep(0.3)
    mto = ProductionOrder.objects.filter(
        company=company, order_number=f'MTO-{so.order_number}'
    ).first()
    if mto:
        log(PASS, 'SD→PP', f'MTO 생산오더 자동생성: {mto.order_number} / qty={mto.planned_qty}')
    else:
        log(WARN, 'SD→PP', 'MTO 생산오더 없음 (재고 충분하거나 신호 미발생)')

    # 배송완료 전환 → WM OUT + FI 매출전표
    so.status = '배송완료'
    so.save()
    log(PASS, 'SD', '수주 배송완료 전환')

    sm2 = StockMovement.objects.filter(company=company, reference_document=so.order_number).first()
    if sm2:
        log(PASS, 'WM', f'출고이동 생성: {sm2.movement_type} {sm2.quantity}개')
    else:
        log(WARN, 'WM', '출고이동 없음 (TM 전환 후 처리 설계)')

    fi_sale = AccountMove.objects.filter(company=company, ref=so.order_number).first()
    if fi_sale:
        log(PASS, 'FI', f'매출전표 자동생성: {fi_sale.move_number}')
    else:
        log(WARN, 'FI', '매출전표 없음')

except Exception as e:
    log(FAIL, 'SD→WM→FI', f'오류: {e}')
    traceback.print_exc()

# ─── 6. PP 생산오더 완료 → BOM 소비 + FI 생산원가 ──────────────
section('6. PP 생산오더 완료 → WM BOM소비 + FI 연동 테스트')
try:
    if pp_order:
        pp_order.refresh_from_db()
        pp_order.status = '생산중'
        pp_order.save()

        sm_before = StockMovement.objects.filter(company=company, reference_document=pp_order.order_number).count()
        pp_order.status = '완료'
        pp_order.actual_start = TODAY
        pp_order.actual_end   = TODAY
        pp_order.save()
        log(PASS, 'PP', f'생산오더 완료 전환: {pp_order.order_number}')

        sm_after = StockMovement.objects.filter(company=company, reference_document=pp_order.order_number).count()
        log(PASS if sm_after > sm_before else WARN, 'WM',
            f'BOM 소비 이동: {sm_after - sm_before}건 추가' if sm_after > sm_before else 'BOM 소비 이동 없음 (BOM 라인 or 재고 확인)')

        pp_order.refresh_from_db()
        fi_pp = AccountMove.objects.filter(company=company, ref=pp_order.order_number).first()
        if fi_pp:
            log(PASS, 'FI', f'생산원가전표 자동생성: {fi_pp.move_number} / 원가={pp_order.total_cost:,.0f}원')
        else:
            log(WARN, 'FI', f'생산원가전표 없음 (원가={pp_order.total_cost})')
except Exception as e:
    log(FAIL, 'PP→WM→FI', f'오류: {e}')
    traceback.print_exc()

# ─── 7. QM 검사결과 불합격 → PP 재작업 오더 ──────────────────────
section('7. QM 불합격 → PP 재작업 오더 생성 테스트')
from scm_qm.models import InspectionPlan, InspectionResult, DefectRecord
try:
    plan, _ = InspectionPlan.objects.get_or_create(
        company=company, plan_code=f'QP-{UID}',
        defaults={'plan_name': '더미검사계획', 'inspection_type': '수입검사', 'target_item': '더미원자재', 'is_active': True}
    )
    log(PASS, 'QM', f'검사계획: {plan.plan_code}')

    result_num = f'QR-{UID}'
    qm_result = InspectionResult.objects.create(
        company=company,
        result_number=result_num,
        plan=plan,
        item_name='더미원자재',
        lot_number=f'LOT-{UID}',
        inspected_qty=10,
        passed_qty=10,
        failed_qty=0,
        result='합격',
        inspector='김검사',
        inspected_at=timezone.now(),
    )
    log(PASS, 'QM', f'검사결과 합격 생성: {qm_result.result_number}')

    # 불합격으로 전환 → PP 재작업 오더
    qm_result.passed_qty = 7
    qm_result.failed_qty = 3
    qm_result.result = '불합격'
    qm_result.save()
    log(PASS, 'QM', '검사결과 불합격 전환')

    rework = ProductionOrder.objects.filter(company=company, order_number=f'RW-{result_num}').first()
    if rework:
        log(PASS, 'QM→PP', f'재작업 오더 자동생성: {rework.order_number} / qty={rework.planned_qty}')
    else:
        log(FAIL, 'QM→PP', f'재작업 오더 없음 (order_number=RW-{result_num})')

except Exception as e:
    log(FAIL, 'QM→PP', f'오류: {e}')
    traceback.print_exc()

# ─── 8. HR 급여 확정 → FI 인건비전표 ─────────────────────────────
section('8. HR 급여확정 → FI 인건비전표 테스트')
try:
    from scm_hr.models import Department, Employee, Payroll
    dept, _ = Department.objects.get_or_create(
        company=company, name='생산부',
        defaults={'code': f'D-{UID}'}
    )
    emp, _ = Employee.objects.get_or_create(
        company=company, employee_number=f'E-{UID}',
        defaults={
            'name': '더미직원', 'department': dept,
            'position': '사원', 'hire_date': TODAY,
            'email': f'emp{UID}@test.com', 'status': '재직',
        }
    )
    log(PASS, 'HR', f'부서: {dept.name} / 직원: {emp.name}')

    # Payroll 모델 필드 확인 후 생성
    payroll_fields = {f.name for f in Payroll._meta.get_fields()}
    payroll_data = {
        'company': company,
        'employee': emp,
        'payment_date': TODAY,
    }
    # 필드명에 따라 동적으로 설정
    if 'payroll_number' in payroll_fields:
        payroll_data['payroll_number'] = f'PAY-{UID}'
    if 'gross_pay' in payroll_fields:
        payroll_data['gross_pay'] = Decimal('3500000')
    elif 'gross_salary' in payroll_fields:
        payroll_data['gross_salary'] = Decimal('3500000')
    if 'net_pay' in payroll_fields:
        payroll_data['net_pay'] = Decimal('3000000')
    elif 'net_salary' in payroll_fields:
        payroll_data['net_salary'] = Decimal('3000000')
    if 'state' in payroll_fields:
        payroll_data['state'] = '초안'
    elif 'status' in payroll_fields:
        payroll_data['status'] = '초안'

    payroll = Payroll.objects.create(**payroll_data)
    log(PASS, 'HR', f'급여 생성: {getattr(payroll, "payroll_number", payroll.pk)}')

    # 확정 전환 → FI 인건비전표
    if 'state' in payroll_fields:
        payroll.state = '확정'
    elif 'status' in payroll_fields:
        payroll.status = '확정'
    payroll.save()
    log(PASS, 'HR', '급여 확정 전환')

    pay_num = getattr(payroll, 'payroll_number', str(payroll.pk))
    fi_hr = AccountMove.objects.filter(company=company, move_number=f'AUTO-HR-{pay_num}').first()
    if fi_hr:
        log(PASS, 'HR→FI', f'인건비전표 자동생성: {fi_hr.move_number} / {fi_hr.total_debit:,.0f}원')
    else:
        log(FAIL, 'HR→FI', f'인건비전표 없음 (move_number=AUTO-HR-{pay_num})')

except Exception as e:
    log(FAIL, 'HR→FI', f'오류: {e}')
    traceback.print_exc()

# ─── 9. TM 운송 완료 → FI 운반비전표 ────────────────────────────
section('9. TM 운송완료 → FI 운반비전표 테스트')
try:
    from scm_tm.models import Carrier, TransportOrder
    carrier, _ = Carrier.objects.get_or_create(
        company=company, name='더미운송사',
        defaults={'contact': '박운송', 'phone': '02-9999-0000', 'status': '활성'}
    )
    log(PASS, 'TM', f'운송사: {carrier.name}')

    tm_fields = {f.name for f in TransportOrder._meta.get_fields()}
    tm_data = {
        'company': company,
        'transport_number': f'TM-{UID}',
        'carrier': carrier,
        'status': '운송중',
    }
    for field, val in [
        ('origin', '서울'), ('destination', '부산'),
        ('weight_kg', Decimal('500')), ('volume_cbm', Decimal('2.5')),
        ('freight_cost', Decimal('0')),
    ]:
        if field in tm_fields:
            tm_data[field] = val

    tm_order = TransportOrder.objects.create(**tm_data)
    log(PASS, 'TM', f'운송오더 생성: {tm_order.transport_number}')

    tm_order.status = '완료'
    tm_order.save()
    log(PASS, 'TM', '운송오더 완료 전환')

    fi_tm = AccountMove.objects.filter(
        company=company, move_number__startswith=f'AUTO-TM-{tm_order.transport_number}'
    ).first()
    if not fi_tm:
        fi_tm = AccountMove.objects.filter(company=company, ref=tm_order.transport_number).first()
    if fi_tm:
        log(PASS, 'TM→FI', f'운반비전표 자동생성: {fi_tm.move_number}')
    else:
        log(WARN, 'TM→FI', '운반비전표 없음 (FreightRate 등록 필요할 수 있음)')

except Exception as e:
    log(FAIL, 'TM→FI', f'오류: {e}')
    traceback.print_exc()

# ─── 10. WM 재고 min_stock 이하 → MM 자동발주 ─────────────────
section('10. WM 재고 min_stock 이하 → MM 자동발주 테스트')
try:
    inv_test, _ = Inventory.objects.get_or_create(
        company=company,
        item_code=f'AUTO-{UID}',
        warehouse=wh,
        lot_number='',
        defaults={
            'item_name': '더미자동발주품목',
            'stock_qty': 100,
            'system_qty': 100,
            'min_stock': 10,
        }
    )
    log(PASS, 'WM', f'재고 생성: {inv_test.item_code} stock={inv_test.stock_qty} min={inv_test.min_stock}')

    # 재고를 min_stock 이하로 낮춤
    inv_test.stock_qty = 3
    inv_test.save()
    log(PASS, 'WM', f'재고 → {inv_test.stock_qty} (min_stock={inv_test.min_stock} 이하)')

    today_str = TODAY.strftime('%Y-%m-%d')
    auto_po = PurchaseOrder.objects.filter(
        company=company,
        po_number=f'AUTO-PO-{inv_test.item_code}-{today_str}'
    ).first()
    if auto_po:
        log(PASS, 'WM→MM', f'자동발주서 생성: {auto_po.po_number} / qty={auto_po.quantity}')
    else:
        log(FAIL, 'WM→MM', f'자동발주서 없음 (po_number=AUTO-PO-{inv_test.item_code}-{today_str})')

except Exception as e:
    log(FAIL, 'WM→MM', f'오류: {e}')
    traceback.print_exc()

# ─── 11. WI 작업지시 완료 → PP produced_qty ─────────────────────
section('11. WI 작업지시 완료 → PP produced_qty 누계 테스트')
try:
    from scm_wi.models import WorkInstruction
    wi_fields = {f.name for f in WorkInstruction._meta.get_fields()}
    wi_data = {
        'company': company,
        'instruction_number': f'WI-{UID}',
        'title': '더미작업지시',
        'status': '대기',
        'work_center': pp_order.work_center if pp_order else '조립라인1',
    }
    for field, val in [
        ('planned_qty', 5), ('actual_qty', 5),
        ('planned_date', TODAY), ('start_date', TODAY),
    ]:
        if field in wi_fields:
            wi_data[field] = val

    wi = WorkInstruction.objects.create(**wi_data)
    log(PASS, 'WI', f'작업지시 생성: {wi.instruction_number} / work_center={wi.work_center}')

    # PP 오더 초기 produced_qty
    if pp_order:
        pp_order.refresh_from_db()
        # 완료된 오더이므로 새 오더로 테스트
        pp_order2, _ = ProductionOrder.objects.get_or_create(
            company=company, order_number=f'PP2-{UID}',
            defaults={
                'product_name': '더미완제품2', 'planned_qty': 10, 'produced_qty': 0,
                'status': '생산중', 'work_center': wi.work_center,
            }
        )
        qty_before = pp_order2.produced_qty
        log(PASS, 'PP', f'테스트용 오더: {pp_order2.order_number} / produced_qty={qty_before}')

    wi.status = '완료'
    wi.save()
    log(PASS, 'WI', '작업지시 완료 전환')

    if pp_order:
        pp_order2.refresh_from_db()
        qty_after = pp_order2.produced_qty
        if qty_after > qty_before:
            log(PASS, 'WI→PP', f'produced_qty 누계: {qty_before} → {qty_after}')
        else:
            log(WARN, 'WI→PP', f'produced_qty 미변경={qty_after} (work_center 매칭 확인)')

except Exception as e:
    log(FAIL, 'WI→PP', f'오류: {e}')
    traceback.print_exc()

# ─── 12. Workflow 결재 → 문서 상태 전환 ──────────────────────────
section('12. Workflow 결재승인 → 문서상태 자동전환 테스트')
try:
    from scm_workflow.models import ApprovalTemplate, ApprovalStep, ApprovalRequest
    from django.contrib.contenttypes.models import ContentType

    tmpl, _ = ApprovalTemplate.objects.get_or_create(
        company=company, name='더미결재템플릿',
        defaults={'description': '테스트용', 'is_active': True}
    )
    ApprovalStep.objects.get_or_create(
        template=tmpl, step_no=1,
        defaults={'approver_role': '', 'action': 'approve', 'is_final': True}
    )

    # PurchaseOrder에 대한 결재 요청
    test_po = PurchaseOrder.objects.filter(company=company).last()
    if test_po:
        ct = ContentType.objects.get_for_model(test_po)
        req_fields = {f.name for f in ApprovalRequest._meta.get_fields()}
        req_data = {
            'company': company, 'template': tmpl,
            'requester': user, 'title': f'발주 결재 요청 {test_po.po_number}',
            'status': 'pending', 'current_step': 1,
            'content_type': ct, 'object_id': test_po.pk,
        }
        # optional fields
        for f in ['description', 'note']:
            if f in req_fields:
                req_data[f] = '더미 결재 테스트'

        req = ApprovalRequest.objects.create(**req_data)
        log(PASS, 'WF', f'결재요청 생성: {req.title}')

        old_status = test_po.status
        req.status = 'approved'
        req.save()
        log(PASS, 'WF', '결재 승인 전환')

        test_po.refresh_from_db()
        if test_po.status != old_status:
            log(PASS, 'WF→MM', f'문서상태 자동전환: {old_status} → {test_po.status}')
        else:
            log(WARN, 'WF→MM', f'문서상태 미변경 (현재={test_po.status}, ContentType 매핑 확인)')
    else:
        log(WARN, 'WF', '테스트할 발주서 없음')

except Exception as e:
    log(FAIL, 'WF', f'오류: {e}')
    traceback.print_exc()

# ─── 최종 요약 ────────────────────────────────────────────────
section('=== 테스트 결과 요약 ===')
passed = [r for r in results if PASS in r]
warned = [r for r in results if WARN in r]
failed = [r for r in results if FAIL in r]
print(f'\n  통과: {len(passed)}건  경고: {len(warned)}건  실패: {len(failed)}건\n')
if failed:
    print('  [실패 목록]')
    for r in failed: print(r)
if warned:
    print('\n  [경고 목록]')
    for r in warned: print(r)

print('\n  [생성된 FI 전표 목록]')
from scm_fi.models import AccountMove
for m in AccountMove.objects.filter(company=company, move_number__startswith='AUTO-').order_by('-id')[:10]:
    print(f'    {m.move_number} | {m.move_type} | {m.total_debit:,.0f}원')
