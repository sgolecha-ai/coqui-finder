"""Live level meter for all 6 channels of the XVF3800. Ctrl+C to stop.

Use it to check that channels 3-6 (raw mics) are working, and to find which channel is
which microphone: tap gently next to one microphone and watch which bar jumps.

  .venv/bin/python device/mic_check.py
"""
import sys

import numpy as np

from common import backend, permission_hint, stream_blocks

LABELS = ["ch1 processed", "ch2 processed", "ch3 mic 0", "ch4 mic 1", "ch5 mic 2", "ch6 mic 3"]


def main():
    print(f"Recording with {backend()}. Levels in dBFS (0 = loudest possible). Ctrl+C to stop.\n")
    peak = np.full(6, -120.0)
    drawn = False
    loudest = -120.0
    try:
        for x in stream_blocks(1600):                         # 0.1 s blocks
            rms = 20 * np.log10(np.sqrt(np.mean(x ** 2, axis=0)) + 1e-6)   # silent channels read -120 dB
            peak = np.maximum(peak - 1.0, rms)                  # slowly falling peak hold
            loudest = max(loudest, rms[2:6].max())
            lines = []
            for lab, r, p in zip(LABELS, rms, peak):
                n = int(np.clip((r + 90) / 2, 0, 40))         # -90 dBFS .. -10 dBFS -> 0..40 characters
                lines.append(f"{lab:14s} {r:6.1f} dB |{'#' * n:<40s}| peak {p:6.1f}")
            if drawn:
                sys.stdout.write("\x1b[6F")                     # move the cursor back up 6 lines
            sys.stdout.write("\n".join(lines) + "\n")
            sys.stdout.flush()
            drawn = True
    except KeyboardInterrupt:
        pass
    if loudest <= -119:
        print("\nChannels 3-6 were completely silent." + permission_hint() +
              "\nAlso check the 6-channel firmware is flashed and setup/configure_xvf.sh has been run.")
    else:
        print("\nIf channels 3-6 stay near the bottom while you talk, run setup/configure_xvf.sh again.")


if __name__ == "__main__":
    main()
