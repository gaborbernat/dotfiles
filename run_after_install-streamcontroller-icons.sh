#!/bin/bash
set -euo pipefail

if ! flatpak info com.core447.StreamController >/dev/null 2>&1; then
    exit 0
fi

icon_dir="$HOME/.local/share/streamcontroller-icons"
mkdir -p "$icon_dir"

icons=(
    fedora-logo-icon.png
    firefox.png
    com.mitchellh.ghostty.png
    org.gnome.Nautilus.svg
    org.gnome.SystemMonitor.svg
    org.gnome.Software.svg
    io.github.celluloid_player.Celluloid.svg
    steam.png
    com.obsproject.Studio.png
    app.bluebubbles.BlueBubbles.png
    rustdesk.png
    org.gnome.Connections.svg
    solaar.svg
    org.gnome.Settings.svg
    org.localsend.localsend_app.png
    io.github.seadve.Kooha.svg
)

for icon in "${icons[@]}"; do
    source=
    for root in "$HOME/.local/share/icons/hicolor" /usr/share/icons/hicolor \
        /var/lib/flatpak/exports/share/icons/hicolor "$HOME/.local/share/flatpak/exports/share/icons/hicolor"; do
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

music_icon=/usr/share/icons/Adwaita/scalable/places/folder-music.svg
if [[ -f "$music_icon" ]] && ! cmp -s "$music_icon" "$icon_dir/folder-music.svg"; then
    install -m 0644 "$music_icon" "$icon_dir/folder-music.svg"
fi

symbolic_icons=(
    'nav-home actions/go-home-symbolic.svg'
    'nav-back actions/go-previous-symbolic.svg'
    'nav-emoji emotes/face-smile-symbolic.svg'
    'capture devices/camera-photo-symbolic.svg'
    'volume-low status/audio-volume-low-symbolic.svg'
    'volume-high status/audio-volume-high-symbolic.svg'
    'volume-muted status/audio-volume-muted-symbolic.svg'
    'microphone-muted status/microphone-sensitivity-muted-symbolic.svg'
    'sound devices/audio-speakers-symbolic.svg'
)

temp_icon=$(mktemp "$icon_dir/.icon.XXXXXX")
trap 'rm -f "$temp_icon"' EXIT

for entry in "${symbolic_icons[@]}"; do
    read -r name icon <<<"$entry"
    source="/usr/share/icons/Adwaita/symbolic/$icon"
    if [[ ! -f "$source" ]]; then
        printf 'Stream Deck icon missing: %s\n' "$source" >&2
        continue
    fi

    sed -E 's/#[[:xdigit:]]{6}/#ffffff/g' "$source" >"$temp_icon"
    if ! cmp -s "$temp_icon" "$icon_dir/$name.svg"; then
        install -m 0644 "$temp_icon" "$icon_dir/$name.svg"
    fi
done
