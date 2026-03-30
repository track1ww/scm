from decimal import Decimal

from django.db.models import F, Sum, Count, ExpressionWrapper, DecimalField, Q
from django.utils import timezone

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Warehouse, Inventory, StockMovement
from .serializers import (
    WarehouseSerializer,
    InventorySerializer,
    StockMovementSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    창고 마스터 CRUD.
    - company 스코프 자동 적용
    - ?search=  warehouse_code / warehouse_name / location 검색
    - ?ordering= warehouse_code, warehouse_name
    """
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    search_fields   = ['warehouse_code', 'warehouse_name', 'location']
    ordering_fields = ['warehouse_code', 'warehouse_name']
    filterset_fields = ['warehouse_type', 'is_active']

    def get_queryset(self):
        return Warehouse.objects.filter(
            company=self.request.user.company
        ).order_by('warehouse_code')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class InventoryViewSet(viewsets.ModelViewSet):
    """
    재고 CRUD.
    - company 스코프 자동 적용
    - ?search=  item_code / item_name / lot_number / bin_code 검색
    - ?warehouse= / ?category= 필터
    - GET /inventory/dashboard/  대시보드 집계
    """
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    search_fields   = ['item_code', 'item_name', 'lot_number', 'bin_code']
    ordering_fields = ['item_code', 'item_name', 'stock_qty', 'updated_at']
    filterset_fields = ['warehouse', 'category']

    def get_queryset(self):
        return (
            Inventory.objects
            .filter(company=self.request.user.company)
            .select_related('warehouse')
            .order_by('item_code')
        )

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    # ------------------------------------------------------------------ #
    #  GET /api/wm/inventory/analysis/                                   #
    #  재고 분석: ABC 분류, 회전율, 불용재고, 창고별 재고금액             #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'], url_path='analysis')
    def analysis(self, request):
        """
        재고 분석 종합 리포트.

        Returns:
            abc_classification: ABC 분류별 품목 수 및 재고금액
            turnover:           최근 3개월 OUT 기준 회전율 (품목별)
            dead_stock:         6개월 이상 미이동 불용재고 품목 수 / 금액
            by_warehouse:       창고별 재고금액 합계
        """
        today         = timezone.now().date()
        three_months_ago = today.replace(day=1)
        # 정확한 3개월 전 날짜 계산
        month = today.month - 3
        year  = today.year
        if month <= 0:
            month += 12
            year  -= 1
        three_months_ago = today.replace(year=year, month=month, day=1)

        six_months_ago = today.replace(day=1)
        month6 = today.month - 6
        year6  = today.year
        if month6 <= 0:
            month6 += 12
            year6  -= 1
        six_months_ago = today.replace(year=year6, month=month6, day=1)

        qs = self.get_queryset()

        # --- 재고금액 = stock_qty * unit_price 표현식 ---
        stock_value_expr = ExpressionWrapper(
            F('stock_qty') * F('unit_price'),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )

        # ── 1. ABC 분류별 집계 ────────────────────────────────────────── #
        # ABC 분류는 category 필드에 'A', 'B', 'C' 등 저장 가정
        # 비어있거나 미분류인 경우 'UNCLASSIFIED' 처리
        abc_raw = (
            qs.values('category')
            .annotate(
                item_count=Count('id'),
                total_stock_value=Sum(stock_value_expr),
            )
            .order_by('category')
        )
        abc_classification = [
            {
                'category':          row['category'] or 'UNCLASSIFIED',
                'item_count':        row['item_count'],
                'total_stock_value': row['total_stock_value'] or Decimal('0'),
            }
            for row in abc_raw
        ]

        # ── 2. 창고별 재고금액 합계 ───────────────────────────────────── #
        by_warehouse_raw = (
            qs.values('warehouse__warehouse_code', 'warehouse__warehouse_name')
            .annotate(
                item_count=Count('id'),
                total_stock_value=Sum(stock_value_expr),
            )
            .order_by('-total_stock_value')
        )
        by_warehouse = [
            {
                'warehouse_code':    row['warehouse__warehouse_code'],
                'warehouse_name':    row['warehouse__warehouse_name'],
                'item_count':        row['item_count'],
                'total_stock_value': row['total_stock_value'] or Decimal('0'),
            }
            for row in by_warehouse_raw
        ]

        # ── 3. 회전율: 최근 3개월 OUT 이동 기준 ──────────────────────── #
        # StockMovement.OUT 수량 합계 / 현재 재고수량
        out_movements = (
            StockMovement.objects
            .filter(
                company=request.user.company,
                movement_type='OUT',
                created_at__date__gte=three_months_ago,
            )
            .values('material_code')
            .annotate(total_out=Sum('quantity'))
        )
        out_map = {row['material_code']: row['total_out'] for row in out_movements}

        # 현재 재고를 item_code 기준 집계
        current_stock_map = (
            qs.values('item_code')
            .annotate(
                total_qty=Sum('stock_qty'),
                total_value=Sum(stock_value_expr),
            )
        )

        turnover_list = []
        for item in current_stock_map:
            code      = item['item_code']
            total_qty = item['total_qty'] or 0
            out_qty   = float(out_map.get(code, 0))
            turnover_rate = (
                round(out_qty / total_qty, 4) if total_qty > 0 else None
            )
            turnover_list.append({
                'item_code':     code,
                'current_qty':   total_qty,
                'out_3m':        out_qty,
                'turnover_rate': turnover_rate,
                'stock_value':   item['total_value'] or Decimal('0'),
            })
        # 회전율 높은 순 정렬
        turnover_list.sort(
            key=lambda x: x['turnover_rate'] if x['turnover_rate'] is not None else -1,
            reverse=True,
        )

        # ── 4. 불용재고: 6개월 이상 OUT 이동 없는 품목 ───────────────── #
        # 최근 6개월 내 OUT 이동이 한 번이라도 있는 material_code 집합
        active_codes = set(
            StockMovement.objects
            .filter(
                company=request.user.company,
                movement_type='OUT',
                created_at__date__gte=six_months_ago,
            )
            .values_list('material_code', flat=True)
            .distinct()
        )

        dead_qs = qs.exclude(item_code__in=active_codes).filter(stock_qty__gt=0)
        dead_agg = dead_qs.aggregate(
            dead_item_count=Count('id'),
            dead_stock_value=Sum(stock_value_expr),
        )

        return Response({
            'as_of_date':        str(today),
            'abc_classification': abc_classification,
            'by_warehouse':      by_warehouse,
            'turnover': {
                'period_start':  str(three_months_ago),
                'period_end':    str(today),
                'items':         turnover_list,
            },
            'dead_stock': {
                'threshold_date':  str(six_months_ago),
                'item_count':      dead_agg['dead_item_count'] or 0,
                'total_value':     dead_agg['dead_stock_value'] or Decimal('0'),
            },
        })

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        창고 현황 대시보드 집계.

        Returns:
            total_warehouses: 활성 창고 수
            total_items:      전체 품목 수 (재고 레코드 수)
            low_stock_count:  부족재고 품목 수 (stock_qty <= min_stock, min_stock > 0)
        """
        qs = self.get_queryset()

        total_warehouses = Warehouse.objects.filter(
            company=request.user.company,
            is_active=True,
        ).count()

        total_items = qs.count()

        # DB 레벨에서 부족재고 필터 (is_low_stock property 동일 조건)
        # Inventory.is_low_stock: min_stock > 0 and stock_qty <= min_stock
        low_stock_count = qs.filter(
            min_stock__gt=0,
            stock_qty__lte=F('min_stock'),
        ).count()

        return Response({
            'total_warehouses': total_warehouses,
            'total_items':      total_items,
            'low_stock_count':  low_stock_count,
        })


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    재고 이동 이력 (읽기 전용).
    - company 스코프 자동 적용
    - ?search=  material_code / material_name / reference_document 검색
    - ?movement_type= / ?reference_type= / ?warehouse= 필터
    """
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    search_fields    = ['material_code', 'material_name', 'reference_document']
    ordering_fields  = ['created_at', 'movement_type', 'material_code']
    filterset_fields = ['movement_type', 'reference_type', 'warehouse']

    def get_queryset(self):
        return (
            StockMovement.objects
            .filter(company=self.request.user.company)
            .select_related('warehouse')
            .order_by('-created_at')
        )
