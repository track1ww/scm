from rest_framework import serializers
from .models import Warehouse, Inventory, StockMovement


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Warehouse
        fields = [
            'id',
            'warehouse_code',
            'warehouse_name',
            'warehouse_type',
            'location',
            'is_active',
            'company',
        ]
        read_only_fields = ['company']


class InventorySerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(
        source='warehouse.warehouse_name', read_only=True
    )
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Inventory
        fields = [
            'id',
            'item_code',
            'item_name',
            'category',
            'warehouse',
            'warehouse_name',
            'bin_code',
            'stock_qty',
            'system_qty',
            'unit_price',
            'min_stock',
            'lot_number',
            'expiry_date',
            'updated_at',
            'is_low_stock',
            'company',
        ]
        read_only_fields = ['company', 'updated_at', 'is_low_stock']


class StockMovementSerializer(serializers.ModelSerializer):
    movement_type_display  = serializers.CharField(
        source='get_movement_type_display', read_only=True
    )
    reference_type_display = serializers.CharField(
        source='get_reference_type_display', read_only=True
    )
    warehouse_name = serializers.CharField(
        source='warehouse.warehouse_name', read_only=True
    )

    class Meta:
        model  = StockMovement
        fields = [
            'id',
            'movement_type',
            'movement_type_display',
            'material_code',
            'material_name',
            'warehouse',
            'warehouse_name',
            'quantity',
            'before_qty',
            'after_qty',
            'reference_document',
            'reference_type',
            'reference_type_display',
            'note',
            'created_at',
            'created_by',
            'company',
        ]
        read_only_fields = fields  # 이력 테이블 전체 읽기 전용
