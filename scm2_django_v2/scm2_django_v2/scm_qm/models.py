from django.db import models
from django.conf import settings
from scm_accounts.models import Company
from scm_mm.models import Material


class InspectionPlan(models.Model):
    INSPECTION_TYPE_CHOICES = [
        ('INCOMING', '수입검사'),
        ('PROCESS',  '공정검사'),
        ('FINAL',    '최종검사'),
        ('PERIODIC', '정기검사'),
    ]

    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    material        = models.ForeignKey(
        Material, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inspection_plans', verbose_name='대상 자재'
    )
    inspection_type = models.CharField(
        max_length=20, choices=INSPECTION_TYPE_CHOICES, default='INCOMING',
        verbose_name='검사 유형'
    )
    sampling_method = models.CharField(max_length=100, blank=True, verbose_name='샘플링 방법')
    sample_size     = models.IntegerField(default=1, verbose_name='샘플 크기')
    criteria        = models.TextField(blank=True, verbose_name='합격 기준')
    is_active       = models.BooleanField(default=True)

    class Meta:
        ordering = ['inspection_type', 'material']
        verbose_name = '검사계획'
        verbose_name_plural = '검사계획 목록'

    def __str__(self):
        return f"[{self.get_inspection_type_display()}] {self.material or '공통'}"


class InspectionResult(models.Model):
    REFERENCE_TYPE_CHOICES = [
        ('GR',       '입고'),
        ('SO',       '출고'),
        ('PERIODIC', '정기'),
    ]
    STATUS_CHOICES = [
        ('PENDING',     '검사중'),
        ('PASSED',      '합격'),
        ('FAILED',      '불합격'),
        ('CONDITIONAL', '조건부합격'),
    ]

    company          = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    plan             = models.ForeignKey(
        InspectionPlan, on_delete=models.SET_NULL, null=True,
        related_name='results', verbose_name='검사계획'
    )
    reference_type   = models.CharField(max_length=20, choices=REFERENCE_TYPE_CHOICES, default='GR')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='참조번호')
    inspected_qty    = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='검사 수량')
    passed_qty       = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='합격 수량')
    failed_qty       = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='불합격 수량')
    inspector        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='inspections', verbose_name='검사자'
    )
    inspection_date  = models.DateField(verbose_name='검사일')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remarks          = models.TextField(blank=True, verbose_name='비고')

    class Meta:
        ordering = ['-inspection_date']
        verbose_name = '검사결과'
        verbose_name_plural = '검사결과 목록'

    def __str__(self):
        return f"{self.reference_number} ({self.get_status_display()})"

    @property
    def pass_rate(self) -> float:
        if self.inspected_qty and self.inspected_qty > 0:
            return round(float(self.passed_qty / self.inspected_qty * 100), 1)
        return 0.0


class DefectReport(models.Model):
    SEVERITY_CHOICES = [
        ('MINOR',    '경결함'),
        ('MAJOR',    '중결함'),
        ('CRITICAL', '치명결함'),
    ]
    STATUS_CHOICES = [
        ('OPEN',        '미처리'),
        ('IN_PROGRESS', '처리중'),
        ('CLOSED',      '완료'),
    ]

    company           = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    inspection        = models.ForeignKey(
        InspectionResult, on_delete=models.CASCADE,
        related_name='defect_reports', verbose_name='검사결과'
    )
    defect_type       = models.CharField(max_length=100, verbose_name='결함 유형')
    defect_qty        = models.DecimalField(max_digits=15, decimal_places=4, default=0, verbose_name='결함 수량')
    severity          = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MINOR')
    description       = models.TextField(blank=True, verbose_name='결함 설명')
    corrective_action = models.TextField(blank=True, verbose_name='시정 조치')
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '결함보고'
        verbose_name_plural = '결함보고 목록'

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.defect_type} ({self.get_status_display()})"
