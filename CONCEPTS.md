# CONCEPTS

This file explains every concept used in the HENS-Astar project. The target reader may have a strong heat transfer background but no AI background, or vice versa. Each concept is covered in plain prose. No prior knowledge of the other field is assumed.

___

## HEAT TRANSFER CONCEPTS

___

### 1. Heat Exchanger Network Synthesis (HENS)

A process plant typically has streams that need to be heated and streams that need to be cooled. Rather than supplying all that heating and cooling with external utilities, you look for opportunities to transfer heat from a hot stream directly to a cold stream through a heat exchanger. Heat Exchanger Network Synthesis is the engineering problem of deciding which hot streams should exchange heat with which cold streams, in what order, and at what duties, so that the total annual cost of the network is minimized. The difficulty is that the number of possible network configurations grows combinatorially with the number of streams.

___

### 2. Stream (Hot and Cold)

A stream is a process fluid that must change temperature from a supply value to a target value. A hot stream enters at a high temperature and must be cooled to a lower target — heat must be removed from it. A cold stream enters at a low temperature and must be heated to a higher target — heat must be added to it. Each stream is characterized by its supply temperature, target temperature, and heat capacity flow rate. The total heat duty of a stream is the product of its heat capacity flow rate and its temperature change.

___

### 3. Heat Capacity Flow Rate (FCp)

FCp is the product of the mass flow rate of a stream and its specific heat capacity. Its unit is kW per degree Celsius. When a stream with FCp = 2.0 kW/°C changes temperature by 10°C, it exchanges 20 kW of heat. FCp is treated as constant along each stream in this project, which is the standard assumption in linear HENS problems. A larger FCp means a stream is thermally "heavy" and requires more energy per degree of temperature change.

___

### 4. Total Annualized Cost (TAC)

TAC is the single objective function being minimized. It combines two kinds of cost: capital costs, which arise from purchasing and installing heat exchangers, and operating costs, which arise from consuming steam or cooling water every year. Capital costs are converted to an annual equivalent by multiplying by an annualization factor that represents the cost of money over the equipment lifetime. TAC in this project equals the sum of annualized exchanger costs, plus a fixed penalty per unit, plus the annual utility bills.

___

### 5. Minimum Temperature Approach (Delta T min)

For heat to flow spontaneously from a hot stream to a cold stream, the hot stream must always be warmer than the cold stream at every point along the exchanger. Delta T min is the minimum acceptable temperature difference between the two streams at any point in a heat exchanger. A value of 10°C means the hot stream must exceed the cold stream temperature by at least 10°C throughout. This constraint prevents thermodynamically infeasible matches and also ensures a practical driving force for heat transfer.

___

### 6. Log Mean Temperature Difference (LMTD) — Chen Approximation

The rate of heat transfer in an exchanger depends on the temperature difference between the two streams, which varies along the length of the exchanger. The log mean temperature difference (LMTD) is the mathematically correct average driving force for a counter-current exchanger. Because the logarithm makes it inconvenient to compute during optimization, this project uses the Chen (1987) approximation: LMTD is approximated as the cube root of the product of the two terminal temperature differences times their arithmetic mean. This approximation is accurate to within a few percent for most practical cases.

___

### 7. Heat Exchanger Area and Capital Cost

The required heat transfer area of an exchanger is calculated as the duty divided by the product of the overall heat transfer coefficient and the LMTD. A larger area means a physically bigger and more expensive unit. Capital cost follows a power-law correlation: cost equals a fixed charge plus a variable charge proportional to area raised to an exponent less than one, reflecting economies of scale for larger equipment. In this project the cost law is: Capital ($) = 8000 + 1200 × Area^0.6.

___

### 8. External Utilities (Steam and Cooling Water)

When process-to-process heat exchange cannot satisfy all stream duties — either because temperatures are incompatible or because there is a global surplus of heat on one side — external utilities are used. Steam is the external heating utility: it delivers heat to cold streams that cannot be fully heated by hot process streams. Cooling water is the external cooling utility: it removes heat from hot streams that cannot be fully cooled by cold process streams. Both utilities carry an annual operating cost proportional to the duty they handle.

___

### 9. Pinch Point and Composite Curves

