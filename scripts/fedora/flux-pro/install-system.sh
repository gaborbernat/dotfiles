#!/bin/bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this install phase as root" >&2
    exit 1
fi
binary="${1:?Usage: install-system.sh /path/to/antec-flux-pro-display}"

if [[ ! -x "${binary}" ]]; then
    echo "Built driver not found: ${binary}" >&2
    exit 1
fi

groupadd --system --force antec-flux
if ! id -u antec-flux >/dev/null 2>&1; then
    useradd --system --no-create-home --gid antec-flux --shell /usr/sbin/nologin antec-flux
fi

install -D -m 0755 "${binary}" /usr/local/bin/antec-flux-pro-display
source_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
install -D -m 0644 "${source_dir}/config.conf" /etc/antec-flux-pro-display/config.conf
install -D -m 0644 "${source_dir}/70-antec-flux-pro-display.rules" /etc/udev/rules.d/70-antec-flux-pro-display.rules
install -D -m 0644 "${source_dir}/antec-flux-pro-display.service" /etc/systemd/system/antec-flux-pro-display.service

udevadm control --reload-rules
udevadm trigger --subsystem-match=usb --attr-match=idVendor=2022 --attr-match=idProduct=0522
udevadm settle
systemctl daemon-reload
systemctl enable --now antec-flux-pro-display.service
systemctl restart antec-flux-pro-display.service
