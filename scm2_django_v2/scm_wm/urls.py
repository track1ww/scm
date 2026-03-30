from rest_framework.routers import DefaultRouter
from .views import (
    WarehouseViewSet,
    InventoryViewSet,
    StockMovementViewSet,
    BinLocationViewSet,
    CycleCountViewSet,
)

router = DefaultRouter()
router.register('warehouses',   WarehouseViewSet,     basename='warehouse')
router.register('inventory',    InventoryViewSet,     basename='inventory')
router.register('movements',    StockMovementViewSet, basename='stock-movement')
router.register('bins',         BinLocationViewSet,   basename='bin-location')
router.register('cycle-counts', CycleCountViewSet,    basename='cycle-count')

urlpatterns = router.urls
