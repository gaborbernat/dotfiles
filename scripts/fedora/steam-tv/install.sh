#!/usr/bin/bash
# Installs the trigger that opens Steam Big Picture when an Xbox controller connects.
set -euo pipefail

(( EUID == 0 )) || { echo 'Run with sudo.' >&2; exit 1; }
cd "$(dirname "$0")"

install --mode=0755 steam-tv-trigger steam-tv lgtv-hdmi /usr/local/bin/
install --mode=0644 99-steam-tv.rules /etc/udev/rules.d/
install --mode=0644 steam-tv.service /etc/systemd/system/
install --mode=0644 steam-tv-user.service /etc/systemd/user/steam-tv.service
restorecon /usr/local/bin/steam-tv-trigger /usr/local/bin/steam-tv /usr/local/bin/lgtv-hdmi \
    /etc/udev/rules.d/99-steam-tv.rules \
    /etc/systemd/system/steam-tv.service /etc/systemd/user/steam-tv.service
systemctl daemon-reload
udevadm control --reload
echo 'Installed the controller trigger for Steam Big Picture.'
