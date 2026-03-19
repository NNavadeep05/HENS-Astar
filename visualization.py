"""
visualization.py  (v2 — Matrix-Based Decision Tree Visualization)
==================================================================
Three plots aligned to the decision-tree framing:

  1. MATRIX GRID DIAGRAM  — shows the 2D match matrix (Hi × Cj)
                           with match order, duties, and utility nodes
  2. A* DECISION TREE PATH — f/g/h per tree level + energy drawdown
  3. ENERGY BEFORE vs AFTER — grouped bar chart of stream duties

Authors : Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course  : Classical AI
"""

from __future__ import annotations
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import to_rgba
import numpy as np
from typing import Dict, List, Optional, TYPE_CHECKING

from state import HENSState

if TYPE_CHECKING:
    from state import HotStream, ColdStream
    from astar import AStarResult

# ---------------------------------------------------------------------------
# Shared palette
# ---------------------------------------------------------------------------
HOT_COLOR    = "#E8544A"
COLD_COLOR   = "#4A90D9"
HX_COLOR     = "#6B4A9E"
HEATER_COLOR = "#F5891D"
COOLER_COLOR = "#42B8C5"
BG_COLOR     = "#F7F7F7"
GRID_COLOR   = "#CCCCCC"


# ===========================================================================
# 1. MATRIX GRID DIAGRAM
# ===========================================================================

def plot_matrix_network(
    goal_state:   HENSState,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    title: str = "Heat Exchanger Network — Match Matrix",
) -> plt.Figure:
    """
    Draws the HEN as a 2D grid:
      columns = hot streams  (H1 … Hn)
      rows    = cold streams (C1 … Cm)
      cell    = filled (exchanger) or empty

    Alongside the grid:
      - right panels  : utility heaters (steam)
      - bottom panels : utility coolers (cooling water)
    """
    n_hot  = len(hot_streams)
    n_cold = len(cold_streams)

    hot_ids  = list(hot_streams.keys())
    cold_ids = list(cold_streams.keys())

    # Grid layout: main matrix + right column (heaters) + bottom row (coolers)
    fig = plt.figure(figsize=(max(10, n_hot * 2.2 + 3),
                               max(8,  n_cold * 2.0 + 3)))
    fig.patch.set_facecolor(BG_COLOR)

    gs = gridspec.GridSpec(
        n_cold + 2, n_hot + 2,
        figure=fig,
        hspace=0.05, wspace=0.05,
        left=0.12, right=0.95, top=0.92, bottom=0.12,
    )

    ax_main = fig.add_subplot(gs[:n_cold, :n_hot])
    ax_main.set_facecolor(BG_COLOR)

    # --- Draw grid lines ---------------------------------------------------
    for i in range(n_cold + 1):
        ax_main.axhline(y=i, color=GRID_COLOR, lw=0.8)
    for j in range(n_hot + 1):
        ax_main.axvline(x=j, color=GRID_COLOR, lw=0.8)

    # --- Fill exchanger cells -----------------------------------------------
    match_lookup = {}  # (hot_id, cold_id) → (duty, order)
    for m in goal_state.matches:
        match_lookup[(m.hot_id, m.cold_id)] = (m.duty, m.order)

    for ci, c_id in enumerate(cold_ids):
        for hi, h_id in enumerate(hot_ids):
            row = n_cold - 1 - ci   # invert: C1 at top
            col = hi

            if (h_id, c_id) in match_lookup:
                duty, order = match_lookup[(h_id, c_id)]
                # Draw filled cell
                rect = plt.Rectangle(
                    (col, row), 1, 1,
                    facecolor=to_rgba(HX_COLOR, 0.25),
                    edgecolor=HX_COLOR, lw=2,
                )
                ax_main.add_patch(rect)
                ax_main.text(
                    col + 0.5, row + 0.65,
                    f"HX{order}", ha="center", va="center",
                    fontsize=9, fontweight="bold", color=HX_COLOR,
                )
                ax_main.text(
                    col + 0.5, row + 0.3,
                    f"{duty:.0f} kW", ha="center", va="center",
                    fontsize=7.5, color="#444444",
                )
            else:
                ax_main.text(
                    col + 0.5, row + 0.5, "·",
                    ha="center", va="center",
                    fontsize=14, color=GRID_COLOR,
                )

    # --- Axis labels (stream IDs + temperatures) ----------------------------
    ax_main.set_xlim(0, n_hot)
    ax_main.set_ylim(0, n_cold)
    ax_main.set_xticks([i + 0.5 for i in range(n_hot)])
    ax_main.set_xticklabels([
        f"{h}\n{hot_streams[h].T_in:.0f}°→{hot_streams[h].T_out:.0f}°"
        for h in hot_ids
    ], fontsize=8, color=HOT_COLOR, fontweight="bold")
    ax_main.xaxis.set_ticks_position("top")
    ax_main.xaxis.set_label_position("top")

    ax_main.set_yticks([n_cold - 1 - i + 0.5 for i in range(n_cold)])
    ax_main.set_yticklabels([
        f"{c}\n{cold_streams[c].T_in:.0f}°→{cold_streams[c].T_out:.0f}°"
        for c in cold_ids
    ], fontsize=8, color=COLD_COLOR, fontweight="bold")
    ax_main.tick_params(length=0)

    # --- Utility heater annotations  (right of grid) -----------------------
    ax_heat = fig.add_subplot(gs[:n_cold, n_hot])
    ax_heat.set_facecolor(BG_COLOR)
    ax_heat.axis("off")

    heater_by_cold = {h.cold_id: h for h in goal_state.heaters}
    for ci, c_id in enumerate(cold_ids):
        row = n_cold - 1 - ci
        if c_id in heater_by_cold:
            h = heater_by_cold[c_id]
            ax_heat.add_patch(plt.FancyBboxPatch(
                (0.05, row / n_cold + 0.02), 0.9, 0.85 / n_cold,
                boxstyle="round,pad=0.02",
                facecolor=to_rgba(HEATER_COLOR, 0.3),
                edgecolor=HEATER_COLOR, lw=1.5,
                transform=ax_heat.transAxes,
            ))
            ax_heat.text(
                0.5, (row + 0.5) / n_cold,
                f"♨ Steam\n{h.duty:.0f} kW",
                ha="center", va="center",
                fontsize=7, color=HEATER_COLOR, fontweight="bold",
                transform=ax_heat.transAxes,
            )

    # --- Utility cooler annotations  (below grid) --------------------------
    ax_cool = fig.add_subplot(gs[n_cold, :n_hot])
    ax_cool.set_facecolor(BG_COLOR)
    ax_cool.axis("off")

    cooler_by_hot = {c.hot_id: c for c in goal_state.coolers}
    for hi, h_id in enumerate(hot_ids):
        if h_id in cooler_by_hot:
            c = cooler_by_hot[h_id]
            ax_cool.add_patch(plt.FancyBboxPatch(
                (hi / n_hot + 0.02, 0.1), 0.85 / n_hot, 0.8,
                boxstyle="round,pad=0.02",
                facecolor=to_rgba(COOLER_COLOR, 0.3),
                edgecolor=COOLER_COLOR, lw=1.5,
                transform=ax_cool.transAxes,
            ))
            ax_cool.text(
                (hi + 0.5) / n_hot, 0.5,
                f"❄ CW\n{c.duty:.0f} kW",
                ha="center", va="center",
                fontsize=7, color=COOLER_COLOR, fontweight="bold",
                transform=ax_cool.transAxes,
            )

    # --- Legend & title -----------------------------------------------------
    legend_patches = [
        mpatches.Patch(color=HX_COLOR,     alpha=0.5, label="Process HX (matched)"),
        mpatches.Patch(color=HEATER_COLOR, alpha=0.5, label="Steam Heater"),
        mpatches.Patch(color=COOLER_COLOR, alpha=0.5, label="Cooling Water"),
    ]
    fig.legend(handles=legend_patches, loc="lower right", fontsize=8, framealpha=0.85)
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.97)
    return fig


