from rest_framework import serializers
from .models import Warehouse, Inventory, BinLocation, CycleCount, CycleCountLine, StockMovement


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class InventorySerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = '__all__'


class BinLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BinLocation
        fields = '__all__'


class CycleCountLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleCountLine
        fields = '__all__'


class CycleCountSerializer(serializers.ModelSerializer):
    lines = CycleCountLineSerializer(many=True, read_only=True)

    class Meta:
        model = CycleCount
        fields = '__all__'


class CycleCountWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleCount
        fields = '__all__'


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'
        read_only_fields = ['created_at']
