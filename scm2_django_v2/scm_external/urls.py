from rest_framework.routers import DefaultRouter
from .views import ExternalAPIConfigViewSet, RealTimeProxyViewSet

router = DefaultRouter()
router.register('configs',  ExternalAPIConfigViewSet, basename='external-config')
router.register('proxy',    RealTimeProxyViewSet,     basename='external-proxy')

urlpatterns = router.urls
