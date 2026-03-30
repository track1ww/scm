"""운송 경로 최적화 유틸리티

간단한 휴리스틱 기반 운송 최적화 모듈:
- Haversine 공식 기반 거리 계산
- 부피중량 고려 운임 견적
- 점수 기반 운송사 추천 (urgency 가중치 반영)
- 최근접 이웃 알고리즘(Nearest Neighbor Heuristic) TSP 근사

참고:
    Haversine formula: R. W. Sinnott, "Virtues of the Haversine", Sky and Telescope (1984)
    운임 산정: IATA 국제항공운송협회 부피중량 기준 (1 CBM = 333 kg)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_EARTH_RADIUS_KM: float = 6371.0
_VOLUMETRIC_WEIGHT_FACTOR: float = 333.0  # 1 CBM = 333 kg (IATA 기준)

# 긴급도별 (비용 가중치, 평점 가중치)
_URGENCY_WEIGHTS: Dict[str, Tuple[float, float]] = {
    "urgent": (0.3, 0.7),   # 긴급: 평점 우선
    "normal": (0.5, 0.5),   # 보통: 동일 가중치
    "economy": (0.8, 0.2),  # 경제: 비용 우선
}


# ---------------------------------------------------------------------------
# 1. 거리 계산 (Haversine)
# ---------------------------------------------------------------------------

def calculate_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Haversine 공식으로 두 GPS 좌표 간 대원거리(Great-Circle Distance)를 계산합니다.

    수식:
        a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
        c = 2 * atan2(√a, √(1−a))
        d = R * c   (R = 지구 반지름 6371 km)

    Args:
        lat1: 출발지 위도 (도, -90 ~ 90).
        lon1: 출발지 경도 (도, -180 ~ 180).
        lat2: 도착지 위도 (도, -90 ~ 90).
        lon2: 도착지 경도 (도, -180 ~ 180).

    Returns:
        두 지점 간 거리 (km), 소수점 3자리.

    Raises:
        ValueError: 위도/경도 범위를 벗어난 경우.
    """
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValueError(
            f"위도는 -90 ~ 90 사이여야 합니다. (lat1={lat1}, lat2={lat2})"
        )
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        raise ValueError(
            f"경도는 -180 ~ 180 사이여야 합니다. (lon1={lon1}, lon2={lon2})"
        )

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = _EARTH_RADIUS_KM * c

    return round(distance, 3)


# ---------------------------------------------------------------------------
# 2. 운임 견적 계산
# ---------------------------------------------------------------------------

def estimate_freight_cost(
    distance_km: float,
    weight_kg: float,
    volume_cbm: float,
    base_rate_per_km: float = 500.0,
    min_cost: float = 10000.0,
) -> float:
    """운임 견적 계산 (실중량 vs 부피중량 비교).

    부피중량 계산:
        부피중량(kg) = 부피(CBM) × 333

    과금중량 결정:
        과금중량 = max(실중량, 부피중량)

    운임 산정:
        운임 = 거리(km) × km당 기본요율 × (과금중량(kg) / 1000)
        최소 운임 적용

    Args:
        distance_km: 운송 거리 (km).
        weight_kg: 실제 중량 (kg).
        volume_cbm: 화물 부피 (CBM, Cubic Meter).
        base_rate_per_km: km당 기본 운임 (원, 기본값=500원/km).
        min_cost: 최소 운임 (원, 기본값=10,000원).

    Returns:
        견적 운임 (원), 소수점 2자리. min_cost 미만이면 min_cost 반환.

    Raises:
        ValueError: 거리, 중량, 부피가 음수인 경우.
    """
    if distance_km < 0:
        raise ValueError(f"거리는 0 이상이어야 합니다. (distance_km={distance_km})")
    if weight_kg < 0:
        raise ValueError(f"중량은 0 이상이어야 합니다. (weight_kg={weight_kg})")
    if volume_cbm < 0:
        raise ValueError(f"부피는 0 이상이어야 합니다. (volume_cbm={volume_cbm})")

    volumetric_weight_kg = volume_cbm * _VOLUMETRIC_WEIGHT_FACTOR
    chargeable_weight_kg = max(weight_kg, volumetric_weight_kg)

    cost = distance_km * base_rate_per_km * (chargeable_weight_kg / 1000.0)
    return round(max(cost, min_cost), 2)


# ---------------------------------------------------------------------------
# 3. 운송사 추천
# ---------------------------------------------------------------------------

