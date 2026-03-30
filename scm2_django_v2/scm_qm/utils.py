"""
scm_qm.utils — SPC (Statistical Process Control) 알고리즘

주요 함수:
    calc_control_limits(values, usl, lsl)  → X-bar / R 관리한계 + 공정능력 지수
    classify_spc_points(values, ucl, lcl)  → 관리이탈 포인트 감지 (Nelson 규칙 1·2·3)
    calc_process_capability(values, usl, lsl) → Cp, Cpk, Cpm
"""
import math
import statistics
from typing import Optional

# ─── 상수 ────────────────────────────────────────────────────────
# A2, D3, D4 계수 (부분군 크기 2~10)
_CONSTANTS = {
    2:  {'A2': 1.880, 'D3': 0,     'D4': 3.267},
    3:  {'A2': 1.023, 'D3': 0,     'D4': 2.574},
    4:  {'A2': 0.729, 'D3': 0,     'D4': 2.282},
    5:  {'A2': 0.577, 'D3': 0,     'D4': 2.114},
    6:  {'A2': 0.483, 'D3': 0,     'D4': 2.004},
    7:  {'A2': 0.419, 'D3': 0.076, 'D4': 1.924},
    8:  {'A2': 0.373, 'D3': 0.136, 'D4': 1.864},
    9:  {'A2': 0.337, 'D3': 0.184, 'D4': 1.816},
    10: {'A2': 0.308, 'D3': 0.223, 'D4': 1.777},
}


def calc_process_capability(
    values: list,
    usl: Optional[float],
    lsl: Optional[float],
    target: Optional[float] = None,
) -> dict:
    """
    공정능력 지수 계산.

    Args:
        values: 측정값 리스트 (float)
        usl:    규격 상한 (Upper Spec Limit)
        lsl:    규격 하한 (Lower Spec Limit)
        target: 목표값 (Cpm 계산용, 없으면 (usl+lsl)/2)

    Returns:
        {
            mean, std, n,
            cp, cpl, cpu, cpk,
            cpm (target 있을 때),
        }
    """
    if not values or len(values) < 2:
        return {'error': '데이터가 충분하지 않습니다 (최소 2개)'}

    floats = [float(v) for v in values]
    n      = len(floats)
    mean   = statistics.mean(floats)
    std    = statistics.stdev(floats)

    result: dict = {'mean': round(mean, 6), 'std': round(std, 6), 'n': n}

    if std == 0:
        result['error'] = '표준편차가 0입니다'
        return result

    if usl is not None and lsl is not None:
        cp  = (float(usl) - float(lsl)) / (6 * std)
        result['cp'] = round(cp, 4)

    if usl is not None:
        cpu = (float(usl) - mean) / (3 * std)
        result['cpu'] = round(cpu, 4)

    if lsl is not None:
        cpl = (mean - float(lsl)) / (3 * std)
        result['cpl'] = round(cpl, 4)

    if 'cpu' in result and 'cpl' in result:
        result['cpk'] = round(min(result['cpu'], result['cpl']), 4)
    elif 'cpu' in result:
        result['cpk'] = result['cpu']
    elif 'cpl' in result:
        result['cpk'] = result['cpl']

    # Cpm (Taguchi)
    if usl is not None and lsl is not None:
        t = float(target) if target is not None else (float(usl) + float(lsl)) / 2
        tau = math.sqrt(std ** 2 + (mean - t) ** 2)
        cpm = (float(usl) - float(lsl)) / (6 * tau) if tau > 0 else None
        if cpm is not None:
            result['cpm']    = round(cpm, 4)
            result['target'] = t

    return result


