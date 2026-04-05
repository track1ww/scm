from rest_framework import serializers
from .models import WorkInstruction, WorkResult, WorkStandard


class WorkResultSerializer(serializers.ModelSerializer):
    wi_number = serializers.CharField(source='work_instruction.wi_number', read_only=True)

    class Meta:
        model  = WorkResult
        fields = '__all__'


class WorkInstructionSerializer(serializers.ModelSerializer):
    results        = WorkResultSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = WorkInstruction
        fields = '__all__'
        read_only_fields = ['company']


class WorkStandardSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = WorkStandard
        fields = '__all__'
        read_only_fields = ['company', 'created_at', 'updated_at']
