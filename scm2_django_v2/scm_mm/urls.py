from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet, MaterialViewSet, PurchaseOrderViewSet,
    PurchaseOrderLineViewSet, GoodsReceiptViewSet, MaterialPriceHistoryViewSet,
    RFQViewSet, SupplierEvaluationViewSet,
)

router = DefaultRouter()
router.register('suppliers',     SupplierViewSet,             basename='supplier')
router.register('materials',     MaterialViewSet,             basename='material')
router.register('orders',        PurchaseOrderViewSet,        basename='po')
router.register('po-lines',      PurchaseOrderLineViewSet,    basename='po-line')
router.register('receipts',      GoodsReceiptViewSet,         basename='gr')
router.register('price-history', MaterialPriceHistoryViewSet, basename='price-history')
router.register('rfqs',          RFQViewSet,                  basename='rfq')
router.register('evaluations',   SupplierEvaluationViewSet,   basename='evaluation')

urlpatterns = router.urls