The composite curve is a single temperature-enthalpy (T-H) curve that represents all streams of one type combined. The hot composite curve is constructed by stacking the heat content of all hot streams over their shared temperature intervals. The cold composite is built the same way. When the two composite curves are plotted together (with the cold curve shifted horizontally to maintain the minimum temperature approach), the point where they most closely approach each other is the pinch. At the pinch, there is no remaining thermodynamic driving force for heat transfer, and the network naturally divides into two independent regions above and below this point.

___

### 10. QHmin and QCmin (Minimum Utility Targets)

Pinch analysis provides exact lower bounds on the external utility requirements before any network is designed. QHmin is the minimum steam duty that must be supplied to satisfy all cold stream requirements — it represents the unavoidable deficit of heat above the pinch. QCmin is the minimum cooling water duty that must be used — it represents the unavoidable surplus of heat below the pinch. Any network that uses less than QHmin or QCmin is thermodynamically infeasible. Any network that uses exactly these amounts has achieved the theoretical minimum utility consumption.

___

### 11. Energy Balance and Feasibility

At the level of the whole network, the first law of thermodynamics requires that heat in equals heat out. Total hot duty plus steam input must equal total cold duty plus cooling water removed. At the level of each individual heat exchanger, feasibility requires that the temperature difference between the hot and cold streams is non-negative everywhere and meets the Delta T min constraint. In the search, a goal state is declared feasible when every stream has had its full duty satisfied within a small numerical tolerance.

___

## AI / SEARCH CONCEPTS

___

### 12. State Space Search

State space search is a general method for solving problems where a solution is found by exploring a space of possible configurations. A state describes the complete situation at one point in time. Starting from an initial state, the algorithm generates successor states by applying valid actions. The search continues until a state satisfying the goal condition is reached. In this project, each state is a partial heat exchanger network represented as a matrix of stream matches, and the goal is a state where all stream duties are satisfied.

___

### 13. Decision Tree

A decision tree is a way of organizing a state space search where every node corresponds to a sequence of choices made so far, and every branch corresponds to one new choice. The root is the starting condition with no choices made. At each level of the tree, one decision is taken — in this project, one new heat exchanger is placed. The tree branches at each level into as many successors as there are feasible stream pairs available. The path from the root to a goal node records the complete sequence of decisions that built the network.

___

### 14. A* Search Algorithm

A* is a best-first graph search algorithm that always expands the node with the lowest value of f(n) = g(n) + h(n), where g is the cost from the start to the current node and h is a heuristic estimate of the cost from the current node to the goal. A* is guaranteed to find the optimal (lowest-cost) solution if the heuristic is admissible, meaning it never overestimates the true remaining cost. A* uses a priority queue to always process the most promising node next, and a visited-state set to avoid re-expanding the same configuration twice.

___

### 15. g(n) — Cost So Far

g(n) is the total cost accumulated along the path from the root of the search tree to the current node n. In this project, g(n) is the total annualized cost of all heat exchangers placed so far plus the cost of any utility units already assigned. It is an exact value computed incrementally as each exchanger is added. When A* selects a goal node, the g(n) value of that node is the final TAC of the synthesized network.

___

### 16. h(n) — Heuristic Function

h(n) is an estimate of the cheapest way to complete the network from the current state to a goal state. It must be fast to compute and must never overestimate the true remaining cost. In this project, h(n) is computed using three components: an aggregate energy balance, a per-stream temperature obligation, and a pinch-based composite curve analysis. The heuristic ignores all capital costs of future exchangers and uses only utility costs, which makes it a valid lower bound.

___

### 17. f(n) = g(n) + h(n)

f(n) is the estimated total cost of a complete network that passes through node n. The g term captures what has already been spent, and the h term estimates what must still be spent. A* expands nodes in increasing order of f(n). If h is admissible, the first goal node expanded by A* has the minimum possible g(n) value, meaning A* has found the globally optimal solution. The f(n) value of intermediate nodes can only grow or stay flat as the search progresses toward the goal.

___

### 18. Admissibility of a Heuristic

