from django.contrib import admin

from .models import Department, Employee, Payroll


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('dept_code', 'dept_name', 'is_active', 'company')
    list_filter = ('is_active', 'company')
    search_fields = ('dept_code', 'dept_name')
    ordering = ('dept_code',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('emp_code', 'name', 'dept', 'position', 'employment_type', 'hire_date', 'status', 'email', 'phone', 'company')
    list_filter = ('status', 'employment_type', 'dept', 'company')
    search_fields = ('emp_code', 'name', 'email', 'phone', 'position')
    ordering = ('emp_code',)
    date_hierarchy = 'hire_date'


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('payroll_number', 'employee', 'pay_year', 'pay_month', 'gross_pay', 'total_deduction', 'net_pay', 'state', 'payment_date', 'company')
    list_filter = ('state', 'pay_year', 'pay_month', 'company')
    search_fields = ('payroll_number', 'employee__name', 'employee__emp_code')
    ordering = ('-pay_year', '-pay_month', 'employee__emp_code')
