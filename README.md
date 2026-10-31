# Coqui Finder

Listen for (pretend) coqui frogs with a reSpeaker XVF3800 microphone array and report how many
males are calling, which direction each one is, and roughly how far away.

Start on a **Mac**: plug the board in, run the tools, change the code and test it, all on one
computer. Moving to a Raspberry Pi for a portable device comes later (see `README_PI.md`).

## What you need

- A Mac with macOS 13 or newer, and [Homebrew](https://brew.sh)
- reSpeaker XVF3800 and a USB-C cable (or a USB-C adapter if your Mac has only USB-A)

## Step 1: Install (one time, about 5 minutes)

Unzip the project, open **Terminal**, go to the folder and run the setup:

```bash
cd ~/Downloads/coqui_finder        # or wherever you unzipped it
bash setup/mac_install.sh
```

It installs the firmware tool (`dfu-util`), a Python environment with everything the code needs,
and Seeed's XVF3800 tools and firmware (in `vendor/respeaker`). It finishes by running the tests,
which should print `All tests passed`.

## Step 2: Flash the 6-channel firmware (one time)

Plug the XVF3800 into the Mac using the board's **XMOS USB-C port**, the one **next to the
3.5 mm headphone jack**, then:

```bash
bash setup/flash_firmware.sh
```

It finds the newest `*_16k6ch.bin` firmware, asks before flashing, and the board restarts by itself.

## Step 3: Send the raw microphones to channels 3–6 (one time)

```bash
bash setup/configure_xvf.sh
```

This routes microphones 0–3 to channels 3–6, saves the setting on the board, and shows the
firmware version, the board's microphone positions, and its 6 input channels.

## Step 4: Check the microphones

```bash
.venv/bin/python device/mic_check.py
```

The first time, macOS asks whether Terminal may use the microphone: click **Allow**. You'll see a
live level bar for all six channels. Talk or tap near the board: channels 3–6 should move. To find
which channel is which microphone, **tap gently next to one microphone at a time** and watch which
bar jumps. Ctrl+C to stop.

## Step 5: Check the software

```bash
.venv/bin/python tests/test_pipeline.py
.venv/bin/python device/listen.py --wav samples/04_two_frogs_30deg.wav
```

These use recordings made by the simulator, so they test the software without the board. The
second command should report 2 calling frogs.

## Step 6: Line up the angles with your chalk circle

Draw the chalk circle with 0° and 90° lines (see the experiment plan). Put the array in the middle
at about 1.2 m height, then:

```bash
.venv/bin/python device/clap_test.py
```

Clap at the 0° mark and then at the 90° mark, about 1 m from the array. The offset is saved to
`device/device_config.json`, so all results then match your chalk angles. Check other directions
any time with `--check`.

## Step 7: Listen

```bash
.venv/bin/python device/listen.py                        # listen 30 s, then report
.venv/bin/python device/listen.py --seconds 60 --loop    # keep going, one report per minute
```

Example report:

```
  2 calling frog(s):
    angle   range    est. distance   calls   level
       20°   medium      9.2 m          7    50.2 dB
       47°   far        15.5 m          7    45.0 dB
```

Every recording is saved in `recordings/` with a `.json` result beside it, so you can re-analyse
any trial later with `device/listen.py --wav recordings/<file>.wav`.

**Distance and level are rough until the board is calibrated.** The code assumes a microphone
sensitivity; measuring the real one with the calibration tone and a sound meter is a good first
project for Claude Code.

## Changing the code with Claude Code

Claude Code is Claude in the Mac's Terminal. It can read this project, run the tools, record from
the board, and change the code, asking permission before it runs commands or edits files.
Claude accounts are for adults, so a parent should run Claude Code, with the kids alongside
deciding what to try.

### Set up (one time)

```bash
curl -fsSL https://claude.ai/install.sh | bash      # or: brew install --cask claude-code
```

Open a new Terminal window, then:

```bash
cd ~/Downloads/coqui_finder
git init && git add -A && git commit -m "Starting point"    # so every change can be undone
claude                                                       # log in through your browser the first time
```

Claude Code needs a paid Claude plan (Pro, Max, Team or Enterprise) or a Claude Console account.
It automatically reads `CLAUDE.md` in this folder, which explains the project, the hardware, the
angle conventions and how to test.

### Example requests

```text
Run the tests and explain what the pipeline does, step by step, for a middle schooler.

Record 30 seconds while I play frog_01 at 2 m and tell me if the bearing is right.

Add a live mode to listen.py that reports every 5 seconds using a rolling 30-second buffer.

Help me calibrate the microphone level: I'll play the calibration tone at 71 dB, 1 m from the board.

The two frogs 15° apart are being counted as one. Use each call's pitch to separate them.

Draw a compass picture of the frogs found in the last recording.

Commit these changes with a clear message.
```

### Good habits

- Ask Claude to **run `tests/test_pipeline.py` after every change**.
- Keep good recordings from experiments in `samples/` with a `.truth.json` file; they become new tests.
- Commit working versions (`git commit`, or ask Claude to). `git diff` shows what changed, and you
  can always go back.
- Type `/clear` between unrelated tasks; `claude -c` continues your last conversation.
- Claude asks before running commands. Approve tests and recordings; think twice before approving
  firmware flashing or anything with `sudo`.

More: [Claude Code quickstart](https://code.claude.com/docs/en/quickstart) ·
[setup and requirements](https://code.claude.com/docs/en/setup)

## Troubleshooting (Mac)

| Problem | Try |
|---|---|
| Channels 3–6 completely silent | Allow microphone access: **System Settings → Privacy & Security → Microphone**, switch on Terminal, then quit and reopen Terminal |
| `XVF3800 not found, or it has fewer than 6 input channels` | Replug the board. If it shows only 2 channels, the 6-channel firmware isn't flashed yet (Step 2). **Audio MIDI Setup** (in Applications → Utilities) shows the board and its channel count |
| `flash_firmware.sh` can't find the board | Use the XMOS USB-C port next to the 3.5 mm jack; try without a USB hub |
| `configure_xvf.sh` says `No backend available` | Run `brew install libusb` and try again. Or use Seeed's ready-made tool: `vendor/respeaker/host_control/mac_arm64/xvf_host AUDIO_MGR_OP_CH3 1 0` (and so on); if macOS blocks it, right-click it in Finder and choose Open once |
| Channels 3–6 very quiet | Expected: raw mic data isn't amplified. Distant calls may be only a few hundred counts |

## What's in this folder

| Path | What it is |
|---|---|
| `setup/` | `mac_install.sh`, `flash_firmware.sh`, `configure_xvf.sh` (Mac and Pi), `install.sh` (Pi) |
| `device/` | Tools for the real board: `mic_check`, `clap_test`, `listen` |
| `coqui_sim/` | The core code: simulator, direction finding (SRP-PHAT), detection, counting, range |
| `tests/` | Regression test on the sample recordings |
| `samples/` | Simulated XVF3800 recordings with answer keys |
| `tools/pi.sh` | Later: copy code to a Raspberry Pi and run it there |
| `experiments.py`, `make_figures.py`, `export_samples.py`, `demo_scene.py`, `compare_arrays.py` | The simulation studies from the report |
| `CLAUDE.md` | Project briefing that Claude Code reads automatically |
| `README_PI.md` | Later: moving the device to a Raspberry Pi |
