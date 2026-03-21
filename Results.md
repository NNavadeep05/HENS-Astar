# Results — HENS-Astar

**Algorithm:** A* Decision-Tree Search  
**Delta T min:** 10 °C

The script now runs two sequential problems to demonstrate the algorithm's optimality and scalability: the classic **4H/4C Linnhoff Benchmark** and an **8H/8C Synthetic Benchmark**.

___

## 4H/4C Linnhoff Benchmark

### Stream Data

| Stream | Type | T_in (°C) | T_out (°C) | FCp (kW/°C) | Duty (kW) |
|---|---|---|---|---|---|
| H1 | Hot | 200 | 80 | 2.0 | 240 |
| H2 | Hot | 150 | 50 | 4.0 | 400 |
| H3 | Hot | 180 | 60 | 3.0 | 360 |
| H4 | Hot | 130 | 40 | 2.5 | 225 |
| C1 | Cold | 30 | 120 | 3.0 | 270 |
| C2 | Cold | 40 | 130 | 2.5 | 225 |
| C3 | Cold | 50 | 160 | 2.0 | 220 |
| C4 | Cold | 20 | 100 | 4.0 | 320 |

Total hot duty: 1225.0 kW  
Total cold duty: 1035.0 kW  
Surplus hot duty (must be rejected via cooling water): 190.0 kW

___

### Optimal Network

#### Match Matrix

Rows are cold streams, columns are hot streams. Numbers show the order in which exchangers were placed.

```
            H1      H2      H3      H4
  C1         .       .     [5]       .
  C2        [2]     [3]      .       .
  C3        [1]      .       .       .
  C4         .      [4]      .      [6]
```

#### Process Heat Exchangers

| Unit | Hot | Cold | Duty (kW) | Annualized Cost ($/yr) |
|---|---|---|---|---|
| HX1 | H1 | C3 | 220.0 | 8,376 |
| HX2 | H1 | C2 | 20.0 | 7,252 |
| HX3 | H2 | C2 | 205.0 | 9,235 |
| HX4 | H2 | C4 | 195.0 | 8,192 |
| HX5 | H3 | C1 | 270.0 | 8,364 |
| HX6 | H4 | C4 | 125.0 | 8,204 |

#### Utility Units

No steam heating was required. H3 and H4 both have target temperatures low enough that cooling water handles the remainder after process exchange.

| Type | Stream | Duty (kW) | Annual Cost ($/yr) |
|---|---|---|---|
| Cooling Water | H3 | 90.0 | 5,400 |
| Cooling Water | H4 | 100.0 | 6,000 |

___

### Cost Summary

| Component | Cost ($/yr) |
|---|---|
| Exchanger Capital (annualized at 25%/yr) | 49,623 |
| Utility Operating Cost | 11,400 |
| **Total Annualized Cost (TAC)** | **60,244** |

___

### Search Performance

| Metric | Value |
|---|---|
| Nodes expanded | 235 |
| Nodes generated | 599 |
| Maximum tree depth reached | 6 |
| Solution depth | 6 |
| Time elapsed | ~0.02 seconds |

#### Tree Level Breakdown

| Level | Nodes Expanded |
|---|---|
| 0 | 1 |
| 1 | 4 |
| 2 | 17 |
| 3 | 64 |
| 4 | 84 |
| 5 | 61 |
| 6 | 4 |

Branching peaks at levels 3 and 4 where stream loads are partially satisfied and the most feasible pair combinations exist. By level 6, most streams are near their targets and the branching collapses.

___

### Energy Balance

All streams reached their target temperatures within the 0.5 kW tolerance.

| Stream | Status |
|---|---|
| H1 | Satisfied |
| H2 | Satisfied |
| H3 | Satisfied |
| H4 | Satisfied |
| C1 | Satisfied |
| C2 | Satisfied |
| C3 | Satisfied |
| C4 | Satisfied |

___

## 8H/8C Synthetic Benchmark & Scalability

The project now dynamically runs a double-sized variant directly after the 4H/4C problem. The **8H/8C Synthetic Benchmark** contains 16 streams and 64 total pairs, pushing the combinatorial branching factor significantly higher. 

To offset the exponentially expanded search matrix, the solver relies on the combined strength of the **P4 Anchor-Hot pruning** rule and the newly added **v3 primary admissible heuristic**—which integrates pinch-point composite curve limits (QHmin and QCmin) to prune suboptimal paths early. 

The console execution concludes with a **Scalability Comparison** table, summarizing and comparing both dimensions directly, highlighting metrics such as the node expansion growth vs the network complexity, runtime (seconds), and final TAC.

___

## Notes

The network recovers heat between H1 and C3/C2, H2 and C2/C4, H3 and C1, and H4 and C4. No cold stream required steam because the total hot duty exceeds total cold duty by 190 kW, leaving enough process heat available for all cold targets.

The search found the optimal solution for 4H/4C in 235 node expansions and milliseconds of computation. For context, a naive search without the anchor-hot pruning rule (P4) or the v3 pinch heuristic would explore the same network under exponentially more placement orderings and sub-optimal partial states.
