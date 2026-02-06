#!/bin/bash
set -euo pipefail

if ! command -v rustup &>/dev/null; then
    echo "rustup not found, skipping"
    exit 0
fi

echo "Installing Rust stable toolchain..."
rustup default stable
rustup update stable
echo "Rust stable toolchain installed"
