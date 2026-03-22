"""
state.py
========
State representation for the HENS A* decision tree.

The network topology is stored as a 2D match matrix (NetworkMatrix):
  rows    = cold streams, columns = hot streams
  entry   = placement order (1-based) if matched, 0 if empty

The matrix uniquely identifies the network, enables O(1) duplicate
detection, and serves as the hash key for the A* visited set.

Decision tree view:
  Level 0  : empty matrix, all streams at full load
  Level k  : k process exchangers placed
  Each edge: one Match(Hi, Cj, duty) action

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Stream definitions (immutable input data, not part of the search state)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HotStream:
    """Process stream to be cooled from T_in to T_out."""
    sid:   str
    T_in:  float  # supply temperature (C)
    T_out: float  # target temperature (C)
    FCp:   float  # heat capacity flow rate (kW/C)

    @property
    def Q_total(self) -> float:
        return self.FCp * (self.T_in - self.T_out)


@dataclass(frozen=True)
class ColdStream:
    """Process stream to be heated from T_in to T_out."""
    sid:   str
    T_in:  float
    T_out: float
    FCp:   float

    @property
    def Q_total(self) -> float:
        return self.FCp * (self.T_out - self.T_in)


# ---------------------------------------------------------------------------
# Match and utility records (frozen for immutability and hashing)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExchangerMatch:
    hot_id:  str
    cold_id: str
    duty:    float  # kW transferred
    order:   int    # placement sequence number (1-based)

    def __repr__(self) -> str:
        return f"HX{self.order}({self.hot_id}<->{self.cold_id}, {self.duty:.1f} kW)"


@dataclass(frozen=True)
class UtilityHeater:
    cold_id: str
    duty:    float  # kW supplied by steam

    def __repr__(self) -> str:
        return f"Steam({self.cold_id}, {self.duty:.1f} kW)"


@dataclass(frozen=True)
class UtilityCooler:
    hot_id: str
    duty:   float  # kW removed by cooling water

    def __repr__(self) -> str:
        return f"CW({self.hot_id}, {self.duty:.1f} kW)"


# ---------------------------------------------------------------------------
# NetworkMatrix
# ---------------------------------------------------------------------------

class NetworkMatrix:
    """
    2D match matrix keyed by (cold_id, hot_id).
    Value is the exchanger placement order (1-based), or 0 if unmatched.
    """

    def __init__(self, hot_ids: List[str], cold_ids: List[str]):
        self.hot_ids  = list(hot_ids)
        self.cold_ids = list(cold_ids)
        self._data: Dict[Tuple[str, str], int] = {}

    def set(self, cold_id: str, hot_id: str, order: int) -> None:
        self._data[(cold_id, hot_id)] = order

    def get(self, cold_id: str, hot_id: str) -> int:
        return self._data.get((cold_id, hot_id), 0)

    def is_matched(self, cold_id: str, hot_id: str) -> bool:
        return self._data.get((cold_id, hot_id), 0) > 0

    def copy(self) -> "NetworkMatrix":
        m = NetworkMatrix(self.hot_ids, self.cold_ids)
        m._data = dict(self._data)
        return m

    def to_frozenset(self) -> frozenset:
        return frozenset(self._data.items())

    def __repr__(self) -> str:
        col_w  = 7
        header = " " * 6 + "".join(f"{h:>{col_w}}" for h in self.hot_ids)
        lines  = [header, "-" * len(header)]
        for c_id in self.cold_ids:
            row = f"{c_id:<6}"
            for h_id in self.hot_ids:
                val  = self.get(c_id, h_id)
                cell = f"[{val}]" if val > 0 else " . "
                row += f"{cell:>{col_w}}"
            lines.append(row)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HENSState — one node in the decision tree
# ---------------------------------------------------------------------------

class HENSState:
    """
    A* search node. Holds the current match matrix, remaining stream loads,
    placed exchangers and utilities, tree depth, and accumulated cost.
    """

    TOLERANCE = 0.5  # kW — residual below this is treated as satisfied

    def __init__(
        self,
        matrix:         NetworkMatrix,
        hot_remaining:  Dict[str, float],
        cold_remaining: Dict[str, float],
        matches:        Tuple[ExchangerMatch, ...] = (),
        heaters:        Tuple[UtilityHeater, ...]  = (),
        coolers:        Tuple[UtilityCooler, ...]  = (),
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

    def is_goal(self) -> bool:
        """True when all stream duties are satisfied within tolerance."""
        return (all(v <= self.TOLERANCE for v in self.hot_remaining.values()) and
                all(v <= self.TOLERANCE for v in self.cold_remaining.values()))

    def total_hot_remaining(self) -> float:
        return sum(max(0.0, v) for v in self.hot_remaining.values())

    def total_cold_remaining(self) -> float:
        return sum(max(0.0, v) for v in self.cold_remaining.values())

    def num_exchangers(self) -> int:
        return len(self.matches)

    def num_utilities(self) -> int:
        return len(self.heaters) + len(self.coolers)

    def already_matched(self, hot_id: str, cold_id: str) -> bool:
        return self.matrix.is_matched(cold_id, hot_id)

    def _state_key(self):
        """Canonical key for hashing and duplicate detection."""
        return (
            self.matrix.to_frozenset(),
            frozenset((k, round(v, 1)) for k, v in self.hot_remaining.items()),
            frozenset((k, round(v, 1)) for k, v in self.cold_remaining.items()),
        )

    def __hash__(self) -> int:
        return hash(self._state_key())

    def __eq__(self, other) -> bool:
        return isinstance(other, HENSState) and self._state_key() == other._state_key()

    def __lt__(self, other) -> bool:
        return self.g_cost < other.g_cost

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

    def __repr__(self) -> str:
        return (
            f"HENSState(level={self.tree_level}, g={self.g_cost:.0f}, "
            f"HXs={self.num_exchangers()}, "
            f"hot_rem={self.total_hot_remaining():.1f} kW, "
            f"cold_rem={self.total_cold_remaining():.1f} kW)\n"
            f"  Matrix:\n{self.matrix}"
        )


# ---------------------------------------------------------------------------
# Root node factory
# ---------------------------------------------------------------------------

def make_initial_state(
    hot_streams:  List[HotStream],
    cold_streams: List[ColdStream],
) -> HENSState:
    """Build the root node: empty matrix, all streams at full load, level 0."""
    matrix = NetworkMatrix(
        [h.sid for h in hot_streams],
        [c.sid for c in cold_streams],
    )
    return HENSState(
        matrix         = matrix,
        hot_remaining  = {h.sid: h.Q_total for h in hot_streams},
        cold_remaining = {c.sid: c.Q_total for c in cold_streams},
        tree_level     = 0,
    )
