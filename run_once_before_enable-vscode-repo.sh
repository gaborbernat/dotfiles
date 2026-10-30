#!/bin/bash
set -euo pipefail

# Microsoft publishes a signed RPM repository so DNF can update Code.
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
repo=$(mktemp)
trap 'rm -f "$repo"' EXIT
cat >"$repo" <<'REPO'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
REPO
sudo install -m 0644 "$repo" /etc/yum.repos.d/vscode.repo
