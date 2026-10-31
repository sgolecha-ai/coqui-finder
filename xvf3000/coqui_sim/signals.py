"""Source signals: a synthetic coqui call and background noise.

The synthetic call is a stand-in until real recordings are available. Swap in a
real call with `load_call_wav()`; everything downstream accepts any mono call.
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from .config import FS


def synth_coqui_call(rng=None, fs=FS, pitch_scale=1.0):
    """Two-note "co-qui" call, normalised to unit RMS.

    ASSUMED shape (approximate, from published descriptions): a ~100 ms tonal
    "co" near 1.15 kHz, a short gap, then a ~150 ms "qui" sweeping up from about
    1.75 to 2.15 kHz, each with a weak second harmonic. `pitch_scale` lets each
    simulated frog differ slightly, as real males do.
    """
    rng = np.random.default_rng() if rng is None else rng

    def note(dur, f0, f1):
        n = int(dur * fs)
        t = np.arange(n) / fs
        f = np.linspace(f0, f1, n) * pitch_scale
        phase = 2 * np.pi * np.cumsum(f) / fs
        env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.6  # smooth on/off
        return env * (np.sin(phase) + 0.1 * np.sin(2 * phase + rng.uniform(0, 2 * np.pi)))

    co = note(0.100, 1150, 1180)
    gap = np.zeros(int(0.030 * fs))
    qui = note(0.150, 1750, 2150)
    call = np.concatenate([co, gap, qui])
    return call / np.sqrt(np.mean(call ** 2))


def load_call_wav(path, fs=FS):
    """Load a real call recording (mono or first channel), resample, unit RMS.

    Trim the file to a single call first (e.g. in Audacity).
    """
    sr, x = wavfile.read(path)
    x = x.astype(float)
    if x.ndim > 1:
        x = x[:, 0]
    if sr != fs:
        g = np.gcd(sr, fs)
        x = resample_poly(x, fs // g, sr // g)
    x = x - x.mean()
    return x / np.sqrt(np.mean(x ** 2))


def coloured_noise(n, rng, fs=FS):
    """Night-forest-like noise, unit RMS: pink-ish below 3 kHz plus an insect band.

    ASSUMED spectrum. Insects (crickets, katydids) mostly sit above the coqui
    band, so most of their energy is removed by the analysis band-pass.
    """
    spec = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / fs)
    shape = 1.0 / np.sqrt(np.maximum(f, 100.0))          # pink
    shape *= (f < 7000)
    insect = 6.0 * np.exp(-0.5 * ((f - 4800) / 500) ** 2)  # insect band
    spec *= shape + insect * shape.max()
    x = np.fft.irfft(spec, n)
    return x / np.sqrt(np.mean(x ** 2))
