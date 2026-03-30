from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'company', 'recipient',
            'notification_type', 'notification_type_display',
            'title', 'message',
            'is_read', 'read_at',
            'ref_module', 'ref_id',
            'created_at',
        ]
        read_only_fields = ['id', 'is_read', 'read_at', 'created_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """내부 서비스에서 알림 생성 시 사용"""

    class Meta:
        model = Notification
        fields = [
            'company', 'recipient', 'notification_type',
            'title', 'message', 'ref_module', 'ref_id',
        ]

    def validate_notification_type(self, value):
        valid_types = [t[0] for t in Notification.TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f'유효하지 않은 알림 유형입니다. 허용값: {valid_types}'
            )
        return value


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
