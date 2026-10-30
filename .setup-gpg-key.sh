#!/bin/bash
set -euo pipefail

if ! command -v gpg &>/dev/null; then
    echo "gpg not found, installing via brew..." >&2
    if ! command -v brew &>/dev/null; then
        echo "Error: brew not installed. Install Homebrew first." >&2
        exit 1
    fi
    brew install gnupg >&2
fi

if gpg --list-secret-keys --keyid-format short 2>/dev/null | grep -q "^sec"; then
    gpg --list-secret-keys --keyid-format short
    exit 0
fi

name=$(git config --global user.name 2>/dev/null || true)
if [[ -z "$name" ]]; then
    read -rp "Enter your full name for git commits: " name </dev/tty
    if [[ -z "$name" ]]; then
        echo "Error: Name is required" >&2
        exit 1
    fi
    git config --global user.name "$name"
fi

email=$(git config --global user.email 2>/dev/null || true)
if [[ -z "$email" ]]; then
    read -rp "Enter your email for git commits: " email </dev/tty
    if [[ -z "$email" ]]; then
        echo "Error: Email is required" >&2
        exit 1
    fi
    git config --global user.email "$email"
fi

gpg --batch --passphrase '' --quick-gen-key "$name <$email>" ed25519 sign never >&2

key_id=$(gpg --list-secret-keys --keyid-format short 2>/dev/null | grep "^sec" | head -1 | grep -oE "[0-9A-F]{8,}")
if [[ -z "$key_id" ]]; then
    echo "Error: Failed to create GPG key" >&2
    exit 1
fi

echo "Created GPG key: $key_id" >&2

if command -v gh &>/dev/null && gh auth status &>/dev/null; then
    echo "Adding GPG key to GitHub..." >&2
    gpg --armor --export "$key_id" | gh gpg-key add - >&2
    echo "GPG key added to GitHub" >&2
fi

gpg --list-secret-keys --keyid-format short
