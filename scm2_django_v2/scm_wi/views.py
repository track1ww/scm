from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import WorkInstruction, WorkResult
from .serializers import WorkInstructionSerializer, WorkResultSerializer
from scm_core.mixins import StateLockMixin


class WorkInstructionViewSet(StateLockMixin, viewsets.ModelViewSet):
    locked_states = ['완료']
    serializer_class = WorkInstructionSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['wi_number', 'title', 'assigned_to']
    filterset_fields = ['status', 'priority', 'work_center']
    ordering_fields  = ['planned_start', 'created_at', 'priority']

    def get_queryset(self):
        return WorkInstruction.objects.filter(
            company=self.request.user.company
        ).prefetch_related('results').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':       qs.count(),
            'in_progress': qs.filter(status='진행중').count(),
            'completed':   qs.filter(status='완료').count(),
            'on_hold':     qs.filter(status='보류').count(),
            'waiting':     qs.filter(status='대기').count(),
        })


class WorkResultViewSet(viewsets.ModelViewSet):
    serializer_class = WorkResultSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    search_fields    = ['worker_name']
    filterset_fields = ['work_instruction', 'result_date']

    def get_queryset(self):
        return WorkResult.objects.filter(
            work_instruction__company=self.request.user.company
        ).select_related('work_instruction').order_by('-result_date')
