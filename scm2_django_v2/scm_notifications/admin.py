from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'recipient', 'notification_type', 'title', 'is_read', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'company']
    search_fields = ['recipient__name', 'recipient__email', 'title']
    readonly_fields = ['created_at', 'read_at']
    ordering = ['-created_at']
