"""
constraints.py
==============
Enforces thermodynamic feasibility constraints for the HENS problem.

Key constraint:
    ΔT_min — minimum temperature difference maintained across any heat exchanger.
    This ensures thermodynamic driving force and prevents infeasible matches.

Energy balance is also checked: duty transferred ≤ min(available_hot, available_cold).

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
from typing import Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream


# ---------------------------------------------------------------------------
# Temperature tracking utility
# ---------------------------------------------------------------------------

def current_hot_temp(hot: "HotStream", remaining_load: float) -> float:
    """
    Estimate the *current* outlet temperature of a hot stream given the
    fraction of its load that has NOT yet been removed.

    As heat is extracted, the stream temperature drops from T_in toward T_out.
    T_current = T_out + (remaining_load / FCp)
    """
    return hot.T_out + remaining_load / hot.FCp


def current_cold_temp(cold: "ColdStream", remaining_demand: float) -> float:
    """
    Estimate the *current* inlet temperature of a cold stream given the
    fraction of its demand that has NOT yet been supplied.

    As heat is added, the stream temperature rises from T_in toward T_out.
    T_current = T_out - (remaining_demand / FCp)
    """
    return cold.T_out - remaining_demand / cold.FCp


# ---------------------------------------------------------------------------
# Core feasibility check
# ---------------------------------------------------------------------------

def is_feasible_match(
    hot: "HotStream",
    cold: "ColdStream",
    hot_remaining: float,
    cold_remaining: float,
    duty: float,
    delta_T_min: float,
) -> bool:
    """
    Check whether transferring `duty` kW from `hot` to `cold` is thermodynamically
    feasible, given current remaining loads.

    Feasibility conditions:
      1. Duty must be positive and within available loads on both sides.
      2. At *both* ends of the exchanger, the hot stream must be at least
         ΔT_min hotter than the cold stream:
            hot inlet  (current T of hot)  ≥ cold outlet + ΔT_min
            hot outlet (after giving duty) ≥ cold inlet  + ΔT_min

    Parameters
    ----------
    hot, cold         : stream definitions (supply/target temps, FCp)
    hot_remaining     : heat still available on this hot stream (kW)
    cold_remaining    : heat still demanded by this cold stream (kW)
    duty              : proposed heat transfer (kW)
    delta_T_min       : minimum temperature approach (°C)

    Returns
    -------
    True if the match is feasible, False otherwise.
    """
    # --- Basic energy balance ---
    if duty <= 0:
        return False
    if duty > hot_remaining + 1e-6:
        return False
    if duty > cold_remaining + 1e-6:
        return False

    # --- Compute temperatures at both ends of the exchanger ---
    # Hot stream: enters at T_hot_in, exits at T_hot_in - duty/FCp_hot
    T_hot_in  = current_hot_temp(hot, hot_remaining)
    T_hot_out = T_hot_in - duty / hot.FCp

    # Cold stream: exits at T_cold_out, enters at T_cold_out - duty/FCp_cold
    T_cold_out = current_cold_temp(cold, cold_remaining) + duty / cold.FCp
    T_cold_in  = current_cold_temp(cold, cold_remaining)

    # --- ΔT_min check at both ends (counter-current configuration) ---
    # Hot-in vs Cold-out  (one end of the exchanger)
    if T_hot_in - T_cold_out < delta_T_min - 1e-6:
        return False
    # Hot-out vs Cold-in  (other end of the exchanger)
    if T_hot_out - T_cold_in < delta_T_min - 1e-6:
        return False

    return True


# ---------------------------------------------------------------------------
# Generate all valid (hot, cold, max_duty) candidates for a state
# ---------------------------------------------------------------------------

def get_feasible_matches(
    state: "HENSState",
    hot_streams: Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min: float,
    already_matched_fn=None,
) -> List[Tuple[str, str, float]]:
    """
    Return a list of (hot_id, cold_id, max_feasible_duty) tuples
    for all thermodynamically feasible matches in the current state.

    Pruning rules applied here:
      P1. already_matched_fn(hot_id, cold_id) → skip pairs already in matrix
      P2. ΔTmin check via is_feasible_match
      P3. Energy balance: max_duty = min(hot_remaining, cold_remaining)

    Parameters
    ----------
    already_matched_fn : callable(hot_id, cold_id) → bool | None
        If provided, skip pairs where this returns True (matrix-based P1 pruning).
    """
    candidates = []
    TOLERANCE = 0.5  # kW

    for h_id, h_rem in state.hot_remaining.items():
        if h_rem <= TOLERANCE:
            continue
        hot = hot_streams[h_id]

        for c_id, c_rem in state.cold_remaining.items():
            if c_rem <= TOLERANCE:
                continue

            # P1: matrix-based duplicate check
            if already_matched_fn is not None and already_matched_fn(h_id, c_id):
                continue

            cold = cold_streams[c_id]
            max_duty = min(h_rem, c_rem)

            # P2: thermodynamic feasibility (ΔTmin)
            if is_feasible_match(hot, cold, h_rem, c_rem, max_duty, delta_T_min):
                candidates.append((h_id, c_id, max_duty))

    return candidates


# ---------------------------------------------------------------------------
# Check for streams that MUST use utilities (no process matches possible)
# ---------------------------------------------------------------------------

def find_mandatory_utilities(
    state: "HENSState",
    hot_streams: Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min: float,
) -> Tuple[List[str], List[str]]:
    """
    Identify hot streams that have no feasible cold matches (must use coolers)
    and cold streams that have no feasible hot matches (must use heaters).

    Returns
    -------
    (must_cool_ids, must_heat_ids)
    """
    TOLERANCE = 0.5

    # Active streams
    active_hot  = {h: r for h, r in state.hot_remaining.items()  if r > TOLERANCE}
    active_cold = {c: r for c, r in state.cold_remaining.items() if r > TOLERANCE}

    # Which hot streams have at least one feasible cold match?
    hot_has_match = set()
    cold_has_match = set()

    for h_id, h_rem in active_hot.items():
        hot = hot_streams[h_id]
        for c_id, c_rem in active_cold.items():
            cold = cold_streams[c_id]
            duty = min(h_rem, c_rem)
            if is_feasible_match(hot, cold, h_rem, c_rem, duty, delta_T_min):
                hot_has_match.add(h_id)
                cold_has_match.add(c_id)

    must_cool = [h for h in active_hot  if h not in hot_has_match]
    must_heat = [c for c in active_cold if c not in cold_has_match]

    return must_cool, must_heat
