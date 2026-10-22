#!/usr/bin/env python3
"""
phase_margin.py — Phase margin of a two-pole loop against its damping factor (lecture 02)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Single panel, 4x3 in at 300 dpi, linear axes, 12 pt labels, 0.3 pt grid, no legend:
  * black 2 pt      : exact  PM = atan( 2ζ / sqrt(-2ζ² + sqrt(4ζ⁴ + 1)) )
  * gray 1.5 pt dashed : the rule of thumb PM ≈ 100 ζ
  * black 0.8 pt dashed guides at ζ = 0.707 and at the PM there (65.5°), each named in a
    rounded white box with 8 pt text

Usage
-----
    python phase_margin.py
    python phase_margin.py --out fig.png

Dependencies: numpy, matplotlib
"""
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

BLACK = "black"
GRAY  = "gray"
BOX   = dict(boxstyle="round", fc="w", ec="k", lw=1)


# ---------------------------------------------------------------- styling ---
def apply_style(font="Arial Narrow"):
    """Global matplotlib look used across the lecture notebooks."""
    from matplotlib.font_manager import findfont, FontProperties
    try:
        resolved = findfont(FontProperties(family=font), fallback_to_default=False)
        mpl.rcParams["font.family"] = font if resolved else "sans-serif"
    except Exception:
        mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams.update({
        "font.weight":      "bold",
        "axes.labelweight": "bold",
        "mathtext.default": "regular",
    })


def style_axis(ax, xlabel, ylabel, fontsize=12):
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.grid(True, which="both", linewidth=0.3)


# ------------------------------------------------------------------- data ---
def pm_exact(zeta):
    """Phase margin in degrees of a loop with two poles, damping factor zeta."""
    return np.degrees(np.arctan(2 * zeta / np.sqrt(-2 * zeta**2 + np.sqrt(4 * zeta**4 + 1))))


# ------------------------------------------------------------------- plot ---
def make_figure(z_ref=0.707):
    zeta = np.linspace(0, 1.0, 1000)
    pm_ref = pm_exact(z_ref)                    # 65.5 deg at 0.707

    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    ax.axvline(z_ref, color="k", linestyle="dashed", linewidth=0.8)
    ax.axhline(pm_ref, color="k", linestyle="dashed", linewidth=0.8)
    ax.annotate(r"$\zeta$ = 0.707 (Q=0.707)", (z_ref, 5), fontsize=8, bbox=BOX)
    ax.annotate(f"PM $\\approx$ {pm_ref:.1f}°", (0.1, pm_ref), fontsize=8, bbox=BOX)

    ax.plot(zeta, 100 * zeta, label=r"Approx ($100\cdot\zeta$)",
            color=GRAY, linestyle="--", linewidth=1.5)
    ax.plot(zeta, pm_exact(zeta), label="Exact", color=BLACK, linestyle="-", linewidth=2)

    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 90)
    style_axis(ax, r"Damping Factor ($\zeta$)", "Phase Margin [deg]")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()

    apply_style()
    fig = make_figure()
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
