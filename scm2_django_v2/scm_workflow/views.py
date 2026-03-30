from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import ApprovalTemplate, ApprovalRequest, ApprovalAction
from .serializers import (
    ApprovalTemplateSerializer,
    ApprovalRequestSerializer,
    ApprovalRequestCreateSerializer,
    ApprovalActionInputSerializer,
)


class ApprovalTemplateViewSet(viewsets.ModelViewSet):
    """
    결재 템플릿 CRUD

    list   GET  /api/workflow/templates/
    create POST /api/workflow/templates/
    """
    queryset = ApprovalTemplate.objects.prefetch_related('steps').all()
    serializer_class = ApprovalTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['company', 'module', 'doc_type', 'is_active']
    search_fields = ['name', 'module', 'doc_type']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return ApprovalTemplate.objects.prefetch_related('steps').all()
        if user.company:
            return ApprovalTemplate.objects.prefetch_related('steps').filter(
                company=user.company
            )
        return ApprovalTemplate.objects.none()


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    """
    결재 요청 관리

    list     GET  /api/workflow/requests/
    retrieve GET  /api/workflow/requests/{id}/
    create   POST /api/workflow/requests/
    approve  POST /api/workflow/requests/{id}/approve/
    reject   POST /api/workflow/requests/{id}/reject/
    cancel   POST /api/workflow/requests/{id}/cancel/
    pending  GET  /api/workflow/requests/pending/   — 내가 결재해야 할 건
    my       GET  /api/workflow/requests/my/        — 내가 요청한 건
    """
    queryset = ApprovalRequest.objects.select_related(
        'company', 'template', 'requester', 'content_type'
    ).prefetch_related('actions__approver', 'actions__step').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['company', 'status', 'template']
    ordering_fields = ['created_at', 'completed_at', 'current_step']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ApprovalRequestCreateSerializer
        return ApprovalRequestSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalRequest.objects.select_related(
            'company', 'template', 'requester', 'content_type'
        ).prefetch_related('actions__approver', 'actions__step')

        if user.is_admin or user.is_superuser:
            return qs.all()
        if user.company:
            return qs.filter(company=user.company)
        return qs.none()

    # ------------------------------------------------------------------
    # 커스텀 액션
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'], url_path='my')
    def my_requests(self, request):
        """내가 요청한 결재 목록"""
        qs = self.get_queryset().filter(requester=request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = ApprovalRequestSerializer(
            qs, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_for_me(self, request):
        """내가 결재해야 할 대기 건 (approver_role 이 user.department 와 일치하는 단계)"""
        qs = self.get_queryset().filter(status='pending')
        # 간단한 필터: 현재 단계의 approver_role 이 요청자의 부서와 일치
        my_dept = request.user.department
        result = []
        for req in qs:
            if req.template:
                step = req.template.steps.filter(step_no=req.current_step).first()
                if step and (
                    step.approver_role == my_dept or step.approver_role == ''
                ):
                    result.append(req)
        serializer = ApprovalRequestSerializer(
            result, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """결재 승인"""
        approval_request = self.get_object()

        if approval_request.status != 'pending':
            return Response(
                {'detail': f'현재 상태({approval_request.get_status_display()})에서는 승인할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        input_ser = ApprovalActionInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        comment = input_ser.validated_data['comment']

        current_step = None
        if approval_request.template:
            current_step = approval_request.template.steps.filter(
                step_no=approval_request.current_step
            ).first()

        # 결재 행위 기록
        ApprovalAction.objects.create(
            request=approval_request,
            step=current_step,
            approver=request.user,
            action='approved',
            comment=comment,
        )

        # 다음 단계 진행 또는 최종 승인
        total_steps = (
            approval_request.template.steps.count()
            if approval_request.template else 0
        )
        if approval_request.current_step >= total_steps:
            approval_request.status = 'approved'
            approval_request.completed_at = timezone.now()
        else:
            approval_request.current_step += 1

        approval_request.save(update_fields=['status', 'current_step', 'completed_at'])

        serializer = ApprovalRequestSerializer(
            approval_request, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """결재 반려"""
        approval_request = self.get_object()

        if approval_request.status != 'pending':
            return Response(
                {'detail': f'현재 상태({approval_request.get_status_display()})에서는 반려할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        input_ser = ApprovalActionInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        comment = input_ser.validated_data['comment']

        current_step = None
        if approval_request.template:
            current_step = approval_request.template.steps.filter(
                step_no=approval_request.current_step
            ).first()

        ApprovalAction.objects.create(
            request=approval_request,
            step=current_step,
            approver=request.user,
            action='rejected',
            comment=comment,
        )

        approval_request.status = 'rejected'
        approval_request.completed_at = timezone.now()
        approval_request.save(update_fields=['status', 'completed_at'])

        serializer = ApprovalRequestSerializer(
            approval_request, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """결재 요청 취소 (요청자 본인만 가능)"""
        approval_request = self.get_object()

        if approval_request.requester != request.user and not request.user.is_admin:
            return Response(
                {'detail': '본인이 요청한 결재만 취소할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if approval_request.status not in ('pending',):
            return Response(
                {'detail': f'현재 상태({approval_request.get_status_display()})에서는 취소할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approval_request.status = 'cancelled'
        approval_request.completed_at = timezone.now()
        approval_request.save(update_fields=['status', 'completed_at'])

        serializer = ApprovalRequestSerializer(
            approval_request, context={'request': request}
        )
        return Response(serializer.data)
