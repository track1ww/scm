from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserPermission, Role, UserRole, ROLE_PRESETS

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'email', 'name', 'department', 'is_admin', 'company', 'company_name']
        read_only_fields = ['email', 'is_admin']

    def get_company_name(self, obj):
        return obj.company.company_name if obj.company else ''


class RegisterSerializer(serializers.ModelSerializer):
    password     = serializers.CharField(write_only=True, min_length=8)
    company_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = ['email', 'name', 'password', 'department', 'company_code']

    def create(self, validated_data):
        company_code = validated_data.pop('company_code', None)
        from .models import Company
        company = None
        if company_code:
            company = Company.objects.filter(company_code=company_code).first()
        user = User.objects.create_user(
            username   = validated_data['email'],
            email      = validated_data['email'],
            name       = validated_data['name'],
            password   = validated_data['password'],
            department = validated_data.get('department', ''),
            company    = company,
        )
        return user


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserPermission
        fields = ['id', 'user', 'module', 'can_read', 'can_write', 'can_delete']


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
