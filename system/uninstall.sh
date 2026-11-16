#!/bin/bash
# Removes luces. First, without sudo: luces shortcut remove
# Usage: sudo bash system/uninstall.sh
set -u
[ "$(id -u)" -eq 0 ] || { echo "Run it with sudo"; exit 1; }
systemctl disable --now luces-data.timer luces.service 2>/dev/null   # on stopping, it paints black
rm -f /etc/systemd/system/luces.service /etc/systemd/system/luces-data.service /etc/systemd/system/luces-data.timer
systemctl daemon-reload
rm -f /etc/udev/rules.d/60-luces.rules
udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw --settle
rm -f /usr/local/bin/luces /usr/local/share/applications/luces.desktop
rm -rf /usr/local/lib/luces /var/lib/luces
getent passwd luces >/dev/null && userdel luces
getent group luces >/dev/null && groupdel luces
echo "Done. A reboot brings back the effect stored in the chip."
