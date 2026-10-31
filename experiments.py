"""Phase 1 experiments: does the XVF3800 geometry meet the Coqui Finder targets?

Run:  python experiments.py            (full run, ~15-25 min on 2 cores)
      python experiments.py --quick    (smoke test, ~2 min)
      python experiments.py --call my_call.wav   (use a real coqui recording)

Writes results/*.json and figures/*.png. Then run `python make_figures.py`.
"""
import argparse
import json
import os
from multiprocessing import Pool

import numpy as np

from coqui_sim import config as cfg
from coqui_sim.acoustics import frog_at, render_scene
from coqui_sim.doa import SrpPhat, ang_diff
from coqui_sim.pipeline import run_device, range_class
from coqui_sim.signals import load_call_wav, synth_coqui_call

CALL_WAV = None
SRP = None
MATCH_DEG = 15.0   # a found frog "matches" a real one if within the +/-15 deg target


def call_fn(frog, rng):
    if CALL_WAV is not None:
        return CALL_WAV
    return synth_coqui_call(rng, pitch_scale=frog.pitch_scale)


def _init(wav):
    global CALL_WAV, SRP
    CALL_WAV = load_call_wav(wav) if wav else None
    SRP = SrpPhat()


def circ_median(b):
    b = np.asarray(b)
    return float(b[np.argmin([ang_diff(b, x).sum() for x in b])])


# --- Experiment 1: one frog, bearing / detection / range vs distance & noise -----
def _e1_trial(args):
    seed, dist, noise = args
    rng = np.random.default_rng(seed)
    az = rng.uniform(0, 360)
    frog = frog_at(az, dist, rng.uniform(0.3, 4.0), rng)
    frog.call_times = list(0.3 + 0.6 * np.arange(5) + rng.uniform(0, 0.1, 5))
    x = render_scene([frog], 3.6, rng, call_fn, background_spl=cfg.BACKGROUND_SPL[noise])
    found, calls = run_device(x, SRP, max_sources_per_call=1)
    near = [c for c in calls if ang_diff(c["bearing"], az) < 30]
    return {
        "dist": dist, "noise": noise, "az": az, "spl_at_1m": frog.spl_at_1m,
        "n_calls_detected": len(calls),
        "call_errors": [float(ang_diff(c["bearing"], az)) for c in calls],
        "frog_bearing": circ_median([c["bearing"] for c in calls]) if calls else None,
        "frog_level": float(np.median([c["level"] for c in calls])) if calls else None,
        "n_near": len(near),
    }


# --- Experiment 2: two frogs, how close can they be and still be split? --------
def _e2_trial(args):
    seed, sep = args
    rng = np.random.default_rng(seed)
    az0 = rng.uniform(0, 360)
    frogs = []
    for az in (az0, (az0 + sep) % 360):
        fr = frog_at(az, rng.uniform(6, 10), rng.uniform(0.5, 3.0), rng)
        period = rng.uniform(*cfg.CALL_PERIOD_S)
        fr.call_times = list(np.arange(rng.uniform(0, period), 19.5, period))
        frogs.append((az, fr))
    x = render_scene([f for _, f in frogs], 20.0, rng, call_fn)
    found, _ = run_device(x, SRP)
    truth = [a for a, _ in frogs]
    hits = [any(ang_diff(fr["bearing"], t) <= MATCH_DEG for fr in found) for t in truth]
    return {"sep": sep, "n_found": len(found), "both_found": bool(all(hits)),
            "success": bool(all(hits) and len(found) == 2)}


