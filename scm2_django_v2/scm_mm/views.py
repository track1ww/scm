from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from scm_core.mixins import AuditLogMixin
from .models import Supplier, Material, PurchaseOrder, PurchaseOrderLine, GoodsReceipt, MaterialPriceHistory
from .serializers import (SupplierSerializer, MaterialSerializer,
                           PurchaseOrderSerializer, PurchaseOrderLineSerializer,
                           GoodsReceiptSerializer, MaterialPriceHistorySerializer)

class SupplierViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class   = SupplierSerializer
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'contact', 'email']
    ordering_fields    = ['name', 'created_at']

    def get_queryset(self):
        return Supplier.objects.filter(
            company=self.request.user.company
        )

class MaterialViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class = MaterialSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['material_code', 'material_name']

    def get_queryset(self):
        return Material.objects.filter(company=self.request.user.company)

    @action(detail=True, methods=['get'], url_path='supplier-comparison')
    def supplier_comparison(self, request, pk=None):
        """
        Compare suppliers for this material based on price history.
        GET /api/mm/materials/{id}/supplier-comparison/
        Returns list of suppliers with latest price and price trend.
        """
        material = self.get_object()
        from .models import MaterialPriceHistory
        from django.db.models import Min, Max, Avg

        histories = MaterialPriceHistory.objects.filter(
            material=material, company=request.user.company
        ).select_related('supplier')

        # Group by supplier
        supplier_data = {}
        for h in histories:
            sid = h.supplier_id or 'no_supplier'
            if sid not in supplier_data:
                supplier_data[sid] = {
                    'supplier_id': h.supplier_id,
                    'supplier_name': str(h.supplier) if h.supplier else '미지정',
                    'prices': [],
                }
            supplier_data[sid]['prices'].append({
                'price': float(h.unit_price),
                'date': str(h.effective_from),
                'price_type': h.price_type,
            })

        result = []
        for sid, d in supplier_data.items():
            prices = [p['price'] for p in d['prices']]
            d['latest_price'] = prices[0] if prices else 0
            d['min_price'] = min(prices) if prices else 0
            d['max_price'] = max(prices) if prices else 0
            d['avg_price'] = round(sum(prices) / len(prices), 2) if prices else 0
            d['history_count'] = len(prices)
            result.append(d)

        # Sort by latest price ascending
        result.sort(key=lambda x: x['latest_price'])
        return Response(result)

    @action(detail=True, methods=['get'], url_path='requirements')
    def requirements_plan(self, request, pk=None):
        """
        Simple requirements planning for a material.
        GET /api/mm/materials/{id}/requirements/
        Returns: current stock, pending POs, pending SOs, net requirement.
        """
        material = self.get_object()
        company = request.user.company
        result = {
            'material_id': material.pk,
            'material_code': getattr(material, 'material_code', ''),
            'material_name': getattr(material, 'material_name', str(material)),
            'unit': getattr(material, 'unit', ''),
        }

        # Current WM stock
        try:
            from scm_wm.models import Inventory
            inv = Inventory.objects.filter(
                company=company,
                item_code=getattr(material, 'material_code', ''),
            ).first()
            result['current_stock'] = float(getattr(inv, 'stock_qty', 0) or 0)
            result['min_stock'] = float(getattr(inv, 'min_stock', 0) or 0)
        except Exception:
            result['current_stock'] = 0
            result['min_stock'] = 0

        # Pending POs (incoming supply)
        try:
            from scm_mm.models import PurchaseOrder
            pending_po_qty = sum(
                float(po.quantity or 0)
                for po in PurchaseOrder.objects.filter(
                    company=company,
                    item_name=getattr(material, 'material_name', ''),
                    status__in=['발주확정', '납품중'],
                )
            )
            result['pending_po_qty'] = pending_po_qty
        except Exception:
            result['pending_po_qty'] = 0

        # Pending SOs (outgoing demand)
        try:
            from scm_sd.models import SalesOrder
            pending_so_qty = sum(
                float(so.quantity or 0)
                for so in SalesOrder.objects.filter(
                    company=company,
                    item_name=getattr(material, 'material_name', ''),
                    status__in=['주문접수', '생산/조달중', '출하준비'],
                )
                if hasattr(so, 'quantity')
            )
            result['pending_so_qty'] = pending_so_qty
        except Exception:
            result['pending_so_qty'] = 0

        # Net requirement
        net = result['current_stock'] + result['pending_po_qty'] - result['pending_so_qty']
        result['net_available'] = round(net, 2)
        result['shortage'] = round(max(0, result['min_stock'] - net), 2)
        result['reorder_needed'] = result['shortage'] > 0

        return Response(result)

class PurchaseOrderViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class = PurchaseOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['po_number', 'item_name']
    filterset_fields = ['status', 'supplier']

    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            company=self.request.user.company
        ).select_related('supplier').prefetch_related('lines__material').order_by('-created_at')

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':    qs.count(),
            'pending':  qs.exclude(status__in=['입고완료','취소']).count(),
            'complete': qs.filter(status='입고완료').count(),
        })

class PurchaseOrderLineViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderLineSerializer

    def get_queryset(self):
        qs = PurchaseOrderLine.objects.filter(po__company=self.request.user.company)
        po_id = self.request.query_params.get('po')
        if po_id:
            qs = qs.filter(po_id=po_id)
        return qs.select_related('material')

    def perform_create(self, serializer):
        serializer.save()


class GoodsReceiptViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        return GoodsReceipt.objects.filter(
            company=self.request.user.company
        ).select_related('po').order_by('-created_at')


class MaterialPriceHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialPriceHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaterialPriceHistory.objects.filter(company=self.request.user.company)
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
