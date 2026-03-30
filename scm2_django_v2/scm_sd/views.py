from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, F
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
import uuid
from scm_core.mixins import AuditLogMixin
from .models import Customer, SalesOrder, Delivery, SalesInvoice
from .serializers import CustomerSerializer, SalesOrderSerializer, DeliverySerializer, SalesInvoiceSerializer


class CustomerViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'sd'
    serializer_class = CustomerSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['customer_code', 'customer_name', 'contact', 'email']
    ordering_fields  = ['customer_name', 'created_at']

    def get_queryset(self):
        return Customer.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class SalesOrderViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'sd'
    serializer_class = SalesOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['order_number', 'customer_name', 'item_name']
    filterset_fields = ['status', 'customer']
    ordering_fields  = ['ordered_at', 'order_number']

    def get_queryset(self):
        return SalesOrder.objects.filter(
            company=self.request.user.company
        ).select_related('customer').order_by('-ordered_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        total_sales = qs.filter(status='배송완료').aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        return Response({
            'total':       qs.count(),
            'pending':     qs.exclude(status__in=['배송완료', '취소']).count(),
            'shipped':     qs.filter(status='배송완료').count(),
            'total_sales': float(total_sales),
        })


class DeliveryViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'sd'
    serializer_class = DeliverySerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    search_fields    = ['delivery_number', 'item_name']
    filterset_fields = ['status']

    def get_queryset(self):
        return Delivery.objects.filter(
            company=self.request.user.company
        ).select_related('order').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_delivery(self, request, pk=None):
        from django.utils import timezone
        delivery = self.get_object()
        delivery.status = '배송완료'
        delivery.save(update_fields=['status'])

        if not SalesInvoice.objects.filter(delivery=delivery).exists():
            order = delivery.order
            supply = Decimal(str(order.total_amount or 0))
            vat = supply * Decimal('0.1')
            SalesInvoice.objects.create(
                company=request.user.company,
                sales_order=order,
                delivery=delivery,
                invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                supply_amount=supply,
                vat_amount=vat,
                total_amount=supply + vat,
                status='draft',
            )
        return Response({'detail': '배송이 확정되고 송장이 생성되었습니다.'})


class SalesInvoiceViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'sd'
    serializer_class = SalesInvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SalesInvoice.objects.filter(
            company=self.request.user.company
        ).select_related('sales_order__customer', 'delivery')

    def perform_create(self, serializer):
        inv_no = f"INV-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(company=self.request.user.company, invoice_number=inv_no)

    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != 'draft':
            return Response({'detail': '임시 상태의 송장만 발행 가능합니다.'}, status=400)
        invoice.status = 'issued'
        invoice.save(update_fields=['status'])
        return Response(SalesInvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != 'issued':
            return Response({'detail': '발행된 송장만 수금 처리 가능합니다.'}, status=400)
        invoice.status = 'paid'
        invoice.save(update_fields=['status'])
        return Response(SalesInvoiceSerializer(invoice).data)
