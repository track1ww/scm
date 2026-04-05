"""
P5-3 테스트 — TM 운임 자동정산 + WI 작업표준 버전관리

커버리지:
  TM  (9)   FreightRate 조회, 자동 freight_cost 계산, FI 운반비전표 생성,
            fallback 로직, 중복 전표 방지, 통화·금액 정확도
  WI  (9)   WorkStandard CRUD, promote/deprecate/new_version 액션,
            버전 중복 방지, active 단일성, 권한 범위 격리
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from scm_accounts.models import Company, User
from scm_fi.models import AccountMove, AccountMoveLine
from scm_tm.models import Carrier, TransportOrder, FreightRate
from scm_wi.models import WorkStandard


# ─────────────────────────────────────────────────────────────────────────────
# 공통 베이스
# ─────────────────────────────────────────────────────────────────────────────

class BaseP53TestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_code='P53CO', company_name='P53테스트주식회사',
        )
        self.user = User.objects.create_user(
            username='p53user', email='p53@test.com', password='testpass123',
            name='P53테스터', company=self.company,
        )
        self.client = APIClient()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'p53@test.com', 'password': 'testpass123'})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')


# ─────────────────────────────────────────────────────────────────────────────
# TM: 운임 자동정산
# ─────────────────────────────────────────────────────────────────────────────

class TMFreightSettlementTests(BaseP53TestCase):
    """TransportOrder 완료 → FreightRate 조회 → freight_cost 자동계산 + FI 전표."""

    def setUp(self):
        super().setUp()
        self.carrier = Carrier.objects.create(
            company=self.company, carrier_code='CAR-001', carrier_name='P53운송사',
        )
        self.rate = FreightRate.objects.create(
            company=self.company, carrier=self.carrier,
            origin='서울', destination='부산',
            rate_per_kg=Decimal('10.00'),
            rate_per_cbm=Decimal('50000.00'),
            min_charge=Decimal('50000.00'),
            valid_from=datetime.date(2024, 1, 1),
        )

    def _make_to(self, number, weight=100, volume=2, status='배차완료'):
        return TransportOrder.objects.create(
            company=self.company, transport_number=number,
            carrier=self.carrier, origin='서울', destination='부산',
            weight_kg=Decimal(str(weight)), volume_cbm=Decimal(str(volume)),
            status=status,
        )

    def test_tm_01_freight_cost_auto_calculated_on_completion(self):
        """완료 전환 → freight_cost = max(50000, 100×10 + 2×50000) = 101,000."""
        to = self._make_to('TM-001')
        to.status = '완료'
        to.save()

        to.refresh_from_db()
        self.assertAlmostEqual(float(to.freight_cost), 101000.0, places=1)

    def test_tm_02_min_charge_applied_when_calculated_below_minimum(self):
        """계산값 < min_charge 이면 min_charge 적용 (1kg 운송)."""
        to = self._make_to('TM-002', weight=1, volume=0)
        to.status = '완료'
        to.save()

        to.refresh_from_db()
        # weight=1, rate_per_kg=10 → 10 < min_charge(50000) → 50000
        self.assertAlmostEqual(float(to.freight_cost), 50000.0, places=1)

    def test_tm_03_fi_journal_created_on_completion(self):
        """완료 → FI 운반비전표(AUTO-TM-*) 생성."""
        to = self._make_to('TM-003')
        to.status = '완료'
        to.save()

        move = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-TM-TM-003',
        ).first()
        self.assertIsNotNone(move, 'FI 운반비전표 없음')
        self.assertEqual(move.move_type, 'ENTRY')

    def test_tm_04_fi_journal_dr_freight_cr_accrued(self):
        """전표 라인: DR 운반비(6100) / CR 미지급운임(2520)."""
        to = self._make_to('TM-004')
        to.status = '완료'
        to.save()

        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-TM-TM-004',
        )
        lines = AccountMoveLine.objects.filter(move=move)
        self.assertEqual(lines.count(), 2)
        codes = set(lines.values_list('account__code', flat=True))
        self.assertIn('6100', codes)
        self.assertIn('2520', codes)

    def test_tm_05_fi_journal_amount_matches_freight_cost(self):
        """전표 금액 = 계산된 freight_cost."""
        to = self._make_to('TM-005')
        to.status = '완료'
        to.save()

        to.refresh_from_db()
        move = AccountMove.objects.get(
            company=self.company, move_number='AUTO-TM-TM-005',
        )
        self.assertAlmostEqual(float(move.total_debit),  float(to.freight_cost), places=1)
        self.assertAlmostEqual(float(move.total_credit), float(to.freight_cost), places=1)

    def test_tm_06_duplicate_completion_no_double_journal(self):
        """이미 완료 상태에서 재저장해도 FI 전표 중복 없음."""
        to = self._make_to('TM-006')
        to.status = '완료'
        to.save()
        count1 = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-TM-TM-006',
        ).count()

        to.save()  # 동일 상태 재저장
        count2 = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-TM-TM-006',
        ).count()
        self.assertEqual(count1, count2)

    def test_tm_07_no_fi_when_no_freight_rate(self):
        """FreightRate 없는 구간은 freight_cost=0, FI 전표 미생성."""
        to = TransportOrder.objects.create(
            company=self.company, transport_number='TM-NORATE',
            carrier=self.carrier, origin='인천', destination='대전',
            weight_kg=Decimal('50'), volume_cbm=Decimal('1'),
            status='배차완료',
        )
        to.status = '완료'
        to.save()

        exists = AccountMove.objects.filter(
            company=self.company, move_number='AUTO-TM-TM-NORATE',
        ).exists()
        self.assertFalse(exists)

    def test_tm_08_freight_cost_cbm_dominated(self):
        """CBM 비중이 높은 화물: 대형화물 10CBM × 50,000 = 500,000 (min_charge 초과)."""
        to = self._make_to('TM-008', weight=10, volume=10)
        to.status = '완료'
        to.save()

        to.refresh_from_db()
        # 10×10 + 10×50000 = 100 + 500000 = 500100 > 50000
        self.assertAlmostEqual(float(to.freight_cost), 500100.0, places=1)

    def test_tm_09_carrier_api_create(self):
        """Carrier API POST → 201."""
        resp = self.client.post('/api/tm/carriers/', {
            'carrier_code': 'CAR-NEW', 'carrier_name': '신규운송사',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['carrier_name'], '신규운송사')


# ─────────────────────────────────────────────────────────────────────────────
# WI: 작업표준 버전관리
# ─────────────────────────────────────────────────────────────────────────────

class WorkStandardVersionTests(BaseP53TestCase):
    """WorkStandard CRUD + promote/deprecate/new_version 액션 검증."""

    def _make_ws(self, code='WS-001', version='1.0', status='draft', title='작업표준'):
        return WorkStandard.objects.create(
            company=self.company, standard_code=code,
            work_center='WC-A', title=title,
            content='작업 절차 내용', version=version, status=status,
        )

    def test_wi_01_work_standard_api_create(self):
        """WorkStandard API POST → 201, status=draft."""
        resp = self.client.post('/api/wi/standards/', {
            'standard_code': 'WS-API', 'work_center': 'WC-B',
            'title': 'API생성표준', 'content': '내용',
            'version': '1.0', 'effective_from': '2024-01-01',
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['status'], 'draft')

    def test_wi_02_promote_draft_to_active(self):
        """draft → promote → status=active."""
        ws = self._make_ws()
        resp = self.client.post(f'/api/wi/standards/{ws.pk}/promote/')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'active')

    def test_wi_03_promote_sets_previous_active_to_deprecated(self):
        """신버전 promote 시 기존 active → deprecated."""
        old = self._make_ws(version='1.0', status='active')
        new = self._make_ws(version='2.0', status='draft')
        self.client.post(f'/api/wi/standards/{new.pk}/promote/')

        old.refresh_from_db()
        new.refresh_from_db()
        self.assertEqual(old.status, 'deprecated')
        self.assertEqual(new.status, 'active')

    def test_wi_04_only_one_active_per_standard_code(self):
        """동일 standard_code에 active는 항상 1개."""
        for ver in ['1.0', '2.0', '3.0']:
            ws = self._make_ws(code='WS-ACTIVE', version=ver)
            self.client.post(f'/api/wi/standards/{ws.pk}/promote/')

        active_count = WorkStandard.objects.filter(
            company=self.company, standard_code='WS-ACTIVE', status='active',
        ).count()
        self.assertEqual(active_count, 1)

    def test_wi_05_deprecate_active(self):
        """active → deprecate → status=deprecated."""
        ws = self._make_ws(status='active')
        resp = self.client.post(f'/api/wi/standards/{ws.pk}/deprecate/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'deprecated')

    def test_wi_06_promote_already_active_returns_400(self):
        """이미 active 상태에서 promote → 400."""
        ws = self._make_ws(status='active')
        resp = self.client.post(f'/api/wi/standards/{ws.pk}/promote/')
        self.assertEqual(resp.status_code, 400)

    def test_wi_07_new_version_creates_minor_increment(self):
        """new_version → 1.0 기반 → 1.1 생성."""
        ws = self._make_ws(version='1.0')
        resp = self.client.post(f'/api/wi/standards/{ws.pk}/new-version/')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['version'], '1.1')
        self.assertEqual(resp.data['status'], 'draft')

    def test_wi_08_new_version_duplicate_returns_409(self):
        """이미 동일 버전 존재 시 new_version → 409."""
        ws = self._make_ws(version='1.0')
        self._make_ws(version='1.1')  # 이미 존재
        resp = self.client.post(f'/api/wi/standards/{ws.pk}/new-version/')
        self.assertEqual(resp.status_code, 409)

    def test_wi_09_standards_scoped_to_company(self):
        """타 회사 WorkStandard 는 목록에 미포함."""
        other = Company.objects.create(company_code='WI-OTHER', company_name='타회사WI')
        WorkStandard.objects.create(
            company=other, standard_code='WS-OTHER',
            work_center='WC-X', title='타회사표준', version='1.0',
        )
        self._make_ws(code='WS-MINE')

        resp = self.client.get('/api/wi/standards/')
        self.assertEqual(resp.status_code, 200)
        codes = [r['standard_code'] for r in resp.data.get('results', resp.data)]
        self.assertIn('WS-MINE', codes)
        self.assertNotIn('WS-OTHER', codes)
