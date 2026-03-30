from django.db import models
from scm_accounts.models import Company


class Carrier(models.Model):
    """운송사 마스터"""
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    carrier_code   = models.CharField(max_length=20, unique=True)
    carrier_name   = models.CharField(max_length=200)
    contact        = models.CharField(max_length=100, blank=True)
    phone          = models.CharField(max_length=50, blank=True)
    email          = models.EmailField(blank=True)
    vehicle_type   = models.CharField(max_length=50, blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.carrier_code} {self.carrier_name}"


class TransportOrder(models.Model):
    """운송 계획/오더"""
    STATUS = [
        ('계획', '계획'), ('배차완료', '배차완료'), ('운송중', '운송중'),
        ('도착', '도착'), ('완료', '완료'), ('취소', '취소'),
    ]
    company          = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    transport_number = models.CharField(max_length=50, unique=True)
    carrier          = models.ForeignKey(Carrier, on_delete=models.SET_NULL,
                                          null=True, blank=True)
    origin           = models.CharField(max_length=200)
    destination      = models.CharField(max_length=200)
    item_description = models.CharField(max_length=200, blank=True)
    weight_kg        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    volume_cbm       = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    freight_cost     = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency         = models.CharField(max_length=10, default='KRW')
    status           = models.CharField(max_length=20, choices=STATUS, default='계획')
    planned_date     = models.DateField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival   = models.DateTimeField(null=True, blank=True)
    tracking_number  = models.CharField(max_length=100, blank=True)
    note             = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transport_number


class FreightRate(models.Model):
    """운임 단가표"""
    company        = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    carrier        = models.ForeignKey(Carrier, on_delete=models.CASCADE,
                                        related_name='rates')
    origin         = models.CharField(max_length=200)
    destination    = models.CharField(max_length=200)
    rate_per_kg    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rate_per_cbm   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_charge     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency       = models.CharField(max_length=10, default='KRW')
    valid_from     = models.DateField()
    valid_to       = models.DateField(null=True, blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-valid_from']

    def __str__(self):
        return f"{self.carrier.carrier_name}: {self.origin} -> {self.destination}"


class ShipmentTracking(models.Model):
    """운송 추적 이벤트"""
    company          = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    transport_order  = models.ForeignKey(TransportOrder, on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='tracking_events')
    transport_number = models.CharField(max_length=50, blank=True)
    location         = models.CharField(max_length=200)
    status_note      = models.CharField(max_length=200, blank=True)
    tracked_at       = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tracked_at', '-created_at']

    def __str__(self):
        return f"{self.transport_number or str(self.transport_order_id)} @ {self.location}"
