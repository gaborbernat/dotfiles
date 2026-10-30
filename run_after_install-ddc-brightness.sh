#!/bin/bash
# GNOME Extensions version 59, compatible with GNOME Shell 49 and 50.
set -euo pipefail

if [[ "${SKIP_DDC_BRIGHTNESS:-}" == 1 ]]; then
    exit 0
fi
if [[ "${XDG_CURRENT_DESKTOP:-}" != *GNOME* ]] ||
    [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && ! -S "${XDG_RUNTIME_DIR:-}/bus" ]]; then
    echo "GNOME session unavailable; DDC brightness will install on the next chezmoi apply"
    exit 0
fi
if ! command -v ddcutil >/dev/null 2>&1; then
    echo "ddcutil unavailable; DDC brightness will install after DNF setup"
    exit 0
fi
uuid=display-brightness-ddcutil@themightydeity.github.com
if [[ ! -d "$HOME/.local/share/gnome-shell/extensions/$uuid" ]]; then
    zip=$(mktemp --suffix=.zip)
    trap 'rm -f "$zip"' EXIT
    curl -fL -sS -o "$zip" "https://extensions.gnome.org/download-extension/$uuid.shell-extension.zip?version_tag=69941"
    printf '%s  %s\n' be457ab7b623d51716618c250fef5c8d99417e9861518f362f3303ae1c75c9ce "$zip" | sha256sum -c -
    gnome-extensions install --force "$zip"
fi

current=$(gsettings get org.gnome.shell enabled-extensions)
updated=$(python3 -c '
import ast
import sys

extensions = ast.literal_eval(sys.argv[1].removeprefix("@as "))
if sys.argv[2] not in extensions:
    extensions.append(sys.argv[2])
print(repr(extensions))
' "$current" "$uuid")
if [[ "$updated" != "$current" ]]; then
    gsettings set org.gnome.shell enabled-extensions "$updated"
fi
echo "DDC brightness extension installed and enabled (log out and back in if needed)"
