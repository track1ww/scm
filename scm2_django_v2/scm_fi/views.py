import uuid
import datetime
from decimal import Decimal
from datetime import date

from django.utils import timezone
from django.db.models import Sum, Count, F, Q

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Account, AccountMove, AccountMoveLine, Budget, FixedAsset, DepreciationSchedule, TaxInvoice, AccountingPeriod
from .serializers import (
    AccountSerializer, AccountMoveSerializer, AccountMoveWriteSerializer,
    BudgetSerializer, FixedAssetSerializer, TaxInvoiceSerializer,
    AccountingPeriodSerializer,
)
from .utils import aging_buckets, calc_depreciation_schedule
from scm_core.mixins import AuditLogMixin, StateLockMixin


class AccountViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'fi'
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['code', 'name']
    filterset_fields = ['account_type', 'is_active', 'is_group']
    ordering_fields = ['code', 'name']

    def get_queryset(self):
        return Account.objects.filter(company=self.request.user.company).order_by('code')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class AccountMoveViewSet(AuditLogMixin, StateLockMixin, viewsets.ModelViewSet):
    audit_module = 'fi'
    locked_states = ['POSTED', 'CANCELLED']
    state_field = 'state'
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['move_number', 'ref', 'created_by']
    filterset_fields = ['move_type', 'state']
    ordering_fields = ['posting_date', 'created_at', 'move_number']

    def get_queryset(self):
        return AccountMove.objects.filter(
            company=self.request.user.company
        ).prefetch_related('lines__account').order_by('-posting_date')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AccountMoveWriteSerializer
        return AccountMoveSerializer

    def perform_create(self, serializer):
        move_number = f'JE-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(company=self.request.user.company, move_number=move_number)

    @action(detail=True, methods=['post'])
    def post(self, request, pk=None):
        """전표 확정 (DRAFT → POSTED)"""
        move = self.get_object()
        # Check accounting period is open
        import datetime
        posting_date = move.posting_date or datetime.date.today()
        period_closed = AccountingPeriod.objects.filter(
            company=move.company,
            year=posting_date.year,
            month=posting_date.month,
            status='closed'
        ).exists()
        if period_closed:
            return Response(
                {'detail': f'{posting_date.year}년 {posting_date.month}월은 마감된 회계기간입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if move.state != 'DRAFT':
            return Response({'detail': f'DRAFT 상태만 확정 가능합니다. 현재: {move.state}'}, status=400)
        move.state    = 'POSTED'
        move.posted_at = timezone.now()
        move.save(update_fields=['state', 'posted_at'])
        return Response(AccountMoveSerializer(move).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """전표 취소"""
        move = self.get_object()
        if move.state == 'CANCELLED':
            return Response({'detail': '이미 취소된 전표입니다.'}, status=400)
        move.state = 'CANCELLED'
        move.save(update_fields=['state'])
        return Response(AccountMoveSerializer(move).data)

    @action(detail=False, methods=['get'])
    def aging(self, request):
        """
        AR/AP 나이분석 — 전표 라인 기준 5구간 집계.

        Query Params:
            type: 'receivable' (매출채권) | 'payable' (매입채무)
        """
        aging_type = request.query_params.get('type', 'receivable')
        today = date.today()

        if aging_type == 'receivable':
            move_types = ['SALE', 'RECEIPT']
        else:
            move_types = ['PURCHASE', 'PAYMENT']

        lines = AccountMoveLine.objects.filter(
            move__company=request.user.company,
            move__state='POSTED',
            move__move_type__in=move_types,
            is_reconciled=False,
            due_date__isnull=False,
        ).select_related('move', 'account')

        records = []
        for line in lines:
            amount = float(line.debit) - float(line.credit)
            if abs(amount) < 0.01:
                continue
            records.append({
                'due_date':     str(line.due_date),
                'amount':       abs(amount),
                'account_code': line.account.code,
                'account_name': line.account.name,
                'move_number':  line.move.move_number,
                'days_overdue': (today - line.due_date).days,
            })

        # 구간별 분류
        buckets = {
            'not_due': [],
            '0_30':    [],
            '31_60':   [],
            '61_90':   [],
            'over_90': [],
        }
        for rec in records:
            d = rec['days_overdue']
            if d < 0:
                buckets['not_due'].append(rec)
            elif d <= 30:
                buckets['0_30'].append(rec)
            elif d <= 60:
                buckets['31_60'].append(rec)
            elif d <= 90:
                buckets['61_90'].append(rec)
            else:
                buckets['over_90'].append(rec)

        summary = {
            key: {
                'count':  len(v),
                'amount': round(sum(r['amount'] for r in v), 2),
            }
            for key, v in buckets.items()
        }

        return Response({
            'type':    aging_type,
            'as_of':   str(today),
            'summary': summary,
            'records': records,
        })


class BudgetViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'fi'
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['budget_year', 'budget_month', 'account']
    ordering_fields = ['budget_year', 'budget_month']

    def get_queryset(self):
        return Budget.objects.filter(
            company=self.request.user.company
        ).select_related('account').order_by('-budget_year', 'budget_month')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class FixedAssetViewSet(viewsets.ModelViewSet):
    serializer_class = FixedAssetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['asset_code', 'asset_name', 'location']
    filterset_fields = ['category', 'status', 'depreciation_method']
    ordering_fields = ['asset_code', 'acquisition_date']

    def get_queryset(self):
        return FixedAsset.objects.filter(
            company=self.request.user.company
        ).prefetch_related('schedules').order_by('asset_code')

    def perform_create(self, serializer):
        asset = serializer.save(company=self.request.user.company)
        # 취득 시 book_value = acquisition_cost
        asset.book_value = asset.acquisition_cost
        asset.save(update_fields=['book_value'])

    @action(detail=True, methods=['post'])
    def depreciate(self, request, pk=None):
        """감가상각 스케줄 생성 (연간 정액/정률법)."""
        asset = self.get_object()
        method_map = {'straight_line': 'SL', 'declining': 'DB'}
        method = method_map.get(asset.depreciation_method, 'SL')

        schedule = calc_depreciation_schedule(
            asset_value=asset.acquisition_cost,
            salvage_value=asset.salvage_value,
            useful_life=asset.useful_life_years,
            method=method,
            start_date=asset.acquisition_date,
        )

        created = []
        for entry in schedule:
            obj, _ = DepreciationSchedule.objects.update_or_create(
                asset=asset,
                period_year=entry['year'] + asset.acquisition_date.year - 1,
                period_month=asset.acquisition_date.month,
                defaults={
                    'depreciation_amount': entry['depreciation'],
                    'accumulated_amount': asset.acquisition_cost - entry['book_value'],
                    'book_value_after': entry['book_value'],
                },
            )
            created.append(obj)

        from .serializers import DepreciationScheduleSerializer
        return Response({
            'asset_code': asset.asset_code,
            'schedules':  DepreciationScheduleSerializer(created, many=True).data,
        })


class TaxInvoiceViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'fi'
    serializer_class = TaxInvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['invoice_number', 'counterpart']
    filterset_fields = ['invoice_type', 'status']
    ordering_fields = ['issue_date', 'created_at']

    def get_queryset(self):
        return TaxInvoice.objects.filter(
            company=self.request.user.company
        ).order_by('-issue_date')

    def perform_create(self, serializer):
        invoice_number = f'TAX-{uuid.uuid4().hex[:8].upper()}'
        supply = serializer.validated_data.get('supply_amount', Decimal('0'))
        vat    = round(supply * Decimal('0.1'), 2)
        total  = supply + vat
        serializer.save(
            company=self.request.user.company,
            invoice_number=invoice_number,
            vat_amount=vat,
            total_amount=total,
        )

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """세금계산서 발행 (draft → issued)"""
        inv = self.get_object()
        if inv.status != 'draft':
            return Response({'detail': f'draft 상태만 발행 가능합니다. 현재: {inv.status}'}, status=400)
        inv.status = 'issued'
        inv.save(update_fields=['status'])
        return Response(TaxInvoiceSerializer(inv).data)

    @action(detail=True, methods=['post'], url_path='issue-nts')
    def issue_nts(self, request, pk=None):
        """
        국세청 ASP 전자세금계산서 발행.
        NTS_ASP_CERT_KEY 환경변수 미설정 시 503 반환.
        """
        from .nts_service import NTSASPClient, NTSServiceDisabled, build_payload_from_invoice
        inv = self.get_object()
        if inv.status != 'issued':
            return Response({'detail': '먼저 내부 발행(issue)을 완료하세요.'}, status=400)
        try:
            client  = NTSASPClient()
            payload = build_payload_from_invoice(inv)
            result  = client.issue(payload)
            # 승인번호 저장 (nts_confirm_num 필드가 있다면)
            if hasattr(inv, 'nts_confirm_num') and result.get('nts_confirm_num'):
                inv.nts_confirm_num = result['nts_confirm_num']
                inv.status = 'nts_issued'
                inv.save(update_fields=['nts_confirm_num', 'status'])
            return Response({'detail': '국세청 전자세금계산서가 발행되었습니다.', **result})
        except NTSServiceDisabled as e:
            return Response({'detail': str(e), 'code': 'NTS_DISABLED'}, status=503)
        except Exception as e:
            return Response({'detail': f'ASP 오류: {e}'}, status=502)

    @action(detail=True, methods=['post'], url_path='cancel-nts')
    def cancel_nts(self, request, pk=None):
        """국세청 ASP 전자세금계산서 취소."""
        from .nts_service import NTSASPClient, NTSServiceDisabled
        inv = self.get_object()
        confirm_num = getattr(inv, 'nts_confirm_num', None)
        if not confirm_num:
            return Response({'detail': '국세청 승인번호(nts_confirm_num)가 없습니다.'}, status=400)
        try:
            client = NTSASPClient()
            result = client.cancel(confirm_num, reason=request.data.get('reason', ''))
            inv.status = 'nts_cancelled'
            inv.save(update_fields=['status'])
            return Response({'detail': '취소되었습니다.', **result})
        except NTSServiceDisabled as e:
            return Response({'detail': str(e), 'code': 'NTS_DISABLED'}, status=503)
        except Exception as e:
            return Response({'detail': f'ASP 오류: {e}'}, status=502)

    @action(detail=False, methods=['get'], url_path='nts-status')
    def nts_status(self, request):
        """국세청 ASP 연동 활성화 여부 확인."""
        from .nts_service import is_enabled, _get_config
        cfg = _get_config()
        return Response({
            'enabled':  is_enabled(),
            'provider': cfg['provider'],
            'base_url': cfg['base_url'] if is_enabled() else None,
            'message':  ('연동 활성화됨' if is_enabled()
                         else 'NTS_ASP_CERT_KEY 환경변수를 설정하면 활성화됩니다.'),
        })


class AccountingPeriodViewSet(viewsets.ModelViewSet):
    serializer_class = AccountingPeriodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AccountingPeriod.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=True, methods=['post'], url_path='close')
    def close_period(self, request, pk=None):
        period = self.get_object()
        if period.status == 'closed':
            return Response({'detail': '이미 마감된 기간입니다.'}, status=400)
        period.status = 'closed'
        period.closed_by = request.user
        period.closed_at = timezone.now()
        period.save(update_fields=['status', 'closed_by', 'closed_at'])
        return Response(AccountingPeriodSerializer(period).data)

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen_period(self, request, pk=None):
        period = self.get_object()
        if period.status == 'open':
            return Response({'detail': '이미 열린 기간입니다.'}, status=400)
        period.status = 'open'
        period.closed_by = None
        period.closed_at = None
        period.save(update_fields=['status', 'closed_by', 'closed_at'])
        return Response(AccountingPeriodSerializer(period).data)


# ──────────────────────────────────────────────────────────────
# 재무제표 자동생성 API
# GET /api/fi/statements/income/?year=2026&month=3   → 손익계산서
# GET /api/fi/statements/balance/?year=2026&month=3  → 대차대조표
# ──────────────────────────────────────────────────────────────

class FinancialStatementView(APIView):
    """
    확정(POSTED) 전표 라인을 계정과목 유형별로 집계해
    손익계산서(Income Statement)와 대차대조표(Balance Sheet)를 반환합니다.

    Query params:
        year  (int, 필수)
        month (int, 선택 — 없으면 해당 연도 전체)
        type  'income' | 'balance' (기본 income)
    """
    permission_classes = [IsAuthenticated]

    def _date_range(self, year, month):
        if month:
            start = datetime.date(year, month, 1)
            if month == 12:
                end = datetime.date(year + 1, 1, 1)
            else:
                end = datetime.date(year, month + 1, 1)
        else:
            start = datetime.date(year, 1, 1)
            end   = datetime.date(year + 1, 1, 1)
        return start, end

    def _aggregate_lines(self, company, start, end, account_types):
        """계정유형 목록에 해당하는 전표라인을 계정별로 집계."""
        lines = (
            AccountMoveLine.objects
            .filter(
                move__company=company,
                move__state='POSTED',
                move__posting_date__gte=start,
                move__posting_date__lt=end,
                account__account_type__in=account_types,
            )
            .values('account__code', 'account__name', 'account__account_type')
            .annotate(total_debit=Sum('debit'), total_credit=Sum('credit'))
            .order_by('account__code')
        )
        return list(lines)

    def get(self, request):
        company = request.user.company
        if not company:
            return Response({'detail': '회사 정보가 없습니다.'}, status=400)

        try:
            year  = int(request.query_params.get('year',  timezone.now().year))
            month = request.query_params.get('month')
            month = int(month) if month else None
            stmt_type = request.query_params.get('type', 'income')
        except (ValueError, TypeError):
            return Response({'detail': 'year/month는 정수여야 합니다.'}, status=400)

        start, end = self._date_range(year, month)
        period_label = f"{year}년 {month}월" if month else f"{year}년"

        if stmt_type == 'income':
            return self._income_statement(company, start, end, period_label)
        elif stmt_type == 'balance':
            return self._balance_sheet(company, start, end, period_label)
        else:
            return Response({'detail': "type은 'income' 또는 'balance'여야 합니다."}, status=400)

    def _income_statement(self, company, start, end, period_label):
        """손익계산서: 수익 - 비용 = 당기순이익."""
        revenue_lines  = self._aggregate_lines(company, start, end, ['REVENUE'])
        expense_lines  = self._aggregate_lines(company, start, end, ['EXPENSE'])

        def net(line):
            return float(line['total_credit'] or 0) - float(line['total_debit'] or 0)

        revenues  = [{'code': l['account__code'], 'name': l['account__name'],
                      'amount': net(l)} for l in revenue_lines]
        expenses  = [{'code': l['account__code'], 'name': l['account__name'],
                      'amount': -net(l)} for l in expense_lines]  # 비용은 debit이 증가

        total_revenue = sum(r['amount'] for r in revenues)
        total_expense = sum(e['amount'] for e in expenses)
        net_income    = total_revenue - total_expense

        return Response({
            'type': 'income_statement',
            'period': period_label,
            'revenues': revenues,
            'expenses': expenses,
            'total_revenue': round(total_revenue, 2),
            'total_expense': round(total_expense, 2),
            'net_income':    round(net_income, 2),
            'generated_at':  timezone.now().isoformat(),
        })

    def _balance_sheet(self, company, start, end, period_label):
        """
        대차대조표: 자산 = 부채 + 자본
        누적 기준 — start를 회계 시작(연초)으로, end를 조회 기준일로 사용.
        """
        asset_lines     = self._aggregate_lines(company, start, end, ['ASSET'])
        liability_lines = self._aggregate_lines(company, start, end, ['LIABILITY'])
        equity_lines    = self._aggregate_lines(company, start, end, ['EQUITY'])

        def asset_net(line):   # 자산: debit 증가
            return float(line['total_debit'] or 0) - float(line['total_credit'] or 0)

        def liab_net(line):    # 부채·자본: credit 증가
            return float(line['total_credit'] or 0) - float(line['total_debit'] or 0)

        assets      = [{'code': l['account__code'], 'name': l['account__name'],
                        'amount': asset_net(l)} for l in asset_lines]
        liabilities = [{'code': l['account__code'], 'name': l['account__name'],
                        'amount': liab_net(l)} for l in liability_lines]
        equities    = [{'code': l['account__code'], 'name': l['account__name'],
                        'amount': liab_net(l)} for l in equity_lines]

        total_assets      = sum(a['amount'] for a in assets)
        total_liabilities = sum(l['amount'] for l in liabilities)
        total_equity      = sum(e['amount'] for e in equities)

        return Response({
            'type': 'balance_sheet',
            'period': period_label,
            'assets':      assets,
            'liabilities': liabilities,
            'equity':      equities,
            'total_assets':      round(total_assets, 2),
            'total_liabilities': round(total_liabilities, 2),
            'total_equity':      round(total_equity, 2),
            'is_balanced':       round(total_assets, 2) == round(total_liabilities + total_equity, 2),
            'generated_at':      timezone.now().isoformat(),
        })
