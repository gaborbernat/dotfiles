#!/bin/bash
set -euo pipefail

config=$1
desktop_user=$2
source_dir=$(dirname "$config")
desktop_uid=$(id -u "$desktop_user")
socket_group="xremap-$desktop_user"

if ! getent group "$socket_group" >/dev/null; then
    groupadd --system "$socket_group"
fi
if ! id xremap >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home --shell /sbin/nologin \
        --groups input,"$socket_group" xremap
else
    usermod --append --groups input,"$socket_group" xremap
fi
usermod --append --groups "$socket_group" "$desktop_user"
printf 'uinput\n' > /etc/modules-load.d/xremap.conf
modprobe uinput
install -m 0644 "$source_dir/99-xremap-uinput.rules" \
    /etc/udev/rules.d/99-xremap-uinput.rules
udevadm control --reload-rules
udevadm trigger --subsystem-match=misc --sysname-match=uinput
udevadm settle

restart_needed=0
if ! cmp -s "$config" /etc/xremap/config.yml; then
    install -D -m 0644 "$config" /etc/xremap/config.yml
    restart_needed=1
fi
service=$(mktemp)
trap 'rm -f "$service"' EXIT
cat > "$service" <<EOF
[Unit]
Description=Mac application shortcuts via xremap
After=systemd-logind.service systemd-modules-load.service

[Service]
User=xremap
Group=xremap
SupplementaryGroups=input $socket_group
RuntimeDirectory=xremap
RuntimeDirectoryMode=0755
RuntimeDirectoryPreserve=yes
ExecStartPre=+/usr/bin/modprobe uinput
ExecStartPre=+/usr/bin/udevadm settle
ExecStartPre=+/usr/bin/setfacl -m g:input:rw /dev/uinput
ExecStartPre=+/usr/bin/install -d -m 2770 -o xremap -g $socket_group /run/xremap/$desktop_uid
ExecStart=/usr/bin/xremap --desktop=socket --no-window-logging --allow-launch=false --watch=device /etc/xremap/config.yml
Restart=on-failure
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF

if ! cmp -s "$service" /etc/systemd/system/xremap.service; then
    install -m 0644 "$service" /etc/systemd/system/xremap.service
    systemctl daemon-reload
    restart_needed=1
fi
systemctl enable xremap.service
if systemctl is-active --quiet xremap.service; then
    if [[ "$restart_needed" == 1 ]]; then
        systemctl restart xremap.service
    fi
else
    systemctl reset-failed xremap.service
    systemctl start xremap.service
fi
