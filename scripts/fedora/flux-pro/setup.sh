#!/bin/bash
set -euo pipefail

if ! grep -qx 'ID=fedora' /etc/os-release; then
    echo "This installer targets Fedora" >&2
    exit 1
fi
installer="$(dirname "${BASH_SOURCE[0]}")/install-system.sh"
if ! bash "${installer}" --detect; then
    echo "No Antec Flux Pro display detected on USB" >&2
    exit 1
fi

sudo dnf install -y rust cargo gcc make lm_sensors-devel libusb1-devel pkgconf-pkg-config
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT
git clone --depth 1 --branch v1.2 https://github.com/Reikooters/antec-flux-pro-display.git "${build_dir}/source"
revision=$(git -C "${build_dir}/source" rev-parse HEAD)
if [[ ${revision} != 3dce4aecae9b4df967e6594fab556cb1ddd1b274 ]]; then
    echo "Upstream tag moved; refusing to build an unreviewed revision" >&2
    exit 1
fi
cargo build --release --locked --manifest-path "${build_dir}/source/Cargo.toml"
sudo bash "${installer}" "${build_dir}/source/target/release/antec-flux-pro-display"
systemctl --no-pager --full status antec-flux-pro-display.service
