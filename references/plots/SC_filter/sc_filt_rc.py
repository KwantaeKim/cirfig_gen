#!/usr/bin/env python3
"""
sc_filt_rc.py — Switched-capacitor filter against its RC prototype (lecture 07)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots). sc_filt.py in this folder is the
lecture 08 version with two simulated curves.

Single panel, 3x3 in at 300 dpi, log frequency axis 1 kHz to 1 MHz:
  * black 1 pt dashed : ideal 1st-order RC low-pass, R = 1 MΩ
  * navy 1 pt solid   : simulated SC filter (column 2 of the TSV)
  * engineering ticks on frequency, 0.3 pt grid on major and minor ticks, no tick marks
Two bands:
  * --band hf : C = 1 pF,  f_c = 159 kHz, data sc_filt_hf.tsv
  * --band lf : C = 10 pF, f_c = 15.9 kHz, data sc_filt_lf.tsv

Usage
-----
    python sc_filt_rc.py --band hf
    python sc_filt_rc.py --band lf --out fig.png

Required data (tab-separated, no header, numeric only)
------------------------------------------------------
  sc_filt_hf.tsv, sc_filt_lf.tsv : col0 = frequency [Hz], col1 unused, col2 = magnitude [dB]

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
BANDS = {"hf": ("sc_filt_hf.tsv", 1e-12), "lf": ("sc_filt_lf.tsv", 10e-12)}

# ---------------------------------------------------------------- palette ---
NAVY  = "#0000C8"
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
    """Labels + thin grid + engineering tick formatters, tick marks hidden."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", lw=0.3)
    ax.tick_params(axis="both", which="both", length=0)
    if eng_x:
        ax.xaxis.set_major_formatter(EngFormatter(places=places))
    if eng_y:
        ax.yaxis.set_major_formatter(EngFormatter(places=places))


# ------------------------------------------------------------------- data ---
def rc_lpf(f, R, C):
    """|H| in dB of a 1st-order RC low-pass, H(s) = 1 / (1 + s/wc)."""
    wc = 1 / (R * C)
    _, H = signal.freqs([wc], [1, wc], worN=2 * np.pi * f)
    return 20 * np.log10(np.abs(H))


# ------------------------------------------------------------------- plot ---
def make_figure(sim, C, R=1e6, fmin=1e3, fmax=1e6, ylim_db=(-30, 5)):
    fig, ax = plt.subplots(figsize=(3, 3), dpi=300)
    f = np.logspace(np.log10(fmin), np.log10(fmax), 1000)

    ax.semilogx(f, rc_lpf(f, R, C), "--", color=BLACK, lw=1, label="RC LPF")
    ax.semilogx(sim[0], sim[2], "-", color=NAVY, lw=1, label="SC filter")

    style_axis(ax, "Frequency [Hz]", "Magnitude [dB]")
    ax.set_xlim(fmin, fmax)
    ax.set_ylim(*ylim_db)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--band", choices=list(BANDS), default="lf")
    p.add_argument("--data", default=None, help="override the TSV chosen by --band")
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()
    fname, C = BANDS[a.band]
    path = a.data or os.path.join(HERE, fname)

    apply_style()
    fig = make_figure(pd.read_csv(path, sep="\t", header=None), C)
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
