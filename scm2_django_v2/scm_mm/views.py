import math
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from scm_core.mixins import AuditLogMixin
from .utils import calc_safety_stock, calc_eoq, calc_reorder_point
from .models import (
    Supplier, Material, PurchaseOrder, PurchaseOrderLine,
    GoodsReceipt, MaterialPriceHistory, RFQ, SupplierEvaluation,
    SupplierMaterialConfig,
)
from .serializers import (
    SupplierSerializer, MaterialSerializer,
    PurchaseOrderSerializer, PurchaseOrderLineSerializer,
    GoodsReceiptSerializer, MaterialPriceHistorySerializer,
    RFQSerializer, SupplierEvaluationSerializer,
    SupplierMaterialConfigSerializer,
)

class SupplierViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class   = SupplierSerializer
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'contact', 'email']
    ordering_fields    = ['name', 'created_at']

    def get_queryset(self):
        return Supplier.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

class MaterialViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class = MaterialSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['material_code', 'material_name']

    def get_queryset(self):
        return Material.objects.filter(company=self.request.user.company)

    @action(detail=True, methods=['get'], url_path='supplier-comparison')
    def supplier_comparison(self, request, pk=None):
        """
        Compare suppliers for this material based on price history.
        GET /api/mm/materials/{id}/supplier-comparison/
        Returns list of suppliers with latest price and price trend.
        """
        material = self.get_object()
        from .models import MaterialPriceHistory
        from django.db.models import Min, Max, Avg

        histories = MaterialPriceHistory.objects.filter(
            material=material, company=request.user.company
        ).select_related('supplier')

        # Group by supplier
        supplier_data = {}
        for h in histories:
            sid = h.supplier_id or 'no_supplier'
            if sid not in supplier_data:
                supplier_data[sid] = {
                    'supplier_id': h.supplier_id,
                    'supplier_name': str(h.supplier) if h.supplier else '미지정',
                    'prices': [],
                }
            supplier_data[sid]['prices'].append({
                'price': float(h.unit_price),
                'date': str(h.effective_from),
                'price_type': h.price_type,
            })

        result = []
        for sid, d in supplier_data.items():
            prices = [p['price'] for p in d['prices']]
            d['latest_price'] = prices[0] if prices else 0
            d['min_price'] = min(prices) if prices else 0
            d['max_price'] = max(prices) if prices else 0
            d['avg_price'] = round(sum(prices) / len(prices), 2) if prices else 0
            d['history_count'] = len(prices)
            result.append(d)

        # Sort by latest price ascending
        result.sort(key=lambda x: x['latest_price'])
        return Response(result)

    @action(detail=True, methods=['get'], url_path='requirements')
    def requirements_plan(self, request, pk=None):
        """
        Simple requirements planning for a material.
        GET /api/mm/materials/{id}/requirements/
        Returns: current stock, pending POs, pending SOs, net requirement.
        """
        material = self.get_object()
        company = request.user.company
        result = {
            'material_id': material.pk,
            'material_code': getattr(material, 'material_code', ''),
            'material_name': getattr(material, 'material_name', str(material)),
            'unit': getattr(material, 'unit', ''),
        }

        # Current WM stock
        try:
            from scm_wm.models import Inventory
            inv = Inventory.objects.filter(
                company=company,
                item_code=getattr(material, 'material_code', ''),
            ).first()
            result['current_stock'] = float(getattr(inv, 'stock_qty', 0) or 0)
            result['min_stock'] = float(getattr(inv, 'min_stock', 0) or 0)
        except Exception:
            result['current_stock'] = 0
            result['min_stock'] = 0

        # Pending POs (incoming supply)
        try:
            from scm_mm.models import PurchaseOrder
            pending_po_qty = sum(
                float(po.quantity or 0)
                for po in PurchaseOrder.objects.filter(
                    company=company,
                    item_name=getattr(material, 'material_name', ''),
                    status__in=['발주확정', '납품중'],
                )
            )
            result['pending_po_qty'] = pending_po_qty
        except Exception:
            result['pending_po_qty'] = 0

        # Pending SOs (outgoing demand)
        try:
            from scm_sd.models import SalesOrder
            pending_so_qty = sum(
                float(so.quantity or 0)
                for so in SalesOrder.objects.filter(
                    company=company,
                    item_name=getattr(material, 'material_name', ''),
                    status__in=['주문접수', '생산/조달중', '출하준비'],
                )
                if hasattr(so, 'quantity')
            )
            result['pending_so_qty'] = pending_so_qty
        except Exception:
            result['pending_so_qty'] = 0

        # Net requirement
        net = result['current_stock'] + result['pending_po_qty'] - result['pending_so_qty']
        result['net_available'] = round(net, 2)
        result['shortage'] = round(max(0, result['min_stock'] - net), 2)
        result['reorder_needed'] = result['shortage'] > 0

        return Response(result)

class PurchaseOrderViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class = PurchaseOrderSerializer
    filter_backends  = [filters.SearchFilter, DjangoFilterBackend]
    search_fields    = ['po_number', 'item_name']
    filterset_fields = ['status', 'supplier']

    def get_queryset(self):
        return PurchaseOrder.objects.filter(
            company=self.request.user.company
        ).select_related('supplier').prefetch_related('lines__material').order_by('-created_at')

    def perform_create(self, serializer):
        import uuid
        from django.utils import timezone
        po_number = serializer.validated_data.get('po_number') or \
            f'PO-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}'
        serializer.save(company=self.request.user.company, po_number=po_number)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({
            'total':    qs.count(),
            'pending':  qs.exclude(status__in=['입고완료','취소']).count(),
            'complete': qs.filter(status='입고완료').count(),
        })

class PurchaseOrderLineViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderLineSerializer

    def get_queryset(self):
        qs = PurchaseOrderLine.objects.filter(po__company=self.request.user.company)
        po_id = self.request.query_params.get('po')
        if po_id:
            qs = qs.filter(po_id=po_id)
        return qs.select_related('material')

    def perform_create(self, serializer):
        serializer.save()


class GoodsReceiptViewSet(AuditLogMixin, viewsets.ModelViewSet):
    audit_module = 'mm'
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        return GoodsReceipt.objects.filter(
            company=self.request.user.company
        ).select_related('po').order_by('-created_at')


class MaterialPriceHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialPriceHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaterialPriceHistory.objects.filter(company=self.request.user.company)
        material_id = self.request.query_params.get('material')
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class RFQViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """견적요청(RFQ) CRUD + 발주서 자동전환"""
    audit_module = 'mm'
    serializer_class = RFQSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['rfq_number', 'item_name']
    filterset_fields = ['status', 'supplier']
    ordering_fields = ['created_at', 'required_date']

    def get_queryset(self):
        return RFQ.objects.filter(
            company=self.request.user.company
        ).select_related('supplier').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    # ------------------------------------------------------------------
    # POST /api/mm/rfqs/{id}/convert-to-po/
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='convert-to-po')
    def convert_to_po(self, request, pk=None):
        """
        RFQ를 발주서(PurchaseOrder)로 자동 전환합니다.
        status가 'received'(견적수신) 또는 'closed'(마감)인 경우에만 허용됩니다.
        """
        rfq = self.get_object()

        # 상태 검증
        if rfq.status not in ('received', 'closed'):
            return Response(
                {'error': '견적 수신 또는 마감 상태에서만 전환 가능합니다.'},
                status=400,
            )

        # 발주서 번호 생성 (중복 방지)
        po_number = f'PO-{rfq.rfq_number}'
        if PurchaseOrder.objects.filter(po_number=po_number).exists():
            return Response(
                {'error': f'이미 전환된 발주서가 있습니다: {po_number}'},
                status=400,
            )

        # 최신 단가 조회 (공급업체 + 자재명 기반)
        unit_price = Decimal('0')
        try:
            price_record = (
                MaterialPriceHistory.objects
                .filter(
                    company=rfq.company,
                    supplier=rfq.supplier,
                    material__material_name=rfq.item_name,
                    price_type='purchase',
                )
                .order_by('-effective_from')
                .first()
            )
            if price_record:
                unit_price = price_record.unit_price
        except Exception:
            pass  # 단가 조회 실패 시 0으로 진행

        # 발주서 생성
        po = PurchaseOrder.objects.create(
            company=rfq.company,
            po_number=po_number,
            supplier=rfq.supplier,
            item_name=rfq.item_name,
            quantity=rfq.quantity,
            unit_price=unit_price,
            delivery_date=rfq.required_date,
            status='발주확정',
            note=f'RFQ {rfq.rfq_number}에서 자동 전환',
        )

        # RFQ 상태를 'closed'로 업데이트
        rfq.status = 'closed'
        rfq.save(update_fields=['status'])

        # 알림 발송 (DB 저장 + WebSocket push)
        self._notify_auto_po(rfq, po)

        return Response({'po_number': po.po_number, 'id': po.id}, status=201)

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _notify_auto_po(self, rfq, po):
        """발주서 자동생성 알림을 회사 사용자 전원에게 전송합니다."""
        title = '발주서 자동생성'
        message = f'RFQ {rfq.rfq_number}에서 발주서 {po.po_number} 자동생성됨'

        try:
            from scm_accounts.models import User as ScmUser
            from scm_notifications.models import Notification
            from scm_notifications.push import push_notification

            company_users = ScmUser.objects.filter(
                company=rfq.company,
                is_active=True,
            )
            for user in company_users:
                notif = Notification.objects.create(
                    company=rfq.company,
                    recipient=user,
                    notification_type='system',
                    title=title,
                    message=message,
                    ref_module='mm',
                    ref_id=po.id,
                )
                push_notification(
                    user_id=user.id,
                    notification_data={
                        'id': notif.id,
                        'title': notif.title,
                        'message': notif.message,
                        'notification_type': notif.notification_type,
                        'is_read': notif.is_read,
                        'created_at': str(notif.created_at),
                    },
                )
        except Exception:
            pass  # 알림 실패가 핵심 트랜잭션을 방해하지 않도록 무시


class SupplierEvaluationViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """공급업체 성과평가"""
    audit_module = 'mm'
    serializer_class = SupplierEvaluationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['supplier', 'eval_year', 'eval_month']
    ordering_fields = ['eval_year', 'eval_month', 'total_score']

    def get_queryset(self):
        return SupplierEvaluation.objects.filter(
            company=self.request.user.company
        ).select_related('supplier').order_by('-eval_year', '-eval_month')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class SupplierMaterialConfigViewSet(viewsets.ModelViewSet):
    """품목+매입처 조합 리드타임 설정"""
    serializer_class = SupplierMaterialConfigSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['material', 'supplier']

    def get_queryset(self):
        return SupplierMaterialConfig.objects.filter(
            company=self.request.user.company
        ).select_related('material', 'supplier')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


# ─── SCM 계산기 API ───────────────────────────────────────────────────────────

# 재고 유형별 기본 서비스 수준 / 위험재고 리드타임 비율
_INV_TYPE_CONFIG = {
    'raw_material':  {'service_level': 0.95, 'danger_factor': 0.5, 'label': '원자재'},
    'finished_good': {'service_level': 0.99, 'danger_factor': 0.3, 'label': '완제품'},
    'semi_finished': {'service_level': 0.95, 'danger_factor': 0.5, 'label': '반제품'},
    'mro':           {'service_level': 0.90, 'danger_factor': 0.7, 'label': '소모품/MRO'},
    'perishable':    {'service_level': 0.98, 'danger_factor': 0.25, 'label': '신선/냉장'},
}


