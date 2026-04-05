"""
P5-1 E2E 시나리오 테스트 — 전체 비즈니스 흐름 통합 검증

시나리오:
  1. 발주 전체 사이클 — PO → 입고완료 → WM IN → FI 매입전표 (금액 검증)
  2. 수주 전체 사이클 — SO → 배송완료 → WM OUT → FI 매출+COGS 4라인
  3. 생산 전체 사이클 — BOM → PP완료 → WM BOM소비+완제품IN → FI 생산원가전표
  4. 결재 워크플로우  — 요청 → 승인/반려 → 상태 전이 → 다단계 진행
  5. RBAC 권한 검증   — BUYER 역할 → apply_to_user → 전체 모듈 권한 검증
  6. AuditLog 연속    — CREATE→UPDATE→DELETE 3단계 연속 로그 검증
"""
import datetime
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from scm_accounts.models import Company, User, Role, UserPermission, ALL_MODULES
from scm_core.models import AuditLog
from scm_fi.models import Account, AccountMove, AccountMoveLine
from scm_mm.models import Material, MaterialPriceHistory, PurchaseOrder, Supplier
from scm_pp.models import BillOfMaterial, BomLine, ProductionOrder
from scm_sd.models import Customer, SalesOrder
from scm_wm.models import Inventory, StockMovement
from scm_workflow.models import (
    ApprovalAction, ApprovalRequest, ApprovalStep, ApprovalTemplate,
)


# ─────────────────────────────────────────────────────────────────────────────
# 공통 베이스
# ─────────────────────────────────────────────────────────────────────────────

class BaseE2ETestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_code='E2E01', company_name='E2E테스트주식회사',
        )
        self.user = User.objects.create_user(
            username='e2euser', email='e2e@test.com', password='testpass123',
            name='E2E테스터', company=self.company,
        )
        self.client = APIClient()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'e2e@test.com', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 1: 발주 전체 사이클
# ─────────────────────────────────────────────────────────────────────────────

class E2EPurchaseOrderCycleTest(BaseE2ETestCase):
    """PO 생성 → 입고완료 → WM 재고 IN → FI 매입전표 자동 생성."""

    def setUp(self):
        super().setUp()
        self.supplier = Supplier.objects.create(
            company=self.company, name='E2E공급사',
        )
        self.po = PurchaseOrder.objects.create(
            company=self.company, po_number='E2E-PO-001',
            supplier=self.supplier, item_name='E2E원재료',
            quantity=100, unit_price=Decimal('5000.00'), status='발주확정',
        )

    def test_e2e_po_01_wm_stock_movement_created(self):
        """입고완료 → StockMovement IN 기록."""
        self.po.status = '입고완료'
        self.po.save()

        mv = StockMovement.objects.filter(
            company=self.company, movement_type='IN',
            reference_document='E2E-PO-001',
        ).first()
        self.assertIsNotNone(mv, 'StockMovement IN이 없음')
        self.assertEqual(int(mv.quantity), 100)

    def test_e2e_po_02_inventory_qty_increased(self):
        """입고완료 → Inventory stock_qty += 100."""
        self.po.status = '입고완료'
        self.po.save()

        inv = Inventory.objects.filter(company=self.company).first()
        self.assertIsNotNone(inv)
        self.assertGreaterEqual(inv.stock_qty, 100)

    def test_e2e_po_03_fi_journal_created_with_correct_amount(self):
        """입고완료 → FI 매입전표 금액 = qty × unit_price = 500,000."""
        self.po.status = '입고완료'
        self.po.save()

        move = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-PO-E2E-PO-001',
        ).first()
        self.assertIsNotNone(move, 'FI 매입전표가 없음')
        self.assertEqual(move.move_type, 'PURCHASE')
        self.assertAlmostEqual(float(move.total_debit),  500000.0, places=1)
        self.assertAlmostEqual(float(move.total_credit), 500000.0, places=1)

    def test_e2e_po_04_fi_journal_lines_dr_inventory_cr_ap(self):
        """매입전표 2라인: DR 재고자산(1400) / CR 매입채무(2510)."""
        self.po.status = '입고완료'
        self.po.save()

        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-PO-E2E-PO-001',
        )
        lines = AccountMoveLine.objects.filter(move=move)
        self.assertEqual(lines.count(), 2)
        codes = set(lines.values_list('account__code', flat=True))
        self.assertIn('1400', codes)
        self.assertIn('2510', codes)

    def test_e2e_po_05_duplicate_receipt_no_double_journal(self):
        """이미 입고완료 상태에서 재저장해도 FI 전표 중복 생성 없음."""
        self.po.status = '입고완료'
        self.po.save()
        count1 = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-PO-E2E-PO-001',
        ).count()

        # 동일 PO 다시 save (old.status == '입고완료'이므로 시그널 미발화)
        self.po.save()
        count2 = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-PO-E2E-PO-001',
        ).count()
        self.assertEqual(count1, count2)


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 2: 수주 전체 사이클
# ─────────────────────────────────────────────────────────────────────────────

