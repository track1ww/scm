from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from scm_accounts.models import Company


class ApprovalTemplate(models.Model):
    """결재 템플릿 — 회사/모듈/문서유형별 결재 흐름 정의"""
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='approval_templates'
    )
    name = models.CharField(max_length=100, verbose_name='템플릿명')
    module = models.CharField(max_length=50, verbose_name='모듈')   # 'mm', 'sd', 'hr', ...
    doc_type = models.CharField(max_length=50, verbose_name='문서유형')  # 'purchase_order', 'leave', ...
    is_active = models.BooleanField(default=True, verbose_name='활성')

    class Meta:
        unique_together = ('company', 'module', 'doc_type')
        ordering = ['company', 'module', 'doc_type']
        verbose_name = '결재 템플릿'
        verbose_name_plural = '결재 템플릿'

    def __str__(self):
        return f"[{self.company}] {self.name} ({self.module}/{self.doc_type})"


class ApprovalStep(models.Model):
    """결재 단계 — 템플릿에 속한 순서별 결재자 역할 정의"""
    template = models.ForeignKey(
        ApprovalTemplate, on_delete=models.CASCADE, related_name='steps'
    )
    step_no = models.IntegerField(verbose_name='단계번호')
    step_name = models.CharField(max_length=100, verbose_name='단계명')
    approver_role = models.CharField(max_length=100, blank=True, verbose_name='결재자 역할')

    class Meta:
        unique_together = ('template', 'step_no')
        ordering = ['template', 'step_no']
        verbose_name = '결재 단계'
        verbose_name_plural = '결재 단계'

    def __str__(self):
        return f"{self.template.name} - Step {self.step_no}: {self.step_name}"


class ApprovalRequest(models.Model):
    """결재 요청 — 특정 문서 객체에 대한 결재 진행 상태"""
    STATUS = [
        ('pending',   '대기'),
        ('approved',  '승인'),
        ('rejected',  '반려'),
        ('cancelled', '취소'),
    ]
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='approval_requests'
    )
    template = models.ForeignKey(
        ApprovalTemplate, on_delete=models.SET_NULL, null=True, related_name='requests'
    )
    requester = models.ForeignKey(
        'scm_accounts.User', on_delete=models.CASCADE, related_name='approval_requests'
    )
    # GenericForeignKey — 어떤 모델의 문서도 참조 가능
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    current_step = models.IntegerField(default=1, verbose_name='현재 단계')
    status = models.CharField(
        max_length=20, choices=STATUS, default='pending', verbose_name='상태'
    )
    title = models.CharField(max_length=200, blank=True, verbose_name='결재 제목')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='요청일시')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료일시')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = '결재 요청'
        verbose_name_plural = '결재 요청'

    def __str__(self):
        return f"[{self.get_status_display()}] {self.requester} - {self.created_at:%Y-%m-%d}"


class ApprovalAction(models.Model):
    """결재 행위 — 각 단계에서 결재자가 취한 행동 기록"""
    ACTION_CHOICES = [
        ('approved',  '승인'),
        ('rejected',  '반려'),
        ('delegated', '위임'),
    ]
    request = models.ForeignKey(
        ApprovalRequest, on_delete=models.CASCADE, related_name='actions'
    )
    step = models.ForeignKey(
        ApprovalStep, on_delete=models.SET_NULL, null=True, related_name='actions'
    )
    approver = models.ForeignKey(
        'scm_accounts.User', on_delete=models.CASCADE, related_name='approval_actions'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='행동')
    comment = models.TextField(blank=True, verbose_name='의견')
    acted_at = models.DateTimeField(auto_now_add=True, verbose_name='처리일시')

    class Meta:
        ordering = ['request', 'acted_at']
        verbose_name = '결재 행위'
        verbose_name_plural = '결재 행위'

    def __str__(self):
        return (
            f"[{self.get_action_display()}] {self.approver} "
            f"on request#{self.request_id} step#{self.step_id}"
        )
