from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, EmployeeViewSet, PayrollViewSet

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('employees',   EmployeeViewSet,   basename='employee')
router.register('payrolls',    PayrollViewSet,     basename='payroll')

urlpatterns = router.urls
