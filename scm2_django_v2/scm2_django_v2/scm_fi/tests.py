"""
scm_fi 테스트 스위트

테스트 구조:
  - AccountViewSetTest      : 계정과목 CRUD + balance + balance_sheet
  - AccountMoveViewSetTest  : 전표 CRUD + post + cancel + dashboard
  - TaxInvoiceViewSetTest   : 세금계산서 CRUD + issue + cancel + summary
  - TaxUtilsTest            : create_purchase_tax_lines / create_sale_tax_lines

실행:
  python manage.py test scm_fi
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from scm_accounts.models import Company
from .models import Account, AccountMove, AccountMoveLine, TaxInvoice
from .tax_utils import create_purchase_tax_lines, create_sale_tax_lines

User = get_user_model()


# --------------------------------------------------------------------------- #
#  공통 픽스처 믹스인                                                          #
# --------------------------------------------------------------------------- #
class FITestMixin:
    """
    테스트 케이스 공통 setUp:
      - company 생성
      - 인증 유저 생성 (user.company = company)
      - JWT 토큰 주입
    """

    def _make_company(self, name='테스트컴퍼니'):
        return Company.objects.create(name=name)

    def _make_user(self, company, email='fi@test.com', password='pass1234!'):
        user = User.objects.create_user(email=email, password=password)
        user.company = company
        user.save()
        return user

    def _auth(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _make_account(self, company, code='11000', name='현금', account_type='ASSET'):
        return Account.objects.create(
            company=company, code=code, name=name,
            account_type=account_type, is_active=True,
        )

    def _make_move(self, company, state='DRAFT', move_number=None):
        import uuid
        return AccountMove.objects.create(
            company      = company,
            move_number  = move_number or f'JE-{uuid.uuid4().hex[:8].upper()}',
            move_type    = 'ENTRY',
            posting_date = timezone.now().date(),
            state        = state,
        )

    def _make_balanced_lines(self, move, debit_account, credit_account, amount=Decimal('100000')):
        """대차균형 라인 2건 생성 후 전표 합계 갱신."""
        AccountMoveLine.objects.create(move=move, account=debit_account,  debit=amount,  credit=Decimal('0'))
        AccountMoveLine.objects.create(move=move, account=credit_account, debit=Decimal('0'), credit=amount)
        AccountMove.objects.filter(pk=move.pk).update(total_debit=amount, total_credit=amount)
        move.refresh_from_db()


# --------------------------------------------------------------------------- #
#  인증 없이 접근 차단 테스트                                                  #
# --------------------------------------------------------------------------- #
class FIUnauthenticatedTest(APITestCase):
    def test_accounts_requires_auth(self):
        resp = self.client.get('/api/fi/accounts/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_moves_requires_auth(self):
        resp = self.client.get('/api/fi/moves/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tax_invoices_requires_auth(self):
        resp = self.client.get('/api/fi/tax-invoices/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# --------------------------------------------------------------------------- #
#  AccountViewSet                                                              #
# --------------------------------------------------------------------------- #
class AccountViewSetTest(FITestMixin, APITestCase):
    def setUp(self):
        self.company = self._make_company()
        self.user    = self._make_user(self.company)
        self._auth(self.user)

        self.account_cash     = self._make_account(self.company, '10100', '현금',   'ASSET')
        self.account_revenue  = self._make_account(self.company, '40100', '매출액', 'REVENUE')

    # ---- 목록 조회 ----
    def test_list_accounts(self):
        resp = self.client.get('/api/fi/accounts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codes = [a['code'] for a in resp.data.get('results', resp.data)]
        self.assertIn('10100', codes)

    # ---- 생성 ----
    def test_create_account(self):
        payload = {
            'code': '20100', 'name': '외상매입금',
            'account_type': 'LIABILITY', 'is_active': True,
        }
        resp = self.client.post('/api/fi/accounts/', payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['code'], '20100')
        self.assertEqual(resp.data['company'], self.company.pk)

    # ---- company 격리: 타사 계정과목 조회 불가 ----
    def test_company_isolation(self):
        other_company = self._make_company('타사')
        self._make_account(other_company, '99999', '타사계정', 'ASSET')
        resp = self.client.get('/api/fi/accounts/')
        codes = [a['code'] for a in resp.data.get('results', resp.data)]
        self.assertNotIn('99999', codes)

    # ---- balance 액션 ----
    def test_balance_action(self):
        move = self._make_move(self.company)
        self._make_balanced_lines(move, self.account_cash, self.account_revenue)
        move.state = 'POSTED'
        move.save()

        resp = self.client.get(f'/api/fi/accounts/{self.account_cash.pk}/balance/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('balance', resp.data)
        self.assertEqual(Decimal(str(resp.data['total_debit'])), Decimal('100000'))

    # ---- balance_sheet 액션 ----
    def test_balance_sheet_action(self):
        resp = self.client.get('/api/fi/accounts/balance_sheet/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    # ---- 비활성 계정과목 목록에서 제외 ----
    def test_inactive_account_excluded(self):
        self.account_cash.is_active = False
        self.account_cash.save()
        resp = self.client.get('/api/fi/accounts/')
        codes = [a['code'] for a in resp.data.get('results', resp.data)]
        self.assertNotIn('10100', codes)


# --------------------------------------------------------------------------- #
#  AccountMoveViewSet                                                          #
# --------------------------------------------------------------------------- #
class AccountMoveViewSetTest(FITestMixin, APITestCase):
    def setUp(self):
        self.company        = self._make_company()
        self.user           = self._make_user(self.company)
        self._auth(self.user)
        self.account_debit  = self._make_account(self.company, '10100', '현금',   'ASSET')
        self.account_credit = self._make_account(self.company, '40100', '매출액', 'REVENUE')

    def _move_payload(self, state='DRAFT', move_number=None):
        import uuid
        return {
            'move_number':  move_number or f'JE-{uuid.uuid4().hex[:8].upper()}',
            'move_type':    'ENTRY',
            'posting_date': '2025-01-15',
            'state':        state,
            'lines': [
                {'account': self.account_debit.pk,  'debit': '100000', 'credit': '0'},
                {'account': self.account_credit.pk, 'debit': '0',      'credit': '100000'},
            ],
        }

    # ---- 목록 조회 ----
    def test_list_moves(self):
        self._make_move(self.company)
        resp = self.client.get('/api/fi/moves/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ---- 생성 ----
    def test_create_move(self):
        resp = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['company'], self.company.pk)
        self.assertEqual(len(resp.data['lines']), 2)

    # ---- 라인 없이 생성 불가 ----
    def test_create_move_without_lines_fails(self):
        payload = self._move_payload()
        payload['lines'] = []
        resp = self.client.post('/api/fi/moves/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- 대차 불일치 POSTED 생성 불가 ----
    def test_create_posted_move_unbalanced_fails(self):
        import uuid
        payload = {
            'move_number':  f'JE-{uuid.uuid4().hex[:8].upper()}',
            'move_type':    'ENTRY',
            'posting_date': '2025-01-15',
            'state':        'POSTED',
            'lines': [
                {'account': self.account_debit.pk,  'debit': '100000', 'credit': '0'},
                {'account': self.account_credit.pk, 'debit': '0',      'credit': '50000'},
            ],
        }
        resp = self.client.post('/api/fi/moves/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- post 액션: DRAFT → POSTED ----
    def test_post_action(self):
        resp_create = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        move_id = resp_create.data['id']

        resp = self.client.post(f'/api/fi/moves/{move_id}/post/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['state'], 'POSTED')
        self.assertIsNotNone(resp.data['posted_at'])

    # ---- post 액션: 이미 확정된 전표 ----
    def test_post_action_already_posted(self):
        resp_create = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        move_id = resp_create.data['id']
        self.client.post(f'/api/fi/moves/{move_id}/post/')
        resp = self.client.post(f'/api/fi/moves/{move_id}/post/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- cancel 액션: POSTED → CANCELLED ----
    def test_cancel_action(self):
        resp_create = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        move_id = resp_create.data['id']
        self.client.post(f'/api/fi/moves/{move_id}/post/')

        resp = self.client.post(f'/api/fi/moves/{move_id}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['state'], 'CANCELLED')

    # ---- cancel 액션: DRAFT 전표 취소 불가 ----
    def test_cancel_draft_move_returns_400(self):
        resp_create = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        move_id = resp_create.data['id']
        resp = self.client.post(f'/api/fi/moves/{move_id}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- 확정된 전표 PUT 수정 불가 ----
    def test_update_posted_move_forbidden(self):
        resp_create = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        move_id = resp_create.data['id']
        self.client.post(f'/api/fi/moves/{move_id}/post/')

        resp = self.client.put(f'/api/fi/moves/{move_id}/', self._move_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- 확정된 전표 DELETE 불가 ----
    def test_delete_posted_move_forbidden(self):
        resp_create = self.client.post('/api/fi/moves/', self._move_payload(), format='json')
        move_id = resp_create.data['id']
        self.client.post(f'/api/fi/moves/{move_id}/post/')

        resp = self.client.delete(f'/api/fi/moves/{move_id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- dashboard 액션 ----
    def test_dashboard_action(self):
        resp = self.client.get('/api/fi/moves/dashboard/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for key in ('total', 'draft', 'posted', 'cancelled', 'locked',
                    'posted_total_debit', 'posted_total_credit'):
            self.assertIn(key, resp.data)

    # ---- company 격리 ----
    def test_company_isolation(self):
        other_company = self._make_company('타사')
        other_user    = self._make_user(other_company, email='other@test.com')
        other_move    = self._make_move(other_company)

        resp = self.client.get('/api/fi/moves/')
        ids = [m['id'] for m in resp.data.get('results', resp.data)]
        self.assertNotIn(other_move.pk, ids)


# --------------------------------------------------------------------------- #
#  TaxInvoiceViewSet                                                           #
# --------------------------------------------------------------------------- #
class TaxInvoiceViewSetTest(FITestMixin, APITestCase):
    def setUp(self):
        self.company = self._make_company()
        self.user    = self._make_user(self.company)
        self._auth(self.user)

    def _invoice_payload(self, invoice_number=None):
        import uuid
        return {
            'invoice_number':            invoice_number or f'TI-{uuid.uuid4().hex[:8].upper()}',
            'invoice_type':              'SALE',
            'supplier_or_customer_name': '(주)테스트거래처',
            'supply_amount':             '100000.00',
            'tax_amount':                '10000.00',
            'total_amount':              '110000.00',
            'issue_date':                '2025-01-15',
        }

    def _make_invoice(self, status_val='DRAFT'):
        import uuid
        inv = TaxInvoice.objects.create(
            company                  = self.company,
            invoice_number           = f'TI-{uuid.uuid4().hex[:8].upper()}',
            invoice_type             = 'SALE',
            supplier_or_customer_name = '(주)테스트',
            supply_amount            = Decimal('100000'),
            tax_amount               = Decimal('10000'),
            total_amount             = Decimal('110000'),
            issue_date               = timezone.now().date(),
            status                   = status_val,
            created_by               = self.user,
        )
        return inv

    # ---- 목록 조회 ----
    def test_list_tax_invoices(self):
        self._make_invoice()
        resp = self.client.get('/api/fi/tax-invoices/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ---- 생성 ----
    def test_create_tax_invoice(self):
        resp = self.client.post('/api/fi/tax-invoices/', self._invoice_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'DRAFT')
        self.assertEqual(resp.data['company'], self.company.pk)

    # ---- 세액 불일치 생성 불가 ----
    def test_create_tax_invoice_wrong_tax_fails(self):
        payload = self._invoice_payload()
        payload['tax_amount'] = '5000.00'
        resp = self.client.post('/api/fi/tax-invoices/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- issue 액션: DRAFT → ISSUED ----
    def test_issue_action(self):
        inv  = self._make_invoice('DRAFT')
        resp = self.client.post(f'/api/fi/tax-invoices/{inv.pk}/issue/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'ISSUED')

    # ---- issue 액션: 이미 발행된 청구서 ----
    def test_issue_already_issued_fails(self):
        inv  = self._make_invoice('ISSUED')
        resp = self.client.post(f'/api/fi/tax-invoices/{inv.pk}/issue/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- cancel 액션: ISSUED → CANCELLED ----
    def test_cancel_action(self):
        inv  = self._make_invoice('ISSUED')
        resp = self.client.post(f'/api/fi/tax-invoices/{inv.pk}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'CANCELLED')

    # ---- cancel 액션: DRAFT 세금계산서 ----
    def test_cancel_draft_invoice_returns_400(self):
        inv  = self._make_invoice('DRAFT')
        resp = self.client.post(f'/api/fi/tax-invoices/{inv.pk}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- 발행된 세금계산서 삭제 불가 ----
    def test_delete_issued_invoice_forbidden(self):
        inv  = self._make_invoice('ISSUED')
        resp = self.client.delete(f'/api/fi/tax-invoices/{inv.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- DRAFT 세금계산서 삭제 가능 ----
    def test_delete_draft_invoice_ok(self):
        inv  = self._make_invoice('DRAFT')
        resp = self.client.delete(f'/api/fi/tax-invoices/{inv.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # ---- summary 액션 ----
    def test_summary_action(self):
        self._make_invoice('ISSUED')
        resp = self.client.get('/api/fi/tax-invoices/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for key in ('period', 'purchase', 'sale', 'net_vat_payable'):
            self.assertIn(key, resp.data)

    # ---- summary 기간 필터 ----
    def test_summary_period_filter(self):
        self._make_invoice('ISSUED')
        resp = self.client.get('/api/fi/tax-invoices/summary/?year=2025&month=1')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['period']['year'], '2025')

    # ---- company 격리 ----
    def test_company_isolation(self):
        other_company = self._make_company('타사')
        other_user    = self._make_user(other_company, email='other2@test.com')
        TaxInvoice.objects.create(
            company                  = other_company,
            invoice_number           = 'TI-OTHER-001',
            invoice_type             = 'SALE',
            supplier_or_customer_name = '타사거래처',
            supply_amount            = Decimal('200000'),
            tax_amount               = Decimal('20000'),
            total_amount             = Decimal('220000'),
            issue_date               = timezone.now().date(),
            status                   = 'DRAFT',
            created_by               = other_user,
        )
        resp = self.client.get('/api/fi/tax-invoices/')
        numbers = [i['invoice_number'] for i in resp.data.get('results', resp.data)]
        self.assertNotIn('TI-OTHER-001', numbers)


# --------------------------------------------------------------------------- #
#  TaxUtils (tax_utils.py)                                                    #
# --------------------------------------------------------------------------- #
class TaxUtilsTest(FITestMixin, APITestCase):
    def setUp(self):
        self.company = self._make_company()
        self.user    = self._make_user(self.company)
        # tax_utils 에서 사용하는 계정과목 생성
        self._make_account(self.company, '13500', '부가세대급금', 'ASSET')
        self._make_account(self.company, '25100', '매입채무',     'LIABILITY')
        self._make_account(self.company, '11000', '매출채권',     'ASSET')
        self._make_account(self.company, '25500', '부가세예수금', 'LIABILITY')

    def test_create_purchase_tax_lines(self):
        move  = self._make_move(self.company)
        lines = create_purchase_tax_lines(move, Decimal('100000'), self.company)
        self.assertEqual(len(lines), 2)
        move.refresh_from_db()
        # 부가세대급금 차변 = 10,000
        vat_line = next(l for l in lines if l.account.code == '13500')
        self.assertEqual(vat_line.debit, Decimal('10000'))

    def test_create_sale_tax_lines(self):
        move  = self._make_move(self.company)
        lines = create_sale_tax_lines(move, Decimal('200000'), self.company)
        self.assertEqual(len(lines), 2)
        # 부가세예수금 대변 = 20,000
        vat_line = next(l for l in lines if l.account.code == '25500')
        self.assertEqual(vat_line.credit, Decimal('20000'))

    def test_create_purchase_tax_lines_missing_account_raises(self):
        Account.objects.filter(company=self.company, code='13500').delete()
        move = self._make_move(self.company)
        with self.assertRaises(ValueError):
            create_purchase_tax_lines(move, Decimal('100000'), self.company)
