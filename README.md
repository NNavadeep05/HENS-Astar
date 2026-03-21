# HENS-Astar

**Heat Exchanger Network Synthesis via A\* Decision-Tree Search**

___

## Description

HENS is a classic process engineering problem: given a set of hot and cold streams, find the cheapest network of heat exchangers that brings each stream to its target temperature. The hard part is that the number of possible networks grows fast, and most formulations end up either brute-forcing it or relying on heuristics that do not guarantee optimality.

This project uses A\* search on a decision tree, where each node represents a partial network and each branch adds one exchanger. Because the heuristic is admissible, the first complete solution A\* finds is guaranteed to be optimal.

___

## Problem Formulation

| Element | Description |
|---|---|
| Root node | Empty network, no matches placed |
| Tree level k | k process heat exchangers placed so far |
| Branch action | Place one feasible (Hi, Cj) match |
| Goal | All stream duties satisfied within tolerance |
| Objective | Minimize Total Annualized Cost (TAC) |

At each level, the branching is constrained by the Delta T min condition and a canonical ordering rule that prevents the same network from being explored twice under different placement sequences.

___

## Algorithm

The search runs standard A\* with a min-heap on f(n) = g(n) + h(n).

**g(n)** is the accumulated TAC so far: annualized exchanger capital computed from area using the Chen (1987) LMTD approximation, plus utility operating costs added as each unit is placed.

**h(n)** is a three-component lower bound (v3 Heuristic). 
1. **Component A:** An energy-balance bound on the aggregate hot and cold surplus across remaining streams. 
2. **Component B:** A temperature-feasibility bound tracking portions of streams that thermodynamically cannot be served by process exchange and must use utilities regardless of what matches remain. 
3. **Component C:** A pinch point composite curve analysis that calculates the strict minimum heating (QHmin) and cooling (QCmin) duties from the remaining stream segments.
The heuristic takes the maximum of all three components, keeping it tight without ever overestimating.

___

## Pruning Rules

Four pruning rules keep the tree manageable:

| Rule | Description |
|---|---|
| P1 | Skip any (Hi, Cj) pair already in the match matrix |
| P2 | Skip matches that violate Delta T min at either exchanger end |
| P3 | Only offer utility actions when a stream has no feasible process partner |
| P4 | Fix the lowest-indexed unmatched hot stream as the branching anchor per level, collapsing commutative orderings into one path |

P4 in particular cuts the search space substantially. Without it, placing H1-C1 then H2-C2 and placing H2-C2 then H1-C1 would both be explored separately.

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

## Benchmark Problems

The project evaluates two test cases sequentially:

1. **4H/4C Linnhoff Benchmark**: The classic problem from Linnhoff and Hindmarsh (1983), a standard reference in heat integration literature.
2. **8H/8C Synthetic Benchmark**: A larger, 16-stream scalable problem to dynamically test the A* decision-tree's efficiency on broader matrices.

Delta T min: 10 °C

___

## Project Structure

```
.
├── main.py            Entry point — runs the dual-benchmarks, problem data, outputs scalability table
├── state.py           HENSState and NetworkMatrix — search node representation
├── astar.py           A* engine — priority queue, visited set, goal test
├── actions.py         Successor generator — MATCH, ADD_HEATER, ADD_COOLER
├── constraints.py     Thermodynamic feasibility — Delta T min checks
├── heuristic.py       Admissible v3 heuristic with pinch point composite curve analysis
├── cost.py            TAC model — area, LMTD, capital, utility costs
├── visualization.py   Four matplotlib figures — matrix grid, search path, energy balance, composite plot
├── CONCEPTS.md        Detailed glossary of all 26 thermodynamic and AI concepts
└── requirements.txt   Dependencies
```

___

## Installation and Usage

Requires Python 3.9 or above.

```bash
pip install -r requirements.txt
python main.py
```

On Windows, double-clicking `run.bat` handles both steps.

___

## Output

Running `main.py` solves both problems sequentially. It prints the stream table, A\* progress (nodes expanded, f and g values, remaining duties), the final match matrix, per-exchanger costs, utility costs, search statistics, and a scalability comparison table. 

It then opens four matplotlib figures:
1. A matrix grid showing which streams are matched and at what duty.
2. A plot of f(n), g(n), and h(n) along the solution path.
3. An energy balance chart comparing process recovery against utility use per stream.
4. T-H composite curves showing the shaded pinch point, hot and cold composite curves, and bounded QHmin and QCmin utility targets.

___

## Authors

Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori

Course: Classical AI

___

## References

Linnhoff, B. and Hindmarsh, E. (1983). The pinch design method for heat exchanger networks. *Chemical Engineering Science*, 38(5), 745-763.

Chen, J.J.J. (1987). Comments on improvements on a replacement for the logarithmic mean. *Chemical Engineering Science*, 42(10), 2488-2489.
