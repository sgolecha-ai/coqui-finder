"""Compare microphone array designs for the Coqui Finder.

For each design: single-call bearing error (typical night, foliage echoes), how well two
frogs calling at the same moment are separated, and the width of the "direction blur"
(main lobe of the SRP-PHAT map).

  python compare_arrays.py
"""
import json
import os
from itertools import combinations
from multiprocessing import Pool

import numpy as np
from scipy.signal import stft

from coqui_sim import config as cfg
from coqui_sim.acoustics import frog_at, render_scene
from coqui_sim.doa import ang_diff, peaks_on_circle
from coqui_sim.signals import synth_coqui_call


def circle(n, diameter_m):
    a = 2 * np.pi * np.arange(n) / n
    r = diameter_m / 2
    return np.stack([r * np.cos(a), r * np.sin(a), np.zeros(n)], axis=1)


def grid(k, pitch_m):
    c = (np.arange(k) - (k - 1) / 2) * pitch_m
    return np.array([[x, y, 0.0] for y in c for x in c])


ARRAYS = {
    "XVF3800: 4 mics, 66 mm square": cfg.MIC_POS,
    "6-mic circle, 9 cm across": circle(6, 0.093),
    "UMA-16: 16 mics, 4x4 grid, 42 mm pitch": grid(4, 0.042),
    "8-mic circle, 18 cm across": circle(8, 0.18),
    "12-mic circle, 30 cm across": circle(12, 0.30),
}


class Srp:
    """SRP-PHAT for any number of microphones."""

    def __init__(self, mic_pos):
        self.pairs = list(combinations(range(len(mic_pos)), 2))
        f = np.fft.rfftfreq(cfg.NFFT, 1 / cfg.FS)
        self.bins = np.where((f >= cfg.BAND_HZ[0]) & (f <= cfg.BAND_HZ[1]))[0]
        a = np.radians(cfg.AZ_GRID_DEG)
        u = np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], axis=1)
        tau = np.stack([(mic_pos[j] - mic_pos[i]) @ u.T / cfg.C_SOUND for i, j in self.pairs])
        self.steer = np.exp(2j * np.pi * tau[:, :, None] * f[self.bins][None, None, :])   # conj steering

    def map(self, x, t0=None, t1=None):
        """SRP map summed over frames inside [t0, t1] s (default: frames well above the noise floor)."""
        _, t, Z = stft(x, fs=cfg.FS, nperseg=cfg.NFFT, noverlap=cfg.NFFT - cfg.HOP, boundary=None, padded=False)
        X = Z[:, self.bins, :]
        if t0 is not None:
            keep = (t >= t0) & (t <= t1)
        else:
            e = 10 * np.log10(np.mean(np.abs(X) ** 2, axis=(0, 1)) + 1e-30)
            keep = e > np.percentile(e, 20) + 6
            if keep.sum() < 2:
                keep = e >= np.sort(e)[-3]
        X = X[:, :, keep]
        m = 0
        for p, (i, j) in enumerate(self.pairs):
            cr = X[i] * np.conj(X[j])
            cr /= np.abs(cr) + 1e-20
            m = m + np.real(np.einsum("ab,bt->a", self.steer[p], cr))
        return m / (len(self.pairs) * len(self.bins) * X.shape[2])


def call_fn(fr, rng):
    return synth_coqui_call(rng, pitch_scale=fr.pitch_scale)


def single_trial(args):
    name, seed, dist = args
    mics = ARRAYS[name]
    rng = np.random.default_rng(seed)
    az = rng.uniform(0, 360)
    fr = frog_at(az, dist, rng.uniform(0.3, 4.0), rng)
    fr.call_times = [0.1]
    x = render_scene([fr], 0.55, rng, call_fn, background_spl=cfg.BACKGROUND_SPL["typical"], mic_pos=mics)
    m = Srp(mics).map(x)
    return float(ang_diff(cfg.AZ_GRID_DEG[np.argmax(m)], az))


