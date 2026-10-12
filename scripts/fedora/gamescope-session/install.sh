#!/usr/bin/bash
# Installs the SteamOS-style "Steam Big Picture" login session for a dedicated "gaming"
# user, so Gamescope drives the LG TV directly with HDR while the desktop stays logged in.
# Usage: sudo install.sh [gamescope-session=<commit>] [gamescope-session-steam=<commit>]
# Without arguments it keeps the installed versions, or installs the pinned ones.
set -euo pipefail

readonly GAMING_USER=gaming
readonly GITHUB_LOGIN=gaborbernat
readonly LIBRARY=/home/games/steam
readonly STATE=/usr/local/share/gamescope-session-local
readonly MANIFEST="$STATE/installed-files"
readonly VERSIONS="$STATE/versions"

# Checksums only cover the pinned commits; `u` installs newer ones after showing the diff.
declare -A PINNED=(
    [gamescope-session]=73d2da84ace7f41006a0f85bd2fdb19ef593a464
    [gamescope-session-steam]=1a3fdb7fa15a4bba7204bef69702b7a10a297828
)
declare -A PINNED_SHA256=(
    [gamescope-session]=aa6d86c082db00ae2501c5198be3c5d38b06d9252ad4fb04cb287ab31e1ec320
    [gamescope-session-steam]=1729029426c3de44f83fa674dce6bda8bd9a2b292df10d67b7acf74f1b0f8d62
)
# The upstream scripts hardcode /usr paths, so the files go there and the manifest records
# them for removal. Distro-specific extras (polkit policy, http loader, the duplicate
# session entry) are skipped.
readonly FILES=(
    usr/bin/export-gpu
    usr/bin/gamescope-session-plus
    usr/lib/systemd/user/gamescope-session-plus@.service
    usr/share/gamescope-session-plus/device-quirks
    usr/share/gamescope-session-plus/gamescope-session-plus
    usr/share/gamescope/scripts/50-custom/50-disable-explicit-sync.lua
    usr/bin/steamos-session-select
    usr/bin/steamos-update
    usr/bin/steamos-select-branch
    usr/bin/jupiter-biosupdate
    usr/share/gamescope-session-plus/sessions.d/steam
    usr/share/wayland-sessions/gamescope-session-steam.desktop
)

(( EUID == 0 )) || { echo 'Run with sudo.' >&2; exit 1; }
main_user=${SUDO_USER:?Run through sudo from the desktop user}
main_home=$(getent passwd "$main_user" | cut -d: -f6)

declare -A commits=()
for repo in "${!PINNED[@]}"; do
    commits[$repo]=$(awk -v repo="$repo" '$1 == repo {print $2}' "$VERSIONS" 2>/dev/null || true)
    [[ -n "${commits[$repo]}" ]] || commits[$repo]=${PINNED[$repo]}
