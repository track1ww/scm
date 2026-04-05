from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status as http_status
from .models import WorkInstruction, WorkResult, WorkStandard
from .serializers import WorkInstructionSerializer, WorkResultSerializer, WorkStandardSerializer
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


class WorkStandardViewSet(viewsets.ModelViewSet):
    """
    작업표준서 버전 관리

    list     GET  /api/wi/standards/
    create   POST /api/wi/standards/
    promote  POST /api/wi/standards/{id}/promote/   — draft → active (기존 active → deprecated)
    deprecate POST /api/wi/standards/{id}/deprecate/ — active → deprecated
    new_version POST /api/wi/standards/{id}/new_version/ — 현재 버전 기반 새 버전 생성
    """
    serializer_class = WorkStandardSerializer
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['standard_code', 'work_center', 'status']
    search_fields    = ['standard_code', 'title', 'work_center']
    ordering_fields  = ['standard_code', 'version', 'created_at']

    def get_queryset(self):
        return WorkStandard.objects.filter(
            company=self.request.user.company
        ).order_by('standard_code', '-version')

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            created_by=self.request.user.name or self.request.user.username,
        )

    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        """draft → active. 동일 standard_code의 기존 active 버전은 deprecated 처리."""
        ws = self.get_object()
        if ws.status == 'active':
            return Response({'detail': '이미 활성 상태입니다.'}, status=http_status.HTTP_400_BAD_REQUEST)
        if ws.status == 'deprecated':
            return Response({'detail': '폐기된 표준은 재활성화할 수 없습니다.'}, status=http_status.HTTP_400_BAD_REQUEST)

        # 동일 code의 기존 active → deprecated
        WorkStandard.objects.filter(
            company=ws.company,
            standard_code=ws.standard_code,
            status='active',
        ).update(status='deprecated')

        ws.status = 'active'
        ws.save(update_fields=['status', 'updated_at'])
        return Response(WorkStandardSerializer(ws).data)

    @action(detail=True, methods=['post'])
    def deprecate(self, request, pk=None):
        """active/draft → deprecated."""
        ws = self.get_object()
        if ws.status == 'deprecated':
            return Response({'detail': '이미 폐기 상태입니다.'}, status=http_status.HTTP_400_BAD_REQUEST)

        ws.status = 'deprecated'
        ws.save(update_fields=['status', 'updated_at'])
        return Response(WorkStandardSerializer(ws).data)

    @action(detail=True, methods=['post'], url_path='new-version')
    def new_version(self, request, pk=None):
        """현재 버전 기반으로 마이너 버전 +0.1 의 새 draft 생성."""
        ws = self.get_object()
        try:
            major, minor = ws.version.split('.')
            new_ver = f"{major}.{int(minor) + 1}"
        except (ValueError, AttributeError):
            new_ver = f"{ws.version}.1"

        if WorkStandard.objects.filter(
            company=ws.company, standard_code=ws.standard_code, version=new_ver
        ).exists():
            return Response(
                {'detail': f'버전 {new_ver} 이 이미 존재합니다.'},
                status=http_status.HTTP_409_CONFLICT,
            )

        new_ws = WorkStandard.objects.create(
            company=ws.company,
            standard_code=ws.standard_code,
            work_center=ws.work_center,
            title=ws.title,
            content=ws.content,
            version=new_ver,
            status='draft',
            created_by=request.user.name or request.user.username,
        )
        return Response(WorkStandardSerializer(new_ws).data, status=http_status.HTTP_201_CREATED)
