#!/bin/bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
    echo "Run this script as root" >&2
    exit 1
fi

dnf install -y curl gnupg2
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
curl -fLsS --retry 3 -o "$staging/key.asc" https://d2t3ff60b2tol4.cloudfront.net/repomd.xml.key
fingerprint=$(GNUPGHOME="$staging" gpg --batch --show-keys --with-colons "$staging/key.asc" |
    awk -F: '$1 == "fpr" { print $10; exit }')
if [[ "$fingerprint" != AEEB94E9C5A3B54ECFA4A66AA684470CACCAF35C ]]; then
    echo "Insync repository key fingerprint mismatch" >&2
    exit 1
fi

rpm --import "$staging/key.asc"
cat > "$staging/insync.repo" <<'EOF'
[insync]
name=Insync
# The RPM scans for this legacy URL before overwriting the repository file.
# http://yum.insync.io/
baseurl=https://yum.insync.io/fedora/$releasever/
enabled=1
gpgcheck=1
gpgkey=https://d2t3ff60b2tol4.cloudfront.net/repomd.xml.key
EOF
install -m 0644 "$staging/insync.repo" /etc/yum.repos.d/insync.repo
dnf install -y insync

# The vendor RPM can replace this file with an HTTP base URL in its post-install script.
install -m 0644 "$staging/insync.repo" /etc/yum.repos.d/insync.repo
