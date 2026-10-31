"""Loudness calibration: teach the code how loud the board's numbers really are.

The board gives numbers ("counts"), not decibels. To turn counts into dB SPL (what a sound
level meter shows) the code uses FULL_SCALE_SPL in coqui_sim/config.py, which is only a
guess (ASSUMED 120 dB) until this script measures it. Distance estimates depend on it:
6 dB wrong makes every distance 2 times too near or too far.

How it works:
  1. Records 5 s of the room with the calibration sound OFF (is the room quiet enough?).
  2. Records 10 s with the calibration sound ON, played from a phone 1 m from the board.
  3. You type in what the sound level meter next to the board read during step 2.
  4. The code measures the same sound with its current guess. The difference between its
     number and the meter's is how wrong the guess is, so it corrects FULL_SCALE_SPL by that
     much and (if you say yes) saves the new value in coqui_sim/config.py.

  .venv/bin/python xvf3000/device/loudness_cal.py
  .venv/bin/python xvf3000/device/loudness_cal.py --make-sound   # (re)make the calibration sound
"""
import argparse
import datetime
import os
import re
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

from common import ROOT, record_wav
from coqui_sim import config as cfg
from coqui_sim.pipeline import band_level_spl
from coqui_sim.xvf_format import read_xvf_wav

SOUND_PATH = os.path.join(ROOT, "calibration", "calibration_sound.wav")
CONFIG_PY = os.path.join(ROOT, "coqui_sim", "config.py")
MIN_LEAD_DB = 10       # the calibration sound must be this much louder than the room


def make_sound(path=SOUND_PATH, seconds=60, fs=22050):
    """Write the calibration sound: steady hiss covering the coqui band (0.9-2.5 kHz).

    A hiss (band-limited noise) is used instead of a single beep because a beep's loudness
    changes a lot when you move a few centimetres (echoes in the room add and cancel).
    """
    rng = np.random.default_rng(71)
    sos = butter(6, cfg.BAND_HZ, btype="band", fs=fs, output="sos")
    y = sosfiltfilt(sos, rng.normal(0, 1, seconds * fs))
    fade = np.minimum(1, np.minimum(np.arange(len(y)), np.arange(len(y))[::-1]) / (0.5 * fs))
    y = y * fade / np.abs(y).max() * 0.9                  # 0.5 s fade in/out, no clipping
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wavfile.write(path, fs, (y * 32767).astype(np.int16))
    print(f"Wrote {path} ({seconds} s). Copy it to the phone that will play it.")


def measure(seconds):
    """Record from the board; return (level of all 4 mics, level of each mic) in dB SPL."""
    path = os.path.join(tempfile.gettempdir(), "loudness.wav")
    record_wav(path, seconds)
    x = read_xvf_wav(path)                                # (4, N) pressure, using today's guess
    return band_level_spl(x), [band_level_spl(x[k:k + 1]) for k in range(4)]


def ask_meter():
    while True:
        try:
            v = float(input("What did the sound level meter read (dB)? ").strip())
            if 40 <= v <= 110:
                return v
        except ValueError:
            pass
        print("  Please type just the number, for example 71.5")


def save_full_scale(new, meter):
    """Replace the FULL_SCALE_SPL line in coqui_sim/config.py with the measured value."""
    text = open(CONFIG_PY).read()
    line = (f"FULL_SCALE_SPL = {new:.1f}   # MEASURED {datetime.date.today()} by loudness_cal.py "
            f"(meter read {meter:.1f} dB)")
    text, n = re.subn(r"^FULL_SCALE_SPL = .*$", line, text, flags=re.M)
    if n != 1:
        raise SystemExit("Couldn't find the FULL_SCALE_SPL line in config.py; change it by hand.")
    with open(CONFIG_PY, "w") as f:
        f.write(text)
    print(f"Saved in {CONFIG_PY}:\n  {line}")


def report(quiet, loud, per_mic, meter):
    """Print what was measured; return the corrected FULL_SCALE_SPL (or None if unusable)."""
    print(f"\nRoom, sound off:      {quiet:5.1f} dB  (as the code measures it now)")
    print(f"Calibration sound on: {loud:5.1f} dB  (as the code measures it now)")
    print("  each mic:           " + ", ".join(f"mic {k} {v:.1f}" for k, v in enumerate(per_mic)))
    print(f"Sound level meter:    {meter:5.1f} dB")
    if loud - quiet < MIN_LEAD_DB:
        print(f"\nThe sound is only {loud - quiet:.0f} dB louder than the room (needs {MIN_LEAD_DB}). "
              "Turn the phone up or find a quieter spot, and try again.")
        return None
    if max(per_mic) - min(per_mic) > 3:
        print("\nWarning: the mics disagree by more than 3 dB. Is the phone pointing at the board, "
              "1 m away, with nothing in between?")
    off_by = meter - loud
    new = cfg.FULL_SCALE_SPL + off_by
    print(f"\nThe code's guess was off by {off_by:+.1f} dB. "
          f"FULL_SCALE_SPL: {cfg.FULL_SCALE_SPL:.1f} -> {new:.1f} dB")
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-sound", action="store_true", help="write the calibration sound WAV and stop")
    if ap.parse_args().make_sound:
        return make_sound()
    print("Loudness calibration. Phone 1 m from the board; sound level meter right next to the board.")
    input("\n1) Calibration sound OFF, everyone quiet. Press Enter (records 5 s)...")
    quiet, _ = measure(5)
    input("\n2) Start the calibration sound on the phone. Press Enter (records 10 s), "
          "and watch the meter while it records...")
    loud, per_mic = measure(10)
    meter = ask_meter()
    new = report(quiet, loud, per_mic, meter)
    if new is not None and input("\nSave this in config.py? [y/N] ").strip().lower() == "y":
        save_full_scale(new, meter)
        print("Run the script again to check: it should now be off by about 0 dB.")


if __name__ == "__main__":
    main()
