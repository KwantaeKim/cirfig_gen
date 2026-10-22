#!/usr/bin/env python3
"""
sample_hold.py — Sample-and-hold waveforms and the zero-order-hold sinc response (lecture 07)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Four figures, chosen with --fig:
  sh       4x3 in, no axes. Sine input as a 1 pt black dotted line, sample-and-hold
           output as 1.5 pt segments: green #005000 while holding, navy #0000C8 at the
           jump on each rising clock edge. Gray 0.5 pt dotted stems mark the sampling
           instants. The clock is a 1.2 pt navy square wave drawn below the signal.
           A 1.5 pt arrow along y = 0 is the time axis.
  th       Same frame. Track-and-hold output as a 1.5 pt black line (follows the input
           while the clock is high, holds while low) over the sample-and-hold output as a
           0.5 pt navy line, which updates on the falling edge.
  sinc     4x3 in, linear frequency 0 to 10 f_s: |H_ZOH| = |sinc(f/f_s)| in dB as a 1.5 pt
           black line, gray dotted guides at f_s/2 and at the -3.92 dB droop, each named
           in a rounded white box with 8 pt text. Ticks every f_s, no tick marks.
  sinc_log 3x3 in, the same on a log axis from 0.1 f_s to 10 f_s.

Usage
-----
    python sample_hold.py --fig sh
    python sample_hold.py --fig sinc_log --out fig.png

Dependencies: numpy, matplotlib
"""
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter

# ---------------------------------------------------------------- palette ---
NAVY  = "#0000C8"
GREEN = "#005000"
BLACK = "black"
GRAY  = "gray"


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


