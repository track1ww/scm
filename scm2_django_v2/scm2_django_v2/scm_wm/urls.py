from rest_framework.routers import DefaultRouter

from .views import WarehouseViewSet, InventoryViewSet, StockMovementViewSet

router = DefaultRouter()
router.register('warehouses', WarehouseViewSet, basename='warehouse')
router.register('inventory',  InventoryViewSet,  basename='inventory')
router.register('movements',  StockMovementViewSet, basename='movement')

urlpatterns = router.urls
