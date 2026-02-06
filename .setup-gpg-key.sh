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

EMAIL=$(git config --global user.email 2>/dev/null || echo "")
NAME=$(git config --global user.name 2>/dev/null || echo "")

if [[ -z "$NAME" ]]; then
    read -rp "Enter your full name for git commits: " NAME </dev/tty
    if [[ -z "$NAME" ]]; then
        echo "Error: Name is required" >&2
        exit 1
    fi
    git config --global user.name "$NAME"
fi

if [[ -z "$EMAIL" ]]; then
    read -rp "Enter your email for git commits: " EMAIL </dev/tty
    if [[ -z "$EMAIL" ]]; then
        echo "Error: Email is required" >&2
        exit 1
    fi
    git config --global user.email "$EMAIL"
fi

gpg --batch --passphrase '' --quick-gen-key "$NAME <$EMAIL>" ed25519 sign never >&2

KEY_ID=$(gpg --list-secret-keys --keyid-format short 2>/dev/null | grep "^sec" | head -1 | grep -oE "[0-9A-F]{8,}")

if [[ -z "$KEY_ID" ]]; then
    echo "Error: Failed to create GPG key" >&2
    exit 1
fi

echo "Created GPG key: $KEY_ID" >&2

if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
    echo "Adding GPG key to GitHub..." >&2
    gpg --armor --export "$KEY_ID" | gh gpg-key add - >&2
    echo "GPG key added to GitHub" >&2
fi

gpg --list-secret-keys --keyid-format short
