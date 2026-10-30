# shellcheck shell=bash

gnome_session_ready() {
    [[ "${XDG_CURRENT_DESKTOP:-}" == *GNOME* ]] && command -v gsettings >/dev/null 2>&1 &&
        [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" || -S "${XDG_RUNTIME_DIR:-}/bus" ]]
}

install_pinned_extension() {
    local uuid=$1 version_tag=$2 sha256=$3
    # Global, not local: the EXIT trap fires after this function returns.
    extension_zip=$(mktemp --suffix=.zip)
    trap 'rm -f "${extension_zip}"' EXIT
    curl -fL -sS -o "${extension_zip}" \
        "https://extensions.gnome.org/download-extension/${uuid}.shell-extension.zip?version_tag=${version_tag}"
    printf '%s  %s\n' "${sha256}" "${extension_zip}" | sha256sum -c -
    gnome-extensions install --force "${extension_zip}"
}

# Each argument is +uuid to append if missing or -uuid to remove, applied in order.
edit_extension_list() {
    local key=$1 current updated
    shift
    current=$(gsettings get org.gnome.shell "${key}")
    updated=$(python3 -c '
import ast
import sys

names = ast.literal_eval(sys.argv[1].removeprefix("@as "))
for change in sys.argv[2:]:
    name = change[1:]
    if change.startswith("-"):
        names = [existing for existing in names if existing != name]
    elif name not in names:
        names.append(name)
print(repr(names) if names else "@as []")
' "${current}" "$@")
    if [[ "${updated}" != "${current}" ]]; then
        gsettings set org.gnome.shell "${key}" "${updated}"
    fi
}