# --- Experiment 3: counting N frogs in a 25 s listen -----------------------------
def _e3_trial(args):
    seed, n = args
    rng = np.random.default_rng(seed)
    frogs, truth = [], []
    for _ in range(n):
        az = rng.uniform(0, 360)
        fr = frog_at(az, rng.uniform(2, 20), rng.uniform(0.3, 4.0), rng)
        period = rng.uniform(*cfg.CALL_PERIOD_S)
        fr.call_times = list(np.arange(rng.uniform(0, period), 24.5, period * rng.uniform(0.9, 1.1)))
        frogs.append(fr)
        truth.append(az)
    x = render_scene(frogs, 25.0, rng, call_fn)
    found, _ = run_device(x, SRP)
    # "Separable" frogs: >= 20 deg from every other frog (the array's resolution).
    t = np.array(truth)
    separable = sum(all(ang_diff(t[i], t[j]) >= 20 for j in range(n) if j != i) for i in range(n))
    matched = sum(any(ang_diff(fr["bearing"], a) <= MATCH_DEG for fr in found) for a in truth)
    false_frogs = sum(all(ang_diff(fr["bearing"], a) > MATCH_DEG for a in truth) for fr in found)
    # Resolvable groups: true frogs merged when < 20 deg apart (circular single linkage).
    srt = np.sort(t)
    gaps = np.diff(np.append(srt, srt[0] + 360))
    groups = max(1, int(np.sum(gaps >= 20))) if n > 1 else 1
    return {"n_true": n, "n_groups": groups, "n_found": len(found), "n_separable": int(separable),
            "n_matched": int(matched), "n_false": int(false_frogs)}


# --- Experiment 4: how much do foliage echoes hurt? ------------------------------
def _e4_trial(args):
    seed, refl_gain = args
    rng = np.random.default_rng(seed)
    az = rng.uniform(0, 360)
    frog = frog_at(az, 10.0, rng.uniform(0.3, 4.0), rng)
    frog.call_times = list(0.3 + 0.6 * np.arange(5) + rng.uniform(0, 0.1, 5))
    x = render_scene([frog], 3.6, rng, call_fn, reflect_gain=refl_gain,
                     n_reflectors=4 if refl_gain > 0 else 0)
    _, calls = run_device(x, SRP, max_sources_per_call=1)
    return {"refl_gain": refl_gain,
            "call_errors": [float(ang_diff(c["bearing"], az)) for c in calls],
            "frog_error": float(ang_diff(circ_median([c["bearing"] for c in calls]), az)) if calls else None}


def run(pool, fn, jobs, name):
    print(f"{name}: {len(jobs)} simulations ...", flush=True)
    out = pool.map(fn, jobs, chunksize=2)
    with open(f"results/{name}.json", "w") as f:
        json.dump(out, f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--call", help="path to a real single-call WAV")
    ap.add_argument("--only", nargs="*", help="subset, e.g. e2 e3")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    a = ap.parse_args()
    os.makedirs("results", exist_ok=True)

    k = 4 if a.quick else 1
    dists = [1, 2, 4, 7, 10, 15, 20, 25, 30]
    e1 = [(i, d, nz) for d in dists for nz in cfg.BACKGROUND_SPL for i in range(40 // k)]
    e1 = [(1000 * j + s, d, nz) for j, (s, d, nz) in enumerate(e1)]
    seps = [5, 10, 15, 20, 30, 45, 90, 180]
    e2 = [(50_000 + 100 * s + i, s) for s in seps for i in range(16 // k)]
    ns = [1, 2, 3, 4, 5, 6, 8, 12]
    e3 = [(90_000 + 100 * n + i, n) for n in ns for i in range(16 // k)]
    gains = [0.0, 0.15, 0.3, 0.5]
    e4 = [(130_000 + 1000 * j + i, g) for j, g in enumerate(gains) for i in range(40 // k)]

    todo = set(a.only or ["e1", "e2", "e3", "e4"])
    with Pool(a.workers, initializer=_init, initargs=(a.call,)) as pool:
        if "e1" in todo:
            run(pool, _e1_trial, e1, "e1_single_frog")
        if "e2" in todo:
            run(pool, _e2_trial, e2, "e2_two_frogs")
        if "e3" in todo:
            run(pool, _e3_trial, e3, "e3_counting")
        if "e4" in todo:
            run(pool, _e4_trial, e4, "e4_foliage")
    print("done -> results/. Now run: python make_figures.py")


if __name__ == "__main__":
    main()
