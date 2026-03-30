from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserPermission, Role, UserRole, ROLE_PRESETS

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

class RoleSerializer(serializers.ModelSerializer):
    code_display = serializers.SerializerMethodField()

    class Meta:
        model  = Role
        fields = ['id', 'company', 'code', 'code_display', 'name', 'description', 'created_at']
        read_only_fields = ['company', 'created_at']

    def get_code_display(self, obj):
        return ROLE_PRESETS.get(obj.code, obj.code)

class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model  = UserRole
        fields = ['id', 'user', 'user_name', 'role', 'role_name', 'assigned_at', 'assigned_by']
        read_only_fields = ['assigned_at', 'assigned_by']
