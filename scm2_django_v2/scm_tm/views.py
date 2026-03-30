from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg
from django_filters.rest_framework import DjangoFilterBackend
from .models import Carrier, TransportOrder, FreightRate, ShipmentTracking
from .serializers import CarrierSerializer, TransportOrderSerializer, FreightRateSerializer, ShipmentTrackingSerializer


class CarrierViewSet(viewsets.ModelViewSet):
    serializer_class = CarrierSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['carrier_code', 'carrier_name', 'contact']

    def get_queryset(self):
        return Carrier.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class TransportOrderViewSet(viewsets.ModelViewSet):
    serializer_class = TransportOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['transport_number', 'origin', 'destination', 'tracking_number']
    filterset_fields = ['status', 'carrier']
    ordering_fields  = ['planned_date', 'created_at']

    def get_queryset(self):
        return TransportOrder.objects.filter(
            company=self.request.user.company
        ).select_related('carrier').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        avg_freight = qs.exclude(freight_cost=0).aggregate(
            avg=Avg('freight_cost')
        )['avg'] or 0
        return Response({
            'total':        qs.count(),
            'in_transit':   qs.filter(status='운송중').count(),
            'completed':    qs.filter(status='완료').count(),
            'planned':      qs.filter(status='계획').count(),
            'total_freight': float(qs.aggregate(s=Sum('freight_cost'))['s'] or 0),
            'avg_freight':   float(avg_freight),
        })


class FreightRateViewSet(viewsets.ModelViewSet):
    serializer_class = FreightRateSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    search_fields    = ['origin', 'destination']
    filterset_fields = ['carrier', 'is_active']

    def get_queryset(self):
        return FreightRate.objects.filter(
            company=self.request.user.company
        ).select_related('carrier')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class ShipmentTrackingViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentTrackingSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['transport_number', 'location', 'status_note']
    filterset_fields = ['transport_order']
    ordering_fields  = ['tracked_at', 'created_at']

    def get_queryset(self):
        return ShipmentTracking.objects.filter(
            company=self.request.user.company
        ).select_related('transport_order').order_by('-tracked_at')

    def perform_create(self, serializer):
        order = serializer.validated_data.get('transport_order')
        tn = order.transport_number if order else ''
        serializer.save(company=self.request.user.company, transport_number=tn)
