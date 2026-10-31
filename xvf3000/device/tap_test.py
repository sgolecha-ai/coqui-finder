"""Tap test: find which channel is which microphone, one hole at a time.

Number the 4 mic holes 1-4 going round the square (either way). For each hole you tap
gently right next to it; the script records a few seconds, keeps the loudest moment on
each raw mic channel, and shows which channel heard the tap best. At the end it checks
that the channels go round the board in order, which direction finding needs.

  .venv/bin/python xvf3000/device/tap_test.py
"""
import os
import tempfile

import numpy as np
from scipy.io import wavfile

from common import record_wav
from coqui_sim.xvf_format import RAW_CHANNELS

SECONDS = 3
MIN_LEAD_DB = 3          # the loudest channel must beat the next one by this much
LABELS = [f"ch{c + 1} mic {m}" for m, c in enumerate(RAW_CHANNELS)]


def peak_levels(wav_path):
    """Loudest moment on each raw mic channel, in dBFS (0 = loudest possible)."""
    _, x = wavfile.read(wav_path)
    raw = x[:, RAW_CHANNELS].astype(float)
    raw -= raw.mean(axis=0)                       # remove any steady offset
    return 20 * np.log10(np.abs(raw).max(axis=0) / 32768 + 1e-9)


def show(peaks, best):
    for k, (lab, p) in enumerate(zip(LABELS, peaks)):
        bar = "#" * int(np.clip((p + 90) / 2, 0, 45))   # -90 dBFS .. 0 dBFS -> 0..45 characters
        print(f"  {lab:10s} {p:6.1f} dB |{bar}" + ("   <- loudest" if k == best else ""))


def tap_one_hole(n):
    """Record taps next to hole n until one channel is clearly loudest; return that mic number."""
    path = os.path.join(tempfile.gettempdir(), "tap.wav")
    while True:
        input(f"\nHole {n}: press Enter, then tap 3 times right next to hole {n}...")
        record_wav(path, SECONDS)
        peaks = peak_levels(path)
        best = int(np.argmax(peaks))
        show(peaks, best)
        lead = peaks[best] - np.sort(peaks)[-2]
        if lead >= MIN_LEAD_DB:
            return best
        print(f"  Only {lead:.1f} dB ahead of the next channel. Tap closer to the hole and try again.")


def goes_round(order):
    """True if the mics found for holes 1-4 go round the square in order (either direction)."""
    steps = {(b - a) % 4 for a, b in zip(order, order[1:] + order[:1])}
    return sorted(order) == [0, 1, 2, 3] and steps in ({1}, {3})


def main():
    print("Tap test. Number the 4 mic holes 1-4 going round the square (either way).")
    order = [tap_one_hole(n) for n in range(1, 5)]
    print("\n" + "\n".join(f"Hole {n + 1} -> {LABELS[m]}" for n, m in enumerate(order)))
    if goes_round(order):
        print("\nGood: the channels go round the board in order. The mic order in the code is right.")
    elif sorted(order) != [0, 1, 2, 3]:
        print("\nTwo holes picked the same channel. Run it again, tapping right next to each hole.")
    else:
        print("\nThe channels are NOT in order round the board. Share the result above with Claude:\n"
              "the mic order in coqui_sim/config.py needs changing.")


if __name__ == "__main__":
    main()
