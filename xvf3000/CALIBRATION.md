# Calibration day: the clap test and the loudness test

Two calibrations make the Coqui Finder's answers match the real world:

| Test | What it fixes | Without it |
|---|---|---|
| **Clap test** | **Direction**: lines the device's angles up with your chalk circle | Angles are correct relative to each other, but rotated (and maybe mirrored) compared with your chalk marks |
| **Loudness test** | **Distance**: teaches the code how loud the board's numbers really are | Every distance could be 2, 4 or more times too near or too far |

Counting frogs and detecting calls work without either test.

All commands are typed in **Terminal**, in the project folder. The scripts ask you questions,
so run them in your own Terminal window, not through Claude.

## What you need

- The board plugged into the Mac, and the tap test done (`tap_view.py`: the red light goes round
  the picture when you tap round the board)
- Chalk (or masking tape on the floor), a tape measure, and a small sticker
- **Phone A** to play the calibration sound
- **Phone B** with a sound level meter app, for example **NIOSH SLM** (free, iPhone) or
  **Sound Meter** (Android)
- A notebook for the results
- A quiet place: no fans, TV or traffic noise, and everyone quiet during recordings

---

## Part 1: The clap test (direction)

### What it does

When you press Enter, the script records **4 seconds** from the board's 4 raw microphones while
you clap 3 times. Then it:

1. **Finds the claps.** It chops the recording into about 250 short slices (32 ms each) and keeps
   the loudest 3%, which are your claps. If the claps aren't at least 10 dB louder than the rest,
   it asks you to clap again.
2. **Works out the direction.** For each clap slice it tries **360 directions, 1° apart**, and
   asks: "If the sound came from here, it would reach each mic a tiny bit earlier or later than
   the others. Do the 4 mics agree?" The direction where they agree best wins. (The time
   differences are less than 0.2 thousandths of a second! The method is called **SRP-PHAT**.)
3. **Gives one number: the raw bearing**, the direction in the code's own coordinates. It won't
   be 0° even if you clapped at your 0° mark, and that's fine.

You do this at the **0° mark** and then at the **90° mark**. From the two raw bearings it works
out:

- **The offset:** the raw bearing that means "your 0° mark".
- **The direction:** do your chalk numbers go the same way round as the code's, or the
  opposite way?

It saves these 2 numbers to `xvf3000/device/device_config.json`. From then on every tool
converts its answers into **chalk angles**: `chalk angle = sign × (raw bearing − offset)`.
The recordings themselves are not kept.

### Set up the chalk circle

1. Put the board in the middle of a clear space, **flat**, at the height you'll use for the frog
   tests. Keep big objects (walls, boxes) at least 1 m away if you can.
2. Draw a circle **1 m from the board** (a 2 m wide circle). Tie chalk to a 1 m string, or measure
   1 m in several directions.
3. Mark **0°, 45°, 90°, 135°, 180°, 225°, 270° and 315°** around the circle. Pick which way the
   numbers go (clockwise or anticlockwise) and stick with it; the script works out which you
   chose.
4. Put a **sticker on the board pointing at 0°**. If the board gets turned, the calibration is
   wrong, so you can use the sticker to put it back the same way.

### Run it

```bash
.venv/bin/python xvf3000/device/clap_test.py
```

1. Stand on the **0° mark**. Press Enter, then **clap 3 times**, about 1 second apart. It prints
   the raw bearing.
2. Stand on the **90° mark**, press Enter and clap 3 times again.
3. It prints what it saved and checks itself: the 0° mark should come out as 0° and the 90° mark
   as 90°.

If it warns that the claps are not about 90° apart, check you stood on the right marks and try
again somewhere quieter.

### Measure how accurate it is (science fair data!)

```bash
.venv/bin/python xvf3000/device/clap_test.py --check
```

Clap 3 times at each mark (press Enter each time) and write down what it says. Ctrl+C stops it.
Do every mark at least twice.

| Real angle (chalk mark) | Reported angle, try 1 | Try 2 | Error (reported − real) |
|---|---|---|---|
| 0° | | | |
| 45° | | | |
| 90° | | | |
| 135° | | | |
| 180° | | | |
| 225° | | | |
| 270° | | | |
| 315° | | | |

