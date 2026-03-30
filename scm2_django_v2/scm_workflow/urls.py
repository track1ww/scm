from rest_framework.routers import DefaultRouter
from .views import ApprovalTemplateViewSet, ApprovalRequestViewSet

router = DefaultRouter()
router.register(r'templates', ApprovalTemplateViewSet, basename='approval-template')
router.register(r'requests',  ApprovalRequestViewSet,  basename='approval-request')

urlpatterns = router.urls
