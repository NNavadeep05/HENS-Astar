# CONCEPTS

All concepts used in HENS-Astar are briefly explained here.
___

## **HEAT TRANSFER CONCEPTS**

___

### 1. Heat Exchanger Network Synthesis (HENS)

A process plant has streams that need heating and streams that need cooling. Running everything through steam and cooling water works, but costs a lot. A cheaper option is to transfer heat directly between process streams through heat exchangers. HENS is the problem of deciding which streams to pair, in what order, and at what duties, to minimize total annual cost. The number of possible network configurations grows combinatorially with stream count, which is why a search algorithm is needed.

___

### 2. Stream (Hot and Cold)

A stream is a process fluid moving from one temperature to another. Hot streams need to be cooled; cold streams need to be heated. Each stream has a supply temperature, a target temperature, and a heat capacity flow rate. Total duty is FCp multiplied by the temperature change. Once a stream's duty is fully satisfied, it plays no further role in the search.

___

### 3. Heat Capacity Flow Rate (FCp)

FCp is mass flow rate times specific heat capacity, in units of kW per degree Celsius. A stream with FCp = 2.0 kW/C that drops 50 degrees releases 100 kW. It is treated as constant along each stream, the standard assumption for linear HENS. A higher FCp means the stream is thermally heavier and requires more energy per degree of temperature change.

___

### 4. Total Annualized Cost (TAC)

TAC is what A* minimizes. It combines capital and operating cost into one annual figure. Capital cost covers buying and installing heat exchangers, spread over the equipment lifetime using an annualization factor. Operating cost covers steam and cooling water consumed each year. TAC equals annualized exchange costs plus a fixed penalty per unit plus annual utility bills.

___

### 5. Minimum Temperature Approach (Delta T min)

For heat to flow from a hot stream to a cold stream, the hot side must stay warmer at every point along the exchanger. Delta T min is the minimum acceptable temperature gap, set to 10 degrees C in this project. Any match that violates this at either exchanger end is thermodynamically infeasible and is rejected before entering the search.

___

### 6. Log Mean Temperature Difference and Chen Approximation

The driving force for heat transfer varies along an exchanger as both stream temperatures change. **LMTD** is the correct average driving force for counter-current flow. This project uses the Chen (1987) approximation: LMTD is the cube root of (dT1 x dT2 x (dT1 + dT2) / 2), where dT1 and dT2 are the temperature differences at each exchanger end. It is accurate to within a few percent for most industrial cases.

___

### 7. Heat Exchanger Area and Capital Cost

**Area = duty / (U x LMTD)**, where U is the overall heat transfer coefficient. A larger duty or smaller driving force means a bigger, more expensive unit. Capital cost follows a power law: Cost = 8000 + 1200 x Area^0.6. The exponent below 1 reflects economies of scale.

___

### 8. External Utilities

When process streams cannot satisfy each other due to temperature incompatibility or a global heat imbalance, external utilities fill the gap. **Steam** heats cold streams that no hot process stream can reach. **Cooling water** removes heat from hot streams with nowhere to send it. Both carry an annual operating cost proportional to duty. Minimizing utility use is always cheaper, so the solver maximizes process-to-process heat recovery first.

___

### 9. Pinch Point and Composite Curves

The hot composite curve stacks all hot stream heat content over shared temperature intervals into a single temperature-enthalpy curve. The cold composite is built the same way. When both are plotted together with the cold curve shifted to maintain the minimum temperature approach, the closest point between them is the **pinch**. At the pinch, there is no remaining driving force, and the network splits into two thermodynamically independent regions.

___

### 10. QHmin and QCmin

Pinch analysis gives exact lower bounds on utility requirements before any network is designed. **QHmin** is the minimum steam that must be supplied, the heat deficit above the pinch that no process stream can cover. **QCmin** is the minimum cooling water required, the heat surplus below the pinch that no process stream can absorb. No feasible network can beat these targets.

___

### 11. Energy Balance and Feasibility

Across the whole network, heat in must equal heat out. At each exchanger, the hot stream must stay above the cold stream by at least Delta T min throughout. A state is declared a goal when every stream has its duty satisfied within 0.5 kW tolerance.

___

## **AI / SEARCH CONCEPTS**

___

### 12. State Space Search

State space search finds solutions by exploring configurations. A state captures the full situation at one point; here, a partial network. Starting from an empty network, the algorithm generates new states by placing heat exchangers one at a time until all streams are satisfied. The challenge is that the number of states is large, so the search needs guidance.

