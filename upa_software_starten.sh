#!/bin/sh
# UPA-Software starten (Linux/macOS). Beispiel: ./upa_software_starten.sh --port /dev/ttyACM0
cd "$(dirname "$0")"
exec python3 upa_server.py "$@"
