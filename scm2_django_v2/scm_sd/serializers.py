from rest_framework import serializers
from .models import Customer, SalesOrder, Delivery, SalesInvoice


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'
        read_only_fields = ['company']


class SalesOrderSerializer(serializers.ModelSerializer):
    customer_display = serializers.CharField(source='customer.customer_name', read_only=True)
    total_amount     = serializers.FloatField(read_only=True)
    order_number     = serializers.CharField(required=False, allow_blank=True)
    customer_name    = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model  = SalesOrder
        fields = '__all__'
        read_only_fields = ['company']


class DeliverySerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model  = Delivery
        fields = '__all__'
        read_only_fields = ['company']


class SalesInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='sales_order.customer.customer_name', read_only=True)
    order_number  = serializers.CharField(source='sales_order.order_number', read_only=True)

    class Meta:
        model  = SalesInvoice
        fields = '__all__'
