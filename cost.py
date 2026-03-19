"""
cost.py
=======
Cost model for Heat Exchanger Network Synthesis (HENS).

Computes:
  1. Exchanger capital cost  (annualized, area-based)
  2. Utility operating cost  (steam and cooling water)
  3. Total Annualized Cost   (TAC = annualized capital + operating)

Cost model reference: Chen (1987) log-mean temperature approximation
    A = Q / (U × ΔT_lm)
    Capital_cost = a + b × A^c     (standard cost law)

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
import math
from typing import Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream, ExchangerMatch


# ---------------------------------------------------------------------------
# Cost parameters  (adjustable)
# ---------------------------------------------------------------------------

# Overall heat-transfer coefficient  (kW / m² °C)  — average approximation
U_DEFAULT = 0.5

# Area-cost law:  Capital ($) = COST_A + COST_B × Area^COST_C
COST_A = 8_000.0    # fixed cost per unit ($)
COST_B = 1_200.0    # variable cost coefficient ($/m^COST_C)
COST_C = 0.6        # cost exponent (economies of scale)

# Annualisation factor (fraction of capital per year; e.g. 25% for 4-yr payback)
ANNUALISATION_FACTOR = 0.25

# Utility costs ($/kW·year)
STEAM_COST_PER_KW_YEAR    = 160.0   # external heating (steam)
COOLING_COST_PER_KW_YEAR  =  60.0   # external cooling (cooling water)

# Penalty per additional exchanger unit (to drive fewer units)
UNIT_PENALTY = 5_000.0   # $ per exchanger


# ---------------------------------------------------------------------------
# Log-mean temperature difference
# ---------------------------------------------------------------------------

def delta_T_lm(T_h_in: float, T_h_out: float, T_c_in: float, T_c_out: float) -> float:
    """
    Chen (1987) approximation for ΔT_lm (counter-current exchanger):
        ΔT_lm ≈ ((ΔT1 × ΔT2 × (ΔT1+ΔT2)/2)) ^(1/3)

    Falls back to arithmetic mean when ΔT1 = ΔT2.
    """
    dT1 = T_h_in  - T_c_out   # hot inlet  vs cold outlet
    dT2 = T_h_out - T_c_in    # hot outlet vs cold inlet

    # Clamp to small positive to avoid math errors
    dT1 = max(dT1, 0.1)
    dT2 = max(dT2, 0.1)

    if abs(dT1 - dT2) < 1e-6:
        return dT1   # identical → use directly

    # Chen approximation
    return ((dT1 * dT2 * (dT1 + dT2) / 2.0)) ** (1.0 / 3.0)


# ---------------------------------------------------------------------------
# Exchanger capital cost
# ---------------------------------------------------------------------------

def exchanger_area(duty: float, T_h_in: float, T_h_out: float,
                   T_c_in: float, T_c_out: float,
                   U: float = U_DEFAULT) -> float:
    """
    Required heat-exchanger area (m²) for a given duty and temperature profile.
        A = Q / (U × ΔT_lm)
    """
    dtlm = delta_T_lm(T_h_in, T_h_out, T_c_in, T_c_out)
    if dtlm < 1e-6:
        return float("inf")
    return duty / (U * dtlm)


def exchanger_capital_cost(area: float) -> float:
    """Purchased + installed cost ($ per exchanger) using power-law correlation."""
    return COST_A + COST_B * (area ** COST_C)


def annualised_exchanger_cost(area: float) -> float:
    """Annual capital charge ($/year)."""
    return exchanger_capital_cost(area) * ANNUALISATION_FACTOR


# ---------------------------------------------------------------------------
# Full cost of a single ExchangerMatch
# ---------------------------------------------------------------------------

def match_cost(
    match: "ExchangerMatch",
    hot_streams: Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    hot_remaining_before: float,
    cold_remaining_before: float,
) -> float:
    """
    Annualised capital cost ($/ yr) for one process-to-process heat exchanger.

    We reconstruct the temperature profile from remaining loads before transfer.
    """
    from constraints import current_hot_temp, current_cold_temp

    hot  = hot_streams[match.hot_id]
    cold = cold_streams[match.cold_id]

    T_h_in  = current_hot_temp(hot,  hot_remaining_before)
    T_h_out = T_h_in - match.duty / hot.FCp

    T_c_in  = current_cold_temp(cold, cold_remaining_before)
    T_c_out = T_c_in + match.duty / cold.FCp

    area = exchanger_area(match.duty, T_h_in, T_h_out, T_c_in, T_c_out)
    return annualised_exchanger_cost(area) + UNIT_PENALTY


# ---------------------------------------------------------------------------
# Utility operating costs
# ---------------------------------------------------------------------------

def utility_heater_cost(duty: float) -> float:
    """Annual operating cost of an external heater supplying `duty` kW."""
    return duty * STEAM_COST_PER_KW_YEAR


def utility_cooler_cost(duty: float) -> float:
    """Annual operating cost of an external cooler removing `duty` kW."""
    return duty * COOLING_COST_PER_KW_YEAR


# ---------------------------------------------------------------------------
# Total Annualized Cost  (TAC) of a complete / partial solution state
# ---------------------------------------------------------------------------

def compute_tac(
    state: "HENSState",
    hot_streams: Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
) -> float:
    """
    Compute the Total Annualized Cost (TAC) of the network represented by `state`.

    TAC = Σ annualised_exchanger_cost(match)
        + Σ utility_heater_cost(heater)
        + Σ utility_cooler_cost(cooler)

    Note: We approximate match temperatures using stream start-points because full
    history is not stored. For final reporting main.py recomputes from the path.
    """
    tac = 0.0

    # --- Process-to-process exchangers ---
    for match in state.matches:
        hot  = hot_streams[match.hot_id]
        cold = cold_streams[match.cold_id]
        # Approximate: use full stream temperatures (conservative estimate)
        area = exchanger_area(
            match.duty,
            hot.T_in,  hot.T_out,
            cold.T_in, cold.T_out,
        )
        tac += annualised_exchanger_cost(area) + UNIT_PENALTY

    # --- Utility heaters ---
    for heater in state.heaters:
        tac += utility_heater_cost(heater.duty)

    # --- Utility coolers ---
    for cooler in state.coolers:
        tac += utility_cooler_cost(cooler.duty)

    return tac


def compute_g_cost(
    prev_g: float,
    action_type: str,
    duty: float,
    hot_id: str = "",
    cold_id: str = "",
    hot_streams: Dict = None,
    cold_streams: Dict = None,
    T_h_in: float = 0.0,
    T_h_out: float = 0.0,
    T_c_in: float = 0.0,
    T_c_out: float = 0.0,
) -> float:
    """
    Incremental cost of ONE action added to the existing g(n).

    action_type: "match" | "heater" | "cooler"
    """
    if action_type == "match":
        area = exchanger_area(duty, T_h_in, T_h_out, T_c_in, T_c_out)
        return prev_g + annualised_exchanger_cost(area) + UNIT_PENALTY
    elif action_type == "heater":
        return prev_g + utility_heater_cost(duty)
    elif action_type == "cooler":
        return prev_g + utility_cooler_cost(duty)
    return prev_g
