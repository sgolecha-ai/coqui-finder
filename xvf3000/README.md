# Coqui Finder for the XVF3000 board (temporary)

A copy of the working code, changed for the **ReSpeaker USB Mic Array v2.0** (XVF3000 chip,
micro-USB, USB ID `2886:0018`), so we can try the whole thing end to end while we wait for the
XVF3800. When the XVF3800 arrives, go back to the code in the main folder; this folder can then
be deleted.

## What's different from the XVF3800 code

| | XVF3000 (this folder) | XVF3800 (main folder) |
|---|---|---|
| Raw microphones | channels 2-5 | channels 3-6 |
| Other channels | 1 = processed, 6 = playback | 1-2 = processed |
| Mic positions | 45 mm square, 32 mm from the centre (MEASURED) | 66 mm square (DOCUMENTED) |
| Setup | none: works out of the box | flash firmware + `configure_xvf.sh` |

**Don't run `setup/flash_firmware.sh` or `setup/configure_xvf.sh` with this board.** They are
for the XVF3800 only.

The test recordings in `samples/` were made again with the XVF3000 mic positions.

## Commands (run from the main project folder)

```bash
.venv/bin/python xvf3000/tests/test_pipeline.py                  # run after every change
.venv/bin/python xvf3000/device/mic_check.py                     # live levels (your own Terminal)
.venv/bin/python xvf3000/device/tap_view.py                      # tap picture: which mic is loudest (your own Terminal)
.venv/bin/python xvf3000/device/tap_test.py                      # the same check as text, one hole at a time
.venv/bin/python xvf3000/device/clap_test.py                     # angle calibration (your own Terminal)
.venv/bin/python xvf3000/device/loudness_cal.py                  # loudness calibration (your own Terminal)
.venv/bin/python xvf3000/device/listen.py --seconds 30           # record + find frogs
.venv/bin/python xvf3000/device/listen.py --wav xvf3000/samples/04_two_frogs_30deg.wav
```

Recordings go to `xvf3000/recordings/`, and the clap-test calibration to
`xvf3000/device/device_config.json`, so nothing mixes with the XVF3800 results.

## First things to check with the board

1. **Mic positions:** measured: the 4 mic holes form a square with ~45 mm sides, which matches
   the 32 mm circle in `coqui_sim/config.py`.
2. **Which channel is which mic:** run `tap_view.py`. A window shows the 4 mics. Tap next to
   one mic hole: the mic that heard it loudest lights up red and stays lit until the next tap,
   with every mic's level written next to it. Tap the holes going round the board; after 4
   different mics it says whether they go round in order. (`--demo` shows pretend taps.)
   (Channel 1 also jumps when you tap: it's the board's processed mix of all 4 mics. Ignore it.)
3. **Calibration (clap test + loudness test):** follow [CALIBRATION.md](CALIBRATION.md).
4. **Find the pretend frogs:** follow [FROG_TEST.md](FROG_TEST.md) (phones play `frogs/frog_A.wav` etc.).
