#!/bin/bash
set -euo pipefail

if command -v copilot >/dev/null 2>&1; then
    exit 0
fi

npm install --global --prefix "$HOME/.local" @github/copilot