class CalculatorLeadTimeView(APIView):
    """GET /mm/calculator/lead-time/?material_id=X&supplier_id=Y
    우선순위: 품목+매입처 조합 > 품목 기본값 > 매입처 기본값 > 시스템 기본값(7)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        material_id = request.query_params.get('material_id')
        supplier_id = request.query_params.get('supplier_id')
        company     = request.user.company

        source     = 'default'
        lead_time  = 7
        material_name = ''
        supplier_name = ''

        # 1. 품목+매입처 조합
        if material_id and supplier_id:
            cfg = SupplierMaterialConfig.objects.filter(
                company=company, material_id=material_id, supplier_id=supplier_id
            ).first()
            if cfg:
                lead_time = cfg.lead_time_days
                source    = 'material_supplier'

        # 2. 품목 기본값
        if source == 'default' and material_id:
            mat = Material.objects.filter(company=company, pk=material_id).first()
            if mat:
                lead_time     = mat.lead_time_days
                material_name = mat.material_name
                source        = 'material'

        # 3. 매입처 기본값
        if source == 'default' and supplier_id:
            sup = Supplier.objects.filter(company=company, pk=supplier_id).first()
            if sup:
                lead_time     = sup.lead_time_days
                supplier_name = sup.name
                source        = 'supplier'

        # 품목/매입처 이름 보완
        if material_id and not material_name:
            mat = Material.objects.filter(company=company, pk=material_id).first()
            if mat: material_name = mat.material_name
        if supplier_id and not supplier_name:
            sup = Supplier.objects.filter(company=company, pk=supplier_id).first()
            if sup: supplier_name = sup.name

        source_label = {
            'material_supplier': f'품목+매입처 조합 설정값',
            'material':          f'품목 기본값 ({material_name})',
            'supplier':          f'매입처 기본값 ({supplier_name})',
            'default':           '시스템 기본값',
        }[source]

        return Response({
            'lead_time_days': lead_time,
            'source':         source,
            'source_label':   source_label,
            'material_name':  material_name,
            'supplier_name':  supplier_name,
        })


class CalculatorSafetyStockView(APIView):
    """POST /mm/calculator/safety-stock/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        d = request.data
        inv_type      = d.get('inventory_type', 'raw_material')
        avg_demand    = float(d.get('avg_demand', 0))
        demand_std    = float(d.get('demand_std', 0))
        lead_time     = float(d.get('lead_time', 1))
        service_level = d.get('service_level')

        cfg = _INV_TYPE_CONFIG.get(inv_type, _INV_TYPE_CONFIG['raw_material'])
        sl  = float(service_level) if service_level is not None else cfg['service_level']

        ss  = calc_safety_stock(demand_std, lead_time, sl)
        rop = calc_reorder_point(avg_demand, lead_time, ss['safety_stock'])

        danger_lt    = lead_time * cfg['danger_factor']
        danger_stock = round(avg_demand * danger_lt, 2)

        return Response({
            'inventory_type':       inv_type,
            'inventory_type_label': cfg['label'],
            'service_level':        sl,
            'z_score':              ss['z'],
            'safety_stock':         ss['safety_stock'],
            'danger_stock':         danger_stock,
            'reorder_point':        rop['rop'],
            'lead_time_demand':     rop['lead_time_demand'],
            'interpretation': {
                'safety_stock': f"재고가 {ss['safety_stock']} 이하로 떨어지면 안전재고 진입",
                'danger_stock': f"재고가 {danger_stock} 이하로 떨어지면 위험재고 — 긴급 발주 필요",
                'reorder_point': f"재고가 {rop['rop']} 이하로 떨어지면 즉시 발주",
            }
        })


class CalculatorEOQView(APIView):
    """POST /mm/calculator/eoq/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        d = request.data
        annual_demand = float(d.get('annual_demand', 0))
        order_cost    = float(d.get('order_cost', 0))
        holding_cost  = float(d.get('holding_cost', 0))

        if holding_cost <= 0:
            return Response({'error': '보관비용(holding_cost)은 0보다 커야 합니다.'}, status=400)
        if annual_demand <= 0:
            return Response({'error': '연간 수요량(annual_demand)은 0보다 커야 합니다.'}, status=400)

        result = calc_eoq(annual_demand, order_cost, holding_cost)
        result['annual_order_cost']   = round(result['annual_orders'] * order_cost, 0)
        result['annual_holding_cost'] = round(result['eoq'] / 2 * holding_cost, 0)
        result['total_annual_cost']   = round(
            result['annual_order_cost'] + result['annual_holding_cost'], 0
        )
        return Response(result)


class CalculatorDemandForecastView(APIView):
    """GET /mm/calculator/demand-forecast/
    item_code, method (sma|wma|exp), history_months, forecast_periods
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from scm_wm.models import StockMovement

        item_code        = request.query_params.get('item_code', '')
        method           = request.query_params.get('method', 'wma')
        history_months   = int(request.query_params.get('history_months', 6))
        forecast_periods = int(request.query_params.get('forecast_periods', 3))
        company          = request.user.company

        qs = StockMovement.objects.filter(
            company=company, movement_type='OUT'
        )
        if item_code:
            qs = qs.filter(material_code=item_code)

        monthly = (
            qs.annotate(month=TruncMonth('created_at'))
              .values('month', 'material_code', 'material_name')
              .annotate(total_qty=Sum('quantity'))
              .order_by('material_code', 'month')
        )

        # 품목별 그룹화
        grouped = defaultdict(list)
        for row in monthly:
            grouped[(row['material_code'], row['material_name'])].append({
                'month': row['month'].strftime('%Y-%m') if row['month'] else '',
                'qty':   float(row['total_qty'] or 0),
            })

        results = []
        for (code, name), history in grouped.items():
            hist = history[-history_months:]
            qtys = [h['qty'] for h in hist]
            if not qtys:
                continue

            forecast = self._forecast(qtys, method, forecast_periods)
            avg      = round(sum(qtys) / len(qtys), 1)
            std      = round(
                math.sqrt(sum((q - avg) ** 2 for q in qtys) / max(len(qtys), 1)), 1
            )

            results.append({
                'item_code':        code,
                'item_name':        name,
                'history':          hist,
                'forecast':         forecast,
                'avg_monthly':      avg,
                'std_monthly':      std,
                'method':           method,
                'recommended_order': max(0, round(forecast[0]['forecast'] if forecast else avg, 0)),
            })

        return Response({'results': results, 'method': method})

    def _forecast(self, qtys, method, periods):
        n = len(qtys)
        forecasts = []
        if n == 0:
            return forecasts

        if method == 'sma':
            window = min(3, n)
            base   = sum(qtys[-window:]) / window
            for i in range(periods):
                forecasts.append({'period': i + 1, 'forecast': round(base, 1)})

        elif method == 'wma':
            window  = min(3, n)
            weights = list(range(1, window + 1))
            vals    = qtys[-window:]
            base    = sum(w * v for w, v in zip(weights, vals)) / sum(weights)
            for i in range(periods):
                forecasts.append({'period': i + 1, 'forecast': round(base, 1)})

        elif method == 'exp':
            alpha = 0.3
            s     = qtys[0]
            for q in qtys[1:]:
                s = alpha * q + (1 - alpha) * s
            for i in range(periods):
                forecasts.append({'period': i + 1, 'forecast': round(s, 1)})
                s = alpha * s + (1 - alpha) * s  # 미래 기간은 자기 자신으로 갱신

        return forecasts


