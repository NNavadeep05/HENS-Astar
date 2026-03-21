"""
visualization.py  (v3 — Matrix-Based Decision Tree Visualization + Composite Curves)
=====================================================================================
Four plots aligned to the decision-tree framing:

  1. MATRIX GRID DIAGRAM  — shows the 2D match matrix (Hi × Cj)
                           with match order, duties, and utility nodes
  2. A* DECISION TREE PATH — f/g/h per tree level + energy drawdown
  3. ENERGY BEFORE vs AFTER — grouped bar chart of stream duties
  4. T-H COMPOSITE CURVES  — hot/cold composite curves with pinch annotation,
                              QHmin and QCmin shading

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
# 4. T-H COMPOSITE CURVES  (Pinch analysis visualization)
# ===========================================================================

def _build_curve_points(
    segments: List,   # list of (T_high, T_low, FCp)
) -> List:
    """
    Build composite curve as list of (H_cumulative, T) points.
    Sweeps from highest T to lowest T.
    """
    if not segments:
        return []

    temps = set()
    for T_high, T_low, _ in segments:
        temps.add(T_high)
        temps.add(T_low)
    temps_sorted = sorted(temps, reverse=True)

    points = []
    H = 0.0
    points.append((H, temps_sorted[0]))

    for i in range(len(temps_sorted) - 1):
        T_top = temps_sorted[i]
        T_bot = temps_sorted[i + 1]
        dT = T_top - T_bot

        FCp_sum = sum(
            fcp for (th, tl, fcp) in segments
            if th >= T_top - 1e-9 and tl <= T_bot + 1e-9
        )
        H += FCp_sum * dT
        points.append((H, T_bot))

    return points  # (H, T) from high-T to low-T


def plot_composite_curves(
    goal_state,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float = 10.0,
    title: str = "Temperature-Enthalpy Composite Curves",
) -> plt.Figure:
    """
    Build and plot the T-H composite curves for all streams,
    with pinch point annotation and QHmin / QCmin shading.

    Algorithm:
    1. Build hot composite: segments (T_in, T_out, FCp) for each hot stream,
       sweep temperature breakpoints from high to low, accumulate enthalpy.
    2. Build cold composite the same way, then shift the cold curve
       horizontally (right) so the minimum vertical gap to the hot
       curve equals delta_T_min — this gives the utility targets.
    3. The pinch is the temperature where minimum vertical gap occurs.
    4. QHmin = gap at low-enthalpy end of cold curve (steam needed);
       QCmin = gap at high-enthalpy end of hot curve (cooling needed).
    """
    # --- Build hot segments -------------------------------------------------
    hot_segs = []
    for h in hot_streams.values():
        hot_segs.append((h.T_in, h.T_out, h.FCp))

    # --- Build cold segments ------------------------------------------------
    cold_segs = []
    for c in cold_streams.values():
        cold_segs.append((c.T_out, c.T_in, c.FCp))  # (T_high, T_low, FCp)

    hot_pts  = _build_curve_points(hot_segs)   # (H, T) high→low T
    cold_pts = _build_curve_points(cold_segs)  # (H, T) high→low T

    if not hot_pts or not cold_pts:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "Insufficient data for composite curves",
                ha="center", va="center", transform=ax.transAxes)
        return fig

    # Reverse to ascending T for plotting (low T → high T)
    hot_plot  = list(reversed(hot_pts))   # (H, T) ascending T
    cold_plot = list(reversed(cold_pts))  # (H, T) ascending T

    hot_total  = hot_pts[-1][0]
    cold_total = cold_pts[-1][0]

    # --- Shift cold curve horizontally to enforce ΔTmin --------------------
    # The cold curve is shifted RIGHT by an offset so that the minimum vertical
    # temperature gap (hot T - cold T at same H) equals delta_T_min.
    # We bisect over the horizontal shift.
    #
    # For a given shift S, the cold curve becomes (H + S, T).
    # We interpolate T at common H values and find the minimum gap.

    def min_vertical_gap(shift: float) -> float:
        """Minimum (hot_T - cold_T) evaluated at H-breakpoints."""
        # Collect all H breakpoints
        h_vals_hot  = [p[0] for p in hot_plot]
        h_vals_cold = [p[0] + shift for p in cold_plot]

        all_H = sorted(set(h_vals_hot + h_vals_cold))
        # Restrict to overlap region
        H_start = max(min(h_vals_hot), min(h_vals_cold))
        H_end   = min(max(h_vals_hot), max(h_vals_cold))

        if H_end <= H_start:
            return float("inf")   # no overlap

        gaps = []
        for H in all_H:
            if H < H_start - 1e-6 or H > H_end + 1e-6:
                continue
            T_hot  = _interp_T(hot_plot,  H)
            T_cold = _interp_T([(p[0] + shift, p[1]) for p in cold_plot], H)
            if T_hot is not None and T_cold is not None:
                gaps.append(T_hot - T_cold)

        return min(gaps) if gaps else float("inf")

    def _interp_T(pts, H_query):
        """Linearly interpolate T at H_query from list of (H, T) ascending H."""
        if not pts:
            return None
        H_arr = [p[0] for p in pts]
        T_arr = [p[1] for p in pts]
        if H_query < H_arr[0] or H_query > H_arr[-1]:
            return None
        for k in range(len(pts) - 1):
            H_lo, H_hi = H_arr[k], H_arr[k + 1]
            if H_lo <= H_query <= H_hi:
                if abs(H_hi - H_lo) < 1e-9:
                    return T_arr[k]
                frac = (H_query - H_lo) / (H_hi - H_lo)
                return T_arr[k] + frac * (T_arr[k + 1] - T_arr[k])
        return None

    # Bisect to find the shift that gives minimum gap = delta_T_min
    lo, hi_shift = 0.0, cold_total + hot_total
    for _ in range(60):
        mid = (lo + hi_shift) / 2.0
        gap = min_vertical_gap(mid)
        if gap < delta_T_min:
            lo = mid
        else:
            hi_shift = mid
    best_shift = (lo + hi_shift) / 2.0

    # Compute QHmin and QCmin from the shift
    # QHmin = steam needed to push cold curve start to meet hot curve
    #       = cold_total - hot_total + shift  (energy balance after shift)
    # QCmin = cooling needed for hot surplus
    QHmin = max(0.0, cold_total + best_shift - hot_total)
    QCmin = max(0.0, hot_total - cold_total - best_shift)

    # Build shifted cold curve for plotting
    cold_shifted = [(p[0] + best_shift, p[1]) for p in cold_plot]  # (H, T)

    # --- Find pinch temperature (minimum gap location) ----------------------
    pinch_H   = 0.0
    pinch_T   = 0.0
    min_gap_seen = float("inf")

    all_H_pts = sorted(set(
        [p[0] for p in hot_plot] +
        [p[0] for p in cold_shifted]
    ))
    H_start_ov = max(hot_plot[0][0],  cold_shifted[0][0])
    H_end_ov   = min(hot_plot[-1][0], cold_shifted[-1][0])

    for H in all_H_pts:
        if H < H_start_ov - 1e-6 or H > H_end_ov + 1e-6:
            continue
        T_hot  = _interp_T(hot_plot,      H)
        T_cold = _interp_T(cold_shifted,  H)
        if T_hot is not None and T_cold is not None:
            gap = T_hot - T_cold
            if gap < min_gap_seen:
                min_gap_seen = gap
                pinch_H = H
                pinch_T = T_hot

    # --- Plot ----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Hot composite curve
    hot_H = [p[0] for p in hot_plot]
    hot_T = [p[1] for p in hot_plot]
    ax.plot(hot_H, hot_T, color=HOT_COLOR, lw=2.5, label="Hot Composite", zorder=3)

    # Cold composite curve (shifted)
    col_H = [p[0] for p in cold_shifted]
    col_T = [p[1] for p in cold_shifted]
    ax.plot(col_H, col_T, color=COLD_COLOR, lw=2.5, label="Cold Composite", zorder=3)

    # Pinch vertical dashed line
    ax.axvline(x=pinch_H, color="#888888", lw=1.4, linestyle="--", zorder=2)
    ax.text(
        pinch_H, pinch_T + 3,
        f"Pinch\n{pinch_T:.1f}°C",
        ha="center", va="bottom", fontsize=9, color="#444444",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
    )

    # QHmin shading: steam region — left of cold start, fills gap above cold
    if best_shift > 1e-3 and QHmin > 1e-3:
        # Region: from H=0 to cold curve start (= best_shift), above 0
        # Fill between x=0 and x=best_shift as a vertical band
        cold_start_T = cold_shifted[0][1]
        H_fill = [0.0, best_shift, best_shift, 0.0]
        T_fill = [0.0, 0.0, cold_start_T, cold_start_T]
        ax.fill(H_fill, T_fill, color="orange", alpha=0.18, zorder=1,
                label=f"QHmin = {QHmin:.1f} kW")

    # QCmin shading: cooling region — right of hot curve end
    if QCmin > 1e-3:
        hot_end_H = hot_H[-1]
        cold_end_H = col_H[-1]
        hot_end_T  = hot_T[-1]
        H_fill = [hot_end_H, max(hot_end_H, cold_end_H),
                  max(hot_end_H, cold_end_H), hot_end_H]
        T_fill = [0.0, 0.0, hot_end_T, hot_end_T]
        ax.fill(H_fill, T_fill, color="cyan", alpha=0.18, zorder=1,
                label=f"QCmin = {QCmin:.1f} kW")

    ax.set_xlabel("Enthalpy H (kW)", fontsize=11)
    ax.set_ylabel("Temperature T (°C)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.25)

    # Annotation box with ΔTmin
    ax.text(
        0.97, 0.05,
        f"ΔTmin = {delta_T_min:.0f}°C\nQHmin = {QHmin:.1f} kW\nQCmin = {QCmin:.1f} kW",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.85, ec=GRID_COLOR),
    )

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
    """Generate and show all four visualization figures."""
    if not result.success:
        print("  No solution to visualize.")
        return

    print("\n  Generating visualizations …")
    fig1 = plot_matrix_network(result.goal_state, hot_streams, cold_streams)
    fig2 = plot_search_progress(result.path)
    fig3 = plot_energy_before_after(result.goal_state, hot_streams, cold_streams)
    fig4 = plot_composite_curves(result.goal_state, hot_streams, cold_streams, delta_T_min)
    plt.show()
    print("  Plots displayed. Close windows to exit.")
