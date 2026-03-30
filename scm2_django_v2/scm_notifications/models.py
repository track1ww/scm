from django.db import models
from scm_accounts.models import Company


class Notification(models.Model):
    """사용자 알림 — 결재, 납기, 재고 부족 등 다양한 유형의 인앱 알림"""
    TYPES = [
        ('approval_request',  '결재요청'),
        ('approval_result',   '결재결과'),
        ('deadline_warning',  '납기임박'),
        ('low_stock',         '부족재고'),
        ('inspection_result', '검사결과'),
        ('system',            '시스템'),
    ]
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='notifications'
    )
    recipient = models.ForeignKey(
        'scm_accounts.User', on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30, choices=TYPES, verbose_name='알림유형'
    )
    title = models.CharField(max_length=200, verbose_name='제목')
    message = models.TextField(verbose_name='내용')
    is_read = models.BooleanField(default=False, verbose_name='읽음')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='읽은 일시')

    # 참조 문서 — 어떤 모듈의 어떤 레코드에 대한 알림인지
    ref_module = models.CharField(max_length=50, blank=True, verbose_name='참조 모듈')
    ref_id = models.IntegerField(null=True, blank=True, verbose_name='참조 ID')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['company', 'notification_type']),
            models.Index(fields=['recipient', 'created_at']),
        ]
        verbose_name = '알림'
        verbose_name_plural = '알림'

    def __str__(self):
        read_flag = '[읽음]' if self.is_read else '[미읽음]'
        return f"{read_flag} {self.recipient} — {self.title}"
