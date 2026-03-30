"""SPC (Statistical Process Control) 유틸리티

공정관리를 위한 통계적 계산 모듈:
- Cpk (공정능력지수) 계산
- X-bar/R 관리도 데이터 계산
- 관리한계선(UCL/LCL) 계산
- Western Electric 이상 규칙 탐지
- 이동범위(Moving Range) 계산

참고:
    Montgomery, D.C. (2020). Introduction to Statistical Quality Control (8th ed.)
    AIAG SPC Manual (2nd ed.)
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# AIAG SPC Manual Table: d2, D3, D4, A2 상수 (서브그룹 크기 n=2..10)
# ---------------------------------------------------------------------------
_D2: Dict[int, float] = {
    2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
    6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078,
}

_D3: Dict[int, float] = {
    2: 0.000, 3: 0.000, 4: 0.000, 5: 0.000,
    6: 0.000, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223,
}

_D4: Dict[int, float] = {
    2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114,
    6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777,
}

_A2: Dict[int, float] = {
    2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577,
    6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308,
}

# 개별값 관리도(n=1)용 상수
_D2_INDIVIDUAL: float = 1.128
_D4_INDIVIDUAL: float = 3.267
_D3_INDIVIDUAL: float = 0.000


def calculate_cpk(
    values: List[float],
    usl: float,
    lsl: float,
) -> Dict[str, float]:
    """공정능력지수 Cp, Cpk, Cpl, Cpu 계산.

    수식:
        sigma = 표준편차 (표본)
        Cp    = (USL - LSL) / (6 * sigma)
        Cpu   = (USL - mean) / (3 * sigma)
        Cpl   = (mean - LSL) / (3 * sigma)
        Cpk   = min(Cpu, Cpl)

    판정 기준:
        Cpk >= 1.67 : 탁월 (excellent)
        Cpk >= 1.33 : 우수 (capable)
        Cpk >= 1.00 : 양호 (marginal)
        Cpk <  1.00 : 불량 (incapable)

    Args:
        values: 측정값 리스트 (최소 2개 이상).
        usl: 상한 규격한계 (Upper Specification Limit).
        lsl: 하한 규격한계 (Lower Specification Limit).

    Returns:
        Dict containing keys:
            mean (float): 평균.
            std (float): 표본 표준편차.
            cp (float): 공정능력 Cp.
            cpu (float): 상한 공정능력 Cpu.
            cpl (float): 하한 공정능력 Cpl.
            cpk (float): 공정능력지수 Cpk.
            judgment (str): 판정 문자열.

    Raises:
        ValueError: values 개수가 2 미만이거나 USL <= LSL 인 경우.
    """
    if len(values) < 2:
        raise ValueError("values 는 최소 2개 이상이어야 합니다.")
    if usl <= lsl:
        raise ValueError(f"USL({usl}) 은 LSL({lsl}) 보다 커야 합니다.")

    mean_val: float = statistics.mean(values)
    std_val: float = statistics.stdev(values)  # 표본 표준편차 (n-1)

    if std_val == 0.0:
        cp = cpu = cpl = cpk = float("inf")
    else:
        cp = (usl - lsl) / (6.0 * std_val)
        cpu = (usl - mean_val) / (3.0 * std_val)
        cpl = (mean_val - lsl) / (3.0 * std_val)
        cpk = min(cpu, cpl)

    if cpk == float("inf"):
        judgment = "탁월"
    elif cpk >= 1.67:
        judgment = "탁월"
    elif cpk >= 1.33:
        judgment = "우수"
    elif cpk >= 1.00:
        judgment = "양호"
    else:
        judgment = "불량"

    return {
        "mean": round(mean_val, 6),
        "std": round(std_val, 6),
        "cp": round(cp, 4) if cp != float("inf") else cp,
        "cpu": round(cpu, 4) if cpu != float("inf") else cpu,
        "cpl": round(cpl, 4) if cpl != float("inf") else cpl,
        "cpk": round(cpk, 4) if cpk != float("inf") else cpk,
        "judgment": judgment,
    }


def calculate_control_limits(
    values: List[float],
    subgroup_size: int = 1,
) -> Dict[str, float]:
    """X-bar 관리도 및 R 관리도의 관리한계선(UCL/CL/LCL) 계산.

    subgroup_size == 1 인 경우 개별값-이동범위(I-MR) 관리도를 사용합니다.
    subgroup_size >= 2 인 경우 X-bar R 관리도를 사용합니다.

    I-MR 관리도 수식 (n=1):
        X_bar  = 전체 평균
        MR_bar = 이동범위 평균
        sigma  = MR_bar / d2  (d2=1.128)
        UCL_X  = X_bar + 3 * sigma
        LCL_X  = X_bar - 3 * sigma
        UCL_MR = D4 * MR_bar  (D4=3.267)

    X-bar 관리도 수식 (서브그룹):
        X_double_bar = 서브그룹 평균의 평균
        R_bar        = 서브그룹 범위의 평균
        UCL_Xbar     = X_double_bar + A2 * R_bar
        LCL_Xbar     = X_double_bar - A2 * R_bar
        UCL_R        = D4 * R_bar
        LCL_R        = D3 * R_bar

    Args:
        values: 측정값 리스트.
        subgroup_size: 서브그룹 크기 (기본값=1, 개별값 관리도).

    Returns:
        Dict containing keys:
            cl (float): 중심선.
            ucl (float): 상한 관리한계.
            lcl (float): 하한 관리한계.
            sigma (float): 추정 공정 표준편차.
            r_bar (float): 범위 평균 (또는 MR bar).
            ucl_r (float): R 관리도 UCL.
            lcl_r (float): R 관리도 LCL.
            chart_type (str): 'I-MR' 또는 'Xbar-R'.

    Raises:
        ValueError: 데이터 부족 또는 지원되지 않는 서브그룹 크기.
    """
    n = subgroup_size
    if n not in range(1, 11):
        raise ValueError("subgroup_size 는 1 ~ 10 사이여야 합니다.")
    if len(values) < 2:
        raise ValueError("values 는 최소 2개 이상이어야 합니다.")

    if n == 1:
        # I-MR 관리도
        moving_ranges = calculate_moving_range(values)
        x_bar = statistics.mean(values)
        mr_bar = statistics.mean(moving_ranges) if moving_ranges else 0.0
        sigma = mr_bar / _D2_INDIVIDUAL if mr_bar > 0 else 0.0
        ucl = x_bar + 3.0 * sigma
        lcl = x_bar - 3.0 * sigma
        ucl_r = _D4_INDIVIDUAL * mr_bar
        lcl_r = _D3_INDIVIDUAL * mr_bar
        return {
            "cl": round(x_bar, 6),
            "ucl": round(ucl, 6),
            "lcl": round(lcl, 6),
            "sigma": round(sigma, 6),
            "r_bar": round(mr_bar, 6),
            "ucl_r": round(ucl_r, 6),
            "lcl_r": round(lcl_r, 6),
            "chart_type": "I-MR",
        }
    else:
        # X-bar R 관리도: values 를 서브그룹으로 분할
        subgroups: List[List[float]] = []
        for i in range(0, len(values) - n + 1, n):
            subgroups.append(values[i: i + n])

        if not subgroups:
            raise ValueError("서브그룹을 구성하기에 데이터가 부족합니다.")

        subgroup_means = [statistics.mean(sg) for sg in subgroups]
        subgroup_ranges = [max(sg) - min(sg) for sg in subgroups]

        x_double_bar = statistics.mean(subgroup_means)
        r_bar = statistics.mean(subgroup_ranges)
        sigma = r_bar / _D2[n] if r_bar > 0 else 0.0

        a2 = _A2[n]
        ucl = x_double_bar + a2 * r_bar
        lcl = x_double_bar - a2 * r_bar
        ucl_r = _D4[n] * r_bar
        lcl_r = _D3[n] * r_bar

        return {
            "cl": round(x_double_bar, 6),
            "ucl": round(ucl, 6),
            "lcl": round(lcl, 6),
            "sigma": round(sigma, 6),
            "r_bar": round(r_bar, 6),
            "ucl_r": round(ucl_r, 6),
            "lcl_r": round(lcl_r, 6),
            "chart_type": "Xbar-R",
        }


def detect_out_of_control(
    values: List[float],
    ucl: float,
    lcl: float,
    cl: float,
) -> List[Dict[str, Any]]:
    """Western Electric 이상 규칙(Rule 1~4) 탐지.

    탐지 규칙:
        Rule 1: 관리한계(UCL/LCL) 외부 점 1개 이상.
        Rule 2: 연속 9점이 모두 중심선(CL)의 같은 쪽에 위치.
        Rule 3: 연속 6점이 단조 증가 또는 단조 감소.
        Rule 4: 연속 14점이 교대로 증감 (지그재그).

    Args:
        values: 측정값 리스트 (시계열 순서).
        ucl: 상한 관리한계.
        lcl: 하한 관리한계.
        cl: 중심선 (평균).

    Returns:
        위반 점들의 리스트. 각 항목은 Dict:
            index (int): 위반 시작 인덱스 (0-based).
            value (float): 해당 측정값.
            rule (int): 위반된 규칙 번호 (1~4).
            rule_description (str): 규칙 설명.
    """
    violations: List[Dict[str, Any]] = []
    n = len(values)

    # Rule 1: 관리한계 외부 점
    for i, v in enumerate(values):
        if v > ucl or v < lcl:
            violations.append({
                "index": i,
                "value": v,
                "rule": 1,
                "rule_description": "Rule 1: 관리한계 외부 점",
            })

    # Rule 2: 연속 9점이 중심선 한쪽
    run_len = 9
    if n >= run_len:
        for i in range(n - run_len + 1):
            window = values[i: i + run_len]
            above = all(v > cl for v in window)
            below = all(v < cl for v in window)
            if above or below:
                side = "위" if above else "아래"
                violations.append({
                    "index": i + run_len - 1,
                    "value": values[i + run_len - 1],
                    "rule": 2,
                    "rule_description": f"Rule 2: 연속 9점 중심선 {side}",
                })

    # Rule 3: 연속 6점 단조 증가/감소
    run_len = 6
    if n >= run_len:
        for i in range(n - run_len + 1):
            window = values[i: i + run_len]
            increasing = all(window[j] < window[j + 1] for j in range(run_len - 1))
            decreasing = all(window[j] > window[j + 1] for j in range(run_len - 1))
            if increasing or decreasing:
                direction = "증가" if increasing else "감소"
                violations.append({
                    "index": i + run_len - 1,
                    "value": values[i + run_len - 1],
                    "rule": 3,
                    "rule_description": f"Rule 3: 연속 6점 단조 {direction}",
                })

    # Rule 4: 연속 14점 교대 증감 (지그재그)
    run_len = 14
    if n >= run_len:
        for i in range(n - run_len + 1):
            window = values[i: i + run_len]
            # 방향 1: 올라갔다 내려갔다 (짝수 인덱스에서 상승)
            alt1 = all(
                (window[j] < window[j + 1]) if j % 2 == 0 else (window[j] > window[j + 1])
                for j in range(run_len - 1)
            )
            # 방향 2: 내려갔다 올라갔다 (짝수 인덱스에서 하강)
            alt2 = all(
                (window[j] > window[j + 1]) if j % 2 == 0 else (window[j] < window[j + 1])
                for j in range(run_len - 1)
            )
            if alt1 or alt2:
                violations.append({
                    "index": i + run_len - 1,
                    "value": values[i + run_len - 1],
                    "rule": 4,
                    "rule_description": "Rule 4: 연속 14점 교대 증감",
                })

    # 중복 제거: 동일 (index, rule) 쌍
    seen: set = set()
    unique_violations: List[Dict[str, Any]] = []
    for v in violations:
        key = (v["index"], v["rule"])
        if key not in seen:
            seen.add(key)
            unique_violations.append(v)

    unique_violations.sort(key=lambda x: (x["index"], x["rule"]))
    return unique_violations


def calculate_moving_range(values: List[float]) -> List[float]:
    """이동범위(Moving Range, MR) 계산 - 개별값 관리도(I-MR chart)용.

    MR_i = |X_i - X_{i-1}|  (i = 2, 3, ..., n)

    결과 리스트 길이는 len(values) - 1 입니다.

    Args:
        values: 측정값 리스트 (최소 2개 이상).

    Returns:
        이동범위 값 리스트.

    Raises:
        ValueError: values 개수가 2 미만인 경우.
    """
    if len(values) < 2:
        raise ValueError("이동범위 계산을 위해 값이 최소 2개 이상 필요합니다.")
    return [abs(values[i] - values[i - 1]) for i in range(1, len(values))]


def get_control_chart_data(
    values: List[float],
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
) -> Dict[str, Any]:
    """관리도 전체 데이터 반환 (프론트엔드 차트 렌더링용).

    관리한계선, 이상 포인트, 공정능력지수를 하나의 딕셔너리로 반환합니다.
    USL/LSL 이 제공된 경우 Cpk 를 함께 계산합니다.

    Args:
        values: 측정값 리스트 (시계열 순서, 최소 2개 이상).
        usl: 상한 규격한계 (Optional). 제공 시 Cpk 계산 포함.
        lsl: 하한 규격한계 (Optional). 제공 시 Cpk 계산 포함.

    Returns:
        Dict containing keys:
            values (List[float]): 입력 측정값 리스트.
            indices (List[int]): 인덱스 리스트 (0-based).
            control_limits (Dict): cl, ucl, lcl, sigma, r_bar, chart_type 등.
            out_of_control (List[Dict]): Western Electric 위반 포인트 목록.
            cpk_result (Dict | None): USL/LSL 제공 시 Cpk 결과, 아니면 None.
            usl (float | None): 상한 규격한계.
            lsl (float | None): 하한 규격한계.
            n (int): 데이터 포인트 수.

    Raises:
        ValueError: values 개수가 2 미만인 경우.
    """
    if len(values) < 2:
        raise ValueError("values 는 최소 2개 이상이어야 합니다.")

    # 관리한계 계산 (개별값 I-MR 관리도)
    control_limits = calculate_control_limits(values, subgroup_size=1)

    # 이상 포인트 탐지
    out_of_control = detect_out_of_control(
        values,
        ucl=control_limits["ucl"],
        lcl=control_limits["lcl"],
        cl=control_limits["cl"],
    )

    # Cpk 계산 (USL/LSL 제공 시)
    cpk_result: Optional[Dict[str, float]] = None
    if usl is not None and lsl is not None:
        cpk_result = calculate_cpk(values, usl=usl, lsl=lsl)

    return {
        "values": values,
        "indices": list(range(len(values))),
        "control_limits": control_limits,
        "out_of_control": out_of_control,
        "cpk_result": cpk_result,
        "usl": usl,
        "lsl": lsl,
        "n": len(values),
    }
