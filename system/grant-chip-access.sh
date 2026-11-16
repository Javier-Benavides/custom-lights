#!/bin/bash
# Gives the plugdev group access to the lighting chip only, to test it without root.
# Usage: sudo bash system/grant-chip-access.sh
# To undo it: sudo rm -f /etc/udev/rules.d/60-luces.rules
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run it with sudo"; exit 1; }
printf '%s\n' 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="048d", ATTRS{idProduct}=="5711", GROUP="plugdev", MODE="0660"' \
  > /etc/udev/rules.d/60-luces.rules
udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw --settle
echo "Only two nodes should say plugdev; the rest, root root:"
ls -l /dev/hidraw*
