#!/bin/bash
set -euo pipefail

if [[ "${SKIP_SELECTED_FLATPAKS:-}" == 1 ]]; then
    exit 0
fi

apps=(
    org.localsend.localsend_app
    be.alexandervanhee.gradia
    com.vysp3r.ProtonPlus
    app.bluebubbles.BlueBubbles
    com.rustdesk.RustDesk
)
missing=()
for app in "${apps[@]}"; do
    if ! flatpak info --system "$app" >/dev/null 2>&1; then
        missing+=("$app")
    fi
done

if ((${#missing[@]} == 0)); then
    exit 0
fi

sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
sudo flatpak install --system -y flathub "${missing[@]}"
