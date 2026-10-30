#!/bin/bash
set -euo pipefail

if [[ "${XDG_CURRENT_DESKTOP:-}" != *GNOME* ]] || [[ $(gnome-shell --version || true) != 'GNOME Shell 51.'* ]]; then
    exit 0
fi

metadata="${HOME}/.local/share/gnome-shell/extensions/vicinae@dagimg-dot/metadata.json"
if [[ ! -f "${metadata}" ]] ||
    ! jq -e '.version == 17 and (."shell-version" | index("51") == null)' "${metadata}" >/dev/null; then
    exit 0
fi

updated=$(mktemp "${metadata%/*}/.metadata.XXXXXX")
trap 'rm -f "$updated"' EXIT
jq '."shell-version" += ["51"]' "${metadata}" >"${updated}"
chmod 0644 "${updated}"
mv "${updated}" "${metadata}"
echo 'Vicinae GNOME extension now supports GNOME 51; log out and back in to load it'
