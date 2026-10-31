# Later: moving Coqui Finder to a Raspberry Pi

Do this once everything works on the Mac (`README.md`). The Pi makes the device portable. You
keep editing the code on the Mac, and `tools/pi.sh` copies it to the Pi and runs it there.

## What you need

- Raspberry Pi 4 with Raspberry Pi OS **Bullseye or newer** (32-bit or 64-bit both work).
  Check on the Pi: `grep VERSION_CODENAME /etc/os-release` should say `bullseye`, `bookworm` or
  `trixie`, not `buster`.
- About 300 MB free (`df -h ~`), and internet access during setup
- SSH from the Mac to the Pi

The XVF3800 keeps its firmware and channel routing from the Mac setup, so there's no need to
flash or configure it again.

## Step 1: Password-free SSH from the Mac (one time)

On the Mac:

```bash
ls ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519      # make a key if you don't have one
ssh-copy-id <username>@raspberrypi.local               # type the Pi password one last time
ssh <username>@raspberrypi.local echo connected        # should print "connected" with no password
```

## Step 2: Copy the project to the Pi

On the Mac, in the project folder:

```bash
echo "<username>@raspberrypi.local" > .pi_host
tools/pi.sh push            # copies the code to ~/coqui_finder on the Pi
tools/pi.sh shell           # opens a terminal on the Pi, in that folder
```

## Step 3: Install on the Pi (one time, about 10 minutes)

In the Pi terminal:

```bash
bash setup/install.sh
```

It installs Python packages and recording tools, Seeed's tools, and a USB rule so the board can be
controlled without `sudo`. Log out and back in if it says you were added to a group.

## Step 4: Check it on the Pi

Plug the XVF3800 into the Pi, then in the Pi terminal:

```bash
.venv/bin/python device/mic_check.py         # channels 3-6 should move when you talk
.venv/bin/python tests/test_pipeline.py
.venv/bin/python device/clap_test.py         # the Pi needs its own angle calibration
```

## Everyday use from the Mac

```bash
tools/pi.sh push                 # copy the latest code to the Pi
tools/pi.sh test                 # push + run the regression test on the Pi
tools/pi.sh listen 30            # push + record 30 s on the Pi + analyse + pull recordings to the Mac
tools/pi.sh pull                 # fetch recordings/ from the Pi
tools/pi.sh run "arecord -l"     # run any command on the Pi
tools/pi.sh shell                # terminal on the Pi (for mic_check.py and clap_test.py)
```

Edit code **only on the Mac**: `tools/pi.sh push` overwrites the Pi's copy of the code (it leaves
the Pi's recordings, settings, Python environment and Seeed tools alone). Claude Code on the Mac can
use these commands too.

## Troubleshooting (Pi)

| Problem | Try |
|---|---|
| `XVF3800 sound card not found` | Replug the board; check `arecord -l` lists it |
| `configure_xvf.sh` says access denied | Replug the board after `install.sh`, or log out and back in |
| Channels 3–6 silent | Run `bash setup/configure_xvf.sh` on the Pi; Seeed also suggests checking the mixer: `amixer -c <card> contents` |
| `Recording failed` | Check `arecord -D plughw:<card>,0 --dump-hw-params` for supported formats; add one to `formats` in `device/device_config.json` |
| Another program is using the board | Close it; only one program can record from the board at a time |
