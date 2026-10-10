#!/bin/bash
set -euo pipefail

if [[ "${SKIP_FEDORA_GAMEMODE:-}" == "1" ]]; then
    exit 0
fi

user=$(id -un)
if ! id -nG "$user" | grep -qw gamemode; then
    sudo usermod -aG gamemode "$user"
    echo "Added $user to gamemode; log out and back in before using GameMode"
fi
