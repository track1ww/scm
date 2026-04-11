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
    lead_time_days = models.IntegerField(default=7)
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
    STATUS = [('발주확정','발주확정'),('납품중','납품중'),
              ('입고완료','입고완료'),('취소','취소')]
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    po_number    = models.CharField(max_length=50, unique=True)
    supplier     = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    item_name    = models.CharField(max_length=200)
    quantity     = models.IntegerField()
    unit_price   = models.DecimalField(max_digits=15, decimal_places=2)
    currency     = models.CharField(max_length=10, default='KRW')
    delivery_date= models.DateField(null=True, blank=True)
    warehouse    = models.CharField(max_length=100, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS, default='발주확정')
    note         = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.po_number


class PurchaseOrderLine(models.Model):
    """발주서 다품목 라인 (SalesOrderLine과 동일한 패턴)"""
    po         = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    line_no    = models.PositiveIntegerField(default=1)
    material   = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    item_name  = models.CharField(max_length=200)
    quantity   = models.IntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unit       = models.CharField(max_length=20, default='EA')
    note       = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['line_no']

    @property
    def line_total(self):
        return float(self.quantity) * float(self.unit_price)

    def __str__(self): return f"{self.po.po_number} L{self.line_no}"


class GoodsReceipt(models.Model):
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    gr_number    = models.CharField(max_length=50, unique=True)
    po           = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True)
    item_name    = models.CharField(max_length=200)
    ordered_qty  = models.IntegerField()
    received_qty = models.IntegerField()
    rejected_qty = models.IntegerField(default=0)
    warehouse    = models.CharField(max_length=100, blank=True)
    receiver     = models.CharField(max_length=100, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.gr_number


class RFQ(models.Model):
    """견적요청서"""
    company       = models.ForeignKey(Company, on_delete=models.CASCADE)
    rfq_number    = models.CharField(max_length=50, unique=True)
    supplier      = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    item_name     = models.CharField(max_length=200)
    quantity      = models.IntegerField()
    required_date = models.DateField(null=True, blank=True)
    status        = models.CharField(max_length=20, choices=[
        ('draft', '초안'), ('sent', '발송'), ('received', '견적수신'), ('closed', '마감')
    ], default='draft')
    note          = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.rfq_number


class SupplierEvaluation(models.Model):
    """공급업체 성과평가"""
    company        = models.ForeignKey(Company, on_delete=models.CASCADE)
    supplier       = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    eval_year      = models.IntegerField()
    eval_month     = models.IntegerField()
    delivery_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quality_score  = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    price_score    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_score    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade          = models.CharField(max_length=5, blank=True)
    note           = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['company', 'supplier', 'eval_year', 'eval_month']

    def __str__(self): return f"{self.supplier} {self.eval_year}-{self.eval_month:02d}"


class MaterialPriceHistory(models.Model):
    PRICE_TYPE = [('purchase', '구매단가'), ('standard', '표준원가')]
    company      = models.ForeignKey('scm_accounts.Company', on_delete=models.CASCADE)
    material     = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='price_history')
    supplier     = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)
    price_type   = models.CharField(max_length=20, choices=PRICE_TYPE, default='purchase')
    unit_price   = models.DecimalField(max_digits=15, decimal_places=2)
    currency     = models.CharField(max_length=10, default='KRW')
    effective_from = models.DateField()
    effective_to   = models.DateField(null=True, blank=True)
    note         = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.material.material_name} {self.unit_price} ({self.effective_from})"


class SupplierMaterialConfig(models.Model):
    """품목+매입처 조합별 리드타임 및 최소발주량 설정"""
    company        = models.ForeignKey('scm_accounts.Company', on_delete=models.CASCADE)
    material       = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='supplier_configs')
    supplier       = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='material_configs')
    lead_time_days = models.IntegerField(default=7)
    min_order_qty  = models.IntegerField(default=1)
    note           = models.CharField(max_length=200, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['company', 'material', 'supplier']

    def __str__(self):
        return f"{self.supplier.name} × {self.material.material_name} ({self.lead_time_days}일)"
