#!/bin/sh
set -eu

case "${XDG_CURRENT_DESKTOP:-}" in
    *GNOME*) ;;
    *) exit 0 ;;
esac
[ -S "${XDG_RUNTIME_DIR:-}/bus" ] || exit 0

systemctl --user daemon-reload
systemctl --user enable --now order-monitors.service
