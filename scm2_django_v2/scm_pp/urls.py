from rest_framework.routers import DefaultRouter
from .views import (BillOfMaterialViewSet, BomLineViewSet,
                     ProductionOrderViewSet, MrpRunViewSet,
                     WorkCenterCostViewSet)

router = DefaultRouter()
router.register('boms',               BillOfMaterialViewSet,   basename='bom')
router.register('bom-lines',          BomLineViewSet,          basename='bom-line')
router.register('production-orders',  ProductionOrderViewSet,  basename='production-order')
router.register('mrp-plans',          MrpRunViewSet,           basename='mrp-plan')
router.register('work-center-costs',  WorkCenterCostViewSet,   basename='work-center-cost')

urlpatterns = router.urls
