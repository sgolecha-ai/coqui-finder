#!/usr/bin/env bash
# Run on your Mac. Copies code to the Pi, runs commands there, and fetches recordings back.
#
#   tools/pi.sh push                  copy code to the Pi (keeps the Pi's .venv, vendor, recordings, settings)
#   tools/pi.sh test                  push, then run the regression test on the Pi
#   tools/pi.sh listen [seconds]      push, record + analyse on the Pi, then pull the recordings
#   tools/pi.sh run "<command>"       run any command in the project folder on the Pi
#   tools/pi.sh shell                 open an interactive shell on the Pi (for mic_check / clap_test)
#   tools/pi.sh pull                  copy recordings (and the Pi's angle settings, kept separate) to the Mac
#
# Set the Pi address once:  echo "yourname@raspberrypi.local" > .pi_host
set -euo pipefail
cd "$(dirname "$0")/.."

PI="${PI_HOST:-$(cat .pi_host 2>/dev/null || true)}"
[ -n "$PI" ] || { echo 'Set the Pi address first:  echo "yourname@raspberrypi.local" > .pi_host'; exit 1; }
DIR="coqui_finder"

push() {
    rsync -a --delete \
        --exclude .git/ --exclude .venv/ --exclude vendor/ --exclude recordings/ \
        --exclude __pycache__/ --exclude results/ --exclude figures/ \
        --exclude .pi_host --exclude device/device_config.json --exclude device/device_config_pi.json \
        ./ "$PI:$DIR/"
    echo "Pushed code to $PI:$DIR"
}

pull() {
    mkdir -p recordings
    rsync -a "$PI:$DIR/recordings/" recordings/ 2>/dev/null || echo "(no recordings on the Pi yet)"
    rsync -a "$PI:$DIR/device/device_config.json" device/device_config_pi.json 2>/dev/null || true
    echo "Pulled recordings/ (and the Pi's angle settings as device/device_config_pi.json)"
}

remote() { ssh "$PI" "cd $DIR && $*"; }

case "${1:-}" in
    push)   push ;;
    pull)   pull ;;
    test)   push; remote ".venv/bin/python tests/test_pipeline.py" ;;
    listen) push; remote ".venv/bin/python device/listen.py --seconds ${2:-30}"; pull ;;
    run)    shift; remote "$*" ;;
    shell)  ssh -t "$PI" "cd $DIR && exec bash -l" ;;
    *)      sed -n '2,12p' "$0"; exit 1 ;;
esac
