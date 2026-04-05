from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ChatRoom, ChatMessage, ChatMember, ChatNotice
from .serializers import (ChatRoomSerializer, ChatMessageSerializer,
                           ChatNoticeSerializer)

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        return ChatRoom.objects.filter(
            members=self.request.user
        ).prefetch_related('chatmember_set__user').order_by('-id')

    def perform_create(self, serializer):
        room = serializer.save(created_by=self.request.user,
                               company=self.request.user.company)
        ChatMember.objects.create(room=room, user=self.request.user)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        ChatMember.objects.get_or_create(room=room, user=request.user)
        return Response({'status': 'joined'})

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """읽음 처리"""
        ChatMember.objects.filter(
            room_id=pk, user=request.user
        ).update(last_read_at=timezone.now())
        return Response({'status': 'ok'})

    def destroy(self, request, *args, **kwargs):
        """채팅방 삭제 — 방 개설자 또는 관리자만 가능. 메시지·멤버 모두 삭제."""
        room = self.get_object()
        if room.created_by != request.user and not request.user.is_admin:
            return Response(
                {'detail': '채팅방을 삭제할 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """채팅방 나가기 — 본인을 멤버에서 제거. 남은 멤버 없으면 방 자동 삭제."""
        room = self.get_object()
        deleted, _ = ChatMember.objects.filter(room=room, user=request.user).delete()
        if deleted == 0:
            return Response(
                {'detail': '이미 채팅방에 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ChatMember.objects.filter(room=room).exists():
            room.delete()
            return Response({'status': 'room_deleted'})
        return Response({'status': 'left'})

    @action(detail=False, methods=['post'])
    def create_dm(self, request):
        """1:1 채팅방 생성 또는 기존 방 반환"""
        target_id = request.data.get('target_user_id')
        uid1, uid2 = sorted([request.user.id, int(target_id)])
        room_key   = f'dm_{uid1}_{uid2}'

        room, created = ChatRoom.objects.get_or_create(
            room_key=room_key,
            defaults={
                'room_type': 'dm',
                'room_name': f'DM {uid1}-{uid2}',
                'created_by': request.user,
                'company': request.user.company,
            }
        )
        if created:
            from scm_accounts.models import User
            for uid in [request.user.id, target_id]:
                ChatMember.objects.get_or_create(room=room, user_id=uid)
        return Response(ChatRoomSerializer(room, context={'request':request}).data)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        room_id = self.request.query_params.get('room_id')
        qs = ChatMessage.objects.filter(is_deleted=False).select_related('sender')
        if room_id:
            qs = qs.filter(room_id=room_id)
        return qs.order_by('-created_at')[:100]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user,
                        sender_name=self.request.user.name)

    @action(detail=True, methods=['delete'])
    def soft_delete(self, request, pk=None):
        msg = self.get_object()
        if msg.sender != request.user and not request.user.is_admin:
            return Response(status=status.HTTP_403_FORBIDDEN)
        msg.is_deleted = True
        msg.save()
        return Response({'status': 'deleted'})


class ChatNoticeViewSet(viewsets.ModelViewSet):
    serializer_class = ChatNoticeSerializer

    def get_queryset(self):
        return ChatNotice.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user,
                        author_name=self.request.user.name,
                        company=self.request.user.company)
