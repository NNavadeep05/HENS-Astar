"""
actions.py  (v2 — Decision-Tree Action Generator)
===================================================
Generates successor nodes in the HENS A* decision tree.

ACTION TAXONOMY
---------------
At each node (tree level k), the branching choices are:

  1. MATCH(Hi, Cj)  — place a process heat exchanger
       • Only if (Hi, Cj) NOT already in the matrix  ← matrix pruning
       • Only if ΔTmin constraint is satisfied        ← thermodynamic pruning
       • Transfers the full feasible duty (min of remaining loads)

  2. ADD_HEATER(Cj) — use external steam on cold stream Cj
       • Only offered when Cj has NO feasible process match available
       • Moves to the utility-finalization phase

  3. ADD_COOLER(Hi) — use external cooling water on hot stream Hi
       • Only offered when Hi has NO feasible process match available
       • Moves to the utility-finalization phase

PRUNING RULES ENFORCED HERE
----------------------------
  P1. Skip (Hi, Cj) if already in the matrix  [NetworkMatrix.is_matched]
  P2. Skip matches violating ΔTmin             [constraints.is_feasible_match]
  P3. Utilities only when NO process options remain for that stream
  P4. Canonical pair ordering: to prevent (H1→C1 then H2→C2) and
      (H2→C2 then H1→C1) being explored as separate branches, we
      enforce that new matches use the LOWEST-INDEXED unmatched hot stream
      that still has remaining load. This collapses equivalent orderings
      into a single path through the tree.

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
from typing import Dict, List, TYPE_CHECKING

from state import HENSState, ExchangerMatch, UtilityHeater, UtilityCooler
from constraints import get_feasible_matches, current_hot_temp, current_cold_temp
from cost import compute_g_cost

if TYPE_CHECKING:
    from state import HotStream, ColdStream


TOLERANCE = 0.5   # kW — loads below this are considered satisfied


# ===========================================================================
# Action 1: Place a process heat exchanger
# ===========================================================================

def action_match(
    state:       HENSState,
    hot_id:      str,
    cold_id:     str,
    duty:        float,
    hot_streams: Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
) -> HENSState:
    """
    Place HX(hot_id, cold_id) transferring `duty` kW.

    Updates:
      • matrix[cold_id][hot_id] = next match order
      • hot_remaining[hot_id]   reduced by duty
      • cold_remaining[cold_id] reduced by duty
      • matches tuple extended
      • tree_level incremented by 1  (new tree level)
      • g_cost incremented by exchanger cost
    """
    hot  = hot_streams[hot_id]
    cold = cold_streams[cold_id]

    h_rem = state.hot_remaining[hot_id]
    c_rem = state.cold_remaining[cold_id]

    # Reconstruct temperatures at this point for cost calculation
    T_h_in  = current_hot_temp(hot,  h_rem)
    T_h_out = T_h_in - duty / hot.FCp
    T_c_in  = current_cold_temp(cold, c_rem)
    T_c_out = T_c_in + duty / cold.FCp

    new_g = compute_g_cost(
        prev_g      = state.g_cost,
        action_type = "match",
        duty        = duty,
        T_h_in      = T_h_in,
        T_h_out     = T_h_out,
        T_c_in      = T_c_in,
        T_c_out     = T_c_out,
    )

    # Build successor
    succ = state.clone()
    order = succ.num_exchangers() + 1          # 1-based sequence in matrix
    succ.matrix.set(cold_id, hot_id, order)   # record in matrix
    succ.hot_remaining[hot_id]   = max(0.0, h_rem - duty)
    succ.cold_remaining[cold_id] = max(0.0, c_rem - duty)
    succ.matches  = state.matches + (ExchangerMatch(hot_id, cold_id, duty, order),)
    succ.tree_level += 1
    succ.g_cost   = new_g
    return succ


# ===========================================================================
# Action 2: Add external steam heater
# ===========================================================================

def action_add_heater(state: HENSState, cold_id: str, duty: float) -> HENSState:
    """Supply `duty` kW of steam to cold stream `cold_id`."""
    new_g = compute_g_cost(
        prev_g      = state.g_cost,
        action_type = "heater",
        duty        = duty,
    )
    succ = state.clone()
    succ.cold_remaining[cold_id] = max(0.0, state.cold_remaining[cold_id] - duty)
    succ.heaters  = state.heaters + (UtilityHeater(cold_id, duty),)
    succ.g_cost   = new_g
    return succ


# ===========================================================================
# Action 3: Add external cooling-water cooler
# ===========================================================================

def action_add_cooler(state: HENSState, hot_id: str, duty: float) -> HENSState:
    """Remove `duty` kW via cooling water from hot stream `hot_id`."""
    new_g = compute_g_cost(
        prev_g      = state.g_cost,
        action_type = "cooler",
        duty        = duty,
    )
    succ = state.clone()
    succ.hot_remaining[hot_id] = max(0.0, state.hot_remaining[hot_id] - duty)
    succ.coolers  = state.coolers + (UtilityCooler(hot_id, duty),)
    succ.g_cost   = new_g
    return succ


# ===========================================================================
# Master successor generator — called by A* at each frontier node
# ===========================================================================

def get_successors(
    state:        HENSState,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float,
) -> List[HENSState]:
    """
    Generate all valid children of `state` in the decision tree.

    DECISION TREE STRUCTURE
    -----------------------
    Level k node → children at level k+1 (one new HX each)

    Ordering pruning (P4):
      We fix the "next hot stream" as the lowest-indexed hot stream
      that still has remaining load AND at least one feasible cold match.
      For each such hot stream, we branch over all feasible cold partners.
      This eliminates commutative-order duplicates.

    Utility actions:
      Offered only for streams that have NO feasible process partner.
    """
    successors: List[HENSState] = []

    # ---- Collect all feasible (Hi, Cj) candidates (after pruning P1, P2) --
    all_feasible = get_feasible_matches(
        state        = state,
        hot_streams  = hot_streams,
        cold_streams = cold_streams,
        delta_T_min  = delta_T_min,
        already_matched_fn = state.already_matched,   # P1: matrix check
    )

    # Sets for utility eligibility
    hot_with_match  = set(h for h, c, _ in all_feasible)
    cold_with_match = set(c for h, c, _ in all_feasible)

    # ---- Pruning P4: fix the anchor hot stream ----------------------------
    # Pick the FIRST (by original order) hot stream that has remaining load
    # AND appears in at least one feasible pair.
    anchor_hot = None
    for h_id in hot_streams.keys():   # preserves insertion order
        if (state.hot_remaining.get(h_id, 0) > TOLERANCE
                and h_id in hot_with_match):
            anchor_hot = h_id
            break

    # ---- 1. Process match actions (only via anchor hot) -------------------
    if anchor_hot is not None:
        for h_id, c_id, max_duty in all_feasible:
            if h_id != anchor_hot:
                continue                  # enforce canonical ordering
            if max_duty < TOLERANCE:
                continue
            succ = action_match(state, h_id, c_id, max_duty,
                                 hot_streams, cold_streams)
            successors.append(succ)

    # ---- 2. Utility heaters (only when cold stream has no process option) -
    for c_id, c_rem in state.cold_remaining.items():
        if c_rem <= TOLERANCE:
            continue
        if c_id not in cold_with_match:
            succ = action_add_heater(state, c_id, c_rem)
            successors.append(succ)

    # ---- 3. Utility coolers (only when hot stream has no process option) --
    for h_id, h_rem in state.hot_remaining.items():
        if h_rem <= TOLERANCE:
            continue
        if h_id not in hot_with_match:
            succ = action_add_cooler(state, h_id, h_rem)
            successors.append(succ)

    return successors
