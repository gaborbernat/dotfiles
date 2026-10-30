#!/bin/bash
set -euo pipefail

if [[ "${XDG_CURRENT_DESKTOP:-}" != *GNOME* ]] || ! command -v gsettings >/dev/null 2>&1; then
    exit 0
fi

if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && ! -S "${XDG_RUNTIME_DIR:-}/bus" ]]; then
    exit 0
fi

gsettings set org.gnome.desktop.interface monospace-font-name 'JetBrains Mono 11'
