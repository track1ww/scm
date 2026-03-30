from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter, DateFromToRangeFilter
import django_filters

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogFilter(FilterSet):
    """감사 로그 세부 필터"""
    module = CharFilter(field_name='module', lookup_expr='icontains')
    model_name = CharFilter(field_name='model_name', lookup_expr='icontains')
    object_repr = CharFilter(field_name='object_repr', lookup_expr='icontains')
    user = django_filters.NumberFilter(field_name='user__id')
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = AuditLog
        fields = ['company', 'action', 'module', 'model_name', 'user', 'date_from', 'date_to']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    감사 로그 — 읽기 전용

    list     GET /api/core/audit-logs/
    retrieve GET /api/core/audit-logs/{id}/

    필터 파라미터:
      ?module=mm
      ?model_name=PurchaseOrder
      ?action=CREATE
      ?user=42
      ?date_from=2025-01-01&date_to=2025-12-31
      ?object_repr=PO-2025
    """
    queryset = AuditLog.objects.select_related('company', 'user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AuditLogFilter
    search_fields = ['module', 'model_name', 'object_repr', 'user__name', 'user__email']
    ordering_fields = ['created_at', 'module', 'action']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        # 슈퍼유저는 전체, 관리자는 자사, 일반 사용자는 자신이 생성한 로그만
        if user.is_superuser:
            return AuditLog.objects.select_related('company', 'user').all()
        if user.is_admin and user.company:
            return AuditLog.objects.select_related('company', 'user').filter(
                company=user.company
            )
        if user.company:
            return AuditLog.objects.select_related('company', 'user').filter(
                company=user.company, user=user
            )
        return AuditLog.objects.none()
