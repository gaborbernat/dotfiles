#!/bin/bash
set -euo pipefail

readonly VENDOR=2022 PRODUCT=0522

if [[ "${1:-}" == --detect ]]; then
    for usb_device in /sys/bus/usb/devices/*; do
        if [[ -f "${usb_device}/idVendor" && -f "${usb_device}/idProduct" ]] &&
            [[ $(<"${usb_device}/idVendor") == "${VENDOR}" && $(<"${usb_device}/idProduct") == "${PRODUCT}" ]]; then
            exit 0
        fi
    done
    exit 1
fi
if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this install phase as root" >&2
    exit 1
fi
binary="${1:?Usage: install-system.sh --detect | /path/to/antec-flux-pro-display}"

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
printf 'SUBSYSTEM=="usb", ATTR{idVendor}=="%s", ATTR{idProduct}=="%s", GROUP="antec-flux", MODE="0660"\n' \
    "${VENDOR}" "${PRODUCT}" | install -D -m 0644 /dev/stdin /etc/udev/rules.d/70-antec-flux-pro-display.rules
install -D -m 0644 "${source_dir}/antec-flux-pro-display.service" /etc/systemd/system/antec-flux-pro-display.service

udevadm control --reload-rules
udevadm trigger --subsystem-match=usb --attr-match=idVendor="${VENDOR}" --attr-match=idProduct="${PRODUCT}"
udevadm settle
systemctl daemon-reload
systemctl enable --now antec-flux-pro-display.service
systemctl restart antec-flux-pro-display.service
