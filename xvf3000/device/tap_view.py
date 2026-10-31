"""Tap picture: tap next to a mic hole and see which microphone heard it loudest.

A window shows the 4 microphones where the code thinks they are. Just tap next to one
mic hole (no keys to press): the script spots the tap by itself, lights up the mic that
heard it loudest, and keeps it lit until the next tap. Tap the holes going round the
board; after 4 different mics it says whether they go round in order, which the
direction finding needs. Close the window or press Ctrl+C to stop.

  .venv/bin/python xvf3000/device/tap_view.py
  .venv/bin/python xvf3000/device/tap_view.py --demo     # pretend taps, no board needed
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

from common import FS, stream_blocks
from coqui_sim import config as cfg
from coqui_sim.xvf_format import RAW_CHANNELS
from tap_test import goes_round

BLOCK = 800            # 0.05 s of audio per update
TAP_DB = 15            # a tap is at least this much louder than the room's background
GAP_BLOCKS = 8         # after a tap, wait 0.4 s before listening for the next one
NAMES = [f"mic {m}\n(channel {c + 1})" for m, c in enumerate(RAW_CHANNELS)]
GREY, RED = "#9a9a9a", "#e8452c"


def peak_db(x):
    """Loudest sample on each raw mic channel of a block, in dBFS (0 = loudest possible)."""
    raw = x[:, RAW_CHANNELS]
    return 20 * np.log10(np.abs(raw - raw.mean(axis=0)).max(axis=0) + 1e-9)


def demo_blocks():
    """Pretend audio: quiet noise, and a tap next to mic 0, 1, 2, 3, 0, ... every second."""
    rng = np.random.default_rng(1)
    i = 0
    while True:
        x = rng.normal(0, 0.001, (BLOCK, 6))
        if i % 20 == 10:
            gains = np.full(4, 0.01)
            gains[(i // 20) % 4] = 0.08
            x[100:140, RAW_CHANNELS] += gains * rng.normal(0, 1, (40, 1))
        yield x
        i += 1


def make_window():
    """Draw the board and its 4 mics; return the parts that change."""
    fig, ax = plt.subplots(figsize=(7, 7.5))
    fig.subplots_adjust(0, 0, 1, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-80, 80)
    ax.set_ylim(-95, 92)
    ax.add_patch(Circle((0, 0), 48, color="#e6e6e6", zorder=0))          # the board
    circles, labels = [], []
    for (x, y, _), name in zip(cfg.MIC_POS * 1000, NAMES):              # metres -> mm
        circles.append(ax.add_patch(Circle((x, y), 9, color=GREY)))
        labels.append(ax.text(1.75 * x, 1.75 * y, name, ha="center", va="center", fontsize=11))
    title = ax.text(0, 84, "Tap next to a mic hole", ha="center", fontsize=17, weight="bold")
    footer = ax.text(0, -84, "", ha="center", va="center", fontsize=12)
    return fig, circles, labels, title, footer


def add_tap(taps, mic):
    """Remember the order of up to 4 different mics; a 5th tap starts again."""
    if len(taps) == 4:
        taps.clear()
    if mic not in taps:
        taps.append(mic)


def sequence_text(taps):
    s = "Taps: " + "  →  ".join(f"mic {m}" for m in taps)
    if len(taps) < 4:
        return s + "\n(keep going round the board)"
    if goes_round(taps):
        return s + "\nThey go round in order: the mic order in the code is right!"
    return s + "\nNOT in order round the board: show this to Claude."


def show_tap(parts, peaks, taps):
    """Light up the loudest mic and write every mic's level under it."""
    fig, circles, labels, title, footer = parts
    best = int(np.argmax(peaks))
    lead = peaks[best] - np.sort(peaks)[-2]
    for k, (c, lab) in enumerate(zip(circles, labels)):
        c.set_color(RED if k == best else GREY)
        c.set_radius(13 if k == best else 9)
        lab.set_text(f"{NAMES[k]}\n{peaks[k]:.0f} dB")
        lab.set_weight("bold" if k == best else "normal")
    title.set_text(f"Loudest: mic {best}  ({lead:.0f} dB louder than the next)")
    footer.set_text(sequence_text(taps))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="pretend taps, no board needed")
    ap.add_argument("--save", help="with --demo: save the picture after 4 taps to this PNG and stop")
    a = ap.parse_args()
    if a.save:
        plt.switch_backend("Agg")                  # draw off-screen, no window
    parts = make_window()
    if not a.save:
        plt.ion()
        plt.show()
    background, taps, since_tap = None, [], GAP_BLOCKS
    for x in (demo_blocks() if a.demo else stream_blocks(BLOCK)):
        peaks = peak_db(x)
        since_tap += 1
        if background is None:
            background = peaks.max()
        if since_tap > GAP_BLOCKS and peaks.max() > background + TAP_DB:
            add_tap(taps, int(np.argmax(peaks)))
            show_tap(parts, peaks, taps)
            since_tap = 0
            if a.save and len(taps) == 4:
                parts[0].savefig(a.save, dpi=110)
                return
        elif since_tap > GAP_BLOCKS:
            background = 0.95 * background + 0.05 * peaks.max()   # slowly follow the room's noise
        if a.save:
            continue
        if not plt.fignum_exists(parts[0].number):
            return                                                # window closed
        plt.pause(BLOCK / FS if a.demo else 0.001)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
