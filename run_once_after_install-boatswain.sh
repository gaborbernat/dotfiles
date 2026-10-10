#!/bin/bash
set -euo pipefail

if [[ "${SKIP_BOATSWAIN:-}" == 1 ]]; then
    exit 0
fi

# Boatswain is available on Flathub, not in Fedora 44's RPM repositories.
sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
sudo flatpak install --system -y flathub com.feaneron.Boatswain
