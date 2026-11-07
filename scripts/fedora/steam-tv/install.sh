#!/usr/bin/bash
# Installs the triggers that open Steam Big Picture when an Xbox controller connects, and exit it when the last one
# disconnects.
set -euo pipefail

((EUID == 0)) || {
    echo 'Run with sudo.' >&2
    exit 1
}
cd "$(dirname "$0")"

workdir=$(mktemp -d)
trap 'rm -rf "${workdir}"' EXIT
sed -n 's/^\([A-Z_]*\)=\(.*\)$/s|@\1@|\2|g/p' ids.conf >"${workdir}/ids.sed"
for file in steam-tv-trigger steam-tv steam-tv-off 99-steam-tv.rules; do
    sed --file="${workdir}/ids.sed" "${file}" >"${workdir}/${file}"
done

install --mode=0755 "${workdir}/steam-tv-trigger" "${workdir}/steam-tv" "${workdir}/steam-tv-off" lgtv-hdmi \
    /usr/local/bin/
install --mode=0644 "${workdir}/99-steam-tv.rules" /etc/udev/rules.d/
install --mode=0644 steam-tv.service steam-tv-off.service /etc/systemd/system/
install --mode=0644 steam-tv-user.service /etc/systemd/user/steam-tv.service
install --mode=0644 steam-tv-off-user.service /etc/systemd/user/steam-tv-off.service
restorecon /usr/local/bin/steam-tv-trigger /usr/local/bin/steam-tv /usr/local/bin/steam-tv-off \
    /usr/local/bin/lgtv-hdmi \
    /etc/udev/rules.d/99-steam-tv.rules \
    /etc/systemd/system/steam-tv.service /etc/systemd/system/steam-tv-off.service \
    /etc/systemd/user/steam-tv.service /etc/systemd/user/steam-tv-off.service
systemctl daemon-reload
udevadm control --reload
echo 'Installed the controller triggers for Steam Big Picture.'
