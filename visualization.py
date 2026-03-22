"""
visualization.py
================
Four publication-quality plots for the HENS A* project.

  1. Network matrix grid — match topology with exchanger duties and utilities
  2. A* search path — f(n), g(n), h(n) per tree level + duty draw-down
  3. Energy balance — stream duty coverage before and after synthesis
  4. T-H composite curves — pinch analysis with QHmin and QCmin

Authors: Navadeep Nandedapu, Raghu Perala, Vivekadithya Yayavaram, Daivamsh Atoori
Course:  Classical AI
"""

from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import to_rgba
from matplotlib.ticker import FuncFormatter
import numpy as np
from typing import Dict, List, TYPE_CHECKING

from state import HENSState

if TYPE_CHECKING:
    from state import HotStream, ColdStream
    from astar import AStarResult


# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
BG         = "#0F1117"
SURFACE    = "#1A1D27"
BORDER     = "#2A2D3A"
HOT        = "#FF6B6B"
HOT_DIM    = "#7A3030"
COLD       = "#4FC3F7"
COLD_DIM   = "#1A4A6B"
HX         = "#A78BFA"
HX_DIM     = "#3D2F6B"
STEAM      = "#FB923C"
CW         = "#34D399"
TEXT       = "#E8EAF0"
TEXT_DIM   = "#6B7280"
GRID       = "#1F2335"
ACCENT     = "#F59E0B"

plt.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    SURFACE,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   TEXT,
    "axes.titlecolor":   TEXT,
    "xtick.color":       TEXT_DIM,
    "ytick.color":       TEXT_DIM,
    "text.color":        TEXT,
    "grid.color":        GRID,
    "grid.linewidth":    0.6,
    "legend.facecolor":  SURFACE,
    "legend.edgecolor":  BORDER,
    "legend.labelcolor": TEXT,
    "font.family":       "monospace",
})


def _money(x, _):
    return f"${x:,.0f}"


# ---------------------------------------------------------------------------
# 1. Network matrix grid
# ---------------------------------------------------------------------------

