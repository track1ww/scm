from rest_framework.routers import DefaultRouter
from .views import CarrierViewSet, TransportOrderViewSet, FreightRateViewSet, ShipmentTrackingViewSet

router = DefaultRouter()
router.register('carriers',  CarrierViewSet,          basename='carrier')
router.register('orders',    TransportOrderViewSet,   basename='transport-order')
router.register('rates',     FreightRateViewSet,      basename='freight-rate')
router.register('tracking',  ShipmentTrackingViewSet, basename='shipment-tracking')

urlpatterns = router.urls
