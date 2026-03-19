# HENS-Astar

**Heat Exchanger Network Synthesis via A\* Decision-Tree Search**

---

## Overview

HENS-Astar solves the Heat Exchanger Network Synthesis (HENS) problem — a core challenge in chemical process engineering — by framing it as a decision-tree search and solving it with the A\* algorithm.

Given a set of hot and cold process streams, the goal is to design a network of heat exchangers that transfers heat between streams as efficiently as possible, minimizing the Total Annualized Cost (TAC) of the network. This includes annualized capital costs for exchanger units and operating costs for external utilities (steam and cooling water).

---

## Problem Formulation

| Element | Description |
|---|---|
| Root node | Empty network — no matches placed |
| Tree level k | k process heat exchangers have been placed |
| Branch action | Place one feasible (Hi, Cj) match |
| Goal | All stream duties satisfied within tolerance |
| Objective | Minimize Total Annualized Cost (TAC) |

The search space is pruned using thermodynamic feasibility (Delta T min constraint) and a canonical ordering rule that collapses commutative-equivalent paths into a single branch.

---

## Algorithm

**Search:** A\* on a decision tree with a min-heap priority queue ordered by f(n) = g(n) + h(n).

**Cost function g(n):** Accumulated TAC — annualized exchanger capital (area-based, Chen 1987 LMTD approximation) plus utility operating costs.

**Heuristic h(n):** Admissible two-component lower bound:
- Energy-balance bound — aggregate hot/cold surplus deficit
- Temperature-feasibility bound — portions of streams that thermodynamically must use utilities regardless of process matches

Taking the maximum of both components gives a tighter bound while preserving admissibility. A\* is therefore guaranteed to return the optimal network.

---

## Pruning Rules

| Rule | Description |
|---|---|
| P1 | Skip (Hi, Cj) already present in the match matrix |
| P2 | Skip matches violating the Delta T min constraint at either exchanger end |
| P3 | Offer utilities only when a stream has no feasible process partner |
| P4 | Anchor-hot ordering — fix the lowest-indexed unmatched hot stream per level to eliminate commutative duplicates |

---

## Cost Model

```
Capital cost  =  (8000 + 1200 * Area^0.6)  x  annualisation factor (25%)
Area          =  Q / (U x dT_lm)           [Chen 1987 approximation]
Steam cost    =  160  $/kW.yr
Cooling water =   60  $/kW.yr
Unit penalty  =  5000  $ per exchanger
```

---

## Benchmark Problem

Classic 4H / 4C stream problem (Linnhoff and Hindmarsh, 1983).

| Stream | Type | T_in (C) | T_out (C) | FCp (kW/C) | Duty (kW) |
|---|---|---|---|---|---|
| H1 | Hot | 200 | 80 | 2.0 | 240 |
| H2 | Hot | 150 | 50 | 4.0 | 400 |
| H3 | Hot | 180 | 60 | 3.0 | 360 |
| H4 | Hot | 130 | 40 | 2.5 | 225 |
| C1 | Cold | 30 | 120 | 3.0 | 270 |
| C2 | Cold | 40 | 130 | 2.5 | 225 |
| C3 | Cold | 50 | 160 | 2.0 | 220 |
| C4 | Cold | 20 | 100 | 4.0 | 320 |

Delta T min: 10 C

---

## Project Structure

```
.
├── main.py            Entry point — problem data, A* call, results output
├── state.py           HENSState and NetworkMatrix — search node representation
├── astar.py           A* engine — priority queue, visited set, goal test
├── actions.py         Successor generator — MATCH, ADD_HEATER, ADD_COOLER
├── constraints.py     Thermodynamic feasibility — Delta T min checks
├── heuristic.py       Admissible two-component heuristic
├── cost.py            TAC model — area, LMTD, capital, utility costs
├── visualization.py   Three matplotlib figures — matrix grid, search path, energy balance
└── requirements.txt   Dependencies
```

---

## Installation and Usage

**Requirements:** Python 3.9+

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

On Windows, double-click `run.bat` for a one-click install and run.

---

## Output

The solver prints:

- Full stream data and cost parameters
- A\* progress log (nodes expanded, f/g values, remaining duties)
- Optimal network match matrix
- Per-exchanger duty and annualized cost breakdown
- Utility units and operating costs
- Total Annualized Cost (TAC)
- Search statistics — nodes expanded, tree depth, time elapsed
- Tree level breakdown histogram

Three plots are generated:

1. **Matrix Grid Diagram** — 2D match matrix with exchanger duties and utility nodes
2. **A\* Decision Tree Path** — f(n), g(n), h(n) per tree level alongside energy draw-down
3. **Energy Balance** — stream duty coverage by process HX vs utility

---

## Authors

Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori

Course: Classical AI

---

## References

- Linnhoff, B. and Hindmarsh, E. (1983). The pinch design method for heat exchanger networks. *Chemical Engineering Science*, 38(5), 745-763.
- Chen, J.J.J. (1987). Comments on improvements on a replacement for the logarithmic mean. *Chemical Engineering Science*, 42(10), 2488-2489.
