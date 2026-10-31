"""Read/write audio in the reSpeaker XVF3800 6-channel USB layout.

What the board sends with the 16k6ch firmware (as `arecord -c 6 -r 16000 -f S16_LE`):
  channel 1 (index 0): processed output (AEC/beamformer/AGC) - XMOS proprietary
  channel 2 (index 1): second processed output
  channels 3-6 (index 2-5): raw microphones 0-3, routed with AUDIO_MGR_OP_CH3..6 = (1, 0..3)

The simulator cannot reproduce the XMOS voice processing, so channels 1-2 are
written as silence. Our pipeline only uses channels 3-6.

Scaling: digital full scale (int16 = 32767) = FULL_SCALE_SPL peak (ASSUMED 120 dB
SPL, typical for MEMS mics). Replace with the board's measured sensitivity.
"""
import numpy as np
from scipy.io import wavfile

from . import config as cfg

RAW_CHANNELS = [2, 3, 4, 5]          # 0-based indexes of mics 0-3 in the 6-ch file


def _pa_per_count():
    return cfg.spl_to_pa(cfg.FULL_SCALE_SPL) * np.sqrt(2) / 32768.0


def write_xvf_wav(path, mics_pa, processed=None):
    """mics_pa: (4, N) pressure in Pa -> 6-channel int16 WAV at 16 kHz."""
    n = mics_pa.shape[1]
    out = np.zeros((n, 6), dtype=np.int16)
    raw = np.round(mics_pa / _pa_per_count())
    out[:, 2:6] = np.clip(raw, -32768, 32767).T.astype(np.int16)
    if processed is not None:
        out[:, 0:2] = processed
    wavfile.write(path, cfg.FS, out)


def read_xvf_wav(path):
    """6-channel XVF3800 WAV (simulated or real) -> (4, N) pressure in Pa from channels 3-6."""
    fs, x = wavfile.read(path)
    if fs != cfg.FS:
        raise ValueError(f"expected {cfg.FS} Hz, got {fs} Hz")
    if x.ndim != 2 or x.shape[1] != 6:
        raise ValueError(f"expected 6 channels, got shape {x.shape}")
    if x.dtype == np.int16:
        counts = x[:, RAW_CHANNELS].astype(float)
    elif x.dtype == np.int32:                      # if recorded as S32_LE
        counts = x[:, RAW_CHANNELS].astype(float) / 65536.0
    else:                                          # float WAV in [-1, 1]
        counts = x[:, RAW_CHANNELS].astype(float) * 32768.0
    return (counts * _pa_per_count()).T
