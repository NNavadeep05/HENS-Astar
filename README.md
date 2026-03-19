# HENS-Astar

**Heat Exchanger Network Synthesis via A\* Decision-Tree Search**

___

## Overview

HENS-Astar solves the Heat Exchanger Network Synthesis (HENS) problem, a core challenge in chemical process engineering, by framing it as a decision-tree search and solving it with the A\* algorithm.

Given a set of hot and cold process streams, the goal is to design a network of heat exchangers that transfers heat between streams as efficiently as possible, minimizing the Total Annualized Cost (TAC) of the network. This includes annualized capital costs for exchanger units and operating costs for external utilities such as steam and cooling water.

___

## Problem Formulation

| Element | Description |
|---|---|
| Root node | Empty network with no matches placed |
| Tree level k | k process heat exchangers have been placed |
| Branch action | Place one feasible (Hi, Cj) match |
| Goal | All stream duties satisfied within tolerance |
| Objective | Minimize Total Annualized Cost (TAC) |

The search space is pruned using thermodynamic feasibility constraints (the Delta T min condition) and a canonical ordering rule that collapses commutative-equivalent paths into a single branch.

___

## Algorithm

**Search:** A\* on a decision tree with a min-heap priority queue ordered by f(n) = g(n) + h(n).

**Cost function g(n):** Accumulated TAC comprising annualized exchanger capital using an area-based power law correlation with the Chen (1987) LMTD approximation, plus utility operating costs.

**Heuristic h(n):** An admissible two-component lower bound consisting of the following:

- Energy-balance bound — aggregate hot and cold surplus or deficit across all remaining streams
- Temperature-feasibility bound — portions of streams that thermodynamically must use utilities regardless of available process matches

Taking the maximum of both components produces a tighter bound while preserving admissibility. A\* is therefore guaranteed to return the globally optimal network.

___

## Pruning Rules

| Rule | Description |
|---|---|
| P1 | Skip any (Hi, Cj) pair already present in the match matrix |
| P2 | Skip matches violating the Delta T min constraint at either end of the exchanger |
| P3 | Offer utility actions only when a stream has no feasible process partner |
| P4 | Anchor-hot ordering fixes the lowest-indexed unmatched hot stream per level, eliminating commutative duplicates |

___

## Cost Model

```
Capital cost  =  (8000 + 1200 x Area^0.6)  x  annualisation factor (25%)
Area          =  Q / (U x dT_lm)            [Chen 1987 approximation]
Steam cost    =  160  $/kW.yr
Cooling water =   60  $/kW.yr
Unit penalty  =  5000  $ per exchanger
```

___

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

___

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

___

## Installation and Usage

**Requirements:** Python 3.9 or above.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the solver
python main.py
```

On Windows, double-clicking `run.bat` will handle dependency installation and execution automatically.

___

## Output

The solver produces the following:

**Console output** includes the full stream data table, cost parameters, an A\* progress log showing nodes expanded along with f and g values and remaining duties, the optimal network match matrix, a per-exchanger breakdown of duty and annualized cost, utility unit costs, the Total Annualized Cost, search statistics covering nodes expanded and tree depth and elapsed time, and a tree level breakdown histogram.

**Graphical output** consists of three plots. The first is a Matrix Grid Diagram showing the 2D match matrix with exchanger duties and utility nodes. The second is an A\* Decision Tree Path plot showing f(n), g(n), and h(n) per tree level alongside energy draw-down. The third is an Energy Balance chart showing each stream's duty coverage split between process heat exchange and external utilities.

___

## Authors

Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori

Course: Classical AI

___

## References

Linnhoff, B. and Hindmarsh, E. (1983). The pinch design method for heat exchanger networks. *Chemical Engineering Science*, 38(5), 745-763.

Chen, J.J.J. (1987). Comments on improvements on a replacement for the logarithmic mean. *Chemical Engineering Science*, 42(10), 2488-2489.
