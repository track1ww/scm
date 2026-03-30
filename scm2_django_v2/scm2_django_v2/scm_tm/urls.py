from rest_framework.routers import DefaultRouter
from .views import CarrierViewSet, TransportOrderViewSet, TransportTrackingViewSet

router = DefaultRouter()
router.register('carriers', CarrierViewSet,          basename='carrier')
router.register('orders',   TransportOrderViewSet,   basename='transportorder')
router.register('tracking', TransportTrackingViewSet, basename='transporttracking')

urlpatterns = router.urls
