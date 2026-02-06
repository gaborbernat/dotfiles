#!/bin/bash
set -euo pipefail

if ! command -v rustup &>/dev/null; then
    echo "Installing rustup..."
    brew install rustup
fi

echo "Installing Rust stable toolchain..."
rustup default stable
rustup update stable
echo "Rust stable toolchain installed"
