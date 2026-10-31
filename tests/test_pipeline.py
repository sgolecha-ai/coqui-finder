"""Regression test: the pipeline must still find the frogs in the bundled sample recordings.

Run before and after every code change:   .venv/bin/python tests/test_pipeline.py
(or: python3 -m pytest tests/)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from coqui_sim.doa import ang_diff                    # noqa: E402
from coqui_sim.pipeline import run_device             # noqa: E402
from coqui_sim.xvf_format import read_xvf_wav         # noqa: E402

SAMPLES = os.path.join(ROOT, "samples")
TOLERANCE_DEG = 15


def check(name):
    truth = json.load(open(os.path.join(SAMPLES, name + ".truth.json")))
    frogs, _ = run_device(read_xvf_wav(os.path.join(SAMPLES, name + ".wav")))
    real = [f["azimuth_deg"] for f in truth["frogs"]]
    assert len(frogs) == len(real), f"{name}: found {len(frogs)} frogs, expected {len(real)}"
    for a in real:
        best = min((ang_diff(f["bearing"], a) for f in frogs), default=999)
        assert best <= TOLERANCE_DEG, f"{name}: frog at {a:.0f}° missed (closest {best:.0f}° away)"
    return f"{name}: {len(frogs)} frog(s), bearings " + ", ".join(f"{f['bearing']:.0f}°" for f in frogs)


def test_one_frog():
    check("01_one_frog_10m_quiet")


def test_two_frogs():
    check("04_two_frogs_30deg")


def test_no_frogs():
    check("07_no_frogs_typical")


if __name__ == "__main__":
    for n in ["01_one_frog_10m_quiet", "04_two_frogs_30deg", "07_no_frogs_typical"]:
        print("PASS", check(n))
    print("All tests passed.")
