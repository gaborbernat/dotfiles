#!/bin/bash
# Astra Monitor v42 (GNOME Extensions version_tag 73927)
set -euo pipefail

if [[ "${SKIP_ASTRA_MONITOR:-}" == "1" ]]; then
    exit 0
fi
if ! command -v gnome-extensions >/dev/null 2>&1; then
    echo "gnome-extensions unavailable; skipping Astra Monitor"
    exit 0
fi
if [[ "${XDG_CURRENT_DESKTOP:-}" != *GNOME* ]] ||
    [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && ! -S "${XDG_RUNTIME_DIR:-}/bus" ]]; then
    echo "GNOME session unavailable; Astra Monitor will install on the next chezmoi apply"
    exit 0
fi

uuid=monitor@astraext.github.io
if [[ ! -d "${HOME}/.local/share/gnome-shell/extensions/${uuid}" ]]; then
    zip=$(mktemp --suffix=.zip)
    trap 'rm -f "$zip"' EXIT
    curl -fL -sS -o "${zip}" \
        "https://extensions.gnome.org/download-extension/${uuid}.shell-extension.zip?version_tag=73927"
    printf '%s  %s\n' 673cb04e38dc73f71d1e5c8f9c892a9cbf1fe41ddfc2166d6845f52a0839aa98 "${zip}" | sha256sum -c -
    gnome-extensions install --force "${zip}"
fi

current=$(gsettings get org.gnome.shell enabled-extensions)
updated=$(python3 -c '
import ast
import sys

options = ast.literal_eval(sys.argv[1].removeprefix("@as "))
if sys.argv[2] not in options:
    options.append(sys.argv[2])
print(repr(options))
' "${current}" "${uuid}")
if [[ "${updated}" != "${current}" ]]; then
    gsettings set org.gnome.shell enabled-extensions "${updated}"
fi
echo "Astra Monitor installed and enabled (log out and back in if it is not visible yet)"