class CalculatorTransferListView(APIView):
    """GET /mm/calculator/transfer-list/
    창고 간 재고 불균형 탐지 → 이관 권고 목록 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from scm_wm.models import Inventory

        company = request.user.company
        inv_qs  = Inventory.objects.filter(company=company).select_related('warehouse')

        # item_code별로 창고 재고 집계
        item_map = defaultdict(list)
        for inv in inv_qs:
            item_map[inv.item_code].append({
                'warehouse_id':   inv.warehouse_id,
                'warehouse_name': inv.warehouse.warehouse_name if inv.warehouse else '-',
                'item_name':      inv.item_name,
                'stock_qty':      inv.stock_qty,
                'min_stock':      inv.min_stock,
                'category':       inv.category,
            })

        transfer_list = []
        for item_code, warehouses in item_map.items():
            if len(warehouses) < 2:
                continue  # 창고 1곳뿐이면 이관 불필요

            # 부족 창고: stock_qty < min_stock
            deficit  = [w for w in warehouses if w['min_stock'] > 0 and w['stock_qty'] < w['min_stock']]
            # 여유 창고: stock_qty > min_stock * 2 (여유분 = stock - min_stock)
            surplus  = [w for w in warehouses if w['stock_qty'] > w['min_stock'] * 2 and w['min_stock'] > 0]

            if not deficit or not surplus:
                continue

            for d in deficit:
                needed = d['min_stock'] - d['stock_qty']
                for s in surplus:
                    available = s['stock_qty'] - s['min_stock']  # 안전재고 초과분
                    transfer_qty = min(needed, available)
                    if transfer_qty <= 0:
                        continue
                    transfer_list.append({
                        'item_code':       item_code,
                        'item_name':       d['item_name'],
                        'category':        d['category'],
                        'from_warehouse':  s['warehouse_name'],
                        'to_warehouse':    d['warehouse_name'],
                        'transfer_qty':    transfer_qty,
                        'deficit_stock':   d['stock_qty'],
                        'deficit_min':     d['min_stock'],
                        'surplus_stock':   s['stock_qty'],
                        'urgency':         '긴급' if d['stock_qty'] == 0 else '권고',
                    })
                    needed -= transfer_qty
                    if needed <= 0:
                        break

        transfer_list.sort(key=lambda x: (x['urgency'] == '권고', x['item_code']))
        return Response({'results': transfer_list, 'count': len(transfer_list)})
