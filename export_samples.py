"""Write example scenes as XVF3800-format WAVs, each with a ground-truth JSON.

  python export_samples.py            -> samples/*.wav, *.truth.json, *_raw.csv, figures

Each WAV is exactly what `arecord -D hw:<card>,0 -c 6 -r 16000 -f S16_LE` would
capture from the board (channels 3-6 = raw mics 0-3; channels 1-2 silent here).
The script then reads every WAV back and runs the device pipeline on it, so the
same code path will work on real recordings.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from coqui_sim import config as cfg
from coqui_sim.acoustics import frog_at, render_scene
from coqui_sim.doa import ang_diff
from coqui_sim.pipeline import run_device
from coqui_sim.signals import synth_coqui_call
from coqui_sim.xvf_format import read_xvf_wav, write_xvf_wav

OUT = "samples"


def call_fn(frog, rng):
    return synth_coqui_call(rng, pitch_scale=frog.pitch_scale)


def make_scene(name, spec, duration, noise, seed, note):
    """spec: list of (azimuth_deg, distance_m, height_m)."""
    rng = np.random.default_rng(seed)
    frogs = []
    for az, d, h in spec:
        fr = frog_at(az, d, h, rng)
        period = rng.uniform(*cfg.CALL_PERIOD_S)
        fr.call_times = [float(t) for t in np.arange(rng.uniform(0.2, period), duration - 0.5, period)]
        frogs.append((az, d, h, fr))
    x = render_scene([f for *_, f in frogs], duration, rng, call_fn,
                     background_spl=cfg.BACKGROUND_SPL[noise])
    wav = f"{OUT}/{name}.wav"
    write_xvf_wav(wav, x)
    truth = {
        "file": f"{name}.wav", "note": note, "duration_s": duration,
        "sample_rate_hz": cfg.FS, "format": "WAV, 6 channels, int16 (S16_LE)",
        "channels": {"1": "processed output (silent in simulation)",
                     "2": "processed output (silent in simulation)",
                     "3": "raw mic 0", "4": "raw mic 1", "5": "raw mic 2", "6": "raw mic 3"},
        "mic_positions_m": cfg.MIC_POS.tolist(),
        "azimuth_convention": "degrees counter-clockwise from the +x axis of the mic coordinates",
        "background": f"{noise} ({cfg.BACKGROUND_SPL[noise]} dB SPL)",
        "frogs": [{"azimuth_deg": round(float(az), 1), "distance_m": float(d), "height_m": float(h),
                   "level_at_1m_db_spl": round(fr.spl_at_1m, 1),
                   "call_times_s": [round(t, 3) for t in fr.call_times]}
                  for az, d, h, fr in frogs],
    }
    with open(f"{OUT}/{name}.truth.json", "w") as f:
        json.dump(truth, f, indent=2)
    return wav, truth


def check(wav, truth):
    """Read the WAV back and run the device pipeline on it."""
    x = read_xvf_wav(wav)
    found, _ = run_device(x)
    real = [fr["azimuth_deg"] for fr in truth["frogs"]]
    hit = sum(any(ang_diff(f["bearing"], a) <= 15 for f in found) for a in real)
    return found, hit


def plot_one_call(wav, truth, path):
    """Zoom on one call: the four raw mics, showing the tiny arrival-time offsets."""
    from scipy.io import wavfile
    from scipy.signal import butter, sosfiltfilt
    _, raw = wavfile.read(wav)
    fr = truth["frogs"][0]
    t0 = fr["call_times_s"][1] + fr["distance_m"] / cfg.C_SOUND
    i0, i1 = int((t0 - 0.03) * cfg.FS), int((t0 + 0.33) * cfg.FS)
    seg = raw[i0:i1, 2:6].astype(float)
    t = (np.arange(i0, i1) / cfg.FS - t0) * 1000
    sos = butter(4, cfg.BAND_HZ, btype="band", fs=cfg.FS, output="sos")
    filt = sosfiltfilt(sos, seg, axis=0)
    cols = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    step = 2.4 * np.abs(seg).max()
    for k in range(4):
        ax.plot(t, seg[:, k] + (3 - k) * step, color=cols[k], lw=0.6)
        ax.text(t[0] - 4, (3 - k) * step, f"ch{k + 3}\nmic {k}", ha="right", va="center",
                fontsize=9, color=cols[k], clip_on=False)
    ax.set_xlim(t[0], t[-1])
    ax.set_yticks([])
    ax.set_xlabel("Time from call arrival (ms)")
    ax.set_title(f"One call as int16 samples, frog at {fr['distance_m']:.0f} m / {fr['azimuth_deg']:.0f}° "
                 f"(peak ±{int(np.abs(seg).max())} of ±32767)", loc="left", fontsize=11, fontweight="bold")
    ax = axes[1]
    z = (t > 20) & (t < 26)              # 6 ms inside the "co" note
    for k in range(4):
        ax.plot(t[z], filt[z, k], "-", color=cols[k], lw=1.6, label=f"mic {k}")
    ax.set_xlabel("ms (band-passed 0.9–2.5 kHz)")
    ax.set_title("Zoomed: mics hear it up to ~0.27 ms apart", loc="left", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4)
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    scenes = [
        ("01_one_frog_10m_quiet", [(60, 10, 2.0)], 10, "quiet", 1, "One frog, quiet night"),
        ("02_one_frog_15m_typical", [(200, 15, 1.5)], 10, "typical", 2, "One frog at the Gate 1 distance"),
        ("03_one_frog_25m_loud", [(310, 25, 2.5)], 10, "loud", 3, "Hard case: far frog, loud background"),
        ("04_two_frogs_30deg", [(40, 8, 1.0), (70, 9, 2.0)], 20, "typical", 4, "Two frogs 30 deg apart"),
        ("05_four_frogs_demo", [(25, 6, 1.0), (105, 6, 2.5), (145, 18, 1.5), (185, 18, 3.0)], 25,
         "typical", 5, "Mixed distances, like the demo figure"),
        ("06_chorus_12_frogs", [(a, d, h) for a, d, h in zip(
            np.arange(0, 360, 30) + 7, [3, 5, 8, 12, 15, 18, 4, 7, 10, 14, 17, 20],
            [1, 2, 3, 1.5, 2.5, 0.5, 3.5, 1, 2, 3, 1.5, 2.5])], 25, "typical", 6,
         "Dense chorus: expect an undercount"),
        ("07_no_frogs_typical", [], 10, "typical", 7, "Background only: should report 0 frogs"),
    ]
    print(f"{'file':32s} {'frogs':>5s} {'found':>5s} {'matched':>7s}  bearings found")
    for name, spec, dur, noise, seed, note in scenes:
        wav, truth = make_scene(name, spec, dur, noise, seed, note)
        found, hit = check(wav, truth)
        print(f"{name:32s} {len(spec):5d} {len(found):5d} {hit:7d}  "
              + ", ".join(f"{f['bearing']:.0f}° {f['range_class']}" for f in found))

    # A small text view of the raw samples for one call (first 4000 samples after it starts).
    from scipy.io import wavfile
    _, raw = wavfile.read(f"{OUT}/02_one_frog_15m_typical.wav")
    tr = json.load(open(f"{OUT}/02_one_frog_15m_typical.truth.json"))
    i0 = int((tr["frogs"][0]["call_times_s"][0]) * cfg.FS)
    np.savetxt(f"{OUT}/02_one_call_raw_samples.csv", raw[i0:i0 + 4000], fmt="%d", delimiter=",",
               header="ch1_processed,ch2_processed,ch3_mic0,ch4_mic1,ch5_mic2,ch6_mic3", comments="")
    plot_one_call(f"{OUT}/01_one_frog_10m_quiet.wav",
                  json.load(open(f"{OUT}/01_one_frog_10m_quiet.truth.json")),
                  f"{OUT}/one_call_four_mics.png")


if __name__ == "__main__":
    main()
