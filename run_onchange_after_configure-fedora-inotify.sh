#!/bin/bash
set -euo pipefail

# Copilot's MCP watcher can exhaust Fedora's default 128 inotify instances.
printf 'fs.inotify.max_user_instances = 512\n' | sudo tee /etc/sysctl.d/90-dotfiles-inotify.conf >/dev/null
sudo sysctl -w fs.inotify.max_user_instances=512
