#!/bin/bash
# Installs luces as two system services. Read it first: it runs as root. See docs/hardware.md.
# Usage: sudo bash system/install.sh
# It asks for coordinates with one decimal and METAR stations, kept in /var/lib/luces/control/place.toml.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run it with sudo"; exit 1; }
[ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ] || { echo "Run it with sudo from your own user"; exit 1; }
OWNER=$SUDO_USER
HERE=$(cd "$(dirname "$0")/.." && pwd)
DEST=/usr/local/lib/luces
CONTROL=/var/lib/luces/control

echo "== Tests"
(cd "$HERE" && runuser -u "$OWNER" -- python3 -m unittest discover -s tests -t . -q)

echo "== System account"
getent group luces >/dev/null || groupadd --system luces
getent passwd luces >/dev/null || useradd --system --gid luces --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin luces

echo "== Program (a fixed copy owned by root)"
rm -rf "$DEST"
install -d -m 0755 "$DEST" "$DEST/bin"
cp -r "$HERE/luces" "$DEST/luces"
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} +
find "$DEST" -name AGENTS.md -delete
chown -R root:root "$DEST"
install -m 0755 "$HERE"/bin/* "$DEST/bin/"
ln -sfn "$DEST/bin/luces" /usr/local/bin/luces
install -d -m 0755 /usr/local/share/applications
install -m 0644 "$HERE/system/luces.desktop" /usr/local/share/applications/luces.desktop

echo "== Folders"
install -d -o luces -g luces -m 0755 /var/lib/luces /var/lib/luces/data
install -d -o "$OWNER" -g luces -m 0750 "$CONTROL"

if [ ! -e "$CONTROL/place.toml" ]; then
  echo "== Place: used for the Sun and the weather. It stays on this machine"
  read -rp "Latitude with one decimal: " lat
  read -rp "Longitude with one decimal: " lon
  read -rp "METAR stations by preference, separated by spaces (empty: no weather): " stations
  list=$(printf '"%s", ' $stations); [ -n "$stations" ] || list=
  printf 'lat = %s\nlon = %s\nstations = [%s]\n' "$lat" "$lon" "${list%, }" > "$CONTROL/place.toml"
  chown "$OWNER":luces "$CONTROL/place.toml"; chmod 0640 "$CONTROL/place.toml"
fi

echo "== Permissions: the chip, the mouse's interface 3 and the GPU's I2C bus"
install -m 0644 "$HERE/system/60-luces.rules" /etc/udev/rules.d/60-luces.rules
# The keyboard's interface 2 also carries the keys being pressed: only if you enabled it, then run this again
if python3 -I -c 'import sys, tomllib; d = tomllib.load(open(sys.argv[1], "rb")); sys.exit(d.get("keyboard", {}).get("enabled") is not True)' \
    "$CONTROL/settings.toml" 2>/dev/null; then
  echo "== Permissions: the keyboard's interface 2"
  install -m 0644 "$HERE/system/61-luces-keyboard.rules" /etc/udev/rules.d/61-luces-keyboard.rules
else
  rm -f /etc/udev/rules.d/61-luces-keyboard.rules
fi
udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw --subsystem-match=i2c-dev --settle

echo "== Services"
install -m 0644 "$HERE"/system/luces.service "$HERE"/system/luces-data.service "$HERE"/system/luces-data.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable luces.service luces-data.timer
systemctl restart luces.service luces-data.timer   # on a reinstall, a running service would keep the old code
systemctl start luces-data.service || true
sleep 3
systemctl --no-pager --lines=0 status luces.service || true
runuser -u "$OWNER" -- /usr/local/bin/luces status
echo
echo "One step left, without sudo, from your desktop session: luces shortcut"
