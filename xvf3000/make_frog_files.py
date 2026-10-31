"""Make the coqui call files that the phones play (the pretend frogs).

  .venv/bin/python xvf3000/make_frog_files.py      -> xvf3000/frogs/*.wav and frogs.json

Each frog_X.wav is 60 s of one pretend male: the "co-qui" call repeating every 1.6-2.7 s,
each frog with its own pitch and rhythm, as real males differ. set_volume.wav is the same
call back to back with no pauses, at exactly the same loudness, so a sound level meter can
read it steadily: set each phone's volume with it, then play the frog file without touching
the volume. frogs.json records each frog's pitch and call times, for the answer keys.
"""
import json
import os

import numpy as np
from scipy.io import wavfile

from coqui_sim.signals import synth_coqui_call

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frogs")
FS = 22050             # Hz; plenty for calls below 2.5 kHz, and keeps the files small
SECONDS = 60
VOLUME_SECONDS = 30
CALL_RMS = 0.4         # every file has the same loudness per call (peaks about 0.6 of full scale)
# name: (pitch_scale, seconds between calls). Pitches within ±5% and rhythms inside the
# 1.5-3 s range of real males (CALL_PERIOD_S in coqui_sim/config.py).
FROGS = {"A": (0.95, 1.8), "B": (1.00, 2.4), "C": (1.05, 1.6), "D": (0.98, 2.7)}


def call(rng, pitch):
    return CALL_RMS * synth_coqui_call(rng, fs=FS, pitch_scale=pitch)


def frog_track(rng, pitch, period):
    """SECONDS of one frog calling. Returns (audio, list of call start times in s)."""
    y = np.zeros(SECONDS * FS)
    times, t = [], rng.uniform(0.3, period)
    while True:
        c = call(rng, pitch)
        i = int(t * FS)
        if i + len(c) > len(y):
            return y, times
        y[i:i + len(c)] += c
        times.append(round(t, 3))
        t += period * rng.uniform(0.92, 1.08)          # real frogs aren't perfectly regular


def write(name, y):
    wavfile.write(os.path.join(OUT, name), FS, np.round(y * 32767).astype(np.int16))


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(2026)
    info = {"sample_rate_hz": FS, "seconds": SECONDS, "call_rms_dbfs": round(20 * np.log10(CALL_RMS), 1),
            "frogs": {}}
    for name, (pitch, period) in FROGS.items():
        y, times = frog_track(rng, pitch, period)
        write(f"frog_{name}.wav", y)
        info["frogs"][f"frog_{name}.wav"] = {
            "pitch_scale": pitch, "co_hz": round(1150 * pitch), "qui_top_hz": round(2150 * pitch),
            "period_s": period, "n_calls": len(times), "call_times_s": times}
        print(f"frog_{name}.wav: 'co' {1150 * pitch:.0f} Hz, 'qui' up to {2150 * pitch:.0f} Hz, "
              f"a call every ~{period} s ({len(times)} calls)")
    calls = np.concatenate([call(rng, 1.0) for _ in range(int(VOLUME_SECONDS / 0.28) + 1)])
    write("set_volume.wav", calls[:VOLUME_SECONDS * FS])
    print(f"set_volume.wav: {VOLUME_SECONDS} s of calls back to back, same loudness as the frogs")
    with open(os.path.join(OUT, "frogs.json"), "w") as f:
        json.dump(info, f, indent=2)


if __name__ == "__main__":
    main()
