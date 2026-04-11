from rest_framework.routers import DefaultRouter
from .views import (
    SubcontractOrderViewSet,
    SubcontractOrderLineViewSet,
    SubcontractMaterialViewSet,
    SubcontractReceiptViewSet,
)

router = DefaultRouter()
router.register('orders',    SubcontractOrderViewSet,    basename='sub-order')
router.register('lines',     SubcontractOrderLineViewSet, basename='sub-line')
router.register('materials', SubcontractMaterialViewSet, basename='sub-material')
router.register('receipts',  SubcontractReceiptViewSet,  basename='sub-receipt')

urlpatterns = router.urls
