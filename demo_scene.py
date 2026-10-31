"""One simulated listen, shown the way the device would see it.

Left: map of the real frogs (dots) and what the device reports (arrows, length =
range class). Right: bearing over time - each call lights up at its frog's bearing.

  python demo_scene.py [--seed 7] [--frogs 4] [--call my_call.wav]
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from coqui_sim import config as cfg
from coqui_sim.acoustics import frog_at, render_scene
from coqui_sim.doa import SrpPhat
from coqui_sim.pipeline import run_device
from coqui_sim.signals import load_call_wav, synth_coqui_call
from make_figures import GRID, INK, INK2, S1, S2, SURFACE  # palette + rcParams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--frogs", type=int, default=4)
    ap.add_argument("--noise", default="typical", choices=list(cfg.BACKGROUND_SPL))
    ap.add_argument("--call")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    wav = load_call_wav(a.call) if a.call else None
    call_fn = (lambda fr, r: wav) if wav is not None else (lambda fr, r: synth_coqui_call(r, pitch_scale=fr.pitch_scale))

    # Spread the frogs out so the demo shows separable frogs at mixed distances.
    base = rng.uniform(0, 360)
    azs = (base + np.sort(rng.choice(np.arange(0, 360, 40), a.frogs, replace=False))) % 360
    frogs = []
    for az, d in zip(azs, rng.choice([3, 6, 9, 13, 18], a.frogs)):
        fr = frog_at(az, d, rng.uniform(0.5, 3.0), rng)
        period = rng.uniform(*cfg.CALL_PERIOD_S)
        fr.call_times = list(np.arange(rng.uniform(0, period), 24.5, period))
        frogs.append((az, d, fr))

    x = render_scene([f for *_, f in frogs], 25.0, rng, call_fn, background_spl=cfg.BACKGROUND_SPL[a.noise])
    srp = SrpPhat()
    found, est = run_device(x, srp)

    fig = plt.figure(figsize=(12, 5.4))
    ax = fig.add_subplot(1, 2, 1)
    ax.set_aspect("equal")
    for r in (5, 15):
        ax.add_patch(plt.Circle((0, 0), r, fill=False, color=GRID, lw=1, ls="--"))
        ax.text(r * 0.72, r * 0.72, f"{r} m", fontsize=8.5, color=INK2)
    rlen = {"near": 4, "medium": 10, "far": 17}
    for fr in found:
        b = np.radians(fr["bearing"])
        L = rlen[fr["range_class"]]
        ax.annotate("", xy=(L * np.cos(b), L * np.sin(b)), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=S1, lw=2, mutation_scale=14))
        ax.text((L + 3.2) * np.cos(b), (L + 3.2) * np.sin(b),
                f"{fr['bearing']:.0f}°\n{fr['range_class']}", color=S1, fontsize=8.5,
                ha="center", va="center", zorder=5)
    for az, d, _ in frogs:
        ax.plot(d * np.cos(np.radians(az)), d * np.sin(np.radians(az)), "o", color=S2, ms=9,
                mec=SURFACE, mew=1.5, zorder=4)
    ax.plot(0, 0, "s", color=INK, ms=7)
    ax.set_xlim(-21, 21)
    ax.set_ylim(-21, 21)
    ax.set_xlabel("m")
    ax.set_ylabel("m")
    ax.plot([], [], "o", color=S2, ms=8, label="real frog")
    ax.plot([], [], "-", color=S1, lw=2, label="device: bearing + range class")
    ax.legend(loc="lower left", fontsize=9)
    ax.set_title(f"{len(frogs)} frogs present, device reports {len(found)}")

    ax = fig.add_subplot(1, 2, 2)
    for az, d, _ in frogs:
        ax.axhline(az, color=S2, lw=1, ls=(0, (2, 3)), zorder=1)
        ax.text(25.4, az, f"{az:.0f}° ({d:.0f} m)", va="center", fontsize=8.5, color=S2)
    ax.scatter([e["t"] for e in est], [e["bearing"] for e in est], s=14, color=S1,
               edgecolor=SURFACE, lw=0.5, zorder=3, label="bearing estimate")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 360)
    ax.set_yticks(range(0, 361, 90))
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Bearing (°)")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Each call is placed at its frog's bearing")
    fig.tight_layout()
    os.makedirs("figures", exist_ok=True)
    fig.savefig("figures/fig0_demo_scene.png", dpi=150)
    print("true:", [(round(az), round(d)) for az, d, _ in frogs])
    print("found:", [(round(fr["bearing"]), fr["range_class"], fr["n_calls"]) for fr in found])


if __name__ == "__main__":
    main()
