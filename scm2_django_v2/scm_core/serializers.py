from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'company',
            'user', 'user_name', 'user_email',
            'action', 'action_display',
            'module', 'model_name',
            'object_id', 'object_repr',
            'changes',
            'ip_address', 'user_agent',
            'created_at',
        ]
        read_only_fields = fields  # 감사 로그는 읽기 전용

    def get_user_name(self, obj):
        return obj.user.name if obj.user else '시스템'

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None


class AuditLogCreateSerializer(serializers.ModelSerializer):
    """내부 서비스용 감사 로그 기록 시리얼라이저 (직접 호출 또는 미들웨어에서 사용)"""

    class Meta:
        model = AuditLog
        fields = [
            'company', 'user', 'action', 'module', 'model_name',
            'object_id', 'object_repr', 'changes', 'ip_address', 'user_agent',
        ]

    def validate_action(self, value):
        valid = [c[0] for c in AuditLog.ACTION_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f'유효하지 않은 작업 유형입니다. 허용값: {valid}'
            )
        return value
