#!/usr/bin/env python3
"""
pole_zero.py — s-plane and z-plane pole-zero plots with region of convergence (lecture 08)

One of the reference plots in references/plots/. The plot style and the PowerPoint
sizing rules live in AGENTS.md (section Plots).

Both plots assume a causal system:
  * s-plane, 4x3 in : ROC is the half plane right of the rightmost pole
  * z-plane, 4x4 in : ROC is the annulus outside the outermost pole, unit circle drawn
                      as a 1.5 pt black circle, ROC boundary as a dashed blue circle
Shared conventions:
  * axes through the origin as 1 pt black lines, no tick labels, no tick marks
  * poles: red "x" markers (s=100, 2 pt stroke), zeros: white circles with a blue edge
  * ROC shaded light blue (#d6eaff at 50 %)
  * axis labels at 14 pt, legend at 10 pt in a black-edged box, 0.3 pt gray grid

Usage
-----
    python pole_zero.py --plane s --poles=-1
    python pole_zero.py --plane s --poles=-1+2j,-1-2j      # complex pair, lecture 02
    python pole_zero.py --plane z --poles=0.5
    python pole_zero.py --plane z --poles=0.5+0.5j,0.5-0.5j --zeros=1 --out fig.png

Write --poles=... with the equals sign and separate values with commas, so that a
leading minus sign is not read as an option.

Dependencies: numpy, matplotlib
"""
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter

# ---------------------------------------------------------------- palette ---
RED   = "#C00000"
BLUE  = "b"
ROC   = "#D6EAFF"
ROC_EDGE = "#4472C4"
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


def _axes_and_markers(ax, poles, zeros, limit, xlabel, ylabel):
    """Origin axes, pole and zero markers, blank ticks, grid and legend."""
    ax.axhline(0, color=BLACK, linewidth=1, zorder=1)
    ax.axvline(0, color=BLACK, linewidth=1, zorder=1)
    if len(poles):
        ax.scatter(np.real(poles), np.imag(poles), s=100, marker="x",
                   color=RED, linewidth=2, label="Poles", zorder=3)
    if len(zeros):
        ax.scatter(np.real(zeros), np.imag(zeros), s=100, marker="o",
                   facecolors="white", edgecolors=BLUE, linewidth=2, label="Zeros", zorder=3)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.xaxis.set_major_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(NullFormatter())
    ax.grid(which="both", linewidth=0.3, zorder=0, color="gray", alpha=0.5)
    ax.tick_params(axis="both", which="both", length=0)
    ax.legend(loc="upper right", framealpha=1, edgecolor=BLACK, fontsize=10)


# ------------------------------------------------------------------- plot ---
def s_plane(poles, zeros):
    """ROC of a causal system: Re(s) > Re of the rightmost pole."""
    poles, zeros = np.asarray(poles, complex), np.asarray(zeros, complex)
    fig, ax = plt.subplots(figsize=(4, 3), dpi=300)

    pts = np.concatenate([poles, zeros])
    limit = max(np.max(np.abs(np.r_[pts.real, pts.imag])) * 1.5, 2) if len(pts) else 5

    if len(poles):
        sigma_max = np.max(poles.real)
        ax.axvspan(sigma_max, limit * 2, color=ROC, alpha=0.5, zorder=0, label="ROC")

    _axes_and_markers(ax, poles, zeros, limit, r"$\sigma$ (Real)", r"$j\omega$ (Imaginary)")
    fig.tight_layout()
    return fig


def z_plane(poles, zeros):
    """ROC of a causal system: |z| > radius of the outermost pole."""
    poles, zeros = np.asarray(poles, complex), np.asarray(zeros, complex)
    fig, ax = plt.subplots(figsize=(4, 4), dpi=300)
    ax.set_aspect("equal")

    pts = np.concatenate([poles, zeros])
    limit = max(np.max(np.abs(pts)) if len(pts) else 0, 1) * 1.8

    if len(poles):
        r = np.max(np.abs(poles))
        # shade everything, then mask the inside of the ROC radius with a white disc
        ax.fill_between(np.linspace(-limit * 2, limit * 2, 2), -limit * 2, limit * 2,
                        color=ROC, alpha=0.5, zorder=0, label="ROC")
        ax.add_patch(plt.Circle((0, 0), r, color="white", zorder=0))
        ax.add_patch(plt.Circle((0, 0), r, fill=False, linestyle="--",
                                linewidth=1, color=ROC_EDGE, zorder=2))

    ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, linestyle="-",
                            linewidth=1.5, color=BLACK, zorder=1))
    ax.annotate("Unit circle", xy=(0.707, 0.707), fontsize=10, color=BLACK,
                ha="left", va="bottom")

    _axes_and_markers(ax, poles, zeros, limit, r"Re$(z)$", r"Im$(z)$")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- main ---
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plane", choices=["s", "z"], default="z")
    p.add_argument("--poles", default=None,
                   help="comma-separated complex numbers, e.g. --poles=-1+2j,-1-2j "
                        "(default: s: -1, z: 0.5)")
    p.add_argument("--zeros", default="", help="comma-separated complex numbers")
    p.add_argument("--out", default=None,
                   help="output image path (png/pdf/svg); omit to open a window")
    a = p.parse_args()

    def parse(s):
        return [complex(v) for v in s.replace(" ", "").split(",") if v]
    a.poles = parse(a.poles) if a.poles is not None else ([-1] if a.plane == "s" else [0.5])
    a.zeros = parse(a.zeros)

    apply_style()
    fig = (s_plane if a.plane == "s" else z_plane)(a.poles, a.zeros)
    if a.out:
        fig.savefig(a.out, bbox_inches="tight")
        print(f"saved {a.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
