"""재무 계산 유틸리티

K-GAAP/IFRS 기준 재무 계산 모듈:
- AR/AP 나이분석 (Aging Analysis)
- 고정자산 감가상각 스케줄 (정액법/정률법)
- 월별 현금흐름 예측 (Cash Flow Forecast)

참고:
    K-GAAP 기업회계기준서
    IFRS IAS 16 (유형자산)
    IFRS IAS 36 (자산손상)
"""

from __future__ import annotations

import calendar
import math
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _today() -> date:
    """오늘 날짜를 반환합니다 (테스트 시 monkeypatch 가능)."""
    return date.today()


def _round2(value: Decimal) -> Decimal:
    """소수점 2자리로 반올림합니다."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _add_months(d: date, months: int) -> date:
    """주어진 날짜에 월 수를 더합니다. 월말 오버플로우를 처리합니다."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# ---------------------------------------------------------------------------
# 1. AR/AP 나이분석 (Aging Analysis)
# ---------------------------------------------------------------------------

def calculate_aging_buckets(
    invoices: List[Dict[str, Any]],
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """채권/채무 나이분석 (Aging Analysis).

    각 청구서의 만기일(due_date)을 기준 날짜와 비교하여
    연체 구간별 금액을 집계합니다.

    버킷 정의:
        not_due    : 만기 미도래 (due_date > reference_date)
        days_0_30  : 0~30일 연체
        days_31_60 : 31~60일 연체
        days_61_90 : 61~90일 연체
        over_90    : 90일 초과 연체

    Args:
        invoices: 청구서 리스트. 각 항목은 Dict:
            amount (Decimal | float | str): 청구 금액.
            due_date (date): 만기일.
            partner (str, optional): 거래처명.
            ref (str, optional): 참조번호.
        reference_date: 기준 날짜 (기본값: 오늘).

    Returns:
        Dict containing keys:
            not_due (Decimal): 미도래 금액.
            days_0_30 (Decimal): 0~30일 연체 금액.
            days_31_60 (Decimal): 31~60일 연체 금액.
            days_61_90 (Decimal): 61~90일 연체 금액.
            over_90 (Decimal): 90일 초과 연체 금액.
            total (Decimal): 합계.
            detail (List[Dict]): 청구서별 버킷 정보.

    Raises:
        ValueError: 필수 필드(amount, due_date)가 누락된 경우.
    """
    ref = reference_date if reference_date is not None else _today()

    buckets: Dict[str, Decimal] = {
        "not_due": Decimal("0"),
        "days_0_30": Decimal("0"),
        "days_31_60": Decimal("0"),
        "days_61_90": Decimal("0"),
        "over_90": Decimal("0"),
    }
    detail: List[Dict[str, Any]] = []

    for idx, inv in enumerate(invoices):
        if "amount" not in inv or "due_date" not in inv:
            raise ValueError(
                f"invoices[{idx}] 에 'amount' 또는 'due_date' 필드가 없습니다."
            )

        amount = _round2(Decimal(str(inv["amount"])))
        due_date: date = inv["due_date"]
        partner: str = inv.get("partner", "")
        ref_no: str = inv.get("ref", "")

        days_overdue: int = (ref - due_date).days

        if days_overdue <= 0:
            bucket_key = "not_due"
        elif days_overdue <= 30:
            bucket_key = "days_0_30"
        elif days_overdue <= 60:
            bucket_key = "days_31_60"
        elif days_overdue <= 90:
            bucket_key = "days_61_90"
        else:
            bucket_key = "over_90"

        buckets[bucket_key] += amount
        detail.append({
            "partner": partner,
            "ref": ref_no,
            "amount": amount,
            "due_date": due_date,
            "days_overdue": max(days_overdue, 0),
            "bucket": bucket_key,
        })

    total = sum(buckets.values(), Decimal("0"))
    return {
        "not_due": _round2(buckets["not_due"]),
        "days_0_30": _round2(buckets["days_0_30"]),
        "days_31_60": _round2(buckets["days_31_60"]),
        "days_61_90": _round2(buckets["days_61_90"]),
        "over_90": _round2(buckets["over_90"]),
        "total": _round2(total),
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# 2. 감가상각 스케줄 - 정액법 (Straight-Line)
# ---------------------------------------------------------------------------

def calculate_straight_line_depreciation(
    acquisition_cost: Decimal,
    salvage_value: Decimal,
    useful_life_years: int,
    start_date: date,
) -> List[Dict[str, Any]]:
    """정액법(Straight-Line Method) 감가상각 스케줄 생성.

    수식:
        연간 감가상각비 = (취득원가 - 잔존가치) / 내용연수
        월 감가상각비  = 연간 감가상각비 / 12

    월별 스케줄을 생성하며, 마지막 월에는 단수 조정(rounding adjustment)을
    적용하여 장부가치가 정확히 잔존가치에 수렴합니다.

    Args:
        acquisition_cost: 취득원가.
        salvage_value: 잔존가치 (처분 시 예상 회수액).
        useful_life_years: 내용연수 (년, 1 이상).
        start_date: 자산 취득일 (감가상각 시작월 기준).

    Returns:
        월별 감가상각 스케줄 리스트. 각 항목은 Dict:
            year (int): 연도.
            month (int): 월.
            depreciation (Decimal): 당월 감가상각비.
            accumulated (Decimal): 누적 감가상각비.
            book_value (Decimal): 기말 장부가치.

    Raises:
        ValueError: 취득원가 <= 잔존가치 또는 내용연수 < 1 인 경우.
    """
    if useful_life_years < 1:
        raise ValueError("내용연수는 1년 이상이어야 합니다.")
    if acquisition_cost <= salvage_value:
        raise ValueError("취득원가는 잔존가치보다 커야 합니다.")

    depreciable_amount = acquisition_cost - salvage_value
    total_months = useful_life_years * 12
    monthly_dep = _round2(depreciable_amount / Decimal(str(total_months)))

    schedule: List[Dict[str, Any]] = []
    accumulated = Decimal("0")
    current_date = date(start_date.year, start_date.month, 1)

    for i in range(total_months):
        is_last = i == total_months - 1
        if is_last:
            # 단수 조정: 목표 누적액 = depreciable_amount
            dep = depreciable_amount - accumulated
        else:
            dep = monthly_dep

        accumulated += dep
        book_value = acquisition_cost - accumulated

        schedule.append({
            "year": current_date.year,
            "month": current_date.month,
            "depreciation": _round2(dep),
            "accumulated": _round2(accumulated),
            "book_value": _round2(book_value),
        })
        current_date = _add_months(current_date, 1)

    return schedule


# ---------------------------------------------------------------------------
# 3. 감가상각 스케줄 - 정률법 (Declining Balance)
# ---------------------------------------------------------------------------

def calculate_declining_balance_depreciation(
    acquisition_cost: Decimal,
    salvage_value: Decimal,
    useful_life_years: int,
    start_date: date,
) -> List[Dict[str, Any]]:
    """정률법(Declining Balance Method) 감가상각 스케줄 생성.

    정률(상각률) 계산:
        r = 1 - (잔존가치 / 취득원가) ^ (1 / 내용연수)

    K-GAAP 실무에서 잔존가치 = 0 인 경우 취득원가의 5%를 잔존가치로 가정하여
    상각률을 계산하고 마지막 연도에 단수 조정합니다.

    Args:
        acquisition_cost: 취득원가.
        salvage_value: 잔존가치.
        useful_life_years: 내용연수 (년).
        start_date: 자산 취득일.

    Returns:
        월별 감가상각 스케줄 리스트 (정액법과 동일한 구조).

    Raises:
        ValueError: 취득원가 <= 잔존가치 또는 내용연수 < 1 인 경우.
    """
    if useful_life_years < 1:
        raise ValueError("내용연수는 1년 이상이어야 합니다.")
    if acquisition_cost <= salvage_value:
        raise ValueError("취득원가는 잔존가치보다 커야 합니다.")

    # 잔존가치 0 처리: 수학적 계산을 위해 최소값 적용
    effective_salvage = salvage_value
    if effective_salvage == Decimal("0"):
        effective_salvage = acquisition_cost * Decimal("0.05")

    ratio_float = float(effective_salvage) / float(acquisition_cost)
    declining_rate = Decimal(
        str(1.0 - math.pow(ratio_float, 1.0 / useful_life_years))
    )
    declining_rate = declining_rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    total_months = useful_life_years * 12
    monthly_rate = declining_rate / Decimal("12")

    schedule: List[Dict[str, Any]] = []
    accumulated = Decimal("0")
    remaining_book = acquisition_cost
    current_date = date(start_date.year, start_date.month, 1)
    depreciable_amount = acquisition_cost - salvage_value

    for i in range(total_months):
        is_last = i == total_months - 1
        if is_last:
            dep = depreciable_amount - accumulated
        else:
            dep = _round2(remaining_book * monthly_rate)
            # 장부가치가 잔존가치 아래로 내려가지 않도록 제한
            max_dep = remaining_book - salvage_value
            if dep > max_dep:
                dep = max_dep

        accumulated += dep
        remaining_book = acquisition_cost - accumulated

        schedule.append({
            "year": current_date.year,
            "month": current_date.month,
            "depreciation": _round2(dep),
            "accumulated": _round2(accumulated),
            "book_value": _round2(remaining_book),
        })
        current_date = _add_months(current_date, 1)

    return schedule


# ---------------------------------------------------------------------------
# 4. 현금흐름 예측 (Cash Flow Forecast)
# ---------------------------------------------------------------------------

def forecast_cash_flow(
    opening_balance: Decimal,
    receivables: List[Dict[str, Any]],
    payables: List[Dict[str, Any]],
    periods: int = 12,
) -> List[Dict[str, Any]]:
    """월별 현금흐름 예측 (Cash Flow Forecast).

    수금 예정액(receivables)과 지급 예정액(payables)을 월별로 집계하여
    기초잔액에서 순현금흐름을 계산합니다.

    Args:
        opening_balance: 예측 시작 시점의 현금 잔액.
        receivables: 수금 예정 리스트. 각 항목은 Dict:
            amount (Decimal | float | str): 수금 예정 금액.
            expected_date (date): 수금 예정일.
            partner (str, optional): 거래처명.
        payables: 지급 예정 리스트. 각 항목은 Dict:
            amount (Decimal | float | str): 지급 예정 금액.
            expected_date (date): 지급 예정일.
            partner (str, optional): 거래처명.
        periods: 예측 기간 (월 수, 기본값=12).

    Returns:
        월별 현금흐름 리스트. 각 항목은 Dict:
            year (int): 연도.
            month (int): 월.
            inflow (Decimal): 당월 수입 (수금).
            outflow (Decimal): 당월 지출 (지급).
            net (Decimal): 순현금흐름 (inflow - outflow).
            balance (Decimal): 기말 현금잔액.

    Raises:
        ValueError: periods < 1 인 경우.
    """
    if periods < 1:
        raise ValueError("periods 는 1 이상이어야 합니다.")

    today = _today()
    start_date = date(today.year, today.month, 1)

    # 월별 집계 딕셔너리 초기화: (year, month) -> {'inflow': Decimal, 'outflow': Decimal}
    monthly: Dict[tuple, Dict[str, Decimal]] = {}
    for p in range(periods):
        period_date = _add_months(start_date, p)
        key = (period_date.year, period_date.month)
        monthly[key] = {"inflow": Decimal("0"), "outflow": Decimal("0")}

    # 수금 집계
    for rec in receivables:
        exp_date: date = rec["expected_date"]
        amount = _round2(Decimal(str(rec["amount"])))
        key = (exp_date.year, exp_date.month)
        if key in monthly:
            monthly[key]["inflow"] += amount

    # 지급 집계
    for pay in payables:
        exp_date = pay["expected_date"]
        amount = _round2(Decimal(str(pay["amount"])))
        key = (exp_date.year, exp_date.month)
        if key in monthly:
            monthly[key]["outflow"] += amount

    # 순차적 잔액 계산
    result: List[Dict[str, Any]] = []
    balance = opening_balance

    for p in range(periods):
        period_date = _add_months(start_date, p)
        key = (period_date.year, period_date.month)
        inflow = monthly[key]["inflow"]
        outflow = monthly[key]["outflow"]
        net = inflow - outflow
        balance = balance + net

        result.append({
            "year": period_date.year,
            "month": period_date.month,
            "inflow": _round2(inflow),
            "outflow": _round2(outflow),
            "net": _round2(net),
            "balance": _round2(balance),
        })

    return result
