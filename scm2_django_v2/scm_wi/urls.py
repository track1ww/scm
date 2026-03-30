from rest_framework.routers import DefaultRouter
from .views import WorkInstructionViewSet, WorkResultViewSet

router = DefaultRouter()
router.register('work-orders',  WorkInstructionViewSet, basename='work-order')
router.register('results',      WorkResultViewSet,      basename='work-result')

urlpatterns = router.urls
