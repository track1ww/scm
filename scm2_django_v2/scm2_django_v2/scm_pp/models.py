from django.db import models
from django.conf import settings
from scm_accounts.models import Company
from scm_mm.models import Material


class BOM(models.Model):
    company   = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    material  = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name='boms',
        verbose_name='완제품/반제품'
    )
    version    = models.CharField(max_length=20, default='1.0')
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'BOM'
        verbose_name_plural = 'BOM 목록'

    def __str__(self):
        return f"BOM [{self.material}] v{self.version}"


class BOMLine(models.Model):
    bom                = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name='lines')
    component_material = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name='bom_lines',
        verbose_name='구성 자재'
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=4)
    unit     = models.CharField(max_length=20, default='EA')

    class Meta:
        verbose_name = 'BOM 라인'
        verbose_name_plural = 'BOM 라인 목록'

    def __str__(self):
        return f"{self.bom} - {self.component_material} x{self.quantity}"


class ProductionOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT',       '초안'),
        ('RELEASED',    '릴리즈'),
        ('IN_PROGRESS', '진행중'),
        ('COMPLETED',   '완료'),
        ('CANCELLED',   '취소'),
    ]

    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    order_number = models.CharField(max_length=50, unique=True, verbose_name='생산오더번호')
    bom          = models.ForeignKey(BOM, on_delete=models.SET_NULL, null=True, related_name='production_orders')
    planned_qty  = models.DecimalField(max_digits=15, decimal_places=4, verbose_name='계획 수량')
    actual_qty   = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='실적 수량')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    planned_start = models.DateField(null=True, blank=True, verbose_name='계획 시작일')
    planned_end   = models.DateField(null=True, blank=True, verbose_name='계획 종료일')
    actual_start  = models.DateField(null=True, blank=True, verbose_name='실제 시작일')
    actual_end    = models.DateField(null=True, blank=True, verbose_name='실제 종료일')
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='production_orders'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '생산오더'
        verbose_name_plural = '생산오더 목록'

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"


class MRPPlan(models.Model):
    STATUS_CHOICES = [
        ('PENDING', '검토중'),
        ('ORDERED', '발주완료'),
        ('CLOSED',  '완료'),
    ]

    company            = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    plan_date          = models.DateField(verbose_name='계획 기준일')
    material           = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name='mrp_plans',
        verbose_name='자재'
    )
    required_qty       = models.DecimalField(max_digits=15, decimal_places=4, verbose_name='소요 수량')
    available_qty      = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='가용 수량')
    shortage_qty       = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='부족 수량')
    suggested_order_qty = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='발주 제안 수량')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        ordering = ['-plan_date', 'material']
        verbose_name = 'MRP 계획'
        verbose_name_plural = 'MRP 계획 목록'

    def __str__(self):
        return f"MRP [{self.material}] {self.plan_date} 부족:{self.shortage_qty}"
