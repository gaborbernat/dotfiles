#!/bin/bash
set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

if ! command -v rustup &>/dev/null; then
    echo "Installing rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
fi

echo "Installing Rust stable toolchain..."
rustup default stable
rustup update stable
echo "✅ Rust stable toolchain installed"