def pair_trial(args):
    name, seed, sep = args
    mics = ARRAYS[name]
    rng = np.random.default_rng(seed)
    az0 = rng.uniform(0, 360)
    frogs = []
    for k, az in enumerate((az0, (az0 + sep) % 360)):
        fr = frog_at(az, rng.uniform(6, 10), rng.uniform(0.5, 3.0), rng, spread_db=1.5)
        fr.call_times = [0.1 + k * rng.uniform(0, 0.05)]        # two calls overlapping in time
        frogs.append((az, fr))
    x = render_scene([f for _, f in frogs], 0.6, rng, call_fn, background_spl=cfg.BACKGROUND_SPL["typical"],
                     mic_pos=mics)
    m = Srp(mics).map(x)
    pk = peaks_on_circle(m, cfg.AZ_GRID_DEG, n_max=2, min_sep_deg=4, rel_height=0.5)
    ok = len(pk) == 2 and all(min(ang_diff(p, a) for p in pk) <= 6 for a, _ in frogs)
    return bool(ok)


def turns_trial(args):
    """Two frogs taking turns (no overlap), 5 calls each; bearings per call, then grouped."""
    name, seed, sep = args
    mics = ARRAYS[name]
    rng = np.random.default_rng(seed)
    az0 = rng.uniform(0, 360)
    frogs, windows = [], []
    for k, az in enumerate((az0, (az0 + sep) % 360)):
        d = rng.uniform(6, 10)
        fr = frog_at(az, d, rng.uniform(0.5, 3.0), rng)
        fr.call_times = [0.1 + 0.8 * i + 0.4 * k for i in range(5)]
        frogs.append((az, fr))
        windows += [(t + d / cfg.C_SOUND, t + d / cfg.C_SOUND + 0.29) for t in fr.call_times]
    x = render_scene([f for _, f in frogs], 4.2, rng, call_fn, background_spl=cfg.BACKGROUND_SPL["typical"],
                     mic_pos=mics)
    srp = Srp(mics)
    b = np.array([cfg.AZ_GRID_DEG[np.argmax(srp.map(x, a, z))] for a, z in windows])
    # group: smoothed circular histogram, a frog = a peak supported by >= 3 calls
    az = cfg.AZ_GRID_DEG
    dens = np.exp(-0.5 * (ang_diff(az[:, None], b[None, :]) / 3.0) ** 2).sum(axis=1)
    found = []
    for i in np.argsort(dens)[::-1]:
        if dens[i] < 1.5:
            break
        if dens[i] >= dens[(i - 1) % 360] and dens[i] >= dens[(i + 1) % 360] and \
                all(ang_diff(az[i], f) >= 5 for f in found) and (ang_diff(b, az[i]) <= 4).sum() >= 3:
            found.append(az[i])
    truth = [a for a, _ in frogs]
    return bool(len(found) == 2 and all(min(ang_diff(f, a) for f in found) <= 6 for a in truth))


def lobe_width(name):
    """Width (deg) of the main lobe at half height, frog at 60 deg, 5 m, quiet, no echoes."""
    mics = ARRAYS[name]
    rng = np.random.default_rng(1)
    fr = frog_at(60, 5, 1.2, rng, spread_db=0)
    fr.call_times = [0.1]
    x = render_scene([fr], 0.55, rng, call_fn, background_spl=None, n_reflectors=0, quantise=False, mic_pos=mics)
    m = Srp(mics).map(x)
    m = (m - m.min()) / (m.max() - m.min())
    k = int(np.argmax(m))
    w = 0
    for step in (1, -1):
        j = k
        while m[j % 360] >= 0.5 and abs(j - k) < 180:
            j += step
        w += abs(j - k)
    return float(w)


def main():
    out = {}
    seps = [8, 12, 16, 20, 25, 30]
    turn_seps = [6, 10, 15, 20, 30]
    with Pool(os.cpu_count()) as pool:
        for name in ARRAYS:
            r = {"mics": len(ARRAYS[name]), "lobe_width_deg": lobe_width(name)}
            for d in (15, 25):
                e = pool.map(single_trial, [(name, 1000 * d + i, d) for i in range(80)])
                r[f"p90_err_{d}m"] = float(np.percentile(e, 90))
            r["two_frog_success"] = {}
            for s in seps:
                ok = pool.map(pair_trial, [(name, 50_000 + 100 * s + i, s) for i in range(30)])
                r["two_frog_success"][s] = 100 * float(np.mean(ok))
            r["turns_success"] = {}
            for s_ in turn_seps:
                ok = pool.map(turns_trial, [(name, 70_000 + 100 * s_ + i, s_) for i in range(20)])
                r["turns_success"][s_] = 100 * float(np.mean(ok))
            out[name] = r
            print(name, json.dumps(r))
    os.makedirs("results", exist_ok=True)
    with open("results/array_comparison.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
