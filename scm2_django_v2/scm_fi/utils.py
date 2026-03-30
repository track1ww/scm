"""
scm_fi.utils — 재무 알고리즘 유틸리티

주요 함수:
    aging_buckets(records, date_field, amount_field, as_of)
        → AR/AP 5구간 나이분석 집계

    calc_depreciation_schedule(asset_value, salvage_value, useful_life,
                               method, start_date)
        → 감가상각 스케줄 (SL/DB/SYD)

    budget_variance(budget_amount, actual_amount)
        → 예산 vs 실적 차이 분석
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any


# ─── AR/AP Aging ─────────────────────────────────────────────────────────────

def aging_buckets(
    records: list[dict],
    date_field: str,
    amount_field: str,
    as_of: date | None = None,
) -> dict:
    """
    채권/채무 나이분석 — 5구간 집계.

    Args:
        records:      {'due_date': ..., 'amount': ..., ...} 딕셔너리 리스트
        date_field:   만기일 필드명 (기본 'due_date')
        amount_field: 금액 필드명 (기본 'amount')
        as_of:        기준일 (없으면 오늘)

    Returns:
        {
            'as_of': str,
            'buckets': {
                'not_due':  {'count': int, 'amount': Decimal},
                '0_30':     {...},
                '31_60':    {...},
                '61_90':    {...},
                'over_90':  {...},
            },
            'total': {'count': int, 'amount': Decimal},
        }
    """
    as_of = as_of or date.today()

    buckets: dict[str, dict] = {
        'not_due': {'count': 0, 'amount': Decimal('0')},
        '0_30':    {'count': 0, 'amount': Decimal('0')},
        '31_60':   {'count': 0, 'amount': Decimal('0')},
        '61_90':   {'count': 0, 'amount': Decimal('0')},
        'over_90': {'count': 0, 'amount': Decimal('0')},
    }

    for rec in records:
        raw_date   = rec.get(date_field)
        raw_amount = rec.get(amount_field, 0)

        if raw_date is None:
            continue

        # date 정규화
        if isinstance(raw_date, str):
            raw_date = date.fromisoformat(raw_date[:10])

        amount = Decimal(str(raw_amount))
        days_overdue = (as_of - raw_date).days

        if days_overdue < 0:
            key = 'not_due'
        elif days_overdue <= 30:
            key = '0_30'
        elif days_overdue <= 60:
            key = '31_60'
        elif days_overdue <= 90:
            key = '61_90'
        else:
            key = 'over_90'

        buckets[key]['count']  += 1
        buckets[key]['amount'] += amount

    total_count  = sum(b['count']  for b in buckets.values())
    total_amount = sum(b['amount'] for b in buckets.values())

    return {
        'as_of':   str(as_of),
        'buckets': buckets,
        'total':   {'count': total_count, 'amount': total_amount},
    }


# ─── 감가상각 ─────────────────────────────────────────────────────────────────

def calc_depreciation_schedule(
    asset_value:  float | Decimal,
    salvage_value: float | Decimal,
    useful_life:  int,
    method:       str = 'SL',
    start_date:   date | None = None,
) -> list[dict]:
    """
    감가상각 스케줄 계산.

    Args:
        asset_value:   취득원가
        salvage_value: 잔존가치
        useful_life:   내용연수 (년)
        method:        'SL' (정액), 'DB' (정률), 'SYD' (연수합계)
        start_date:    취득일 (없으면 오늘)

    Returns:
        연도별 스케줄 리스트:
        [{'year': 1, 'depreciation': ..., 'book_value': ..., 'date': 'YYYY-MM-DD'}, ...]
    """
    cost     = Decimal(str(asset_value))
    salvage  = Decimal(str(salvage_value))
    n        = int(useful_life)
    start    = start_date or date.today()
    schedule = []
    book_val = cost

    if method == 'SL':
        annual_dep = (cost - salvage) / n
        for yr in range(1, n + 1):
            dep       = annual_dep
            book_val -= dep
            schedule.append({
                'year':         yr,
                'depreciation': round(dep,      2),
                'book_value':   round(book_val, 2),
                'date':         str(start.replace(year=start.year + yr)),
            })

    elif method == 'DB':
        # 정률법: rate = 1 - (salvage/cost)^(1/n)
        if cost > 0 and salvage > 0:
            rate = Decimal(str(1 - (float(salvage) / float(cost)) ** (1.0 / n)))
        else:
            rate = Decimal('2') / Decimal(str(n))  # 이중체감법 fallback
        for yr in range(1, n + 1):
            dep = book_val * rate
            if yr == n:
                dep = book_val - salvage
            book_val -= dep
            schedule.append({
                'year':         yr,
                'depreciation': round(dep,      2),
                'book_value':   round(book_val, 2),
                'date':         str(start.replace(year=start.year + yr)),
            })

    elif method == 'SYD':
        # 연수합계법: SYD = n*(n+1)/2
        syd = n * (n + 1) / 2
        depreciable = cost - salvage
        for yr in range(1, n + 1):
            fraction = Decimal(str((n - yr + 1) / syd))
            dep      = depreciable * fraction
            book_val -= dep
            schedule.append({
                'year':         yr,
                'depreciation': round(dep,      2),
                'book_value':   round(book_val, 2),
                'date':         str(start.replace(year=start.year + yr)),
            })

    return schedule


# ─── 예산 차이 분석 ───────────────────────────────────────────────────────────

def budget_variance(budget_amount: float | Decimal, actual_amount: float | Decimal) -> dict:
    """
    예산 vs 실적 차이 분석.

    Returns:
        {
            budget, actual,
            variance (actual - budget),
            variance_pct (%),
            status: 'over' | 'under' | 'on_target',
        }
    """
    b = Decimal(str(budget_amount))
    a = Decimal(str(actual_amount))
    v = a - b
    pct = (v / b * 100) if b != 0 else Decimal('0')

    if abs(pct) <= 5:
        status = 'on_target'
    elif v > 0:
        status = 'over'
    else:
        status = 'under'

    return {
        'budget':       round(b,   2),
        'actual':       round(a,   2),
        'variance':     round(v,   2),
        'variance_pct': round(pct, 2),
        'status':       status,
    }
