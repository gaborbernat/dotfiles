#!/bin/bash
set -euo pipefail

if ! flatpak info com.core447.StreamController >/dev/null 2>&1; then
    exit 0
fi

icon_dir="$HOME/.local/share/streamcontroller-icons"
mkdir -p "$icon_dir"

icons=(
    firefox.png
    com.mitchellh.ghostty.png
    org.gnome.Nautilus.svg
    steam.png
    com.obsproject.Studio.png
    app.bluebubbles.BlueBubbles.png
    com.rustdesk.RustDesk.png
    org.gnome.Connections.svg
    solaar.svg
    org.gnome.Settings.svg
    org.localsend.localsend_app.png
    io.github.seadve.Kooha.svg
)

for icon in "${icons[@]}"; do
    source=
    for root in /usr/share/icons/hicolor /var/lib/flatpak/exports/share/icons/hicolor \
        "$HOME/.local/share/flatpak/exports/share/icons/hicolor"; do
        for size in 128x128 256x256 512x512 scalable; do
            candidate="$root/$size/apps/$icon"
            if [[ -f "$candidate" ]]; then
                source="$candidate"
                break 2
            fi
        done
    done

    if [[ -z "$source" ]]; then
        printf 'Stream Deck icon missing: %s\n' "$icon" >&2
        continue
    fi

    if ! cmp -s "$source" "$icon_dir/$icon"; then
        install -m 0644 "$source" "$icon_dir/$icon"
    fi
done