class E2ESalesOrderCycleTest(BaseE2ETestCase):
    """SO 배송완료 → WM OUT → FI 매출+COGS 4라인."""

    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(
            company=self.company, customer_code='E2E-CUST', customer_name='E2E고객사',
        )
        self.so = SalesOrder.objects.create(
            company=self.company, order_number='E2E-SO-001',
            customer=self.customer, customer_name='E2E고객사',
            item_name='E2E제품', quantity=20,
            unit_price=Decimal('3000.00'), discount_rate=Decimal('0.00'),
            status='배송중',
        )

    def test_e2e_so_01_wm_stock_out_on_delivery(self):
        """배송완료 → StockMovement OUT 기록."""
        self.so.status = '배송완료'
        self.so.save()

        mv = StockMovement.objects.filter(
            company=self.company, movement_type='OUT',
            reference_document='E2E-SO-001',
        ).first()
        self.assertIsNotNone(mv)
        self.assertEqual(int(mv.quantity), 20)

    def test_e2e_so_02_fi_journal_has_4_lines(self):
        """FI 매출전표 4라인: AR(1100), 매출(4000), COGS(5000), 재고(1400)."""
        self.so.status = '배송완료'
        self.so.save()

        move = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-SO-E2E-SO-001',
        ).first()
        self.assertIsNotNone(move, 'FI 매출전표가 없음')
        lines = AccountMoveLine.objects.filter(move=move)
        self.assertEqual(lines.count(), 4)

        codes = set(lines.values_list('account__code', flat=True))
        self.assertIn('1100', codes)  # 매출채권
        self.assertIn('4000', codes)  # 매출
        self.assertIn('5000', codes)  # 매출원가
        self.assertIn('1400', codes)  # 재고자산

    def test_e2e_so_03_revenue_amount_matches_total_amount(self):
        """AR/매출 라인 금액 = 20 × 3,000 = 60,000."""
        self.so.status = '배송완료'
        self.so.save()

        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-SO-E2E-SO-001',
        )
        ar = AccountMoveLine.objects.get(move=move, account__code='1100')
        rev = AccountMoveLine.objects.get(move=move, account__code='4000')
        self.assertAlmostEqual(float(ar.debit),   60000.0, places=1)
        self.assertAlmostEqual(float(rev.credit), 60000.0, places=1)

    def test_e2e_so_04_cogs_estimated_70pct_when_no_price_history(self):
        """단가이력 없으면 COGS = revenue × 0.7 = 42,000."""
        self.so.status = '배송완료'
        self.so.save()

        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-SO-E2E-SO-001',
        )
        cogs = AccountMoveLine.objects.get(move=move, account__code='5000')
        self.assertAlmostEqual(float(cogs.debit), 42000.0, places=1)

    def test_e2e_so_05_cogs_exact_when_price_history_exists(self):
        """단가이력 있으면 COGS = unit_cost × qty = 2000 × 20 = 40,000."""
        mat = Material.objects.create(
            company=self.company, material_code='E2E-PROD', material_name='E2E제품',
        )
        MaterialPriceHistory.objects.create(
            company=self.company, material=mat,
            unit_price=Decimal('2000.00'),
            effective_from=datetime.date(2024, 1, 1),
        )
        self.so.status = '배송완료'
        self.so.save()

        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-SO-E2E-SO-001',
        )
        cogs = AccountMoveLine.objects.get(move=move, account__code='5000')
        self.assertAlmostEqual(float(cogs.debit), 40000.0, places=1)


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3: 생산 전체 사이클
# ─────────────────────────────────────────────────────────────────────────────