def plot_matrix_network(
    goal_state:   HENSState,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    title: str = "Heat Exchanger Network — Match Matrix",
) -> plt.Figure:

    n_hot  = len(hot_streams)
    n_cold = len(cold_streams)
    hot_ids  = list(hot_streams.keys())
    cold_ids = list(cold_streams.keys())

    cell = 1.8
    pad  = 1.6
    fig_w = n_hot  * cell + pad * 2.5
    fig_h = n_cold * cell + pad * 2.0

    fig = plt.figure(figsize=(max(11, fig_w), max(8, fig_h)))
    fig.patch.set_facecolor(BG)

    gs = gridspec.GridSpec(
        n_cold + 2, n_hot + 2, figure=fig,
        hspace=0.04, wspace=0.04,
        left=0.13, right=0.94, top=0.90, bottom=0.10,
    )

    ax = fig.add_subplot(gs[:n_cold, :n_hot])
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0, n_hot)
    ax.set_ylim(0, n_cold)

    # Grid
    for i in range(n_cold + 1):
        ax.axhline(y=i, color=BORDER, lw=1.0, zorder=1)
    for j in range(n_hot + 1):
        ax.axvline(x=j, color=BORDER, lw=1.0, zorder=1)

    match_lookup = {(m.hot_id, m.cold_id): (m.duty, m.order) for m in goal_state.matches}

    for ci, c_id in enumerate(cold_ids):
        for hi, h_id in enumerate(hot_ids):
            row = n_cold - 1 - ci
            col = hi
            if (h_id, c_id) in match_lookup:
                duty, order = match_lookup[(h_id, c_id)]
                ax.add_patch(mpatches.FancyBboxPatch(
                    (col + 0.06, row + 0.06), 0.88, 0.88,
                    boxstyle="round,pad=0.04",
                    facecolor=to_rgba(HX, 0.18),
                    edgecolor=HX, lw=1.8, zorder=2,
                ))
                ax.text(col + 0.5, row + 0.64, f"HX{order}",
                        ha="center", va="center",
                        fontsize=8.5, fontweight="bold", color=HX, zorder=3)
                ax.text(col + 0.5, row + 0.30, f"{duty:.0f} kW",
                        ha="center", va="center",
                        fontsize=7, color=TEXT_DIM, zorder=3)
            else:
                ax.text(col + 0.5, row + 0.5, "·",
                        ha="center", va="center",
                        fontsize=16, color=BORDER, zorder=2)

    ax.set_xticks([i + 0.5 for i in range(n_hot)])
    ax.set_xticklabels(
        [f"{h}  {hot_streams[h].T_in:.0f}→{hot_streams[h].T_out:.0f}°C"
         for h in hot_ids],
        fontsize=7.5, color=HOT, fontweight="bold",
    )
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")

    ax.set_yticks([n_cold - 1 - i + 0.5 for i in range(n_cold)])
    ax.set_yticklabels(
        [f"{c}  {cold_streams[c].T_in:.0f}→{cold_streams[c].T_out:.0f}°C"
         for c in cold_ids],
        fontsize=7.5, color=COLD, fontweight="bold",
    )
    ax.tick_params(length=0)

    # Steam heaters (right column)
    ax_heat = fig.add_subplot(gs[:n_cold, n_hot])
    ax_heat.set_facecolor(BG)
    ax_heat.axis("off")
    heater_by_cold = {h.cold_id: h for h in goal_state.heaters}
    for ci, c_id in enumerate(cold_ids):
        row = n_cold - 1 - ci
        if c_id in heater_by_cold:
            h = heater_by_cold[c_id]
            ax_heat.add_patch(mpatches.FancyBboxPatch(
                (0.05, row / n_cold + 0.04), 0.88, 0.82 / n_cold,
                boxstyle="round,pad=0.03",
                facecolor=to_rgba(STEAM, 0.15),
                edgecolor=STEAM, lw=1.4,
                transform=ax_heat.transAxes,
            ))
            ax_heat.text(0.5, (row + 0.5) / n_cold,
                         f"Steam\n{h.duty:.0f} kW",
                         ha="center", va="center",
                         fontsize=6.5, color=STEAM, fontweight="bold",
                         transform=ax_heat.transAxes)

    # Cooling water (bottom row)
    ax_cool = fig.add_subplot(gs[n_cold, :n_hot])
    ax_cool.set_facecolor(BG)
    ax_cool.axis("off")
    cooler_by_hot = {c.hot_id: c for c in goal_state.coolers}
    for hi, h_id in enumerate(hot_ids):
        if h_id in cooler_by_hot:
            c = cooler_by_hot[h_id]
            ax_cool.add_patch(mpatches.FancyBboxPatch(
                (hi / n_hot + 0.03, 0.08), 0.82 / n_hot, 0.82,
                boxstyle="round,pad=0.03",
                facecolor=to_rgba(CW, 0.15),
                edgecolor=CW, lw=1.4,
                transform=ax_cool.transAxes,
            ))
            ax_cool.text((hi + 0.5) / n_hot, 0.5,
                         f"CW\n{c.duty:.0f} kW",
                         ha="center", va="center",
                         fontsize=6.5, color=CW, fontweight="bold",
                         transform=ax_cool.transAxes)

    legend_patches = [
        mpatches.Patch(color=HX,    alpha=0.7, label="Process HX"),
        mpatches.Patch(color=STEAM, alpha=0.7, label="Steam"),
        mpatches.Patch(color=CW,    alpha=0.7, label="Cooling Water"),
    ]
    fig.legend(handles=legend_patches, loc="lower right",
               fontsize=8, framealpha=0.9,
               facecolor=SURFACE, edgecolor=BORDER)
    fig.suptitle(title, fontsize=12, fontweight="bold", color=TEXT, y=0.96)
    return fig


# ---------------------------------------------------------------------------
# 2. A* search path
# ---------------------------------------------------------------------------

