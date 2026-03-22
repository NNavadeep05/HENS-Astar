"""
constraints.py
==============
Thermodynamic feasibility checks for the HENS problem.

Enforces delta_T_min at both ends of every proposed heat exchanger match,
and energy balance (duty <= min available load on each side).

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
from typing import Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream

TOLERANCE = 0.5  # kW


def current_hot_temp(hot: "HotStream", remaining_load: float) -> float:
    """Current temperature of a hot stream given remaining load.
    T = T_out + remaining_load / FCp (stream cools as heat is removed)."""
    return hot.T_out + remaining_load / hot.FCp


def current_cold_temp(cold: "ColdStream", remaining_demand: float) -> float:
    """Current temperature of a cold stream given remaining demand.
    T = T_out - remaining_demand / FCp (stream heats as demand is met)."""
    return cold.T_out - remaining_demand / cold.FCp


def is_feasible_match(
    hot:            "HotStream",
    cold:           "ColdStream",
    hot_remaining:  float,
    cold_remaining: float,
    duty:           float,
    delta_T_min:    float,
) -> bool:
    """
    Return True if transferring `duty` kW from hot to cold is feasible.

    Checks:
      1. Duty is positive and within available loads on both sides.
      2. Hot stream exceeds cold stream by at least delta_T_min at both
         exchanger ends (counter-current configuration).
    """
    if duty <= 0:
        return False
    if duty > hot_remaining + 1e-6 or duty > cold_remaining + 1e-6:
        return False

    T_hot_in   = current_hot_temp(hot, hot_remaining)
    T_hot_out  = T_hot_in - duty / hot.FCp
    T_cold_in  = current_cold_temp(cold, cold_remaining)
    T_cold_out = T_cold_in + duty / cold.FCp

    if T_hot_in  - T_cold_out < delta_T_min - 1e-6:
        return False
    if T_hot_out - T_cold_in  < delta_T_min - 1e-6:
        return False

    return True


def get_feasible_matches(
    state:              "HENSState",
    hot_streams:        Dict[str, "HotStream"],
    cold_streams:       Dict[str, "ColdStream"],
    delta_T_min:        float,
    already_matched_fn=None,
) -> List[Tuple[str, str, float]]:
    """
    Return (hot_id, cold_id, max_duty) for all feasible matches in the current state.

    Applies P1 (matrix duplicate check) and P2 (delta_T_min check).
    max_duty = min(hot_remaining, cold_remaining).
    """
    candidates = []

    for h_id, h_rem in state.hot_remaining.items():
        if h_rem <= TOLERANCE:
            continue
        hot = hot_streams[h_id]

        for c_id, c_rem in state.cold_remaining.items():
            if c_rem <= TOLERANCE:
                continue
            if already_matched_fn is not None and already_matched_fn(h_id, c_id):
                continue

            cold     = cold_streams[c_id]
            max_duty = min(h_rem, c_rem)

            if is_feasible_match(hot, cold, h_rem, c_rem, max_duty, delta_T_min):
                candidates.append((h_id, c_id, max_duty))

    return candidates


def find_mandatory_utilities(
    state:        "HENSState",
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float,
) -> Tuple[List[str], List[str]]:
    """
    Return (must_cool_ids, must_heat_ids) for streams with no feasible process match.
    These streams must use external utilities regardless of network configuration.
    """
    active_hot  = {h: r for h, r in state.hot_remaining.items()  if r > TOLERANCE}
    active_cold = {c: r for c, r in state.cold_remaining.items() if r > TOLERANCE}

    hot_has_match  = set()
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
