#!/usr/bin/env bash
# One-time setup on a Mac. Run from the project folder:   bash setup/mac_install.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ "$(uname)" = "Darwin" ] || { echo "This script is for macOS. On a Raspberry Pi use setup/install.sh."; exit 1; }

echo "== 1/4 Homebrew tools (dfu-util for firmware, libusb for board control) =="
if ! command -v brew >/dev/null; then
    echo "Homebrew is needed. Install it from https://brew.sh (one command), then run this script again."
    exit 1
fi
brew install dfu-util libusb git

echo "== 2/4 Python environment (.venv) =="
command -v python3 >/dev/null || { echo "python3 not found: run  brew install python  and try again."; exit 1; }
python3 -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install numpy scipy matplotlib sounddevice pyusb libusb-package

echo "== 3/4 Seeed reSpeaker XVF3800 tools and firmware (vendor/respeaker) =="
if [ ! -d vendor/respeaker ]; then
    mkdir -p vendor
    git clone --depth 1 https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git vendor/respeaker
else
    echo "already present"
fi

echo "== 4/4 Check =="
.venv/bin/python - <<'EOF'
import numpy, scipy, sounddevice, usb.core
print("numpy", numpy.__version__, "| scipy", scipy.__version__, "| sounddevice and pyusb OK")
found = [d["name"] for d in sounddevice.query_devices() if "respeaker" in d["name"].lower()]
print("XVF3800 audio device:", found[0] if found else "not plugged in (that's fine for now)")
EOF
.venv/bin/python tests/test_pipeline.py

cat <<EOF

Mac setup done. Next steps (see README.md):
  1. Plug the XVF3800 into the Mac with the board's XMOS USB-C port (next to the 3.5 mm jack).
  2. bash setup/flash_firmware.sh      # one time: 6-channel firmware
  3. bash setup/configure_xvf.sh       # route raw mics to channels 3-6
  4. .venv/bin/python device/mic_check.py
EOF
