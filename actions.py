"""
actions.py
==========
Generates successor states in the HENS A* decision tree.

Three action types at each node:
  1. MATCH(Hi, Cj)   — place a process heat exchanger
  2. ADD_HEATER(Cj)  — steam on cold stream Cj (only if no process match exists)
  3. ADD_COOLER(Hi)  — cooling water on hot stream Hi (only if no process match exists)

Pruning rules enforced here:
  P1. Skip (Hi, Cj) already in the matrix
  P2. Skip matches violating delta_T_min
  P3. Utilities only when no process match is available for that stream
  P4. Anchor-hot: fix the lowest-indexed hot stream with remaining load as
      the branching point per level — collapses commutative orderings into one path

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
from typing import Dict, List, TYPE_CHECKING

from state import HENSState, ExchangerMatch, UtilityHeater, UtilityCooler
from constraints import get_feasible_matches, current_hot_temp, current_cold_temp
from cost import compute_g_cost

if TYPE_CHECKING:
    from state import HotStream, ColdStream


TOLERANCE = 0.5  # kW — duties below this are treated as satisfied


def action_match(
    state:        HENSState,
    hot_id:       str,
    cold_id:      str,
    duty:         float,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
) -> HENSState:
    """Place one process heat exchanger transferring `duty` kW."""
    hot   = hot_streams[hot_id]
    cold  = cold_streams[cold_id]
    h_rem = state.hot_remaining[hot_id]
    c_rem = state.cold_remaining[cold_id]

    # Current temperatures from remaining loads
    T_h_in  = current_hot_temp(hot, h_rem)
    T_h_out = T_h_in - duty / hot.FCp
    T_c_in  = current_cold_temp(cold, c_rem)
    T_c_out = T_c_in + duty / cold.FCp

    new_g = compute_g_cost(
        prev_g=state.g_cost,
        action_type="match",
        duty=duty,
        T_h_in=T_h_in,
        T_h_out=T_h_out,
        T_c_in=T_c_in,
        T_c_out=T_c_out,
    )

    succ  = state.clone()
    order = succ.num_exchangers() + 1
    succ.matrix.set(cold_id, hot_id, order)
    succ.hot_remaining[hot_id]   = max(0.0, h_rem - duty)
    succ.cold_remaining[cold_id] = max(0.0, c_rem - duty)
    succ.matches    = state.matches + (ExchangerMatch(hot_id, cold_id, duty, order),)
    succ.tree_level += 1
    succ.g_cost     = new_g
    return succ


def action_add_heater(state: HENSState, cold_id: str, duty: float) -> HENSState:
    """Supply `duty` kW of steam to cold stream `cold_id`."""
    new_g = compute_g_cost(prev_g=state.g_cost, action_type="heater", duty=duty)
    succ  = state.clone()
    succ.cold_remaining[cold_id] = max(0.0, state.cold_remaining[cold_id] - duty)
    succ.heaters = state.heaters + (UtilityHeater(cold_id, duty),)
    succ.g_cost  = new_g
    return succ


def action_add_cooler(state: HENSState, hot_id: str, duty: float) -> HENSState:
    """Remove `duty` kW via cooling water from hot stream `hot_id`."""
    new_g = compute_g_cost(prev_g=state.g_cost, action_type="cooler", duty=duty)
    succ  = state.clone()
    succ.hot_remaining[hot_id] = max(0.0, state.hot_remaining[hot_id] - duty)
    succ.coolers = state.coolers + (UtilityCooler(hot_id, duty),)
    succ.g_cost  = new_g
    return succ


def get_successors(
    state:        HENSState,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float,
) -> List[HENSState]:
    """Return all valid child states of `state`."""
    successors: List[HENSState] = []

    all_feasible = get_feasible_matches(
        state=state,
        hot_streams=hot_streams,
        cold_streams=cold_streams,
        delta_T_min=delta_T_min,
        already_matched_fn=state.already_matched,
    )

    hot_with_match  = set(h for h, c, _ in all_feasible)
    cold_with_match = set(c for h, c, _ in all_feasible)

    # P4: pick the first hot stream with remaining load that has a feasible match
    anchor_hot = None
    for h_id in hot_streams:
        if state.hot_remaining.get(h_id, 0) > TOLERANCE and h_id in hot_with_match:
            anchor_hot = h_id
            break

    # Process matches — anchor hot only
    if anchor_hot is not None:
        for h_id, c_id, max_duty in all_feasible:
            if h_id != anchor_hot or max_duty < TOLERANCE:
                continue
            successors.append(
                action_match(state, h_id, c_id, max_duty, hot_streams, cold_streams)
            )

    # Steam heaters — only when cold stream has no process match
    for c_id, c_rem in state.cold_remaining.items():
        if c_rem > TOLERANCE and c_id not in cold_with_match:
            successors.append(action_add_heater(state, c_id, c_rem))

    # Cooling water — only when hot stream has no process match
    for h_id, h_rem in state.hot_remaining.items():
        if h_rem > TOLERANCE and h_id not in hot_with_match:
            successors.append(action_add_cooler(state, h_id, h_rem))

    return successors
