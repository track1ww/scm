from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Department, Employee, Payroll, Attendance, Leave, LeaveBalance
from .serializers import (DepartmentSerializer, EmployeeSerializer, PayrollSerializer,
                           AttendanceSerializer, LeaveSerializer, LeaveBalanceSerializer)
from scm_core.mixins import AuditLogMixin, StateLockMixin


class DepartmentViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'hr'
    serializer_class = DepartmentSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['dept_code', 'dept_name']

    def get_queryset(self):
        return Department.objects.filter(
            company=self.request.user.company
        ).annotate(employee_count=Count('employee'))

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class EmployeeViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'hr'
    serializer_class = EmployeeSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['emp_code', 'name', 'email']
    filterset_fields = ['status', 'employment_type', 'dept']
    ordering_fields  = ['name', 'hire_date', 'created_at']

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.request.user.company
        ).select_related('dept').order_by('emp_code')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':    qs.count(),
            'active':   qs.filter(status='재직').count(),
            'on_leave': qs.filter(status='휴직').count(),
            'resigned': qs.filter(status='퇴직').count(),
        })


class PayrollViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    search_fields    = ['payroll_number', 'employee__name']
    filterset_fields = ['state', 'pay_year', 'pay_month']

    def get_queryset(self):
        return Payroll.objects.filter(
            company=self.request.user.company
        ).select_related('employee').order_by('-pay_year', '-pay_month')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        year  = request.query_params.get('year')
        month = request.query_params.get('month')
        qs = self.get_queryset()
        if year:
            qs = qs.filter(pay_year=year)
        if month:
            qs = qs.filter(pay_month=month)
        agg = qs.aggregate(
            total_gross=Sum('gross_pay'),
            total_deduction=Sum('total_deduction'),
            total_net=Sum('net_pay'),
        )
        return Response({
            'count':           qs.count(),
            'total_gross':     float(agg['total_gross'] or 0),
            'total_deduction': float(agg['total_deduction'] or 0),
            'total_net':       float(agg['total_net'] or 0),
        })


class AttendanceViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'hr'
    serializer_class = AttendanceSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['employee__name', 'employee__emp_code']
    filterset_fields = ['employee', 'work_type', 'work_date']
    ordering_fields  = ['work_date']

    def get_queryset(self):
        return Attendance.objects.filter(
            company=self.request.user.company
        ).select_related('employee').order_by('-work_date')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class LeaveViewSet(AuditLogMixin, StateLockMixin, viewsets.ModelViewSet):
    audit_module = 'hr'
    locked_states = ['approved', 'rejected']
    serializer_class = LeaveSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['employee__name', 'reason']
    filterset_fields = ['employee', 'leave_type', 'status']
    ordering_fields  = ['start_date', 'created_at']

    def get_queryset(self):
        return Leave.objects.filter(
            company=self.request.user.company
        ).select_related('employee').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave = self.get_object()
        if leave.status != 'pending':
            return Response({'detail': '대기 상태만 승인 가능합니다.'}, status=400)
        leave.status = 'approved'
        leave.save(update_fields=['status'])
        return Response(LeaveSerializer(leave).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if leave.status != 'pending':
            return Response({'detail': '대기 상태만 반려 가능합니다.'}, status=400)
        leave.status = 'rejected'
        leave.save(update_fields=['status'])
        return Response(LeaveSerializer(leave).data)
