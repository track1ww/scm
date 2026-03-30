from django.db import models
from scm_accounts.models import Company


class AuditLog(models.Model):
    """감사 로그 — 모든 CREATE / UPDATE / DELETE 작업 이력 기록"""
    ACTION_CHOICES = [
        ('CREATE', '생성'),
        ('UPDATE', '수정'),
        ('DELETE', '삭제'),
    ]
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='audit_logs'
    )
    user = models.ForeignKey(
        'scm_accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='audit_logs'
    )
    action = models.CharField(
        max_length=10, choices=ACTION_CHOICES, verbose_name='작업'
    )
    module = models.CharField(max_length=50, verbose_name='모듈')
    model_name = models.CharField(max_length=100, verbose_name='모델명')
    object_id = models.IntegerField(verbose_name='객체 ID')
    object_repr = models.CharField(
        max_length=200, blank=True, verbose_name='객체 표현'
    )
    # 변경 전후 데이터 — {'field': {'before': ..., 'after': ...}} 구조 권장
    changes = models.JSONField(default=dict, verbose_name='변경 내역')
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name='IP 주소'
    )
    user_agent = models.CharField(
        max_length=500, blank=True, verbose_name='User-Agent'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='기록일시')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'module']),
            models.Index(fields=['company', 'model_name', 'object_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
        verbose_name = '감사 로그'
        verbose_name_plural = '감사 로그'

    def __str__(self):
        user_repr = self.user.name if self.user else '시스템'
        return (
            f"[{self.action}] {self.module}.{self.model_name}#{self.object_id}"
            f" by {user_repr} at {self.created_at:%Y-%m-%d %H:%M}"
        )
