from django.contrib import admin

from .models import Supplier, Material, PurchaseOrder, GoodsReceipt


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'contact', 'email', 'phone', 'payment_terms', 'status', 'created_at')
    list_filter = ('status', 'payment_terms', 'company')
    search_fields = ('name', 'contact', 'email', 'phone')
    ordering = ('name',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('material_code', 'material_name', 'material_type', 'unit', 'min_stock', 'lead_time_days', 'company')
    list_filter = ('material_type', 'unit', 'company')
    search_fields = ('material_code', 'material_name')
    ordering = ('material_code',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'item_name', 'quantity', 'unit_price', 'currency', 'delivery_date', 'status', 'company')
    list_filter = ('status', 'currency', 'company')
    search_fields = ('po_number', 'item_name', 'supplier__name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display  = (
        'gr_number', 'po', 'item_name',
        'ordered_qty', 'received_qty', 'rejected_qty',
        'warehouse', 'receiver', 'status', 'company',
    )
    list_filter   = ('status', 'company', 'warehouse')
    search_fields = ('gr_number', 'item_name', 'receiver', 'po__po_number')
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'
