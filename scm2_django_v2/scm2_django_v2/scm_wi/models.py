from django.db import models
from django.conf import settings
from scm_accounts.models import Company
from scm_hr.models import Department


class WorkOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT',       '임시'),
        ('IN_PROGRESS', '진행중'),
        ('COMPLETED',   '완료'),
        ('CANCELLED',   '취소'),
    ]
    PRIORITY_CHOICES = [
        ('LOW',    '낮음'),
        ('MEDIUM', '보통'),
        ('HIGH',   '높음'),
        ('URGENT', '긴급'),
    ]

    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    order_number = models.CharField(max_length=50, unique=True)
    title        = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    assigned_to  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_work_orders'
    )
    department   = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    status       = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='DRAFT'
    )
    priority     = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM'
    )
    due_date     = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} - {self.title}"


class WorkOrderComment(models.Model):
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name='comments'
    )
    author     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='work_order_comments'
    )
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.work_order.order_number}] {self.author} - {self.created_at:%Y-%m-%d}"