class E2EProductionCycleTest(BaseE2ETestCase):
    """PP 생산완료 → WM BOM소비+완제품 IN → FI 생산원가전표."""

    def setUp(self):
        super().setUp()
        self.raw_mat = Material.objects.create(
            company=self.company, material_code='E2E-RAW', material_name='E2E원재료A',
        )
        MaterialPriceHistory.objects.create(
            company=self.company, material=self.raw_mat,
            unit_price=Decimal('1000.00'),
            effective_from=datetime.date(2024, 1, 1),
        )
        self.bom = BillOfMaterial.objects.create(
            company=self.company, bom_code='E2E-BOM', product_name='E2E완제품',
        )
        BomLine.objects.create(
            bom=self.bom, material_code='E2E-RAW', material_name='E2E원재료A',
            quantity=Decimal('5.000'), unit='EA', scrap_rate=Decimal('0.00'),
        )
        self.pp = ProductionOrder.objects.create(
            company=self.company, order_number='E2E-PP-001',
            bom=self.bom, product_name='E2E완제품',
            planned_qty=10, status='생산중',
        )

    def test_e2e_pp_01_bom_out_on_completion(self):
        """완료 → BOM 원재료 OUT = 5 × 10 = 50."""
        self.pp.status = '완료'
        self.pp.save()

        mv = StockMovement.objects.filter(
            company=self.company, movement_type='OUT',
            material_code='E2E-RAW', reference_document='E2E-PP-001',
        ).first()
        self.assertIsNotNone(mv)
        self.assertAlmostEqual(float(mv.quantity), 50.0, places=1)

    def test_e2e_pp_02_fg_in_on_completion(self):
        """완료 → 완제품 IN = 10."""
        self.pp.status = '완료'
        self.pp.save()

        mv = StockMovement.objects.filter(
            company=self.company, movement_type='IN',
            reference_document='E2E-PP-001',
        ).first()
        self.assertIsNotNone(mv)
        self.assertEqual(int(mv.quantity), 10)

    def test_e2e_pp_03_fi_production_cost_journal(self):
        """완료 → FI 생산원가전표: 1000 × 5 × 10 = 50,000."""
        self.pp.status = '완료'
        self.pp.save()

        move = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-PP-E2E-PP-001',
        ).first()
        self.assertIsNotNone(move, 'FI 생산원가전표가 없음')
        self.assertEqual(move.move_type, 'ENTRY')
        self.assertAlmostEqual(float(move.total_debit),  50000.0, places=1)
        self.assertAlmostEqual(float(move.total_credit), 50000.0, places=1)

    def test_e2e_pp_04_fi_journal_lines_dr_inventory_cr_production_cost(self):
        """생산원가전표 2라인: DR 재고자산(1400) / CR 생산원가(5100)."""
        self.pp.status = '완료'
        self.pp.save()

        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-PP-E2E-PP-001',
        )
        lines = AccountMoveLine.objects.filter(move=move)
        self.assertEqual(lines.count(), 2)
        codes = set(lines.values_list('account__code', flat=True))
        self.assertIn('1400', codes)
        self.assertIn('5100', codes)

    def test_e2e_pp_05_no_fi_journal_when_no_price_history(self):
        """단가이력 없으면 production_cost=0 → FI 전표 미생성."""
        MaterialPriceHistory.objects.filter(
            company=self.company, material=self.raw_mat,
        ).delete()

        pp2 = ProductionOrder.objects.create(
            company=self.company, order_number='E2E-PP-NOPRICE',
            bom=self.bom, product_name='E2E완제품',
            planned_qty=5, status='생산중',
        )
        pp2.status = '완료'
        pp2.save()

        exists = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-PP-E2E-PP-NOPRICE',
        ).exists()
        self.assertFalse(exists)


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 4: 결재 워크플로우
# ─────────────────────────────────────────────────────────────────────────────

