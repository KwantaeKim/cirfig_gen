#!/usr/bin/env python3
"""
stability.py — Loop-gain Bode plot and phase-margin comparison (lecture 03)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Two figures, chosen with --fig. Both are two stacked panels, 4x4 in at 300 dpi, 12 pt
axis labels, 0.3 pt grid on major and minor ticks, no tick marks.
  bode   Loop gain (dB) over loop phase (deg) of A·β·wp1·wp2 / (s + wp1)(s + wp2) with
         A·β = 100, fp1 = 100 Hz, fp2 = 2 kHz. Black 1.5 pt curves. 0.8 pt solid line at
         0 dB, dashed 0.8 pt guides at the gain crossover frequency, at -180° and at the
         phase there, so the gap between the last two is the phase margin. Phase ticks
         at -180, -90 and 0. Shared frequency axis.
  pm     Closed-loop magnitude (top, log frequency) and step response (bottom, 15 ms) of a
         second-order loop at f0 = 300 Hz with Q = 2 (small phase margin, dashed) and
         Q = 0.5 (large phase margin, solid), black 1.5 pt. 12 pt tick labels, 10 pt
         legends lower left and lower right.

Usage
-----
    python stability.py --fig bode
    python stability.py --fig pm --out fig.png

Dependencies: numpy, scipy, matplotlib
"""
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
from scipy import signal

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
    """12 pt labels + thin grid, tick marks hidden."""
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.grid(True, which="both", linewidth=0.3)
    ax.tick_params(axis="both", which="both", length=0)


def legend(ax, loc, fontsize=10):
    ax.legend(loc=loc, framealpha=1, edgecolor=BLACK, fontsize=fontsize)


# ------------------------------------------------------------------- plot ---
def fig_bode(A=1e4, beta=1e-2, fp1=100, fp2=2e3):
    wp1, wp2 = 2 * np.pi * fp1, 2 * np.pi * fp2
    loop = signal.TransferFunction([A * beta * wp1 * wp2], [1, wp1 + wp2, wp1 * wp2])
    f = np.logspace(0, 5, 2000)
    _, mag, phase = signal.bode(loop, w=2 * np.pi * f)

    i_gc = np.argmin(np.abs(mag))               # gain crossover, |T| = 0 dB
    f_gc, phase_gc = f[i_gc], phase[i_gc]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 4), dpi=300, sharex=True)
    ax1.semilogx(f, mag, color=BLACK, linewidth=1.5)
    ax1.axhline(0, color="k", linewidth=0.8)
    ax1.axvline(f_gc, linestyle="dashed", color="k", linewidth=0.8)
    ax1.set_ylim(-10, 20)
    style_axis(ax1, None, "Loop Gain [dB]")

    ax2.semilogx(f, phase, color=BLACK, linewidth=1.5)
    ax2.axhline(-180, linestyle="dashed", color="k", linewidth=0.8)
    ax2.axhline(phase_gc, linestyle="dashed", color="k", linewidth=0.8)
    ax2.axvline(f_gc, linestyle="dashed", color="k", linewidth=0.8)
    ax2.set_ylim(-210, 10)
    ax2.set_yticks([-180, -90, 0])
    style_axis(ax2, "Frequency [Hz]", "Loop Phase [deg]")
    ax2.xaxis.set_major_formatter(EngFormatter(places=0))

    fig.tight_layout()
    return fig


def fig_pm(f0=300, tmax=0.015):
    w0 = 2 * np.pi * f0
    cases = [
        # literal φ: with mathtext.default = regular the \phi command has no glyph
        (r"Small $φ_\mathrm{PM}$", 2,   "--"),
        (r"Large $φ_\mathrm{PM}$", 0.5, "-"),
    ]
    f = np.logspace(0, 5, 2000)
    t = np.linspace(0, tmax, 1000)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(4, 4), dpi=300)
    for label, Q, style in cases:
        sys = signal.TransferFunction([w0**2], [1, w0 / Q, w0**2])
        _, mag, _ = signal.bode(sys, w=2 * np.pi * f)
        ax1.semilogx(f, mag, label=label, color=BLACK, linestyle=style, linewidth=1.5)
        tout, yout = signal.step(sys, T=t)
        ax2.plot(tout, yout, label=label, color=BLACK, linestyle=style, linewidth=1.5)

    ax1.set(xlim=(10, 10000), ylim=(-50, 20))
    style_axis(ax1, "Frequency [Hz]", "Magnitude [dB]")
    ax1.xaxis.set_major_formatter(EngFormatter(places=0))
    legend(ax1, "lower left")

    ax2.set(xlim=(0, tmax), ylim=(0, 2.0))
    style_axis(ax2, "Time [s]", "Amplitude [V]")
    ax2.xaxis.set_major_formatter(EngFormatter(unit="s", places=1))
    legend(ax2, "lower right")

    for ax in (ax1, ax2):
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_fontsize(12)

    fig.tight_layout()
    return fig


FIGS = {"bode": fig_bode, "pm": fig_pm}


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fig", choices=list(FIGS), default="bode")
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()

    apply_style()
    fig = FIGS[a.fig]()
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
