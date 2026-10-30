#!/bin/bash
set -euo pipefail

if ! distrobox list | grep -Eq '^[[:xdigit:]]+[[:space:]]*\|[[:space:]]*claude-desktop[[:space:]]*\|'; then
    if ! distrobox create --name claude-desktop --image docker.io/library/debian:13 \
        --additional-packages 'curl ca-certificates gnupg' --yes; then
        distrobox list | grep -Eq '^[[:xdigit:]]+[[:space:]]*\|[[:space:]]*claude-desktop[[:space:]]*\|'
    fi
fi

ready=false
for ((attempt = 0; attempt < 60; attempt++)); do
    if distrobox enter claude-desktop -- true >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 2
done
if [[ "$ready" != true ]]; then
    echo 'Claude Distrobox did not finish starting' >&2
    exit 1
fi

if ! distrobox enter claude-desktop -- dpkg-query -W claude-desktop >/dev/null 2>&1; then
    distrobox enter claude-desktop -- sudo curl -fsSLo \
        /usr/share/keyrings/claude-desktop-archive-keyring.asc \
        https://downloads.claude.ai/claude-desktop/key.asc
    fingerprint=$(distrobox enter claude-desktop -- sudo gpg --batch --with-colons --show-keys \
        /usr/share/keyrings/claude-desktop-archive-keyring.asc 2>/dev/null |
        awk -F: '$1 == "fpr" { print $10; exit }')
    if [[ "$fingerprint" != 31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE ]]; then
        echo 'Claude apt signing key has an unexpected fingerprint' >&2
        exit 1
    fi
    printf '%s %s\n' \
        'deb [signed-by=/usr/share/keyrings/claude-desktop-archive-keyring.asc]' \
        'https://downloads.claude.ai/claude-desktop/apt/stable stable main' |
        distrobox enter claude-desktop -- sudo tee /etc/apt/sources.list.d/claude-desktop.list >/dev/null
    distrobox enter claude-desktop -- sudo apt-get update
    distrobox enter claude-desktop -- sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y claude-desktop
fi

distrobox enter claude-desktop -- distrobox-export --app claude-desktop
gtk-update-icon-cache --force --ignore-theme-index "$HOME/.local/share/icons/hicolor"
