#!/bin/bash
set -euo pipefail

rule=$(mktemp)
trap 'rm -f "$rule"' EXIT
# mprocs gives each updater a PTY, so one prompt needs a ticket shared across them.
printf 'Defaults:%s timestamp_timeout=30, timestamp_type=global\n' "$(id -un)" > "$rule"
visudo -cf "$rule"
sudo install -m 0440 "$rule" /etc/sudoers.d/90-dotfiles-timestamp
sudo visudo -c
