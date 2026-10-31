"""Fixed facts and modelling assumptions for the Coqui Finder simulator.

Everything a reviewer might want to argue with lives here, labelled as either
MEASURED/DOCUMENTED (from a source) or ASSUMED (a placeholder to replace with
field data).
"""
import numpy as np

# --- Audio -------------------------------------------------------------------
FS = 16_000            # Hz. XVF3800 6-channel USB firmware (16k6ch) sample rate. DOCUMENTED.
C_SOUND = 343.0        # m/s, speed of sound at ~20 C.

# --- XVF3800 microphone geometry ---------------------------------------------
# DOCUMENTED: AEC_MIC_ARRAY_GEO on the reSpeaker XVF3800 returns
# [0.033,-0.033,0, 0.033,0.033,0, -0.033,0.033,0, -0.033,-0.033,0] (metres).
# Read it from your own board with `python xvf_host.py AEC_MIC_ARRAY_GEO`.
MIC_POS = np.array([
    [0.033, -0.033, 0.0],
    [0.033, 0.033, 0.0],
    [-0.033, 0.033, 0.0],
    [-0.033, -0.033, 0.0],
])
ARRAY_HEIGHT_M = 1.2   # ASSUMED: device held at chest height.

# --- Coqui call ----------------------------------------------------------------
# DOCUMENTED: average "co" note level 70.4 dB SPL at 1 m (Benevides et al. 2019).
CALL_SPL_AT_1M = 70.4
# ASSUMED: frog-to-frog and head-orientation spread of source level (dB, 1 sigma).
CALL_SPL_SPREAD_DB = 3.0
# ASSUMED: seconds between calls of one male (varies with temperature).
CALL_PERIOD_S = (1.5, 3.0)

# --- Environment -------------------------------------------------------------
# ASSUMED: extra loss in vegetation on top of spherical spreading (dB per metre).
EXCESS_ATTEN_DB_PER_M = 0.1
# ASSUMED: microphone self-noise expressed as equivalent SPL (typical MEMS, SNR ~64 dB).
MIC_SELF_NOISE_SPL = 30.0
# ASSUMED: background noise levels (broadband dB SPL) for quiet / typical / loud nights.
BACKGROUND_SPL = {"quiet": 40.0, "typical": 50.0, "loud": 60.0}

# --- Raw-channel quantisation (XVF3800 category-1 raw mics) -------------------
# ASSUMED: 16-bit samples, digital full scale ~120 dB SPL (typical MEMS acoustic overload).
QUANT_BITS = 16
FULL_SCALE_SPL = 120.0

# --- Processing --------------------------------------------------------------
NFFT = 512             # 32 ms frames at 16 kHz
HOP = 256
BAND_HZ = (900.0, 2500.0)   # analysis band covering "co" and "qui" notes
AZ_GRID_DEG = np.arange(0, 360, 1.0)

P_REF = 20e-6          # Pa, reference pressure for dB SPL


def spl_to_pa(spl_db):
    """RMS pressure in pascals for a level in dB SPL."""
    return P_REF * 10 ** (spl_db / 20.0)


def pa_to_spl(p_rms):
    return 20 * np.log10(np.maximum(p_rms, 1e-12) / P_REF)
