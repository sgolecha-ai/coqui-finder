"""Turn frogs, noise and foliage into the four raw XVF3800 microphone channels.

Model (per microphone):
  * direct sound from each frog: exact fractional delay r/c, spherical spreading
    1/r, extra vegetation loss, frog-specific source level;
  * foliage echoes: a few random point reflectors near each frog (trunks, leaves)
    re-radiating a weaker, later copy;
  * background noise as a *diffuse* field (many plane waves from random
    directions), so it is partly correlated between nearby mics, as in reality;
  * independent microphone self-noise;
  * 16-bit quantisation of the raw (un-amplified) channels.
"""
from dataclasses import dataclass, field

import numpy as np

from . import config as cfg
from .signals import coloured_noise


@dataclass
class Frog:
    x: float
    y: float
    z: float                       # height above ground, m
    spl_at_1m: float = cfg.CALL_SPL_AT_1M
    pitch_scale: float = 1.0
    call_times: list = field(default_factory=list)  # seconds

    def position(self):
        return np.array([self.x, self.y, self.z])


def azimuth_deg(dx, dy):
    """Azimuth convention used everywhere: degrees counter-clockwise from +x."""
    return np.degrees(np.arctan2(dy, dx)) % 360


def frog_at(azimuth, distance, height, rng, spread_db=cfg.CALL_SPL_SPREAD_DB):
    """Place a frog at a horizontal distance/azimuth from the array (array at origin)."""
    a = np.radians(azimuth)
    return Frog(
        x=distance * np.cos(a), y=distance * np.sin(a), z=height,
        spl_at_1m=cfg.CALL_SPL_AT_1M + rng.normal(0, spread_db),
        pitch_scale=rng.uniform(0.95, 1.05),
    )


def _delay_into(out, sig, start_s, delays_s, gains, fs=cfg.FS):
    """Add `sig` to every mic channel of `out` with per-mic fractional delay and gain."""
    n_out = out.shape[1]
    d_min = delays_s.min()
    i0 = int(np.floor((start_s + d_min) * fs))
    frac = (start_s + delays_s) * fs - i0          # per-mic delay in samples, >= 0
    n = len(sig) + int(np.ceil(frac.max())) + 32
    nfft = 1 << int(np.ceil(np.log2(n)))
    S = np.fft.rfft(sig, nfft)
    k = np.arange(len(S))
    for m in range(out.shape[0]):
        y = np.fft.irfft(S * np.exp(-2j * np.pi * k * frac[m] / nfft), nfft)[:n] * gains[m]
        a, b = max(i0, 0), min(i0 + n, n_out)
        if b > a:
            out[m, a:b] += y[a - i0:b - i0]


def render_scene(frogs, duration_s, rng, call_fn, background_spl=cfg.BACKGROUND_SPL["typical"],
                 n_reflectors=4, reflect_gain=0.3, quantise=True,
                 mic_pos=cfg.MIC_POS, array_height=cfg.ARRAY_HEIGHT_M):
    """Return (4, N) pressure signals in pascals at the four mics.

    `call_fn(frog, rng)` returns a unit-RMS call waveform for that frog.
    """
    fs = cfg.FS
    n = int(duration_s * fs)
    out = np.zeros((len(mic_pos), n))
    mics = mic_pos + np.array([0, 0, array_height])

    for frog in frogs:
        src = frog.position()
        # Reflectors: random points within ~3 m of the frog (assumed foliage/trunks).
        refl = src + rng.normal(0, 1.5, size=(n_reflectors, 3)) * np.array([1, 1, 0.5])
        refl[:, 2] = np.clip(refl[:, 2], 0.2, None)
        for t0 in frog.call_times:
            call = call_fn(frog, rng) * cfg.spl_to_pa(frog.spl_at_1m)  # pressure at 1 m
            # Direct path
            r = np.linalg.norm(mics - src, axis=1)
            g = (1.0 / r) * 10 ** (-cfg.EXCESS_ATTEN_DB_PER_M * r / 20)
            _delay_into(out, call, t0, r / cfg.C_SOUND, g)
            # Foliage echoes
            for p in refl:
                r1 = np.linalg.norm(p - src)
                r2 = np.linalg.norm(mics - p, axis=1)
                rt = r1 + r2
                g = reflect_gain * rng.uniform(0.3, 1.0) / rt * 10 ** (-cfg.EXCESS_ATTEN_DB_PER_M * rt / 20)
                _delay_into(out, call, t0, rt / cfg.C_SOUND, g)

    # Diffuse background noise: 48 plane waves from random 3-D directions.
    if background_spl is not None:
        n_dirs = 48
        p_each = cfg.spl_to_pa(background_spl) / np.sqrt(n_dirs)
        nfft = 1 << int(np.ceil(np.log2(n + 64)))
        k = np.arange(nfft // 2 + 1)
        for _ in range(n_dirs):
            u = rng.normal(size=3)
            u /= np.linalg.norm(u)
            delays = -(mic_pos @ u) / cfg.C_SOUND * fs        # samples, plane wave
            delays -= delays.min()
            N = np.fft.rfft(coloured_noise(nfft, rng), nfft) * p_each
            for m in range(len(mic_pos)):
                out[m] += np.fft.irfft(N * np.exp(-2j * np.pi * k * delays[m] / nfft), nfft)[:n]

    # Microphone self-noise (independent per mic, white).
    out += rng.standard_normal(out.shape) * cfg.spl_to_pa(cfg.MIC_SELF_NOISE_SPL)

    if quantise:
        fs_pa = cfg.spl_to_pa(cfg.FULL_SCALE_SPL) * np.sqrt(2)   # peak pressure at 0 dBFS
        q = 2 ** (cfg.QUANT_BITS - 1)
        out = np.clip(np.round(out / fs_pa * q), -q, q - 1) / q * fs_pa
    return out
