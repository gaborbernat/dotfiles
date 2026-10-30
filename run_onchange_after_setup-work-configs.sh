#!/bin/bash
set -euo pipefail

if [[ -f "${HOME}/.local/share/chezmoi-private/uv.toml" ]]; then
    mkdir -p "${HOME}/.config/uv"
    ln -sf "${HOME}/.local/share/chezmoi-private/uv.toml" "${HOME}/.config/uv/uv.toml"
    echo "✅ Linked work uv.toml"
fi
