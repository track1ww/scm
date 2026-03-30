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
    STATUS = [
        ('draft',       '주문접수'),
        ('confirmed',   '생산/조달중'),
        ('ready',       '출하준비'),
        ('in_delivery', '배송중'),
        ('delivered',   '배송완료'),
        ('cancelled',   '취소'),
    ]
    company       = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    order_number  = models.CharField(max_length=50, unique=True)
    customer      = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    customer_name = models.CharField(max_length=200, blank=True)
    item_name     = models.CharField(max_length=200)
    quantity      = models.IntegerField()
    unit_price    = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status        = models.CharField(max_length=20, choices=STATUS, default='draft')
    shipped_qty   = models.IntegerField(default=0)
    ordered_at    = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        return float(self.quantity * self.unit_price * (1 - self.discount_rate / 100))

    def __str__(self): return self.order_number


class Delivery(models.Model):
    STATUS = [
        ('pending',   '출하준비'),
        ('shipped',   '배송중'),
        ('delivered', '배송완료'),
        ('cancelled', '취소'),
    ]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    delivery_number = models.CharField(max_length=50, unique=True)
    order           = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, null=True)
    item_name       = models.CharField(max_length=200, blank=True)
    delivery_qty    = models.IntegerField()
    carrier         = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    delivery_date   = models.DateField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.delivery_number
