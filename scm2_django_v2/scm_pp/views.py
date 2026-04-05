from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import BillOfMaterial, BomLine, ProductionOrder, MrpRun, WorkCenterCost
from .serializers import (BillOfMaterialSerializer, BomLineSerializer,
                           ProductionOrderSerializer, MrpRunSerializer,
                           WorkCenterCostSerializer)
from scm_core.mixins import AuditLogMixin, StateLockMixin


class BillOfMaterialViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'pp'
    serializer_class = BillOfMaterialSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['bom_code', 'product_name']

    def get_queryset(self):
        return BillOfMaterial.objects.filter(
            company=self.request.user.company
        ).annotate(line_count=Count('lines')).prefetch_related('lines')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class BomLineViewSet(viewsets.ModelViewSet):
    serializer_class = BomLineSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['bom']

    def get_queryset(self):
        return BomLine.objects.filter(
            bom__company=self.request.user.company
        ).select_related('bom')


class ProductionOrderViewSet(AuditLogMixin, StateLockMixin, viewsets.ModelViewSet):
    audit_module = 'pp'
    locked_states = ['완료']
    serializer_class = ProductionOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['order_number', 'product_name']
    filterset_fields = ['status', 'work_center']
    ordering_fields  = ['planned_start', 'created_at']

    def get_queryset(self):
        return ProductionOrder.objects.filter(
            company=self.request.user.company
        ).select_related('bom').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':        qs.count(),
            'in_progress':  qs.filter(status='생산중').count(),
            'completed':    qs.filter(status='완료').count(),
            'planned':      qs.filter(status='계획').count(),
            'total_produced': qs.aggregate(s=Sum('produced_qty'))['s'] or 0,
            'total_defect':   qs.aggregate(s=Sum('defect_qty'))['s'] or 0,
        })


class WorkCenterCostViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """작업장별 원가 단가 (공정비·인건비·간접비) 관리."""
    audit_module     = 'pp'
    serializer_class = WorkCenterCostSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['work_center']
    search_fields    = ['work_center']

    def get_queryset(self):
        return WorkCenterCost.objects.filter(
            company=self.request.user.company
        ).order_by('work_center', '-effective_from')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class MrpRunViewSet(viewsets.ModelViewSet):
    serializer_class = MrpRunSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        return MrpRun.objects.filter(
            company=self.request.user.company
        ).order_by('-run_date')

    def perform_create(self, serializer):
        import uuid as _uuid
        run_number = f'MRP-{_uuid.uuid4().hex[:8].upper()}'
        serializer.save(company=self.request.user.company, run_number=run_number)

    @action(detail=False, methods=['post'], url_path='run_mrp')
    def run_mrp(self, request):
        """BOM 기반 자재 소요량 계획 실행."""
        import uuid as _uuid
        company = request.user.company
        run_number = f'MRP-{_uuid.uuid4().hex[:8].upper()}'

        pending_orders = ProductionOrder.objects.filter(
            company=company, status__in=['계획', '확정'],
        )

        total_items = planned_orders = 0
        summary = []

        for po in pending_orders:
            po_qty = float(getattr(po, 'planned_qty', getattr(po, 'quantity', 1)) or 1)
            # BOM 매핑: finished_item 또는 product_name
            boms = BillOfMaterial.objects.filter(
                company=company,
                finished_item=getattr(po, 'item_name', getattr(po, 'product_name', '')),
                is_active=True,
            )
            for bom in boms:
                for line in BomLine.objects.filter(bom=bom):
                    req_qty = float(line.quantity) * po_qty
                    total_items    += 1
                    planned_orders += 1
                    summary.append({
                        'production_order': str(po),
                        'component':        getattr(line, 'component_name', str(line)),
                        'required_qty':     round(req_qty, 4),
                        'unit':             getattr(line, 'unit', ''),
                    })

        mrp = MrpRun.objects.create(
            company=company,
            run_number=run_number,
            status='완료',
            total_items=total_items,
            planned_orders=planned_orders,
            note=f'Auto-run: {planned_orders}건 소요량 계획',
        )
        return Response({
            'run_number':     mrp.run_number,
            'status':         '완료',
            'total_items':    total_items,
            'planned_orders': planned_orders,
            'requirements':   summary,
        })