# ===========================================================================
# 2. A* DECISION TREE PATH  (f / g / h per level + energy drawdown)
# ===========================================================================

def plot_search_progress(
    path: List[HENSState],
    title: str = "A* Decision-Tree Path — f(n), g(n), h(n) per Level",
) -> plt.Figure:
    """
    Two-panel figure:
    Top : f(n), g(n), h(n) cost components vs tree level
    Bottom : Hot & cold remaining duty vs tree level (energy draw-down)
    """
    from heuristic import heuristic as compute_h

    levels  = [s.tree_level for s in path]
    g_vals  = [s.g_cost for s in path]
    h_vals  = [compute_h(s) for s in path]
    f_vals  = [g + h for g, h in zip(g_vals, h_vals)]
    hot_rem = [s.total_hot_remaining()  for s in path]
    cld_rem = [s.total_cold_remaining() for s in path]

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    fig.patch.set_facecolor(BG_COLOR)

    # ---- Top: f, g, h vs tree level ----------------------------------------
    ax1 = axes[0]
    ax1.set_facecolor(BG_COLOR)
    ax1.plot(levels, f_vals, "o-",  color="#6B4A9E", lw=2.2, ms=7, label="f(n) = g + h")
    ax1.plot(levels, g_vals, "s--", color=HOT_COLOR,  lw=1.8, ms=5, label="g(n) cost-so-far")
    ax1.plot(levels, h_vals, "^:",  color=COLD_COLOR,  lw=1.8, ms=5, label="h(n) heuristic")
    ax1.fill_between(levels, g_vals, f_vals, alpha=0.10, color=COLD_COLOR, label="h region")
    ax1.fill_between(levels, [0]*len(levels), g_vals, alpha=0.06, color=HOT_COLOR)

    # Mark each HX placement (level transition = new exchanger)
    for i, (lv, st) in enumerate(zip(levels, path)):
        if i > 0 and st.num_exchangers() > path[i-1].num_exchangers():
            ax1.axvline(x=lv, color=HX_COLOR, alpha=0.35, lw=1.2, linestyle="--")
            ax1.text(lv, max(f_vals) * 0.97,
                     f"HX{st.num_exchangers()}",
                     fontsize=7, color=HX_COLOR, ha="center", va="top",
                     bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.7))

    ax1.set_ylabel("Cost ($/yr)", fontsize=10)
    ax1.set_title(title, fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8, loc="upper right")
    ax1.grid(True, alpha=0.25)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # ---- Bottom: remaining duty draw-down ----------------------------------
    ax2 = axes[1]
    ax2.set_facecolor(BG_COLOR)
    ax2.fill_between(levels, hot_rem, alpha=0.30, color=HOT_COLOR, label="Hot remaining")
    ax2.fill_between(levels, cld_rem, alpha=0.30, color=COLD_COLOR, label="Cold remaining")
    ax2.plot(levels, hot_rem, "o-", color=HOT_COLOR,  lw=2, ms=5)
    ax2.plot(levels, cld_rem, "s-", color=COLD_COLOR, lw=2, ms=5)
    ax2.set_xlabel("Tree Level (# process HXs placed)", fontsize=10)
    ax2.set_ylabel("Remaining Duty (kW)", fontsize=10)
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.25, axis="y")
    ax2.set_xticks(levels)

    plt.tight_layout()
    return fig


