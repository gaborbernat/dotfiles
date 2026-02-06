#!/bin/bash
set -euo pipefail

SDKMAN_BREW_DIR="$(brew --prefix sdkman-cli 2>/dev/null)/libexec" || true

if [[ -z "$SDKMAN_BREW_DIR" || ! -d "$SDKMAN_BREW_DIR" ]]; then
    echo "SDKMAN not installed via brew, skipping"
    exit 0
fi

export SDKMAN_DIR="$SDKMAN_BREW_DIR"
if [[ -s "${SDKMAN_DIR}/bin/sdkman-init.sh" ]]; then
    source "${SDKMAN_DIR}/bin/sdkman-init.sh"
    echo "SDKMAN initialized from brew: $(sdk version)"
else
    echo "SDKMAN init script not found"
fi
