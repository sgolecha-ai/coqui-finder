"""Line the device's angles up with your chalk circle.

You clap (or tap two sticks) once at the 0° chalk mark and once at the 90° mark, about 1 m
from the array. The script measures each clap's raw bearing, works out the offset and the
direction angles increase, and saves them to device/device_config.json. After this, every
tool reports angles that match your chalk marks.

  .venv/bin/python xvf3000/device/clap_test.py
  .venv/bin/python xvf3000/device/clap_test.py --check     # just report clap bearings with current settings
"""
import argparse
import os
import tempfile

import numpy as np

from common import load_config, record_wav, save_config, to_chalk_angle
from coqui_sim.doa import SrpPhat, ang_diff, stft_channels
from coqui_sim.xvf_format import read_xvf_wav


def clap_bearing(wav_path):
    """Raw bearing of the loudest short sounds in the clip (claps are too short for the frog detector)."""
    x = read_xvf_wav(wav_path)
    f, t, Z = stft_channels(x)
    srp = SrpPhat()
    e = np.mean(np.abs(Z[:, srp.bins, :]) ** 2, axis=(0, 1))
    loud = e >= np.percentile(e, 97)                 # the clap frames
    if loud.sum() == 0 or 10 * np.log10(e.max() / np.median(e)) < 10:
        return None
    m = srp.frame_maps(Z)[loud].sum(axis=0)
    return float(srp.az[np.argmax(m)])


def capture(prompt, seconds=4):
    input(f"\n{prompt}\nPress Enter, then clap 3 times (about 1 s apart)...")
    path = os.path.join(tempfile.gettempdir(), "clap.wav")
    record_wav(path, seconds)
    b = clap_bearing(path)
    if b is None:
        print("  Couldn't hear a clear clap. Clap louder or move closer, and try again.")
    else:
        print(f"  raw bearing: {b:.0f}°")
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report clap angles using the saved settings")
    a = ap.parse_args()
    cfg = load_config()
    if a.check:
        while True:
            b = capture("Clap anywhere around the array (Ctrl+C to stop).")
            if b is not None:
                print(f"  chalk angle: {to_chalk_angle(b, cfg):.0f}°")

    b0 = None
    while b0 is None:
        b0 = capture("Stand at the 0° chalk mark, about 1 m from the array.")
    b90 = None
    while b90 is None:
        b90 = capture("Now stand at the 90° chalk mark, about 1 m from the array.")

    d = (b90 - b0 + 180) % 360 - 180                  # signed raw change from the 0° to the 90° mark
    sign = 1 if d > 0 else -1
    if not 45 <= abs(d) <= 135:
        print(f"\nWarning: the two claps are {abs(d):.0f}° apart instead of about 90°. "
              "Check the chalk marks and try again in a quieter spot.")
    cfg["bearing_offset_deg"] = round(b0, 1)
    cfg["bearing_sign"] = sign
    save_config(cfg)
    print(f"\nSaved: offset {b0:.0f}°, angles run {'the same way as' if sign > 0 else 'opposite to'} raw bearings.")
    print(f"Check: 0° mark -> {to_chalk_angle(b0, cfg):.0f}°, 90° mark -> {to_chalk_angle(b90, cfg):.0f}°")
    print("Run with --check to try other directions.")


if __name__ == "__main__":
    main()
