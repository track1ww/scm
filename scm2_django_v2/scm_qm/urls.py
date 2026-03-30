from rest_framework.routers import DefaultRouter
from .views import (InspectionPlanViewSet, InspectionResultViewSet,
                     DefectRecordViewSet, CorrectiveActionViewSet)

router = DefaultRouter()
router.register('inspection-plans',   InspectionPlanViewSet,    basename='inspection-plan')
router.register('inspection-results', InspectionResultViewSet,  basename='inspection-result')
router.register('defect-reports',     DefectRecordViewSet,      basename='defect-report')
router.register('corrective-actions', CorrectiveActionViewSet,  basename='corrective-action')

urlpatterns = router.urls