def plot_search_progress(
    path: List[HENSState],
    title: str = "A* Decision-Tree Path",
) -> plt.Figure:

    from heuristic import heuristic as compute_h

    levels  = [s.tree_level for s in path]
    g_vals  = [s.g_cost for s in path]
    h_vals  = [compute_h(s) for s in path]
    f_vals  = [g + h for g, h in zip(g_vals, h_vals)]
    hot_rem = [s.total_hot_remaining()  for s in path]
    cld_rem = [s.total_cold_remaining() for s in path]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), sharex=True,
                                    gridspec_kw={"hspace": 0.06})
    fig.patch.set_facecolor(BG)

    # Top panel: f, g, h
    ax1.set_facecolor(SURFACE)
    ax1.fill_between(levels, g_vals, f_vals, alpha=0.12, color=COLD)
    ax1.fill_between(levels, [0] * len(levels), g_vals, alpha=0.08, color=HOT)

    ax1.plot(levels, f_vals, "o-",  color=HX,   lw=2.2, ms=7,
             label="f(n) = g + h", zorder=4)
    ax1.plot(levels, g_vals, "s--", color=HOT,  lw=1.8, ms=5,
             label="g(n)  cost so far", zorder=4)
    ax1.plot(levels, h_vals, "^:",  color=COLD, lw=1.8, ms=5,
             label="h(n)  heuristic", zorder=4)

    # Mark each exchanger placement
    for i, (lv, st) in enumerate(zip(levels, path)):
        if i > 0 and st.num_exchangers() > path[i - 1].num_exchangers():
            ax1.axvline(x=lv, color=HX, alpha=0.3, lw=1.2, ls="--", zorder=2)
            ax1.text(lv, max(f_vals) * 0.96,
                     f"HX{st.num_exchangers()}",
                     fontsize=7, color=HX, ha="center", va="top",
                     bbox=dict(boxstyle="round,pad=0.2",
                               fc=SURFACE, ec=HX, alpha=0.9))

    ax1.set_ylabel("Cost  ($/yr)", fontsize=10, color=TEXT)
    ax1.set_title(title, fontsize=12, fontweight="bold", color=TEXT, pad=10)
    ax1.legend(fontsize=8, loc="upper right")
    ax1.grid(True, alpha=0.4)
    ax1.yaxis.set_major_formatter(FuncFormatter(_money))
    ax1.spines[:].set_color(BORDER)

    # Bottom panel: duty draw-down
    ax2.set_facecolor(SURFACE)
    ax2.fill_between(levels, hot_rem, alpha=0.25, color=HOT)
    ax2.fill_between(levels, cld_rem, alpha=0.25, color=COLD)
    ax2.plot(levels, hot_rem, "o-", color=HOT,  lw=2, ms=5,
             label="Hot remaining")
    ax2.plot(levels, cld_rem, "s-", color=COLD, lw=2, ms=5,
             label="Cold remaining")

    ax2.set_xlabel("Tree Level  (exchangers placed)", fontsize=10, color=TEXT)
    ax2.set_ylabel("Remaining Duty  (kW)", fontsize=10, color=TEXT)
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.4, axis="y")
    ax2.set_xticks(levels)
    ax2.spines[:].set_color(BORDER)

    return fig


# ---------------------------------------------------------------------------
# 3. Energy balance
# ---------------------------------------------------------------------------

def plot_energy_before_after(
    goal_state:   HENSState,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    title: str = "Stream Energy Balance",
) -> plt.Figure:

    all_streams = (
        [(sid, "hot",  hot_streams[sid].Q_total)  for sid in hot_streams] +
        [(sid, "cold", cold_streams[sid].Q_total) for sid in cold_streams]
    )
    labels = [s[0] for s in all_streams]
    totals = [s[2] for s in all_streams]
    kinds  = [s[1] for s in all_streams]

    hx_hot  = {h: 0.0 for h in hot_streams}
    hx_cold = {c: 0.0 for c in cold_streams}
    for m in goal_state.matches:
        hx_hot[m.hot_id]   += m.duty
        hx_cold[m.cold_id] += m.duty

    util_hot  = {c.hot_id:  c.duty for c in goal_state.coolers}
    util_cold = {h.cold_id: h.duty for h in goal_state.heaters}

    covered, utility = [], []
    for sid, kind, _ in all_streams:
        if kind == "hot":
            covered.append(hx_hot.get(sid, 0.0))
            utility.append(util_hot.get(sid, 0.0))
        else:
            covered.append(hx_cold.get(sid, 0.0))
            utility.append(util_cold.get(sid, 0.0))

    xs = np.arange(len(labels))
    w  = 0.28

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)

    base_colors = [HOT if k == "hot" else COLD for k in kinds]

    # Background: original duty
    ax.bar(xs, totals, w * 2.6,
           color=[to_rgba(c, 0.08) for c in base_colors],
           edgecolor=[to_rgba(c, 0.35) for c in base_colors],
           linewidth=1.2, label="Original Duty", zorder=1)

    # Process HX coverage
    ax.bar(xs - w * 0.55, covered, w,
           color=to_rgba(HX, 0.7),
           edgecolor=HX, lw=0.8,
           label="Process HX", zorder=2)

    # Utility coverage
    util_colors = [
        to_rgba(STEAM, 0.7) if k == "cold" else to_rgba(CW, 0.7)
        for k in kinds
    ]
    ax.bar(xs + w * 0.55, utility, w,
           color=util_colors,
           edgecolor=[STEAM if k == "cold" else CW for k in kinds],
           lw=0.8, hatch="///",
           label="Utility (Steam / CW)", zorder=2)

    # Percentage labels
    for i, (cov, util, tot) in enumerate(zip(covered, utility, totals)):
        pct = 100 * (cov + util) / max(tot, 1)
        ax.text(xs[i], tot + max(totals) * 0.012,
                f"{pct:.0f}%",
                ha="center", va="bottom",
                fontsize=7.5, color=TEXT_DIM)

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10)
    for tick, kind in zip(ax.get_xticklabels(), kinds):
        tick.set_color(HOT if kind == "hot" else COLD)
        tick.set_fontweight("bold")

    ax.set_ylabel("Duty  (kW)", fontsize=10, color=TEXT)
    ax.set_title(title, fontsize=12, fontweight="bold", color=TEXT)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3, axis="y")
    ax.spines[:].set_color(BORDER)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4. T-H composite curves
