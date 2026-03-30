from django.contrib import admin
from .models import ApprovalTemplate, ApprovalStep, ApprovalRequest, ApprovalAction


class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 1
    ordering = ['step_no']


@admin.register(ApprovalTemplate)
class ApprovalTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'module', 'doc_type', 'is_active']
    list_filter = ['company', 'module', 'is_active']
    search_fields = ['name', 'module', 'doc_type']
    inlines = [ApprovalStepInline]


class ApprovalActionInline(admin.TabularInline):
    model = ApprovalAction
    extra = 0
    readonly_fields = ['acted_at']


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'company', 'status', 'current_step', 'created_at']
    list_filter = ['company', 'status']
    search_fields = ['requester__name', 'requester__email']
    readonly_fields = ['created_at', 'completed_at']
    inlines = [ApprovalActionInline]


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ['request', 'step', 'approver', 'action', 'acted_at']
    list_filter = ['action']
    readonly_fields = ['acted_at']
