from rest_framework import serializers
from .models import Carrier, TransportOrder, FreightRate, ShipmentTracking


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Carrier
        fields = '__all__'
        read_only_fields = ['company']


class TransportOrderSerializer(serializers.ModelSerializer):
    carrier_name   = serializers.CharField(source='carrier.carrier_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = TransportOrder
        fields = '__all__'
        read_only_fields = ['company']


class FreightRateSerializer(serializers.ModelSerializer):
    carrier_name = serializers.CharField(source='carrier.carrier_name', read_only=True)

    class Meta:
        model  = FreightRate
        fields = '__all__'
        read_only_fields = ['company']


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ShipmentTracking
        fields = '__all__'
        read_only_fields = ['company', 'transport_number', 'created_at']
