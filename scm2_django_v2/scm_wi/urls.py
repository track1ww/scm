from rest_framework.routers import DefaultRouter
from .views import WorkInstructionViewSet, WorkResultViewSet, WorkStandardViewSet

router = DefaultRouter()
router.register('work-orders',  WorkInstructionViewSet, basename='work-order')
router.register('results',      WorkResultViewSet,      basename='work-result')
router.register('standards',    WorkStandardViewSet,    basename='work-standard')

urlpatterns = router.urls
