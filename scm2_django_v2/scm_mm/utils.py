"""
scm_mm.utils — MRP / 구매 계획 알고리즘 유틸리티

주요 함수:
    calc_eoq(demand, order_cost, holding_cost)
        → Economic Order Quantity (경제적 주문량)

    calc_safety_stock(demand_std, lead_time, service_level)
        → 안전재고 (정규분포 기반)

    calc_reorder_point(avg_demand, lead_time, safety_stock)
        → 재주문점

    run_mrp(bom_tree, demand_schedule, inventory_map, lead_time_map)
        → 자재 소요량 계획 (MRP) — 기간별 순소요량 / 발주계획 산출

    classify_abc(items, value_field, qty_field)
        → ABC 분류 (파레토 원칙: A=상위80%, B=15%, C=5%)
"""
from __future__ import annotations

import math
from collections import defaultdict
from decimal import Decimal
from typing import Any


# ─── EOQ ─────────────────────────────────────────────────────────────────────

def calc_eoq(
    annual_demand:  float,
    order_cost:     float,
    holding_cost:   float,
) -> dict:
    """
    Wilson EOQ 공식.

    Args:
        annual_demand: 연간 수요량
        order_cost:    1회 발주비용
        holding_cost:  단위당 연간 보관비용

    Returns:
        {'eoq': float, 'annual_orders': float, 'cycle_days': float}
    """
    if holding_cost <= 0:
        return {'error': '보관비용은 0보다 커야 합니다'}
    eoq = math.sqrt((2 * annual_demand * order_cost) / holding_cost)
    annual_orders = annual_demand / eoq if eoq > 0 else 0
    cycle_days    = 365 / annual_orders if annual_orders > 0 else 0
    return {
        'eoq':           round(eoq, 2),
        'annual_orders': round(annual_orders, 2),
        'cycle_days':    round(cycle_days, 1),
    }


# ─── Safety Stock ─────────────────────────────────────────────────────────────

# 서비스 수준 → Z-score 매핑
_Z_SCORES = {
    0.90: 1.282,
    0.95: 1.645,
    0.97: 1.881,
    0.98: 2.054,
    0.99: 2.326,
}


def calc_safety_stock(
    demand_std:    float,
    lead_time:     float,
    service_level: float = 0.95,
) -> dict:
    """
    안전재고 계산 (수요 변동성 기반).

    Args:
        demand_std:    수요 표준편차 (1기간)
        lead_time:     조달 리드타임 (기간 수)
        service_level: 서비스 수준 (0~1, 기본 95%)

    Returns:
        {'z': float, 'safety_stock': float, 'service_level': float}
    """
    z = _Z_SCORES.get(service_level)
    if z is None:
        # 가장 가까운 Z 사용
        closest = min(_Z_SCORES, key=lambda k: abs(k - service_level))
        z = _Z_SCORES[closest]

    ss = z * demand_std * math.sqrt(lead_time)
    return {
        'z':             round(z,  3),
        'safety_stock':  round(ss, 2),
        'service_level': service_level,
    }


# ─── Reorder Point ────────────────────────────────────────────────────────────

def calc_reorder_point(
    avg_demand:    float,
    lead_time:     float,
    safety_stock:  float = 0,
) -> dict:
    """
    재주문점 (ROP) 계산.

    ROP = 평균수요 × 리드타임 + 안전재고

    Returns:
        {'rop': float, 'lead_time_demand': float, 'safety_stock': float}
    """
    ltd = avg_demand * lead_time
    rop = ltd + safety_stock
    return {
        'rop':               round(rop, 2),
        'lead_time_demand':  round(ltd, 2),
        'safety_stock':      round(safety_stock, 2),
    }


# ─── MRP ─────────────────────────────────────────────────────────────────────

def run_mrp(
    gross_requirements: dict[str, dict[int, float]],
    inventory_map:      dict[str, float],
    lead_time_map:      dict[str, int],
    lot_size_map:       dict[str, float] | None = None,
    periods:            int = 8,
) -> dict[str, list[dict]]:
    """
    단순 MRP 계산 (독립품목 수준, BOM 확장 없이).

    Args:
        gross_requirements: {material_code: {period: qty}} — 총소요량
        inventory_map:      {material_code: current_qty}    — 현재 재고
        lead_time_map:      {material_code: periods}        — 리드타임 (기간)
        lot_size_map:       {material_code: lot_size}       — 로트 크기 (없으면 1)
        periods:            계획 기간 수

    Returns:
        {material_code: [
            {
                'period': int,
                'gross_req': float,
                'scheduled_receipt': float,
                'projected_oh': float,
                'net_req': float,
                'planned_order_receipt': float,
                'planned_order_release': float,
            },
            ...
        ]}
    """
    result: dict[str, list[dict]] = {}

    for mat_code, reqs in gross_requirements.items():
        lt       = lead_time_map.get(mat_code, 1)
        lot_size = (lot_size_map or {}).get(mat_code, 1)
        on_hand  = float(inventory_map.get(mat_code, 0))
        schedule = []

        for p in range(1, periods + 1):
            gross   = float(reqs.get(p, 0))
            net_req = max(gross - on_hand, 0)

            # 로트 크기 단위로 올림
            if net_req > 0 and lot_size > 0:
                planned_receipt = math.ceil(net_req / lot_size) * lot_size
            else:
                planned_receipt = 0

            release_period = p - lt

            on_hand = on_hand + planned_receipt - gross
            on_hand = max(on_hand, 0)

            schedule.append({
                'period':                 p,
                'gross_req':              round(gross,           2),
                'projected_oh':           round(on_hand,         2),
                'net_req':                round(net_req,         2),
                'planned_order_receipt':  round(planned_receipt, 2),
                'planned_order_release':  round(planned_receipt, 2) if release_period >= 1 else 0,
                'planned_order_release_period': release_period,
            })

        result[mat_code] = schedule

    return result


# ─── ABC 분류 ─────────────────────────────────────────────────────────────────

def classify_abc(
    items: list[dict],
    value_field: str = 'annual_value',
    code_field:  str = 'material_code',
) -> list[dict]:
    """
    ABC 분류 (파레토 원칙).

    Args:
        items:       [{'material_code': str, 'annual_value': float, ...}, ...]
        value_field: 금액/가치 필드명
        code_field:  품목코드 필드명

    Returns:
        items with 'abc_class' ('A'|'B'|'C') and 'cumulative_pct' added
    """
    if not items:
        return []

    sorted_items = sorted(items, key=lambda x: float(x.get(value_field, 0)), reverse=True)
    total = sum(float(i.get(value_field, 0)) for i in sorted_items)

    if total == 0:
        for item in sorted_items:
            item['abc_class'] = 'C'
            item['cumulative_pct'] = 0
        return sorted_items

    cumulative = 0.0
    result = []
    for item in sorted_items:
        val = float(item.get(value_field, 0))
        cumulative += val
        pct = cumulative / total * 100
        cls = 'A' if pct <= 80 else ('B' if pct <= 95 else 'C')
        result.append({**item, 'abc_class': cls, 'cumulative_pct': round(pct, 2)})

    return result