# ---------------------------------------------------------------------------

def _build_curve(segments):
    """Build (H, T) composite curve points swept from high T to low T."""
    if not segments:
        return []
    temps = set()
    for T_hi, T_lo, _ in segments:
        temps.add(T_hi)
        temps.add(T_lo)
    T_sorted = sorted(temps, reverse=True)
    pts, H = [], 0.0
    pts.append((H, T_sorted[0]))
    for i in range(len(T_sorted) - 1):
        T_top, T_bot = T_sorted[i], T_sorted[i + 1]
        FCp_sum = sum(
            fcp for (th, tl, fcp) in segments
            if th >= T_top - 1e-9 and tl <= T_bot + 1e-9
        )
        H += FCp_sum * (T_top - T_bot)
        pts.append((H, T_bot))
    return pts  # (H, T), high T to low T


def _interp_T(pts_asc, H_q):
    """Interpolate T at H_q from list of (H, T) in ascending H order."""
    if not pts_asc:
        return None
    Hs = [p[0] for p in pts_asc]
    Ts = [p[1] for p in pts_asc]
    if H_q < Hs[0] or H_q > Hs[-1]:
        return None
    for k in range(len(pts_asc) - 1):
        if Hs[k] <= H_q <= Hs[k + 1]:
            dH = Hs[k + 1] - Hs[k]
            if dH < 1e-9:
                return Ts[k]
            return Ts[k] + (H_q - Hs[k]) / dH * (Ts[k + 1] - Ts[k])
    return None


