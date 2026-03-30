import uuid
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import WorkOrder, WorkOrderComment
from .serializers import WorkOrderSerializer, WorkOrderCommentSerializer


class WorkOrderViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields    = ['order_number', 'title', 'description']
    filterset_fields = ['status', 'priority', 'department', 'assigned_to']
    ordering_fields  = ['created_at', 'due_date', 'priority']

    def get_queryset(self):
        return WorkOrder.objects.filter(
            company=self.request.user.company
        ).select_related(
            'assigned_to', 'department'
        ).prefetch_related('comments').order_by('-created_at')

    def perform_create(self, serializer):
        order_number = serializer.validated_data.get('order_number') or f'WO-{uuid.uuid4().hex[:8].upper()}'
        serializer.save(company=self.request.user.company, order_number=order_number)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """작업지시서 완료 처리: IN_PROGRESS → COMPLETED"""
        work_order = self.get_object()
        if work_order.status not in ('DRAFT', 'IN_PROGRESS'):
            return Response(
                {'detail': f'완료 처리할 수 없는 상태입니다. 현재 상태: {work_order.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        work_order.status       = 'COMPLETED'
        work_order.completed_at = timezone.now()
        work_order.save(update_fields=['status', 'completed_at'])
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """작업지시서 시작: DRAFT → IN_PROGRESS"""
        work_order = self.get_object()
        if work_order.status != 'DRAFT':
            return Response(
                {'detail': f'임시 상태인 경우에만 시작할 수 있습니다. 현재 상태: {work_order.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        work_order.status = 'IN_PROGRESS'
        work_order.save(update_fields=['status'])
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """작업지시서 취소: COMPLETED 제외 → CANCELLED"""
        work_order = self.get_object()
        if work_order.status == 'COMPLETED':
            return Response(
                {'detail': '완료된 작업지시서는 취소할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        work_order.status = 'CANCELLED'
        work_order.save(update_fields=['status'])
        return Response(WorkOrderSerializer(work_order).data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """댓글 조회 및 등록"""
        work_order = self.get_object()
        if request.method == 'GET':
            qs = work_order.comments.select_related('author').all()
            return Response(WorkOrderCommentSerializer(qs, many=True).data)

        serializer = WorkOrderCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(work_order=work_order, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """작업지시 현황 대시보드"""
        qs = self.get_queryset()
        return Response({
            'total':       qs.count(),
            'draft':       qs.filter(status='DRAFT').count(),
            'in_progress': qs.filter(status='IN_PROGRESS').count(),
            'completed':   qs.filter(status='COMPLETED').count(),
            'cancelled':   qs.filter(status='CANCELLED').count(),
            'urgent':      qs.filter(priority='URGENT').count(),
            'overdue':     qs.filter(
                status__in=['DRAFT', 'IN_PROGRESS'],
                due_date__lt=timezone.now().date()
            ).count(),
        })
