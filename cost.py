"""
cost.py
=======
Cost model for HENS. Computes exchanger capital cost (annualized, area-based),
utility operating costs, and Total Annualized Cost (TAC).

Area-cost law:  A = Q / (U x dT_lm),  Cost = COST_A + COST_B x A^COST_C
Reference: Chen (1987) LMTD approximation.

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from state import HENSState, HotStream, ColdStream, ExchangerMatch


# Cost parameters — adjust here if needed
U_DEFAULT            = 0.5       # overall heat transfer coefficient (kW / m2 C)
COST_A               = 8_000.0   # fixed cost per exchanger ($)
COST_B               = 1_200.0   # area cost coefficient ($/m^COST_C)
COST_C               = 0.6       # area cost exponent
ANNUALISATION_FACTOR = 0.25      # capital spread over 4-year payback
STEAM_COST_PER_KW_YEAR   = 160.0  # $/kW.yr
COOLING_COST_PER_KW_YEAR =  60.0  # $/kW.yr
UNIT_PENALTY         = 5_000.0   # $ per exchanger unit (discourages excess units)


def delta_T_lm(T_h_in: float, T_h_out: float, T_c_in: float, T_c_out: float) -> float:
    """Chen (1987) approximation: dT_lm = (dT1 x dT2 x (dT1+dT2)/2)^(1/3)."""
    dT1 = max(T_h_in  - T_c_out, 0.1)
    dT2 = max(T_h_out - T_c_in,  0.1)
    if abs(dT1 - dT2) < 1e-6:
        return dT1
    return (dT1 * dT2 * (dT1 + dT2) / 2.0) ** (1.0 / 3.0)


def exchanger_area(duty: float, T_h_in: float, T_h_out: float,
                   T_c_in: float, T_c_out: float,
                   U: float = U_DEFAULT) -> float:
    """Required area in m2: A = Q / (U x dT_lm)."""
    dtlm = delta_T_lm(T_h_in, T_h_out, T_c_in, T_c_out)
    if dtlm < 1e-6:
        return float("inf")
    return duty / (U * dtlm)


def exchanger_capital_cost(area: float) -> float:
    """Purchased and installed cost ($): COST_A + COST_B x Area^COST_C."""
    return COST_A + COST_B * (area ** COST_C)


def annualised_exchanger_cost(area: float) -> float:
    """Annual capital charge ($/yr)."""
    return exchanger_capital_cost(area) * ANNUALISATION_FACTOR


def match_cost(
    match:                 "ExchangerMatch",
    hot_streams:           Dict[str, "HotStream"],
    cold_streams:          Dict[str, "ColdStream"],
    hot_remaining_before:  float,
    cold_remaining_before: float,
) -> float:
    """Annualised capital cost for one process heat exchanger."""
    from constraints import current_hot_temp, current_cold_temp
    hot  = hot_streams[match.hot_id]
    cold = cold_streams[match.cold_id]
    T_h_in  = current_hot_temp(hot,  hot_remaining_before)
    T_h_out = T_h_in - match.duty / hot.FCp
    T_c_in  = current_cold_temp(cold, cold_remaining_before)
    T_c_out = T_c_in + match.duty / cold.FCp
    area = exchanger_area(match.duty, T_h_in, T_h_out, T_c_in, T_c_out)
    return annualised_exchanger_cost(area) + UNIT_PENALTY


def utility_heater_cost(duty: float) -> float:
    """Annual steam cost for supplying `duty` kW."""
    return duty * STEAM_COST_PER_KW_YEAR


def utility_cooler_cost(duty: float) -> float:
    """Annual cooling water cost for removing `duty` kW."""
    return duty * COOLING_COST_PER_KW_YEAR


def compute_tac(
    state:        "HENSState",
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
) -> float:
    """
    TAC of the network in `state`.
    Exchanger temperatures are approximated from full stream endpoints
    since intermediate history is not stored.
    """
    tac = 0.0
    for match in state.matches:
        hot  = hot_streams[match.hot_id]
        cold = cold_streams[match.cold_id]
        area = exchanger_area(match.duty, hot.T_in, hot.T_out, cold.T_in, cold.T_out)
        tac += annualised_exchanger_cost(area) + UNIT_PENALTY
    for heater in state.heaters:
        tac += utility_heater_cost(heater.duty)
    for cooler in state.coolers:
        tac += utility_cooler_cost(cooler.duty)
    return tac


def compute_g_cost(
    prev_g:      float,
    action_type: str,
    duty:        float,
    T_h_in:      float = 0.0,
    T_h_out:     float = 0.0,
    T_c_in:      float = 0.0,
    T_c_out:     float = 0.0,
    **kwargs,
) -> float:
    """Incremental g(n) cost for one action. action_type: match | heater | cooler."""
    if action_type == "match":
        area = exchanger_area(duty, T_h_in, T_h_out, T_c_in, T_c_out)
        return prev_g + annualised_exchanger_cost(area) + UNIT_PENALTY
    if action_type == "heater":
        return prev_g + utility_heater_cost(duty)
    if action_type == "cooler":
        return prev_g + utility_cooler_cost(duty)
    return prev_g
