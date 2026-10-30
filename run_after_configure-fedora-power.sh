#!/bin/bash
set -euo pipefail

if [[ "${XDG_CURRENT_DESKTOP:-}" != *GNOME* ]] || ! command -v gsettings >/dev/null 2>&1; then
    exit 0
fi
if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && ! -S "${XDG_RUNTIME_DIR:-}/bus" ]]; then
    exit 0
fi

gsettings set org.gnome.desktop.session idle-delay 300
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
