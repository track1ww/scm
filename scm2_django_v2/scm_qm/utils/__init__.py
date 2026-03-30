"""scm_qm utils package - SPC and quality management utilities."""
from .spc import (
    calculate_cpk,
    calculate_control_limits,
    detect_out_of_control,
    calculate_moving_range,
    get_control_chart_data,
)


def calc_process_capability(values, usl=None, lsl=None, target=None):
    """views.py 호환 래퍼 — calculate_cpk 호출."""
    try:
        if usl is not None and lsl is not None:
            return calculate_cpk([float(v) for v in values], usl=float(usl), lsl=float(lsl))
        # USL/LSL 없으면 기본 통계만 반환
        import statistics as _s
        vals = [float(v) for v in values]
        return {'mean': round(_s.mean(vals), 6), 'std': round(_s.stdev(vals), 6), 'n': len(vals)}
    except Exception as e:
        return {'error': str(e)}


def calc_control_limits(values, subgroup_size=1):
    """views.py 호환 래퍼 — calculate_control_limits 호출."""
    return calculate_control_limits([float(v) for v in values], subgroup_size=subgroup_size)


def classify_spc_points(values, ucl, lcl, center):
    """views.py 호환 래퍼 — detect_out_of_control 호출."""
    return detect_out_of_control(
        [float(v) for v in values], ucl=float(ucl), lcl=float(lcl), cl=float(center)
    )


__all__ = [
    'calculate_cpk', 'calculate_control_limits', 'detect_out_of_control',
    'calculate_moving_range', 'get_control_chart_data',
    'calc_process_capability', 'calc_control_limits', 'classify_spc_points',
]