def style_axis(ax, xlabel, ylabel, eng_x=True, places=0):
    """Labels + thin grid + engineering tick formatter, tick marks hidden."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", linewidth=0.3)
    ax.tick_params(axis="both", which="both", length=0)
    if eng_x:
        ax.xaxis.set_major_formatter(EngFormatter(places=places))


# ------------------------------------------------------- waveform helpers ---
def _clock(t, Ts, duty=0.5):
    return ((t % Ts) < (Ts * duty))


def _waveform_frame(ax, t, yc, clk, clk_height=0.2, clk_offset=-1.4):
    """Shared frame of the waveform drawings: clock, time arrow, no axes."""
    ax.step(t, clk.astype(float) * clk_height + clk_offset, where="post",
            color=NAVY, linewidth=1.2)
    ax.annotate("", xy=(t[-1] + 0.3, 0), xytext=(t[0] - 0.2, 0),
                arrowprops=dict(arrowstyle="->", linewidth=1.5, color=BLACK),
                annotation_clip=False)
    ax.set_ylim(-1.7, 1.2)
    ax.axis("off")


# ------------------------------------------------------------------- plot ---
def fig_sh(Ts=0.43):
    """Sample-and-hold: sample on the rising edge, hold for one period."""
    t = np.linspace(0, 2 * np.pi, 4000)
    yc = np.sin(t)
    clk = _clock(t, Ts)
    edges = np.where(np.diff(clk.astype(int)) == 1)[0] + 1
    t_edges, y_edges = t[edges], np.sin(t[edges])

    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    ax.vlines(t_edges, 0, y_edges, linestyles="dotted", color=GRAY, linewidth=0.5)
    ax.plot(t, yc, linestyle=":", color=BLACK, linewidth=1)

    t_start, val = t[0], yc[0]
    for t_edge in t_edges:
        ax.plot([t_start, t_edge], [val, val], color=GREEN, linewidth=1.5)     # hold
        new_val = np.sin(t_edge)
        ax.plot([t_edge, t_edge], [val, new_val], color=NAVY, linewidth=1.5)   # sample
        t_start, val = t_edge, new_val
    ax.plot([t_start, t[-1]], [val, val], color=GREEN, linewidth=1.5)

    _waveform_frame(ax, t, yc, clk)
    fig.tight_layout(pad=0)
    return fig


def fig_th(Ts=0.45):
    """Track-and-hold (track while clock high) over sample-and-hold (falling edge)."""
    t = np.linspace(0, 2 * np.pi, 4000)
    yc = np.sin(t)
    clk = _clock(t, Ts)

    y_th = np.zeros_like(t)
    y_sh = np.zeros_like(t)
    last_th, last_sh = 0.0, 0.0
    for i in range(len(t)):
        if clk[i]:
            y_th[i] = last_th = yc[i]
        else:
            y_th[i] = last_th
        if i > 0 and not clk[i] and clk[i - 1]:
            last_sh = yc[i]
        y_sh[i] = last_sh
    y_track = np.where(clk, y_th, np.nan)
    y_hold = np.where(~clk, y_th, np.nan)

    edges = np.where(np.diff(clk.astype(int)) != 0)[0] + 1
    t_edges, y_edges = t[edges], np.sin(t[edges])

    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    ax.vlines(t_edges, 0, y_edges, linestyles="dotted", color=GRAY, linewidth=0.5, zorder=1)
    ax.plot(t, yc, linestyle=":", color=BLACK, linewidth=1, zorder=1)
    ax.plot(t, y_sh, color=NAVY, linestyle="-", linewidth=0.5, zorder=2, label="Sample-and-hold")
    ax.plot(t, y_track, color=BLACK, linewidth=1.5, zorder=3, label="Track-and-hold")
    ax.plot(t, y_hold, color=BLACK, linewidth=1.5, zorder=3)

    _waveform_frame(ax, t, yc, clk)
    fig.tight_layout(pad=0)
    return fig


def _sinc_db(f, fs=1.0):
    """|H_ZOH(f)| in dB. The phase term exp(-j pi f/fs) has unit magnitude."""
    return 20 * np.log10(np.abs(np.sinc(f / fs)))


def _sinc_annotations(ax, fs=1.0):
    droop = _sinc_db(0.5 * fs, fs)          # -3.92 dB at f_s/2
    box = dict(boxstyle="round", fc="w", ec="k", lw=1)
    ax.axvline(0.5 * fs, color=GRAY, linestyle=":", linewidth=0.8)
    ax.annotate(r"$f=f_{s}/2$", (0.5 * fs, 0.1), fontsize=8, bbox=box)
    ax.axhline(droop, color=GRAY, linestyle=":", linewidth=0.8)
    ax.annotate(f"{droop:.2f} dB", (1, -4), fontsize=8, bbox=box)


def fig_sinc(fs=1.0, fmax=10.0):
    f = np.linspace(0, fmax, 10000)
    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
    ax.plot(f, _sinc_db(f, fs), color=BLACK, linewidth=1.5)
    _sinc_annotations(ax, fs)
    style_axis(ax, r"Frequency ($f/f_{s}$)", "Magnitude (dB)")
    ax.set_xlim(0, fmax)
    ax.set_ylim(-30, 1)
    ax.set_xticks(np.arange(0, fmax + 1, 1))
    fig.tight_layout()
    return fig


def fig_sinc_log(fs=1.0, fmin=0.1, fmax=10.0):
    f = np.logspace(np.log10(fmin), np.log10(fmax), 10000)
    fig, ax = plt.subplots(figsize=(3, 3), dpi=300)
    ax.semilogx(f, _sinc_db(f, fs), color=BLACK, linewidth=1.5)
    _sinc_annotations(ax, fs)
    style_axis(ax, r"Frequency ($f/f_{s}$)", "Magnitude (dB)")
    ax.set_xlim(fmin, fmax)
    ax.set_ylim(-30, 1)
    fig.tight_layout()
    return fig


FIGS = {"sh": fig_sh, "th": fig_th, "sinc": fig_sinc, "sinc_log": fig_sinc_log}


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fig", choices=list(FIGS), default="sh")
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
