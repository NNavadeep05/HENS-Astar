"""
main.py  (v2 — Decision-Tree A* for HENS)
==========================================
Entry point for the Classical AI HENS project.

Frames the problem explicitly as a DECISION TREE SEARCH:
  Root  : empty network matrix (no matches)
  Levels: each level = one process HX placed
  Goal  : all streams reach target temperature

Run:
    python main.py

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI — Heat Exchanger Network Synthesis using A* Search
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


# ===========================================================================
# PROBLEM DATA  —  Classic HENS benchmark (4H / 4C streams)
# Linnhoff & Hindmarsh (1983) variant
# ===========================================================================

HOT_STREAMS = [
    HotStream("H1", T_in=200, T_out= 80, FCp=2.0),   # 240 kW
    HotStream("H2", T_in=150, T_out= 50, FCp=4.0),   # 400 kW
    HotStream("H3", T_in=180, T_out= 60, FCp=3.0),   # 360 kW
    HotStream("H4", T_in=130, T_out= 40, FCp=2.5),   # 225 kW
]

COLD_STREAMS = [
    ColdStream("C1", T_in= 30, T_out=120, FCp=3.0),  # 270 kW
    ColdStream("C2", T_in= 40, T_out=130, FCp=2.5),  # 225 kW
    ColdStream("C3", T_in= 50, T_out=160, FCp=2.0),  # 220 kW
    ColdStream("C4", T_in= 20, T_out=100, FCp=4.0),  # 320 kW
]

DELTA_T_MIN = 10.0   # °C minimum temperature approach


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("\n" + "=" * 70)
    print("  AI-BASED HEAT EXCHANGER NETWORK SYNTHESIS — DECISION TREE A*")
    print("  Algorithm : A* Search on Decision Tree")
    print("  Team      : Navadeep | Raghu | Vivekadithya | Daivamsh")
    print("  Course    : Classical AI")
    print("=" * 70)

    # --- Problem summary ----------------------------------------------------
    print("\n  DECISION TREE DEFINITION")
    print("  " + "-" * 60)
    print(f"  Root node   : empty matrix — all {len(HOT_STREAMS)} hot × "
          f"{len(COLD_STREAMS)} cold streams unsatisfied")
    print(f"  Branching   : feasible (Hi, Cj) pairs per level (pruned by ΔTmin + matrix)")
    print(f"  Goal depth  : variable — when all stream duties satisfied")
    print(f"  Max pairs   : {len(HOT_STREAMS) * len(COLD_STREAMS)} "
          f"(= {len(HOT_STREAMS)}H × {len(COLD_STREAMS)}C)")

    print(f"\n  STREAM DATA")
    print("  " + "-" * 62)
    print(f"  {'ID':<5} {'Type':<6} {'T_in':>6} {'T_out':>6} {'FCp':>7} {'Duty':>10}")
    print("  " + "-" * 62)
    for h in HOT_STREAMS:
        print(f"  {h.sid:<5} {'Hot':<6} {h.T_in:>6.1f} {h.T_out:>6.1f} "
              f"{h.FCp:>7.1f} {h.Q_total:>10.1f} kW")
    for c in COLD_STREAMS:
        print(f"  {c.sid:<5} {'Cold':<6} {c.T_in:>6.1f} {c.T_out:>6.1f} "
              f"{c.FCp:>7.1f} {c.Q_total:>10.1f} kW")

    total_hot  = sum(h.Q_total for h in HOT_STREAMS)
    total_cold = sum(c.Q_total for c in COLD_STREAMS)
    print("  " + "-" * 62)
    print(f"  Total hot   : {total_hot:.1f} kW")
    print(f"  Total cold  : {total_cold:.1f} kW")
    print(f"  ΔT_min      : {DELTA_T_MIN} °C")

    print(f"\n  HEURISTIC : {heuristic_is_admissible()}")

    print(f"\n  COST PARAMETERS")
    print(f"  Steam   : ${STEAM_COST_PER_KW_YEAR:,.0f} / kW·yr  |  "
          f"CW : ${COOLING_COST_PER_KW_YEAR:,.0f} / kW·yr")
    print(f"  Capital : $({COST_A:.0f} + {COST_B:.0f}×A^{COST_C}) annualised at "
          f"{ANNUALISATION_FACTOR*100:.0f}%/yr  |  Unit penalty: ${UNIT_PENALTY:,.0f}")

    # --- Build stream dicts ------------------------------------------------
    hot_dict  = {h.sid: h for h in HOT_STREAMS}
    cold_dict = {c.sid: c for c in COLD_STREAMS}

    # --- Run A* on the decision tree ----------------------------------------
    print("\n  RUNNING A* DECISION-TREE SEARCH …")
    result = astar_search(
        hot_streams  = hot_dict,
        cold_streams = cold_dict,
        delta_T_min  = DELTA_T_MIN,
        max_nodes    = 100_000,
        verbose      = True,
    )

    # --- Results ------------------------------------------------------------
    if not result.success:
        print("\n  ✗ No feasible network found. Check stream data / ΔTmin.")
        return

    goal = result.goal_state

    print("\n" + "=" * 70)
    print("  OPTIMAL NETWORK — RESULTS")
    print("=" * 70)

    # Match matrix
    print(f"\n  NETWORK MATCH MATRIX (rows=Cold, cols=Hot)")
    print("  " + "-" * 50)
    print(goal.matrix)

    # Exchanger table
    print(f"\n  PROCESS HEAT EXCHANGERS ({goal.num_exchangers()} units)")
    print("  " + "-" * 55)
    print(f"  {'HX':<5} {'Hot':<5} {'Cold':<5} {'Duty (kW)':>12} {'Cost ($/yr)':>14}")
    print("  " + "-" * 55)

    from cost import exchanger_area, annualised_exchanger_cost
    total_hx_cost = 0.0
    for m in goal.matches:
        h = hot_dict[m.hot_id]
        c = cold_dict[m.cold_id]
        area = exchanger_area(m.duty, h.T_in, h.T_out, c.T_in, c.T_out)
        cost = annualised_exchanger_cost(area) + UNIT_PENALTY
        total_hx_cost += cost
        print(f"  {f'HX{m.order}':<5} {m.hot_id:<5} {m.cold_id:<5} "
              f"{m.duty:>12.1f} {cost:>14,.0f}")

    # Utility table
    from cost import utility_heater_cost, utility_cooler_cost
    total_util_cost = 0.0
    if goal.heaters or goal.coolers:
        print(f"\n  UTILITY UNITS ({goal.num_utilities()})")
        print("  " + "-" * 55)
        for h in goal.heaters:
            c = utility_heater_cost(h.duty)
            total_util_cost += c
            print(f"  Steam → {h.cold_id:<5}   {h.duty:>12.1f} kW  {c:>14,.0f}")
        for c in goal.coolers:
            cost = utility_cooler_cost(c.duty)
            total_util_cost += cost
            print(f"  CW   → {c.hot_id:<5}    {c.duty:>12.1f} kW  {cost:>14,.0f}")

    print("\n  " + "=" * 55)
    print(f"  {'Exchanger Capital (ann.)':35} ${total_hx_cost:>14,.0f} /yr")
    print(f"  {'Utility Operating':35} ${total_util_cost:>14,.0f} /yr")
    print(f"  {'TOTAL ANNUALIZED COST (TAC)':35} ${goal.g_cost:>14,.0f} /yr")

    print(f"\n  SEARCH PERFORMANCE")
    print("  " + "-" * 42)
    print(f"  Nodes expanded   : {result.nodes_expanded:,}")
    print(f"  Nodes generated  : {result.nodes_generated:,}")
    print(f"  Max tree depth   : {result.max_tree_depth}")
    print(f"  Solution depth   : {goal.tree_level}")
    print(f"  Time elapsed     : {result.time_seconds:.4f} s")

    print(f"\n  TREE LEVEL BREAKDOWN  (nodes expanded per level)")
    print("  " + "-" * 35)
    for lv in sorted(result.tree_level_stats):
        bar = "█" * min(result.tree_level_stats[lv], 40)
        print(f"  Level {lv:2d}: {result.tree_level_stats[lv]:5,}  {bar}")

    print(f"\n  ENERGY BALANCE VERIFICATION")
    print("  " + "-" * 40)
    for h_id, rem in goal.hot_remaining.items():
        status = "✓ OK" if rem <= 0.5 else f"⚠ {rem:.1f} kW remaining"
        print(f"  {h_id}: {status}")
    for c_id, rem in goal.cold_remaining.items():
        status = "✓ OK" if rem <= 0.5 else f"⚠ {rem:.1f} kW remaining"
        print(f"  {c_id}: {status}")

    # --- Visualization -------------------------------------------------------
    visualize_all(result, hot_dict, cold_dict, DELTA_T_MIN)


if __name__ == "__main__":
    main()
