"""
state.py  (v2 — Matrix-Based Decision Tree)
============================================
State representation for Heat Exchanger Network Synthesis (HENS).

DESIGN: Matrix-based representation
------------------------------------
The HEN topology is stored as a 2D match matrix:
  - rows    → cold streams  (C1, C2, …)
  - columns → hot streams   (H1, H2, …)
  - entry   → match_order (1-based int) if matched, 0 if no match

This matrix UNIQUELY identifies the network topology and is used for:
  1. Hashing / duplicate detection in the A* visited set
  2. Visualizing the grid-style HEN diagram
  3. Pruning: reject any (Hi, Cj) pair already matched

DECISION TREE VIEW
------------------
  Root  (level 0) : empty matrix, all loads at full duty
  Level k          : k process matches have been placed
  Each edge        : one Match(Hi, Cj, duty) action

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ===========================================================================
# Stream definitions  (immutable input data — not part of the search state)
# ===========================================================================

@dataclass(frozen=True)
class HotStream:
    """A process stream that must be cooled from T_in to T_out."""
    sid:  str    # identifier, e.g. "H1"
    T_in: float  # supply temperature (°C)
    T_out: float # target temperature (°C)
    FCp:  float  # heat-capacity flow rate (kW/°C)

    @property
    def Q_total(self) -> float:
        """Total heat that must be removed (kW)."""
        return self.FCp * (self.T_in - self.T_out)


@dataclass(frozen=True)
class ColdStream:
    """A process stream that must be heated from T_in to T_out."""
    sid:  str
    T_in: float
    T_out: float
    FCp:  float

    @property
    def Q_total(self) -> float:
        """Total heat that must be added (kW)."""
        return self.FCp * (self.T_out - self.T_in)


# ===========================================================================
# Match / utility records  (tuple-based for immutability & hashing)
# ===========================================================================

@dataclass(frozen=True)
class ExchangerMatch:
    """One process-to-process heat exchanger placed in the network."""
    hot_id:  str
    cold_id: str
    duty:    float    # kW transferred
    order:   int      # sequence number (1-based) → stored in the matrix

    def __repr__(self) -> str:
        return f"HX{self.order}({self.hot_id}↔{self.cold_id}, {self.duty:.1f} kW)"


@dataclass(frozen=True)
class UtilityHeater:
    """External steam heater supplying heat to a cold stream."""
    cold_id: str
    duty:    float    # kW supplied

    def __repr__(self) -> str:
        return f"Steam({self.cold_id}, {self.duty:.1f} kW)"


@dataclass(frozen=True)
class UtilityCooler:
    """External cooling-water cooler removing heat from a hot stream."""
    hot_id: str
    duty:   float     # kW removed

    def __repr__(self) -> str:
        return f"CW({self.hot_id}, {self.duty:.1f} kW)"


# ===========================================================================
# NetworkMatrix — 2D representation of the HEN topology
# ===========================================================================

class NetworkMatrix:
    """
    2D match matrix for the HEN.

    Indexed by (cold_id, hot_id).
    Value = match_order (int, 1-based) if an exchanger exists, else 0.

    This captures the COMPLETE topology of the network in a form that:
      • Is unique (no ordering ambiguity — only the SET of matches matters)
      • Can be hashed for the visited-state set
      • Can be printed as a readable grid
    """

    def __init__(self, hot_ids: List[str], cold_ids: List[str]):
        self.hot_ids  = list(hot_ids)
        self.cold_ids = list(cold_ids)
        # matrix[cold_idx][hot_idx] = order (0 = empty)
        self._data: Dict[Tuple[str, str], int] = {}

    def set(self, cold_id: str, hot_id: str, order: int) -> None:
        self._data[(cold_id, hot_id)] = order

    def get(self, cold_id: str, hot_id: str) -> int:
        return self._data.get((cold_id, hot_id), 0)

    def is_matched(self, cold_id: str, hot_id: str) -> bool:
        """Return True if (Hi, Cj) already has an exchanger."""
        return self._data.get((cold_id, hot_id), 0) > 0

    def copy(self) -> "NetworkMatrix":
        m = NetworkMatrix(self.hot_ids, self.cold_ids)
        m._data = dict(self._data)
        return m

    def to_frozenset(self) -> frozenset:
        """Hashable representation — only non-zero cells matter."""
        return frozenset(self._data.items())

    def __repr__(self) -> str:
        """Pretty-print as a grid table."""
        col_w = 7
        header = " " * 6 + "".join(f"{h:>{col_w}}" for h in self.hot_ids)
        lines  = [header, "-" * len(header)]
        for c_id in self.cold_ids:
            row = f"{c_id:<6}"
            for h_id in self.hot_ids:
                val = self.get(c_id, h_id)
                cell = f"[{val}]" if val > 0 else " · "
                row += f"{cell:>{col_w}}"
            lines.append(row)
        return "\n".join(lines)


# ===========================================================================
# HENSState — one node in the A* decision tree
# ===========================================================================

class HENSState:
    """
    A node in the A* decision-tree for Heat Exchanger Network Synthesis.

    Attributes
    ----------
    matrix         : NetworkMatrix  — 2D match topology
    hot_remaining  : {hot_id: remaining_load_kW}
    cold_remaining : {cold_id: remaining_demand_kW}
    matches        : tuple[ExchangerMatch]  — ordered list of placed HXs
    heaters        : tuple[UtilityHeater]
    coolers        : tuple[UtilityCooler]
    tree_level     : int  — depth in the decision tree (= number of HX matches)
    g_cost         : float  — accumulated TAC cost so far
    parent         : HENSState | None  — back-pointer for path reconstruction
    """

    TOLERANCE = 0.5   # kW — residual below this is treated as fully satisfied

    def __init__(
        self,
        matrix:         NetworkMatrix,
        hot_remaining:  Dict[str, float],
        cold_remaining: Dict[str, float],
        matches:        Tuple[ExchangerMatch, ...]  = (),
        heaters:        Tuple[UtilityHeater, ...]   = (),
        coolers:        Tuple[UtilityCooler, ...]   = (),
        tree_level:     int   = 0,
        g_cost:         float = 0.0,
        parent:         Optional["HENSState"] = None,
    ):
        self.matrix         = matrix
        self.hot_remaining  = dict(hot_remaining)
        self.cold_remaining = dict(cold_remaining)
        self.matches        = tuple(matches)
        self.heaters        = tuple(heaters)
        self.coolers        = tuple(coolers)
        self.tree_level     = tree_level
        self.g_cost         = g_cost
        self.parent         = parent

    # ------------------------------------------------------------------
    # Goal test
    # ------------------------------------------------------------------

    def is_goal(self) -> bool:
        """All streams satisfied within tolerance."""
        return (all(v <= self.TOLERANCE for v in self.hot_remaining.values()) and
                all(v <= self.TOLERANCE for v in self.cold_remaining.values()))

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def total_hot_remaining(self)  -> float:
        return sum(max(0.0, v) for v in self.hot_remaining.values())

    def total_cold_remaining(self) -> float:
        return sum(max(0.0, v) for v in self.cold_remaining.values())

    def num_exchangers(self) -> int:
        return len(self.matches)

    def num_utilities(self) -> int:
        return len(self.heaters) + len(self.coolers)

    def already_matched(self, hot_id: str, cold_id: str) -> bool:
        """Check matrix — prevents duplicate (Hi, Cj) pairs."""
        return self.matrix.is_matched(cold_id, hot_id)

    # ------------------------------------------------------------------
    # Hashing & equality  (key for A* visited set)
    # ------------------------------------------------------------------

    def _state_key(self):
        """
        Canonical key based on the matrix topology + remaining loads.
        Two states are EQUAL iff they have the same matches (regardless of order)
        AND same remaining duties.  This is the matrix-based duplicate pruning.
        """
        matrix_key = self.matrix.to_frozenset()
        hot_key    = frozenset((k, round(v, 1)) for k, v in self.hot_remaining.items())
        cold_key   = frozenset((k, round(v, 1)) for k, v in self.cold_remaining.items())
        return (matrix_key, hot_key, cold_key)

    def __hash__(self) -> int:
        return hash(self._state_key())

    def __eq__(self, other) -> bool:
        if not isinstance(other, HENSState):
            return False
        return self._state_key() == other._state_key()

    def __lt__(self, other) -> bool:
        """Tie-break for heapq — lower g_cost preferred."""
        return self.g_cost < other.g_cost

    # ------------------------------------------------------------------
    # Clone (produces successor with back-pointer set to self)
    # ------------------------------------------------------------------

    def clone(self) -> "HENSState":
        return HENSState(
            matrix         = self.matrix.copy(),
            hot_remaining  = dict(self.hot_remaining),
            cold_remaining = dict(self.cold_remaining),
            matches        = self.matches,
            heaters        = self.heaters,
            coolers        = self.coolers,
            tree_level     = self.tree_level,
            g_cost         = self.g_cost,
            parent         = self,
        )

    # ------------------------------------------------------------------
    # Pretty-print
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"HENSState(level={self.tree_level}, "
            f"g={self.g_cost:.0f}, "
            f"HXs={self.num_exchangers()}, "
            f"hot_rem={self.total_hot_remaining():.1f} kW, "
            f"cold_rem={self.total_cold_remaining():.1f} kW)\n"
            f"  Matrix:\n{self.matrix}"
        )


# ===========================================================================
# Factory — build root node (level 0 of the decision tree)
# ===========================================================================

def make_initial_state(
    hot_streams:  List[HotStream],
    cold_streams: List[ColdStream],
) -> HENSState:
    """
    Root node of the decision tree.
    • Empty matrix (no matches)
    • All streams at full thermal load
    • tree_level = 0
    """
    hot_ids  = [h.sid for h in hot_streams]
    cold_ids = [c.sid for c in cold_streams]
    matrix   = NetworkMatrix(hot_ids, cold_ids)

    hot_remaining  = {h.sid: h.Q_total for h in hot_streams}
    cold_remaining = {c.sid: c.Q_total for c in cold_streams}

    return HENSState(
        matrix         = matrix,
        hot_remaining  = hot_remaining,
        cold_remaining = cold_remaining,
        tree_level     = 0,
    )
