"""
heuristic.py  (v3 — Pinch-Point Enhanced Admissible Heuristic)
==============================================================
Admissible heuristic for the HENS A* decision-tree search.

THREE COMPONENTS, all lower bounds on remaining cost:

Component A — AGGREGATE ENERGY BALANCE
    h_A = max(0, Σcold_remaining − Σhot_remaining) × steam_cost
          + max(0, Σhot_remaining − Σcold_remaining) × CW_cost
    The global mismatch between total heat supply and demand.

Component B — TEMPERATURE-FEASIBILITY (per-stream thermodynamic obligation)
    For each cold stream, any portion of its demand that lies ABOVE
    (max_hot_T − ΔTmin) cannot be met by process exchange and MUST
    come from steam. Symmetrically, hot portions below (min_cold_T +
    ΔTmin) must use cooling water. Both are strict thermodynamic
    lower bounds derived from individual stream temperature levels.

Component C — PINCH POINT COMPOSITE CURVE ANALYSIS
    Builds the hot and cold composite curves from all remaining stream
    segments, then applies Pinch Analysis to determine the minimum
    heating utility (QHmin) and minimum cooling utility (QCmin) that
    thermodynamics requires regardless of the network configuration.
    The cold composite curve is shifted by ΔTmin when compared to the
    hot composite, enforcing the minimum approach temperature.

    Steps:
      1. Collect remaining hot segments (T_current → T_out, FCp, load).
      2. Collect remaining cold segments (T_current → T_out, FCp, load).
      3. Build hot composite curve: temperature breakpoints sorted
         descending; cumulative enthalpy swept from high T to low T.
      4. Build cold composite curve similarly.
      5. Shift cold curve up by ΔTmin (treat cold temperatures as
         T + ΔTmin when overlapping with the hot curve).
      6. Identify the pinch: interval where hot − cold enthalpy is min.
      7. QHmin = max(0, cold_total − hot_total_above_pinch)
         QCmin = max(0, hot_total − cold_total_above_pinch)

FINAL HEURISTIC:
    heating_utility = max(heat_deficit_A, heat_deficit_B, heat_deficit_C)
    cooling_utility = max(cool_surplus_A, cool_surplus_B, cool_surplus_C)
    h(n) = heating_utility × STEAM_COST + cooling_utility × CW_COST

ADMISSIBILITY GUARANTEE
------------------------
All three components are lower bounds because they:
  1. Ignore all exchanger capital costs (≥ 0)
  2. Use the cheapest utility rates
  3. Never overestimate the TRUE minimum utility needed

Component C uses the pinch-analysis lower bound which is physically
tight but never exceeds the real minimum — it is the thermodynamic
floor for any feasible network. If the calculation encounters
numerical issues, it falls back to max(A, B).

Therefore h(n) ≤ h*(n) ∀n  →  A* remains OPTIMAL.

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from cost import STEAM_COST_PER_KW_YEAR, COOLING_COST_PER_KW_YEAR

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream


TOLERANCE = 0.5   # kW


# ===========================================================================
# Composite curve builder  (shared by heuristic and visualization)
# ===========================================================================

def _build_composite_curve(
    segments: List[Tuple[float, float, float]],   # (T_high, T_low, FCp)
    ascending: bool = False,
) -> List[Tuple[float, float]]:
    """
    Build a composite curve from a list of stream segments.

    Each segment is (T_high, T_low, FCp) where T_high > T_low.
    Returns a list of (cumulative_H, T) points.

    If ascending=False (hot curve): sweep from high T to low T,
    enthalpy grows from left rightwards.
    If ascending=True  (cold curve): sweep from low T to high T.
    """
    if not segments:
        return [(0.0, 0.0)]

    # Collect all unique temperature breakpoints
    temps = set()
    for T_high, T_low, _ in segments:
        temps.add(T_high)
        temps.add(T_low)
    temps_sorted = sorted(temps, reverse=True)   # high → low

    # Build curve by sweeping from high T to low T
    points: List[Tuple[float, float]] = []
    H = 0.0
    points.append((H, temps_sorted[0]))

    for i in range(len(temps_sorted) - 1):
        T_top = temps_sorted[i]
        T_bot = temps_sorted[i + 1]
        dT = T_top - T_bot

        # Sum FCp of all segments covering this interval
        FCp_sum = sum(
            fcp for (th, tl, fcp) in segments
            if th >= T_top - 1e-9 and tl <= T_bot + 1e-9
        )
        H += FCp_sum * dT
        points.append((H, T_bot))

    if ascending:
        # Return in ascending temperature order (low → high)
        points = list(reversed(points))
    return points


# ===========================================================================
# Primary admissible heuristic
# ===========================================================================

def heuristic(
    state: "HENSState",
    hot_streams:  Optional[Dict[str, "HotStream"]]  = None,
    cold_streams: Optional[Dict[str, "ColdStream"]] = None,
    delta_T_min:  float = 10.0,
) -> float:
    """
    Compute h(n): admissible lower bound of remaining cost.

    Combines three components — all are lower bounds:
      (A) ENERGY-BALANCE bound  (aggregate)
      (B) TEMPERATURE-FEASIBILITY bound  (per-stream thermodynamic obligation)
      (C) PINCH-POINT bound  (composite curve analysis)

    h(n) = max(A, B, C) per utility type × utility_cost

    Parameters
    ----------
    state        : current A* node
    hot_streams  : optional dict {id: HotStream} — used for temperature bounds
    cold_streams : optional dict {id: ColdStream}
    delta_T_min  : minimum approach temperature (°C)

    Returns
    -------
    float : h(n) in $/year
    """

    # ---- Total remaining loads --------------------------------------------
    total_hot  = sum(max(0.0, v) for v in state.hot_remaining.values()
                     if v > TOLERANCE)
    total_cold = sum(max(0.0, v) for v in state.cold_remaining.values()
                     if v > TOLERANCE)

    # ---- Component A: aggregate energy balance ----------------------------
    heat_deficit_A = max(0.0, total_cold - total_hot)
    cool_surplus_A = max(0.0, total_hot  - total_cold)

    # ---- Component B: temperature-based thermodynamic lower bounds --------
    heat_deficit_B = 0.0
    cool_surplus_B = 0.0

    # ---- Component C: pinch point composite curve -------------------------
    heat_deficit_C = 0.0
    cool_surplus_C = 0.0

    if hot_streams and cold_streams:
        from constraints import current_hot_temp, current_cold_temp

        max_hot_T = max(
            (current_hot_temp(hot_streams[h], r)
             for h, r in state.hot_remaining.items() if r > TOLERANCE),
            default=0.0,
        )
        min_cold_T = min(
            (current_cold_temp(cold_streams[c], r)
             for c, r in state.cold_remaining.items() if r > TOLERANCE),
            default=9999.0,
        )

        # ---- Component B computation ----
        # Cold portion above (max_hot_T − ΔTmin): MUST be steam-heated
        for c_id, c_rem in state.cold_remaining.items():
            if c_rem <= TOLERANCE:
                continue
            cold = cold_streams[c_id]
            T_cold_target = cold.T_out
            obligatory_T = max_hot_T - delta_T_min
            if T_cold_target > obligatory_T:
                T_cold_current = current_cold_temp(cold, c_rem)
                T_bottom = max(T_cold_current, obligatory_T)
                if T_cold_target > T_bottom:
                    forced_steam_duty = cold.FCp * (T_cold_target - T_bottom)
                    heat_deficit_B += min(forced_steam_duty, c_rem)

        # Hot portion below (min_cold_T + ΔTmin): MUST use cooling water
        for h_id, h_rem in state.hot_remaining.items():
            if h_rem <= TOLERANCE:
                continue
            hot = hot_streams[h_id]
            T_hot_target = hot.T_out
            obligatory_T = min_cold_T + delta_T_min
            if T_hot_target < obligatory_T:
                T_hot_current = current_hot_temp(hot, h_rem)
                T_top = min(T_hot_current, obligatory_T)
                if T_top > T_hot_target:
                    forced_CW_duty = hot.FCp * (T_top - T_hot_target)
                    cool_surplus_B += min(forced_CW_duty, h_rem)

        # ---- Component C: pinch composite curve analysis ----
        try:
            # Build hot segments: (T_current, T_out, FCp)
            hot_segs: List[Tuple[float, float, float]] = []
            for h_id, h_rem in state.hot_remaining.items():
                if h_rem <= TOLERANCE:
                    continue
                hot = hot_streams[h_id]
                T_curr = current_hot_temp(hot, h_rem)
                T_target = hot.T_out
                if T_curr > T_target + 1e-9:
                    hot_segs.append((T_curr, T_target, hot.FCp))

            # Build cold segments: (T_out, T_current, FCp)
            cold_segs: List[Tuple[float, float, float]] = []
            for c_id, c_rem in state.cold_remaining.items():
                if c_rem <= TOLERANCE:
                    continue
                cold = cold_streams[c_id]
                T_curr = current_cold_temp(cold, c_rem)
                T_target = cold.T_out
                if T_target > T_curr + 1e-9:
                    cold_segs.append((T_target, T_curr, cold.FCp))

            if hot_segs and cold_segs:
                # Hot composite curve: points are (H, T), H from left
                hot_curve = _build_composite_curve(hot_segs, ascending=False)
                # Total hot enthalpy
                hot_total = hot_curve[-1][0]

                # Cold composite curve: shifted up by delta_T_min
                # Build cold segments with T shifted up by delta_T_min
                cold_segs_shifted = [
                    (T_high + delta_T_min, T_low + delta_T_min, fcp)
                    for (T_high, T_low, fcp) in cold_segs
                ]
                cold_curve_shifted = _build_composite_curve(
                    cold_segs_shifted, ascending=False
                )
                cold_total = cold_curve_shifted[-1][0]

                # Find pinch: temperature intervals on the hot composite
                # where (hot_H_so_far - cold_H_so_far) is minimum.
                # We do a simple interpolation sweep over hot temperature
                # breakpoints to find where the deficit is tightest.

                # Collect all breakpoints on the hot curve temperatures
                hot_temps = sorted(set(T for (_, T) in hot_curve), reverse=True)

                # For each hot-temperature level, find cumulative hot H
                # and the corresponding cold H (by interpolating cold_curve_shifted)
                def interp_cold_H(T_hot: float) -> float:
                    """
                    Interpolate cumulative cold enthalpy at a given
                    shifted-temperature level.
                    """
                    # cold_curve_shifted is ordered high T → low T
                    # (H increases left to right, T decreases)
                    pts = cold_curve_shifted  # [(H, T), ...]
                    if T_hot >= pts[0][1]:
                        return 0.0   # above all cold temps → 0 cold H here
                    if T_hot <= pts[-1][1]:
                        return pts[-1][0]   # below all cold → full cold H
                    # Linear interpolation between bracketing points
                    for k in range(len(pts) - 1):
                        T_hi = pts[k][1]
                        T_lo = pts[k + 1][1]
                        H_hi = pts[k][0]
                        H_lo = pts[k + 1][0]
                        if T_lo <= T_hot <= T_hi:
                            if abs(T_hi - T_lo) < 1e-9:
                                return H_hi
                            frac = (T_hi - T_hot) / (T_hi - T_lo)
                            return H_hi + frac * (H_lo - H_hi)
                    return 0.0

                # Similarly, interpolate cumulative hot H at temperature T
                def interp_hot_H(T_hot: float) -> float:
                    pts = hot_curve  # [(H, T), ...]
                    if T_hot >= pts[0][1]:
                        return 0.0
                    if T_hot <= pts[-1][1]:
                        return pts[-1][0]
                    for k in range(len(pts) - 1):
                        T_hi = pts[k][1]
                        T_lo = pts[k + 1][1]
                        H_hi = pts[k][0]
                        H_lo = pts[k + 1][0]
                        if T_lo <= T_hot <= T_hi:
                            if abs(T_hi - T_lo) < 1e-9:
                                return H_hi
                            frac = (T_hi - T_hot) / (T_hi - T_lo)
                            return H_hi + frac * (H_lo - H_hi)
                    return 0.0

                # Evaluate gap = (cold_H_at_T - hot_H_at_T) at each hot
                # temperature breakpoint; the temperature with the minimum
                # gap (or most negative gap, indicating least excess of hot)
                # defines the pinch.
                # Convention: gap > 0 → cold needs more from utilities above.
                min_gap = float("inf")
                pinch_hot_H = 0.0
                pinch_cold_H = 0.0

                for (H_hot, T_pt) in hot_curve:
                    H_cold_here = interp_cold_H(T_pt)
                    gap = H_cold_here - H_hot
                    if gap < min_gap:
                        min_gap = gap
                        pinch_hot_H = H_hot
                        pinch_cold_H = H_cold_here

                # Also check at each cold-curve breakpoint temperature
                for (H_cold, T_pt) in cold_curve_shifted:
                    H_hot_here = interp_hot_H(T_pt)
                    gap = H_cold - H_hot_here
                    if gap < min_gap:
                        min_gap = gap
                        pinch_hot_H = H_hot_here
                        pinch_cold_H = H_cold

                # QHmin = max(0, cold demand above pinch − hot supply above pinch)
                hot_above_pinch  = pinch_hot_H   # enthalpy delivered to pinch
                cold_above_pinch = pinch_cold_H  # enthalpy demanded to pinch

                QHmin = max(0.0, cold_above_pinch - hot_above_pinch)
                QCmin = max(0.0, (hot_total - hot_above_pinch)
                                 - (cold_total - cold_above_pinch))

                heat_deficit_C = QHmin
                cool_surplus_C = QCmin

        except Exception:
            # If any numerical issue, component C stays 0
            # (falls back to max(A, B) safely)
            heat_deficit_C = 0.0
            cool_surplus_C = 0.0

    # ---- Combine: take the tighter (larger) lower bound per component -----
    heating_utility = max(heat_deficit_A, heat_deficit_B, heat_deficit_C)
    cooling_utility = max(cool_surplus_A, cool_surplus_B, cool_surplus_C)

    h = (heating_utility * STEAM_COST_PER_KW_YEAR
       + cooling_utility * COOLING_COST_PER_KW_YEAR)

    return h


# ===========================================================================
# Admissibility proof (accessible from reports)
# ===========================================================================

def heuristic_is_admissible() -> str:
    return (
        "Admissible (v3): h(n) = max(A, B, C) per utility, × utility_cost. "
        "Component A: aggregate energy balance. "
        "Component B: per-stream temperature obligation (steam/CW forced by ΔTmin). "
        "Component C: Pinch Point composite curve — QHmin/QCmin lower bounds. "
        "All three ignore capital costs (≥0) and use minimum utility rates "
        "→ h(n) ≤ h*(n) always → A* is OPTIMAL."
    )
