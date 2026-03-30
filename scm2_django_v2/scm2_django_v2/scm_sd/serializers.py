from rest_framework import serializers
from .models import Customer, SalesOrder, Delivery


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'


class SalesOrderSerializer(serializers.ModelSerializer):
    customer_display = serializers.CharField(source='customer.customer_name', read_only=True)
    total_amount     = serializers.SerializerMethodField()
    order_number     = serializers.CharField(required=False, allow_blank=True)

    def get_total_amount(self, obj):
        return obj.total_amount

    class Meta:
        model  = SalesOrder
        fields = '__all__'
        read_only_fields = ['company']


class DeliverySerializer(serializers.ModelSerializer):
    order_number     = serializers.CharField(source='order.order_number', read_only=True)
    delivery_number  = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = Delivery
        fields = '__all__'
        read_only_fields = ['company', 'item_name']
