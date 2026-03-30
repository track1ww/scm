from rest_framework import serializers
from .models import WorkOrder, WorkOrderComment


class WorkOrderCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model  = WorkOrderComment
        fields = '__all__'
        read_only_fields = ['author', 'work_order']


class WorkOrderSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    department_name  = serializers.CharField(source='department.dept_name', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    comments         = WorkOrderCommentSerializer(many=True, read_only=True)
    order_number     = serializers.CharField(required=False, allow_blank=True)

    # Accept extra fields from legacy frontend (ignored by model)
    work_center  = serializers.CharField(required=False, allow_blank=True, write_only=True)
    planned_qty  = serializers.CharField(required=False, allow_blank=True, write_only=True)
    planned_start = serializers.CharField(required=False, allow_blank=True, write_only=True)
    planned_end   = serializers.CharField(required=False, allow_blank=True, write_only=True)

    # Map Korean status/priority from legacy frontend to English
    STATUS_MAP = {'대기': 'DRAFT', '진행중': 'IN_PROGRESS', '완료': 'COMPLETED', '취소': 'CANCELLED'}
    PRIORITY_MAP = {'낮음': 'LOW', '보통': 'MEDIUM', '높음': 'HIGH', '긴급': 'URGENT'}

    def to_internal_value(self, data):
        data = data.copy()
        if 'status' in data and data['status'] in self.STATUS_MAP:
            data['status'] = self.STATUS_MAP[data['status']]
        if 'priority' in data and data['priority'] in self.PRIORITY_MAP:
            data['priority'] = self.PRIORITY_MAP[data['priority']]
        return super().to_internal_value(data)

    def create(self, validated_data):
        # Remove legacy-only fields not in model
        for f in ('work_center', 'planned_qty', 'planned_start', 'planned_end'):
            validated_data.pop(f, None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for f in ('work_center', 'planned_qty', 'planned_start', 'planned_end'):
            validated_data.pop(f, None)
        return super().update(instance, validated_data)

    class Meta:
        model  = WorkOrder
        fields = '__all__'
        read_only_fields = ['company']
