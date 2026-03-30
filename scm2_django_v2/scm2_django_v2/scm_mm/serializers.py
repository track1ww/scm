from rest_framework import serializers
from .models import Supplier, Material, PurchaseOrder, GoodsReceipt

class SupplierSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='name')

    class Meta:
        model  = Supplier
        fields = ['id', 'supplier_name', 'contact', 'email', 'phone',
                  'payment_terms', 'status', 'created_at', 'company']
        read_only_fields = ['id', 'created_at', 'company']

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Material
        fields = '__all__'

class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    total_amount  = serializers.SerializerMethodField()
    po_number     = serializers.CharField(required=False, allow_blank=True)

    def get_total_amount(self, obj):
        return float(obj.quantity * obj.unit_price)

    class Meta:
        model  = PurchaseOrder
        fields = '__all__'
        read_only_fields = ['company']

class GoodsReceiptSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(source='po.po_number', read_only=True)
    order     = serializers.PrimaryKeyRelatedField(
        source='po', queryset=PurchaseOrder.objects.all(), write_only=True, required=False
    )

    class Meta:
        model  = GoodsReceipt
        fields = '__all__'
        read_only_fields = ['gr_number', 'ordered_qty', 'item_name', 'company']
