from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, MaterialViewSet, PurchaseOrderViewSet, GoodsReceiptViewSet

router = DefaultRouter()
router.register('suppliers',  SupplierViewSet,      basename='supplier')
router.register('materials',  MaterialViewSet,       basename='material')
router.register('orders',     PurchaseOrderViewSet,  basename='po')
router.register('receipts',   GoodsReceiptViewSet,   basename='gr')

urlpatterns = router.urls
