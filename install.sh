#!/usr/bin/env bash
# Mouse Buttons — kurulum / installer
# Kullanım / Usage:  ./install.sh
# Sadece yönetici şifresi gereken adım: mouse okuma izni kuralı (udev).
# The only step that needs sudo: the mouse access rule (udev).
set -euo pipefail
cd "$(dirname "$0")"

APP_ID="io.github.snemege.MouseButtons"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"
DEST="$DATA/mouse-buttons"
PY="$(command -v python3 || true)"

say() { printf '\n==> %s\n' "$*"; }

[ -n "$PY" ] || { echo "python3 bulunamadı / python3 not found"; exit 1; }

say "Gerekli paketler kontrol ediliyor / Checking dependencies"
if ! "$PY" - 2>/dev/null <<'EOF'
import evdev, gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
EOF
then
  cat <<'EOF'
Eksik paket var / Some packages are missing. Install them, then run ./install.sh again:
  Fedora:          sudo dnf install python3-evdev python3-gobject gtk4 libadwaita
  Debian / Ubuntu: sudo apt install python3-evdev python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
  Arch:            sudo pacman -S python-evdev python-gobject gtk4 libadwaita
EOF
  exit 1
fi
for tool in systemd-run gio; do
  command -v "$tool" >/dev/null || echo "Uyarı / Warning: '$tool' yok; 'Uygulama aç' eylemi çalışmaz / needed by the 'Launch app' action"
done

say "Dosyalar kuruluyor / Installing files  ($DEST)"
install -Dm755 mouse_buttons.py "$DEST/mouse_buttons.py"
mkdir -p "$DATA/icons" "$DATA/applications" "$CONF/systemd/user"
cp -r data/icons/hicolor "$DATA/icons/"
gtk-update-icon-cache -f -t "$DATA/icons/hicolor" >/dev/null 2>&1 || true
sed "s|@PYTHON@|$PY|; s|@SCRIPT@|$DEST/mouse_buttons.py|" \
  "data/$APP_ID.desktop.in" > "$DATA/applications/$APP_ID.desktop"
sed "s|@PYTHON@|$PY|; s|@SCRIPT@|$DEST/mouse_buttons.py|" \
  data/mouse-buttons.service.in > "$CONF/systemd/user/mouse-buttons.service"

if [ "${FT_SKIP_UDEV:-}" != 1 ]; then
  say "Mouse okuma izni / Mouse access permission (sudo şifresi istenebilir / may ask for your password)"
  sudo install -Dm644 data/70-mouse-buttons.rules /etc/udev/rules.d/70-mouse-buttons.rules
  sudo udevadm control --reload
  sudo udevadm trigger --subsystem-match=input --action=change
  sudo udevadm trigger --subsystem-match=misc --action=change
fi

if [ "${FT_SKIP_SYSTEMD:-}" != 1 ]; then
  say "Arka plan servisi başlatılıyor / Starting the background service"
  systemctl --user daemon-reload
  systemctl --user enable mouse-buttons.service
  systemctl --user restart mouse-buttons.service
fi

cat <<'EOF'

Kurulum tamam / Done.
  Open "Mouse Buttons" from your application menu.
  Uygulama menüsünden "Mouse Buttons" uygulamasını açın.
  Servis her açılışta kendiliğinden çalışır / The service starts automatically at every login.
EOF