A heuristic h(n) is admissible if it never overestimates the true cost to reach a goal from n. Admissibility is what guarantees that A* finds the optimal solution. To prove admissibility, it is sufficient to show that h(n) is a strict lower bound on all remaining costs. In this project, admissibility holds because the heuristic accounts only for utility costs (which are unavoidable), ignores all capital costs of future heat exchangers (which are non-negative), and is derived from thermodynamic conservation laws that the real solution must satisfy.

___

### 19. Pruning

Pruning means discarding a branch of the search tree before fully exploring it, because the branch is known to be redundant or suboptimal. Without pruning, the search would explore exponentially many configurations. In this project, several pruning rules are applied: pairs already matched in the current state cannot be matched again, pairs that violate Delta T min are excluded immediately, and states whose estimated total cost exceeds the best known solution are discarded. The anchor-hot rule provides additional structural pruning specific to this problem.

___

### 20. Visited Set and Duplicate Detection

A visited set (also called a closed set) stores the canonical key of every state that has already been expanded. When a new state is generated, its key is checked against this set. If the key is already present, the state is a duplicate and is discarded. This prevents the search from cycling or redundantly exploring the same network configuration arrived at by a different sequence of actions. The canonical key in this project is a frozenset of the current match matrix entries combined with the rounded remaining duties on each stream.

___

### 21. Priority Queue (Min-Heap)

A priority queue is a data structure that always returns the element with the smallest value in constant time. A* uses a min-heap priority queue keyed on f(n) so that it always expands the most promising node next. In Python, the heapq module implements a binary min-heap. Each entry in the queue is a tuple (f_value, tie-break, state), and heapq.heappop returns the tuple with the smallest f_value. The priority queue is called the open set or frontier in search algorithm terminology.

___

## PROJECT-SPECIFIC CONCEPTS

___

### 22. NetworkMatrix (the synthesis matrix)

The NetworkMatrix is the 2D data structure that records which hot and cold stream pairs have been matched in the current state. Rows correspond to cold streams and columns to hot streams. Each cell holds the integer order in which that exchanger was placed (starting from 1), or zero if no exchanger connects that pair. The matrix provides O(1) lookup for duplicate detection, a clean hash key for the visited set, and a readable grid for visualization. Two states with the same matrix and the same remaining duties are considered identical by the search.

___

### 23. Anchor-Hot Pruning Rule (P4)

The anchor-hot rule is a problem-specific pruning rule that prevents the search from generating states that are structurally equivalent but reach identical networks by a different ordering of actions. At each level of the decision tree, the hot stream with the largest remaining duty is fixed as the "anchor" — every branch at that level must include this hot stream. This eliminates orderings that would only differ in the sequence of which hot stream's matches are placed first, without changing the resulting network. The rule is safe because it does not remove any network topology, only redundant orderings.

___

### 24. Pinch-Based Heuristic (v3)

The v3 heuristic is the third iteration of the admissible lower bound used in this project. It adds a composite curve analysis (Component C) to the two earlier bounds. Component C constructs the hot and cold composite curves from the streams that still have remaining duty at the current search node, shifts the cold curve by Delta T min, and computes QHmin and QCmin — the minimum utility targets implied by pinch analysis on the remaining subproblem. This gives a tighter lower bound than the energy balance or temperature obligation alone, because it accounts for temperature-level constraints across the entire remaining subproblem simultaneously.

___

### 25. Tree Level and Solution Depth

The tree level of a node is the number of process heat exchangers that have been placed on the path from the root to that node. The root has tree level zero. Each time an action places a new heat exchanger, the tree level increases by one. The solution depth is the tree level of the goal node — the number of process exchangers in the optimal network. A shallower solution is generally preferred, but optimality is defined by TAC, not depth. The tree level breakdown table in the output shows how many nodes the search expanded at each depth.

___

### 26. Scalability — 4H/4C vs 8H/8C

The 4H/4C benchmark has 4 hot and 4 cold streams, giving at most 16 possible stream pairs. The 8H/8C benchmark has 8 hot and 8 cold streams, giving at most 64 possible pairs. The search space grows combinatorially: with more streams, each level of the decision tree branches more widely, and more levels may be required to satisfy all duties. The scalability comparison table in the output measures how the number of nodes expanded, wall-clock time, and final TAC change as the problem size doubles in each dimension. This demonstrates the practical reach of the A* approach with the v3 heuristic and the pruning rules in place.
