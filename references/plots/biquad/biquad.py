#!/usr/bin/env python3
"""
biquad.py — Second-order filter responses (lecture 02)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Seven figures, chosen with --fig. All have 12 pt axis labels and a 0.3 pt grid on
major and minor ticks unless stated.
  q        4x3 in. |H| of a 2nd-order low-pass at f0 = 300 Hz for Q = 0.5, 0.707 and 2 as
           1.5 pt lines in light gray dotted, gray dashed and black solid. Dashed 0.8 pt
           guide at f0 with its value in a rounded white box (8 pt). Legend lower left.
  step     4x3 in. Step response of the same three filters over 15 ms, time axis in
           engineering units with one decimal. Legend upper right.
  family   4x3 in. 6th-order low-pass family at f0 = 300 Hz: three cascaded Q = 0.5 biquads
           (black dotted), Bessel (red), Butterworth (black), Chebyshev 1 dB (navy), all 1 pt.
           Chebyshev peak normalised to 0 dB. Solid 0.5 pt major grid, dotted 0.3 pt minor
           grid, no tick marks, 8 pt legend.
  lpf, hpf, bpf, notch
           6x4 in. One biquad response at f0 = 316.2 Hz (the geometric centre of the 10 Hz
           to 10 kHz window), Q = 0.5, as a 2 pt blue line, no legend, no annotation.

Usage
-----
    python biquad.py --fig q
    python biquad.py --fig notch --out fig.png

Dependencies: numpy, scipy, matplotlib
"""
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
from scipy import signal

# ---------------------------------------------------------------- palette ---
NAVY  = "#0000C8"
RED   = "#C00000"
BLACK = "black"
GRAY  = "gray"
LIGHT = "#B0B0B0"
BOX   = dict(boxstyle="round", fc="w", ec="k", lw=1)

Q_CASES = [
    dict(label="Q=0.5",                Q=0.5,   color=LIGHT, style=":"),
    dict(label="Q=0.707 (Butterworth)", Q=0.707, color=GRAY,  style="--"),
    dict(label="Q=2",                  Q=2,     color=BLACK, style="-"),
]


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


def style_axis(ax, xlabel, ylabel, fontsize=12, eng_x=True, places=0, unit=""):
    """12 pt labels + thin grid + engineering tick formatter on x."""
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.grid(True, which="both", linewidth=0.3)
    if eng_x:
        ax.xaxis.set_major_formatter(EngFormatter(unit=unit, places=places))


def legend(ax, loc, fontsize=10):
    ax.legend(loc=loc, framealpha=1, edgecolor=BLACK, fontsize=fontsize)


# ------------------------------------------------------------------- data ---
def lpf2(w0, Q):
    """H(s) = w0^2 / (s^2 + (w0/Q) s + w0^2)"""
    return signal.TransferFunction([w0**2], [1, w0 / Q, w0**2])


def biquad(kind, w0, Q):
    den = [1, w0 / Q, w0**2]
    num = {"lpf": [w0**2], "hpf": [1, 0, 0], "bpf": [w0 / Q, 0], "notch": [1, 0, w0**2]}[kind]
    return signal.TransferFunction(num, den)


def mag_db(system, f):
    _, mag, _ = signal.bode(system, w=2 * np.pi * f)
    return mag


# ------------------------------------------------------------------- plot ---
def fig_q(f0=300):
    f = np.logspace(0, 5, 2000)
    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    ax.axvline(f0, color="k", linestyle="dashed", linewidth=0.8)
    ax.annotate(f"f$_0$ = {f0} Hz", (f0, 15), fontsize=8, bbox=BOX)
    for c in Q_CASES:
        ax.semilogx(f, mag_db(lpf2(2 * np.pi * f0, c["Q"]), f), label=c["label"],
                    color=c["color"], linestyle=c["style"], linewidth=1.5)
    ax.set_xlim(10, 10000)
    ax.set_ylim(-50, 20)
    style_axis(ax, "Frequency [Hz]", "Magnitude [dB]")
    legend(ax, "lower left")
    fig.tight_layout()
    return fig


def fig_step(f0=300, tmax=0.015):
    t = np.linspace(0, tmax, 1000)
    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    for c in Q_CASES:
        tout, yout = signal.step(lpf2(2 * np.pi * f0, c["Q"]), T=t)
        ax.plot(tout, yout, label=c["label"], color=c["color"],
                linestyle=c["style"], linewidth=1.5)
    ax.set_xlim(0, tmax)
    ax.set_ylim(0, 2.0)
    style_axis(ax, "Time [s]", "Amplitude [V]", places=1, unit="s")
    legend(ax, "upper right")
    fig.tight_layout()
    return fig


def _biquad_stages(poles):
    """Pair conjugate poles into (wn, Q) biquad stages, lowest |imag| first."""
    poles = sorted(poles, key=lambda p: abs(p.imag))
    return [(abs(p), abs(p) / (2 * abs(p.real))) for p in poles[::2]]


def fig_family(f0=300, N=6):
    w0 = 2 * np.pi * f0
    f = np.logspace(1, 4, 2000)
    w = 2 * np.pi * f
    cases = [
        ("Cascaded Q=0.5", [(w0, 0.5)] * (N // 2),                                BLACK, ":"),
        ("Bessel",         _biquad_stages(signal.bessel(N, w0, output="zpk", analog=True, norm="mag")[1]), RED,   "-"),
        ("Butterworth",    _biquad_stages(signal.butter(N, w0, output="zpk", analog=True)[1]),             BLACK, "-"),
        ("Chebyshev 1dB",  _biquad_stages(signal.cheby1(N, 1, w0, output="zpk", analog=True)[1]),          NAVY,  "-"),
    ]
    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    ax.annotate(f"f$_0$ = {f0} Hz", (f0, 5), fontsize=8, bbox=BOX)
    for label, stages, color, style in cases:
        H = np.ones_like(w, dtype=complex)
        for wn, Q in stages:
            H *= signal.freqs([wn**2], [1, wn / Q, wn**2], worN=w)[1]
        if label.startswith("Chebyshev"):
            H /= max(np.max(np.abs(H)), 1.0)       # peak to 0 dB
        ax.semilogx(f, 20 * np.log10(np.abs(H)), label=label,
                    color=color, linestyle=style, linewidth=1)
    ax.set_xlim(10, 10000)
    ax.set_ylim(-70, 10)
    ax.set_xlabel("Frequency [Hz]", fontsize=12)
    ax.set_ylabel("Magnitude [dB]", fontsize=12)
    ax.tick_params(axis="both", which="both", length=0)
    ax.xaxis.set_major_formatter(EngFormatter(places=0))
    ax.grid(which="major", linestyle="-", linewidth=0.5, alpha=0.7)
    ax.grid(which="minor", linestyle=":", linewidth=0.3, alpha=0.5)
    legend(ax, "lower left", fontsize=8)
    fig.tight_layout()
    return fig


def fig_biquad(kind, f0=316.2, Q=0.5):
    f = np.logspace(0, 5, 2000)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
    ax.semilogx(f, mag_db(biquad(kind, 2 * np.pi * f0, Q), f), "b", linewidth=2)
    ax.set_xlim(10, 10000)
    ax.set_ylim(-50, 5)
    style_axis(ax, "Frequency [Hz]", "Magnitude [dB]")
    fig.tight_layout()
    return fig


FIGS = {
    "q": fig_q, "step": fig_step, "family": fig_family,
    **{k: (lambda k=k: fig_biquad(k)) for k in ("lpf", "hpf", "bpf", "notch")},
}


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fig", choices=list(FIGS), default="q")
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
