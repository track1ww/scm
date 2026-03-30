from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Company, User, UserPermission


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_code', 'company_name', 'business_no', 'plan', 'is_active', 'created_at')
    list_filter = ('plan', 'is_active')
    search_fields = ('company_code', 'company_name', 'business_no')
    ordering = ('company_code',)


class UserPermissionInline(admin.TabularInline):
    model = UserPermission
    extra = 0
    fields = ('module', 'can_read', 'can_write')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'company', 'department', 'is_admin', 'is_active', 'is_staff')
    list_filter = ('is_admin', 'is_active', 'is_staff', 'company')
    search_fields = ('email', 'name', 'username', 'department')
    ordering = ('email',)
    inlines = [UserPermissionInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ('SCM 정보', {'fields': ('name', 'department', 'is_admin', 'company')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('SCM 정보', {'fields': ('email', 'name', 'department', 'is_admin', 'company')}),
    )


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'module', 'can_read', 'can_write')
    list_filter = ('module', 'can_read', 'can_write')
    search_fields = ('user__email', 'user__name', 'module')
