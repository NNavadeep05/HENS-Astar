"""
heuristic.py  (v3 — Pinch-Point Enhanced Admissible Heuristic)
==============================================================
Admissible heuristic h(n) for the HENS A* search.

Three components, all lower bounds on remaining cost:

  A. Aggregate energy balance: global hot/cold surplus or deficit.
  B. Temperature feasibility: per-stream portions that must use utilities
     regardless of process matches (forced by delta_T_min limits).
  C. Pinch composite curve: builds hot and cold composite curves from
     remaining streams, shifts cold by delta_T_min, computes QHmin and
     QCmin from the pinch. Tightest of the three bounds.

Final: h(n) = max(A, B, C) per utility type x utility cost rate.

All components ignore future exchanger capital costs and use minimum
utility rates, so h(n) <= h*(n) always — A* remains optimal.
Falls back to max(A, B) if composite curve hits a numerical issue.

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from cost import STEAM_COST_PER_KW_YEAR, COOLING_COST_PER_KW_YEAR

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream

TOLERANCE = 0.5  # kW


def _build_composite_curve(
    segments: List[Tuple[float, float, float]],  # (T_high, T_low, FCp)
    ascending: bool = False,
) -> List[Tuple[float, float]]:
    """
    Build a composite curve from stream segments (T_high, T_low, FCp).
    Returns (cumulative_H, T) points swept from high T to low T.
    If ascending=True, reverses to low-to-high order.
    """
    if not segments:
        return [(0.0, 0.0)]

    temps = set()
    for T_high, T_low, _ in segments:
        temps.add(T_high)
        temps.add(T_low)
    temps_sorted = sorted(temps, reverse=True)

    points: List[Tuple[float, float]] = []
    H = 0.0
    points.append((H, temps_sorted[0]))

    for i in range(len(temps_sorted) - 1):
        T_top = temps_sorted[i]
        T_bot = temps_sorted[i + 1]
        FCp_sum = sum(
            fcp for (th, tl, fcp) in segments
            if th >= T_top - 1e-9 and tl <= T_bot + 1e-9
        )
        H += FCp_sum * (T_top - T_bot)
        points.append((H, T_bot))

    return list(reversed(points)) if ascending else points


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

        # Component C: pinch composite curve
        try:
            hot_segs = [
                (current_hot_temp(hot_streams[h], r), hot_streams[h].T_out, hot_streams[h].FCp)
                for h, r in state.hot_remaining.items()
                if r > TOLERANCE and current_hot_temp(hot_streams[h], r) > hot_streams[h].T_out + 1e-9
            ]
            cold_segs = [
                (cold_streams[c].T_out, current_cold_temp(cold_streams[c], r), cold_streams[c].FCp)
                for c, r in state.cold_remaining.items()
                if r > TOLERANCE and cold_streams[c].T_out > current_cold_temp(cold_streams[c], r) + 1e-9
            ]

            if hot_segs and cold_segs:
                hot_curve  = _build_composite_curve(hot_segs,  ascending=False)
                hot_total  = hot_curve[-1][0]

                cold_segs_shifted = [(th + delta_T_min, tl + delta_T_min, fcp)
                                     for (th, tl, fcp) in cold_segs]
                cold_curve = _build_composite_curve(cold_segs_shifted, ascending=False)
                cold_total = cold_curve[-1][0]

                def interp_H(pts, T_query):
                    if T_query >= pts[0][1]:  return 0.0
                    if T_query <= pts[-1][1]: return pts[-1][0]
                    for k in range(len(pts) - 1):
                        T_hi, T_lo = pts[k][1], pts[k+1][1]
                        H_hi, H_lo = pts[k][0], pts[k+1][0]
                        if T_lo <= T_query <= T_hi:
                            frac = (T_hi - T_query) / (T_hi - T_lo) if abs(T_hi - T_lo) > 1e-9 else 0.0
                            return H_hi + frac * (H_lo - H_hi)
                    return 0.0

                min_gap = float("inf")
                pinch_hot_H = pinch_cold_H = 0.0

                for H_hot, T_pt in hot_curve:
                    gap = interp_H(cold_curve, T_pt) - H_hot
                    if gap < min_gap:
                        min_gap, pinch_hot_H, pinch_cold_H = gap, H_hot, interp_H(cold_curve, T_pt)

                for H_cold, T_pt in cold_curve:
                    gap = H_cold - interp_H(hot_curve, T_pt)
                    if gap < min_gap:
                        min_gap, pinch_hot_H, pinch_cold_H = gap, interp_H(hot_curve, T_pt), H_cold

                heat_deficit_C = max(0.0, pinch_cold_H - pinch_hot_H)
                cool_surplus_C = max(0.0, (hot_total - pinch_hot_H) - (cold_total - pinch_cold_H))

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
