#!/bin/bash
set -euo pipefail

if ! grep -qx 'ID=fedora' /etc/os-release; then
    echo "This installer targets Fedora" >&2
    exit 1
fi
display_found=0
for usb_device in /sys/bus/usb/devices/*; do
    if [[ -f "$usb_device/idVendor" && -f "$usb_device/idProduct" ]] &&
        [[ $(<"$usb_device/idVendor") == 2022 && $(<"$usb_device/idProduct") == 0522 ]]; then
        display_found=1
        break
    fi
done
if [[ $display_found -ne 1 ]]; then
    echo "No Antec Flux Pro display detected on USB" >&2
    exit 1
fi

sudo dnf install -y rust cargo gcc make lm_sensors-devel libusb1-devel pkgconf-pkg-config
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT
git clone --depth 1 --branch v1.2 https://github.com/Reikooters/antec-flux-pro-display.git "$build_dir/source"
if [[ $(git -C "$build_dir/source" rev-parse HEAD) != 3dce4aecae9b4df967e6594fab556cb1ddd1b274 ]]; then
    echo "Upstream tag moved; refusing to build an unreviewed revision" >&2
    exit 1
fi
cargo build --release --locked --manifest-path "$build_dir/source/Cargo.toml"
sudo bash "$(dirname "${BASH_SOURCE[0]}")/install-system.sh" "$build_dir/source/target/release/antec-flux-pro-display"
systemctl --no-pager --full status antec-flux-pro-display.service
