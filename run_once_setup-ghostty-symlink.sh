#!/bin/bash
set -euo pipefail
mkdir -p "$HOME/Library/Application Support/com.mitchellh.ghostty"
ln -sf "$HOME/.config/ghostty/config" "$HOME/Library/Application Support/com.mitchellh.ghostty/config"
