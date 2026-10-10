#!/bin/bash
set -euo pipefail

if [[ "${SKIP_KOOHA:-}" == 1 ]]; then
    exit 0
fi

if flatpak info --system io.github.seadve.Kooha >/dev/null 2>&1; then
    exit 0
fi

sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
sudo flatpak install --system -y flathub io.github.seadve.Kooha
