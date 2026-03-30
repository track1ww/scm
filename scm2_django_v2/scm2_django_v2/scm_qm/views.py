from django.db.models import Count, Q, Avg
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import InspectionPlan, InspectionResult, DefectReport
from .serializers import (
    InspectionPlanSerializer, InspectionResultSerializer, DefectReportSerializer,
)


class InspectionPlanViewSet(viewsets.ModelViewSet):
    serializer_class = InspectionPlanSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['material__material_code', 'material__material_name', 'sampling_method']
    filterset_fields = ['inspection_type', 'is_active']
    ordering_fields  = ['inspection_type', 'material']

    def get_queryset(self):
        return InspectionPlan.objects.filter(
            company=self.request.user.company
        ).select_related('material').order_by('inspection_type', 'material')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class InspectionResultViewSet(viewsets.ModelViewSet):
    serializer_class = InspectionResultSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['reference_number', 'plan__material__material_name']
    filterset_fields = ['status', 'reference_type', 'inspection_date']
    ordering_fields  = ['inspection_date', 'status']

    def get_queryset(self):
        return InspectionResult.objects.filter(
            company=self.request.user.company
        ).select_related('plan__material', 'inspector').prefetch_related('defect_reports').order_by('-inspection_date')

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            inspector=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """검사결과를 합격 처리합니다."""
        result = self.get_object()
        if result.status not in ('PENDING', 'CONDITIONAL'):
            return Response(
                {'detail': f'합격 처리할 수 없는 상태입니다. 현재 상태: {result.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result.status = 'PASSED'
        result.save(update_fields=['status'])
        return Response(InspectionResultSerializer(result).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """검사결과를 불합격 처리합니다. remarks 를 body 에서 받습니다."""
        result = self.get_object()
        if result.status not in ('PENDING', 'CONDITIONAL'):
            return Response(
                {'detail': f'불합격 처리할 수 없는 상태입니다. 현재 상태: {result.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        remarks = request.data.get('remarks', '')
        if remarks:
            result.remarks = remarks
        result.status = 'FAILED'
        result.save(update_fields=['status', 'remarks'])
        return Response(InspectionResultSerializer(result).data)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """검사결과 현황 대시보드 데이터를 반환합니다."""
        qs = self.get_queryset()

        status_summary = (
            qs.values('status')
            .annotate(count=Count('id'))
        )
        status_map = {item['status']: item['count'] for item in status_summary}

        type_summary = (
            qs.values('reference_type')
            .annotate(count=Count('id'))
        )
        type_map = {item['reference_type']: item['count'] for item in type_summary}

        # 불합격 건수 기준 상위 결함 유형
        top_defects = (
            DefectReport.objects.filter(inspection__company=request.user.company)
            .values('defect_type')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        defect_total   = DefectReport.objects.filter(inspection__company=request.user.company).count()
        open_defects   = DefectReport.objects.filter(
            inspection__company=request.user.company,
            status__in=['OPEN', 'IN_PROGRESS'],
        ).count()

        total = qs.count()
        passed = status_map.get('PASSED', 0)
        overall_pass_rate = round(passed / total * 100, 1) if total > 0 else None

        return Response({
            'total':             total,
            'pending':           status_map.get('PENDING', 0),
            'passed':            passed,
            'failed':            status_map.get('FAILED', 0),
            'conditional':       status_map.get('CONDITIONAL', 0),
            'overall_pass_rate': overall_pass_rate,
            'by_reference_type': type_map,
            'defect_total':      defect_total,
            'open_defects':      open_defects,
            'top_defects':       list(top_defects),
        })


class DefectReportViewSet(viewsets.ModelViewSet):
    serializer_class = DefectReportSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['defect_type', 'description']
    filterset_fields = ['severity', 'status']
    ordering_fields  = ['created_at', 'severity']

    def get_queryset(self):
        return DefectReport.objects.filter(
            company=self.request.user.company
        ).select_related('inspection').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """결함보고를 완료(CLOSED) 처리합니다. corrective_action 을 body 에서 받습니다."""
        report = self.get_object()
        if report.status == 'CLOSED':
            return Response(
                {'detail': '이미 완료된 결함보고입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        corrective_action = request.data.get('corrective_action', '')
        if corrective_action:
            report.corrective_action = corrective_action
        report.status = 'CLOSED'
        report.save(update_fields=['status', 'corrective_action'])
        return Response(DefectReportSerializer(report).data)
