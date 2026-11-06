#!/bin/bash
set -euo pipefail

export PATH="${HOME}/.cargo/bin:${PATH}"

# Only the bootstrap binary is pinned: a later bare `rustup update` (the `u` rust stage) self-updates rustup.
RUSTUP_VERSION=1.29.3

install_rustup() {
    local os arch target sha256
    os="$(uname -s)"
    arch="$(uname -m)"
    case "${os}-${arch}" in
        Linux-x86_64)
            target=x86_64-unknown-linux-gnu
            sha256=b1c8cb14e30889e7e2999e6b69e62d9e9b9ffc0f4df8180564d306d9680e6c55
            ;;
        Linux-aarch64)
            target=aarch64-unknown-linux-gnu
            sha256=9f608c142e0e38a78957d0661ba1dfaf0b6fb37184cfaa4b9a0aa57af6184282
            ;;
        Darwin-x86_64)
            target=x86_64-apple-darwin
            sha256=bc107f1fb0228de7fa32413c89c1b305cea9cd256e94b01150cd054128145429
            ;;
        Darwin-arm64)
            target=aarch64-apple-darwin
            sha256=63752a1919a3a4793173ec70f8f212621a7ce38ba6a246095984482f4de20f9f
            ;;
        *)
            echo "❌ No pinned rustup-init for ${os} ${arch}" >&2
            exit 1
            ;;
    esac

    tmp="$(mktemp -d)"
    trap 'rm -rf "${tmp}"' EXIT
    curl --proto '=https' --tlsv1.2 -sSf -o "${tmp}/rustup-init" \
        "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/${target}/rustup-init"
    if command -v sha256sum &>/dev/null; then
        echo "${sha256}  ${tmp}/rustup-init" | sha256sum -c --quiet -
    else
        echo "${sha256}  ${tmp}/rustup-init" | shasum -a 256 -c --quiet -
    fi
    chmod +x "${tmp}/rustup-init"
    "${tmp}/rustup-init" -y --no-modify-path
}

if ! command -v rustup &>/dev/null; then
    if command -v rustup-init &>/dev/null; then
        echo "Initializing distro-packaged rustup..."
        rustup-init -y --no-modify-path
    else
        echo "Installing rustup ${RUSTUP_VERSION}..."
        install_rustup
    fi
fi

echo "Installing Rust stable toolchain..."
rustup default stable
rustup update stable
echo "✅ Rust stable toolchain installed"
