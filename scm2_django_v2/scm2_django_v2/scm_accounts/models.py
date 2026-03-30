from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    company_code = models.CharField(max_length=20, unique=True)
    company_name = models.CharField(max_length=200)
    business_no  = models.CharField(max_length=20, blank=True)
    plan         = models.CharField(max_length=20, default="BASIC")
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class User(AbstractUser):
    email      = models.EmailField(unique=True)
    name       = models.CharField(max_length=100, default="")
    department = models.CharField(max_length=100, blank=True)
    is_admin   = models.BooleanField(default=False)
    company    = models.ForeignKey(
        Company, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="users"
    )

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username", "name"]

    def __str__(self):
        return f"{self.name} ({self.email})"


class UserPermission(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name="module_permissions")
    module    = models.CharField(max_length=20)
    can_read  = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "module")
