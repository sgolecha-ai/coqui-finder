"""The device's processing chain, run on simulated (or real) 4-channel audio.

  detect calls  ->  bearing per call (SRP-PHAT)  ->  cluster bearings into frogs
                ->  count + range class per frog

The detector here is a simple band-energy detector, standing in for the trained
ML detector. It is deliberately basic: if the pipeline works with it, a trained
detector will only make detection better.
"""
import numpy as np

from . import config as cfg
from .doa import SrpPhat, ang_diff, peaks_on_circle, stft_channels


def detect_calls(Z, f, min_frames=3, thresh_db=6.0, max_gap_frames=3):
    """Return list of (first_frame, last_frame) segments with energy in the call band.

    Energy in BAND_HZ (averaged over mics) is compared with a running noise floor
    (20th percentile of the whole clip). A call is >= min_frames frames above
    floor + thresh_db.
    """
    band = (f >= cfg.BAND_HZ[0]) & (f <= cfg.BAND_HZ[1])
    e = np.mean(np.abs(Z[:, band, :]) ** 2, axis=(0, 1))
    e_db = 10 * np.log10(e + 1e-30)
    floor = np.percentile(e_db, 20)
    on = e_db > floor + thresh_db
    # Bridge short gaps so the "co" and "qui" notes form one call.
    idx = np.where(on)[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= max_gap_frames + 1:
            on[a:b] = True
    segs, start = [], None
    for i, v in enumerate(np.append(on, False)):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_frames:
                segs.append((start, i - 1))
            start = None
    return segs, e_db, floor


def band_level_spl(x_pa):
    """Level (dB SPL) of the call band in a short multichannel pressure clip."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, cfg.BAND_HZ, btype="band", fs=cfg.FS, output="sos")
    y = sosfiltfilt(sos, x_pa, axis=-1)
    return float(cfg.pa_to_spl(np.sqrt(np.mean(y ** 2))))


def estimate_distance(level_spl, call_duration_s=None):
    """Invert spreading + excess loss using the nominal source level (70.4 dB at 1 m)."""
    loss = cfg.CALL_SPL_AT_1M - level_spl
    d_grid = np.linspace(0.3, 80, 4000)
    model = 20 * np.log10(d_grid) + cfg.EXCESS_ATTEN_DB_PER_M * d_grid
    return float(d_grid[np.argmin(np.abs(model - loss))])


def range_class(d):
    return "near" if d < 5 else ("medium" if d <= 15 else "far")


def _distinct_events(times, min_gap_s=0.35):
    """Number of separate calls among bearing estimates (estimates closer than min_gap_s are one call)."""
    n, last = 0, -1e9
    for t in sorted(times):
        if t - last > min_gap_s:
            n, last = n + 1, t
    return n


def cluster_bearings(bearings, levels, times, min_calls=3, bandwidth_deg=6.0, min_sep_deg=20.0):
    """Group bearing estimates into frogs using a smoothed circular histogram.

    A frog is a peak supported by >= min_calls separate calls (real males call
    repeatedly; one-off echoes or noise bursts do not).
    Returns list of dicts: bearing, n_calls, level (median dB SPL).
    """
    if len(bearings) == 0:
        return []
    az = cfg.AZ_GRID_DEG
    b = np.asarray(bearings)
    k = np.exp(-0.5 * (ang_diff(az[:, None], b[None, :]) / bandwidth_deg) ** 2)
    density = k.sum(axis=1)
    frogs = []
    for idx in np.argsort(density)[::-1]:
        if density[idx] < min_calls * 0.5:
            break
        is_local = density[idx] >= density[(idx - 1) % 360] and density[idx] >= density[(idx + 1) % 360]
        if not is_local or any(ang_diff(az[idx], fr["bearing"]) < min_sep_deg for fr in frogs):
            continue
        members = ang_diff(b, az[idx]) < min_sep_deg / 2 + bandwidth_deg
        n_calls = _distinct_events(np.asarray(times)[members])
        if n_calls >= min_calls:
            frogs.append({
                "bearing": float(az[idx]),
                "n_calls": int(n_calls),
                "level": float(np.median(np.asarray(levels)[members])),
            })
    return frogs


def run_device(x_pa, srp=None, max_sources_per_call=2, max_call_frames=24, win_frames=6):
    """Full pipeline on a (4, N) pressure recording. Returns (frogs, per-estimate list).

    A detection no longer than one call (~0.38 s) gives one bearing (two if two
    frogs overlap). A longer detection means several calls ran together, so it is
    cut into ~100 ms slices, each giving its own bearing; at any instant one frog
    usually dominates.
    """
    srp = srp or SrpPhat()
    f, t, Z = stft_channels(x_pa)
    segs, _, _ = detect_calls(Z, f)
    maps = srp.frame_maps(Z)
    est = []
    for a, b in segs:
        if b - a + 1 <= max_call_frames:
            windows, n_max = [(a, b)], max_sources_per_call
        else:
            step = win_frames // 2
            windows = [(s, min(s + win_frames - 1, b)) for s in range(a, b - step + 1, step)]
            n_max = 1
        for w0, w1 in windows:
            m = maps[w0:w1 + 1].sum(axis=0)
            lvl = band_level_spl(x_pa[:, w0 * cfg.HOP: w1 * cfg.HOP + cfg.NFFT])
            for brg in peaks_on_circle(m, srp.az, n_max=n_max, min_sep_deg=20, rel_height=0.75):
                est.append({"t": float(t[w0]), "bearing": brg, "level": lvl})
    frogs = cluster_bearings([e["bearing"] for e in est], [e["level"] for e in est],
                             [e["t"] for e in est])
    for fr in frogs:
        fr["distance_est"] = estimate_distance(fr["level"])
        fr["range_class"] = range_class(fr["distance_est"])
    return frogs, est
