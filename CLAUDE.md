# Coqui Finder: project briefing for Claude Code

## What this is

A middle-school science fair project. A reSpeaker XVF3800 four-microphone array, plugged into
this Mac (and later a Raspberry Pi), listens for coqui frog calls (an invasive frog in Hawaiʻi) and reports how many
males are calling, the direction of each, and a rough distance. There are no real frogs: phones
and laptops play coqui calls at measured angles and distances around the array. Students change
the code with a parent running Claude Code. Keep explanations and output friendly for middle
schoolers; keep the code simple and well commented, and explain changes in plain words.

## Where things run

- **Now: this Mac.** The XVF3800 is plugged into the Mac; code, tests, recordings and git all live
  here. Recording uses the `sounddevice` library (`device/common.py`). macOS must allow Terminal to
  use the microphone, or channels come back silent.
- **Later: a Raspberry Pi** (Raspberry Pi OS Bullseye or newer, 32- or 64-bit), set up with
  `README_PI.md`. Code is still edited only on the Mac; `tools/pi.sh` (address in `.pi_host`) does
  `push`, `test`, `listen [s]`, `pull`, `run "<cmd>"`, `shell`. On the Pi, recording falls back to `arecord`.
- `mic_check.py` and `clap_test.py` are interactive: ask the user to run them in their own terminal.
- Keep code compatible with the Pi's Python: **Python 3.9, numpy 1.19, scipy 1.6** (Bullseye apt
  versions). No `match`, no `X | Y` type hints, no newer numpy/scipy APIs.

## Hardware facts

- XVF3800 with Seeed's **6-channel 16 kHz USB firmware** (`*_16k6ch.bin`), recorded as
  6 channels, 16 kHz, int16 (S16_LE).
- Channels (1-based): 1–2 = XMOS voice-processed outputs (speech-tuned; **not used**),
  3–6 = raw mics 0–3 (routed by `setup/configure_xvf.sh` with `AUDIO_MGR_OP_CH3..6 = 1, 0..3`).
- Mic positions (`AEC_MIC_ARRAY_GEO`, metres): mic0 (+0.033, −0.033), mic1 (+0.033, +0.033),
  mic2 (−0.033, +0.033), mic3 (−0.033, −0.033); flat, so no elevation information.
  These are `MIC_POS` in `coqui_sim/config.py`. Don't change them without checking the board.
- Raw channels are un-amplified and quiet: distant calls can be only tens to hundreds of counts.
  `USB_BIT_DEPTH` (24/32-bit) is an option; it reboots the board and resets the routing.
- Board control: `.venv/bin/python vendor/respeaker/python_control/xvf_host.py <COMMAND> [--values ...]`.
  The board's built-in direction (`DOA_VALUE`, `AEC_AZIMUTH_VALUES`) is speech-tuned; we don't use it.

## Coqui call and physics

- Call: "co" ≈ 1.15 kHz (~100 ms), then "qui" sweeping up to ≈ 2.1 kHz (~150 ms). Hawaiian
  frogs' qui/co frequency ratio averages 1.81. Analysis band 0.9–2.5 kHz.
- Source level 70.4 dB SPL at 1 m (Benevides et al. 2019); −6 dB per doubling of distance.
- Test "frogs" play at 61 dB at 1 m = a real frog heard from 3 m, so real-frog distance = 3 × phone
  distance. Keeping the code's 70.4 dB assumption makes `listen.py` report the real-frog-equivalent distance.
- 66 mm spacing → max inter-mic delay 0.192 ms (adjacent) / 0.27 ms (diagonal) ≈ 3–4 samples,
  so directions come from phase (SRP-PHAT), not sample counting.

## Angle conventions

- `run_device()` returns raw `bearing` in degrees **counter-clockwise from the +x axis of the mic
  coordinates**.
- Students read angles off a chalk circle. `device/clap_test.py` stores `bearing_offset_deg` and
  `bearing_sign` in `device/device_config.json`; `device/common.py: to_chalk_angle()` converts.
  Always report chalk angles to the user, and keep raw bearings in code and tests.

## Code map

- `coqui_sim/config.py`: every constant, each labelled DOCUMENTED or ASSUMED.
- `coqui_sim/pipeline.py`: `run_device(x_pa)`: detect calls (band energy, a stand-in for an ML
  detector) → bearing per call (SRP-PHAT) → group bearings into frogs (≥3 calls, 20° minimum
  separation) → range class from loudness (near < 5 m, medium 5–15 m, far > 15 m).
- `coqui_sim/doa.py`: SRP-PHAT for the 4-mic array. `coqui_sim/xvf_format.py`: read/write the
  6-channel WAV layout (pressure scaling uses an ASSUMED 120 dB SPL full scale).
- `coqui_sim/acoustics.py`, `signals.py`: the simulator (frogs, propagation, echoes, noise).
- `device/`: `mic_check.py` (live levels), `clap_test.py` (angle calibration), `listen.py`
  (record + analyse; saves `recordings/*.wav` + `.json`), `common.py` (find card, record, angles).
- `tests/test_pipeline.py`: regression test on `samples/` (WAV + `.truth.json` answer keys).
- Root scripts (`experiments.py`, `make_figures.py`, `export_samples.py`, `demo_scene.py`,
  `compare_arrays.py`): simulation studies; slow, so don't run them unless asked.

## Commands

```bash
.venv/bin/python tests/test_pipeline.py                 # run after every change (no board needed)
.venv/bin/python device/listen.py --wav samples/04_two_frogs_30deg.wav
.venv/bin/python device/listen.py --seconds 30          # needs the board plugged in
.venv/bin/python device/listen.py --wav recordings/<file>.wav   # re-analyse a recording
.venv/bin/python -c "import sounddevice as sd; print(sd.query_devices())"   # is the board visible?
```

Later, on the Pi from the Mac: `tools/pi.sh test`, `tools/pi.sh listen 30`.

## Working rules

- Run `tests/test_pipeline.py` before and after changes. Don't loosen the tests to make them pass.
- Keep the pipeline usable on both WAV files and live audio; `run_device()` takes a `(4, N)`
  pressure array in pascals.
- When adding a recording from a real experiment as a test, save its `.truth.json` with chalk
  angles **and** raw bearings, distances, and which frog file each phone played.
- After code changes: run the tests (and `tools/pi.sh test` once the Pi is in use). Commit working versions.
- Ask before: `sudo` commands, flashing firmware, `SAVE_CONFIGURATION`/`CLEAR_CONFIGURATION`,
  `USB_BIT_DEPTH`, or deleting recordings.
- Label any new constant DOCUMENTED (with source) or ASSUMED in `config.py`.

## Roadmap (ideas, roughly in order)

1. Calibrate the mic level: calibration tone at 71 dB at 1 m → real full-scale value in `config.py`.
2. Live mode: rolling 30 s buffer, report every few seconds (keep the WAV path working).
3. Real coqui recordings (Xeno-canto, licences that allow changes) in place of the synthetic call.
4. Separate close frogs using each call's pitch and calling rhythm.
5. A trained coqui detector in place of the band-energy detector (keep greenhouse frogs as negatives).
6. Two-unit triangulation: two boards a few metres apart → frog positions on a map.
