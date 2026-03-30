import uuid
from django.db.models import Count, Sum, Q
from django.utils import timezone

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django_filters.rest_framework import DjangoFilterBackend

from .models import Carrier, TransportOrder, TransportTracking
from .serializers import (
    CarrierSerializer,
    TransportOrderSerializer,
    TransportOrderListSerializer,
    TransportTrackingSerializer,
)


class CarrierViewSet(viewsets.ModelViewSet):
    """
    운송사 CRUD

    GET    /api/tm/carriers/           - 목록 (company 자동 필터)
    POST   /api/tm/carriers/           - 생성
    GET    /api/tm/carriers/{id}/      - 상세
    PUT    /api/tm/carriers/{id}/      - 수정
    DELETE /api/tm/carriers/{id}/      - 삭제
    """
    serializer_class = CarrierSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields    = ['carrier_code', 'name', 'contact_name', 'email']
    ordering_fields  = ['carrier_code', 'name', 'is_active']
    filterset_fields = ['is_active']

    def get_queryset(self):
        return Carrier.objects.filter(
            company=self.request.user.company,
        ).order_by('carrier_code')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class TransportOrderViewSet(viewsets.ModelViewSet):
    """
    운송지시 CRUD + 상태 전환 액션

    GET    /api/tm/orders/                  - 목록
    POST   /api/tm/orders/                  - 생성
    GET    /api/tm/orders/{id}/             - 상세 (tracking_records 포함)
    PUT    /api/tm/orders/{id}/             - 수정
    DELETE /api/tm/orders/{id}/             - 삭제

    POST   /api/tm/orders/{id}/dispatch/    - CONFIRMED → IN_TRANSIT
    POST   /api/tm/orders/{id}/complete/    - IN_TRANSIT → DELIVERED
    POST   /api/tm/orders/{id}/cancel/      - → CANCELLED
    GET    /api/tm/orders/dashboard/        - 현황 요약
    """
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields    = ['order_number', 'origin_address', 'destination_address',
                        'cargo_description', 'reference_number']
    ordering_fields  = ['order_number', 'planned_departure', 'planned_arrival',
                        'freight_cost', 'created_at']
    filterset_fields = ['status', 'reference_type', 'carrier']

    def get_queryset(self):
        return TransportOrder.objects.filter(
            company=self.request.user.company,
        ).select_related('carrier', 'created_by').prefetch_related('tracking_records')

    def get_serializer_class(self):
        if self.action == 'list':
            return TransportOrderListSerializer
        return TransportOrderSerializer

    def perform_create(self, serializer):
        order_number = serializer.validated_data.get('order_number') or f'TM-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(
            company      = self.request.user.company,
            created_by   = self.request.user,
            order_number = order_number,
        )

    # ------------------------------------------------------------------ #
    #  POST /api/tm/orders/{id}/dispatch/                                 #
    #  CONFIRMED → IN_TRANSIT                                             #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='dispatch')
    def dispatch(self, request, pk=None):
        order = self.get_object()

        if order.status != 'CONFIRMED':
            return Response(
                {'detail': f"확정(CONFIRMED) 상태의 운송지시만 출발 처리할 수 있습니다. "
                           f"현재 상태: {order.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status           = 'IN_TRANSIT'
        order.actual_departure = timezone.now()
        order.save(update_fields=['status', 'actual_departure'])

        serializer = TransportOrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  POST /api/tm/orders/{id}/complete/                                 #
    #  IN_TRANSIT → DELIVERED                                             #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        order = self.get_object()

        if order.status != 'IN_TRANSIT':
            return Response(
                {'detail': f"운송중(IN_TRANSIT) 상태의 운송지시만 완료 처리할 수 있습니다. "
                           f"현재 상태: {order.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status         = 'DELIVERED'
        order.actual_arrival = timezone.now()
        order.save(update_fields=['status', 'actual_arrival'])

        serializer = TransportOrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  POST /api/tm/orders/{id}/cancel/                                   #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.status in ('DELIVERED', 'CANCELLED'):
            return Response(
                {'detail': f"배송완료 또는 이미 취소된 운송지시는 취소할 수 없습니다. "
                           f"현재 상태: {order.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = 'CANCELLED'
        order.save(update_fields=['status'])

        serializer = TransportOrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  GET /api/tm/orders/dashboard/                                      #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        qs = self.get_queryset()

        # 기간 필터 (planned_departure 기준)
        date_from = request.query_params.get('date_from')
        date_to   = request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(planned_departure__date__gte=date_from)
        if date_to:
            qs = qs.filter(planned_departure__date__lte=date_to)

        agg = qs.aggregate(
            total_freight  = Sum('freight_cost'),
            total_weight   = Sum('weight_kg'),
            total_volume   = Sum('volume_cbm'),
        )

        # 상태별 건수
        status_counts = {
            row['status']: row['cnt']
            for row in qs.values('status').annotate(cnt=Count('id'))
        }

        # 운송사별 건수 Top5
        carrier_top5 = list(
            qs.filter(carrier__isnull=False)
              .values('carrier__carrier_code', 'carrier__name')
              .annotate(cnt=Count('id'), freight_sum=Sum('freight_cost'))
              .order_by('-cnt')[:5]
        )

        return Response({
            'total':          qs.count(),
            'status_counts':  status_counts,
            'draft':          status_counts.get('DRAFT',      0),
            'confirmed':      status_counts.get('CONFIRMED',  0),
            'in_transit':     status_counts.get('IN_TRANSIT', 0),
            'delivered':      status_counts.get('DELIVERED',  0),
            'cancelled':      status_counts.get('CANCELLED',  0),
            'total_freight':  agg['total_freight'] or 0,
            'total_weight_kg':agg['total_weight']  or 0,
            'total_volume_cbm': agg['total_volume'] or 0,
            'carrier_top5':   carrier_top5,
        })


class TransportTrackingViewSet(viewsets.ModelViewSet):
    """
    운송 추적 이력 CRUD

    GET    /api/tm/tracking/           - 전체 목록 (transport_order 필터 지원)
    POST   /api/tm/tracking/           - 추적 기록 등록
    GET    /api/tm/tracking/{id}/      - 상세
    PUT    /api/tm/tracking/{id}/      - 수정
    DELETE /api/tm/tracking/{id}/      - 삭제
    """
    serializer_class = TransportTrackingSerializer
    filter_backends  = [filters.OrderingFilter, DjangoFilterBackend]
    ordering_fields  = ['timestamp']
    filterset_fields = ['transport_order']

    def get_queryset(self):
        return TransportTracking.objects.filter(
            transport_order__company=self.request.user.company,
        ).select_related('transport_order', 'recorded_by').order_by('-timestamp')

    def perform_create(self, serializer):
        # transport_order가 동일 company 소속인지 검증
        transport_order = serializer.validated_data.get('transport_order')
        if transport_order.company != self.request.user.company:
            raise ValidationError({'transport_order': '접근 권한이 없는 운송지시입니다.'})
        serializer.save(recorded_by=self.request.user)