class E2EApprovalWorkflowTest(BaseE2ETestCase):
    """결재 요청 → 승인/반려 → 상태 전이 → 다단계 current_step 진행."""

    def setUp(self):
        super().setUp()
        self.supplier = Supplier.objects.create(
            company=self.company, name='결재공급사',
        )
        self.po = PurchaseOrder.objects.create(
            company=self.company, po_number='WF-PO-001',
            supplier=self.supplier, item_name='결재품목',
            quantity=10, unit_price=Decimal('1000.00'),
        )
        self.template = ApprovalTemplate.objects.create(
            company=self.company, name='구매결재', module='mm',
            doc_type='purchase_order', is_active=True,
        )
        ApprovalStep.objects.create(
            template=self.template, step_no=1, step_name='팀장결재',
        )
        ct = ContentType.objects.get_for_model(PurchaseOrder)
        resp = self.client.post('/api/workflow/requests/', {
            'company': self.company.pk,
            'template': self.template.pk,
            'content_type': ct.pk,
            'object_id': self.po.pk,
            'title': '발주 결재 요청',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.req_id = resp.data['id']

    def test_e2e_wf_01_request_created_pending(self):
        """생성된 결재 요청 상태는 pending."""
        resp = self.client.get(f'/api/workflow/requests/{self.req_id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'pending')
        self.assertEqual(resp.data['current_step'], 1)

    def test_e2e_wf_02_approve_sets_status_approved(self):
        """단일 단계 승인 → status=approved, completed_at 설정."""
        resp = self.client.post(
            f'/api/workflow/requests/{self.req_id}/approve/', {'comment': '승인'}
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'approved')

        ar = ApprovalRequest.objects.get(pk=self.req_id)
        self.assertIsNotNone(ar.completed_at)

    def test_e2e_wf_03_approval_action_recorded(self):
        """승인 시 ApprovalAction 레코드 생성."""
        self.client.post(
            f'/api/workflow/requests/{self.req_id}/approve/', {'comment': 'LGTM'}
        )
        action = ApprovalAction.objects.filter(
            request_id=self.req_id, action='approved',
        ).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.approver, self.user)
        self.assertEqual(action.comment, 'LGTM')

    def test_e2e_wf_04_reject_sets_status_rejected(self):
        """반려 → status=rejected."""
        resp = self.client.post(
            f'/api/workflow/requests/{self.req_id}/reject/', {'comment': '예산 초과'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'rejected')

    def test_e2e_wf_05_double_approve_returns_400(self):
        """이미 approved 상태에서 재승인 시도 → 400."""
        self.client.post(
            f'/api/workflow/requests/{self.req_id}/approve/', {'comment': '1차'}
        )
        resp2 = self.client.post(
            f'/api/workflow/requests/{self.req_id}/approve/', {'comment': '중복'}
        )
        self.assertEqual(resp2.status_code, 400)

    def test_e2e_wf_06_multistep_increments_current_step(self):
        """2단계 템플릿: 1단계 승인 → current_step=2, status=pending."""
        # 별도 doc_type으로 2단계 템플릿 생성 (unique_together 충돌 회피)
        tmpl2 = ApprovalTemplate.objects.create(
            company=self.company, name='2단계구매결재', module='mm',
            doc_type='purchase_order_2step', is_active=True,
        )
        ApprovalStep.objects.create(template=tmpl2, step_no=1, step_name='팀장')
        ApprovalStep.objects.create(
            template=tmpl2, step_no=2, step_name='대표이사')

        po2 = PurchaseOrder.objects.create(
            company=self.company, po_number='WF-PO-002',
            supplier=self.supplier, item_name='2단계품목',
            quantity=5, unit_price=Decimal('500.00'),
        )
        ct = ContentType.objects.get_for_model(PurchaseOrder)
        resp = self.client.post('/api/workflow/requests/', {
            'company': self.company.pk,
            'template': tmpl2.pk,
            'content_type': ct.pk,
            'object_id': po2.pk,
            'title': '2단계 결재',
        })
        req2_id = resp.data['id']

        # 1단계 승인
        resp1 = self.client.post(
            f'/api/workflow/requests/{req2_id}/approve/', {'comment': '1단계'}
        )
        self.assertEqual(resp1.status_code, 200, resp1.data)
        self.assertEqual(resp1.data['current_step'], 2)
        self.assertEqual(resp1.data['status'], 'pending')

        # 2단계 승인
        resp2 = self.client.post(
            f'/api/workflow/requests/{req2_id}/approve/', {'comment': '2단계'}
        )
        self.assertEqual(resp2.data['status'], 'approved')

    def test_e2e_wf_07_cancel_by_requester(self):
        """요청자 본인이 취소 → status=cancelled."""
        resp = self.client.post(f'/api/workflow/requests/{self.req_id}/cancel/', {})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'cancelled')


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 5: RBAC 권한 검증
# ─────────────────────────────────────────────────────────────────────────────

class E2ERBACPermissionTest(BaseE2ETestCase):
    """BUYER 역할 → apply_to_user → 전체 모듈 권한 정확성 검증."""

    def setUp(self):
        super().setUp()
        self.user.is_admin = True
        self.user.save()

        self.buyer_role = Role.objects.create(
            company=self.company, code='BUYER', name='구매담당자',
        )
        self.target = User.objects.create_user(
            username='buyer01', email='buyer01@test.com', password='pass1234',
            name='구매담당01', company=self.company,
        )

    def test_e2e_rbac_01_apply_creates_all_module_permissions(self):
        """apply_to_user → ALL_MODULES 전체에 UserPermission 생성."""
        self.buyer_role.apply_to_user(self.target)
        count = UserPermission.objects.filter(user=self.target).count()
        self.assertEqual(count, len(ALL_MODULES))

    def test_e2e_rbac_02_buyer_mm_read_write(self):
        """BUYER: mm = (read=True, write=True)."""
        self.buyer_role.apply_to_user(self.target)
        perm = UserPermission.objects.get(user=self.target, module='mm')
        self.assertTrue(perm.can_read)
        self.assertTrue(perm.can_write)

    def test_e2e_rbac_03_buyer_sd_no_access(self):
        """BUYER: sd = (read=False, write=False) — 영업 모듈 접근 없음."""
        self.buyer_role.apply_to_user(self.target)
        perm = UserPermission.objects.get(user=self.target, module='sd')
        self.assertFalse(perm.can_read)
        self.assertFalse(perm.can_write)

    def test_e2e_rbac_04_buyer_hr_no_access(self):
        """BUYER: hr = (read=False, write=False)."""
        self.buyer_role.apply_to_user(self.target)
        perm = UserPermission.objects.get(user=self.target, module='hr')
        self.assertFalse(perm.can_read)
        self.assertFalse(perm.can_write)

    def test_e2e_rbac_05_all_modules_match_default_permissions(self):
        """전체 모듈 권한이 ROLE_DEFAULT_PERMISSIONS['BUYER']와 정확히 일치."""
        from scm_accounts.models import ROLE_DEFAULT_PERMISSIONS
        self.buyer_role.apply_to_user(self.target)
        buyer_map = ROLE_DEFAULT_PERMISSIONS['BUYER']
        for module in ALL_MODULES:
            perm = UserPermission.objects.get(user=self.target, module=module)
            exp_r, exp_w = buyer_map[module]
            self.assertEqual(perm.can_read,  exp_r, f'{module}.can_read')
            self.assertEqual(perm.can_write, exp_w, f'{module}.can_write')

    def test_e2e_rbac_06_apply_twice_idempotent(self):
        """apply_to_user 2회 호출 → UserPermission 중복 없음."""
        self.buyer_role.apply_to_user(self.target)
        self.buyer_role.apply_to_user(self.target)
        count = UserPermission.objects.filter(user=self.target).count()
        self.assertEqual(count, len(ALL_MODULES))

    def test_e2e_rbac_07_assign_via_api(self):
        """API /roles/{id}/assign/ 로 역할 할당 → UserRole 생성."""
        from scm_accounts.models import UserRole
        resp = self.client.post(
            f'/api/accounts/roles/{self.buyer_role.pk}/assign/',
            {'user_id': self.target.pk},
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(UserRole.objects.filter(
            role=self.buyer_role, user=self.target,
        ).exists())


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 6: AuditLog 연속 추적
# ─────────────────────────────────────────────────────────────────────────────

class E2EAuditLogTrackingTest(BaseE2ETestCase):
    """동일 객체에 대한 CREATE→UPDATE→DELETE 3단계 AuditLog 연속 검증."""

    def test_e2e_audit_01_create_update_delete_sequence(self):
        """핵심 E2E: 3단계 로그가 순서대로 존재."""
        # CREATE
        r1 = self.client.post('/api/mm/suppliers/', {'name': 'E2E감사공급사'})
        self.assertEqual(r1.status_code, 201)
        sid = r1.data['id']

        log_c = AuditLog.objects.filter(
            company=self.company, action='CREATE', module='mm', object_id=sid,
        ).first()
        self.assertIsNotNone(log_c, 'CREATE 로그 없음')

        # UPDATE
        r2 = self.client.patch(f'/api/mm/suppliers/{sid}/', {'name': 'E2E수정공급사'})
        self.assertEqual(r2.status_code, 200)

        log_u = AuditLog.objects.filter(
            company=self.company, action='UPDATE', module='mm', object_id=sid,
        ).first()
        self.assertIsNotNone(log_u, 'UPDATE 로그 없음')

        # DELETE
        r3 = self.client.delete(f'/api/mm/suppliers/{sid}/')
        self.assertEqual(r3.status_code, 204)

        log_d = AuditLog.objects.filter(
            company=self.company, action='DELETE', module='mm', object_id=sid,
        ).first()
        self.assertIsNotNone(log_d, 'DELETE 로그 없음')

        # 순서: CREATE ≤ UPDATE ≤ DELETE
        self.assertLessEqual(log_c.created_at, log_u.created_at)
        self.assertLessEqual(log_u.created_at, log_d.created_at)

    def test_e2e_audit_02_log_references_correct_user(self):
        """AuditLog.user 가 실제 요청한 유저를 참조."""
        r = self.client.post('/api/mm/suppliers/', {'name': 'AuditUser공급사'})
        sid = r.data['id']
        log = AuditLog.objects.get(
            company=self.company, action='CREATE', module='mm', object_id=sid,
        )
        self.assertEqual(log.user, self.user)

    def test_e2e_audit_03_log_model_name_is_supplier(self):
        """AuditLog.model_name 이 'Supplier' (대소문자 무관)."""
        r = self.client.post('/api/mm/suppliers/', {'name': '모델명검증공급사'})
        sid = r.data['id']
        log = AuditLog.objects.get(
            company=self.company, action='CREATE', module='mm', object_id=sid,
        )
        self.assertEqual(log.model_name.lower(), 'supplier')

    def test_e2e_audit_04_delete_log_retains_object_id(self):
        """객체 삭제 후에도 AuditLog.object_id 로 조회 가능."""
        r = self.client.post('/api/mm/suppliers/', {'name': '삭제검증공급사'})
        sid = r.data['id']
        self.client.delete(f'/api/mm/suppliers/{sid}/')

        log = AuditLog.objects.filter(
            company=self.company, action='DELETE', module='mm', object_id=sid,
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.object_id, sid)

    def test_e2e_audit_05_multi_module_logs_isolated(self):
        """MM 로그와 SD 로그가 module 필드로 격리됨."""
        self.client.post('/api/mm/suppliers/', {'name': 'MM공급사'})
        self.client.post('/api/sd/customers/', {
            'customer_code': 'AUDIT-CUST', 'customer_name': 'SD고객',
        })

        mm_logs = AuditLog.objects.filter(company=self.company, module='mm')
        sd_logs = AuditLog.objects.filter(company=self.company, module='sd')

        self.assertGreater(mm_logs.count(), 0)
        self.assertGreater(sd_logs.count(), 0)

        # 교차 없음
        self.assertFalse(mm_logs.filter(module='sd').exists())
        self.assertFalse(sd_logs.filter(module='mm').exists())
