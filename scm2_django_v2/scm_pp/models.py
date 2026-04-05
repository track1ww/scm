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


class WorkCenterCost(models.Model):
    """작업장별 시간당 원가 (공정비 + 인건비 표준단가)"""
    company         = models.ForeignKey(Company, on_delete=models.CASCADE)
    work_center     = models.CharField(max_length=100)
    machine_rate    = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                          help_text='시간당 기계/공정비 (원)')
    labor_rate      = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                          help_text='시간당 인건비 표준단가 (원)')
    overhead_rate   = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                          help_text='시간당 간접비 (원)')
    effective_from  = models.DateField()
    effective_to    = models.DateField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.work_center} ({self.effective_from})"

    @property
    def total_rate(self):
        return self.machine_rate + self.labor_rate + self.overhead_rate


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
    # ── 원가 정밀화 필드 ──────────────────────────────────────────────
    planned_hours  = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                         help_text='계획 작업시간 (시간)')
    actual_hours   = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                         help_text='실제 작업시간 (시간)')
    material_cost  = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         help_text='자재원가 합계 (자동계산)')
    process_cost   = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         help_text='공정비 (기계비+간접비) 합계')
    labor_cost     = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         help_text='인건비 합계')
    total_cost     = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         help_text='총원가 = 자재+공정+인건비')
    # ─────────────────────────────────────────────────────────────────
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