def calc_control_limits(values: list, subgroup_size: int = 1) -> dict:
    """
    X-bar 또는 I-MR 관리도 한계선 계산.

    subgroup_size=1 : I (Individual) + MR 차트
    subgroup_size>=2: X-bar + R 차트 (부분군 묶기 포함)

    Returns:
        {
            chart_type,
            x_bar, ucl_x, lcl_x,
            r_bar, ucl_r, lcl_r,
            subgroups (X-bar, R 리스트),
        }
    """
    if not values or len(values) < 2:
        return {'error': '데이터 부족 (최소 2개)'}

    floats = [float(v) for v in values]

    if subgroup_size == 1:
        # I-MR 차트
        moving_ranges = [abs(floats[i] - floats[i-1]) for i in range(1, len(floats))]
        x_bar = statistics.mean(floats)
        mr_bar = statistics.mean(moving_ranges)
        d2 = 1.128  # 부분군 크기 2의 d2 계수
        e2 = 2.660
        ucl_x = x_bar + e2 * mr_bar
        lcl_x = x_bar - e2 * mr_bar
        d4 = 3.267
        ucl_r = d4 * mr_bar
        return {
            'chart_type': 'I-MR',
            'x_bar':  round(x_bar,  6),
            'ucl_x':  round(ucl_x,  6),
            'lcl_x':  round(max(lcl_x, 0) if lcl_x < 0 else lcl_x, 6),
            'mr_bar': round(mr_bar, 6),
            'ucl_r':  round(ucl_r,  6),
            'lcl_r':  0,
            'individuals': floats,
            'moving_ranges': moving_ranges,
        }

    # X-bar R 차트
    n = subgroup_size
    consts = _CONSTANTS.get(n, _CONSTANTS[10])
    A2, D3, D4 = consts['A2'], consts['D3'], consts['D4']

    # 부분군 분할
    subgroups = [
        floats[i:i+n] for i in range(0, len(floats), n)
        if len(floats[i:i+n]) == n
    ]
    if not subgroups:
        return {'error': '유효한 부분군 없음'}

    xbars = [statistics.mean(sg) for sg in subgroups]
    ranges = [max(sg) - min(sg) for sg in subgroups]
    x_bar = statistics.mean(xbars)
    r_bar = statistics.mean(ranges)

    ucl_x = x_bar + A2 * r_bar
    lcl_x = x_bar - A2 * r_bar
    ucl_r = D4 * r_bar
    lcl_r = D3 * r_bar

    return {
        'chart_type': 'X-bar R',
        'x_bar':  round(x_bar, 6),
        'ucl_x':  round(ucl_x, 6),
        'lcl_x':  round(lcl_x, 6),
        'r_bar':  round(r_bar, 6),
        'ucl_r':  round(ucl_r, 6),
        'lcl_r':  round(lcl_r, 6),
        'subgroup_size': n,
        'subgroup_count': len(subgroups),
        'xbars':  [round(x, 6) for x in xbars],
        'ranges': [round(r, 6) for r in ranges],
    }


def classify_spc_points(values: list, ucl: float, lcl: float, center: float) -> list:
    """
    Nelson 규칙 1·2·3 기반 관리이탈 포인트 감지.

    규칙 1: UCL/LCL 벗어남
    규칙 2: 연속 9점 중심선 한 쪽
    규칙 3: 연속 6점 단조 증가/감소

    Returns:
        list of {'index': int, 'value': float, 'rules': [1,2,3]}
    """
    floats = [float(v) for v in values]
    n      = len(floats)
    flags  = [set() for _ in range(n)]

    # 규칙 1
    for i, v in enumerate(floats):
        if v > ucl or v < lcl:
            flags[i].add(1)

    # 규칙 2: 연속 9점 중심선 한 쪽
    for i in range(8, n):
        window = floats[i-8:i+1]
        if all(v > center for v in window) or all(v < center for v in window):
            for j in range(i-8, i+1):
                flags[j].add(2)

    # 규칙 3: 연속 6점 단조 증가/감소
    for i in range(5, n):
        window = floats[i-5:i+1]
        if all(window[k] < window[k+1] for k in range(5)):
            for j in range(i-5, i+1):
                flags[j].add(3)
        elif all(window[k] > window[k+1] for k in range(5)):
            for j in range(i-5, i+1):
                flags[j].add(3)

    return [
        {'index': i, 'value': floats[i], 'rules': sorted(flags[i])}
        for i in range(n)
        if flags[i]
    ]
