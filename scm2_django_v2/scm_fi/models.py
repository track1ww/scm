from django.db import models
from scm_accounts.models import Company

class Account(models.Model):
    """계정과목 (K-GAAP CoA)"""
    TYPE = [('ASSET','자산'),('LIABILITY','부채'),('EQUITY','자본'),
            ('REVENUE','수익'),('EXPENSE','비용')]
    company      = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    code         = models.CharField(max_length=10)
    name         = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=TYPE)
    root_type    = models.CharField(max_length=50, blank=True)
    is_group     = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'code')

    def __str__(self): return f"{self.code} {self.name}"


class AccountMove(models.Model):
    """전표 헤더"""
    STATE = [('DRAFT','임시'),('POSTED','확정'),('CANCELLED','취소')]
    TYPE  = [('ENTRY','일반'),('PURCHASE','매입'),('SALE','매출'),
             ('PAYMENT','지급'),('RECEIPT','수금'),('ADJUST','조정')]
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

    def __str__(self): return self.move_number


class AccountMoveLine(models.Model):
    """전표 라인"""
    move         = models.ForeignKey(AccountMove, on_delete=models.CASCADE,
                                      related_name='lines')
    account      = models.ForeignKey(Account, on_delete=models.PROTECT)
    name         = models.CharField(max_length=200, blank=True)
    debit        = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit       = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_reconciled= models.BooleanField(default=False)
    due_date     = models.DateField(null=True, blank=True)

    def __str__(self): return f"{self.move.move_number} — {self.account.name}"


class Budget(models.Model):
    """예산"""
    company          = models.ForeignKey(Company, on_delete=models.CASCADE)
    budget_year      = models.IntegerField()
    budget_month     = models.IntegerField(null=True, blank=True)
    account          = models.ForeignKey(Account, on_delete=models.CASCADE)
    budgeted_amount  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual_amount    = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    variance         = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    note             = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['company', 'budget_year', 'budget_month', 'account']

    def __str__(self): return f"{self.account} {self.budget_year}-{self.budget_month}"


class FixedAsset(models.Model):
    """고정자산"""
    company                  = models.ForeignKey(Company, on_delete=models.CASCADE)
    asset_code               = models.CharField(max_length=50)
    asset_name               = models.CharField(max_length=200)
    category                 = models.CharField(max_length=50, choices=[
        ('machinery', '기계'), ('vehicle', '차량'), ('equipment', '설비'),
        ('furniture', '비품'), ('intangible', '무형자산')
    ])
    acquisition_date         = models.DateField()
    acquisition_cost         = models.DecimalField(max_digits=18, decimal_places=2)
    useful_life_years        = models.IntegerField(default=5)
    salvage_value            = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    depreciation_method      = models.CharField(max_length=20, choices=[
        ('straight_line', '정액법'), ('declining', '정률법')
    ], default='straight_line')
    accumulated_depreciation = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    book_value               = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status                   = models.CharField(max_length=20, choices=[
        ('active', '사용중'), ('disposed', '처분'), ('retired', '폐기')
    ], default='active')
    location                 = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ['company', 'asset_code']

    def __str__(self): return f"{self.asset_code} {self.asset_name}"


class DepreciationSchedule(models.Model):
    """감가상각 스케줄"""
    asset              = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name='schedules')
    period_year        = models.IntegerField()
    period_month       = models.IntegerField()
    depreciation_amount = models.DecimalField(max_digits=18, decimal_places=2)
    accumulated_amount = models.DecimalField(max_digits=18, decimal_places=2)
    book_value_after   = models.DecimalField(max_digits=18, decimal_places=2)
    is_posted          = models.BooleanField(default=False)

    class Meta:
        unique_together = ['asset', 'period_year', 'period_month']

    def __str__(self): return f"{self.asset.asset_code} {self.period_year}-{self.period_month:02d}"


class TaxInvoice(models.Model):
    """세금계산서"""
    TYPE = [('SALE', '매출'), ('PURCHASE', '매입')]
    STATUS = [('draft', '임시'), ('issued', '발행'), ('cancelled', '취소')]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE)
    invoice_number  = models.CharField(max_length=50, unique=True)
    invoice_type    = models.CharField(max_length=20, choices=TYPE, default='SALE')
    issue_date      = models.DateField()
    counterpart     = models.CharField(max_length=200, verbose_name='거래처')
    supply_amount   = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name='공급가액')
    vat_amount      = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name='부가세')
    total_amount    = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name='합계금액')
    status          = models.CharField(max_length=20, choices=STATUS, default='draft')
    remark          = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.invoice_number


class AccountingPeriod(models.Model):
    STATUS = [('open', '열림'), ('closed', '마감')]
    company      = models.ForeignKey('scm_accounts.Company', on_delete=models.CASCADE)
    year         = models.IntegerField(verbose_name='회계연도')
    month        = models.IntegerField(verbose_name='회계월')
    status       = models.CharField(max_length=10, choices=STATUS, default='open')
    closed_by    = models.ForeignKey(
        'scm_accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='closed_periods'
    )
    closed_at    = models.DateTimeField(null=True, blank=True)
    note         = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['company', 'year', 'month']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.year}-{self.month:02d} ({self.get_status_display()})"
