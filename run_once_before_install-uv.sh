#!/bin/bash
set -euo pipefail

if command -v uv >/dev/null 2>&1; then
    echo "✅ uv already installed: $(uv --version)"
    exit 0
fi

echo "📦 Installing uv..."

if [[ -f "$HOME/.local/share/chezmoi-private/uv_install.sh" ]]; then
    source "$HOME/.local/share/chezmoi-private/uv_install.sh"
else
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "✅ uv installed successfully"
