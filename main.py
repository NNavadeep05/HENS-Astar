"""
main.py
=======
Entry point for the HENS A* project.

Solves the Pho and Lapidus (1973) 10SP1 benchmark — 5 hot and 5 cold streams.
Pho and Lapidus could not solve this problem optimally by direct enumeration
and resorted to a look-ahead heuristic with no optimality guarantee.
This implementation finds the guaranteed optimal network using A* search.

Stream data converted from BTU/hr.F and Fahrenheit to kW/C:
  FCp: 1 BTU/hr.F = 0.000293071 kW/C
  T:   C = (F - 32) * 5/9
  delta_T_min: 20F = 11.1C

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from state       import HotStream, ColdStream
from astar       import astar_search
from heuristic   import heuristic_is_admissible
from cost        import (
    STEAM_COST_PER_KW_YEAR, COOLING_COST_PER_KW_YEAR,
    ANNUALISATION_FACTOR, COST_A, COST_B, COST_C, UNIT_PENALTY,
)
from visualization import visualize_all


def _F(f): return (f - 32) * 5 / 9
def _W(w): return w * 0.000293071


# Pho and Lapidus (1973) 10SP1 — 5H/5C
HOT_STREAMS = [
    HotStream("H1", T_in=_F(320), T_out=_F(200), FCp=_W(16670)),
    HotStream("H2", T_in=_F(480), T_out=_F(280), FCp=_W(20000)),
    HotStream("H3", T_in=_F(440), T_out=_F(150), FCp=_W(28000)),
    HotStream("H4", T_in=_F(520), T_out=_F(300), FCp=_W(23800)),
    HotStream("H5", T_in=_F(390), T_out=_F(150), FCp=_W(33600)),
]

COLD_STREAMS = [
    ColdStream("C1", T_in=_F(140), T_out=_F(320), FCp=_W(14450)),
    ColdStream("C2", T_in=_F(240), T_out=_F(431), FCp=_W(11530)),
    ColdStream("C3", T_in=_F(100), T_out=_F(430), FCp=_W(16000)),
    ColdStream("C4", T_in=_F(180), T_out=_F(350), FCp=_W(32760)),
    ColdStream("C5", T_in=_F(200), T_out=_F(400), FCp=_W(26350)),
]

DELTA_T_MIN = 11.1  # 20F converted to C


def _count_feasible_pairs(hot_list, cold_list, dT_min):
    from constraints import is_feasible_match
    count = 0
    for h in hot_list:
        for c in cold_list:
            duty = min(h.Q_total, c.Q_total)
            if is_feasible_match(h, c, h.Q_total, c.Q_total, duty, dT_min):
                count += 1
    return count


def main():
    total_hot  = sum(h.Q_total for h in HOT_STREAMS)
    total_cold = sum(c.Q_total for c in COLD_STREAMS)
    n_feasible = _count_feasible_pairs(HOT_STREAMS, COLD_STREAMS, DELTA_T_MIN)

    print("\n" + "=" * 70)
    print("  AI-BASED HEAT EXCHANGER NETWORK SYNTHESIS")
    print("  Problem   : Pho and Lapidus (1973) 10SP1 — 5H/5C")
    print("  Algorithm : A* Search on Decision Tree")
    print("  Team      : Navadeep | Raghu | Vivekadithya | Daivamsh")
    print("  Course    : Classical AI")
    print("=" * 70)

    print(f"\n  DECISION TREE")
    print("  " + "-" * 55)
    print(f"  Root      : empty matrix, 5H x 5C streams unsatisfied")
    print(f"  Max pairs : 25  |  Feasible: {n_feasible}")
    print(f"  dT_min    : {DELTA_T_MIN} C  (20 F)")

    print(f"\n  STREAM DATA (converted from BTU/Fahrenheit)")
    print("  " + "-" * 65)
    print(f"  {'ID':<5} {'Type':<6} {'T_in':>8} {'T_out':>8} {'FCp':>8} {'Duty':>10}")
    print("  " + "-" * 65)
    for h in HOT_STREAMS:
        print(f"  {h.sid:<5} {'Hot':<6} {h.T_in:>8.1f} {h.T_out:>8.1f} "
              f"{h.FCp:>8.3f} {h.Q_total:>10.1f} kW")
    for c in COLD_STREAMS:
        print(f"  {c.sid:<5} {'Cold':<6} {c.T_in:>8.1f} {c.T_out:>8.1f} "
              f"{c.FCp:>8.3f} {c.Q_total:>10.1f} kW")
    print("  " + "-" * 65)
    print(f"  Total hot : {total_hot:.1f} kW  |  Total cold : {total_cold:.1f} kW")
    print(f"  Surplus   : {max(0.0, total_hot - total_cold):.1f} kW (cooling water)")

    print(f"\n  HEURISTIC : {heuristic_is_admissible()}")
    print(f"\n  COST PARAMETERS")
    print(f"  Steam : ${STEAM_COST_PER_KW_YEAR:,.0f}/kW.yr  |  "
          f"CW : ${COOLING_COST_PER_KW_YEAR:,.0f}/kW.yr")
    print(f"  Capital : $({COST_A:.0f} + {COST_B:.0f}xA^{COST_C}) x {ANNUALISATION_FACTOR*100:.0f}%/yr  |  "
          f"Unit penalty : ${UNIT_PENALTY:,.0f}")

    hot_dict  = {h.sid: h for h in HOT_STREAMS}
    cold_dict = {c.sid: c for c in COLD_STREAMS}

    print("\n  RUNNING A* ...")
    result = astar_search(
        hot_streams  = hot_dict,
        cold_streams = cold_dict,
        delta_T_min  = DELTA_T_MIN,
        max_nodes    = 100_000,
        verbose      = True,
    )

    if not result.success:
        print("\n  No feasible network found.")
        return

    goal = result.goal_state

    print("\n" + "=" * 70)
    print("  OPTIMAL NETWORK")
    print("=" * 70)

    print(f"\n  NETWORK MATCH MATRIX")
    print("  " + "-" * 50)
    print(goal.matrix)

    from cost import exchanger_area, annualised_exchanger_cost, utility_heater_cost, utility_cooler_cost

    print(f"\n  PROCESS HEAT EXCHANGERS ({goal.num_exchangers()} units)")
    print("  " + "-" * 55)
    print(f"  {'HX':<5} {'Hot':<5} {'Cold':<5} {'Duty (kW)':>12} {'Cost ($/yr)':>14}")
    print("  " + "-" * 55)
    total_hx_cost = 0.0
    for m in goal.matches:
        h    = hot_dict[m.hot_id]
        c    = cold_dict[m.cold_id]
        area = exchanger_area(m.duty, h.T_in, h.T_out, c.T_in, c.T_out)
        cost = annualised_exchanger_cost(area) + UNIT_PENALTY
        total_hx_cost += cost
        print(f"  {f'HX{m.order}':<5} {m.hot_id:<5} {m.cold_id:<5} "
              f"{m.duty:>12.1f} {cost:>14,.0f}")

    total_util_cost = 0.0
    if goal.heaters or goal.coolers:
        print(f"\n  UTILITY UNITS ({goal.num_utilities()})")
        print("  " + "-" * 55)
        for h in goal.heaters:
            c = utility_heater_cost(h.duty)
            total_util_cost += c
            print(f"  Steam -> {h.cold_id:<5}   {h.duty:>12.1f} kW  {c:>14,.0f}")
        for c in goal.coolers:
            cost = utility_cooler_cost(c.duty)
            total_util_cost += cost
            print(f"  CW    -> {c.hot_id:<5}   {c.duty:>12.1f} kW  {cost:>14,.0f}")

    print("\n  " + "=" * 55)
    print(f"  {'Exchanger Capital (ann.)':<35} ${total_hx_cost:>14,.0f} /yr")
    print(f"  {'Utility Operating':<35} ${total_util_cost:>14,.0f} /yr")
    print(f"  {'TOTAL ANNUALIZED COST (TAC)':<35} ${goal.g_cost:>14,.0f} /yr")

    print(f"\n  SEARCH PERFORMANCE")
    print("  " + "-" * 42)
    print(f"  Nodes expanded  : {result.nodes_expanded:,}")
    print(f"  Nodes generated : {result.nodes_generated:,}")
    print(f"  Max tree depth  : {result.max_tree_depth}")
    print(f"  Solution depth  : {goal.tree_level}")
    print(f"  Time elapsed    : {result.time_seconds:.4f} s")

    print(f"\n  TREE LEVEL BREAKDOWN")
    print("  " + "-" * 35)
    for lv in sorted(result.tree_level_stats):
        bar = "█" * min(result.tree_level_stats[lv], 40)
        print(f"  Level {lv:2d}: {result.tree_level_stats[lv]:5,}  {bar}")

    print(f"\n  ENERGY BALANCE")
    print("  " + "-" * 40)
    for h_id, rem in goal.hot_remaining.items():
        status = "OK" if rem <= 0.5 else f"REMAINING {rem:.1f} kW"
        print(f"  {h_id}: {status}")
    for c_id, rem in goal.cold_remaining.items():
        status = "OK" if rem <= 0.5 else f"REMAINING {rem:.1f} kW"
        print(f"  {c_id}: {status}")

    print(f"\n  NOTE: Pho and Lapidus (1973) could not solve this problem optimally")
    print(f"  by direct enumeration. They used a 5-step look-ahead heuristic")
    print(f"  with no optimality guarantee. This A* search finds the guaranteed")
    print(f"  optimal network in {result.time_seconds:.3f} seconds.")

    visualize_all(result, hot_dict, cold_dict, DELTA_T_MIN)


if __name__ == "__main__":
    main()
