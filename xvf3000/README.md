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
.venv/bin/python xvf3000/device/clap_test.py                     # angle calibration (your own Terminal)
.venv/bin/python xvf3000/device/listen.py --seconds 30           # record + find frogs
.venv/bin/python xvf3000/device/listen.py --wav xvf3000/samples/04_two_frogs_30deg.wav
```

Recordings go to `xvf3000/recordings/`, and the clap-test calibration to
`xvf3000/device/device_config.json`, so nothing mixes with the XVF3800 results.

## First things to check with the board

1. **Mic positions:** measure the distance between neighbouring mic holes. ~45 mm means the
   32 mm circle in `coqui_sim/config.py` is right.
2. **Which channel is which mic:** run `mic_check.py` and tap next to each mic in turn. Channels
   2-5 should jump one at a time, going round the board in order.
