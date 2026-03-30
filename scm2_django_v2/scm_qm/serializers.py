from rest_framework import serializers
from .models import InspectionPlan, InspectionResult, DefectRecord, CorrectiveAction


class InspectionPlanSerializer(serializers.ModelSerializer):
    inspection_type_display = serializers.CharField(
        source='get_inspection_type_display', read_only=True
    )

    class Meta:
        model  = InspectionPlan
        fields = '__all__'
        read_only_fields = ['company']


class InspectionResultSerializer(serializers.ModelSerializer):
    plan_name    = serializers.CharField(source='plan.plan_name', read_only=True)
    pass_rate    = serializers.FloatField(read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)

    class Meta:
        model  = InspectionResult
        fields = '__all__'
        read_only_fields = ['company']


class DefectRecordSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model  = DefectRecord
        fields = '__all__'
        read_only_fields = ['company']


class CorrectiveActionSerializer(serializers.ModelSerializer):
    defect_number  = serializers.CharField(source='defect.defect_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = CorrectiveAction
        fields = '__all__'
        read_only_fields = ['company']
