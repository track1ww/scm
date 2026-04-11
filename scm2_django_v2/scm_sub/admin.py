from django.contrib import admin
from .models import SubcontractOrder, SubcontractOrderLine, SubcontractMaterial, SubcontractReceipt

class LineInline(admin.TabularInline):
    model = SubcontractOrderLine
    extra = 0

class MaterialInline(admin.TabularInline):
    model = SubcontractMaterial
    extra = 0

@admin.register(SubcontractOrder)
class SubcontractOrderAdmin(admin.ModelAdmin):
    list_display  = ['order_number', 'supplier', 'status', 'due_date', 'created_at']
    list_filter   = ['status']
    search_fields = ['order_number', 'supplier__name']
    inlines       = [LineInline, MaterialInline]

@admin.register(SubcontractReceipt)
class SubcontractReceiptAdmin(admin.ModelAdmin):
    list_display  = ['receipt_number', 'order', 'received_qty', 'receipt_date']
    search_fields = ['receipt_number']
