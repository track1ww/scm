from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, AccountMoveViewSet, TaxInvoiceViewSet

router = DefaultRouter()
router.register('accounts',     AccountViewSet,     basename='account')
router.register('moves',        AccountMoveViewSet, basename='accountmove')
router.register('tax-invoices', TaxInvoiceViewSet,  basename='taxinvoice')

urlpatterns = router.urls
