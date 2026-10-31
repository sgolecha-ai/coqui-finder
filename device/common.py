"""Shared helpers for the device tools: find the board, record from it, convert angles.

Works on a Mac (via the `sounddevice` library) and on a Raspberry Pi (via `sounddevice` if
installed, otherwise Linux's `arecord`).
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FS = 16000
CHANNELS = 6
NAME_PATTERN = r"respeaker|xvf3800|4-mic array"

CONFIG_PATH = os.path.join(ROOT, "device", "device_config.json")
DEFAULT_CONFIG = {
    # Raw bearing (counter-clockwise from the mic-coordinate x axis) that points at your 0° chalk mark.
    "bearing_offset_deg": 0.0,
    # +1: chalk angles increase the same way as raw bearings; -1: they run the other way.
    "bearing_sign": 1,
    # arecord sample formats to try, in order (Raspberry Pi only).
    "formats": ["S16_LE", "S32_LE"],
}

try:
    import sounddevice as sd
except (ImportError, OSError):            # not installed, or PortAudio missing
    sd = None


# ---------------------------------------------------------------- settings and angles
def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def to_chalk_angle(raw_deg, cfg=None):
    """Convert a raw bearing from the pipeline into the angle on your chalk circle."""
    cfg = cfg or load_config()
    return (cfg["bearing_sign"] * (raw_deg - cfg["bearing_offset_deg"])) % 360


# ---------------------------------------------------------------- finding the board
def backend():
    if sd is not None:
        return "sounddevice"
    if shutil.which("arecord"):
        return "arecord"
    sys.exit("No way to record audio. Install sounddevice:  .venv/bin/pip install sounddevice")


def find_input_device():
    """sounddevice index of the XVF3800 (an input with at least 6 channels)."""
    for i, d in enumerate(sd.query_devices()):
        if re.search(NAME_PATTERN, d["name"], re.I) and d["max_input_channels"] >= CHANNELS:
            return i
    names = "\n  ".join(f"{d['name']} ({d['max_input_channels']} in)" for d in sd.query_devices())
    sys.exit("XVF3800 not found, or it has fewer than 6 input channels "
             "(is the 6-channel firmware flashed?). Audio devices seen:\n  " + names)


def find_card():
    """ALSA card number of the XVF3800, from `arecord -l` (Raspberry Pi)."""
    out = subprocess.run(["arecord", "-l"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if re.search(NAME_PATTERN, line, re.I):
            m = re.match(r"card (\d+):", line)
            if m:
                return int(m.group(1))
    sys.exit("XVF3800 sound card not found. Is it plugged in? Try: arecord -l")


def arecord_cmd(card, fmt, seconds=None, out_path=None):
    cmd = ["arecord", "-q", "-D", f"plughw:{card},0", "-c", str(CHANNELS), "-r", str(FS), "-f", fmt]
    if seconds is not None:
        cmd += ["-d", str(int(seconds))]
    cmd += ["-t", "raw"] if out_path is None else [out_path]
    return cmd


def permission_hint():
    if platform.system() == "Darwin":
        return ("\nOn a Mac, allow microphone access: System Settings > Privacy & Security > Microphone, "
                "switch on Terminal (or the app you run this from), then quit and reopen it.")
    return ""


# ---------------------------------------------------------------- recording
def record_wav(out_path, seconds, cfg=None):
    """Record a 6-channel, 16 kHz WAV from the board. Returns a short description of how."""
    cfg = cfg or load_config()
    if backend() == "sounddevice":
        dev = find_input_device()
        x = sd.rec(int(seconds * FS), samplerate=FS, channels=CHANNELS, dtype="int16", device=dev)
        sd.wait()
        wavfile.write(out_path, FS, x)
        if not np.any(x[:, 2:6]):
            print("Warning: channels 3-6 are completely silent." + permission_hint())
        return "sounddevice int16"
    card = find_card()
    last = ""
    for fmt in cfg["formats"]:
        r = subprocess.run(arecord_cmd(card, fmt, seconds, out_path), capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 44:
            return f"arecord {fmt}"
        last = r.stderr.strip()
    sys.exit(f"Recording failed with formats {cfg['formats']}: {last}")


def stream_blocks(block=1600, cfg=None):
    """Yield (block, 6) float arrays scaled to +-1.0, live from the board, until interrupted."""
    cfg = cfg or load_config()
    if backend() == "sounddevice":
        dev = find_input_device()
        with sd.InputStream(samplerate=FS, channels=CHANNELS, dtype="int16", device=dev,
                            blocksize=block) as st:
            while True:
                x, _ = st.read(block)
                yield np.asarray(x, dtype=float) / 32768.0
    fmt = cfg["formats"][0]
    dtype, scale = (np.int16, 32768.0) if fmt == "S16_LE" else (np.int32, 2147483648.0)
    nbytes = block * CHANNELS * np.dtype(dtype).itemsize
    proc = subprocess.Popen(arecord_cmd(find_card(), fmt), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        while True:
            buf = proc.stdout.read(nbytes)
            if len(buf) < nbytes:
                sys.exit("Recording stopped: " + proc.stderr.read().decode(errors="ignore"))
            yield np.frombuffer(buf, dtype=dtype).reshape(-1, CHANNELS).astype(float) / scale
    finally:
        proc.terminate()
