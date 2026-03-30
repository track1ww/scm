from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserPermission

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id','email','name','department','is_admin','company']
        read_only_fields = ['email','is_admin']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ['email','name','password','department']

    def create(self, validated_data):
        return User.objects.create_user(
            username   = validated_data['email'],
            email      = validated_data['email'],
            name       = validated_data['name'],
            password   = validated_data['password'],
            department = validated_data.get('department',''),
        )

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserPermission
        fields = '__all__'
