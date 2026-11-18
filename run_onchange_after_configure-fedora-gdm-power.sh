#!/bin/bash
set -euo pipefail

# Without anyone logged in, the login screen suspends after idle, which cuts off et and RustDesk.
printf '[org/gnome/settings-daemon/plugins/power]\nsleep-inactive-ac-type='"'"'nothing'"'"'\n' |
    sudo install -D -m 0644 /dev/stdin /etc/dconf/db/gdm.d/90-dotfiles-power
sudo dconf update
