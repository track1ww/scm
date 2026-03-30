from rest_framework.routers import DefaultRouter
from .views import (BillOfMaterialViewSet, BomLineViewSet,
                     ProductionOrderViewSet, MrpRunViewSet)

router = DefaultRouter()
router.register('boms',               BillOfMaterialViewSet,   basename='bom')
router.register('bom-lines',          BomLineViewSet,          basename='bom-line')
router.register('production-orders',  ProductionOrderViewSet,  basename='production-order')
router.register('mrp-plans',          MrpRunViewSet,           basename='mrp-plan')

urlpatterns = router.urls
