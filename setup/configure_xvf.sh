#!/usr/bin/env bash
# Route the four raw microphones to USB channels 3-6 and save the setting to the board's flash.
# Needs the 6-channel firmware (setup/flash_firmware.sh). Works on a Mac and on a Raspberry Pi.
# Safe to run again at any time.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
HOST=vendor/respeaker/python_control/xvf_host.py
if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null; then
    # Help pyusb find Homebrew's libusb (needed on Apple-silicon Macs).
    export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
fi
xvf() { "$PY" "$HOST" "$@"; }

echo "== Firmware version and build =="
xvf VERSION
xvf BLD_MSG || true

echo "== Route raw mics (category 1 = microphones without gain or delay) to channels 3-6 =="
for i in 0 1 2 3; do
    ch=$((i + 3))
    xvf "AUDIO_MGR_OP_CH$ch" --values 1 "$i"
    xvf "AUDIO_MGR_OP_CH$ch"
done

echo "== Save to flash (survives power-off) =="
xvf SAVE_CONFIGURATION --values 1

echo "== Microphone positions reported by the board (x, y, z in metres, mic 0..3) =="
xvf AEC_MIC_ARRAY_GEO
echo "Compare these with MIC_POS in coqui_sim/config.py (they should match)."

echo "== Sound device =="
if [ "$(uname)" = "Darwin" ]; then
    "$PY" -c "import sounddevice as sd; [print(f\"  {d['name']}: {d['max_input_channels']} input channels\") for d in sd.query_devices() if 'respeaker' in d['name'].lower()]"
else
    arecord -l | grep -i -E "respeaker|xvf|array" || { echo "Sound card not listed. Replug the board."; exit 1; }
fi
echo
echo "Next: .venv/bin/python device/mic_check.py   (live levels for all 6 channels)"
