from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from scm_accounts.models import Company


class Account(models.Model):
    """계정과목 (K-GAAP CoA)"""
    TYPE = [
        ('ASSET',     '자산'),
        ('LIABILITY', '부채'),
        ('EQUITY',    '자본'),
        ('REVENUE',   '수익'),
        ('EXPENSE',   '비용'),
    ]
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    code         = models.CharField(max_length=10)
    name         = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=TYPE)
    root_type    = models.CharField(max_length=50, blank=True)
    is_group     = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')

    def __str__(self):
        return f"{self.code} {self.name}"


class AccountMove(models.Model):
    """전표 헤더"""
    STATE = [
        ('DRAFT',     '임시'),
        ('POSTED',    '확정'),
        ('CANCELLED', '취소'),
    ]
    TYPE = [
        ('ENTRY',   '일반'),
        ('PURCHASE','매입'),
        ('SALE',    '매출'),
        ('PAYMENT', '지급'),
        ('RECEIPT', '수금'),
        ('ADJUST',  '조정'),
    ]

    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    move_number  = models.CharField(max_length=50, unique=True)
    move_type    = models.CharField(max_length=20, choices=TYPE)
    posting_date = models.DateField()
    ref          = models.CharField(max_length=200, blank=True)
    state        = models.CharField(max_length=20, choices=STATE, default='DRAFT')
    total_debit  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_by   = models.CharField(max_length=100, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    posted_at    = models.DateTimeField(null=True, blank=True)

    # 회계 기간
    period_year  = models.IntegerField(null=True, blank=True, verbose_name='회계 연도')
    period_month = models.IntegerField(null=True, blank=True, verbose_name='회계 월')

    # 기간 마감 잠금
    is_locked    = models.BooleanField(default=False, verbose_name='기간 마감 잠금')

    class Meta:
        ordering = ['-posting_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'period_year', 'period_month']),
            models.Index(fields=['company', 'state']),
            models.Index(fields=['posting_date']),
        ]

    def __str__(self):
        return self.move_number

    def _validate_balanced(self):
        """대차 일치 검증: total_debit == total_credit"""
        if self.total_debit != self.total_credit:
            raise ValidationError(
                f"대차가 일치하지 않습니다. "
                f"차변 합계({self.total_debit}) ≠ 대변 합계({self.total_credit})"
            )

    def _auto_fill_period(self):
        """posting_date 기반으로 period_year/period_month 자동 설정"""
        if self.posting_date and (not self.period_year or not self.period_month):
            self.period_year  = self.posting_date.year
            self.period_month = self.posting_date.month

    def save(self, *args, **kwargs):
        # 기간 마감 잠금 수정 차단
        if self.pk:
            try:
                original = AccountMove.objects.get(pk=self.pk)
                if original.is_locked:
                    raise ValidationError(
                        "기간이 마감된 전표는 수정할 수 없습니다. "
                        "관리자에게 마감 해제를 요청하세요."
                    )
            except AccountMove.DoesNotExist:
                pass

        # 회계 기간 자동 설정
        self._auto_fill_period()

        # POSTED 전환 시 대차 일치 검증
        if self.state == 'POSTED':
            self._validate_balanced()
            if not self.posted_at:
                self.posted_at = timezone.now()

        super().save(*args, **kwargs)


class AccountMoveLine(models.Model):
    """전표 라인"""
    move          = models.ForeignKey(
        AccountMove, on_delete=models.CASCADE, related_name='lines'
    )
    account       = models.ForeignKey(Account, on_delete=models.PROTECT)
    name          = models.CharField(max_length=200, blank=True)
    debit         = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit        = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_reconciled = models.BooleanField(default=False)
    due_date      = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['account']),
            models.Index(fields=['move']),
        ]

    def __str__(self):
        return f"{self.move.move_number} — {self.account.name}"


class TaxInvoice(models.Model):
    """세금계산서"""
    INVOICE_TYPE_CHOICES = [
        ('PURCHASE', '매입'),
        ('SALE',     '매출'),
    ]
    STATUS_CHOICES = [
        ('DRAFT',     '임시'),
        ('ISSUED',    '발행'),
        ('CANCELLED', '취소'),
    ]

    company                  = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, verbose_name='회사'
    )
    invoice_number           = models.CharField(
        max_length=50, unique=True, verbose_name='세금계산서 번호'
    )
    invoice_type             = models.CharField(
        max_length=10, choices=INVOICE_TYPE_CHOICES, verbose_name='유형(매입/매출)'
    )
    supplier_or_customer_name = models.CharField(
        max_length=200, verbose_name='공급자/수요자명'
    )
    supply_amount            = models.DecimalField(
        max_digits=18, decimal_places=2, verbose_name='공급가액'
    )
    tax_amount               = models.DecimalField(
        max_digits=18, decimal_places=2, verbose_name='세액'
    )
    total_amount             = models.DecimalField(
        max_digits=18, decimal_places=2, verbose_name='합계금액'
    )
    issue_date               = models.DateField(verbose_name='발행일')
    account_move             = models.ForeignKey(
        AccountMove, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tax_invoices', verbose_name='연결 전표'
    )
    status                   = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='DRAFT',
        verbose_name='상태'
    )
    created_by               = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tax_invoices_created',
        verbose_name='작성자'
    )
    created_at               = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = '세금계산서'
        verbose_name_plural = '세금계산서 목록'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['company', 'invoice_type', 'status']),
            models.Index(fields=['company', 'issue_date']),
            models.Index(fields=['invoice_number']),
        ]

    def clean(self):
        """tax_amount와 total_amount 자동 검증"""
        from decimal import Decimal
        expected_tax   = (self.supply_amount * Decimal('0.1')).quantize(Decimal('0.01'))
        expected_total = self.supply_amount + self.tax_amount
        if self.tax_amount != expected_tax:
            raise ValidationError(
                f'세액은 공급가액의 10%여야 합니다. '
                f'공급가액: {self.supply_amount}, 기대 세액: {expected_tax}'
            )
        if self.total_amount != expected_total:
            raise ValidationError(
                f'합계금액은 공급가액 + 세액이어야 합니다. '
                f'기대 합계: {expected_total}'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.get_invoice_type_display()}] {self.invoice_number}"
