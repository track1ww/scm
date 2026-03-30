from rest_framework import serializers
from .models import InspectionPlan, InspectionResult, DefectReport


class InspectionPlanSerializer(serializers.ModelSerializer):
    inspection_type_display = serializers.CharField(source='get_inspection_type_display', read_only=True)
    material_name           = serializers.CharField(source='material.material_name', read_only=True)
    material_code           = serializers.CharField(source='material.material_code', read_only=True)
    # Accept legacy fields from frontend
    plan_code   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    plan_name   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    target_item = serializers.CharField(write_only=True, required=False, allow_blank=True)

    INSPECTION_TYPE_MAP = {
        '수입검사': 'INCOMING', '공정검사': 'PROCESS',
        '최종검사': 'FINAL', '정기검사': 'PERIODIC',
    }

    def to_internal_value(self, data):
        data = data.copy()
        if 'inspection_type' in data and data['inspection_type'] in self.INSPECTION_TYPE_MAP:
            data['inspection_type'] = self.INSPECTION_TYPE_MAP[data['inspection_type']]
        # Map plan_name to sampling_method if sampling_method not provided
        if 'plan_name' in data and not data.get('sampling_method'):
            data['sampling_method'] = data.pop('plan_name')
        return super().to_internal_value(data)

    def create(self, validated_data):
        for f in ('plan_code', 'plan_name', 'target_item'):
            validated_data.pop(f, None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for f in ('plan_code', 'plan_name', 'target_item'):
            validated_data.pop(f, None)
        return super().update(instance, validated_data)

    class Meta:
        model  = InspectionPlan
        fields = '__all__'


class DefectReportSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = DefectReport
        fields = '__all__'


class InspectionResultSerializer(serializers.ModelSerializer):
    status_display         = serializers.CharField(source='get_status_display', read_only=True)
    reference_type_display = serializers.CharField(source='get_reference_type_display', read_only=True)
    inspector_name         = serializers.CharField(source='inspector.name', read_only=True)
    plan_type              = serializers.CharField(source='plan.get_inspection_type_display', read_only=True)
    pass_rate              = serializers.FloatField(read_only=True)
    defect_reports         = DefectReportSerializer(many=True, read_only=True)
    # Accept legacy fields from frontend
    item_name   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    lot_number  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    result      = serializers.CharField(write_only=True, required=False, allow_blank=True)

    RESULT_MAP = {'합격': 'PASSED', '불합격': 'FAILED', '조건부합격': 'CONDITIONAL', '검사중': 'PENDING'}

    def to_internal_value(self, data):
        data = data.copy()
        # Auto-set inspection_date to today if not provided
        if not data.get('inspection_date'):
            from django.utils import timezone
            data['inspection_date'] = str(timezone.now().date())
        # Auto-set reference_type if not provided
        if not data.get('reference_type'):
            data['reference_type'] = 'GR'
        # Map legacy result → status
        if 'result' in data and not data.get('status'):
            data['status'] = self.RESULT_MAP.get(data.get('result', ''), 'PENDING')
        # Map item_name → reference_number
        if 'item_name' in data and not data.get('reference_number'):
            data['reference_number'] = data.get('item_name', '')
        return super().to_internal_value(data)

    def create(self, validated_data):
        for f in ('item_name', 'lot_number', 'result'):
            validated_data.pop(f, None)
        return super().create(validated_data)

    class Meta:
        model  = InspectionResult
        fields = '__all__'
        extra_kwargs = {
            'inspection_date': {'required': False},
            'reference_type':  {'required': False},
        }
