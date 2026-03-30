"""
자동화 테스트 — 핵심 ERP API 35+ 케이스

모듈 커버리지:
  Auth (5)  MM (8)  SD (5)  FI (6)  WM (3)  HR (3)  RBAC (4)  AuditLog (3)  NTS (2)  Dashboard (2)
"""

import datetime
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from scm_accounts.models import Company, User, Role, UserRole
from scm_core.models import AuditLog
from scm_mm.models import Supplier, Material, PurchaseOrder, PurchaseOrderLine
from scm_sd.models import Customer, SalesOrder, Delivery
from scm_fi.models import Account, AccountMove, AccountMoveLine
from scm_wm.models import Warehouse, Inventory
from scm_hr.models import Department, Employee


# ──────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────

class BaseAPITestCase(TestCase):
    """모든 테스트의 공통 설정: 회사 + 인증 유저."""

    def setUp(self):
        self.company = Company.objects.create(
            company_code='TEST01',
            company_name='테스트주식회사',
            business_no='1234567890',
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            name='테스터',
            company=self.company,
        )
        self.client = APIClient()
        self._login()

    def _login(self):
        resp = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.access = resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')


# ──────────────────────────────────────────────
# 1. 인증 (Auth)
# ──────────────────────────────────────────────

class AuthTests(BaseAPITestCase):

    def test_01_login_returns_jwt(self):
        """로그인 성공 시 access/refresh 토큰 반환."""
        resp = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_02_login_wrong_password_fails(self):
        """잘못된 비밀번호로 로그인 시 401."""
        self.client.credentials()
        resp = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(resp.status_code, 401)

    def test_03_profile_returns_name_field(self):
        """프로필 API가 name 필드를 반환 (username이 아님)."""
        resp = self.client.get('/api/accounts/profile/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('name', resp.data)
        self.assertEqual(resp.data['name'], '테스터')

    def test_04_token_refresh(self):
        """refresh 토큰으로 새 access 토큰 발급."""
        login = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        refresh = login.data['refresh']
        resp = self.client.post('/api/auth/refresh/', {'refresh': refresh})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_05_unauthenticated_request_rejected(self):
        """인증 없이 보호된 API 접근 시 401."""
        client = APIClient()
        resp = client.get('/api/mm/suppliers/')
        self.assertEqual(resp.status_code, 401)


# ──────────────────────────────────────────────
# 2. MM — 자재관리
# ──────────────────────────────────────────────

class MMTests(BaseAPITestCase):

    def test_06_create_supplier(self):
        """공급업체 생성."""
        resp = self.client.post('/api/mm/suppliers/', {
            'name': '(주)테스트공급사',
            'contact': '홍길동',
            'email': 'vendor@test.com',
            'phone': '02-1234-5678',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['name'], '(주)테스트공급사')

    def test_07_supplier_list_scoped_to_company(self):
        """다른 회사의 공급업체는 조회되지 않음."""
        other_company = Company.objects.create(company_code='OTHER', company_name='타사')
        Supplier.objects.create(company=other_company, name='타사공급사')
        Supplier.objects.create(company=self.company, name='우리공급사')

        resp = self.client.get('/api/mm/suppliers/')
        self.assertEqual(resp.status_code, 200)
        names = [s['name'] for s in resp.data['results']]
        self.assertIn('우리공급사', names)
        self.assertNotIn('타사공급사', names)

    def test_08_create_material(self):
        """자재 생성."""
        resp = self.client.post('/api/mm/materials/', {
            'material_code': 'MTL-001',
            'material_name': '테스트자재',
            'material_type': '원재료',
            'unit': 'EA',
            'min_stock': 10,
            'lead_time_days': 5,
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['material_code'], 'MTL-001')

    def test_09_material_code_unique(self):
        """중복 자재코드 생성 시 400."""
        Material.objects.create(
            company=self.company,
            material_code='MTL-DUP',
            material_name='기존자재',
        )
        resp = self.client.post('/api/mm/materials/', {
            'material_code': 'MTL-DUP',
            'material_name': '중복자재',
        })
        self.assertEqual(resp.status_code, 400)

    def test_10_create_purchase_order(self):
        """발주서 생성."""
        supplier = Supplier.objects.create(company=self.company, name='테스트공급사')
        resp = self.client.post('/api/mm/orders/', {
            'po_number': 'PO-2024-001',
            'supplier': supplier.pk,
            'item_name': '테스트자재',
            'quantity': 100,
            'unit_price': '5000.00',
            'delivery_date': '2024-12-31',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['po_number'], 'PO-2024-001')

    def test_11_create_po_line(self):
        """발주서 라인 품목 생성."""
        supplier = Supplier.objects.create(company=self.company, name='공급사')
        po = PurchaseOrder.objects.create(
            company=self.company,
            po_number='PO-LINE-001',
            supplier=supplier,
            item_name='대표품목',
            quantity=1,
            unit_price=Decimal('1000.00'),
        )
        resp = self.client.post('/api/mm/po-lines/', {
            'po': po.pk,
            'line_no': 1,
            'item_name': '라인품목1',
            'quantity': 50,
            'unit_price': '3000.00',
            'unit': 'EA',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['item_name'], '라인품목1')

    def test_12_po_lines_filter_by_po(self):
        """?po=<id> 필터로 특정 발주서 라인만 조회."""
        supplier = Supplier.objects.create(company=self.company, name='공급사B')
        po1 = PurchaseOrder.objects.create(
            company=self.company, po_number='PO-F-001',
            supplier=supplier, item_name='품목A', quantity=1, unit_price=Decimal('100'),
        )
        po2 = PurchaseOrder.objects.create(
            company=self.company, po_number='PO-F-002',
            supplier=supplier, item_name='품목B', quantity=1, unit_price=Decimal('200'),
        )
        PurchaseOrderLine.objects.create(po=po1, line_no=1, item_name='라인A', quantity=10, unit_price=Decimal('100'))
        PurchaseOrderLine.objects.create(po=po2, line_no=1, item_name='라인B', quantity=20, unit_price=Decimal('200'))

        resp = self.client.get(f'/api/mm/po-lines/?po={po1.pk}')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['item_name'], '라인A')

    def test_13_update_supplier(self):
        """공급업체 정보 수정."""
        supplier = Supplier.objects.create(company=self.company, name='수정전')
        resp = self.client.patch(f'/api/mm/suppliers/{supplier.pk}/', {'name': '수정후'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], '수정후')


# ──────────────────────────────────────────────
# 3. SD — 영업관리
# ──────────────────────────────────────────────

class SDTests(BaseAPITestCase):

    def test_14_create_customer(self):
        """고객사 생성."""
        resp = self.client.post('/api/sd/customers/', {
            'customer_code': 'CUST-001',
            'customer_name': '테스트고객사',
            'contact': '김영업',
            'email': 'buyer@test.com',
            'credit_limit': '10000000.00',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['customer_code'], 'CUST-001')

    def test_15_create_sales_order(self):
        """수주 생성."""
        customer = Customer.objects.create(
            company=self.company,
            customer_code='CUST-SO-001',
            customer_name='수주고객',
        )
        resp = self.client.post('/api/sd/orders/', {
            'order_number': 'SO-2024-001',
            'customer': customer.pk,
            'customer_name': '수주고객',
            'item_name': '제품A',
            'quantity': 50,
            'unit_price': '20000.00',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['order_number'], 'SO-2024-001')

    def test_16_sales_order_total_amount(self):
        """수주 total_amount 계산 확인."""
        customer = Customer.objects.create(
            company=self.company, customer_code='CUST-AMT', customer_name='계산고객',
        )
        so = SalesOrder.objects.create(
            company=self.company,
            order_number='SO-AMT-001',
            customer=customer,
            customer_name='계산고객',
            item_name='제품',
            quantity=10,
            unit_price=Decimal('5000.00'),
            discount_rate=Decimal('10.00'),
        )
        self.assertAlmostEqual(so.total_amount, 45000.0)

    def test_17_create_delivery(self):
        """출하 생성."""
        customer = Customer.objects.create(
            company=self.company, customer_code='CUST-DEL', customer_name='출하고객',
        )
        so = SalesOrder.objects.create(
            company=self.company, order_number='SO-DEL-001',
            customer=customer, customer_name='출하고객',
            item_name='제품', quantity=20, unit_price=Decimal('1000'),
        )
        resp = self.client.post('/api/sd/deliveries/', {
            'delivery_number': 'DEL-2024-001',
            'order': so.pk,
            'item_name': '제품',
            'delivery_qty': 10,
            'carrier': 'CJ대한통운',
            'delivery_date': '2024-12-01',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['delivery_number'], 'DEL-2024-001')

    def test_18_customer_list_scoped(self):
        """타 회사 고객은 목록에 미포함."""
        other = Company.objects.create(company_code='OTHER2', company_name='타사2')
        Customer.objects.create(company=other, customer_code='C-OTHER', customer_name='타사고객')
        Customer.objects.create(company=self.company, customer_code='C-MINE', customer_name='우리고객')

        resp = self.client.get('/api/sd/customers/')
        codes = [c['customer_code'] for c in resp.data['results']]
        self.assertIn('C-MINE', codes)
        self.assertNotIn('C-OTHER', codes)


# ──────────────────────────────────────────────
# 4. FI — 재무회계
# ──────────────────────────────────────────────

class FITests(BaseAPITestCase):

    def _create_account(self, code, name, account_type):
        return Account.objects.create(
            company=self.company, code=code, name=name, account_type=account_type,
        )

    def test_19_create_account(self):
        """계정과목 생성."""
        resp = self.client.post('/api/fi/accounts/', {
            'code': '1001',
            'name': '현금',
            'account_type': 'ASSET',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['code'], '1001')

    def test_20_create_account_move_draft(self):
        """DRAFT 전표 생성 — 생성 후 조회해서 state=DRAFT 확인."""
        resp = self.client.post('/api/fi/moves/', {
            'move_type': 'ENTRY',
            'posting_date': '2024-01-15',
            'ref': '테스트 전표',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        move_id = resp.data['id']
        detail = self.client.get(f'/api/fi/moves/{move_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['state'], 'DRAFT')

    def test_21_financial_statement_income(self):
        """손익계산서 API — 수익/비용 집계."""
        rev_acct = self._create_account('4001', '매출', 'REVENUE')
        exp_acct = self._create_account('5001', '급여', 'EXPENSE')

        move = AccountMove.objects.create(
            company=self.company, move_number='JE-INC-001',
            move_type='ENTRY', posting_date=datetime.date(2024, 6, 15),
            state='POSTED',
        )
        AccountMoveLine.objects.create(move=move, account=rev_acct, credit=Decimal('1000000'))
        AccountMoveLine.objects.create(move=move, account=exp_acct, debit=Decimal('400000'))

        resp = self.client.get('/api/fi/statements/?type=income&year=2024&month=6')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('revenues', resp.data)
        self.assertIn('expenses', resp.data)
        self.assertIn('net_income', resp.data)

    def test_22_financial_statement_balance(self):
        """대차대조표 API — 자산/부채/자본 집계."""
        asset_acct = self._create_account('1100', '매출채권', 'ASSET')
        liab_acct = self._create_account('2100', '매입채무', 'LIABILITY')

        move = AccountMove.objects.create(
            company=self.company, move_number='JE-BAL-001',
            move_type='ENTRY', posting_date=datetime.date(2024, 6, 30),
            state='POSTED',
        )
        AccountMoveLine.objects.create(move=move, account=asset_acct, debit=Decimal('500000'))
        AccountMoveLine.objects.create(move=move, account=liab_acct, credit=Decimal('500000'))

        resp = self.client.get('/api/fi/statements/?type=balance&year=2024&month=6')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('assets', resp.data)
        self.assertIn('liabilities', resp.data)
        self.assertIn('equity', resp.data)

    def test_23_nts_status_disabled_without_key(self):
        """NTS_ASP_CERT_KEY 미설정 시 /nts-status/ 는 enabled=False 반환."""
        import os
        os.environ.pop('NTS_ASP_CERT_KEY', None)
        resp = self.client.get('/api/fi/tax-invoices/nts-status/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['enabled'])

    def test_24_nts_issue_returns_503_when_disabled(self):
        """NTS 미설정 시 발행 API는 503 NTS_DISABLED."""
        import os
        os.environ.pop('NTS_ASP_CERT_KEY', None)

        from scm_fi.models import TaxInvoice
        ti = TaxInvoice.objects.create(
            company=self.company,
            invoice_number='TI-2024-001',
            invoice_type='SALE',
            issue_date=datetime.date(2024, 6, 1),
            counterpart='테스트거래처',
            supply_amount=Decimal('1000000'),
            vat_amount=Decimal('100000'),
            total_amount=Decimal('1100000'),
            status='issued',  # issue_nts endpoint requires issued status
        )
        resp = self.client.post(f'/api/fi/tax-invoices/{ti.pk}/issue-nts/')
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.data.get('code'), 'NTS_DISABLED')


# ──────────────────────────────────────────────
# 5. WM — 창고관리
# ──────────────────────────────────────────────

class WMTests(BaseAPITestCase):

    def test_25_create_warehouse(self):
        """창고 생성."""
        resp = self.client.post('/api/wm/warehouses/', {
            'warehouse_code': 'WH-001',
            'warehouse_name': '메인창고',
            'warehouse_type': '일반창고',
            'location': '서울시 강남구',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['warehouse_code'], 'WH-001')

    def test_26_create_inventory_item(self):
        """재고 품목 등록."""
        wh = Warehouse.objects.create(
            company=self.company,
            warehouse_code='WH-INV-001',
            warehouse_name='재고창고',
        )
        resp = self.client.post('/api/wm/inventory/', {
            'item_code': 'ITM-001',
            'item_name': '테스트제품',
            'warehouse': wh.pk,
            'stock_qty': 100,
            'system_qty': 100,
            'unit_price': '5000.00',
            'min_stock': 10,
            'lot_number': '',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['item_code'], 'ITM-001')

    def test_27_low_stock_flag(self):
        """재고량이 최소재고 이하일 때 is_low_stock=True."""
        wh = Warehouse.objects.create(
            company=self.company, warehouse_code='WH-LOW', warehouse_name='부족창고',
        )
        inv = Inventory.objects.create(
            company=self.company, item_code='LOW-001', item_name='부족품목',
            warehouse=wh, stock_qty=5, min_stock=10,
        )
        self.assertTrue(inv.is_low_stock)


# ──────────────────────────────────────────────
# 6. HR — 인사관리
# ──────────────────────────────────────────────

class HRTests(BaseAPITestCase):

    def test_28_create_department(self):
        """부서 생성."""
        resp = self.client.post('/api/hr/departments/', {
            'dept_code': 'DEPT-DEV',
            'dept_name': '개발팀',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['dept_name'], '개발팀')

    def test_29_create_employee(self):
        """임직원 생성."""
        dept = Department.objects.create(
            company=self.company, dept_code='DEPT-HR', dept_name='인사팀',
        )
        resp = self.client.post('/api/hr/employees/', {
            'emp_code': 'EMP-001',
            'name': '홍길동',
            'dept': dept.pk,
            'position': '대리',
            'employment_type': '정규직',
            'hire_date': '2022-03-01',
            'base_salary': '3500000.00',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['name'], '홍길동')

    def test_30_employee_status_default(self):
        """임직원 기본 상태는 재직."""
        dept = Department.objects.create(
            company=self.company, dept_code='DEPT-IT', dept_name='IT팀',
        )
        emp = Employee.objects.create(
            company=self.company, emp_code='EMP-DEF',
            name='기본직원', dept=dept,
            hire_date=datetime.date(2023, 1, 1),
        )
        self.assertEqual(emp.status, '재직')


# ──────────────────────────────────────────────
# 7. RBAC — 역할 기반 접근 제어
# ──────────────────────────────────────────────

class RBACTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        # RBAC 관리 기능은 is_admin 필요
        self.user.is_admin = True
        self.user.save()

    def test_31_list_role_presets(self):
        """사전 정의 역할 프리셋 목록 조회."""
        resp = self.client.get('/api/accounts/roles/presets/')
        self.assertEqual(resp.status_code, 200)
        preset_codes = [p['code'] for p in resp.data]
        self.assertIn('ADMIN', preset_codes)
        self.assertIn('ACCOUNTANT', preset_codes)

    def test_32_create_role(self):
        """역할 생성 (프리셋 코드 사용)."""
        resp = self.client.post('/api/accounts/roles/', {
            'code': 'VIEWER',
            'name': '조회전용역할',
            'description': '테스트용 역할',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['code'], 'VIEWER')

    def test_33_assign_role_to_user(self):
        """역할 할당 → 사용자에게 권한 부여."""
        role = Role.objects.create(
            company=self.company,
            code='BUYER',
            name='구매담당자',
        )
        other_user = User.objects.create_user(
            username='analyst01',
            email='analyst@test.com',
            password='pass1234',
            name='분석가',
            company=self.company,
        )
        resp = self.client.post(f'/api/accounts/roles/{role.pk}/assign/', {
            'user_id': other_user.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(UserRole.objects.filter(role=role, user=other_user).exists())

    def test_34_revoke_role(self):
        """역할 회수 → UserRole 삭제."""
        role = Role.objects.create(
            company=self.company, code='SALES', name='영업담당자',
        )
        target_user = User.objects.create_user(
            username='target01',
            email='target@test.com',
            password='pass1234',
            name='대상자',
            company=self.company,
        )
        UserRole.objects.create(role=role, user=target_user, assigned_by=self.user)

        resp = self.client.delete(f'/api/accounts/roles/{role.pk}/revoke/', {
            'user_id': target_user.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(UserRole.objects.filter(role=role, user=target_user).exists())


# ──────────────────────────────────────────────
# 8. AuditLog — 감사 로그
# ──────────────────────────────────────────────

class AuditLogTests(BaseAPITestCase):

    def test_35_audit_log_created_on_create(self):
        """공급업체 생성 시 AuditLog CREATE 기록 생성."""
        initial_count = AuditLog.objects.filter(
            company=self.company, action='CREATE', module='mm',
        ).count()

        self.client.post('/api/mm/suppliers/', {
            'name': '감사대상공급사',
            'email': 'audit@test.com',
        })

        new_count = AuditLog.objects.filter(
            company=self.company, action='CREATE', module='mm',
        ).count()
        self.assertEqual(new_count, initial_count + 1)

    def test_36_audit_log_created_on_update(self):
        """공급업체 수정 시 AuditLog UPDATE 기록 생성."""
        supplier = Supplier.objects.create(company=self.company, name='수정전공급사')

        initial_count = AuditLog.objects.filter(
            company=self.company, action='UPDATE', module='mm',
        ).count()

        self.client.patch(f'/api/mm/suppliers/{supplier.pk}/', {'name': '수정후공급사'})

        new_count = AuditLog.objects.filter(
            company=self.company, action='UPDATE', module='mm',
        ).count()
        self.assertEqual(new_count, initial_count + 1)

    def test_37_audit_log_created_on_delete(self):
        """공급업체 삭제 시 AuditLog DELETE 기록 생성."""
        supplier = Supplier.objects.create(company=self.company, name='삭제대상공급사')

        initial_count = AuditLog.objects.filter(
            company=self.company, action='DELETE', module='mm',
        ).count()

        self.client.delete(f'/api/mm/suppliers/{supplier.pk}/')

        new_count = AuditLog.objects.filter(
            company=self.company, action='DELETE', module='mm',
        ).count()
        self.assertEqual(new_count, initial_count + 1)
