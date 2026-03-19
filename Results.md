# Results — HENS-Astar

**Problem:** Linnhoff and Hindmarsh (1983) classic benchmark, 4 hot streams and 4 cold streams  
**Algorithm:** A* Decision-Tree Search  
**Delta T min:** 10 °C

___

## Stream Data

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

___

## Optimal Network

### Match Matrix

Rows represent cold streams and columns represent hot streams. Each cell shows the sequence in which exchangers were placed.

```
            H1      H2      H3      H4
  C1         .       .     [5]       .
  C2        [2]     [3]      .       .
  C3        [1]      .       .       .
  C4         .      [4]      .      [6]
```

### Process Heat Exchangers

| Unit | Hot Stream | Cold Stream | Duty (kW) | Annualized Cost ($/yr) |
|---|---|---|---|---|
| HX1 | H1 | C3 | 220.0 | 8,376 |
| HX2 | H1 | C2 | 20.0 | 7,252 |
| HX3 | H2 | C2 | 205.0 | 9,235 |
| HX4 | H2 | C4 | 195.0 | 8,192 |
| HX5 | H3 | C1 | 270.0 | 8,364 |
| HX6 | H4 | C4 | 125.0 | 8,204 |

### Utility Units

| Type | Stream | Duty (kW) | Annual Cost ($/yr) |
|---|---|---|---|
| Cooling Water | H3 | 90.0 | 5,400 |
| Cooling Water | H4 | 100.0 | 6,000 |

___

## Cost Summary

| Component | Cost ($/yr) |
|---|---|
| Exchanger Capital (annualized at 25%/yr) | 49,623 |
| Utility Operating Cost | 11,400 |
| **Total Annualized Cost (TAC)** | **60,244** |

___

## Search Performance

| Metric | Value |
|---|---|
| Nodes expanded | 235 |
| Nodes generated | 599 |
| Maximum tree depth reached | 6 |
| Solution found at depth | 6 |
| Time elapsed | 0.022 seconds |

### Tree Level Breakdown

| Level | Nodes Expanded |
|---|---|
| 0 | 1 |
| 1 | 4 |
| 2 | 17 |
| 3 | 64 |
| 4 | 84 |
| 5 | 61 |
| 6 | 4 |

The search expanded a total of 235 nodes before reaching the goal at tree level 6. The branching factor peaks at levels 3 and 4 where the most feasible stream combinations exist, and collapses sharply at level 6 once streams are nearly satisfied.

___

## Energy Balance Verification

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

## Key Observations

The optimal network uses 6 process heat exchangers and 2 cooling water utility units. No external steam heating was required, as the total hot duty (1225 kW) exceeds the total cold duty (1035 kW), leaving a surplus of 190 kW that must be rejected via cooling water.

The A* search found the solution in 235 node expansions and 0.022 seconds, demonstrating the effectiveness of the two-component admissible heuristic and the anchor-hot pruning rule in containing the search space. Without pruning, the theoretical maximum number of paths through a 4H x 4C network would be substantially larger.

The solution places H1 against C3 and C2, H2 against C2 and C4, H3 against C1, and H4 against C4, achieving maximum heat recovery between process streams before resorting to utilities.
