from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from scm_mm.models import Material
from .models import BOM, BOMLine, ProductionOrder, MRPPlan
from .serializers import (
    BOMSerializer, BOMWriteSerializer, BOMLineSerializer,
    ProductionOrderSerializer, MRPPlanSerializer,
)


class BOMViewSet(viewsets.ModelViewSet):
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['material__material_code', 'material__material_name', 'version']
    ordering_fields  = ['created_at', 'version']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BOMWriteSerializer
        return BOMSerializer

    def get_queryset(self):
        return BOM.objects.filter(
            company=self.request.user.company
        ).select_related('material').prefetch_related('lines__component_material').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class BOMLineViewSet(viewsets.ModelViewSet):
    serializer_class = BOMLineSerializer

    def get_queryset(self):
        return BOMLine.objects.filter(
            bom__company=self.request.user.company
        ).select_related('bom', 'component_material')


class ProductionOrderViewSet(viewsets.ModelViewSet):
    serializer_class = ProductionOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['order_number', 'bom__material__material_name']
    filterset_fields = ['status']
    ordering_fields  = ['created_at', 'planned_start', 'planned_end']

    def get_queryset(self):
        return ProductionOrder.objects.filter(
            company=self.request.user.company
        ).select_related('bom__material', 'created_by').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """DRAFT 상태의 생산오더를 RELEASED 로 전환합니다."""
        order = self.get_object()
        if order.status != 'DRAFT':
            return Response(
                {'detail': f'DRAFT 상태만 릴리즈 가능합니다. 현재 상태: {order.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = 'RELEASED'
        order.save(update_fields=['status'])
        return Response(ProductionOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """생산오더를 완료 처리합니다. actual_qty 를 body 에서 받습니다."""
        order = self.get_object()
        if order.status not in ('RELEASED', 'IN_PROGRESS'):
            return Response(
                {'detail': f'완료 처리할 수 없는 상태입니다. 현재 상태: {order.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actual_qty = request.data.get('actual_qty')
        if actual_qty is not None:
            order.actual_qty = Decimal(str(actual_qty))
        order.status     = 'COMPLETED'
        order.actual_end = timezone.now().date()
        order.save(update_fields=['status', 'actual_qty', 'actual_end'])
        return Response(ProductionOrderSerializer(order).data)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """생산오더 현황 대시보드 데이터를 반환합니다."""
        qs = self.get_queryset()
        status_summary = (
            qs.values('status')
            .annotate(count=Count('id'))
        )
        status_map = {item['status']: item['count'] for item in status_summary}

        today = timezone.now().date()
        overdue_count = qs.filter(
            planned_end__lt=today,
            status__in=['RELEASED', 'IN_PROGRESS'],
        ).count()

        total_planned = qs.aggregate(s=Sum('planned_qty'))['s'] or Decimal('0')
        total_actual  = qs.aggregate(s=Sum('actual_qty'))['s']  or Decimal('0')
        completion_rate = None
        if total_planned > 0:
            completion_rate = round(float(total_actual / total_planned * 100), 1)

        return Response({
            'total':           qs.count(),
            'draft':           status_map.get('DRAFT', 0),
            'released':        status_map.get('RELEASED', 0),
            'in_progress':     status_map.get('IN_PROGRESS', 0),
            'completed':       status_map.get('COMPLETED', 0),
            'cancelled':       status_map.get('CANCELLED', 0),
            'overdue':         overdue_count,
            'completion_rate': completion_rate,
        })


class MRPPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MRPPlanSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['material__material_code', 'material__material_name']
    filterset_fields = ['status', 'plan_date']
    ordering_fields  = ['plan_date', 'shortage_qty']

    def get_queryset(self):
        return MRPPlan.objects.filter(
            company=self.request.user.company
        ).select_related('material').order_by('-plan_date', 'material')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['post'])
    def run_mrp(self, request):
        """
        MRP 자동 계산 액션.
        릴리즈/진행 중인 생산오더의 BOM 을 전개하여 재고 부족 품목을 자동으로 MRPPlan 에 생성합니다.
        요청 body: { "plan_date": "YYYY-MM-DD" }  (생략 시 오늘)
        """
        from datetime import date as date_cls

        plan_date_raw = request.data.get('plan_date')
        try:
            plan_date = date_cls.fromisoformat(plan_date_raw) if plan_date_raw else timezone.now().date()
        except ValueError:
            return Response(
                {'detail': 'plan_date 형식이 올바르지 않습니다. YYYY-MM-DD 로 입력하세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = request.user.company

        # 릴리즈/진행 중인 생산오더 대상
        active_orders = ProductionOrder.objects.filter(
            company=company,
            status__in=['RELEASED', 'IN_PROGRESS'],
        ).select_related('bom').prefetch_related('bom__lines__component_material')

        # 자재별 소요량 집계
        demand: dict = {}
        for order in active_orders:
            if not order.bom:
                continue
            remaining = order.planned_qty - order.actual_qty
            if remaining <= 0:
                continue
            for line in order.bom.lines.all():
                mat_id = line.component_material_id
                demand[mat_id] = demand.get(mat_id, Decimal('0')) + (line.quantity * remaining)

        if not demand:
            return Response({'detail': '소요량을 계산할 활성 생산오더가 없습니다.', 'created': 0})

        materials = Material.objects.filter(id__in=demand.keys(), company=company)
        mat_map   = {m.id: m for m in materials}

        created_count = 0
        plans_created = []

        for mat_id, required_qty in demand.items():
            material = mat_map.get(mat_id)
            if not material:
                continue

            # 가용 재고는 실재고 모듈 연동 전까지 0 처리 (확장 포인트)
            available_qty = Decimal('0')
            shortage_qty  = max(required_qty - available_qty, Decimal('0'))
            suggested_qty = shortage_qty

            plan, created = MRPPlan.objects.update_or_create(
                company=company,
                plan_date=plan_date,
                material=material,
                defaults={
                    'required_qty':        required_qty,
                    'available_qty':       available_qty,
                    'shortage_qty':        shortage_qty,
                    'suggested_order_qty': suggested_qty,
                    'status':              'PENDING',
                },
            )
            if created:
                created_count += 1
            plans_created.append(MRPPlanSerializer(plan).data)

        return Response({
            'detail':    f'MRP 계산 완료. 신규 {created_count}건 생성.',
            'plan_date': str(plan_date),
            'total':     len(plans_created),
            'plans':     plans_created,
        })
