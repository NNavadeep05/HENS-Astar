# HENS-Astar

**Heat Exchanger Network Synthesis via A\* Decision-Tree Search**

___

## What This Is

A process plant has streams that need heating and streams that need cooling. The naive approach runs everything through steam and cooling water. The smarter approach transfers heat directly between process streams through heat exchangers, using external utilities only for what process exchange cannot cover. Deciding which streams to pair, in what order, and at what duties to minimize total annual cost is the HENS problem. The number of possible networks grows combinatorially, so you need a search algorithm.

This project solves HENS using **A\* search on a decision tree**. Each node is a partial network. Each branch places one heat exchanger. The heuristic is admissible, so the first complete solution A\* returns is the **guaranteed optimal network**.

The benchmark is the **Pho and Lapidus (1973) 10SP1 problem** — 5 hot and 5 cold streams — which they could not solve optimally by direct enumeration in 1973. This implementation finds the guaranteed optimal in **745 node expansions and under 0.15 seconds**.

___

## Problem Formulation

| Element | Description |
|---|---|
| Root node | Empty network, no matches placed |
| Tree level k | k process heat exchangers placed |
| Branch action | Place one feasible (Hi, Cj) match |
| Goal | All stream duties satisfied within tolerance |
| Objective | Minimize **Total Annualized Cost (TAC)** |

___

## Algorithm

**f(n) = g(n) + h(n)**

**g(n)** is the exact TAC accumulated so far: annualized exchanger capital using the Chen (1987) LMTD approximation, plus utility costs added as each unit is placed.

**h(n)** is the v3 admissible heuristic with three components, each a lower bound on remaining cost:

- **Component A** — aggregate energy balance between remaining hot and cold duties
- **Component B** — per-stream temperature obligations forced by the Delta T min constraint
- **Component C** — pinch composite curve analysis computing **QHmin** and **QCmin** from remaining stream segments

The heuristic takes the maximum of all three. It never overestimates, so A\* optimality is guaranteed.

___

## Pruning Rules

| Rule | Description |
|---|---|
| **P1** | Skip any (Hi, Cj) pair already in the match matrix |
| **P2** | Skip matches that violate Delta T min at either exchanger end |
| **P3** | Offer utility actions only when a stream has no feasible process partner |
| **P4** | **Anchor-hot rule** — fix the lowest-indexed unmatched hot stream as the branching point per level, collapsing all commutative orderings into one path |

P4 is the most impactful. Without it, placing H1-C1 then H2-C2 and placing H2-C2 then H1-C1 would both be explored as separate branches despite producing the same network.

___

## Cost Model

```
Capital cost  =  (8000 + 1200 x Area^0.6)  x  annualisation factor (25%)
Area          =  Q / (U x dT_lm)            [Chen 1987 approximation]
Steam         =  160  $/kW.yr
Cooling water =   60  $/kW.yr
Unit penalty  =  5000  $ per exchanger
```

___

## Project Structure

```
.
├── main.py            Entry point. Defines the 5H/5C stream data,
│                      runs the solver, and prints full results.
│
├── state.py           HENSState and NetworkMatrix. The search node
│                      stores the match matrix, remaining duties,
│                      placed exchangers, tree level, and g cost.
│
├── astar.py           A* engine. Min-heap priority queue on f(n),
│                      visited set for duplicate detection, verbose
│                      progress logging, and path reconstruction.
│
├── actions.py         Successor generator. Three action types:
│                      MATCH, ADD_HEATER, ADD_COOLER. Enforces
│                      pruning rules P1 through P4.
│
├── constraints.py     Thermodynamic feasibility. Checks Delta T min
│                      at both exchanger ends and tracks current
│                      stream temperatures from remaining loads.
│
├── heuristic.py       Admissible v3 heuristic. Components A, B, and C
│                      as described above. Also builds composite curves
│                      shared with the visualization module.
│
├── cost.py            TAC model. Chen LMTD, area calculation, power-law
│                      capital cost, utility rates, and incremental
│                      g cost computation per action.
│
├── visualization.py   Four matplotlib figures on a dark precision theme:
│                      network matrix grid, A* search path, stream energy
│                      balance, and T-H composite curves with pinch annotation.
│
├── CONCEPTS.md        Plain-language explanations of all 26 concepts used,
│                      covering both heat transfer and AI/search theory.
│
├── Results.md         Full numerical results with plots embedded.
│
├── requirements.txt   Dependencies (matplotlib only).
├── run.bat            One-click launcher for Windows.
└── run.sh             One-click launcher for Mac and Linux.
```

___

## Installation and Usage

Requires **Python 3.9** or above.

```bash
pip install -r requirements.txt
python main.py
```

On **Windows**, double-click `run.bat`.  
On **Mac or Linux**, run `bash run.sh`.

___

## Output

The solver prints the stream table, A\* search progress, the optimal match matrix, per-exchanger costs, utility costs, and search statistics.

Four figures are generated:

1. **Matrix Grid** — 2D network topology with exchanger duties and utility annotations
2. **A\* Search Path** — f(n), g(n), and h(n) per tree level alongside duty draw-down
3. **Energy Balance** — process HX coverage vs utility use per stream
4. **T-H Composite Curves** — pinch point, QHmin and QCmin shading, hot and cold composites

___

## Authors

Navadeep Nandedapu (23ME10054)  
Raghu Perala (23ME10064)  
Yayavaram Vivekadithya (23ME3EP10)  
Atoori Daivamsh (23CH30008)

**Indian Institute of Technology Kharagpur**  
Course: Artificial Intelligence Foundations and Applications

___

## References

Pho, T.K. and Lapidus, L. (1973). Topics in computer-aided design: Part II. Synthesis of optimal heat exchanger networks by tree searching algorithms. *AIChE Journal*, 19(6), 1182-1189.

Linnhoff, B. and Hindmarsh, E. (1983). The pinch design method for heat exchanger networks. *Chemical Engineering Science*, 38(5), 745-763.

Chen, J.J.J. (1987). Comments on improvements on a replacement for the logarithmic mean. *Chemical Engineering Science*, 42(10), 2488-2489.

Hart, P.E., Nilsson, N.J. and Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics*, 4(2), 100-107.
