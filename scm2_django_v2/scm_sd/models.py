from django.db import models
from scm_accounts.models import Company

class Customer(models.Model):
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    customer_code = models.CharField(max_length=20, unique=True)
    customer_name = models.CharField(max_length=200)
    contact       = models.CharField(max_length=100, blank=True)
    email         = models.EmailField(blank=True)
    credit_limit  = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=50, default='30일')
    status        = models.CharField(max_length=20, default='활성')
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.customer_name


class SalesOrder(models.Model):
    STATUS = [('주문접수','주문접수'),('생산/조달중','생산/조달중'),
              ('출하준비','출하준비'),('배송중','배송중'),
              ('배송완료','배송완료'),('취소','취소')]
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    order_number  = models.CharField(max_length=50, unique=True)
    customer      = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    customer_name = models.CharField(max_length=200)
    item_name     = models.CharField(max_length=200)
    quantity      = models.IntegerField()
    unit_price    = models.DecimalField(max_digits=15, decimal_places=2)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status        = models.CharField(max_length=20, choices=STATUS, default='주문접수')
    shipped_qty   = models.IntegerField(default=0)
    ordered_at    = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        from decimal import Decimal
        dr = self.discount_rate if isinstance(self.discount_rate, Decimal) else Decimal(str(self.discount_rate))
        return float(self.quantity * self.unit_price * (1 - dr / 100))

    def __str__(self): return self.order_number


class Delivery(models.Model):
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    delivery_number = models.CharField(max_length=50, unique=True)
    order           = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, null=True)
    item_name       = models.CharField(max_length=200)
    delivery_qty    = models.IntegerField()
    carrier         = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    delivery_date   = models.DateField(null=True, blank=True)
    status          = models.CharField(max_length=20, default='출하준비')
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.delivery_number


class SalesOrderLine(models.Model):
    """수주 라인 (다품목 지원)"""
    order         = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    line_no       = models.IntegerField(default=1)
    item_name     = models.CharField(max_length=200)
    quantity      = models.IntegerField()
    unit_price    = models.DecimalField(max_digits=15, decimal_places=2)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount        = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    delivery_date = models.DateField(null=True, blank=True)
    note          = models.CharField(max_length=200, blank=True)

    def __str__(self): return f"{self.order.order_number} L{self.line_no}"


class SalesInvoice(models.Model):
    STATUS = [
        ('draft',     '임시'),
        ('issued',    '발행'),
        ('paid',      '수금완료'),
        ('cancelled', '취소'),
    ]
    company         = models.ForeignKey('scm_accounts.Company', on_delete=models.CASCADE)
    sales_order     = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='invoices')
    delivery        = models.ForeignKey(Delivery, null=True, blank=True, on_delete=models.SET_NULL)
    invoice_number  = models.CharField(max_length=30, unique=True)
    invoice_date    = models.DateField()
    due_date        = models.DateField(null=True, blank=True)
    supply_amount   = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    vat_amount      = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status          = models.CharField(max_length=20, choices=STATUS, default='draft')
    note            = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date', '-created_at']

    def __str__(self):
        return self.invoice_number


class CustomerCreditHistory(models.Model):
    """고객 여신 이력"""
    company          = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer         = models.ForeignKey(Customer, on_delete=models.CASCADE)
    transaction_date = models.DateField()
    amount           = models.DecimalField(max_digits=15, decimal_places=2)
    balance          = models.DecimalField(max_digits=15, decimal_places=2)
    note             = models.CharField(max_length=200, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.customer} {self.transaction_date}"
