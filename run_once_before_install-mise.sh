#!/bin/bash
set -euo pipefail

if command -v mise >/dev/null 2>&1; then
    echo "✅ mise already installed: $(mise --version)"
    exit 0
fi

echo "📦 Installing mise..."
curl -fsSL https://mise.run | sh
echo "✅ mise installed successfully"
