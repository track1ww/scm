import uuid
from decimal import Decimal

from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Customer, SalesOrder, Delivery
from .serializers import CustomerSerializer, SalesOrderSerializer, DeliverySerializer


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['customer_code', 'customer_name', 'contact', 'email']
    ordering_fields  = ['customer_name', 'created_at']

    def get_queryset(self):
        return Customer.objects.filter(
            company=self.request.user.company
        ).order_by('customer_name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class SalesOrderViewSet(viewsets.ModelViewSet):
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['order_number', 'customer_name', 'item_name']
    filterset_fields = ['status', 'customer']
    ordering_fields  = ['ordered_at', 'order_number']

    def get_queryset(self):
        return SalesOrder.objects.filter(
            company=self.request.user.company
        ).select_related('customer').order_by('-ordered_at')

    def perform_create(self, serializer):
        # Auto-generate order_number if not provided
        order_number = serializer.validated_data.get('order_number') or f'SO-{uuid.uuid4().hex[:8].upper()}'
        # Auto-populate customer_name from the customer FK if not provided
        customer = serializer.validated_data.get('customer')
        customer_name = serializer.validated_data.get('customer_name', '')
        if not customer_name and customer:
            customer_name = customer.customer_name
        serializer.save(
            company=self.request.user.company,
            order_number=order_number,
            customer_name=customer_name,
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """draft → confirmed 상태로 확정 처리"""
        order = self.get_object()
        if order.status != 'draft':
            return Response(
                {'detail': f'draft 상태인 경우에만 확정할 수 있습니다. 현재 상태: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'confirmed'
        order.save(update_fields=['status'])
        return Response(SalesOrderSerializer(order).data)

    # ------------------------------------------------------------------ #
    #  GET /api/sd/sales-orders/revenue_analysis/                        #
    #  매출 분석: 월별 추이, 고객별 Top10, 제품별 Top10                  #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='revenue_analysis')
    def revenue_analysis(self, request):
        """
        매출 분석 리포트.

        Query Params:
            months (int): 조회 개월 수 (기본값 12, 최대 60)

        Returns:
            monthly_trend:      월별 매출 추이 (수주금액, 건수)
            top_customers:      고객별 매출 Top 10
            top_items:          제품별 매출 Top 10
            period_summary:     기간 전체 합계
        """
        today = timezone.now().date()

        # 조회 기간: 기본 최근 12개월
        try:
            months = max(1, min(int(request.query_params.get('months', 12)), 60))
        except (ValueError, TypeError):
            months = 12

        # 시작 월 계산
        start_month = today.month - months
        start_year  = today.year
        while start_month <= 0:
            start_month += 12
            start_year  -= 1
        period_start = today.replace(year=start_year, month=start_month, day=1)

        # 취소 제외, 기간 내 수주 기준 (ordered_at)
        qs = SalesOrder.objects.filter(
            company=request.user.company,
            ordered_at__date__gte=period_start,
        ).exclude(status='cancelled')

        # 매출금액 표현식: quantity * unit_price * (1 - discount_rate / 100)
        revenue_expr = ExpressionWrapper(
            F('quantity') * F('unit_price') * (
                1 - F('discount_rate') / Decimal('100')
            ),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )

        # ── 1. 월별 매출 추이 ─────────────────────────────────────────── #
        monthly_raw = (
            qs.annotate(
                yr=F('ordered_at__year'),
                mo=F('ordered_at__month'),
            )
            .values('yr', 'mo')
            .annotate(
                order_count=Count('id'),
                revenue=Sum(revenue_expr),
            )
            .order_by('yr', 'mo')
        )
        monthly_trend = [
            {
                'year':        row['yr'],
                'month':       row['mo'],
                'period':      f"{row['yr']}-{str(row['mo']).zfill(2)}",
                'order_count': row['order_count'],
                'revenue':     row['revenue'] or Decimal('0'),
            }
            for row in monthly_raw
        ]

        # ── 2. 고객별 매출 Top 10 ─────────────────────────────────────── #
        top_customers_raw = (
            qs.values('customer_id', 'customer_name')
            .annotate(
                order_count=Count('id'),
                revenue=Sum(revenue_expr),
            )
            .order_by('-revenue')[:10]
        )
        top_customers = [
            {
                'customer_id':   row['customer_id'],
                'customer_name': row['customer_name'],
                'order_count':   row['order_count'],
                'revenue':       row['revenue'] or Decimal('0'),
            }
            for row in top_customers_raw
        ]

        # ── 3. 제품별 매출 Top 10 ─────────────────────────────────────── #
        top_items_raw = (
            qs.values('item_name')
            .annotate(
                order_count=Count('id'),
                total_qty=Sum('quantity'),
                revenue=Sum(revenue_expr),
            )
            .order_by('-revenue')[:10]
        )
        top_items = [
            {
                'item_name':   row['item_name'],
                'order_count': row['order_count'],
                'total_qty':   row['total_qty'],
                'revenue':     row['revenue'] or Decimal('0'),
            }
            for row in top_items_raw
        ]

        # ── 4. 기간 전체 요약 ─────────────────────────────────────────── #
        period_agg = qs.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum(revenue_expr),
        )

        return Response({
            'period': {
                'start':  str(period_start),
                'end':    str(today),
                'months': months,
            },
            'period_summary': {
                'total_orders':  period_agg['total_orders'] or 0,
                'total_revenue': period_agg['total_revenue'] or Decimal('0'),
            },
            'monthly_trend': monthly_trend,
            'top_customers': top_customers,
            'top_items':     top_items,
        })

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """판매 현황 대시보드 요약"""
        qs = self.get_queryset()
        return Response({
            'total':         qs.count(),
            'order_received': qs.filter(status='draft').count(),
            'in_progress':   qs.filter(status='confirmed').count(),
            'ready_to_ship': qs.filter(status='ready').count(),
            'in_delivery':   qs.filter(status='in_delivery').count(),
            'delivered':     qs.filter(status='delivered').count(),
            'cancelled':     qs.filter(status='cancelled').count(),
        })


class DeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = DeliverySerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['delivery_number', 'item_name', 'tracking_number']
    filterset_fields = ['status', 'order']
    ordering_fields  = ['created_at', 'delivery_date']

    def get_queryset(self):
        return Delivery.objects.filter(
            company=self.request.user.company
        ).select_related('order').order_by('-created_at')

    def perform_create(self, serializer):
        # Auto-generate delivery_number if not provided
        delivery_number = serializer.validated_data.get('delivery_number') or f'DL-{uuid.uuid4().hex[:8].upper()}'
        # Auto-populate item_name from the order FK if not provided
        order = serializer.validated_data.get('order')
        item_name = serializer.validated_data.get('item_name', '')
        if not item_name and order:
            item_name = order.item_name
        serializer.save(
            company=self.request.user.company,
            delivery_number=delivery_number,
            item_name=item_name,
        )

    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        """출하 확정: pending → shipped 처리 및 연관 수주 상태 갱신"""
        delivery = self.get_object()
        if delivery.status != 'pending':
            return Response(
                {'detail': f'출하준비(pending) 상태인 경우에만 출하 확정할 수 있습니다. 현재 상태: {delivery.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery.status = 'shipped'
        if not delivery.delivery_date:
            delivery.delivery_date = timezone.now().date()
        delivery.save(update_fields=['status', 'delivery_date'])

        # 연관 수주(SalesOrder) 상태를 배송중으로 갱신
        if delivery.order and delivery.order.status not in ('in_delivery', 'delivered', 'cancelled'):
            delivery.order.status = 'in_delivery'
            delivery.order.shipped_qty = (
                delivery.order.shipped_qty + delivery.delivery_qty
            )
            delivery.order.save(update_fields=['status', 'shipped_qty'])

        return Response(DeliverySerializer(delivery).data)
