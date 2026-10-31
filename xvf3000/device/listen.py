"""Record from the XVF3000 board and report the calling frogs: count, direction and range.

  .venv/bin/python xvf3000/device/listen.py                        # listen 30 s once
  .venv/bin/python xvf3000/device/listen.py --seconds 60 --loop    # keep listening, one report per minute
  .venv/bin/python xvf3000/device/listen.py --wav xvf3000/samples/04_two_frogs_30deg.wav   # analyse a saved file

Every recording is kept in recordings/ with a matching .json result, so any trial can be
re-analysed later (for example after improving the code).
"""
import argparse
import json
import os
import time
from datetime import datetime

from common import ROOT, load_config, record_wav, to_chalk_angle
from coqui_sim.pipeline import run_device
from coqui_sim.xvf_format import read_xvf_wav


def analyse(wav_path, cfg):
    x = read_xvf_wav(wav_path)
    frogs, calls = run_device(x)
    frogs = sorted(frogs, key=lambda f: to_chalk_angle(f["bearing"], cfg))
    for f in frogs:
        f["chalk_angle"] = round(to_chalk_angle(f["bearing"], cfg), 1)
    return {"file": os.path.basename(wav_path), "duration_s": round(x.shape[1] / 16000, 1),
            "frogs_found": len(frogs), "frogs": frogs, "calls_detected": len(calls)}


def report(res):
    print(f"\n{res['file']}  ({res['duration_s']} s, {res['calls_detected']} call bearings)")
    if not res["frogs"]:
        print("  No calling frogs found.")
        return
    print(f"  {res['frogs_found']} calling frog(s):")
    print("    angle   range    est. distance   calls   level")
    for f in res["frogs"]:
        print(f"    {f['chalk_angle']:5.0f}°   {f['range_class']:7s}  {f['distance_est']:6.1f} m       "
              f"{f['n_calls']:4d}   {f['level']:5.1f} dB")
    print("  (Distance and level are rough until the board is calibrated; see README.md.)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--wav", help="analyse an existing 6-channel WAV instead of recording")
    a = ap.parse_args()
    cfg = load_config()

    if a.wav:
        res = analyse(a.wav, cfg)
        report(res)
        return

    out_dir = os.path.join(ROOT, "recordings")
    os.makedirs(out_dir, exist_ok=True)
    while True:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav = os.path.join(out_dir, f"{stamp}.wav")
        print(f"\nListening for {a.seconds} s ...", flush=True)
        t0 = time.time()
        fmt = record_wav(wav, a.seconds, cfg=cfg)
        res = analyse(wav, cfg)
        res["format"] = fmt
        res["analysis_s"] = round(time.time() - t0 - a.seconds, 1)
        with open(wav.replace(".wav", ".json"), "w") as f:
            json.dump(res, f, indent=2)
        report(res)
        if not a.loop:
            break


if __name__ == "__main__":
    main()
