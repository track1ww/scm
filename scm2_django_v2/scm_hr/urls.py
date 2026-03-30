from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, EmployeeViewSet, PayrollViewSet, AttendanceViewSet, LeaveViewSet

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('employees',   EmployeeViewSet,   basename='employee')
router.register('payrolls',    PayrollViewSet,     basename='payroll')
router.register('attendances', AttendanceViewSet,  basename='attendance')
router.register('leaves',      LeaveViewSet,       basename='leave')

urlpatterns = router.urls
