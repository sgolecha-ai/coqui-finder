"""Direction finding on the four raw channels: SRP-PHAT over an azimuth grid.

SRP-PHAT sums phase-transform-weighted cross-spectra of all 6 mic pairs, steered
to each candidate azimuth. Using all pairs together is what suppresses the false
"aliased" directions the 93 mm diagonal pairs would give on their own above
~1.8 kHz.
"""
import numpy as np
from scipy.signal import stft

from . import config as cfg

PAIRS = [(i, j) for i in range(4) for j in range(i + 1, 4)]


def stft_channels(x):
    """(4, N) -> complex STFT (4, n_bins, n_frames) and frame times."""
    f, t, Z = stft(x, fs=cfg.FS, nperseg=cfg.NFFT, noverlap=cfg.NFFT - cfg.HOP,
                   window="hann", boundary=None, padded=False)
    return f, t, Z


class SrpPhat:
    def __init__(self, mic_pos=cfg.MIC_POS, az_grid=cfg.AZ_GRID_DEG, band=cfg.BAND_HZ):
        self.az = az_grid
        f = np.fft.rfftfreq(cfg.NFFT, 1 / cfg.FS)
        self.bins = np.where((f >= band[0]) & (f <= band[1]))[0]
        fb = f[self.bins]
        a = np.radians(az_grid)
        u = np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], axis=1)  # look directions
        # Far-field TDOA for each pair and direction: tau_ij = (p_j - p_i).u / c
        tau = np.stack([(mic_pos[j] - mic_pos[i]) @ u.T / cfg.C_SOUND for i, j in PAIRS])
        # steering[pair, az, bin]
        self.steer = np.exp(-2j * np.pi * tau[:, :, None] * fb[None, None, :])

    def frame_maps(self, Z):
        """SRP map per frame: (n_frames, n_az), range ~[-6, 6]."""
        X = Z[:, self.bins, :]                                   # (4, nb, nt)
        maps = 0
        for p, (i, j) in enumerate(PAIRS):
            cross = X[i] * np.conj(X[j])
            cross /= np.abs(cross) + 1e-20                       # PHAT weighting
            # cross ~ exp(-j2*pi*f*tau) for the true direction, so steer with the conjugate
            maps = maps + np.real(np.einsum("ab,bt->ta", np.conj(self.steer[p]), cross))
        return maps / len(self.bins)

    def bearing(self, Z):
        """Single bearing (deg) from a call's frames, plus the summed map."""
        m = self.frame_maps(Z).sum(axis=0)
        return float(self.az[np.argmax(m)]), m


def peaks_on_circle(m, az, n_max=2, min_sep_deg=15, rel_height=0.6):
    """Up to n_max peaks of a circular map, each >= rel_height of the top peak."""
    order = np.argsort(m)[::-1]
    found = []
    top = m[order[0]]
    lo = m.min()
    for idx in order:
        if (m[idx] - lo) < rel_height * (top - lo):
            break
        is_local = m[idx] >= m[(idx - 1) % len(m)] and m[idx] >= m[(idx + 1) % len(m)]
        if is_local and all(ang_diff(az[idx], az[k]) >= min_sep_deg for k in found):
            found.append(idx)
            if len(found) == n_max:
                break
    return [float(az[k]) for k in found]


def ang_diff(a, b):
    """Absolute angular difference in degrees, 0..180."""
    return np.abs((np.asarray(a) - np.asarray(b) + 180) % 360 - 180)
