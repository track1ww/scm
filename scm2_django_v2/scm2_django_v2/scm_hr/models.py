from django.db import models
from scm_accounts.models import Company

class Department(models.Model):
    company   = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    dept_code = models.CharField(max_length=20, unique=True)
    dept_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self): return self.dept_name


class Employee(models.Model):
    STATUS = [('재직','재직'),('퇴직','퇴직'),('휴직','휴직')]
    EMP_TYPE = [('정규직','정규직'),('계약직','계약직'),
                ('파견직','파견직'),('인턴','인턴')]
    company         = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    emp_code        = models.CharField(max_length=20, unique=True)
    name            = models.CharField(max_length=100)
    dept            = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    position        = models.CharField(max_length=50, blank=True)
    employment_type = models.CharField(max_length=20, choices=EMP_TYPE, default='정규직')
    hire_date       = models.DateField()
    resign_date     = models.DateField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS, default='재직')
    email           = models.EmailField(blank=True)
    phone           = models.CharField(max_length=50, blank=True)
    base_salary     = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.emp_code} {self.name}"


class Payroll(models.Model):
    STATE = [('DRAFT','임시'),('확정','확정')]
    company              = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    payroll_number       = models.CharField(max_length=50, unique=True)
    employee             = models.ForeignKey(Employee, on_delete=models.CASCADE)
    pay_year             = models.IntegerField()
    pay_month            = models.IntegerField()
    base_salary          = models.DecimalField(max_digits=15, decimal_places=2)
    overtime_pay         = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus                = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gross_pay            = models.DecimalField(max_digits=15, decimal_places=2)
    national_pension     = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    health_insurance     = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employment_insurance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    income_tax           = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deduction      = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_pay              = models.DecimalField(max_digits=15, decimal_places=2)
    state                = models.CharField(max_length=20, choices=STATE, default='DRAFT')
    payment_date         = models.DateField(null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.payroll_number} {self.employee.name}"
