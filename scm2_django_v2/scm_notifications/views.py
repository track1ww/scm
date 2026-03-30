from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    UnreadCountSerializer,
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    알림 관리

    list         GET  /api/notifications/         — 내 알림 목록 (최신순)
    retrieve     GET  /api/notifications/{id}/
    create       POST /api/notifications/         — 알림 생성 (관리자/시스템)
    mark_read    POST /api/notifications/{id}/read/
    mark_all_read POST /api/notifications/read_all/
    unread_count GET  /api/notifications/unread_count/
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'is_read', 'ref_module']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer

    def perform_create(self, serializer):
        notif = serializer.save()
        # Push to recipient's WebSocket
        from .push import push_notification
        from .serializers import NotificationSerializer
        push_notification(
            notif.recipient_id,
            NotificationSerializer(notif).data
        )

    def get_queryset(self):
        user = self.request.user
        # 관리자는 회사 전체 알림 조회 가능
        if user.is_admin or user.is_superuser:
            if user.company:
                return Notification.objects.filter(company=user.company)
            return Notification.objects.all()
        # 일반 사용자는 자신의 알림만
        return Notification.objects.filter(recipient=user)

    def list(self, request, *args, **kwargs):
        """알림 목록 + 미읽음 건수를 함께 반환"""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = NotificationSerializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['unread_count'] = self.get_queryset().filter(
                is_read=False
            ).count()
            return response

        serializer = NotificationSerializer(qs, many=True)
        unread_count = self.get_queryset().filter(is_read=False).count()
        return Response({'results': serializer.data, 'unread_count': unread_count})

    # ------------------------------------------------------------------
    # 커스텀 액션
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        """단건 알림 읽음 처리"""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='read_all')
    def mark_all_read(self, request):
        """내 미읽음 알림 전체 읽음 처리"""
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=now)
        return Response(
            {'detail': f'{updated}건의 알림을 읽음 처리했습니다.'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='unread_count')
    def unread_count(self, request):
        """미읽음 알림 건수"""
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        serializer = UnreadCountSerializer({'unread_count': count})
        return Response(serializer.data)
