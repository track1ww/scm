from django.db import models
from scm_accounts.models import Company

class Supplier(models.Model):
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    name          = models.CharField(max_length=200)
    contact       = models.CharField(max_length=100, blank=True)
    email         = models.EmailField(blank=True)
    phone         = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=50, default='30일')
    status        = models.CharField(max_length=20, default='활성')
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.name


class Material(models.Model):
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    material_code  = models.CharField(max_length=50, unique=True)
    material_name  = models.CharField(max_length=200)
    material_type  = models.CharField(max_length=50, default='원재료')
    unit           = models.CharField(max_length=20, default='EA')
    min_stock      = models.IntegerField(default=0)
    lead_time_days = models.IntegerField(default=7)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.material_code} {self.material_name}"


class PurchaseOrder(models.Model):
    STATUS = [
        ('pending',   '대기'),
        ('ordered',   '발주완료'),
        ('confirmed', '확정'),
        ('received',  '입고완료'),
        ('partial',   '부분입고'),
        ('cancelled', '취소'),
    ]
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    po_number    = models.CharField(max_length=50, unique=True)
    supplier     = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    item_name    = models.CharField(max_length=200)
    quantity     = models.IntegerField()
    unit_price   = models.DecimalField(max_digits=15, decimal_places=2)
    currency     = models.CharField(max_length=10, default='KRW')
    delivery_date= models.DateField(null=True, blank=True)
    warehouse    = models.CharField(max_length=100, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS, default='pending')
    note         = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.po_number


class GoodsReceipt(models.Model):
    STATUS = [
        ('draft',     '임시저장'),
        ('confirmed', '입고확인'),
        ('completed', '입고완료'),
        ('cancelled', '취소'),
    ]
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    gr_number    = models.CharField(max_length=50, unique=True)
    po           = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True)
    item_name    = models.CharField(max_length=200)
    ordered_qty  = models.IntegerField()
    received_qty = models.IntegerField()
    rejected_qty = models.IntegerField(default=0)
    warehouse    = models.CharField(max_length=100, blank=True)
    receiver     = models.CharField(max_length=100, blank=True)
    status       = models.CharField(
        max_length=20, choices=STATUS, default='draft',
        verbose_name='상태'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.gr_number