def plot_composite_curves(
    goal_state,
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float = 10.0,
    title: str = "Temperature-Enthalpy Composite Curves",
) -> plt.Figure:

    hot_segs  = [(h.T_in,  h.T_out, h.FCp) for h in hot_streams.values()]
    cold_segs = [(c.T_out, c.T_in,  c.FCp) for c in cold_streams.values()]

    hot_pts  = _build_curve(hot_segs)
    cold_pts = _build_curve(cold_segs)

    if not hot_pts or not cold_pts:
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.text(0.5, 0.5, "Insufficient data",
                ha="center", va="center", transform=ax.transAxes)
        return fig

    # Ascending H order for plotting and interpolation
    hot_asc  = list(reversed(hot_pts))
    cold_asc = list(reversed(cold_pts))

    hot_total  = hot_pts[-1][0]
    cold_total = cold_pts[-1][0]

    # Bisect for horizontal shift so min gap = delta_T_min
    def min_gap(shift):
        H_hot  = [p[0] for p in hot_asc]
        H_cold = [p[0] + shift for p in cold_asc]
        H_ovlp = sorted(set(H_hot + H_cold))
        H_lo   = max(min(H_hot), min(H_cold))
        H_hi   = min(max(H_hot), max(H_cold))
        if H_hi <= H_lo:
            return float("inf")
        gaps = []
        cold_shifted = [(p[0] + shift, p[1]) for p in cold_asc]
        for H in H_ovlp:
            if not (H_lo - 1e-6 <= H <= H_hi + 1e-6):
                continue
            Th = _interp_T(hot_asc,      H)
            Tc = _interp_T(cold_shifted, H)
            if Th is not None and Tc is not None:
                gaps.append(Th - Tc)
        return min(gaps) if gaps else float("inf")

    lo, hi = 0.0, hot_total + cold_total
    for _ in range(70):
        mid = (lo + hi) / 2.0
        if min_gap(mid) < delta_T_min:
            lo = mid
        else:
            hi = mid
    shift = (lo + hi) / 2.0

    QHmin = max(0.0, cold_total + shift - hot_total)
    QCmin = max(0.0, hot_total - cold_total - shift)

    cold_shifted_asc = [(p[0] + shift, p[1]) for p in cold_asc]

    # Find pinch
    pinch_H = pinch_T = 0.0
    mg = float("inf")
    all_H = sorted(set(
        [p[0] for p in hot_asc] +
        [p[0] for p in cold_shifted_asc]
    ))
    H_ov_lo = max(hot_asc[0][0],  cold_shifted_asc[0][0])
    H_ov_hi = min(hot_asc[-1][0], cold_shifted_asc[-1][0])
    for H in all_H:
        if not (H_ov_lo - 1e-6 <= H <= H_ov_hi + 1e-6):
            continue
        Th = _interp_T(hot_asc,          H)
        Tc = _interp_T(cold_shifted_asc, H)
        if Th is not None and Tc is not None and (Th - Tc) < mg:
            mg, pinch_H, pinch_T = Th - Tc, H, Th

    # --- Plot ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)

    hot_H  = [p[0] for p in hot_asc]
    hot_T  = [p[1] for p in hot_asc]
    cold_H = [p[0] for p in cold_shifted_asc]
    cold_T = [p[1] for p in cold_shifted_asc]

    # Shading under curves
    ax.fill_between(hot_H,  hot_T,  alpha=0.08, color=HOT,  zorder=1)
    ax.fill_between(cold_H, cold_T, alpha=0.08, color=COLD, zorder=1)

    # QHmin region: steam needed on the left
    if QHmin > 0.5:
        Tc0 = cold_shifted_asc[0][1]
        ax.fill_betweenx(
            [0, Tc0],
            [0, 0],
            [cold_shifted_asc[0][0], cold_shifted_asc[0][0]],
            color=STEAM, alpha=0.20, zorder=1,
        )
        ax.annotate(
            f"QHmin\n{QHmin:.1f} kW",
            xy=(cold_shifted_asc[0][0] / 2, Tc0 * 0.55),
            fontsize=8.5, color=STEAM, ha="center", fontweight="bold",
        )

    # QCmin region: cooling needed on the right
    if QCmin > 0.5:
        Th_end = hot_asc[-1][1]
        H_end  = hot_asc[-1][0]
        ax.fill_betweenx(
            [0, Th_end],
            [H_end, H_end],
            [H_end + QCmin, H_end + QCmin],
            color=CW, alpha=0.20, zorder=1,
        )
        ax.annotate(
            f"QCmin\n{QCmin:.1f} kW",
            xy=(H_end + QCmin / 2, Th_end * 0.55),
            fontsize=8.5, color=CW, ha="center", fontweight="bold",
        )

    # Main curves
    ax.plot(hot_H,  hot_T,  color=HOT,  lw=2.8, label="Hot Composite",  zorder=4)
    ax.plot(cold_H, cold_T, color=COLD, lw=2.8, label="Cold Composite", zorder=4)

    # Pinch marker
    ax.axvline(x=pinch_H, color=ACCENT, lw=1.4, ls="--", alpha=0.8, zorder=3)
    ax.scatter([pinch_H], [pinch_T], color=ACCENT, s=80, zorder=5)
    ax.annotate(
        f"Pinch  {pinch_T:.1f}°C",
        xy=(pinch_H, pinch_T),
        xytext=(pinch_H + (hot_asc[-1][0] - hot_asc[0][0]) * 0.04, pinch_T + 8),
        fontsize=8.5, color=ACCENT, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.2),
    )

    # Info box
    info = (
        f"dTmin  =  {delta_T_min:.0f} °C\n"
        f"QHmin  =  {QHmin:.1f} kW\n"
        f"QCmin  =  {QCmin:.1f} kW"
    )
    ax.text(0.97, 0.05, info,
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, color=TEXT,
            bbox=dict(boxstyle="round,pad=0.5", fc=SURFACE,
                      ec=BORDER, alpha=0.95))

    ax.set_xlabel("Enthalpy  H  (kW)", fontsize=11, color=TEXT)
    ax.set_ylabel("Temperature  T  (°C)", fontsize=11, color=TEXT)
    ax.set_title(title, fontsize=12, fontweight="bold", color=TEXT)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.spines[:].set_color(BORDER)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def visualize_all(
    result:       "AStarResult",
    hot_streams:  Dict[str, "HotStream"],
    cold_streams: Dict[str, "ColdStream"],
    delta_T_min:  float,
) -> None:
    if not result.success:
        print("  No solution to visualize.")
        return

    print("\n  Generating visualizations ...")
    matplotlib.use("TkAgg")

    fig1 = plot_matrix_network(result.goal_state, hot_streams, cold_streams)
    fig2 = plot_search_progress(result.path)
    fig3 = plot_energy_before_after(result.goal_state, hot_streams, cold_streams)
    fig4 = plot_composite_curves(result.goal_state, hot_streams, cold_streams, delta_T_min)

    plt.show()
    print("  Plots displayed. Close windows to exit.")
