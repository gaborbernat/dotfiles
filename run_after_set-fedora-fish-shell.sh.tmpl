#!/bin/bash
set -euo pipefail

if [[ "${SKIP_FEDORA_FISH_SHELL:-}" == 1 ]]; then
    exit 0
fi

fish=$(command -v fish)
if [[ "$(getent passwd "$(id -un)" | cut -d: -f7)" != "$fish" ]]; then
    sudo usermod --shell "$fish" "$(id -un)"
fi
