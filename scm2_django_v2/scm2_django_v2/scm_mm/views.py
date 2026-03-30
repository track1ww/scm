import uuid
from decimal import Decimal

from django.db.models import Sum, Avg, Count, F, Q, ExpressionWrapper, DecimalField
from django.utils import timezone

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Supplier, Material, PurchaseOrder, GoodsReceipt
from .serializers import (SupplierSerializer, MaterialSerializer,
                           PurchaseOrderSerializer, GoodsReceiptSerializer)

class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class   = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'contact', 'email']
    ordering_fields    = ['name', 'created_at']

    def get_queryset(self):
        return Supplier.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    # ------------------------------------------------------------------ #
    #  GET /api/mm/suppliers/{id}/performance/                            #
    #  공급업체별 성과 지표                                                #
    # ------------------------------------------------------------------ #
    @action(detail=True, methods=['get'], url_path='performance')
    def performance(self, request, pk=None):
        """
        공급업체별 성과 지표.

        Returns:
            supplier_id, supplier_name,
            total_orders:       총 발주 건수,
            total_order_amount: 총 발주금액,
            delivery_rate:      납기 준수율 (입고완료 건 중 delivery_date 이내 입고),
            avg_lead_time_days: 평균 리드타임 (발주일 ~ 입고확인일, 입고확인 기준),
            defect_rate:        불량률 (rejected_qty / received_qty),
            on_time_count:      납기 준수 건수,
            late_count:         납기 초과 건수,
        """
        supplier = self.get_object()

        # 해당 공급업체의 전체 발주 (회사 스코프 이중 확인)
        po_qs = PurchaseOrder.objects.filter(
            company=request.user.company,
            supplier=supplier,
        )

        total_orders = po_qs.count()

        # 총 발주금액: quantity * unit_price 합계
        amount_agg = po_qs.aggregate(
            total_amount=Sum(
                ExpressionWrapper(
                    F('quantity') * F('unit_price'),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
        )
        total_order_amount = amount_agg['total_amount'] or Decimal('0')

        # 납기 준수율: delivery_date가 있고 received 상태인 발주 대상
        received_qs = po_qs.filter(
            status='received',
            delivery_date__isnull=False,
        )
        received_count = received_qs.count()

        # GoodsReceipt 기준으로 실제 입고일(created_at) vs PO의 delivery_date 비교
        # on_time: GR의 최초 입고 확인일이 delivery_date 이하인 건
        on_time_count = 0
        late_count    = 0
        lead_time_days_list = []

        gr_qs = GoodsReceipt.objects.filter(
            company=request.user.company,
            po__supplier=supplier,
            status__in=['confirmed', 'completed'],
        ).select_related('po')

        for gr in gr_qs:
            if gr.po and gr.po.delivery_date:
                actual_date = gr.created_at.date()
                if actual_date <= gr.po.delivery_date:
                    on_time_count += 1
                else:
                    late_count += 1

            # 리드타임: PO 생성일 ~ GR 생성일
            if gr.po:
                lead_days = (gr.created_at.date() - gr.po.created_at.date()).days
                if lead_days >= 0:
                    lead_time_days_list.append(lead_days)

        gr_with_delivery = on_time_count + late_count
        delivery_rate = (
            round(on_time_count / gr_with_delivery * 100, 2)
            if gr_with_delivery > 0 else None
        )
        avg_lead_time_days = (
            round(sum(lead_time_days_list) / len(lead_time_days_list), 1)
            if lead_time_days_list else None
        )

        # 불량률: rejected_qty / received_qty (회사 + 공급업체 스코프)
        defect_agg = GoodsReceipt.objects.filter(
            company=request.user.company,
            po__supplier=supplier,
            status__in=['confirmed', 'completed'],
        ).aggregate(
            total_received=Sum('received_qty'),
            total_rejected=Sum('rejected_qty'),
        )
        total_received = defect_agg['total_received'] or 0
        total_rejected = defect_agg['total_rejected'] or 0
        defect_rate = (
            round(total_rejected / total_received * 100, 2)
            if total_received > 0 else None
        )

        return Response({
            'supplier_id':        supplier.id,
            'supplier_name':      supplier.name,
            'total_orders':       total_orders,
            'total_order_amount': total_order_amount,
            'delivery_rate':      delivery_rate,
            'avg_lead_time_days': avg_lead_time_days,
            'defect_rate':        defect_rate,
            'on_time_count':      on_time_count,
            'late_count':         late_count,
            'gr_evaluated':       gr_with_delivery,
        })

class MaterialViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['material_code', 'material_name']

    def get_queryset(self):
        return Material.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['po_number', 'item_name']
    filterset_fields = ['status', 'supplier']

    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            company=self.request.user.company
        ).select_related('supplier').order_by('-created_at')

    def perform_create(self, serializer):
        # Auto-generate po_number if not provided
        po_number = serializer.validated_data.get('po_number') or f'PO-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(company=self.request.user.company, po_number=po_number)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':    qs.count(),
            'pending':  qs.filter(status__in=['pending', 'ordered', 'confirmed']).count(),
            'complete': qs.filter(status='received').count(),
        })

class GoodsReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        return GoodsReceipt.objects.filter(
            company=self.request.user.company
        ).select_related('po').order_by('-created_at')

    def perform_create(self, serializer):
        po = serializer.validated_data.get('po')
        # Auto-generate gr_number
        gr_number = f'GR-{uuid.uuid4().hex[:8].upper()}'
        # Copy item_name and ordered_qty from PO if available
        item_name   = po.item_name if po else ''
        ordered_qty = po.quantity  if po else 0
        serializer.save(
            company=self.request.user.company,
            gr_number=gr_number,
            item_name=item_name,
            ordered_qty=ordered_qty,
        )
