from rest_framework import serializers
from .models import Department, Employee, Payroll


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Department
        fields = '__all__'


class EmployeeSerializer(serializers.ModelSerializer):
    dept_name = serializers.CharField(source='dept.dept_name', read_only=True)

    class Meta:
        model  = Employee
        fields = '__all__'


class PayrollSerializer(serializers.ModelSerializer):
    employee_name  = serializers.CharField(source='employee.name', read_only=True)
    emp_code       = serializers.CharField(source='employee.emp_code', read_only=True)
    payroll_number = serializers.CharField(required=False, allow_blank=True)
    gross_pay      = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    total_deduction = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    net_pay        = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)

    class Meta:
        model  = Payroll
        fields = '__all__'
        read_only_fields = ['company']
