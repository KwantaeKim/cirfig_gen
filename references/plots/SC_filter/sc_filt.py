#!/usr/bin/env python3
"""
sc_filt.py — Switched-capacitor filter frequency response (lecture 08)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Single panel, 3x3 in at 300 dpi, log frequency axis:
  * black 1 pt line      : ideal 1st-order RC low-pass (R = 1 MΩ, C = 10 pF)
  * navy 0.7 pt solid    : simulated SC filter, eq2.tsv
  * red 0.5 pt dashed    : simulated SC filter, eq1.tsv
  * engineering ticks on frequency, 0.3 pt grid on major and minor ticks

Usage
-----
    python sc_filt.py                  # reads eq1.tsv and eq2.tsv next to the script
    python sc_filt.py --out fig.png    # save instead of show
    python sc_filt.py --eq1 a.tsv --eq2 b.tsv

Required data (tab-separated, no header, numeric only)
------------------------------------------------------
  eq1.tsv, eq2.tsv : col0 = frequency [Hz], col1 = magnitude [dB]

Dependencies: numpy, pandas, scipy, matplotlib
"""
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
from scipy import signal

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


def style_axis(ax, xlabel, ylabel, eng_x=True, eng_y=False, places=0):
    """Labels + thin grid + engineering tick formatters on one Axes."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", lw=0.3)
    if eng_x:
        ax.xaxis.set_major_formatter(EngFormatter(places=places))
    if eng_y:
        ax.yaxis.set_major_formatter(EngFormatter(places=places))


# ------------------------------------------------------------------- data ---
def load_tsv(path):
    return pd.read_csv(path, sep="\t", header=None)


def rc_lpf(f, R=1e6, C=10e-12):
    """|H| in dB of a 1st-order RC low-pass, cut-off 1/(2*pi*R*C) = 15.9 kHz."""
    wc = 1 / (R * C)
    _, H = signal.freqs([1], [1 / wc, 1], worN=2 * np.pi * f)
    return 20 * np.log10(np.abs(H))


# ------------------------------------------------------------------- plot ---
def make_figure(eq1, eq2, fmin=1e3, fmax=10e6, ylim_db=(-40, 5)):
    fig, ax = plt.subplots(figsize=(3, 3), dpi=300)
    f = np.logspace(np.log10(fmin), np.log10(fmax), 1000)

    ax.semilogx(f, rc_lpf(f), "-", color=BLACK, lw=1, label="RC LPF")
    ax.semilogx(eq2[0], eq2[1], "-",  color=NAVY, lw=0.7, label="SC filter")
    ax.semilogx(eq1[0], eq1[1], "--", color=RED,  lw=0.5, label="SC filter")

    style_axis(ax, "Frequency [Hz]", "Magnitude [dB]")
    ax.set_xlim(fmin, fmax)
    ax.set_ylim(*ylim_db)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--eq1", default=os.path.join(HERE, "eq1.tsv"))
    p.add_argument("--eq2", default=os.path.join(HERE, "eq2.tsv"))
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()

    apply_style()
    fig = make_figure(load_tsv(a.eq1), load_tsv(a.eq2))
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
