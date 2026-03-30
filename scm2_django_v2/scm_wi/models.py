from django.db import models
from scm_accounts.models import Company


class WorkInstruction(models.Model):
    STATUS = [
        ('대기', '대기'), ('진행중', '진행중'),
        ('완료', '완료'), ('보류', '보류'), ('취소', '취소'),
    ]
    PRIORITY = [('높음', '높음'), ('보통', '보통'), ('낮음', '낮음')]

    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    wi_number      = models.CharField(max_length=50, unique=True)
    title          = models.CharField(max_length=200)
    description    = models.TextField(blank=True)
    work_center    = models.CharField(max_length=100, blank=True)
    assigned_to    = models.CharField(max_length=100, blank=True)
    priority       = models.CharField(max_length=10, choices=PRIORITY, default='보통')
    status         = models.CharField(max_length=20, choices=STATUS, default='대기')
    planned_start  = models.DateTimeField(null=True, blank=True)
    planned_end    = models.DateTimeField(null=True, blank=True)
    actual_start   = models.DateTimeField(null=True, blank=True)
    actual_end     = models.DateTimeField(null=True, blank=True)
    planned_qty    = models.IntegerField(default=0)
    actual_qty     = models.IntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.wi_number


class WorkResult(models.Model):
    work_instruction = models.ForeignKey(
        WorkInstruction, on_delete=models.CASCADE, related_name='results'
    )
    worker_name      = models.CharField(max_length=100)
    result_date      = models.DateField()
    produced_qty     = models.IntegerField(default=0)
    defect_qty       = models.IntegerField(default=0)
    work_hours       = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    remark           = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.work_instruction.wi_number} - {self.result_date}"
