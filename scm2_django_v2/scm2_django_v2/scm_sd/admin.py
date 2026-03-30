from django.contrib import admin

from .models import Customer, SalesOrder, Delivery


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_code', 'customer_name', 'contact', 'email', 'credit_limit', 'payment_terms', 'status', 'company')
    list_filter = ('status', 'payment_terms', 'company')
    search_fields = ('customer_code', 'customer_name', 'contact', 'email')
    ordering = ('customer_code',)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'item_name', 'quantity', 'unit_price', 'discount_rate', 'status', 'shipped_qty', 'company')
    list_filter = ('status', 'company')
    search_fields = ('order_number', 'customer_name', 'item_name')
    ordering = ('-ordered_at',)
    date_hierarchy = 'ordered_at'


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_number', 'order', 'item_name', 'delivery_qty', 'carrier', 'tracking_number', 'delivery_date', 'status', 'company')
    list_filter = ('status', 'company', 'carrier')
    search_fields = ('delivery_number', 'item_name', 'tracking_number', 'order__order_number')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
