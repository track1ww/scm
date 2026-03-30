from rest_framework.routers import DefaultRouter
from .views import InspectionPlanViewSet, InspectionResultViewSet, DefectReportViewSet

router = DefaultRouter()
router.register('inspection-plans',   InspectionPlanViewSet,   basename='inspection-plan')
router.register('inspection-results', InspectionResultViewSet, basename='inspection-result')
router.register('defect-reports',     DefectReportViewSet,     basename='defect-report')

urlpatterns = router.urls
