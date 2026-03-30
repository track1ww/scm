from rest_framework.routers import DefaultRouter
from .views import BOMViewSet, BOMLineViewSet, ProductionOrderViewSet, MRPPlanViewSet

router = DefaultRouter()
router.register('boms',              BOMViewSet,             basename='bom')
router.register('bom-lines',         BOMLineViewSet,         basename='bom-line')
router.register('production-orders', ProductionOrderViewSet, basename='production-order')
router.register('mrp-plans',         MRPPlanViewSet,         basename='mrp-plan')

urlpatterns = router.urls
