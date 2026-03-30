from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'action', 'module', 'model_name', 'object_id',
        'object_repr', 'user', 'ip_address', 'created_at'
    ]
    list_filter = ['action', 'module', 'company']
    search_fields = [
        'module', 'model_name', 'object_repr',
        'user__name', 'user__email', 'ip_address'
    ]
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()]
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