___

### 13. Decision Tree

Each node in the tree is a partial network. Each branch adds one heat exchanger. The root has no exchangers placed. At every level, the tree branches into as many options as there are feasible stream pairs. The path from root to a goal node is the complete sequence of decisions that built the network. Pruning is what keeps the tree manageable.

___

### 14. A* Search Algorithm

**A*** always expands the node with the lowest f(n) = g(n) + h(n). It uses a priority queue so the most promising node is always processed next, and a visited set to prevent re-expanding the same state twice. If the heuristic is admissible, the first goal node A* expanded is guaranteed to be optimal. That guarantee is why A* is used here instead of simpler search methods.

___

### 15. g(n) - Cost So Far

**g(n)** is the exact TAC accumulated from the root to node n. Every time an exchanger is placed, its annualized capital cost is added. Every time a utility is assigned, its operating cost is added. When A* reaches a goal, the g value of that node is the final TAC.

___

### 16. h(n) - Heuristic Function

**h(n)** estimates the cheapest possible way to complete the network from the current state. It must never overestimate; that is the admissibility requirement. In this project, h(n) uses three components: aggregate energy balance, per-stream temperature obligations, and pinch-based composite curve analysis. All three ignore future exchange capital costs, which makes them valid lower bounds.

___

### 17. f(n) = g(n) + h(n)

**f(n)** is the estimated total cost of any complete network passing through node n. A* expands nodes in order of increasing f. The g term is exact; the h term is an estimate. If h is admissible, the first goal node popped from the queue has the lowest possible g, which is the optimal solution.

___

### 18. Admissibility of a Heuristic

A heuristic is **admissible** if h(n) is always at most equal to the true remaining cost. Proving it here is straightforward: the heuristic charges only for utilities, ignores all future exchanger capital costs, and derives its bounds from thermodynamic conservation laws that any feasible solution must satisfy.

___

### 19. Pruning

Pruning cuts branches before fully exploring them. Four rules apply: pairs already in the match matrix cannot be matched again, pairs violating Delta T min are rejected immediately, the anchor-hot rule eliminates equivalent orderings, and states whose f value exceeds the best known solution are discarded. Without pruning, the search is intractable beyond small problem sizes.

___

### 20. Visited Set and Duplicate Detection

The **visited set** stores the canonical key of every expanded state. When a new state is generated, its key is checked; if already present the state is discarded. The key is a frozenset of match matrix entries combined with rounded remaining duties. Two states that reached the same network by different action sequences collapse into one.

___

### 21. Priority Queue (Min-Heap)

A **min-heap** always returns the element with the smallest value. A* uses this to always expand the node with the lowest f(n) next. Each entry is a tuple of (f_value, tree_level, tie_breaker, state), where the tie_breaker is a counter that prevents heapq from comparing two HENSState objects directly.

___

## **PROJECT-SPECIFIC CONCEPTS**

___

### 22. NetworkMatrix

The **NetworkMatrix** is a 2D dictionary keyed by (cold_id, hot_id). Each cell stores the sequence number of the exchanger placed there, or zero if none. It gives O(1) duplicate checking, a clean frozenset hash for the visited set, and a readable grid for output. Two states with the same matrix and the same remaining duties are treated as identical.

___

### 23. Anchor-Hot Pruning Rule (P4)

Without an ordering constraint, placing H1-C1 then H2-C2 and placing H2-C2 then H1-C1 appear as separate branches even though they produce the same network. The **anchor-hot rule** fixes this: at each level, only the lowest-indexed hot stream with remaining load is allowed to branch. This collapses equivalent orderings into a single path and significantly reduces nodes generated.

___

### 24. Pinch-Based Heuristic (v3)

The **v3 heuristic** adds composite curve analysis to the two earlier bounds. It builds hot and cold composite curves from streams still active at the current node, shifts the cold curve up by Delta T min, then computes QHmin and QCmin for the remaining subproblem. This is tighter than an energy balance alone because it accounts for temperature levels across all remaining streams simultaneously.

___

### 25. Tree Level and Solution Depth

**Tree level** is the number of process heat exchangers placed on the path from the root to the current node. The root is level zero; each exchanger placed adds one level. Solution depth is the tree level of the goal node. Optimality is defined by TAC, not depth, so a deeper solution with cheaper exchangers can beat a shallower one.

___

