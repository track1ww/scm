from django.urls import path
from .views import (
    PurchaseOrderPDF, InspectionReportPDF, SalesInvoicePDF,
    FinancialStatementPDF, PayrollSlipPDF,
)

urlpatterns = [
    path('po/<int:pk>/pdf/',                PurchaseOrderPDF.as_view(),       name='po-pdf'),
    path('inspection/<int:pk>/pdf/',        InspectionReportPDF.as_view(),    name='inspection-pdf'),
    path('invoice/<int:pk>/pdf/',           SalesInvoicePDF.as_view(),        name='invoice-pdf'),
    path('financial-statement/pdf/',        FinancialStatementPDF.as_view(),  name='financial-statement-pdf'),
    path('payroll/<int:pk>/pdf/',           PayrollSlipPDF.as_view(),         name='payroll-pdf'),
]
