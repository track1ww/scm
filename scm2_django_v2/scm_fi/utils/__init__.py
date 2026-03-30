"""scm_fi utils package - Financial calculation utilities."""
from .financial import (
    calculate_aging_buckets,
    calculate_straight_line_depreciation,
    calculate_declining_balance_depreciation,
    forecast_cash_flow,
)

# Aliases used by views.py
aging_buckets = calculate_aging_buckets


def calc_depreciation_schedule(asset_value, salvage_value, useful_life,
                                method='SL', start_date=None):
    """views.py 호환 래퍼."""
    from datetime import date as _date
    from decimal import Decimal as _D

    start = start_date or _date.today()
    cost  = float(asset_value)
    sal   = float(salvage_value)
    n     = int(useful_life)

    if method in ('SL', 'straight_line'):
        rows = calculate_straight_line_depreciation(
            acquisition_cost=_D(str(cost)),
            salvage_value=_D(str(sal)),
            useful_life_years=n,
            acquisition_date=start,
        )
    else:
        rows = calculate_declining_balance_depreciation(
            acquisition_cost=_D(str(cost)),
            salvage_value=_D(str(sal)),
            useful_life_years=n,
            acquisition_date=start,
        )

    # 연도별로 집계 (rows는 월별일 수 있음)
    from collections import defaultdict
    by_year = defaultdict(lambda: {'depreciation': 0, 'book_value': 0})
    for row in rows:
        yr = row.get('year') or row.get('period_year')
        if yr is None:
            continue
        by_year[yr]['depreciation'] += float(row.get('depreciation_amount', row.get('depreciation', 0)))
        by_year[yr]['book_value']    = float(row.get('book_value_after', row.get('book_value', 0)))

    return [
        {'year': yr, 'depreciation': round(v['depreciation'], 2), 'book_value': round(v['book_value'], 2)}
        for yr, v in sorted(by_year.items())
    ]


__all__ = [
    'calculate_aging_buckets', 'calculate_straight_line_depreciation',
    'calculate_declining_balance_depreciation', 'forecast_cash_flow',
    'aging_buckets', 'calc_depreciation_schedule',
]
