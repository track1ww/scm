from rest_framework.routers import DefaultRouter
from .views import WorkOrderViewSet

router = DefaultRouter()
# 기본 라우터: /api/wi/work-orders/
router.register('work-orders', WorkOrderViewSet, basename='work-order')
# 별칭 라우터: /api/wi/instructions/  (프론트엔드 기준 스펙 호환)
router.register('instructions', WorkOrderViewSet, basename='work-order-alias')

urlpatterns = router.urls
