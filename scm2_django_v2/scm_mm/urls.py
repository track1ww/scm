from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet, MaterialViewSet, PurchaseOrderViewSet,
    PurchaseOrderLineViewSet, GoodsReceiptViewSet, MaterialPriceHistoryViewSet,
    RFQViewSet, SupplierEvaluationViewSet, SupplierMaterialConfigViewSet,
    CalculatorLeadTimeView, CalculatorSafetyStockView, CalculatorEOQView,
    CalculatorDemandForecastView, CalculatorTransferListView,
)

router = DefaultRouter()
router.register('suppliers',        SupplierViewSet,              basename='supplier')
router.register('materials',        MaterialViewSet,              basename='material')
router.register('orders',           PurchaseOrderViewSet,         basename='po')
router.register('po-lines',         PurchaseOrderLineViewSet,     basename='po-line')
router.register('receipts',         GoodsReceiptViewSet,          basename='gr')
router.register('price-history',    MaterialPriceHistoryViewSet,  basename='price-history')
router.register('rfqs',             RFQViewSet,                   basename='rfq')
router.register('evaluations',      SupplierEvaluationViewSet,    basename='evaluation')
router.register('supplier-configs', SupplierMaterialConfigViewSet, basename='supplier-config')

urlpatterns = router.urls + [
    path('calculator/lead-time/',     CalculatorLeadTimeView.as_view(),       name='calc-lead-time'),
    path('calculator/safety-stock/',  CalculatorSafetyStockView.as_view(),    name='calc-safety-stock'),
    path('calculator/eoq/',           CalculatorEOQView.as_view(),             name='calc-eoq'),
    path('calculator/demand-forecast/', CalculatorDemandForecastView.as_view(), name='calc-demand'),
    path('calculator/transfer-list/', CalculatorTransferListView.as_view(),    name='calc-transfer'),
]
