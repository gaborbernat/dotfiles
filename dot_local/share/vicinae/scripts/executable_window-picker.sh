#!/bin/sh
# @vicinae.schemaVersion 1
# @vicinae.title Find Window by Monitor
# @vicinae.mode silent

set -eu

if ! response=$(busctl --user --json=short call org.gnome.Shell \
    /org/gnome/Shell/Extensions/FocusedSwitcher org.bernat.FocusedSwitcher ListWindows 2>&1); then
    notify-send 'Window picker unavailable' 'Log out and back in to load the updated GNOME extension.'
    exit 1
fi

windows=$(printf '%s\n' "$response" | jq -er '.data[0]')
labels=$(printf '%s\n' "$windows" | jq -r '
    .windows | sort_by(.monitor, .app, .title) | .[] |
    "\(.monitor) · \(.app) · \(.title | gsub("[\r\n]"; " ")) [#\(.id)]"
')
[ -n "$labels" ] || exit 0

if ! selection=$(printf '%s\n' "$labels" | vicinae dmenu \
    --navigation-title 'Windows by monitor' --placeholder 'Find a window' --format data); then
    exit 0
fi

id=$(printf '%s\n' "$selection" | sed -n 's/.* \[#\([0-9][0-9]*\)\]$/\1/p')
[ -n "$id" ] || exit 1
busctl --user call org.gnome.Shell /org/gnome/Shell/Extensions/FocusedSwitcher \
    org.bernat.FocusedSwitcher BringToCurrentMonitor u "$id"