done
for arg in "$@"; do
    repo=${arg%%=*}
    [[ -v "PINNED[$repo]" && "${arg#*=}" =~ ^[0-9a-f]{40}$ ]] || { echo "Bad argument: $arg" >&2; exit 2; }
    commits[$repo]=${arg#*=}
done

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

for repo in "${!commits[@]}"; do
    archive="$workdir/$repo.tar.gz"
    curl -fsSL -o "$archive" "https://github.com/ChimeraOS/$repo/archive/${commits[$repo]}.tar.gz"
    if [[ "${commits[$repo]}" == "${PINNED[$repo]}" ]]; then
        echo "${PINNED_SHA256[$repo]}  $archive" | sha256sum --check --quiet
    fi
    tar xzf "$archive" -C "$workdir" --strip-components=1
done

mkdir -p "$STATE"
[[ ! -f "$MANIFEST" ]] || xargs --arg-file="$MANIFEST" rm -f
: >"$MANIFEST"
for file in "${FILES[@]}"; do
    # Root's tar keeps the archive's group-writable modes, so normalize them.
    if [[ -x "$workdir/$file" ]]; then mode=0755; else mode=0644; fi
    install -D --mode="$mode" "$workdir/$file" "/$file"
    echo "/$file" >>"$MANIFEST"
done

# In SteamOS mode the Steam client runs its OS, BIOS and dock updaters through these
# helper paths and reports "unable to download updates" when they are missing. Upstream
# elevates through pkexec with a policy allowing anyone to run them as root; the scripts
# behind them only report "nothing to update" here, so they run unprivileged instead.
readonly HELPERS=/usr/bin/steamos-polkit-helpers
install -d "$HELPERS"
for tool in steamos-update jupiter-biosupdate steamos-select-branch; do
    printf '#!/usr/bin/bash\nexec /usr/bin/%s "$@"\n' "$tool" >"$workdir/helper"
    install --mode=0755 "$workdir/helper" "$HELPERS/$tool"
    echo "$HELPERS/$tool" >>"$MANIFEST"
done
printf '#!/usr/bin/bash\nexit 0\n' >"$workdir/helper"
install --mode=0755 "$workdir/helper" "$HELPERS/jupiter-dock-updater"
echo "$HELPERS/jupiter-dock-updater" >>"$MANIFEST"
xargs --arg-file="$MANIFEST" restorecon

for repo in "${!commits[@]}"; do
    echo "$repo ${commits[$repo]}"
done | sort >"$VERSIONS"
echo "Installed the Steam Big Picture session ($(paste -sd' ' "$VERSIONS"))."

if ! id "$GAMING_USER" &>/dev/null; then
    useradd --create-home --comment 'Steam TV' --groups games "$GAMING_USER"
    echo "Created user '$GAMING_USER'. Set its password with: sudo passwd $GAMING_USER"
fi
usermod --append --groups games "$main_user"

# The default ACL makes every file Steam creates group-writable regardless of umask,
# so either user can update or verify games installed by the other.
install -d --owner=root --group=games --mode=2775 "$LIBRARY"
setfacl --recursive --modify g:games:rwX "$LIBRARY"
setfacl --recursive --default --modify g:games:rwX "$LIBRARY"

gaming_home=$(getent passwd "$GAMING_USER" | cut -d: -f6)
install -d --owner="$GAMING_USER" --group="$GAMING_USER" \
    "$gaming_home/.config" "$gaming_home/.config/environment.d"
install --owner="$GAMING_USER" --group="$GAMING_USER" --mode=0644 /dev/stdin \
    "$gaming_home/.config/environment.d/gamescope-session-plus.conf" <<'EOF'
OUTPUT_CONNECTOR=HDMI-A-1
SCREEN_WIDTH=3840
SCREEN_HEIGHT=2160
VULKAN_ADAPTER=1002:7550
ENABLE_GAMESCOPE_WSI=1
ENABLE_GAMESCOPE_HDR=1
EOF

# Mutter reads monitors.xml from the system config dirs as a fallback for every user,
# which covers the GDM greeter whatever dynamic user it runs as.
layout="$main_home/.config/monitors.xml"
if [[ -f "$layout" ]]; then
    install --mode=0644 "$layout" /etc/xdg/monitors.xml
    greeter_config=/var/lib/gdm/seat0/config
    if [[ -d "$greeter_config" ]]; then
        install --mode=0644 --owner="$(stat -c %u "$greeter_config")" "$layout" "$greeter_config/monitors.xml"
    fi
    install --mode=0644 --owner="$GAMING_USER" --group="$GAMING_USER" "$layout" "$gaming_home/.config/monitors.xml"
fi

accounts_user() {
    busctl call org.freedesktop.Accounts "/org/freedesktop/Accounts/User$(id -u "$1")" \
        org.freedesktop.Accounts.User "$2" s "$3"
}
curl -fsSL -o "$workdir/avatar" "https://github.com/$GITHUB_LOGIN.png?size=512"
accounts_user "$main_user" SetIconFile "$workdir/avatar"
accounts_user "$GAMING_USER" SetIconFile /usr/share/icons/hicolor/256x256/apps/steam.png
accounts_user "$GAMING_USER" SetSession gamescope-session-steam
echo "Configured '$GAMING_USER': TV session by default, shared library at $LIBRARY."
