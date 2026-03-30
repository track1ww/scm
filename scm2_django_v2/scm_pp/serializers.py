from rest_framework import serializers
from .models import BillOfMaterial, BomLine, ProductionOrder, MrpRun


class BomLineSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BomLine
        fields = '__all__'
        read_only_fields = ['bom']


class BillOfMaterialSerializer(serializers.ModelSerializer):
    lines      = BomLineSerializer(many=True, read_only=True)
    line_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model  = BillOfMaterial
        fields = '__all__'
        read_only_fields = ['company']


class ProductionOrderSerializer(serializers.ModelSerializer):
    bom_code        = serializers.CharField(source='bom.bom_code', read_only=True)
    completion_rate = serializers.FloatField(read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = ProductionOrder
        fields = '__all__'
        read_only_fields = ['company']


class MrpRunSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MrpRun
        fields = '__all__'
        read_only_fields = ['company']
