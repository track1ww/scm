from rest_framework import serializers
from .models import Department, Employee, Payroll, Attendance, Leave, LeaveBalance


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model  = Department
        fields = '__all__'
        read_only_fields = ['company']


class EmployeeSerializer(serializers.ModelSerializer):
    dept_name            = serializers.CharField(source='dept.dept_name', read_only=True)
    employment_type_display = serializers.CharField(
        source='get_employment_type_display', read_only=True
    )
    status_display       = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Employee
        fields = '__all__'
        read_only_fields = ['company']


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    emp_code      = serializers.CharField(source='employee.emp_code', read_only=True)

    class Meta:
        model  = Payroll
        fields = '__all__'
        read_only_fields = ['company']


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    emp_code      = serializers.CharField(source='employee.emp_code', read_only=True)
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)

    class Meta:
        model  = Attendance
        fields = '__all__'
        read_only_fields = ['company']


class LeaveSerializer(serializers.ModelSerializer):
    employee_name    = serializers.CharField(source='employee.name', read_only=True)
    emp_code         = serializers.CharField(source='employee.emp_code', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Leave
        fields = '__all__'
        read_only_fields = ['company']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model  = LeaveBalance
        fields = '__all__'
        read_only_fields = ['company']