def suggest_carriers(
    carriers: List[Dict[str, Any]],
    weight_kg: float,
    urgency: str = "normal",
) -> List[Dict[str, Any]]:
    """조건에 맞는 운송사 추천 점수 계산 및 정렬.

    점수 계산 방식:
        비용 점수 : 정규화된 비용의 역수 (낮을수록 높은 점수)
        평점 점수 : 정규화된 평균 평점 (높을수록 높은 점수)
        최종 점수 : cost_weight × 비용점수 + rating_weight × 평점점수

    긴급도별 가중치:
        urgent  : 비용 30%, 평점 70%
        normal  : 비용 50%, 평점 50%
        economy : 비용 80%, 평점 20%

    Args:
        carriers: 운송사 리스트. 각 항목은 Dict:
            id (int): 운송사 PK.
            name (str): 운송사명.
            avg_rating (float): 평균 평점 (0.0 ~ 5.0).
            avg_cost (float): 평균 운임 단가.
            max_weight_kg (float, optional): 최대 적재 중량 (kg).
        weight_kg: 화물 중량 (kg). 최대 적재량 필터링에 사용.
        urgency: 긴급도 ('urgent' | 'normal' | 'economy').

    Returns:
        점수 내림차순으로 정렬된 운송사 추천 리스트. 각 항목은 원본 Dict에
        다음 필드를 추가합니다:
            score (float): 종합 점수 (0.0 ~ 1.0).
            cost_score (float): 비용 점수.
            rating_score (float): 평점 점수.
            recommendation_rank (int): 추천 순위.

    Raises:
        ValueError: 유효하지 않은 urgency 값인 경우.
    """
    if urgency not in _URGENCY_WEIGHTS:
        raise ValueError(
            f"urgency 는 'urgent', 'normal', 'economy' 중 하나여야 합니다. "
            f"(받은 값: '{urgency}')"
        )

    if not carriers:
        return []

    cost_weight, rating_weight = _URGENCY_WEIGHTS[urgency]

    # 최대 적재량 필터링
    eligible: List[Dict[str, Any]] = []
    for carrier in carriers:
        max_weight = carrier.get("max_weight_kg")
        if max_weight is not None and weight_kg > float(max_weight):
            continue
        eligible.append(carrier)

    if not eligible:
        return []

    # 비용 및 평점 정규화를 위한 범위 추출
    costs = [float(c.get("avg_cost", 0) or 0) for c in eligible]
    ratings = [float(c.get("avg_rating", 0) or 0) for c in eligible]

    min_cost = min(costs)
    max_cost = max(costs)
    min_rating = min(ratings)
    max_rating = max(ratings)

    cost_range = max_cost - min_cost if max_cost != min_cost else 1.0
    rating_range = max_rating - min_rating if max_rating != min_rating else 1.0

    scored: List[Dict[str, Any]] = []
    for carrier in eligible:
        cost = float(carrier.get("avg_cost", 0) or 0)
        rating = float(carrier.get("avg_rating", 0) or 0)

        # 비용 점수: 낮은 비용 = 높은 점수 (0=비쌈, 1=저렴)
        cost_normalized = (cost - min_cost) / cost_range
        cost_score = 1.0 - cost_normalized

        # 평점 점수: 높은 평점 = 높은 점수 (0=낮음, 1=높음)
        rating_normalized = (rating - min_rating) / rating_range
        rating_score = rating_normalized

        total_score = cost_weight * cost_score + rating_weight * rating_score

        scored.append({
            **carrier,
            "cost_score": round(cost_score, 4),
            "rating_score": round(rating_score, 4),
            "score": round(total_score, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    for rank, item in enumerate(scored, start=1):
        item["recommendation_rank"] = rank

    return scored


# ---------------------------------------------------------------------------
# 4. 최근접 이웃 TSP 근사 (다중 배송지 경로 최적화)
# ---------------------------------------------------------------------------

def optimize_delivery_route(
    depot: Tuple[float, float],
    stops: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """최근접 이웃 알고리즘(Nearest Neighbor Heuristic)으로 배송 경로를 최적화합니다.

    알고리즘:
        1. 출발지(depot)에서 시작
        2. 미방문 배송지 중 현재 위치에서 가장 가까운 곳으로 이동
        3. 모든 배송지 방문 후 출발지로 복귀
        4. 총 이동 거리 계산

    Args:
        depot: 출발/복귀 기지 좌표 (위도, 경도).
        stops: 배송지 리스트. 각 항목은 Dict:
            id (int | str): 배송지 식별자.
            name (str): 배송지명.
            lat (float): 위도.
            lon (float): 경도.

    Returns:
        Dict containing keys:
            route (List[Dict]): 최적화된 방문 순서 리스트.
            total_distance_km (float): 총 이동 거리 (depot 복귀 포함).
            return_distance_km (float): 마지막 배송지에서 depot 복귀 거리.
            depot (Dict): 출발지 정보.

    Raises:
        ValueError: stops 가 비어있는 경우.
    """
    if not stops:
        raise ValueError("배송지 목록이 비어있습니다.")

    unvisited = [dict(s) for s in stops]
    current_lat, current_lon = depot
    route: List[Dict[str, Any]] = []
    total_distance = 0.0
    order = 1

    while unvisited:
        min_dist = float("inf")
        nearest_idx = 0

        for i, stop in enumerate(unvisited):
            dist = calculate_distance_km(
                current_lat, current_lon,
                float(stop["lat"]), float(stop["lon"]),
            )
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        nearest = unvisited.pop(nearest_idx)
        total_distance += min_dist
        route.append({
            "order": order,
            "id": nearest.get("id"),
            "name": nearest.get("name", ""),
            "lat": nearest["lat"],
            "lon": nearest["lon"],
            "distance_from_prev_km": round(min_dist, 3),
        })
        current_lat = float(nearest["lat"])
        current_lon = float(nearest["lon"])
        order += 1

    return_dist = calculate_distance_km(current_lat, current_lon, depot[0], depot[1])
    total_distance += return_dist

    return {
        "route": route,
        "total_distance_km": round(total_distance, 3),
        "return_distance_km": round(return_dist, 3),
        "depot": {"lat": depot[0], "lon": depot[1]},
    }
