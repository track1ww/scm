from django.db import models
from scm_accounts.models import Company


class InspectionPlan(models.Model):
    """검사 계획"""
    TYPE = [('수입검사', '수입검사'), ('공정검사', '공정검사'),
            ('출하검사', '출하검사'), ('정기검사', '정기검사')]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    plan_code       = models.CharField(max_length=50, unique=True)
    plan_name       = models.CharField(max_length=200)
    inspection_type = models.CharField(max_length=20, choices=TYPE, default='수입검사')
    target_item     = models.CharField(max_length=200, blank=True)
    criteria        = models.TextField(blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.plan_code} {self.plan_name}"


class InspectionResult(models.Model):
    """검사 결과"""
    RESULT = [('합격', '합격'), ('불합격', '불합격'), ('조건부합격', '조건부합격')]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    result_number   = models.CharField(max_length=50, unique=True)
    plan            = models.ForeignKey(InspectionPlan, on_delete=models.SET_NULL,
                                        null=True, blank=True)
    item_name       = models.CharField(max_length=200)
    lot_number      = models.CharField(max_length=100, blank=True)
    inspected_qty   = models.IntegerField(default=0)
    passed_qty      = models.IntegerField(default=0)
    failed_qty      = models.IntegerField(default=0)
    result          = models.CharField(max_length=20, choices=RESULT, default='합격')
    inspector       = models.CharField(max_length=100, blank=True)
    inspected_at    = models.DateTimeField(null=True, blank=True)
    remark          = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    @property
    def pass_rate(self):
        if self.inspected_qty == 0:
            return 0
        return round(self.passed_qty / self.inspected_qty * 100, 1)

    def __str__(self):
        return self.result_number


class DefectRecord(models.Model):
    """불량 현황"""
    SEVERITY = [('경미', '경미'), ('보통', '보통'), ('심각', '심각'), ('치명', '치명')]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    defect_number   = models.CharField(max_length=50, unique=True)
    inspection      = models.ForeignKey(InspectionResult, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='defects')
    item_name       = models.CharField(max_length=200)
    defect_type     = models.CharField(max_length=100)
    severity        = models.CharField(max_length=10, choices=SEVERITY, default='보통')
    quantity        = models.IntegerField(default=1)
    description     = models.TextField(blank=True)
    detected_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.defect_number


class CorrectiveAction(models.Model):
    """시정조치 (CAPA)"""
    STATUS = [('등록', '등록'), ('조사중', '조사중'), ('이행중', '이행중'),
              ('완료', '완료'), ('종결', '종결')]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    capa_number     = models.CharField(max_length=50, unique=True)
    defect          = models.ForeignKey(DefectRecord, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='actions')
    title           = models.CharField(max_length=200)
    root_cause      = models.TextField(blank=True)
    action_plan     = models.TextField(blank=True)
    responsible     = models.CharField(max_length=100, blank=True)
    due_date        = models.DateField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS, default='등록')
    completed_at    = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.capa_number


class SPCData(models.Model):
    """SPC 측정 데이터"""
    company           = models.ForeignKey(Company, on_delete=models.CASCADE)
    inspection_result = models.ForeignKey(InspectionResult, on_delete=models.CASCADE,
                                           related_name='spc_data')
    measurement_name  = models.CharField(max_length=100)
    measured_value    = models.DecimalField(max_digits=15, decimal_places=4)
    usl               = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    lsl               = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    target            = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    measured_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.inspection_result} - {self.measurement_name}"


class NCR(models.Model):
    """부적합 보고서 (Non-Conformance Report)"""
    company            = models.ForeignKey(Company, on_delete=models.CASCADE)
    ncr_number         = models.CharField(max_length=50, unique=True)
    defect_ref_number  = models.CharField(max_length=50, blank=True)
    title              = models.CharField(max_length=200)
    description        = models.TextField()
    root_cause         = models.TextField(blank=True)
    corrective_action  = models.TextField(blank=True)
    preventive_action  = models.TextField(blank=True)
    responsible        = models.CharField(max_length=100, blank=True)
    due_date           = models.DateField(null=True, blank=True)
    closed_date        = models.DateField(null=True, blank=True)
    status             = models.CharField(max_length=20, choices=[
        ('open', '개설'), ('in_progress', '처리중'), ('closed', '완료'), ('cancelled', '취소')
    ], default='open')
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.ncr_number
