#!/bin/bash
set -euo pipefail

if [[ -x "$HOME/.local/bin/uv" ]]; then
    echo "✅ uv already installed: $("$HOME/.local/bin/uv" --version)"
    exit 0
fi

echo "📦 Installing uv..."

if [[ -f "$HOME/.local/share/chezmoi-private/uv_install.sh" ]]; then
    source "$HOME/.local/share/chezmoi-private/uv_install.sh"
else
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
fi

echo "✅ uv installed successfully"
