#!/usr/bin/env bash
# One-time setup on a Raspberry Pi (Raspberry Pi OS Bullseye or newer; 32-bit or 64-bit).
# Run from the project folder:   bash setup/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="$(pwd)"

echo "== 1/5 System packages (needs sudo) =="
sudo apt update
sudo apt install -y python3-numpy python3-scipy python3-matplotlib python3-venv python3-pip \
    alsa-utils sox dfu-util git libusb-1.0-0

echo "== 2/5 Python environment (.venv, uses the system numpy/scipy) =="
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install pyusb
# Seeed's control script imports libusb_package but only uses it on Windows.
if ! .venv/bin/pip install libusb-package; then
    echo "libusb-package not available; installing a small stand-in (fine on Linux)."
    SITE="$(.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')"
    printf 'import usb.core\ndef find(**kw):\n    return usb.core.find(**kw)\n' > "$SITE/libusb_package.py"
fi

echo "== 3/5 Seeed reSpeaker XVF3800 tools and firmware (vendor/respeaker) =="
if [ ! -d vendor/respeaker ]; then
    mkdir -p vendor
    git clone --depth 1 https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git vendor/respeaker
else
    echo "already present"
fi

echo "== 4/5 USB permission rule (lets the control script run without sudo) =="
sudo cp setup/99-respeaker-xvf3800.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG audio,plugdev "$USER" || true

echo "== 5/5 Check the Python pieces =="
.venv/bin/python - <<'EOF'
import numpy, scipy, usb.core
print("numpy", numpy.__version__, "| scipy", scipy.__version__, "| pyusb OK")
EOF

cat <<EOF

Setup done. Next steps (see README_PI.md):
  1. Unplug and replug the XVF3800 (so the USB rule applies).
  2. bash setup/flash_firmware.sh      # one time: 6-channel firmware
  3. bash setup/configure_xvf.sh       # route raw mics to channels 3-6
  4. .venv/bin/python device/mic_check.py
If you were just added to the 'audio' or 'plugdev' group, log out and back in first.
EOF
