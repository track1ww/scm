from rest_framework import serializers
from .models import SubcontractOrder, SubcontractOrderLine, SubcontractMaterial, SubcontractReceipt


class SubcontractOrderLineSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()

    class Meta:
        model  = SubcontractOrderLine
        fields = ['id', 'order', 'line_no', 'item_name', 'quantity', 'unit', 'unit_price', 'note', 'line_total']
        extra_kwargs = {'order': {'required': False}}


class SubcontractMaterialSerializer(serializers.ModelSerializer):
    material_code = serializers.CharField(source='material.material_code', read_only=True)

    class Meta:
        model  = SubcontractMaterial
        fields = ['id', 'order', 'material', 'material_code', 'material_name',
                  'quantity', 'unit', 'issued_qty', 'returned_qty', 'note']
        extra_kwargs = {'order': {'required': False}}


class SubcontractReceiptSerializer(serializers.ModelSerializer):
    order_number  = serializers.CharField(source='order.order_number', read_only=True)
    supplier_name = serializers.CharField(source='order.supplier.name', read_only=True)

    class Meta:
        model  = SubcontractReceipt
        fields = ['id', 'company', 'receipt_number', 'order', 'order_number', 'supplier_name',
                  'receipt_date', 'item_name', 'ordered_qty', 'received_qty', 'rejected_qty',
                  'warehouse', 'receiver', 'note', 'created_at']
        read_only_fields = ['company', 'receipt_number']


class SubcontractOrderSerializer(serializers.ModelSerializer):
    supplier_name   = serializers.CharField(source='supplier.name', read_only=True)
    supplier_email  = serializers.CharField(source='supplier.email', read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)
    total_amount    = serializers.ReadOnlyField()
    lines           = SubcontractOrderLineSerializer(many=True, read_only=True)
    materials       = SubcontractMaterialSerializer(many=True, read_only=True)
    issued_by_name  = serializers.CharField(source='issued_by.name', read_only=True)

    class Meta:
        model  = SubcontractOrder
        fields = [
            'id', 'order_number', 'company', 'supplier', 'supplier_name', 'supplier_email',
            'order_date', 'due_date', 'work_description', 'currency',
            'status', 'status_display', 'total_amount',
            'issued_at', 'issued_by', 'issued_by_name',
            'note', 'created_at', 'updated_at',
            'lines', 'materials',
        ]
        read_only_fields = ['company', 'order_number', 'issued_at', 'issued_by']
