from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone


class DashboardSummaryView(APIView):
    """
    GET /api/dashboard/summary/

    Returns aggregated KPIs for all ERP modules scoped to the
    authenticated user's company.  Each module section is wrapped in
    try/except so a single module failure never breaks the whole response.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = request.user.company
        today = timezone.now().date()
        month_start = today.replace(day=1)

        data = {}

        # ------------------------------------------------------------------
        # FI — Finance
        # AccountMove: state choices DRAFT / POSTED / CANCELLED
        #              move_type choices ENTRY / PURCHASE / SALE / PAYMENT /
        #                                RECEIPT / ADJUST
        #              date field: posting_date
        #              revenue aggregation: total_debit on SALE moves
        # ------------------------------------------------------------------
        try:
            import datetime
            from scm_fi.models import AccountMove, Budget
            moves = AccountMove.objects.filter(company=company)
            monthly_revenue = (
                moves
                .filter(state='POSTED', move_type='SALE', posting_date__gte=month_start)
                .aggregate(s=Sum('total_debit'))['s']
            )
            # Budget execution for current year
            current_year = today.year
            year_budgets = Budget.objects.filter(company=company, budget_year=current_year)
            total_budget = float(
                year_budgets.aggregate(s=Sum('budgeted_amount'))['s'] or 0
            )
            year_start = datetime.date(current_year, 1, 1)
            executed = float(
                AccountMove.objects.filter(
                    company=company, state='POSTED', posting_date__gte=year_start
                ).aggregate(s=Sum('total_debit'))['s'] or 0
            )
            execution_rate = round((executed / total_budget * 100), 1) if total_budget > 0 else 0
            data['fi'] = {
                'posted_count': moves.filter(state='POSTED').count(),
                'draft_count': moves.filter(state='DRAFT').count(),
                'monthly_revenue': float(monthly_revenue or 0),
                'budget_total': total_budget,
                'budget_executed': executed,
                'budget_execution_rate': execution_rate,
            }
        except Exception:
            data['fi'] = {}

        # ------------------------------------------------------------------
        # PP — Production Planning
        # ProductionOrder: status choices 계획 / 확정 / 생산중 / 완료 / 취소
        # ------------------------------------------------------------------
        try:
            from scm_pp.models import ProductionOrder
            orders = ProductionOrder.objects.filter(company=company)
            data['pp'] = {
                'total': orders.count(),
                'in_progress': orders.filter(status='생산중').count(),
                'completed': orders.filter(status='완료').count(),
                'planned': orders.filter(status='계획').count(),
                'confirmed': orders.filter(status='확정').count(),
            }
        except Exception:
            data['pp'] = {}

        # ------------------------------------------------------------------
        # WM — Warehouse Management
        # Inventory: quantity field is stock_qty; low stock uses min_stock
        # StockMovement: created_at DateTimeField → filter by __date
        # ------------------------------------------------------------------
        try:
            from django.db.models import F
            from scm_wm.models import Inventory, StockMovement
            inv = Inventory.objects.filter(company=company)
            # Low stock: min_stock > 0 and stock_qty at or below that threshold
            low_stock = inv.filter(min_stock__gt=0, stock_qty__lte=F('min_stock')).count()
            data['wm'] = {
                'total_items': inv.count(),
                'low_stock': low_stock,
                'movements_today': StockMovement.objects.filter(
                    company=company, created_at__date=today
                ).count(),
            }
        except Exception:
            data['wm'] = {}

        # ------------------------------------------------------------------
        # HR — Human Resources
        # Employee: status choices 재직 / 퇴직 / 휴직
        # Leave: status choices pending / approved / rejected / cancelled
        # Attendance: date field is work_date; no direct company FK —
        #             filter via employee__company
        # ------------------------------------------------------------------
        try:
            from scm_hr.models import Employee, Leave, Attendance
            data['hr'] = {
                'employee_count': Employee.objects.filter(
                    company=company, status='재직'
                ).count(),
                'pending_leaves': Leave.objects.filter(
                    company=company, status='pending'
                ).count(),
                'attendance_today': Attendance.objects.filter(
                    employee__company=company, work_date=today
                ).count(),
            }
        except Exception:
            data['hr'] = {}

        # ------------------------------------------------------------------
        # MM — Materials Management
        # PurchaseOrder: status choices 발주확정 / 납품중 / 입고완료 / 취소
        # ------------------------------------------------------------------
        try:
            from scm_mm.models import PurchaseOrder, Material
            data['mm'] = {
                'pending_orders': PurchaseOrder.objects.filter(
                    company=company, status='발주확정'
                ).count(),
                'in_delivery': PurchaseOrder.objects.filter(
                    company=company, status='납품중'
                ).count(),
                'material_count': Material.objects.filter(company=company).count(),
            }
        except Exception:
            data['mm'] = {}

        # ------------------------------------------------------------------
        # SD — Sales & Distribution
        # SalesOrder: ordered_at is DateTimeField → filter with __date or __gte
        #             status choices: 주문접수 / 생산/조달중 / 출하준비 / 배송중 /
        #                             배송완료 / 취소
        #             pending delivery → 출하준비
        # ------------------------------------------------------------------
        try:
            from scm_sd.models import SalesOrder
            sd_orders = SalesOrder.objects.filter(company=company)
            data['sd'] = {
                'monthly_orders': sd_orders.filter(
                    ordered_at__date__gte=month_start
                ).count(),
                'pending_delivery': sd_orders.filter(status='출하준비').count(),
                'in_transit': sd_orders.filter(status='배송중').count(),
                'new_orders': sd_orders.filter(status='주문접수').count(),
            }
        except Exception:
            data['sd'] = {}

        # ------------------------------------------------------------------
        # Workflow — Approval Requests
        # ApprovalRequest: status choices pending / approved / rejected / cancelled
        # ------------------------------------------------------------------
        try:
            from scm_workflow.models import ApprovalRequest
            data['workflow'] = {
                'pending_approvals': ApprovalRequest.objects.filter(
                    company=company, status='pending'
                ).count(),
            }
        except Exception:
            data['workflow'] = {}

        return Response(data)
