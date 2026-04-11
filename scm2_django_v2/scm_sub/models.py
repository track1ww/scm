from django.db import models
from django.conf import settings
from scm_accounts.models import Company
from scm_mm.models import Supplier, Material


class SubcontractOrder(models.Model):
    STATUS = [
        ('draft',       '초안'),
        ('issued',      '발주확정'),
        ('in_progress', '작업중'),
        ('completed',   '작업완료'),
        ('received',    '입고완료'),
        ('closed',      '마감'),
        ('cancelled',   '취소'),
    ]

    company          = models.ForeignKey(Company, on_delete=models.CASCADE)
    order_number     = models.CharField(max_length=50, unique=True)
    supplier         = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    order_date       = models.DateField()
    due_date         = models.DateField(null=True, blank=True)
    work_description = models.CharField(max_length=500, blank=True)
    currency         = models.CharField(max_length=10, default='KRW')
    status           = models.CharField(max_length=20, choices=STATUS, default='draft')
    issued_at        = models.DateTimeField(null=True, blank=True)
    issued_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='issued_sub_orders'
    )
    note             = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    @property
    def total_amount(self):
        return sum(l.line_total for l in self.lines.all())


class SubcontractOrderLine(models.Model):
    order      = models.ForeignKey(SubcontractOrder, on_delete=models.CASCADE, related_name='lines')
    line_no    = models.PositiveIntegerField(default=1)
    item_name  = models.CharField(max_length=200)
    quantity   = models.DecimalField(max_digits=12, decimal_places=3)
    unit       = models.CharField(max_length=20, default='EA')
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    note       = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['line_no']

    @property
    def line_total(self):
        return float(self.quantity) * float(self.unit_price)

    def __str__(self):
        return f"{self.order.order_number} L{self.line_no}"


class SubcontractMaterial(models.Model):
    """사급 자재 – 외주업체에 지급하는 원자재/반제품"""
    order         = models.ForeignKey(SubcontractOrder, on_delete=models.CASCADE, related_name='materials')
    material      = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    material_name = models.CharField(max_length=200)
    quantity      = models.DecimalField(max_digits=12, decimal_places=3)
    unit          = models.CharField(max_length=20, default='EA')
    issued_qty    = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    returned_qty  = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    note          = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.order.order_number} – {self.material_name}"


class SubcontractReceipt(models.Model):
    """외주 완료품 입고 기록"""
    company        = models.ForeignKey(Company, on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)
    order          = models.ForeignKey(SubcontractOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='receipts')
    receipt_date   = models.DateField()
    item_name      = models.CharField(max_length=200)
    ordered_qty    = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    received_qty   = models.DecimalField(max_digits=12, decimal_places=3)
    rejected_qty   = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    warehouse      = models.CharField(max_length=100, blank=True)
    receiver       = models.CharField(max_length=100, blank=True)
    note           = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.receipt_number
