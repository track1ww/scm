from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    AccountViewSet, AccountMoveViewSet, BudgetViewSet,
    FixedAssetViewSet, TaxInvoiceViewSet, AccountingPeriodViewSet,
    FinancialStatementView,
)

router = DefaultRouter()
router.register(r'accounts',      AccountViewSet,          basename='account')
router.register(r'moves',         AccountMoveViewSet,      basename='account-move')
router.register(r'budgets',       BudgetViewSet,           basename='budget')
router.register(r'fixed-assets',  FixedAssetViewSet,       basename='fixed-asset')
router.register(r'tax-invoices',  TaxInvoiceViewSet,       basename='tax-invoice')
router.register(r'periods',       AccountingPeriodViewSet, basename='accounting-period')

urlpatterns = router.urls + [
    path('statements/', FinancialStatementView.as_view(), name='financial-statements'),
]
