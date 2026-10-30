#!/usr/bin/bash
# Installs the SteamOS-style Big Picture login session, in which Gamescope drives the LG TV directly with HDR.
set -euo pipefail

readonly STATE=/usr/local/share/gamescope-session-local
readonly MANIFEST="${STATE}/installed-files"
readonly VERSIONS="${STATE}/versions"
declare -A PINNED=(
    [gamescope - session]=73d2da84ace7f41006a0f85bd2fdb19ef593a464
    [gamescope - session - steam]=1a3fdb7fa15a4bba7204bef69702b7a10a297828
)

((EUID == 0)) || {
    echo 'Run with sudo.' >&2
    exit 1
}
main_user=${SUDO_USER:?Run through sudo from the desktop user}

declare -A commits=()
for repo in "${!PINNED[@]}"; do
    commits[${repo}]=$(awk -v repo="${repo}" '$1 == repo {print $2}' "${VERSIONS}" 2>/dev/null || true)
    [[ -n "${commits[${repo}]}" ]] || commits[${repo}]=${PINNED[${repo}]}
done
for arg in "$@"; do
    repo=${arg%%=*}
    [[ -v "PINNED[${repo}]" && "${arg#*=}" =~ ^[0-9a-f]{40}$ ]] || {
        echo "Bad argument: ${arg}, expected <repo>=<40-hex commit> for repo in: ${!PINNED[*]}" >&2
        exit 2
    }
    commits[${repo}]=${arg#*=}
done

workdir=$(mktemp -d)
install_started=false
installed=false
cleanup() {
    result=$?
    trap - EXIT
    if [[ "${install_started}" == true && "${installed}" == false ]]; then
        while IFS= read -r path; do
            rm -f "${path}"
            if [[ -e "${workdir}/previous${path}" || -L "${workdir}/previous${path}" ]]; then
                cp -a "${workdir}/previous${path}" "${path}"
            fi
        done <"${workdir}/all-files"
        if [[ -f "${workdir}/old-manifest" ]]; then
            cp -p "${workdir}/old-manifest" "${MANIFEST}"
        else
            rm -f "${MANIFEST}"
        fi
        if [[ -f "${workdir}/old-versions" ]]; then
            cp -p "${workdir}/old-versions" "${VERSIONS}"
        else
            rm -f "${VERSIONS}"
        fi
        echo 'Restored the previous Gamescope session after installation failed' >&2
    fi
    rm -f "${STATE}/.installed-files.new" "${STATE}/.versions.new"
    rm -rf "${workdir}"
    exit "${result}"
}
trap cleanup EXIT

# Checksums only cover the pinned commits; update_fedora_extras shows the diff of newer ones before installing them.
declare -A PINNED_SHA256=(
    [gamescope - session]=aa6d86c082db00ae2501c5198be3c5d38b06d9252ad4fb04cb287ab31e1ec320
    [gamescope - session - steam]=1729029426c3de44f83fa674dce6bda8bd9a2b292df10d67b7acf74f1b0f8d62
)
for repo in "${!commits[@]}"; do
    archive="${workdir}/${repo}.tar.gz"
    curl -fsSL -o "${archive}" "https://github.com/ChimeraOS/${repo}/archive/${commits[${repo}]}.tar.gz"
    if [[ "${commits[${repo}]}" == "${PINNED[${repo}]}" ]]; then
        echo "${PINNED_SHA256[${repo}]}  ${archive}" | sha256sum --check --quiet
    fi
    tar xzf "${archive}" -C "${workdir}" --strip-components=1
done

# The upstream scripts hardcode /usr paths, so the files go there and the manifest records them for removal. The list
# leaves out distro-specific extras (polkit policy, http loader, the duplicate session entry).
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
new_manifest="${workdir}/new-manifest"
for file in "${FILES[@]}"; do
    [[ -f "${workdir}/${file}" ]] || {
        echo "Missing session file: ${file}" >&2
        exit 1
    }
    printf '/%s\n' "${file}" >>"${new_manifest}"
done
readonly HELPERS=/usr/bin/steamos-polkit-helpers
readonly HELPER_TOOLS=(steamos-update jupiter-biosupdate steamos-select-branch)
for tool in "${HELPER_TOOLS[@]}" jupiter-dock-updater; do
    printf '%s/%s\n' "${HELPERS}" "${tool}" >>"${new_manifest}"
done

mkdir -p "${STATE}" "${workdir}/previous"
[[ ! -f "${MANIFEST}" ]] || cp -p "${MANIFEST}" "${workdir}/old-manifest"
[[ ! -f "${VERSIONS}" ]] || cp -p "${VERSIONS}" "${workdir}/old-versions"
cp "${new_manifest}" "${workdir}/all-files"
[[ ! -f "${MANIFEST}" ]] || cat "${MANIFEST}" >>"${workdir}/all-files"
sort -u -o "${workdir}/all-files" "${workdir}/all-files"
while IFS= read -r path; do
    [[ -e "${path}" || -L "${path}" ]] || continue
    cp -a --parents "${path}" "${workdir}/previous"
done <"${workdir}/all-files"
install_started=true
for file in "${FILES[@]}"; do
    # Root's tar keeps the archive's group-writable modes, so normalize them.
    if [[ -x "${workdir}/${file}" ]]; then mode=0755; else mode=0644; fi
    install -D --mode="${mode}" "${workdir}/${file}" "/${file}"
done

# In SteamOS mode the Steam client runs its OS, BIOS and dock updaters through these helper paths and reports "unable to
# download updates" when they are missing. Upstream elevates through pkexec with a policy allowing anyone to run them as
# root; the scripts behind them only report "nothing to update" here, so they run unprivileged instead.
install -d "${HELPERS}"
for tool in "${HELPER_TOOLS[@]}"; do
    printf '#!/usr/bin/bash\nexec /usr/bin/%s "$@"\n' "${tool}" >"${workdir}/helper"
    install --mode=0755 "${workdir}/helper" "${HELPERS}/${tool}"
done
printf '#!/usr/bin/bash\nexit 0\n' >"${workdir}/helper"
install --mode=0755 "${workdir}/helper" "${HELPERS}/jupiter-dock-updater"
if [[ -f "${MANIFEST}" ]]; then
    while IFS= read -r path; do
        grep -Fxq "${path}" "${new_manifest}" || rm -f "${path}"
    done <"${MANIFEST}"
fi
xargs --arg-file="${new_manifest}" restorecon

for repo in "${!commits[@]}"; do
    echo "${repo} ${commits[${repo}]}"
done | sort >"${workdir}/new-versions"
install --mode=0644 "${new_manifest}" "${STATE}/.installed-files.new"
install --mode=0644 "${workdir}/new-versions" "${STATE}/.versions.new"
mv -f "${STATE}/.installed-files.new" "${MANIFEST}"
mv -f "${STATE}/.versions.new" "${VERSIONS}"

# A separate user lets the TV session run while the desktop stays logged in.
readonly GAMING_USER=gaming
if ! id "${GAMING_USER}" &>/dev/null; then
    useradd --create-home --comment 'Steam TV' --groups games "${GAMING_USER}"
    echo "Created user '${GAMING_USER}'. Set its password with: sudo passwd ${GAMING_USER}"
fi
usermod --append --groups games "${main_user}"

readonly LIBRARY=/home/games/steam
# The default ACL makes every file Steam creates group-writable regardless of umask, so either user can update or verify
# games installed by the other.
install -d --owner=root --group=games --mode=2775 "${LIBRARY}"
setfacl --recursive --modify g:games:rwX "${LIBRARY}"
setfacl --recursive --default --modify g:games:rwX "${LIBRARY}"

home_dir() {
    getent passwd "$1" | cut -d: -f6
}
gaming_home=$(home_dir "${GAMING_USER}")
install -d --owner="${GAMING_USER}" --group="${GAMING_USER}" \
    "${gaming_home}/.config" "${gaming_home}/.config/environment.d"
install --owner="${GAMING_USER}" --group="${GAMING_USER}" --mode=0644 /dev/stdin \
    "${gaming_home}/.config/environment.d/gamescope-session-plus.conf" <<'EOF'
OUTPUT_CONNECTOR=HDMI-A-1
SCREEN_WIDTH=3840
SCREEN_HEIGHT=2160
VULKAN_ADAPTER=1002:7550
ENABLE_GAMESCOPE_WSI=1
ENABLE_GAMESCOPE_HDR=1
EOF

# Each Steam account keeps its own library list, so the shared library stays invisible (and its games show as not
# installed) until that user's list names it. Steam rewrites the list from memory on exit, so edit it only while that
# user's Steam is closed; Steam fills in the remaining fields from the library's own libraryfolder.vdf.
for user in "${main_user}" "${GAMING_USER}"; do
    folders="$(home_dir "${user}")/.local/share/Steam/steamapps/libraryfolders.vdf"
    if [[ ! -f "${folders}" ]]; then
        echo "Start Steam once as '${user}', quit it, then rerun to add the shared library."
    elif grep -Fq "\"${LIBRARY}\"" "${folders}"; then
        continue
    elif pgrep --uid "${user}" --exact steam >/dev/null; then
        echo "Quit Steam for '${user}', then rerun to add the shared library."
    else
        index=$(awk '
            /^\t"[0-9]+"$/ {
                gsub(/"/, "", $1)
                if ($1 >= candidate) candidate = $1 + 1
            }
            END { print candidate + 0 }
        ' "${folders}")
        {
            sed '$d' "${folders}"
            printf '\t"%s"\n\t{\n\t\t"path"\t\t"%s"\n\t\t"label"\t\t""\n\t\t"apps"\n\t\t{\n\t\t}\n\t}\n}\n' \
                "${index}" "${LIBRARY}"
        } >"${workdir}/libraryfolders.vdf"
        install --owner="${user}" --group="${user}" --mode=0644 "${workdir}/libraryfolders.vdf" "${folders}"
        echo "Added ${LIBRARY} to the Steam libraries of '${user}'."
    fi
done

# Steam cannot drop its built-in library, so make it unwritable: an install aimed there fails with a disk write error
# instead of landing where the other user cannot see it.
for user in "${main_user}" "${GAMING_USER}"; do
    steamapps="$(home_dir "${user}")/.local/share/Steam/steamapps"
    for dir in "${steamapps}/common" "${steamapps}/downloading"; do
        [[ ! -d "${dir}" ]] || chmod a-w "${dir}"
    done
done

shader_config="${gaming_home}/.local/share/Steam/config/config.vdf"
if [[ -f "${shader_config}" ]] && ! grep -Fq '"EnableShaderBackgroundProcessing"' "${shader_config}"; then
    if pgrep --uid "${GAMING_USER}" --exact steam >/dev/null; then
        echo "Quit Steam for '${GAMING_USER}', then rerun to enable background shader processing."
    else
        awk '
            /"ShaderCacheManager"/ { manager = 1 }
            manager && /^[[:space:]]*\{$/ && !inserted {
                print
                print "\t\t\t\t\t\"EnableShaderBackgroundProcessing\"\t\t\"1\""
                inserted = 1
                next
            }
            { print }
            END { if (!inserted) exit 1 }
        ' "${shader_config}" >"${workdir}/config.vdf"
        install --owner="${GAMING_USER}" --group="${GAMING_USER}" --mode=0644 \
            "${workdir}/config.vdf" "${shader_config}"
        echo "Enabled background shader processing for '${GAMING_USER}'."
    fi
fi

layout="$(home_dir "${main_user}")/.config/monitors.xml"
if [[ -f "${layout}" ]]; then
    install --mode=0644 "${layout}" /etc/xdg/monitors.xml
    greeter_config=/var/lib/gdm/seat0/config
    if [[ -d "${greeter_config}" ]]; then
        greeter_owner=$(stat -c %u "${greeter_config}")
        install --mode=0644 --owner="${greeter_owner}" \
            "$(dirname "$0")/greeter-monitors.xml" "${greeter_config}/monitors.xml"
    fi
    install --mode=0644 --owner="${GAMING_USER}" --group="${GAMING_USER}" \
        "${layout}" "${gaming_home}/.config/monitors.xml"
fi

accounts_user() {
    local uid
    uid=$(id -u "$1")
    busctl call org.freedesktop.Accounts "/org/freedesktop/Accounts/User${uid}" \
        org.freedesktop.Accounts.User "$2" s "$3"
}
curl -fsSL -o "${workdir}/avatar" "https://github.com/gaborbernat.png?size=512"
accounts_user "${main_user}" SetIconFile "${workdir}/avatar"
accounts_user "${GAMING_USER}" SetIconFile /usr/share/icons/hicolor/256x256/apps/steam.png
accounts_user "${GAMING_USER}" SetSession gamescope-session-steam
installed=true
echo "Installed the Steam Big Picture session ($(paste -sd' ' "${VERSIONS}" || true))."
echo "Configured '${GAMING_USER}': TV session by default, shared library at ${LIBRARY}."
