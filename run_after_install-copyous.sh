#!/bin/bash
set -euo pipefail

if [[ "${SKIP_COPYOUS:-}" == 1 ]]; then
    exit 0
fi
if [[ "${XDG_CURRENT_DESKTOP:-}" != *GNOME* ]] ||
    [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && ! -S "${XDG_RUNTIME_DIR:-}/bus" ]]; then
    echo "GNOME session unavailable; Copyous will install on the next chezmoi apply"
    exit 0
fi

uuid=copyous@boerdereinar.dev
if [[ ! -d "$HOME/.local/share/gnome-shell/extensions/$uuid" ]]; then
    shell_version=$(gnome-shell --version | awk '{split($3, version, "."); print version[1]}')
    extension_info=$(curl -fsS --get \
        --data-urlencode "uuid=$uuid" \
        --data-urlencode "shell_version=$shell_version" \
        https://extensions.gnome.org/extension-info/)
    if ! download_url=$(jq -er --arg shell_version "$shell_version" \
        'select(.shell_version_map[$shell_version] != null) | .download_url' <<<"$extension_info"); then
        echo "Copyous has no compatible GNOME Shell $shell_version release" >&2
        exit 1
    fi
    zip=$(mktemp --suffix=.zip)
    trap 'rm -f "$zip"' EXIT
    curl -fsSL -o "$zip" "https://extensions.gnome.org$download_url"
    gnome-extensions install --force "$zip"
fi

current=$(gsettings get org.gnome.shell enabled-extensions)
updated=$(python3 -c '
import ast
import sys

options = ast.literal_eval(sys.argv[1].removeprefix("@as "))
if sys.argv[2] not in options:
    options.append(sys.argv[2])
print(repr(options))
' "$current" "$uuid")
if [[ "$updated" != "$current" ]]; then
    gsettings set org.gnome.shell enabled-extensions "$updated"
fi
echo "Copyous installed and enabled (log out and back in if it is not visible yet)"
