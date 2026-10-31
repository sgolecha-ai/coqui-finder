# Frog test: find the pretend frogs

Do this **after** [CALIBRATION.md](CALIBRATION.md) (clap test and loudness test), with the board
in the same spot and pointing the same way (use the sticker).

## The frog files

In `xvf3000/frogs/` (made by `xvf3000/make_frog_files.py`):

| File | What it is |
|---|---|
| `frog_A.wav` | Pretend male A: lower voice ("co" 1092 Hz), calls about every 1.8 s |
| `frog_B.wav` | Male B: middle voice (1150 Hz), about every 2.4 s |
| `frog_C.wav` | Male C: higher voice (1208 Hz), fast caller, about every 1.6 s |
| `frog_D.wav` | Male D: (1127 Hz), slow caller, about every 2.7 s |
| `set_volume.wav` | The call over and over with no pauses, **exactly as loud as the frog calls**. Only for setting the volume |
| `frogs.json` | Each frog's pitch and the exact time of every call (for answer keys) |

Each frog file is 60 seconds: turn on **repeat** in the phone's player, or press play again.

## Step 1: Set each phone's volume to 61 dB at 1 m

Real coqui are about 70 dB at 1 m. Our phones play **61 dB at 1 m**, which is exactly how loud a
real frog sounds from **3 m away**. So a phone 1 m from the board acts like a real frog 3 m away,
and the Coqui Finder's distances are **real-frog distances = 3 × the phone's distance**.

For each phone:
1. Copy all the files to the phone (AirDrop to the Files app, or email).
2. Hold the meter phone **1 m** in front of the frog phone's speaker. Meter on **A-weighting**,
   **slow**.
3. Play `set_volume.wav` and change the volume until the meter reads **61 dB**.
4. **Don't touch the volume again.** Stick a note on the phone: "volume set, don't change!"

The room needs to be quiet: with nothing playing, the meter should read **below 50 dB**.

## Step 2: Put the phones on the chalk circle

- Phones at the **same height** as the board, **speaker pointing at the board**.
- Write down for each phone: **which frog file**, **chalk angle**, **distance** from the board.
- Keep frogs **at least 30° apart**. Closer than 20°, the Coqui Finder counts them as one frog
  (it needs more time and smarter code to split them).

## Step 3: Listen

Start the frog files playing, then:

```bash
.venv/bin/python xvf3000/device/listen.py --seconds 30
```

It records 30 seconds, then prints something like:

```
  3 calling frog(s):
    angle   range    est. distance   calls   level
       20°   near        3.1 m         17    60.4 dB
      110°   near        4.6 m         10    56.6 dB
      200°   medium      5.8 m         14    54.6 dB
```

- **angle** = the chalk angle the frog is calling from
- **est. distance** = the real-frog distance (should be about 3 × the phone's distance)
- **range** = near (under 5 m), medium (5 to 15 m) or far (over 15 m)
- **calls** = how many of its calls were heard. A frog needs at least 3 to count.

Ignore the line "Distance and level are rough until the board is calibrated": you've done that.

Every run is saved in `xvf3000/recordings/` (a `.wav` and a `.json` with the answers). Use
`--loop` to keep listening with a new report every 30 s.

## Suggested experiments

Start simple and add frogs one at a time, so you can see when things go wrong:

1. **One frog** (`frog_A`) at 1 m, 0°. Then move it to 90°, 180°, 270°. Is the angle right?
2. **One frog at different distances:** 0.5 m, 1 m, 2 m, 3 m. Is the distance about 3 × the
   phone distance?
3. **Two frogs** far apart (90° or more), then closer: 60°, 45°, 30°, 20°. When does it see only
   one?
4. **Three frogs**, then **four**.

Results table to copy:

| Trial | Phone(s): file, angle, distance | Frogs found | Angles found | Distances found |
|---|---|---|---|---|
| 1 | frog_A, 0°, 1 m | | | |

## What we expect (from the simulator)

With 4 phones at 1, 1.5, 2 and 3 m, the simulator found every frog within about 10° and within
about 20% of the right distance. **But it also reported a 5th, "ghost" frog** with only 3 or 4
calls. That's because with 4 frogs calling every 2 seconds, more than half the calls overlap
another frog's call, and when two frogs call at the same moment the direction can land in
between them. With the overlapping calls taken out, it found exactly 4.

So with 3 or 4 phones, expect the occasional ghost frog with few calls. Real frog choruses have
the same problem; fixing it (using each frog's pitch and rhythm) is a great next project.

## After an experiment

To turn a good recording into a new test, tell Claude which recording it was and where each
phone was (file, chalk angle, distance). It saves an answer key next to it so the code is checked
against real data from then on.
