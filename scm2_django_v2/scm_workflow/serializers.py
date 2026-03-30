from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ApprovalTemplate, ApprovalStep, ApprovalRequest, ApprovalAction

User = get_user_model()


class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = ['id', 'step_no', 'step_name', 'approver_role']


class ApprovalTemplateSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalTemplate
        fields = [
            'id', 'company', 'name', 'module', 'doc_type', 'is_active', 'steps'
        ]
        read_only_fields = ['id']


class ApprovalActionSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    step_name = serializers.CharField(source='step.step_name', read_only=True)

    class Meta:
        model = ApprovalAction
        fields = [
            'id', 'step', 'step_name', 'approver', 'approver_name',
            'action', 'action_display', 'comment', 'acted_at'
        ]
        read_only_fields = ['id', 'acted_at']


class ApprovalRequestSerializer(serializers.ModelSerializer):
    actions = ApprovalActionSerializer(many=True, read_only=True)
    requester_name = serializers.CharField(source='requester.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    content_type_label = serializers.SerializerMethodField()
    total_steps = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = [
            'id', 'company', 'template', 'template_name',
            'requester', 'requester_name',
            'content_type', 'object_id', 'content_type_label',
            'current_step', 'total_steps',
            'status', 'status_display', 'title',
            'created_at', 'completed_at',
            'actions',
        ]
        read_only_fields = [
            'id', 'current_step', 'status', 'created_at', 'completed_at'
        ]

    def get_content_type_label(self, obj):
        if obj.content_type:
            return f"{obj.content_type.app_label}.{obj.content_type.model}"
        return None

    def get_total_steps(self, obj):
        if obj.template:
            return obj.template.steps.count()
        return None


class ApprovalRequestCreateSerializer(serializers.ModelSerializer):
    """결재 요청 생성 전용 시리얼라이저"""

    class Meta:
        model = ApprovalRequest
        fields = [
            'company', 'template', 'content_type', 'object_id', 'title'
        ]

    def validate(self, attrs):
        template = attrs.get('template')
        if template and not template.is_active:
            raise serializers.ValidationError(
                {'template': '비활성 상태의 결재 템플릿은 사용할 수 없습니다.'}
            )
        if template and not template.steps.exists():
            raise serializers.ValidationError(
                {'template': '결재 단계가 없는 템플릿은 사용할 수 없습니다.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data['requester'] = self.context['request'].user
        validated_data['status'] = 'pending'
        validated_data['current_step'] = 1
        return super().create(validated_data)


class ApprovalActionInputSerializer(serializers.Serializer):
    """승인/반려 액션 입력 전용"""
    comment = serializers.CharField(required=False, allow_blank=True, default='')
