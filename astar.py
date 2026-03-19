"""
astar.py  (v2 — Decision-Tree A* Search)
==========================================
A* Search engine structured explicitly as a decision tree for HENS.

DECISION TREE STRUCTURE
------------------------
  Root node   (level 0) : empty network matrix, all streams at full load
  Level k node          : k process HX matches placed
  Each child edge       : one MATCH action (or a utility finalization)
  Branching factor      : number of feasible (Hi, Cj) pairs via anchor-hot rule
  Depth limit           : ≤ n_hot × n_cold  (all pairs matched at most once)

SEARCH ALGORITHM
-----------------
Standard A* with:
  • min-heap priority queue on f(n) = g(n) + h(n)
  • Visited-state set using matrix-based hash (state._state_key)
  • Pruning inside get_successors (P1–P4)

OPTIMALITY: guaranteed because h(n) is admissible (see heuristic.py).

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from state    import HENSState, make_initial_state
from heuristic import heuristic
from actions   import get_successors

if TYPE_CHECKING:
    from state import HotStream, ColdStream


# ===========================================================================
# Result container
# ===========================================================================

@dataclass
class AStarResult:
    """Return value from the A* search."""
    success:          bool
    goal_state:       Optional[HENSState]
    path:             List[HENSState]   # root → goal
    nodes_expanded:   int
    nodes_generated:  int
    time_seconds:     float
    # Decision-tree statistics
    max_tree_depth:   int               # deepest level reached
    tree_level_stats: Dict[int, int]    # {level: nodes_expanded_at_that_level}

    def __repr__(self) -> str:
        if not self.success:
            return "AStarResult(FAILED — no solution found)"
        return (
            f"AStarResult(\n"
            f"  success          = True\n"
            f"  g_cost (TAC)     = {self.goal_state.g_cost:.2f} $/yr\n"
            f"  exchangers       = {self.goal_state.num_exchangers()}\n"
            f"  utilities        = {self.goal_state.num_utilities()}\n"
            f"  tree_depth_final = {self.goal_state.tree_level}\n"
            f"  nodes_expanded   = {self.nodes_expanded}\n"
            f"  nodes_generated  = {self.nodes_generated}\n"
            f"  max_tree_depth   = {self.max_tree_depth}\n"
            f"  time             = {self.time_seconds:.3f} s\n"
            f")"
        )


# ===========================================================================
# Priority queue item wrapper
# ===========================================================================

@dataclass(order=True)
class PQItem:
    """
    Heap element: (f_value, tie_breaker, state).
    tie_breaker is a monotone counter that prevents heapq from comparing states.
    Prefer nodes at shallower tree levels on ties (breadth-first tie-breaking
    guides A* to explore the most promising paths first).
    """
    f_value:     float
    tree_level:  int          # deeper levels slightly deprioritised on equal f
    tie_breaker: int
    state: HENSState = field(compare=False)


# ===========================================================================
# Core A* function
# ===========================================================================

def astar_search(
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float,
    max_nodes:    int  = 100_000,
    verbose:      bool = True,
) -> AStarResult:
    """
    Run A* search on the HENS decision tree.

    Parameters
    ----------
    hot_streams   : {id: HotStream}
    cold_streams  : {id: ColdStream}
    delta_T_min   : minimum temperature approach (°C)
    max_nodes     : node expansion limit (safety cap)
    verbose       : print progress to console

    Returns
    -------
    AStarResult
    """
    t_start = time.time()

    # ---- Root node ---------------------------------------------------------
    start = make_initial_state(list(hot_streams.values()), list(cold_streams.values()))
    h0    = heuristic(start, hot_streams, cold_streams, delta_T_min)
    f0    = start.g_cost + h0

    frontier: list = []
    heapq.heappush(frontier, PQItem(f0, 0, 0, start))

    visited: set = set()
    counter  = 0
    nodes_expanded   = 0
    nodes_generated  = 1
    max_depth_seen   = 0
    level_stats: Dict[int, int] = {}

    if verbose:
        print(f"\n{'='*65}")
        print(f"  A* HENS Decision-Tree Search")
        print(f"  Problem : {len(hot_streams)}H × {len(cold_streams)}C streams")
        print(f"  ΔT_min  : {delta_T_min} °C")
        print(f"  Root    : level 0 (empty matrix)")
        print(f"{'='*65}")
        _print_header()

    # ---- Main A* loop ------------------------------------------------------
    while frontier:
        item  = heapq.heappop(frontier)
        state = item.state

        # ----- Visited-set pruning: skip re-expanded states -----------------
        key = hash(state)
        if key in visited:
            continue
        visited.add(key)

        nodes_expanded += 1
        depth = state.tree_level
        max_depth_seen = max(max_depth_seen, depth)
        level_stats[depth] = level_stats.get(depth, 0) + 1

        # ----- GOAL TEST ----------------------------------------------------
        if state.is_goal():
            t_end = time.time()
            path  = _reconstruct_path(state)
            if verbose:
                print(f"\n{'='*65}")
                print(f"  ✓ GOAL REACHED  [tree level {state.tree_level}]")
                print(f"  TAC        = ${state.g_cost:,.2f} /yr")
                print(f"  Exchangers = {state.num_exchangers()}")
                print(f"  Utilities  = {state.num_utilities()}")
                print(f"  Nodes exp. = {nodes_expanded:,}")
                print(f"  Time       = {t_end - t_start:.3f} s")
                print(f"\n  Network Matrix:")
                print(state.matrix)
                print(f"{'='*65}\n")
            return AStarResult(
                success          = True,
                goal_state       = state,
                path             = path,
                nodes_expanded   = nodes_expanded,
                nodes_generated  = nodes_generated,
                time_seconds     = t_end - t_start,
                max_tree_depth   = max_depth_seen,
                tree_level_stats = level_stats,
            )

        # ----- Safety cap ---------------------------------------------------
        if nodes_expanded >= max_nodes:
            if verbose:
                print(f"\n  ⚠ Node cap ({max_nodes:,}) reached — stopping.")
            break

        # ----- Expand: generate tree children --------------------------------
        successors = get_successors(state, hot_streams, cold_streams, delta_T_min)
        nodes_generated += len(successors)

        for succ in successors:
            if hash(succ) not in visited:
                h_val = heuristic(succ, hot_streams, cold_streams, delta_T_min)
                f_val = succ.g_cost + h_val
                counter += 1
                heapq.heappush(frontier,
                    PQItem(f_val, succ.tree_level, counter, succ))

        # ----- Progress log -------------------------------------------------
        if verbose and nodes_expanded % 200 == 0:
            best_f = frontier[0].f_value if frontier else 0.0
            _print_row(nodes_expanded, depth, item.f_value, state.g_cost,
                       state.total_hot_remaining(), state.total_cold_remaining(),
                       state.num_exchangers(), best_f)

    # ---- Failure -----------------------------------------------------------
    t_end = time.time()
    if verbose:
        print(f"\n  ✗ No solution found within {nodes_expanded:,} expansions.")
    return AStarResult(
        success          = False,
        goal_state       = None,
        path             = [],
        nodes_expanded   = nodes_expanded,
        nodes_generated  = nodes_generated,
        time_seconds     = t_end - t_start,
        max_tree_depth   = max_depth_seen,
        tree_level_stats = level_stats,
    )


# ===========================================================================
# Path reconstruction
# ===========================================================================

def _reconstruct_path(goal: HENSState) -> List[HENSState]:
    """Trace parent back-pointers: goal → root, then reverse."""
    path, node = [], goal
    while node is not None:
        path.append(node)
        node = node.parent
    return list(reversed(path))


# ===========================================================================
# Verbose helpers
# ===========================================================================

def _print_header():
    print(f"{'Exp':>7} {'Lvl':>4} {'f(n)':>11} {'g(n)':>11} "
          f"{'HRem':>8} {'CRem':>8} {'HXs':>4} {'BestF':>11}")
    print("-" * 72)

def _print_row(exp, lvl, f, g, hr, cr, hxs, bf):
    print(f"{exp:>7,} {lvl:>4} {f:>11,.0f} {g:>11,.0f} "
          f"{hr:>8.1f} {cr:>8.1f} {hxs:>4} {bf:>11,.0f}")
