import uuid
from decimal import Decimal

from django.db.models import Sum, Q, Count
from django.utils import timezone

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from django_filters.rest_framework import DjangoFilterBackend

from .models import Account, AccountMove, AccountMoveLine, TaxInvoice
from .serializers import (
    AccountSerializer,
    AccountMoveSerializer,
    AccountMoveLineSerializer,
    TaxInvoiceSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """계정과목 CRUD + 잔액 조회"""
    serializer_class   = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields      = ['code', 'name', 'root_type']
    ordering_fields    = ['code', 'name', 'account_type']
    filterset_fields   = ['account_type', 'is_group', 'is_active']

    def get_queryset(self):
        return Account.objects.filter(
            company=self.request.user.company,
            is_active=True,
        ).order_by('code')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    # ------------------------------------------------------------------ #
    #  POST /api/fi/accounts/{id}/balance/                                #
    #  계정 잔액 조회: 기간별 차변/대변 집계                              #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['get'], url_path='balance')
    def balance(self, request, pk=None):
        account = self.get_object()

        year  = request.query_params.get('year')
        month = request.query_params.get('month')

        # POSTED 확정 전표 라인만 집계
        qs = AccountMoveLine.objects.filter(
            account=account,
            move__state='POSTED',
            move__company=request.user.company,
        )

        if year:
            qs = qs.filter(move__period_year=year)
        if month:
            qs = qs.filter(move__period_month=month)

        agg = qs.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        total_debit  = agg['total_debit']  or Decimal('0')
        total_credit = agg['total_credit'] or Decimal('0')

        # 계정 유형별 잔액 방향
        debit_normal_types = {'ASSET', 'EXPENSE'}
        if account.account_type in debit_normal_types:
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        return Response({
            'account_id':   account.id,
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'period_year':  year,
            'period_month': month,
            'total_debit':  total_debit,
            'total_credit': total_credit,
            'balance':      balance,
        })

    # ------------------------------------------------------------------ #
    #  GET /api/fi/accounts/balance_sheet/                                #
    #  회사 전체 계정 잔액 목록 (기간 필터 지원)                          #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='balance_sheet')
    def balance_sheet(self, request):
        year  = request.query_params.get('year')
        month = request.query_params.get('month')

        accounts = self.get_queryset().filter(is_group=False)
        result   = []

        for account in accounts:
            qs = AccountMoveLine.objects.filter(
                account=account,
                move__state='POSTED',
                move__company=request.user.company,
            )
            if year:
                qs = qs.filter(move__period_year=year)
            if month:
                qs = qs.filter(move__period_month=month)

            agg = qs.aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )
            total_debit  = agg['total_debit']  or Decimal('0')
            total_credit = agg['total_credit'] or Decimal('0')

            debit_normal_types = {'ASSET', 'EXPENSE'}
            if account.account_type in debit_normal_types:
                balance = total_debit - total_credit
            else:
                balance = total_credit - total_debit

            if total_debit or total_credit:
                result.append({
                    'account_id':   account.id,
                    'account_code': account.code,
                    'account_name': account.name,
                    'account_type': account.account_type,
                    'total_debit':  total_debit,
                    'total_credit': total_credit,
                    'balance':      balance,
                })

        return Response(result)


