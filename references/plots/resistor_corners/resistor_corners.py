#!/usr/bin/env python3
"""
resistor_corners.py — Resistance against temperature at the slow, typical and fast corners

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Single panel, 4x3 in at 300 dpi, linear axes:
  * three 1.5 pt lines with a marker on every data point
    slow    navy  #0000C8  diamond, 5 pt
    typical black          square,  5 pt
    fast    red   #C80000  triangle, 6 pt
  * 12 pt axis labels, 0.3 pt grid, no tick marks, no legend (labels go on the slide)
  * y ticks every 2 kΩ

Usage
-----
    python resistor_corners.py                 # reads resistance_corners.tsv next to the script
    python resistor_corners.py --out fig.png   # save instead of show

Required data (tab-separated, with header)
------------------------------------------
  resistance_corners.tsv : Temperature_C, Slow_kOhm, Typical_kOhm, Fast_kOhm

Dependencies: numpy, pandas, matplotlib
"""
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette ---
NAVY  = "#0000C8"
RED   = "#C80000"
BLACK = "black"


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
    """Labels + thin grid, tick marks hidden (the grid lines mark the ticks)."""
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.grid(True, which="both", linewidth=0.3)
    ax.tick_params(axis="both", which="both", length=0)


# ------------------------------------------------------------------- plot ---
def make_figure(data):
    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    T = data["Temperature_C"]
    ax.plot(T, data["Slow_kOhm"],    marker="D", markersize=5, color=NAVY,  lw=1.5, label="Slow")
    ax.plot(T, data["Typical_kOhm"], marker="s", markersize=5, color=BLACK, lw=1.5, label="Typical")
    ax.plot(T, data["Fast_kOhm"],    marker="^", markersize=6, color=RED,   lw=1.5, label="Fast")

    ax.set(xlim=(-4, 104), ylim=(27, 41))
    ax.set_yticks(np.arange(27, 42, 2))
    style_axis(ax, "Temperature [°C]", r"Resistance [k$\Omega$]")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=os.path.join(HERE, "resistance_corners.tsv"))
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()

    apply_style()
    fig = make_figure(pd.read_csv(a.data, sep="\t"))
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
