"""
heuristic.py  (v4 — Pinch-Point Enhanced Admissible Heuristic)
==============================================================
Admissible heuristic h(n) for the HENS A* search.

Three components, all lower bounds on remaining cost:

  A. Aggregate energy balance: global hot/cold surplus or deficit.
  B. Temperature feasibility: per-stream portions that must use utilities
     regardless of process matches (forced by delta_T_min limits).
  C. Pinch Problem Table Algorithm (Linnhoff & Hindmarsh, 1983):
     merges hot and shifted-cold temperature breakpoints into unified
     intervals, cascades net heat surplus top-to-bottom, reads off
     QHmin and QCmin directly.  Tightest of the three bounds.

Final: h(n) = max(A, B, C) per utility type x utility cost rate.

All components ignore future exchanger capital costs and use minimum
utility rates, so h(n) <= h*(n) always — A* remains optimal.

Bug fix (v4): the previous composite-curve gap method compared
cold_H(T) - hot_H(T) where both curves independently start at H=0 at
their own top temperatures.  Because hot total energy > cold total, the
gap was always ≤ 0, making h_C = 0 on every node.  The Problem Table
Algorithm (PTA) is the standard correct solution.

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from cost import STEAM_COST_PER_KW_YEAR, COOLING_COST_PER_KW_YEAR

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream

TOLERANCE = 0.5  # kW


def _problem_table_algorithm(
    hot_segs:  List[Tuple[float, float, float]],   # (T_hi, T_lo, FCp)
    cold_segs: List[Tuple[float, float, float]],   # (T_hi, T_lo, FCp) — already shifted
) -> Tuple[float, float]:
    """
    Linnhoff & Hindmarsh (1983) Problem Table Algorithm.

    Inputs are stream segments on the SAME temperature scale:
      hot_segs  — (current_T, T_out, FCp) for each active hot stream
      cold_segs — (T_out + dTmin, current_T + dTmin, FCp) for active cold streams

    Algorithm:
      1. Collect all temperature breakpoints from both sets.
      2. For each interval [T_bot, T_top] (high→low), compute:
             surplus_k = (ΣFCp_hot − ΣFCp_cold) × (T_top − T_bot)
      3. Cascade residuals:  R[0]=0,  R[k+1] = R[k] + surplus_k
      4. QHmin = max(0, −min(R))   — external heat needed to keep R ≥ 0
         QCmin = max(0, R_last + QHmin)  — net surplus out the bottom

    Returns (QHmin_kW, QCmin_kW).
    """
    all_segs = hot_segs + cold_segs
    if not all_segs:
        return 0.0, 0.0

    temps: set = set()
    for T_hi, T_lo, _ in all_segs:
        temps.add(T_hi)
        temps.add(T_lo)
    ts = sorted(temps, reverse=True)
    if len(ts) < 2:
        return 0.0, 0.0

    residuals: List[float] = [0.0]
    for i in range(len(ts) - 1):
        T_top, T_bot = ts[i], ts[i + 1]
        hot_fcp  = sum(fcp for (th, tl, fcp) in hot_segs
                       if th >= T_top - 1e-9 and tl <= T_bot + 1e-9)
        cold_fcp = sum(fcp for (th, tl, fcp) in cold_segs
                       if th >= T_top - 1e-9 and tl <= T_bot + 1e-9)
        surplus  = (hot_fcp - cold_fcp) * (T_top - T_bot)
        residuals.append(residuals[-1] + surplus)

    QH_min = max(0.0, -min(residuals))
    QC_min = max(0.0, residuals[-1] + QH_min)
    return QH_min, QC_min


def heuristic(
    state:        "HENSState",
    hot_streams:  Optional[Dict[str, "HotStream"]]  = None,
    cold_streams: Optional[Dict[str, "ColdStream"]] = None,
    delta_T_min:  float = 10.0,
) -> float:
    """Return h(n): admissible lower bound on remaining TAC cost."""

    total_hot  = sum(max(0.0, v) for v in state.hot_remaining.values()  if v > TOLERANCE)
    total_cold = sum(max(0.0, v) for v in state.cold_remaining.values() if v > TOLERANCE)

    # Component A: aggregate energy balance
    heat_deficit_A = max(0.0, total_cold - total_hot)
    cool_surplus_A = max(0.0, total_hot  - total_cold)

    heat_deficit_B = cool_surplus_B = 0.0
    heat_deficit_C = cool_surplus_C = 0.0

    if hot_streams and cold_streams:
        from constraints import current_hot_temp, current_cold_temp

        max_hot_T  = max(
            (current_hot_temp(hot_streams[h], r)
             for h, r in state.hot_remaining.items() if r > TOLERANCE),
            default=0.0,
        )
        min_cold_T = min(
            (current_cold_temp(cold_streams[c], r)
             for c, r in state.cold_remaining.items() if r > TOLERANCE),
            default=9999.0,
        )

        # Component B: per-stream temperature obligations
        for c_id, c_rem in state.cold_remaining.items():
            if c_rem <= TOLERANCE:
                continue
            cold         = cold_streams[c_id]
            obligatory_T = max_hot_T - delta_T_min
            if cold.T_out > obligatory_T:
                T_curr   = current_cold_temp(cold, c_rem)
                T_bottom = max(T_curr, obligatory_T)
                if cold.T_out > T_bottom:
                    heat_deficit_B += min(cold.FCp * (cold.T_out - T_bottom), c_rem)

        for h_id, h_rem in state.hot_remaining.items():
            if h_rem <= TOLERANCE:
                continue
            hot          = hot_streams[h_id]
            obligatory_T = min_cold_T + delta_T_min
            if hot.T_out < obligatory_T:
                T_curr = current_hot_temp(hot, h_rem)
                T_top  = min(T_curr, obligatory_T)
                if T_top > hot.T_out:
                    cool_surplus_B += min(hot.FCp * (T_top - hot.T_out), h_rem)

        # Component C: Problem Table Algorithm (Linnhoff & Hindmarsh, 1983)
        # Bug fix v4: the old composite-curve gap method compared cold_H(T) - hot_H(T)
        # where both curves independently start at H=0 at their own top temperatures.
        # Because hot total energy > cold total, that gap was always <= 0, giving
        # heat_C = cool_C = 0 on every single node.
        # The PTA merges breakpoints into unified intervals and cascades surplus
        # correctly, producing the true QHmin and QCmin.
        try:
            hot_segs = [
                (current_hot_temp(hot_streams[h], r), hot_streams[h].T_out, hot_streams[h].FCp)
                for h, r in state.hot_remaining.items()
                if r > TOLERANCE and current_hot_temp(hot_streams[h], r) > hot_streams[h].T_out + 1e-9
            ]
            cold_segs_shifted = [
                (cold_streams[c].T_out  + delta_T_min,
                 current_cold_temp(cold_streams[c], r) + delta_T_min,
                 cold_streams[c].FCp)
                for c, r in state.cold_remaining.items()
                if r > TOLERANCE and cold_streams[c].T_out > current_cold_temp(cold_streams[c], r) + 1e-9
            ]

            if hot_segs or cold_segs_shifted:
                heat_deficit_C, cool_surplus_C = _problem_table_algorithm(
                    hot_segs, cold_segs_shifted
                )

        except Exception:
            heat_deficit_C = cool_surplus_C = 0.0

    heating_utility = max(heat_deficit_A, heat_deficit_B, heat_deficit_C)
    cooling_utility = max(cool_surplus_A, cool_surplus_B, cool_surplus_C)

    return heating_utility * STEAM_COST_PER_KW_YEAR + cooling_utility * COOLING_COST_PER_KW_YEAR


def heuristic_is_admissible() -> str:
    return (
        "Admissible (v3): h(n) = max(A, B, C) per utility x utility_cost. "
        "A: aggregate energy balance. "
        "B: per-stream temperature obligation. "
        "C: pinch composite curve QHmin/QCmin. "
        "All ignore capital costs and use minimum utility rates — h(n) <= h*(n) always."
    )
