from django.contrib import admin

from .models import Warehouse, Inventory, StockMovement


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('warehouse_code', 'warehouse_name', 'warehouse_type', 'location', 'is_active', 'company')
    list_filter = ('warehouse_type', 'is_active', 'company')
    search_fields = ('warehouse_code', 'warehouse_name', 'location')
    ordering = ('warehouse_code',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'item_name', 'category', 'warehouse', 'bin_code', 'stock_qty', 'system_qty', 'unit_price', 'min_stock', 'lot_number', 'expiry_date', 'company')
    list_filter = ('category', 'warehouse', 'company')
    search_fields = ('item_code', 'item_name', 'lot_number', 'bin_code')
    ordering = ('item_code',)
    date_hierarchy = 'updated_at'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'movement_type', 'material_code', 'material_name',
        'warehouse', 'quantity', 'before_qty', 'after_qty',
        'reference_document', 'reference_type', 'created_by',
    )
    list_filter   = ('movement_type', 'reference_type', 'warehouse', 'company')
    search_fields = ('material_code', 'material_name', 'reference_document')
    readonly_fields = (
        'movement_type', 'material_code', 'material_name', 'warehouse',
        'quantity', 'before_qty', 'after_qty',
        'reference_document', 'reference_type',
        'note', 'created_at', 'created_by',
    )
    ordering       = ('-created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        # 이력 테이블은 Signal 에서만 생성 - Admin 직접 추가 비허용
        return False

    def has_delete_permission(self, request, obj=None):
        return False
