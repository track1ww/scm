from django.db import models
from django.conf import settings
from scm_accounts.models import Company


class Carrier(models.Model):
    """운송사 마스터"""
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    carrier_code = models.CharField(max_length=50, unique=True, verbose_name='운송사 코드')
    name         = models.CharField(max_length=200, verbose_name='운송사명')
    contact_name = models.CharField(max_length=100, blank=True, verbose_name='담당자명')
    phone        = models.CharField(max_length=50, blank=True, verbose_name='전화번호')
    email        = models.EmailField(blank=True, verbose_name='이메일')
    is_active    = models.BooleanField(default=True, verbose_name='활성 여부')

    class Meta:
        verbose_name        = '운송사'
        verbose_name_plural = '운송사 목록'
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['carrier_code']),
        ]

    def __str__(self) -> str:
        return f"[{self.carrier_code}] {self.name}"


class TransportOrder(models.Model):
    """운송지시"""
    STATUS_CHOICES = [
        ('DRAFT',      '임시'),
        ('CONFIRMED',  '확정'),
        ('IN_TRANSIT', '운송중'),
        ('DELIVERED',  '배송완료'),
        ('CANCELLED',  '취소'),
    ]
    REFERENCE_TYPE_CHOICES = [
        ('PO',    '구매오더'),
        ('SO',    '판매오더'),
        ('OTHER', '기타'),
    ]

    company             = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, verbose_name='회사'
    )
    order_number        = models.CharField(
        max_length=50, unique=True, verbose_name='운송지시번호'
    )
    carrier             = models.ForeignKey(
        Carrier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transport_orders', verbose_name='운송사'
    )
    origin_address      = models.CharField(max_length=500, verbose_name='출발지 주소')
    destination_address = models.CharField(max_length=500, verbose_name='도착지 주소')
    cargo_description   = models.TextField(blank=True, verbose_name='화물 내용')
    weight_kg           = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
        verbose_name='중량(kg)'
    )
    volume_cbm          = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
        verbose_name='부피(CBM)'
    )
    planned_departure   = models.DateTimeField(verbose_name='예정 출발일시')
    actual_departure    = models.DateTimeField(
        null=True, blank=True, verbose_name='실제 출발일시'
    )
    planned_arrival     = models.DateTimeField(verbose_name='예정 도착일시')
    actual_arrival      = models.DateTimeField(
        null=True, blank=True, verbose_name='실제 도착일시'
    )
    freight_cost        = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='운임(원)'
    )
    status              = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='DRAFT',
        verbose_name='상태'
    )
    reference_type      = models.CharField(
        max_length=10, choices=REFERENCE_TYPE_CHOICES, default='OTHER',
        verbose_name='참조 유형'
    )
    reference_number    = models.CharField(
        max_length=100, blank=True, verbose_name='참조번호'
    )
    created_by          = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transport_orders_created',
        verbose_name='작성자'
    )
    created_at          = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        verbose_name        = '운송지시'
        verbose_name_plural = '운송지시 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'planned_departure']),
            models.Index(fields=['carrier']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self) -> str:
        return self.order_number


class TransportTracking(models.Model):
    """운송 추적 이력"""
    transport_order = models.ForeignKey(
        TransportOrder, on_delete=models.CASCADE,
        related_name='tracking_records', verbose_name='운송지시'
    )
    location        = models.CharField(max_length=300, verbose_name='현재 위치')
    status_update   = models.TextField(verbose_name='상태 업데이트 내용')
    timestamp       = models.DateTimeField(verbose_name='기록 일시')
    recorded_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tracking_records',
        verbose_name='기록자'
    )

    class Meta:
        verbose_name        = '운송 추적'
        verbose_name_plural = '운송 추적 이력'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transport_order', 'timestamp']),
        ]

    def __str__(self) -> str:
        return f"{self.transport_order.order_number} @ {self.location}"
