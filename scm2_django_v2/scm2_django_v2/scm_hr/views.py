import uuid
from decimal import Decimal
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum

from .models import Department, Employee, Payroll
from .serializers import DepartmentSerializer, EmployeeSerializer, PayrollSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['dept_code', 'dept_name']
    ordering_fields  = ['dept_name', 'dept_code']

    def get_queryset(self):
        return Department.objects.filter(
            company=self.request.user.company
        ).order_by('dept_name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['emp_code', 'name', 'email', 'phone']
    filterset_fields = ['status', 'employment_type', 'dept']
    ordering_fields  = ['name', 'hire_date', 'created_at']

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.request.user.company
        ).select_related('dept').order_by('name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def by_department(self, request):
        """부서별 직원 목록 필터링"""
        dept_id = request.query_params.get('dept_id')
        qs = self.get_queryset()
        if dept_id:
            qs = qs.filter(dept_id=dept_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class PayrollViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['payroll_number', 'employee__name', 'employee__emp_code']
    filterset_fields = ['state', 'pay_year', 'pay_month', 'employee']
    ordering_fields  = ['pay_year', 'pay_month', 'created_at']

    def get_queryset(self):
        return Payroll.objects.filter(
            company=self.request.user.company
        ).select_related('employee', 'employee__dept').order_by('-pay_year', '-pay_month')

    def perform_create(self, serializer):
        data = serializer.validated_data
        base_salary    = Decimal(str(data.get('base_salary',    0) or 0))
        overtime_pay   = Decimal(str(data.get('overtime_pay',   0) or 0))
        bonus          = Decimal(str(data.get('bonus',          0) or 0))
        income_tax     = Decimal(str(data.get('income_tax',     0) or 0))
        nat_pension    = Decimal(str(data.get('national_pension',    0) or 0))
        health_ins     = Decimal(str(data.get('health_insurance',    0) or 0))
        emp_ins        = Decimal(str(data.get('employment_insurance', 0) or 0))
        gross_pay      = base_salary + overtime_pay + bonus
        total_deduction = income_tax + nat_pension + health_ins + emp_ins
        net_pay        = Decimal(str(data.get('net_pay', None) or gross_pay - total_deduction))
        payroll_number = f'PAY-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(
            company=self.request.user.company,
            payroll_number=payroll_number,
            gross_pay=gross_pay,
            total_deduction=total_deduction,
            net_pay=net_pay,
        )

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """월별 급여 합계 요약"""
        year  = request.query_params.get('year')
        month = request.query_params.get('month')

        qs = self.get_queryset()
        if year:
            qs = qs.filter(pay_year=year)
        if month:
            qs = qs.filter(pay_month=month)

        aggregated = qs.aggregate(
            total_gross_pay=Sum('gross_pay'),
            total_net_pay=Sum('net_pay'),
            total_deduction=Sum('total_deduction'),
            total_national_pension=Sum('national_pension'),
            total_health_insurance=Sum('health_insurance'),
            total_employment_insurance=Sum('employment_insurance'),
            total_income_tax=Sum('income_tax'),
        )

        return Response({
            'year':                      year,
            'month':                     month,
            'headcount':                 qs.count(),
            'total_gross_pay':           aggregated['total_gross_pay'] or 0,
            'total_net_pay':             aggregated['total_net_pay'] or 0,
            'total_deduction':           aggregated['total_deduction'] or 0,
            'total_national_pension':    aggregated['total_national_pension'] or 0,
            'total_health_insurance':    aggregated['total_health_insurance'] or 0,
            'total_employment_insurance': aggregated['total_employment_insurance'] or 0,
            'total_income_tax':          aggregated['total_income_tax'] or 0,
        })