class AccountMoveViewSet(viewsets.ModelViewSet):
    """전표 CRUD + 확정(post) 액션"""
    serializer_class   = AccountMoveSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields      = ['move_number', 'ref', 'created_by']
    ordering_fields    = ['posting_date', 'move_number', 'created_at', 'total_debit']
    filterset_fields   = ['state', 'move_type', 'period_year', 'period_month', 'is_locked']

    def get_queryset(self):
        return AccountMove.objects.filter(
            company=self.request.user.company,
        ).prefetch_related('lines__account').order_by('-posting_date', '-created_at')

    def perform_create(self, serializer):
        move_number = serializer.validated_data.get('move_number') or f'JV-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(
            company    = self.request.user.company,
            created_by = self.request.user.name or self.request.user.email,
            move_number = move_number,
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.is_locked:
            raise PermissionDenied(
                '기간이 마감된 전표는 수정할 수 없습니다. '
                '관리자에게 마감 해제를 요청하세요.'
            )
        if instance.state == 'POSTED':
            raise PermissionDenied(
                '확정된 전표는 직접 수정할 수 없습니다. '
                '취소 후 재작성하거나 조정 전표를 사용하세요.'
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise PermissionDenied('기간이 마감된 전표는 삭제할 수 없습니다.')
        if instance.state == 'POSTED':
            raise PermissionDenied(
                '확정된 전표는 삭제할 수 없습니다. 먼저 취소 처리하세요.'
            )
        instance.delete()

    # ------------------------------------------------------------------ #
    #  POST /api/fi/moves/{id}/post/                                      #
    #  임시(DRAFT) → 확정(POSTED) 전환                                   #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='post')
    def post_move(self, request, pk=None):
        move = self.get_object()

        if move.is_locked:
            return Response(
                {'detail': '기간이 마감된 전표는 확정할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if move.state == 'POSTED':
            return Response(
                {'detail': '이미 확정된 전표입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if move.state == 'CANCELLED':
            return Response(
                {'detail': '취소된 전표는 확정할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 라인이 없는 경우 차단
        if not move.lines.exists():
            return Response(
                {'detail': '전표 라인이 없습니다. 라인 등록 후 확정하세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 대차 일치 검증 (model.save()에서도 검증되지만 명시적 메시지 제공)
        if move.total_debit != move.total_credit:
            return Response(
                {
                    'detail': '대차가 일치하지 않아 확정할 수 없습니다.',
                    'total_debit':  str(move.total_debit),
                    'total_credit': str(move.total_credit),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        move.state     = 'POSTED'
        move.posted_at = timezone.now()
        move.save()

        serializer = self.get_serializer(move)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  POST /api/fi/moves/{id}/cancel/                                    #
    #  확정(POSTED) → 취소(CANCELLED)                                    #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_move(self, request, pk=None):
        move = self.get_object()

        if move.is_locked:
            return Response(
                {'detail': '기간이 마감된 전표는 취소할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if move.state == 'CANCELLED':
            return Response(
                {'detail': '이미 취소된 전표입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if move.state == 'DRAFT':
            return Response(
                {'detail': '임시 전표는 삭제를 이용하세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        move.state = 'CANCELLED'
        move.save()

        serializer = self.get_serializer(move)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  GET /api/fi/moves/aging/                                           #
    #  매출채권/매입채무 나이분석 (AR/AP Aging)                           #
    #  ?type=receivable (기본) 또는 ?type=payable                         #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='aging')
    def aging(self, request):
        """
        매출채권/매입채무 나이분석.

        Query Params:
            type (str): 'receivable'(매출채권, 기본값) 또는 'payable'(매입채무)

        Returns:
            {
                type, move_type,
                not_due:  만기 미도래 합계,
                days_0_30:  0~30일 연체 합계,
                days_31_60: 31~60일 연체 합계,
                days_61_90: 61~90일 연체 합계,
                over_90:  90일 초과 연체 합계,
                total:    전체 미결제 합계,
                line_count: 집계 라인 수,
            }
        """
        today    = timezone.now().date()
        doc_type = request.query_params.get('type', 'receivable')

        # SALE 전표 = 매출채권(AR), PURCHASE 전표 = 매입채무(AP)
        move_type = 'SALE' if doc_type == 'receivable' else 'PURCHASE'

        # 미결제(is_reconciled=False), 만기일 존재, POSTED 확정 전표 라인만 대상
        qs = AccountMoveLine.objects.filter(
            move__company=request.user.company,
            move__move_type=move_type,
            move__state='POSTED',
            is_reconciled=False,
            due_date__isnull=False,
        ).select_related('move')

        # 버킷별 분류: Python-level iteration (라인 수가 많을 경우 raw SQL 전환 권장)
        buckets = {
            'not_due':    Decimal('0'),
            'days_0_30':  Decimal('0'),
            'days_31_60': Decimal('0'),
            'days_61_90': Decimal('0'),
            'over_90':    Decimal('0'),
        }
        line_count = 0

        for line in qs.only('debit', 'credit', 'due_date'):
            # 매출채권: debit 기준, 매입채무: credit 기준
            amount = line.debit if doc_type == 'receivable' else line.credit
            if not amount:
                # 방향이 반대인 조정 라인 — net 처리
                amount = (line.credit if doc_type == 'receivable' else line.debit) * Decimal('-1')

            days_overdue = (today - line.due_date).days

            if days_overdue <= 0:
                buckets['not_due']    += amount
            elif days_overdue <= 30:
                buckets['days_0_30']  += amount
            elif days_overdue <= 60:
                buckets['days_31_60'] += amount
            elif days_overdue <= 90:
                buckets['days_61_90'] += amount
            else:
                buckets['over_90']    += amount

            line_count += 1

        total = sum(buckets.values())

        return Response({
            'type':       doc_type,
            'move_type':  move_type,
            'not_due':    buckets['not_due'],
            'days_0_30':  buckets['days_0_30'],
            'days_31_60': buckets['days_31_60'],
            'days_61_90': buckets['days_61_90'],
            'over_90':    buckets['over_90'],
            'total':      total,
            'line_count': line_count,
            'as_of_date': str(today),
        })

    # ------------------------------------------------------------------ #
    #  GET /api/fi/moves/dashboard/                                       #
    #  전표 현황 요약                                                      #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        qs = self.get_queryset()

        year  = request.query_params.get('year')
        month = request.query_params.get('month')
        if year:
            qs = qs.filter(period_year=year)
        if month:
            qs = qs.filter(period_month=month)

        agg = qs.filter(state='POSTED').aggregate(
            posted_debit=Sum('total_debit'),
            posted_credit=Sum('total_credit'),
        )

        return Response({
            'total':     qs.count(),
            'draft':     qs.filter(state='DRAFT').count(),
            'posted':    qs.filter(state='POSTED').count(),
            'cancelled': qs.filter(state='CANCELLED').count(),
            'locked':    qs.filter(is_locked=True).count(),
            'posted_total_debit':  agg['posted_debit']  or Decimal('0'),
            'posted_total_credit': agg['posted_credit'] or Decimal('0'),
        })


class TaxInvoiceViewSet(viewsets.ModelViewSet):
    """
    세금계산서 CRUD + 상태 전환 액션

    GET    /api/fi/tax-invoices/              - 목록
    POST   /api/fi/tax-invoices/              - 생성
    GET    /api/fi/tax-invoices/{id}/         - 상세
    PUT    /api/fi/tax-invoices/{id}/         - 수정
    DELETE /api/fi/tax-invoices/{id}/         - 삭제

    POST   /api/fi/tax-invoices/{id}/issue/   - DRAFT → ISSUED
    POST   /api/fi/tax-invoices/{id}/cancel/  - ISSUED → CANCELLED
    GET    /api/fi/tax-invoices/summary/      - 기간별 집계 요약
    """
    serializer_class   = TaxInvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields      = ['invoice_number', 'supplier_or_customer_name']
    ordering_fields    = ['issue_date', 'invoice_number', 'supply_amount', 'created_at']
    filterset_fields   = ['invoice_type', 'status']

    def get_queryset(self):
        return TaxInvoice.objects.filter(
            company=self.request.user.company,
        ).select_related('account_move', 'created_by').order_by('-issue_date', '-created_at')

    def perform_create(self, serializer):
        invoice_number = serializer.validated_data.get('invoice_number') or f'INV-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(
            company        = self.request.user.company,
            created_by     = self.request.user,
            invoice_number = invoice_number,
        )

    def perform_destroy(self, instance):
        if instance.status == 'ISSUED':
            raise PermissionDenied('발행된 세금계산서는 삭제할 수 없습니다. 먼저 취소 처리하세요.')
        instance.delete()

    # ------------------------------------------------------------------ #
    #  POST /api/fi/tax-invoices/{id}/issue/                              #
    #  DRAFT → ISSUED                                                     #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status != 'DRAFT':
            return Response(
                {'detail': f"임시(DRAFT) 상태의 세금계산서만 발행할 수 있습니다. "
                           f"현재 상태: {invoice.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = 'ISSUED'
        invoice.save(update_fields=['status'])

        serializer = self.get_serializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  POST /api/fi/tax-invoices/{id}/cancel/                             #
    #  ISSUED → CANCELLED                                                 #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status == 'CANCELLED':
            return Response(
                {'detail': '이미 취소된 세금계산서입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if invoice.status == 'DRAFT':
            return Response(
                {'detail': '임시 세금계산서는 삭제를 이용하세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = 'CANCELLED'
        invoice.save(update_fields=['status'])

        serializer = self.get_serializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  GET /api/fi/tax-invoices/summary/                                  #
    #  기간별 매입/매출 세금계산서 집계                                    #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        qs = self.get_queryset().filter(status='ISSUED')

        year  = request.query_params.get('year')
        month = request.query_params.get('month')
        if year:
            qs = qs.filter(issue_date__year=year)
        if month:
            qs = qs.filter(issue_date__month=month)

        purchase_agg = qs.filter(invoice_type='PURCHASE').aggregate(
            supply_total = Sum('supply_amount'),
            tax_total    = Sum('tax_amount'),
            total_total  = Sum('total_amount'),
        )
        sale_agg = qs.filter(invoice_type='SALE').aggregate(
            supply_total = Sum('supply_amount'),
            tax_total    = Sum('tax_amount'),
            total_total  = Sum('total_amount'),
        )

        purchase_supply = purchase_agg['supply_total'] or Decimal('0')
        purchase_tax    = purchase_agg['tax_total']    or Decimal('0')
        sale_supply     = sale_agg['supply_total']     or Decimal('0')
        sale_tax        = sale_agg['tax_total']        or Decimal('0')

        return Response({
            'period': {'year': year, 'month': month},
            'purchase': {
                'count':        qs.filter(invoice_type='PURCHASE').count(),
                'supply_total': purchase_supply,
                'tax_total':    purchase_tax,
                'total_amount': purchase_agg['total_total'] or Decimal('0'),
            },
            'sale': {
                'count':        qs.filter(invoice_type='SALE').count(),
                'supply_total': sale_supply,
                'tax_total':    sale_tax,
                'total_amount': sale_agg['total_total'] or Decimal('0'),
            },
            'net_vat_payable': sale_tax - purchase_tax,
        })
