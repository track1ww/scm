from django.db import models
from django.conf import settings
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


class StockMovement(models.Model):
    """재고 이동 이력 - 모든 재고 변동을 추적하는 핵심 감사 테이블"""

    MOVEMENT_TYPE = [
        ('IN',       '입고'),
        ('OUT',      '출고'),
        ('TRANSFER', '이동'),
        ('ADJUST',   '조정'),
    ]
    REFERENCE_TYPE = [
        ('PO', '발주'),
        ('SO', '판매주문'),
        ('WO', '작업지시'),
    ]

    company            = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True,
        verbose_name='회사'
    )
    warehouse          = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True,
        verbose_name='창고'
    )
    material_code      = models.CharField(max_length=100, verbose_name='자재코드/품목코드')
    material_name      = models.CharField(max_length=200, blank=True, verbose_name='자재명')
    movement_type      = models.CharField(
        max_length=10, choices=MOVEMENT_TYPE,
        verbose_name='이동유형'
    )
    quantity           = models.DecimalField(
        max_digits=15, decimal_places=3,
        verbose_name='수량'
    )
    before_qty         = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name='변동 전 재고'
    )
    after_qty          = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name='변동 후 재고'
    )
    reference_document = models.CharField(
        max_length=100, blank=True,
        verbose_name='참조 문서번호'
    )
    reference_type     = models.CharField(
        max_length=10, choices=REFERENCE_TYPE, blank=True,
        verbose_name='참조 문서유형'
    )
    note               = models.TextField(blank=True, verbose_name='비고')
    created_at         = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    created_by         = models.CharField(max_length=100, blank=True, verbose_name='생성자')

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['material_code', 'warehouse']),
            models.Index(fields=['reference_document']),
            models.Index(fields=['movement_type', 'created_at']),
        ]
        verbose_name        = '재고이동이력'
        verbose_name_plural = '재고이동이력'

    def __str__(self):
        return (
            f"[{self.get_movement_type_display()}] "
            f"{self.material_code} {self.quantity} "
            f"({self.reference_document})"
        )
