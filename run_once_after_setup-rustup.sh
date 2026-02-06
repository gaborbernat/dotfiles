#!/bin/bash
set -euo pipefail

if ! command -v rustup &>/dev/null; then
    echo "Installing rustup..."
    if command -v brew &>/dev/null; then
        brew install rustup
    else
        curl https://sh.rustup.rs -sSf | sh -s -- -y --no-modify-path
    fi
fi

echo "Installing Rust stable toolchain..."
rustup default stable
rustup update stable
echo "Rust stable toolchain installed"
