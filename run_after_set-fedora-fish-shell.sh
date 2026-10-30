#!/bin/bash
set -euo pipefail

if [[ "${SKIP_FEDORA_FISH_SHELL:-}" == 1 ]]; then
    exit 0
fi

fish=$(command -v fish)
user=$(id -un)
shell=$(getent passwd "${user}" | cut -d: -f7 || true)
if [[ "${shell}" != "${fish}" ]]; then
    sudo usermod --shell "${fish}" "${user}"
fi
