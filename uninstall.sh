#!/usr/bin/env bash
# Mouse Buttons — kaldırma / uninstaller
# Kullanım / Usage:  ./uninstall.sh          (ayarlarınız kalır / keeps your settings)
#                    ./uninstall.sh --purge  (ayarları da siler / also deletes your settings)
set -euo pipefail

APP_ID="io.github.snemege.MouseButtons"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

say() { printf '\n==> %s\n' "$*"; }

if [ "${FT_SKIP_SYSTEMD:-}" != 1 ]; then
  say "Servis durduruluyor / Stopping the service"
  systemctl --user disable --now mouse-buttons.service 2>/dev/null || true
fi
rm -f "$CONF/systemd/user/mouse-buttons.service"
[ "${FT_SKIP_SYSTEMD:-}" = 1 ] || systemctl --user daemon-reload

say "Dosyalar siliniyor / Removing files"
rm -rf "$DATA/mouse-buttons"
rm -f "$DATA/applications/$APP_ID.desktop"
find "$DATA/icons/hicolor" -name "$APP_ID.png" -delete 2>/dev/null || true
gtk-update-icon-cache -f -t "$DATA/icons/hicolor" >/dev/null 2>&1 || true

if [ "${1:-}" = "--purge" ]; then
  say "Ayarlar siliniyor / Removing settings"
  rm -rf "$CONF/mouse-buttons"
fi

if [ "${FT_SKIP_UDEV:-}" != 1 ] && [ -f /etc/udev/rules.d/70-mouse-buttons.rules ]; then
  say "Mouse izin kuralı kaldırılıyor / Removing the mouse access rule (sudo)"
  sudo rm -f /etc/udev/rules.d/70-mouse-buttons.rules
  sudo udevadm control --reload
fi

echo
echo "Kaldırıldı / Removed."
