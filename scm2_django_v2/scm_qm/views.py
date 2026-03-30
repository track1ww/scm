from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import InspectionPlan, InspectionResult, DefectRecord, CorrectiveAction
from .serializers import (InspectionPlanSerializer, InspectionResultSerializer,
                           DefectRecordSerializer, CorrectiveActionSerializer)
from .utils import calc_process_capability, calc_control_limits, classify_spc_points


class InspectionPlanViewSet(viewsets.ModelViewSet):
    serializer_class = InspectionPlanSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['plan_code', 'plan_name', 'target_item']
    filterset_fields = ['inspection_type', 'is_active']

    def get_queryset(self):
        return InspectionPlan.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class InspectionResultViewSet(viewsets.ModelViewSet):
    serializer_class = InspectionResultSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['result_number', 'item_name', 'lot_number']
    filterset_fields = ['result']
    ordering_fields  = ['inspected_at', 'created_at']

    def get_queryset(self):
        return InspectionResult.objects.filter(
            company=self.request.user.company
        ).select_related('plan').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':       qs.count(),
            'passed':      qs.filter(result='합격').count(),
            'failed':      qs.filter(result='불합격').count(),
            'conditional': qs.filter(result='조건부합격').count(),
        })

    @action(detail=False, methods=['post'], url_path='spc_analysis')
    def spc_analysis(self, request):
        """
        SPC 분석 — 공정능력 지수 및 관리도 한계선 계산.

        Body:
            values         (list[float]) : 측정값
            usl            (float|null)  : 규격 상한
            lsl            (float|null)  : 규격 하한
            target         (float|null)  : 목표값
            subgroup_size  (int, 기본 1): 부분군 크기
        """
        data          = request.data
        values        = data.get('values', [])
        usl           = data.get('usl')
        lsl           = data.get('lsl')
        target        = data.get('target')
        subgroup_size = int(data.get('subgroup_size', 1))

        if not values:
            return Response({'error': '측정값(values)이 필요합니다.'}, status=400)

        capability = calc_process_capability(values, usl, lsl, target)
        control    = calc_control_limits(values, subgroup_size)

        alerts = []
        if 'ucl_x' in control and 'lcl_x' in control:
            alerts = classify_spc_points(
                values,
                ucl=control['ucl_x'],
                lcl=control['lcl_x'],
                center=control.get('x_bar', 0),
            )

        return Response({
            'capability':     capability,
            'control_limits': control,
            'alerts':         alerts,
        })


class DefectRecordViewSet(viewsets.ModelViewSet):
    serializer_class = DefectRecordSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['defect_number', 'item_name', 'defect_type']
    filterset_fields = ['severity']

    def get_queryset(self):
        return DefectRecord.objects.filter(
            company=self.request.user.company
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class CorrectiveActionViewSet(viewsets.ModelViewSet):
    serializer_class = CorrectiveActionSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['capa_number', 'title']
    filterset_fields = ['status']

    def get_queryset(self):
        return CorrectiveAction.objects.filter(
            company=self.request.user.company
        ).select_related('defect').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
