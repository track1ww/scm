from rest_framework import serializers
from .models import ExternalAPIConfig


class ExternalAPIConfigSerializer(serializers.ModelSerializer):
    feature_type_display = serializers.CharField(source='get_feature_type_display', read_only=True)
    provider_display     = serializers.CharField(source='get_provider_display', read_only=True)
    masked_key           = serializers.SerializerMethodField()

    def get_masked_key(self, obj):
        return obj.masked_key()

    class Meta:
        model  = ExternalAPIConfig
        fields = '__all__'
        extra_kwargs = {
            'api_key':    {'write_only': False},  # returned but masked via masked_key
            'api_secret': {'write_only': True},
            'company':    {'read_only': True},
        }
