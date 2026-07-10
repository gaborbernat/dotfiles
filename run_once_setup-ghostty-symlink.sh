#!/bin/bash
set -euo pipefail
target="$HOME/Library/Application Support/com.mitchellh.ghostty/config"
mkdir -p "$(dirname "$target")"
# Preserve a real (non-symlink) config that predates chezmoi rather than clobbering it.
if [ -e "$target" ] && [ ! -L "$target" ]; then
  mv "$target" "$target.pre-chezmoi.bak"
fi
ln -sf "$HOME/.config/ghostty/config" "$target"
