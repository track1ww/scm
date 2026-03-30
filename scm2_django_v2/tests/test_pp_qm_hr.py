"""
P4-3 자동화 테스트 — PP·QM·HR·크로스모듈·PDF 엔드포인트 확장

커버리지:
  PP  (9)   BOM, BomLine, ProductionOrder CRUD, MRP, 완료→WM IN 신호, 완료→FI 생산원가
  QM  (8)   InspectionPlan, Result, pass_rate, DefectRecord, CorrectiveAction, CAPA 흐름
  HR  (6)   Department, Employee, Payroll, Attendance, Leave, 급여명세서 PDF
  Cross (4) PO 입고→FI 매입전표, SO 배송→FI 매출전표+COGS, PP 완료→FI 생산원가
  Reports(3) 재무제표 PDF(income/balance), 급여명세서 PDF
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from scm_accounts.models import Company, User
from scm_mm.models import Supplier, Material, PurchaseOrder
from scm_sd.models import Customer, SalesOrder
from scm_pp.models import BillOfMaterial, BomLine, ProductionOrder
from scm_qm.models import InspectionPlan, InspectionResult, DefectRecord, CorrectiveAction
from scm_hr.models import Department, Employee, Payroll
from scm_fi.models import AccountMove, Account
from scm_wm.models import Warehouse


# ──────────────────────────────────────────────
# 공통 베이스
# ──────────────────────────────────────────────

class BaseAPITestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_code='P4TEST', company_name='P4테스트주식회사',
        )
        self.user = User.objects.create_user(
            username='p4user', email='p4@test.com', password='testpass123',
            name='P4테스터', company=self.company,
        )
        self.client = APIClient()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'p4@test.com', 'password': 'testpass123'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')


# ──────────────────────────────────────────────
# PP — 생산관리
# ──────────────────────────────────────────────

class PPTests(BaseAPITestCase):

    def test_pp_01_create_bom(self):
        """BOM 생성."""
        resp = self.client.post('/api/pp/boms/', {
            'bom_code': 'BOM-001',
            'product_name': '완제품A',
            'version': '1.0',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['bom_code'], 'BOM-001')

    def test_pp_02_create_bom_line(self):
        """BOM 라인 추가."""
        bom = BillOfMaterial.objects.create(
            company=self.company, bom_code='BOM-L001', product_name='완제품B',
        )
        resp = self.client.post('/api/pp/bom-lines/', {
            'bom': bom.pk,
            'material_code': 'MTL-RAW-01',
            'material_name': '원재료A',
            'quantity': '5.000',
            'unit': 'KG',
            'scrap_rate': '2.00',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['material_code'], 'MTL-RAW-01')

    def test_pp_03_create_production_order(self):
        """생산오더 생성."""
        bom = BillOfMaterial.objects.create(
            company=self.company, bom_code='BOM-PO001', product_name='완제품C',
        )
        resp = self.client.post('/api/pp/production-orders/', {
            'order_number': 'PP-2024-001',
            'bom': bom.pk,
            'product_name': '완제품C',
            'planned_qty': 100,
            'planned_start': '2024-06-01',
            'planned_end': '2024-06-10',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['status'], '계획')

    def test_pp_04_production_order_completion_rate(self):
        """완료율 계산."""
        po = ProductionOrder.objects.create(
            company=self.company, order_number='PP-RATE-001',
            product_name='제품', planned_qty=100, produced_qty=75,
        )
        self.assertEqual(po.completion_rate, 75.0)

    def test_pp_05_update_production_order_status(self):
        """생산오더 상태 변경: 계획 → 생산중."""
        po = ProductionOrder.objects.create(
            company=self.company, order_number='PP-STAT-001',
            product_name='제품', planned_qty=50,
        )
        resp = self.client.patch(f'/api/pp/production-orders/{po.pk}/', {
            'status': '생산중',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], '생산중')

    def test_pp_06_list_boms_scoped(self):
        """타 회사 BOM 미포함."""
        other = Company.objects.create(company_code='OTHER-PP', company_name='타사')
        BillOfMaterial.objects.create(company=other, bom_code='BOM-OTHER', product_name='타사제품')
        BillOfMaterial.objects.create(company=self.company, bom_code='BOM-MINE', product_name='우리제품')

        resp = self.client.get('/api/pp/boms/')
        codes = [b['bom_code'] for b in resp.data['results']]
        self.assertIn('BOM-MINE', codes)
        self.assertNotIn('BOM-OTHER', codes)

    def test_pp_07_production_order_complete_triggers_wm(self):
        """생산오더 완료 → WM 재고 IN 신호 발생."""
        from scm_wm.models import StockMovement
        po = ProductionOrder.objects.create(
            company=self.company, order_number='PP-WM-001',
            product_name='PP자동재고품', planned_qty=10,
        )
        initial_movements = StockMovement.objects.filter(
            company=self.company, reference_document='PP-WM-001',
        ).count()

        po.status = '완료'
        po.save()

        new_movements = StockMovement.objects.filter(
            company=self.company, reference_document='PP-WM-001',
        ).count()
        self.assertGreater(new_movements, initial_movements)

    def test_pp_08_mrp_list(self):
        """MRP 실행 이력 목록 조회."""
        resp = self.client.get('/api/pp/mrp-plans/')
        self.assertEqual(resp.status_code, 200)

    def test_pp_09_bom_line_scrap_rate(self):
        """scrap_rate 있을 때 DB 저장 확인."""
        bom = BillOfMaterial.objects.create(
            company=self.company, bom_code='BOM-SCRAP', product_name='스크랩테스트',
        )
        line = BomLine.objects.create(
            bom=bom, material_code='SC-001', material_name='스크랩자재',
            quantity=Decimal('10.000'), scrap_rate=Decimal('5.00'),
        )
        self.assertEqual(line.scrap_rate, Decimal('5.00'))


# ──────────────────────────────────────────────
# QM — 품질관리
# ──────────────────────────────────────────────

class QMTests(BaseAPITestCase):

    def test_qm_01_create_inspection_plan(self):
        """검사계획 생성."""
        resp = self.client.post('/api/qm/inspection-plans/', {
            'plan_code': 'QP-001',
            'plan_name': '수입검사기준',
            'inspection_type': '수입검사',
            'target_item': '원재료A',
            'criteria': '외관 검사, 치수 측정',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['plan_code'], 'QP-001')

    def test_qm_02_create_inspection_result(self):
        """검사 결과 등록."""
        plan = InspectionPlan.objects.create(
            company=self.company, plan_code='QP-R001', plan_name='검사계획A',
        )
        resp = self.client.post('/api/qm/inspection-results/', {
            'result_number': 'QR-2024-001',
            'plan': plan.pk,
            'item_name': '원재료A',
            'lot_number': 'LOT-001',
            'inspected_qty': 100,
            'passed_qty': 95,
            'failed_qty': 5,
            'result': '합격',
            'inspector': '김검사',
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_qm_03_pass_rate_calculation(self):
        """pass_rate 프로퍼티 검증."""
        plan = InspectionPlan.objects.create(
            company=self.company, plan_code='QP-RATE', plan_name='합격률테스트',
        )
        result = InspectionResult.objects.create(
            company=self.company, result_number='QR-RATE-001',
            plan=plan, item_name='테스트품목',
            inspected_qty=200, passed_qty=190, failed_qty=10,
        )
        self.assertEqual(result.pass_rate, 95.0)

    def test_qm_04_pass_rate_zero_when_no_inspections(self):
        """검사수량 0일 때 pass_rate=0 (ZeroDivision 방지)."""
        result = InspectionResult.objects.create(
            company=self.company, result_number='QR-ZERO',
            item_name='빈품목', inspected_qty=0, passed_qty=0, failed_qty=0,
        )
        self.assertEqual(result.pass_rate, 0)

    def test_qm_05_create_defect_record(self):
        """불량 기록 등록."""
        resp = self.client.post('/api/qm/defect-reports/', {
            'defect_number': 'DEF-2024-001',
            'item_name': '완제품A',
            'defect_type': '치수 불량',
            'severity': '보통',
            'quantity': 3,
            'description': '규격 초과 0.5mm',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['severity'], '보통')

    def test_qm_06_create_corrective_action(self):
        """시정조치(CAPA) 등록."""
        defect = DefectRecord.objects.create(
            company=self.company, defect_number='DEF-CA-001',
            item_name='원재료', defect_type='외관 불량',
        )
        resp = self.client.post('/api/qm/corrective-actions/', {
            'capa_number': 'CAPA-2024-001',
            'defect': defect.pk,
            'title': '외관 불량 재발방지 조치',
            'root_cause': '금형 마모',
            'action_plan': '금형 교체 및 주기적 점검',
            'responsible': '이엔지니어',
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_qm_07_inspection_list_scoped(self):
        """타 회사 검사결과 미포함."""
        other = Company.objects.create(company_code='OTHER-QM', company_name='타품질사')
        InspectionResult.objects.create(
            company=other, result_number='QR-OTHER', item_name='타사품목',
            inspected_qty=10, passed_qty=10, failed_qty=0,
        )
        resp = self.client.get('/api/qm/inspection-results/')
        numbers = [r['result_number'] for r in resp.data['results']]
        self.assertNotIn('QR-OTHER', numbers)

    def test_qm_08_defect_severity_choices(self):
        """불량 심각도 유효값 검증."""
        d = DefectRecord.objects.create(
            company=self.company, defect_number='DEF-SEV',
            item_name='테스트', defect_type='크랙',
            severity='치명',
        )
        self.assertEqual(d.severity, '치명')


# ──────────────────────────────────────────────
# HR — 인사관리
# ──────────────────────────────────────────────

class HRExtendedTests(BaseAPITestCase):

    def _make_dept(self, code='DEPT-P4', name='P4팀'):
        return Department.objects.create(
            company=self.company, dept_code=code, dept_name=name,
        )

    def _make_emp(self, code='EMP-P4-001', dept=None):
        if dept is None:
            dept = self._make_dept()
        return Employee.objects.create(
            company=self.company, emp_code=code, name='P4직원',
            dept=dept, hire_date=datetime.date(2022, 1, 1),
        )

    def test_hr_01_create_payroll(self):
        """급여 레코드 생성."""
        emp = self._make_emp()
        resp = self.client.post('/api/hr/payrolls/', {
            'payroll_number': 'PAY-2024-001',
            'employee': emp.pk,
            'pay_year': 2024,
            'pay_month': 6,
            'base_salary': '4000000.00',
            'overtime_pay': '200000.00',
            'bonus': '0.00',
            'gross_pay': '4200000.00',
            'national_pension': '180000.00',
            'health_insurance': '140000.00',
            'employment_insurance': '33600.00',
            'income_tax': '126000.00',
            'total_deduction': '479600.00',
            'net_pay': '3720400.00',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['payroll_number'], 'PAY-2024-001')

    def test_hr_02_payroll_state_default_draft(self):
        """급여 기본 상태는 DRAFT."""
        emp = self._make_emp(code='EMP-P4-D')
        payroll = Payroll.objects.create(
            company=self.company, payroll_number='PAY-DRAFT',
            employee=emp, pay_year=2024, pay_month=5,
            base_salary=Decimal('3000000'), gross_pay=Decimal('3000000'),
            net_pay=Decimal('2600000'),
        )
        self.assertEqual(payroll.state, 'DRAFT')

    def test_hr_03_create_attendance(self):
        """근태 기록 생성."""
        emp = self._make_emp(code='EMP-P4-ATT')
        resp = self.client.post('/api/hr/attendances/', {
            'employee': emp.pk,
            'work_date': '2024-06-03',
            'check_in': '09:00:00',
            'check_out': '18:00:00',
            'work_type': 'normal',
            'overtime_hours': '0.0',
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_hr_04_create_leave_request(self):
        """휴가 신청."""
        emp = self._make_emp(code='EMP-P4-LV')
        resp = self.client.post('/api/hr/leaves/', {
            'employee': emp.pk,
            'leave_type': '연차',
            'start_date': '2024-07-01',
            'end_date': '2024-07-02',
            'reason': '개인 사유',
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_hr_05_employee_list_scoped(self):
        """타 회사 직원 미포함."""
        other = Company.objects.create(company_code='OTHER-HR', company_name='타인사사')
        other_dept = Department.objects.create(
            company=other, dept_code='DEPT-OTH', dept_name='타사팀',
        )
        Employee.objects.create(
            company=other, emp_code='EMP-OTH', name='타사직원',
            dept=other_dept, hire_date=datetime.date(2020, 1, 1),
        )
        resp = self.client.get('/api/hr/employees/')
        codes = [e['emp_code'] for e in resp.data['results']]
        self.assertNotIn('EMP-OTH', codes)

    def test_hr_06_payroll_pdf_endpoint(self):
        """급여명세서 PDF 엔드포인트 — 200 + PDF content-type."""
        emp = self._make_emp(code='EMP-P4-PDF')
        payroll = Payroll.objects.create(
            company=self.company, payroll_number='PAY-PDF-001',
            employee=emp, pay_year=2024, pay_month=6,
            base_salary=Decimal('4000000'), gross_pay=Decimal('4200000'),
            net_pay=Decimal('3720400'),
        )
        resp = self.client.get(f'/api/reports/payroll/{payroll.pk}/pdf/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')


# ──────────────────────────────────────────────
# Cross-module — FI 자동전기
# ──────────────────────────────────────────────

class CrossModuleFITests(BaseAPITestCase):

    def test_cross_01_po_receipt_creates_fi_journal(self):
        """PO 입고완료 → FI 매입전표(AUTO-PO-*) 자동 생성."""
        supplier = Supplier.objects.create(company=self.company, name='크로스공급사')
        po = PurchaseOrder.objects.create(
            company=self.company, po_number='CROSS-PO-001',
            supplier=supplier, item_name='크로스품목',
            quantity=100, unit_price=Decimal('5000.00'),
        )
        initial = AccountMove.objects.filter(
            company=self.company, move_number__startswith='AUTO-PO-',
        ).count()

        po.status = '입고완료'
        po.save()

        new_count = AccountMove.objects.filter(
            company=self.company, move_number__startswith='AUTO-PO-',
        ).count()
        self.assertGreater(new_count, initial)

    def test_cross_02_po_fi_journal_amount_correct(self):
        """PO 입고 FI 전표 금액 = qty × unit_price."""
        supplier = Supplier.objects.create(company=self.company, name='금액공급사')
        po = PurchaseOrder.objects.create(
            company=self.company, po_number='CROSS-AMT-001',
            supplier=supplier, item_name='금액품목',
            quantity=10, unit_price=Decimal('8000.00'),
        )
        po.status = '입고완료'
        po.save()

        move = AccountMove.objects.filter(
            company=self.company,
            move_number=f'AUTO-PO-{po.po_number}',
        ).first()
        self.assertIsNotNone(move)
        # total_debit = total_credit = 10 * 8000 = 80000
        self.assertAlmostEqual(float(move.total_debit), 80000.0, places=1)
        self.assertAlmostEqual(float(move.total_credit), 80000.0, places=1)

    def test_cross_03_so_delivery_creates_fi_journal(self):
        """SO 배송완료 → FI 매출전표(AUTO-SO-*) 자동 생성 (매출 + COGS 4라인)."""
        from scm_fi.models import AccountMoveLine
        customer = Customer.objects.create(
            company=self.company, customer_code='CROSS-CUST', customer_name='크로스고객',
        )
        so = SalesOrder.objects.create(
            company=self.company, order_number='CROSS-SO-001',
            customer=customer, customer_name='크로스고객',
            item_name='크로스출하품목', quantity=20,
            unit_price=Decimal('3000.00'),
        )
        initial = AccountMove.objects.filter(
            company=self.company, move_number__startswith='AUTO-SO-',
        ).count()

        so.status = '배송완료'
        so.save()

        new_count = AccountMove.objects.filter(
            company=self.company, move_number__startswith='AUTO-SO-',
        ).count()
        self.assertGreater(new_count, initial)

        # 매출+COGS → 4개 라인 (AR, Revenue, COGS, Inventory)
        move = AccountMove.objects.filter(
            company=self.company,
            move_number=f'AUTO-SO-{so.order_number}',
        ).first()
        self.assertIsNotNone(move)
        line_count = AccountMoveLine.objects.filter(move=move).count()
        self.assertEqual(line_count, 4)

    def test_cross_04_pp_complete_creates_fi_journal(self):
        """PP 생산완료 + BOM 자재단가 있을 때 FI 생산원가전표 자동 생성."""
        # 자재에 단가이력 생성
        mat = Material.objects.create(
            company=self.company, material_code='MTL-CROSS',
            material_name='크로스원재료',
        )
        from scm_mm.models import MaterialPriceHistory
        MaterialPriceHistory.objects.create(
            company=self.company, material=mat,
            supplier=None, unit_price=Decimal('2000.00'),
            effective_date=datetime.date(2024, 1, 1),
        )

        bom = BillOfMaterial.objects.create(
            company=self.company, bom_code='BOM-CROSS', product_name='크로스완제품',
        )
        BomLine.objects.create(
            bom=bom, material_code='MTL-CROSS',
            material_name='크로스원재료',
            quantity=Decimal('5.000'),
        )
        pp = ProductionOrder.objects.create(
            company=self.company, order_number='PP-CROSS-001',
            bom=bom, product_name='크로스완제품', planned_qty=10,
        )

        initial = AccountMove.objects.filter(
            company=self.company, move_number__startswith='AUTO-PP-',
        ).count()

        pp.status = '완료'
        pp.save()

        new_count = AccountMove.objects.filter(
            company=self.company, move_number__startswith='AUTO-PP-',
        ).count()
        self.assertGreater(new_count, initial)


# ──────────────────────────────────────────────
# Reports — PDF 엔드포인트
# ──────────────────────────────────────────────

class ReportsPDFTests(BaseAPITestCase):

    def _setup_fi_data(self, year=2024, month=6):
        """손익계산서 테스트용 전표 데이터 생성."""
        from scm_fi.models import Account, AccountMove, AccountMoveLine
        rev = Account.objects.create(
            company=self.company, code='4001', name='매출', account_type='REVENUE',
        )
        exp = Account.objects.create(
            company=self.company, code='5001', name='급여비용', account_type='EXPENSE',
        )
        move = AccountMove.objects.create(
            company=self.company, move_number='JE-PDF-001', move_type='ENTRY',
            posting_date=datetime.date(year, month, 15), state='POSTED',
        )
        AccountMoveLine.objects.create(move=move, account=rev, credit=Decimal('5000000'))
        AccountMoveLine.objects.create(move=move, account=exp, debit=Decimal('2000000'))

    def test_rpt_01_income_statement_pdf(self):
        """손익계산서 PDF — 200 + application/pdf."""
        self._setup_fi_data()
        resp = self.client.get(
            '/api/reports/financial-statement/pdf/?type=income&year=2024&month=6'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_rpt_02_balance_sheet_pdf(self):
        """대차대조표 PDF — 200 + application/pdf."""
        from scm_fi.models import Account, AccountMove, AccountMoveLine
        asset = Account.objects.create(
            company=self.company, code='1001', name='현금', account_type='ASSET',
        )
        liab = Account.objects.create(
            company=self.company, code='2001', name='단기차입금', account_type='LIABILITY',
        )
        move = AccountMove.objects.create(
            company=self.company, move_number='JE-BS-001', move_type='ENTRY',
            posting_date=datetime.date(2024, 6, 30), state='POSTED',
        )
        AccountMoveLine.objects.create(move=move, account=asset, debit=Decimal('1000000'))
        AccountMoveLine.objects.create(move=move, account=liab, credit=Decimal('1000000'))

        resp = self.client.get(
            '/api/reports/financial-statement/pdf/?type=balance&year=2024&month=6'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_rpt_03_income_pdf_invalid_params(self):
        """잘못된 year 파라미터 → 400."""
        resp = self.client.get(
            '/api/reports/financial-statement/pdf/?type=income&year=INVALID&month=6'
        )
        self.assertEqual(resp.status_code, 400)
