#!/usr/bin/env bash
# Flash the XVF3800 with Seeed's 6-channel, 16 kHz USB firmware (raw mics on channels 3-6).
# Works on a Mac and on a Raspberry Pi.
# IMPORTANT: connect to the board's XMOS USB-C port (the one next to the 3.5 mm jack).
set -euo pipefail
cd "$(dirname "$0")/.."
SUDO=""; [ "$(uname)" = "Linux" ] && SUDO="sudo"

FW_DIR=vendor/respeaker/xmos_firmwares/usb
FW="$(ls "$FW_DIR"/respeaker_xvf3800_usb_dfu_firmware_v*_16k6ch.bin 2>/dev/null | sort -V | tail -1 || true)"
if [ -z "$FW" ]; then
    echo "No *_16k6ch.bin firmware found in $FW_DIR. Run the install script first."; exit 1
fi
echo "Firmware: $FW"
echo
echo "Looking for the board..."
if ! $SUDO dfu-util -l | grep -q "2886:001a"; then
    echo "XVF3800 not found. Check the cable is in the XMOS USB-C port (next to the 3.5 mm jack)."; exit 1
fi
$SUDO dfu-util -l | grep "2886:001a"
echo
read -r -p "Flash this firmware now? [y/N] " ok
[ "${ok:-n}" = "y" ] || { echo "Cancelled."; exit 0; }
$SUDO dfu-util -R -e -a 1 -D "$FW"
echo
echo "Done. The board restarts by itself. Wait ~5 s, then run: bash setup/configure_xvf.sh"