# ===========================================================================
# 3. ENERGY BALANCE — BEFORE vs AFTER
# ===========================================================================

def plot_energy_before_after(
    goal_state:   HENSState,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    title: str = "Stream Energy Balance — Before vs After Synthesis",
) -> plt.Figure:
    """
    Grouped bar chart showing, for each stream:
      - Original total duty (pale bar)
      - Duty covered by process HX (coloured)
      - Duty covered by utility (hatched)
    """
    all_streams = (
        [(s_id, "hot",  hot_streams[s_id].Q_total) for s_id in hot_streams]
      + [(s_id, "cold", cold_streams[s_id].Q_total) for s_id in cold_streams]
    )
    labels = [s[0] for s in all_streams]
    totals = [s[2] for s in all_streams]
    kinds  = [s[1] for s in all_streams]

    # Compute process-HX coverage per stream
    hx_hot  = {h: 0.0 for h in hot_streams}
    hx_cold = {c: 0.0 for c in cold_streams}
    for m in goal_state.matches:
        hx_hot[m.hot_id]   += m.duty
        hx_cold[m.cold_id] += m.duty
    util_hot  = {c.hot_id:  c.duty for c in goal_state.coolers}
    util_cold = {h.cold_id: h.duty for h in goal_state.heaters}

    covered = []
    utility = []
    for sid, kind, _ in all_streams:
        if kind == "hot":
            covered.append(hx_hot.get(sid, 0.0))
            utility.append(util_hot.get(sid, 0.0))
        else:
            covered.append(hx_cold.get(sid, 0.0))
            utility.append(util_cold.get(sid, 0.0))

    xs = np.arange(len(labels))
    w  = 0.35

    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Total duty (pale background)
    colors_base = [HOT_COLOR if k == "hot" else COLD_COLOR for k in kinds]
    ax.bar(xs, totals, w * 2.2,
           color=[to_rgba(c, 0.12) for c in colors_base],
           edgecolor=[to_rgba(c, 0.4) for c in colors_base],
           linewidth=1, label="Original Duty")

    # Process HX coverage
    ax.bar(xs - w / 2, covered, w,
           color=[to_rgba(HX_COLOR, 0.75)] * len(xs),
           edgecolor=HX_COLOR, lw=0.8, label="Covered by Process HX")

    # Utility coverage (hatched)
    ax.bar(xs + w / 2, utility, w,
           color=[to_rgba(HEATER_COLOR, 0.65) if k == "cold" else to_rgba(COOLER_COLOR, 0.65)
                  for k in kinds],
           edgecolor="gray", lw=0.8, hatch="///", label="Utility (Steam/CW)")

    # Duty labels
    for i, (cov, util, tot) in enumerate(zip(covered, utility, totals)):
        pct = 100 * (cov + util) / max(tot, 1)
        ax.text(xs[i], tot + max(totals) * 0.01, f"{pct:.0f}%",
                ha="center", va="bottom", fontsize=7.5, color="#333333")

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Duty (kW)", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25, axis="y")

    # Colour-coded x-tick labels
    for tick, kind in zip(ax.get_xticklabels(), kinds):
        tick.set_color(HOT_COLOR if kind == "hot" else COLD_COLOR)
        tick.set_fontweight("bold")

    plt.tight_layout()
    return fig


# ===========================================================================
# Master entry point
# ===========================================================================

def visualize_all(
    result:       "AStarResult",
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float,
) -> None:
    """Generate and show all three visualization figures."""
    if not result.success:
        print("  No solution to visualize.")
        return

    print("\n  Generating visualizations …")
    fig1 = plot_matrix_network(result.goal_state, hot_streams, cold_streams)
    fig2 = plot_search_progress(result.path)
    fig3 = plot_energy_before_after(result.goal_state, hot_streams, cold_streams)
    plt.show()
    print("  Plots displayed. Close windows to exit.")
