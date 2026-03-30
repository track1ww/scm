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


class Attendance(models.Model):
    """근태 기록"""
    company        = models.ForeignKey(Company, on_delete=models.CASCADE)
    employee       = models.ForeignKey(Employee, on_delete=models.CASCADE)
    work_date      = models.DateField()
    check_in       = models.TimeField(null=True, blank=True)
    check_out      = models.TimeField(null=True, blank=True)
    work_type      = models.CharField(max_length=20, choices=[
        ('normal', '정상'), ('late', '지각'), ('early', '조퇴'), ('absent', '결근'),
        ('holiday', '휴일근무'), ('overtime', '야근')
    ], default='normal')
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    note           = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['employee', 'work_date']

    def __str__(self): return f"{self.employee} {self.work_date}"


class Leave(models.Model):
    """휴가 신청"""
    LEAVE_TYPES = [
        ('annual', '연차'), ('half', '반차'), ('sick', '병가'),
        ('special', '특별휴가'), ('unpaid', '무급휴가')
    ]
    company     = models.ForeignKey(Company, on_delete=models.CASCADE)
    employee    = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type  = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date  = models.DateField()
    end_date    = models.DateField()
    days        = models.DecimalField(max_digits=4, decimal_places=1)
    reason      = models.CharField(max_length=200, blank=True)
    status      = models.CharField(max_length=20, choices=[
        ('pending', '대기'), ('approved', '승인'), ('rejected', '반려'), ('cancelled', '취소')
    ], default='pending')
    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_leaves'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.employee} {self.leave_type} {self.start_date}"


class LeaveBalance(models.Model):
    """연차 잔여일수"""
    company         = models.ForeignKey(Company, on_delete=models.CASCADE)
    employee        = models.ForeignKey(Employee, on_delete=models.CASCADE)
    year            = models.IntegerField()
    total_days      = models.DecimalField(max_digits=5, decimal_places=1, default=15)
    used_days       = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    remaining_days  = models.DecimalField(max_digits=5, decimal_places=1, default=15)

    class Meta:
        unique_together = ['employee', 'year']

    def __str__(self): return f"{self.employee} {self.year}년 연차"
