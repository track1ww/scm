from django.db import models
from scm_accounts.models import Company

class Warehouse(models.Model):
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    warehouse_code = models.CharField(max_length=20, unique=True)
    warehouse_name = models.CharField(max_length=100)
    warehouse_type = models.CharField(max_length=50, default='일반창고')
    location       = models.CharField(max_length=200, blank=True)
    is_active      = models.BooleanField(default=True)

    def __str__(self): return self.warehouse_name


class Inventory(models.Model):
    company     = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    item_code   = models.CharField(max_length=100)
    item_name   = models.CharField(max_length=200)
    category    = models.CharField(max_length=100, blank=True)
    warehouse   = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    bin_code    = models.CharField(max_length=50, blank=True)
    stock_qty   = models.IntegerField(default=0)
    system_qty  = models.IntegerField(default=0)
    unit_price  = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    min_stock   = models.IntegerField(default=0)
    expiry_date = models.DateField(null=True, blank=True)
    lot_number  = models.CharField(max_length=100, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item_code', 'warehouse', 'lot_number')

    @property
    def is_low_stock(self):
        return self.min_stock > 0 and self.stock_qty <= self.min_stock

    def __str__(self): return f"{self.item_name} ({self.warehouse})"


class BinLocation(models.Model):
    """창고 내 빈(Bin) 위치"""
    company   = models.ForeignKey(Company, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    bin_code  = models.CharField(max_length=50)
    aisle     = models.CharField(max_length=20, blank=True)
    row       = models.CharField(max_length=20, blank=True)
    level     = models.CharField(max_length=20, blank=True)
    capacity  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['warehouse', 'bin_code']

    def __str__(self): return f"{self.warehouse.warehouse_code}-{self.bin_code}"


class CycleCount(models.Model):
    """재고 실사"""
    company      = models.ForeignKey(Company, on_delete=models.CASCADE)
    count_number = models.CharField(max_length=50, unique=True)
    warehouse    = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    count_date   = models.DateField()
    status       = models.CharField(max_length=20, choices=[
        ('draft', '계획'), ('in_progress', '진행중'), ('completed', '완료'), ('cancelled', '취소')
    ], default='draft')
    counter      = models.CharField(max_length=100, blank=True)
    note         = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.count_number


class CycleCountLine(models.Model):
    """실사 라인"""
    cycle_count  = models.ForeignKey(CycleCount, on_delete=models.CASCADE, related_name='lines')
    inventory    = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    system_qty   = models.DecimalField(max_digits=15, decimal_places=3)
    counted_qty  = models.DecimalField(max_digits=15, decimal_places=3, null=True)
    variance     = models.DecimalField(max_digits=15, decimal_places=3, null=True)
    note         = models.CharField(max_length=200, blank=True)

    def __str__(self): return f"{self.cycle_count.count_number} - {self.inventory.item_code}"


class StockMovement(models.Model):
    MOVEMENT_TYPES = [('IN', '입고'), ('OUT', '출고'), ('TRANSFER', '이동'), ('ADJUST', '조정')]
    company            = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    warehouse          = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    movement_type      = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    material_code      = models.CharField(max_length=100)
    material_name      = models.CharField(max_length=200, blank=True)
    quantity           = models.DecimalField(max_digits=15, decimal_places=3)
    reference_type     = models.CharField(max_length=50, blank=True)
    reference_document = models.CharField(max_length=100, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.movement_type} {self.material_code} {self.quantity}"
