#!/usr/bin/env python3
"""
SQNR.py — Graph-styling example

Reproduces the two-panel figure of the notebook (transient waveform on top,
FFT magnitude below) using the same visual style:
  * Arial Narrow, bold labels (falls back to sans-serif if the font is missing)
  * navy / red / black line palette, thin 0.7 pt lines
  * engineering-unit tick labels (µ, m, k, ...) via EngFormatter
  * light 0.3 pt grid, compact 4x3 in figure at 300 dpi

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Usage
-----
    python SQNR.py                 # reads the four TSVs in CWD
    python SQNR.py --demo          # synthetic data, no files needed
    python SQNR.py --out fig.png   # save instead of show
    python SQNR.py --tran1 a.tsv --tran2 b.tsv --fft1 c.tsv --fft2 d.tsv

Required data (tab-separated, no header, numeric only)
------------------------------------------------------
  tran1 (SQNR_tran.tsv) : col0 = time [s], col1 = signal 1 amplitude [V]
  tran2 (SNDR2_tran.tsv): col0 = time [s], col2 = signal 2 amplitude [V]
                          (col1 exists but is not plotted; same as notebook)
  fft1  (SQNR_fft.tsv)  : col0 = frequency [Hz], col1 = magnitude [dB]
  fft2  (SNDR2_fft.tsv) : col0 = frequency [Hz], col1 = magnitude [dB]

Dependencies: numpy, pandas, matplotlib
"""
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter

# ---------------------------------------------------------------- palette ---
NAVY  = "#1A2258"
RED   = "#C80000"
BLACK = "black"


# ---------------------------------------------------------------- styling ---
def apply_style(font="Arial Narrow"):
    """Global matplotlib look used across the lecture notebooks."""
    from matplotlib.font_manager import findfont, FontProperties
    try:
        # findfont raises/falls back silently; check the resolved file name
        resolved = findfont(FontProperties(family=font), fallback_to_default=False)
        mpl.rcParams["font.family"] = font if resolved else "sans-serif"
    except Exception:
        mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams.update({
        "font.weight":      "bold",
        "axes.labelweight": "bold",
        "mathtext.default": "regular",
    })


def style_axis(ax, xlabel, ylabel, eng_x=True, eng_y=True, places=0):
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


def demo_data(fs=1e6, n=1024, fin=48.8e3, bits=8):
    """Synthetic replacement for the Spectre/Cadence exports: an N-bit
    quantised sine (signal 1) and a slightly distorted one (signal 2)."""
    t = np.arange(n) / fs
    x = 0.5 + 0.45 * np.sin(2 * np.pi * fin * t)
    lsb = 1.0 / 2**bits
    q1 = np.round(x / lsb) * lsb
    q2 = np.round((x + 0.02 * (x - 0.5) ** 2) / lsb) * lsb      # add 2nd-order distortion

    def spectrum(sig):
        w = np.hanning(n)
        X = np.abs(np.fft.rfft((sig - sig.mean()) * w))
        X = 20 * np.log10(X / X.max() + 1e-12)
        f = np.fft.rfftfreq(n, 1 / fs)
        return pd.DataFrame({0: f, 1: X})

    tran1 = pd.DataFrame({0: t, 1: q1, 2: q1})
    tran2 = pd.DataFrame({0: t, 1: q2, 2: q2})
    return tran1, tran2, spectrum(q1), spectrum(q2)


# ------------------------------------------------------------------- plot ---
def make_figure(tran1, tran2, fft1, fft2, fmax=500e3, ylim_db=(-100, 5)):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 3), dpi=300)

    # Transient waveform
    ax1.plot(tran1[0], tran1[1], "-", color=NAVY, lw=0.7, label="Signal 1")
    ax1.plot(tran2[0], tran2[2], "-", color=RED,  lw=0.7, label="Signal 2")
    style_axis(ax1, "Time [s]", "Amplitude [V]")

    # FFT magnitude
    ax2.plot(fft1[0], fft1[1], "-", color=BLACK, lw=0.7)
    ax2.plot(fft2[0], fft2[1], "-", color=RED,   lw=0.7)
    style_axis(ax2, "Frequency [Hz]", "Magnitude [dB]", eng_y=False)
    ax2.set_xlim(0, fmax)
    ax2.set_ylim(*ylim_db)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tran1", default="SQNR_tran.tsv")
    p.add_argument("--tran2", default="SNDR2_tran.tsv")
    p.add_argument("--fft1",  default="SQNR_fft.tsv")
    p.add_argument("--fft2",  default="SNDR2_fft.tsv")
    p.add_argument("--demo", action="store_true",
                   help="use synthetic data instead of reading TSV files")
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()

    apply_style()

    files = [a.tran1, a.tran2, a.fft1, a.fft2]
    if a.demo or not all(os.path.exists(f) for f in files):
        if not a.demo:
            missing = [f for f in files if not os.path.exists(f)]
            print(f"[info] missing {missing} -> using synthetic demo data")
        data = demo_data()
    else:
        data = tuple(load_tsv(f) for f in files)

    fig = make_figure(*data)
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
