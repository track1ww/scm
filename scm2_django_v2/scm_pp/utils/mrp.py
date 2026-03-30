"""MRP (Material Requirements Planning) 고도화 엔진

재고 최적화 및 자재소요량계획 알고리즘:
- ABC 분류 (연간 사용금액 기준 파레토 분석)
- 재주문점 계산 (ROP)
- 경제적 주문량 (EOQ)
- 안전재고 계산 (서비스 수준 기반)
- 다단계 BOM 소요량 전개 (재귀적 폭발전개, Django ORM 연동)
- 순소요량 계산 (가용재고/입고예정 반영)

참고:
    Vollmann, T.E. et al. (2005). Manufacturing Planning and Control for Supply Chain Management.
    K-GAAP 재고자산 평가기준
"""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. ABC 분류 (순수 파이썬, Django ORM 불필요)
# ---------------------------------------------------------------------------

def calculate_abc_classification(
    materials_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """자재 ABC 분류 (연간 사용금액 기준 파레토 분석).

    ABC 분류 기준 (연간 사용금액 누적 비율):
        A 등급: 누적 80% 이하  → 고가치, 집중 관리
        B 등급: 누적 80~95%   → 중간 가치, 보통 관리
        C 등급: 누적 95% 초과 → 저가치, 간소 관리

    Args:
        materials_data: 자재 리스트. 각 항목은 Dict:
            material_code (str): 자재 코드.
            annual_usage_value (Decimal | float | str): 연간 사용금액.
            (기타 필드는 그대로 전달됨)

    Returns:
        자재별 ABC 분류 결과 리스트 (사용금액 내림차순). 각 항목은 Dict:
            material_code (str): 자재 코드.
            class (str): 분류 등급 ('A', 'B', 'C').
            annual_value (Decimal): 연간 사용금액.
            cumulative_pct (float): 누적 비율 (0.0 ~ 100.0).

    Raises:
        ValueError: materials_data 가 None 인 경우.
    """
    if materials_data is None:
        raise ValueError("materials_data 는 None 이 될 수 없습니다.")

    if not materials_data:
        return []

    # Decimal 변환 및 내림차순 정렬
    normalized: List[Dict[str, Any]] = []
    for item in materials_data:
        annual_value = Decimal(str(item.get("annual_usage_value", 0) or 0))
        normalized.append({**item, "_annual_value": annual_value})

    normalized.sort(key=lambda x: x["_annual_value"], reverse=True)

    total_value: Decimal = sum(
        (d["_annual_value"] for d in normalized), Decimal("0")
    )

    result: List[Dict[str, Any]] = []
    cumulative = Decimal("0")

    for d in normalized:
        annual_value = d["_annual_value"]
        cumulative += annual_value

        if total_value > Decimal("0"):
            cum_pct = float(cumulative / total_value * 100)
        else:
            cum_pct = 0.0

        if cum_pct <= 80.0:
            abc_class = "A"
        elif cum_pct <= 95.0:
            abc_class = "B"
        else:
            abc_class = "C"

        # 내부 임시 키 제외하고 결과 구성
        entry: Dict[str, Any] = {
            k: v for k, v in d.items() if k != "_annual_value"
        }
        entry["class"] = abc_class
        entry["annual_value"] = annual_value
        entry["cumulative_pct"] = round(cum_pct, 2)
        result.append(entry)

    return result


# ---------------------------------------------------------------------------
# 2. 재주문점 (Reorder Point)
# ---------------------------------------------------------------------------

def calculate_reorder_point(
    avg_daily_demand: float,
    lead_time_days: int,
    safety_stock: float = 0,
) -> float:
    """재주문점(ROP) 계산.

    수식:
        ROP = (평균일간수요 × 리드타임) + 안전재고

    Args:
        avg_daily_demand: 평균 일간 수요량.
        lead_time_days: 조달 리드타임 (일).
        safety_stock: 안전재고 수량 (기본값=0).

    Returns:
        재주문점 수량 (float).

    Raises:
        ValueError: avg_daily_demand 또는 lead_time_days 가 음수인 경우.
    """
    if avg_daily_demand < 0:
        raise ValueError("avg_daily_demand 는 0 이상이어야 합니다.")
    if lead_time_days < 0:
        raise ValueError("lead_time_days 는 0 이상이어야 합니다.")
    return avg_daily_demand * lead_time_days + safety_stock


# ---------------------------------------------------------------------------
# 3. 경제적 주문량 (EOQ)
# ---------------------------------------------------------------------------

def calculate_eoq(
    annual_demand: float,
    ordering_cost: float,
    holding_cost_per_unit: float,
) -> float:
    """경제적 주문량(EOQ, Economic Order Quantity) 계산.

    수식:
        EOQ = sqrt(2 × D × S / H)

        D: 연간 수요량
        S: 1회 주문비용
        H: 단위당 연간 재고유지비용

    Args:
        annual_demand: 연간 수요량 (D).
        ordering_cost: 1회 주문비용 (S).
        holding_cost_per_unit: 단위당 연간 재고유지비용 (H).

    Returns:
        경제적 주문량 (float). holding_cost_per_unit <= 0 이면 annual_demand 반환.

    Raises:
        ValueError: annual_demand 또는 ordering_cost 가 음수인 경우.
    """
    if annual_demand < 0:
        raise ValueError("annual_demand 는 0 이상이어야 합니다.")
    if ordering_cost < 0:
        raise ValueError("ordering_cost 는 0 이상이어야 합니다.")

    if holding_cost_per_unit <= 0:
        return annual_demand

    return math.sqrt(2.0 * annual_demand * ordering_cost / holding_cost_per_unit)


# ---------------------------------------------------------------------------
# 4. 안전재고 (Safety Stock)
# ---------------------------------------------------------------------------

def calculate_safety_stock(
    avg_daily_demand: float,
    std_daily_demand: float,
    avg_lead_time: float,
    std_lead_time: float,
    service_level: float = 0.95,
) -> float:
    """안전재고 계산 (서비스 수준 기반, 복합 불확실성 모델).

    수식 (수요와 리드타임 모두 불확실한 경우):
        SS = Z × sqrt(L_avg × σ_d² + d_avg² × σ_L²)

        Z       : 서비스 수준에 대응하는 정규분포 Z값
        L_avg   : 평균 리드타임 (일)
        σ_d     : 일간 수요의 표준편차
        d_avg   : 평균 일간 수요량
        σ_L     : 리드타임의 표준편차

    Z값 매핑:
        service_level < 0.90  : Z = 1.282
        service_level < 0.95  : Z = 1.645
        service_level < 0.99  : Z = 2.054
        service_level >= 0.99 : Z = 2.326

    Args:
        avg_daily_demand: 평균 일간 수요량.
        std_daily_demand: 일간 수요량의 표준편차.
        avg_lead_time: 평균 리드타임 (일).
        std_lead_time: 리드타임의 표준편차 (일).
        service_level: 목표 서비스 수준 (기본값=0.95).

    Returns:
        안전재고 수량 (float).

    Raises:
        ValueError: service_level 이 0~1 범위를 벗어난 경우.
    """
    if not (0.0 <= service_level <= 1.0):
        raise ValueError("service_level 은 0.0 ~ 1.0 사이여야 합니다.")

    if service_level < 0.90:
        z = 1.282
    elif service_level < 0.95:
        z = 1.645
    elif service_level < 0.99:
        z = 2.054
    else:
        z = 2.326

    variance = avg_lead_time * (std_daily_demand ** 2) + (avg_daily_demand ** 2) * (std_lead_time ** 2)
    return z * math.sqrt(variance)


# ---------------------------------------------------------------------------
# 5. 다단계 BOM 소요량 전개 (Django ORM 연동)
# ---------------------------------------------------------------------------

def _get_bom_with_lines(bom_id: int, company_id: int) -> Optional[Any]:
    """BOM 헤더와 라인을 ORM으로 조회합니다.

    Args:
        bom_id: BOM PK.
        company_id: 회사 PK (멀티테넌시 격리).

    Returns:
        BillOfMaterial 인스턴스 또는 None.
    """
    try:
        from scm_pp.models import BillOfMaterial
        return (
            BillOfMaterial.objects
            .prefetch_related("lines")
            .filter(id=bom_id, company_id=company_id, is_active=True)
            .first()
        )
    except Exception as exc:
        logger.warning("BOM ORM 조회 실패 (bom_id=%s): %s", bom_id, exc)
        return None


def _get_inventory_available(material_code: str, company_id: int) -> Decimal:
    """현재 가용재고(available stock)를 조회합니다."""
    try:
        from scm_mm.models import Material
        mat = Material.objects.filter(
            material_code=material_code, company_id=company_id
        ).first()
        if mat and hasattr(mat, "stock_qty"):
            return Decimal(str(mat.stock_qty))
        return Decimal("0")
    except Exception:
        return Decimal("0")


def _get_incoming_quantity(
    material_code: str,
    company_id: int,
    required_date: date,
) -> Decimal:
    """발주 잔량 또는 입고예정 수량을 조회합니다."""
    try:
        from scm_mm.models import PurchaseOrderLine
        from django.db.models import Sum
        total = (
            PurchaseOrderLine.objects
            .filter(
                material_code=material_code,
                purchase_order__company_id=company_id,
                purchase_order__status__in=["확정", "발주"],
                expected_date__lte=required_date,
            )
            .aggregate(total=Sum("remaining_qty"))
        )
        return Decimal(str(total["total"] or 0))
    except Exception:
        return Decimal("0")


def explode_bom(
    bom_id: int,
    required_qty: Decimal,
    company_id: int,
    _level: int = 0,
    _visited: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """다단계 BOM 소요량 전개 (재귀적 폭발전개, Recursive BOM Explosion).

    최상위 BOM 부터 하위 구성품까지 재귀적으로 소요량을 전개합니다.
    순환 참조(circular BOM) 방지를 위해 방문한 BOM ID를 추적합니다.

    스크랩율(scrap_rate) 반영:
        실소요량 = 이론소요량 / (1 - scrap_rate/100)

    Args:
        bom_id: 전개할 BOM PK.
        required_qty: 완제품 생산 수량.
        company_id: 회사 PK.
        _level: 현재 BOM 레벨 (내부 재귀용).
        _visited: 순환참조 방지 집합 (내부 재귀용).

    Returns:
        소요량 리스트. 각 항목은 Dict:
            material_code (str): 자재 코드.
            material_name (str): 자재명.
            required_qty (Decimal): 실소요량 (스크랩율 반영).
            unit (str): 단위.
            level (int): BOM 레벨 (0=최상위 구성품).
            bom_id (int): 원본 BOM ID.
    """
    if _visited is None:
        _visited = set()

    if bom_id in _visited:
        logger.warning("순환 BOM 참조 감지됨: bom_id=%s", bom_id)
        return []
    _visited.add(bom_id)

    bom = _get_bom_with_lines(bom_id, company_id)
    if bom is None:
        return []

    result: List[Dict[str, Any]] = []

    for line in bom.lines.all():
        scrap_rate = Decimal(str(line.scrap_rate)) / Decimal("100")
        if scrap_rate >= Decimal("1"):
            scrap_rate = Decimal("0")

        if scrap_rate > Decimal("0"):
            line_req = (
                (required_qty * Decimal(str(line.quantity))) / (Decimal("1") - scrap_rate)
            )
        else:
            line_req = required_qty * Decimal(str(line.quantity))

        line_req = line_req.quantize(Decimal("0.001"))

        result.append({
            "material_code": line.material_code,
            "material_name": line.material_name,
            "required_qty": line_req,
            "unit": line.unit,
            "level": _level,
            "bom_id": bom_id,
        })

        # 하위 BOM 조회 시도
        try:
            from scm_pp.models import BillOfMaterial
            sub_bom = BillOfMaterial.objects.filter(
                bom_code=line.material_code,
                company_id=company_id,
                is_active=True,
            ).first()
            if sub_bom and sub_bom.id != bom_id:
                sub_items = explode_bom(
                    sub_bom.id,
                    line_req,
                    company_id,
                    _level=_level + 1,
                    _visited=_visited,
                )
                result.extend(sub_items)
        except Exception as exc:
            logger.debug(
                "하위 BOM 조회 실패 (material_code=%s): %s", line.material_code, exc
            )

    return result


# ---------------------------------------------------------------------------
# 6. 순소요량 계산
# ---------------------------------------------------------------------------

def calculate_net_requirements(
    material_id: int,
    gross_requirement: Decimal,
    company_id: int,
    required_date: date,
) -> Dict[str, Any]:
    """순소요량 계산 (Net Requirements Calculation).

    수식:
        순소요량 = 총소요량 - 가용재고 - 입고예정량
        순소요량이 0 이하이면 0으로 처리 (재고 여유)

    발주일 계산:
        발주일 = 필요일 - 리드타임(일)
        발주일이 오늘 이전이면 오늘로 설정 (긴급발주)

    Args:
        material_id: 자재 PK.
        gross_requirement: 총소요량.
        company_id: 회사 PK.
        required_date: 자재 필요일.

    Returns:
        Dict containing keys:
            material_id (int): 자재 PK.
            material_code (str): 자재 코드.
            gross (Decimal): 총소요량.
            available (Decimal): 가용재고.
            incoming (Decimal): 입고예정량.
            net (Decimal): 순소요량.
            order_date (date): 권장 발주일.
            lead_time_days (int): 리드타임.
            is_urgent (bool): 긴급발주 여부.
    """
    material_code = str(material_id)
    lead_time_days = 7  # 기본값

    try:
        from scm_mm.models import Material
        mat = Material.objects.filter(id=material_id, company_id=company_id).first()
        if mat:
            material_code = mat.material_code
            if hasattr(mat, "lead_time_days") and mat.lead_time_days:
                lead_time_days = int(mat.lead_time_days)
    except Exception:
        pass

    available = _get_inventory_available(material_code, company_id)
    incoming = _get_incoming_quantity(material_code, company_id, required_date)

    net = gross_requirement - available - incoming
    net = max(net, Decimal("0"))

    order_date = required_date - timedelta(days=lead_time_days)
    today = date.today()
    is_urgent = order_date < today
    if is_urgent:
        order_date = today

    return {
        "material_id": material_id,
        "material_code": material_code,
        "gross": gross_requirement.quantize(Decimal("0.001")),
        "available": available.quantize(Decimal("0.001")),
        "incoming": incoming.quantize(Decimal("0.001")),
        "net": net.quantize(Decimal("0.001")),
        "order_date": order_date,
        "lead_time_days": lead_time_days,
        "is_urgent": is_urgent,
    }