Ideas to try: clap from 2 m away instead of 1 m; clap quietly; turn on a fan. Which makes the
error bigger?

---

## Part 2: The loudness test (distance)

### Why it's needed

The Coqui Finder guesses distance from **how loud** a call is. A coqui is about **70.4 dB at
1 m**, and sound gets **6 dB quieter every time the distance doubles**. So if a call arrives at
58.4 dB (12 dB quieter, two doublings), the frog is about 4 m away.

But the board doesn't measure dB; it gives **numbers ("counts")**. The code turns counts into dB
using one setting, `FULL_SCALE_SPL` in `xvf3000/coqui_sim/config.py`, which is just a guess
(120 dB) until you measure it. If the guess is 6 dB wrong, every distance is 2 times wrong; if
it's 12 dB wrong, 4 times wrong.

### What it does

1. **Room check (5 s):** records the room with the sound off, to make sure the calibration sound
   will be at least 10 dB louder than the background.
2. **Sound on (10 s):** records the calibration sound, a steady hiss covering the coqui's notes
   (0.9–2.5 kHz). A hiss is used instead of a beep because a beep's loudness changes a lot when
   you move a few centimetres (echoes add up or cancel out).
3. **You type the meter reading:** what the sound level meter next to the board showed.
4. **It compares.** It measures the same hiss with its current guess. The difference between its
   number and the meter's number is **how wrong the guess is**, so it corrects
   `FULL_SCALE_SPL` by exactly that much. It also shows each mic's level: they should agree
   within about 3 dB.
5. **It asks before saving.** If you type `y`, it writes the new value into `config.py`, with
   the date and meter reading as a note.

### Set up

1. **Get the calibration sound onto Phone A:** the file is
   `xvf3000/calibration/calibration_sound.wav` (60 seconds). AirDrop it to an iPhone and open it
   from the Files app, or email it to yourself. Turn off "loop" or play it again if it stops.
2. Put **Phone A 1 m from the board**, at the **same height**, with its **speaker pointing at the
   board**, and nothing in between.
3. Put **Phone B (the meter) right next to the board**, with its microphone (the bottom edge of
   most phones) as close to the board's mics as you can without covering any mic hole.
4. Set the meter app to **A-weighting ("dBA")** and **slow** response if it has those options. If
   it shows an **average** (sometimes called **LAeq**), use that.
5. Play the sound and turn Phone A's volume up until the meter reads **about 70 dB**. The exact
   number doesn't matter, as long as it's well above the room (at least 15 dB more than the
   meter shows with the sound off).

### Run it

```bash
.venv/bin/python xvf3000/device/loudness_cal.py
```

1. **Sound off, everyone quiet.** Press Enter: it records 5 seconds.
2. **Start the sound on Phone A.** Press Enter: it records 10 seconds. **Watch the meter** while
   it records and remember the typical number (or reset the average just before and read it
   after).
3. **Type the meter's number**, for example `71.5`, and press Enter.
4. Read the report. If it looks sensible, type **`y`** to save.
5. **Run it again** without moving anything. This time it should say the guess is off by about
   **0 dB**. That proves it worked.

| Try | Meter (dB) | Code measured (dB) | Off by (dB) | New FULL_SCALE_SPL |
|---|---|---|---|---|
| 1 | | | | |
| 2 (check) | | | | |

### If something looks wrong

| Message or problem | What to do |
|---|---|
| "The sound is only N dB louder than the room" | Turn Phone A up, or find a quieter place |
| "The mics disagree by more than 3 dB" | Check Phone A is 1 m away, pointing at the board, nothing in between |
| The meter number jumps around | Use the app's average (LAeq), or the middle of the range you saw |
| "Off by" more than 20 dB | Something is wrong: check the meter reads dB (not dBFS), and the right phone is playing |

Phone meter apps are usually accurate to about ±2 dB, which is good enough here: 2 dB changes a
distance by about 25%.

---

## After calibration

- Ask Claude to **commit** the two files that changed: `xvf3000/device/device_config.json`
  (angles) and `xvf3000/coqui_sim/config.py` (loudness).
- Keep the **board in the same position** (use the sticker) for the frog experiments.
- Next: find the pretend frogs with [FROG_TEST.md](FROG_TEST.md).
