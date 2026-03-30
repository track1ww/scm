import uuid
from decimal import Decimal

from django.db.models import Sum, F
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from scm_core.mixins import AuditLogMixin, StateLockMixin
from .models import Warehouse, Inventory, BinLocation, CycleCount, StockMovement
from .serializers import (
    WarehouseSerializer,
    InventorySerializer,
    BinLocationSerializer,
    CycleCountSerializer,
    CycleCountWriteSerializer,
    CycleCountLineSerializer,
    StockMovementSerializer,
)


class WarehouseViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'wm'
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['warehouse_code', 'warehouse_name', 'location']
    filterset_fields = ['warehouse_type', 'is_active']
    ordering_fields = ['warehouse_code', 'warehouse_name']

    def get_queryset(self):
        return Warehouse.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class InventoryViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'wm'
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['item_code', 'item_name', 'lot_number', 'bin_code']
    filterset_fields = ['warehouse', 'category']
    ordering_fields = ['item_code', 'item_name', 'stock_qty', 'updated_at']

    def get_queryset(self):
        return Inventory.objects.filter(
            company=self.request.user.company
        ).select_related('warehouse')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        qs = self.get_queryset()
        total_warehouses = Warehouse.objects.filter(
            company=request.user.company, is_active=True
        ).count()
        total_items = qs.count()
        low_stock_count = sum(1 for item in qs if item.is_low_stock)
        return Response({
            'total_warehouses': total_warehouses,
            'total_items': total_items,
            'low_stock_count': low_stock_count,
        })

    @action(detail=False, methods=['get'], url_path='analysis')
    def analysis(self, request):
        qs = self.get_queryset()

        # ABC classification by category (by total stock value descending)
        category_data = (
            qs.values('category')
            .annotate(
                total_value=Sum(F('stock_qty') * F('unit_price')),
                item_count=Sum(F('stock_qty') * 0 + 1),
            )
            .order_by('-total_value')
        )
        categories = list(category_data)
        total = sum(Decimal(str(c['total_value'] or 0)) for c in categories)
        cumulative = Decimal('0')
        abc_classification = []
        for cat in categories:
            value = Decimal(str(cat['total_value'] or 0))
            if total > 0:
                cumulative += value
                ratio = cumulative / total * 100
                if ratio <= 80:
                    abc_class = 'A'
                elif ratio <= 95:
                    abc_class = 'B'
                else:
                    abc_class = 'C'
            else:
                abc_class = 'C'
            abc_classification.append({
                'category': cat['category'] or '미분류',
                'total_value': float(value),
                'item_count': cat['item_count'],
                'abc_class': abc_class,
            })

        # Stock value by warehouse
        by_warehouse = (
            qs.values('warehouse__warehouse_code', 'warehouse__warehouse_name')
            .annotate(stock_value=Sum(F('stock_qty') * F('unit_price')))
            .order_by('-stock_value')
        )
        warehouse_data = [
            {
                'warehouse_code': row['warehouse__warehouse_code'],
                'warehouse_name': row['warehouse__warehouse_name'],
                'stock_value': float(row['stock_value'] or 0),
            }
            for row in by_warehouse
        ]

        return Response({
            'abc_classification': abc_classification,
            'by_warehouse': warehouse_data,
        })


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['material_code', 'material_name', 'reference_document']
    filterset_fields = ['movement_type', 'reference_type', 'warehouse']
    ordering_fields = ['created_at', 'material_code', 'movement_type']

    def get_queryset(self):
        return StockMovement.objects.filter(
            company=self.request.user.company
        ).select_related('warehouse').order_by('-created_at')


class BinLocationViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'wm'
    serializer_class = BinLocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['bin_code', 'aisle', 'row', 'level']
    filterset_fields = ['warehouse', 'is_active']
    ordering_fields = ['bin_code', 'warehouse']

    def get_queryset(self):
        return BinLocation.objects.filter(
            company=self.request.user.company
        ).select_related('warehouse')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class CycleCountViewSet(AuditLogMixin, StateLockMixin, viewsets.ModelViewSet):
    audit_module = 'wm'
    locked_states = ['완료']
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['count_number', 'counter']
    filterset_fields = ['status', 'warehouse']
    ordering_fields = ['count_date', 'count_number', 'created_at']

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            return CycleCountWriteSerializer
        return CycleCountSerializer

    def get_queryset(self):
        return CycleCount.objects.filter(
            company=self.request.user.company
        ).prefetch_related('lines').select_related('warehouse').order_by('-created_at')

    def perform_create(self, serializer):
        count_number = 'CC-' + uuid.uuid4().hex[:8].upper()
        serializer.save(company=self.request.user.company, count_number=count_number)
