#!/bin/bash
set -euo pipefail

if ! command -v flatpak >/dev/null 2>&1; then
    exit 0
fi

apps=$(flatpak list --app --columns=application,runtime)
while IFS=$'\t' read -r app runtime; do
    [[ "$runtime" == org.gnome.Platform/* ]] || continue
    for version in 3.0 4.0; do
        source="$HOME/.config/gtk-$version/gtk.css"
        target="$HOME/.var/app/$app/config/gtk-$version/gtk.css"
        if ! cmp -s "$source" "$target"; then
            install -D -m 0644 "$source" "$target"
        fi
    done
done <<<"$apps"
