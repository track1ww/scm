from rest_framework import serializers
from .models import Carrier, TransportOrder, TransportTracking


class CarrierSerializer(serializers.ModelSerializer):
    # Frontend may send carrier_name instead of name
    carrier_name = serializers.CharField(source='name', required=False, allow_blank=True)
    # Frontend may send contact instead of contact_name
    contact      = serializers.CharField(source='contact_name', required=False, allow_blank=True)
    # Frontend may send vehicle_type (not in model, ignore)
    vehicle_type = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def create(self, validated_data):
        validated_data.pop('vehicle_type', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('vehicle_type', None)
        return super().update(instance, validated_data)

    class Meta:
        model  = Carrier
        fields = [
            'id', 'company', 'carrier_code', 'name', 'carrier_name',
            'contact_name', 'contact', 'phone', 'email', 'is_active',
            'vehicle_type',
        ]
        read_only_fields = ['company']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'contact_name': {'required': False, 'allow_blank': True},
        }


class TransportTrackingSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(
        source='recorded_by.name', read_only=True, default=''
    )
    # Accept frontend alias fields
    status_note = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tracked_at  = serializers.DateTimeField(write_only=True, required=False, allow_null=True)

    def to_internal_value(self, data):
        data = data.copy()
        if 'status_note' in data and not data.get('status_update'):
            data['status_update'] = data.pop('status_note')
        if 'tracked_at' in data and not data.get('timestamp'):
            data['timestamp'] = data.pop('tracked_at')
        if not data.get('timestamp'):
            from django.utils import timezone
            data['timestamp'] = timezone.now().isoformat()
        if not data.get('status_update'):
            data['status_update'] = '-'
        return super().to_internal_value(data)

    def create(self, validated_data):
        validated_data.pop('status_note', None)
        validated_data.pop('tracked_at', None)
        return super().create(validated_data)

    class Meta:
        model  = TransportTracking
        fields = [
            'id', 'transport_order',
            'location', 'status_update', 'timestamp',
            'recorded_by', 'recorded_by_name',
            'status_note', 'tracked_at',
        ]
        read_only_fields = ['recorded_by']
        extra_kwargs = {
            'timestamp':     {'required': False},
            'status_update': {'required': False, 'allow_blank': True},
        }


class TransportOrderSerializer(serializers.ModelSerializer):
    carrier_name       = serializers.CharField(source='carrier.name',    read_only=True, default='')
    carrier_code_disp  = serializers.CharField(source='carrier.carrier_code', read_only=True, default='')
    status_display     = serializers.CharField(source='get_status_display',         read_only=True)
    ref_type_display   = serializers.CharField(source='get_reference_type_display', read_only=True)
    created_by_name    = serializers.CharField(source='created_by.name', read_only=True, default='')
    tracking_records   = TransportTrackingSerializer(many=True, read_only=True)
    order_number       = serializers.CharField(required=False, allow_blank=True)

    # Accept legacy field names from frontend
    origin      = serializers.CharField(write_only=True, required=False, allow_blank=True)
    destination = serializers.CharField(write_only=True, required=False, allow_blank=True)
    item_description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    planned_date     = serializers.DateTimeField(write_only=True, required=False, allow_null=True)
    currency         = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def to_internal_value(self, data):
        data = data.copy()
        # Map legacy field names to model field names
        if 'origin' in data and not data.get('origin_address'):
            data['origin_address'] = data.pop('origin')
        if 'destination' in data and not data.get('destination_address'):
            data['destination_address'] = data.pop('destination')
        if 'item_description' in data and not data.get('cargo_description'):
            data['cargo_description'] = data.pop('item_description')
        if 'planned_date' in data:
            planned_date = data.pop('planned_date')
            if planned_date and not data.get('planned_departure'):
                data['planned_departure'] = planned_date
            if planned_date and not data.get('planned_arrival'):
                data['planned_arrival'] = planned_date
        data.pop('currency', None)
        return super().to_internal_value(data)

    class Meta:
        model  = TransportOrder
        fields = [
            'id', 'company',
            'order_number', 'carrier', 'carrier_code_disp', 'carrier_name',
            'origin_address', 'destination_address', 'cargo_description',
            'weight_kg', 'volume_cbm',
            'planned_departure', 'actual_departure',
            'planned_arrival',   'actual_arrival',
            'freight_cost',
            'status', 'status_display',
            'reference_type', 'ref_type_display', 'reference_number',
            'created_by', 'created_by_name', 'created_at',
            'tracking_records',
            # legacy write-only aliases
            'origin', 'destination', 'item_description', 'planned_date', 'currency',
        ]
        read_only_fields = [
            'company', 'created_by', 'created_at',
            'actual_departure', 'actual_arrival',
        ]


class TransportOrderListSerializer(serializers.ModelSerializer):
    """목록 조회용 경량 직렬화 (tracking_records 미포함)"""
    carrier_name     = serializers.CharField(source='carrier.name',    read_only=True, default='')
    carrier_code     = serializers.CharField(source='carrier.carrier_code', read_only=True, default='')
    status_display   = serializers.CharField(source='get_status_display',         read_only=True)
    ref_type_display = serializers.CharField(source='get_reference_type_display', read_only=True)
    created_by_name  = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model  = TransportOrder
        fields = [
            'id', 'company',
            'order_number', 'carrier', 'carrier_code', 'carrier_name',
            'origin_address', 'destination_address',
            'weight_kg', 'volume_cbm', 'freight_cost',
            'planned_departure', 'actual_departure',
            'planned_arrival',   'actual_arrival',
            'status', 'status_display',
            'reference_type', 'ref_type_display', 'reference_number',
            'created_by_name', 'created_at',
        ]
        read_only_fields = ['company', 'created_by', 'created_at']
