from django.db import models
from scm_accounts.models import Company


class BillOfMaterial(models.Model):
    """BOM (자재명세서)"""
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    bom_code       = models.CharField(max_length=50, unique=True)
    product_name   = models.CharField(max_length=200)
    version        = models.CharField(max_length=20, default='1.0')
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bom_code} {self.product_name}"


class BomLine(models.Model):
    """BOM 구성 라인"""
    bom            = models.ForeignKey(BillOfMaterial, on_delete=models.CASCADE,
                                       related_name='lines')
    material_code  = models.CharField(max_length=50)
    material_name  = models.CharField(max_length=200)
    quantity       = models.DecimalField(max_digits=12, decimal_places=3)
    unit           = models.CharField(max_length=20, default='EA')
    scrap_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.bom.bom_code} - {self.material_name}"


class ProductionOrder(models.Model):
    """생산오더"""
    STATUS = [
        ('계획', '계획'), ('확정', '확정'), ('생산중', '생산중'),
        ('완료', '완료'), ('취소', '취소'),
    ]
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    order_number   = models.CharField(max_length=50, unique=True)
    bom            = models.ForeignKey(BillOfMaterial, on_delete=models.SET_NULL,
                                       null=True, blank=True)
    product_name   = models.CharField(max_length=200)
    planned_qty    = models.IntegerField()
    produced_qty   = models.IntegerField(default=0)
    defect_qty     = models.IntegerField(default=0)
    status         = models.CharField(max_length=20, choices=STATUS, default='계획')
    planned_start  = models.DateField(null=True, blank=True)
    planned_end    = models.DateField(null=True, blank=True)
    actual_start   = models.DateField(null=True, blank=True)
    actual_end     = models.DateField(null=True, blank=True)
    work_center    = models.CharField(max_length=100, blank=True)
    note           = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def completion_rate(self):
        if self.planned_qty == 0:
            return 0
        return round(self.produced_qty / self.planned_qty * 100, 1)

    def __str__(self):
        return self.order_number


class MrpRun(models.Model):
    """MRP 실행 이력"""
    STATUS = [('실행중', '실행중'), ('완료', '완료'), ('오류', '오류')]
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    run_number     = models.CharField(max_length=50, unique=True)
    run_date       = models.DateTimeField(auto_now_add=True)
    status         = models.CharField(max_length=20, choices=STATUS, default='실행중')
    total_items    = models.IntegerField(default=0)
    planned_orders = models.IntegerField(default=0)
    note           = models.TextField(blank=True)

    def __str__(self):
        return self.run_number
