from rest_framework import serializers
from .models import ChatRoom, ChatMessage, ChatMember, ChatNotice
from scm_accounts.models import User

class ChatMemberSerializer(serializers.ModelSerializer):
    user_name  = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model  = ChatMember
        fields = ['id','user','user_name','user_email','joined_at','last_read_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    is_mine = serializers.SerializerMethodField()

    def get_is_mine(self, obj):
        req = self.context.get('request')
        return req and obj.sender_id == req.user.id

    class Meta:
        model  = ChatMessage
        fields = ['id','room','sender','sender_name','msg_type',
                  'content','ref_type','ref_id','ref_label',
                  'is_deleted','created_at','is_mine']

class ChatRoomSerializer(serializers.ModelSerializer):
    members      = ChatMemberSerializer(source='chatmember_set', many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    def get_unread_count(self, obj):
        req = self.context.get('request')
        if not req: return 0
        member = obj.chatmember_set.filter(user=req.user).first()
        if not member: return 0
        qs = obj.messages.filter(is_deleted=False)
        if member.last_read_at:
            qs = qs.filter(created_at__gt=member.last_read_at)
        return qs.count()

    def get_last_message(self, obj):
        msg = obj.messages.filter(is_deleted=False).last()
        return {'content': msg.content, 'created_at': str(msg.created_at)[:16]} if msg else None

    class Meta:
        model  = ChatRoom
        fields = ['id','room_type','room_name','members','unread_count','last_message','created_at']

class ChatNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ChatNotice
        fields = '__all__'
