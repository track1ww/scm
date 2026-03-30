from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, SalesOrderViewSet, DeliveryViewSet, SalesInvoiceViewSet

router = DefaultRouter()
router.register('customers',  CustomerViewSet,      basename='customer')
router.register('orders',     SalesOrderViewSet,    basename='sales-order')
router.register('deliveries', DeliveryViewSet,      basename='delivery')
router.register('invoices',   SalesInvoiceViewSet,  basename='sales-invoice')

urlpatterns = router.urls
