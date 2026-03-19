"""
heuristic.py  (v2 — Improved Admissible Heuristic)
====================================================
Enhanced admissible heuristic for the HENS A* decision-tree search.

IMPROVEMENT OVER v1
--------------------
v1 used only aggregate energy balance:
    h = max(0, Σcold − Σhot) × steam_cost
      + max(0, Σhot  − Σcold) × CW_cost

v2 adds a TEMPERATURE-BASED COMPONENT:
    For each cold stream, any portion of its demand that lies ABOVE
    the maximum available hot temperature CANNOT be met by process
    heat exchange — it MUST come from steam.

    For each hot stream, any portion of its load that lies BELOW
    the minimum available cold temperature CANNOT be absorbed by
    process exchange — it MUST use cooling water.

    These are thermodynamic lower bounds (real minimum utility
    obligations), making h(n) tighter while remaining ≤ h*(n).

ADMISSIBILITY GUARANTEE
------------------------
Both components are lower bounds because they:
  1. Ignore all exchanger capital costs (≥ 0)
  2. Use the cheapest utility rates
  3. Never charge more than the TRUE minimum utility needed

Therefore h(n) ≤ h*(n) ∀n  →  A* is OPTIMAL.

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING

from cost import STEAM_COST_PER_KW_YEAR, COOLING_COST_PER_KW_YEAR

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream


TOLERANCE = 0.5   # kW


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
    Compute h(n): improved admissible lower bound of remaining cost.

    Combines two components — both are lower bounds:
      (A) ENERGY-BALANCE bound  (aggregate)
      (B) TEMPERATURE-FEASIBILITY bound  (per-stream thermodynamic obligation)

    h(n) = max(A, B_heat) × steam_cost + max(A, B_cool) × CW_cost
         where comparisons are taken component-wise for tightness.

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

    if hot_streams and cold_streams:
        # Maximum hot-side temperature available (considering remaining work)
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

        # Cold portion above (max_hot_T − ΔTmin): MUST be steam-heated
        for c_id, c_rem in state.cold_remaining.items():
            if c_rem <= TOLERANCE:
                continue
            cold = cold_streams[c_id]
            # Temperature where this cold stream ends
            T_cold_target = cold.T_out
            # If target exceeds (max hot − ΔTmin), some portion must be steam
            obligatory_T = max_hot_T - delta_T_min
            if T_cold_target > obligatory_T:
                # Portion of cold demand above the threshold
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

    # ---- Combine: take the tighter (larger) lower bound per component -----
    heating_utility = max(heat_deficit_A, heat_deficit_B)
    cooling_utility = max(cool_surplus_A, cool_surplus_B)

    h = (heating_utility * STEAM_COST_PER_KW_YEAR
       + cooling_utility * COOLING_COST_PER_KW_YEAR)

    return h


# ===========================================================================
# Admissibility proof (accessible from reports)
# ===========================================================================

def heuristic_is_admissible() -> str:
    return (
        "Admissible (v2): h(n) = max(energy-balance, temperature-obligation) "
        "× utility_cost. Both components ignore capital costs (≥0) and use "
        "minimum utility rates → h(n) ≤ h*(n) always → A* is OPTIMAL."
    )
