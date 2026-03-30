from rest_framework import serializers
from .models import Supplier, Material, PurchaseOrder, PurchaseOrderLine, GoodsReceipt, MaterialPriceHistory


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Supplier
        fields = '__all__'


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Material
        fields = '__all__'


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    material_name_display = serializers.CharField(source='material.material_name', read_only=True)
    line_total = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrderLine
        fields = '__all__'


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    total_amount  = serializers.SerializerMethodField()
    lines         = PurchaseOrderLineSerializer(many=True, read_only=True)

    def get_total_amount(self, obj):
        # 라인이 있으면 라인 합계, 없으면 헤더 단일 금액 사용
        line_qs = obj.lines.all()
        if line_qs.exists():
            return sum(l.line_total for l in line_qs)
        return float(obj.quantity * obj.unit_price)

    class Meta:
        model  = PurchaseOrder
        fields = '__all__'

class GoodsReceiptSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(source='po.po_number', read_only=True)

    class Meta:
        model  = GoodsReceipt
        fields = '__all__'


class MaterialPriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialPriceHistory
        fields = '__all__'
