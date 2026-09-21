#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Snemege
"""Mouse Buttons: mouse tuşlarına istediğin işi atar (X-Mouse Button Control benzeri).

İki modu var:
  --servis   arka planda mouse'u dinler ve tuşları çevirir (systemd kullanıcı servisi)
  (parametresiz)  ayar penceresini açar
"""
import ast
import asyncio
import glob
import json
import os
import re
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path

import evdev
from evdev import ecodes as e
from evdev import InputDevice, UInput

CONFIG_DIR = Path.home() / ".config" / "mouse-buttons"
CONFIG = CONFIG_DIR / "config.json"
STATUS = CONFIG_DIR / "durum.json"
VIRTUAL_PREFIX = "Mouse Buttons"
APP_ID = "io.github.snemege.MouseButtons"
VERSION = "0.1.0"
PROJECT_URL = "https://github.com/Snemege/mouse-buttons"
DEVELOPER_EMAIL = "snemege@gmail.com"
# servis -> pencere: "tuş_kodu değer" (1 = basıldı, 0 = bırakıldı) küçük mesajları
SOCKET_PATH = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "mouse-buttons.sock"
# Pencere, fare imleci "Tuş testi" bölümünün üzerindeyken bu dosyayı sürekli günceller.
# Dosya tazeyse (TEST_TTL saniyeden yeni) servis eylemleri ÇALIŞTIRMAZ; sadece renk yanar.
# Pencere kapanır ya da çökerse dosya bayatlar ve tuşlar kendiliğinden normale döner.
TEST_FLAG = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "mouse-buttons.test"
TEST_TTL = 2.0

# ------------------------------------------------------------ dil / language
# Metinler kaynakta Türkçe yazılır; T() seçili dil İngilizce ise sözlükten karşılığını verir.
SETTINGS = CONFIG_DIR / "settings.json"
LANG_CHOICES = ["auto", "tr", "en"]   # ayardaki değerler
LANGUAGE = "en"                       # o an kullanılan dil ("tr" ya da "en")

EN = {
    # tuşlar
    "Sol yan tuş (geri tuşu)": "Left side button (back)",
    "Sağ yan tuş (ileri tuşu)": "Right side button (forward)",
    "Orta tuş (tekerleğe basma)": "Middle button (wheel click)",
    "Ek tuş 1 (BTN_FORWARD)": "Extra button 1 (BTN_FORWARD)",
    "Ek tuş 2 (BTN_BACK)": "Extra button 2 (BTN_BACK)",
    "Ek tuş 3 (BTN_TASK)": "Extra button 3 (BTN_TASK)",
    "Sol tık": "Left click", "Sağ tık": "Right click", "Orta tuş": "Middle",
    "Sol yan": "Left side", "Sağ yan": "Right side",
    "Ek 1": "Extra 1", "Ek 2": "Extra 2", "Ek 3": "Extra 3",
    # eylemler
    "Varsayılan": "Default",
    "Önceki sanal masaüstü": "Previous workspace",
    "Sonraki sanal masaüstü": "Next workspace",
    "Etkinlikler ekranı": "Activities overview",
    "Geri (Alt+←)": "Back (Alt+←)",
    "İleri (Alt+→)": "Forward (Alt+→)",
    "Pencereyi kapat": "Close window",
    "Kopyala (Ctrl+C)": "Copy (Ctrl+C)",
    "Yapıştır (Ctrl+V)": "Paste (Ctrl+V)",
    "Oynat / duraklat": "Play / pause",
    "Sesi kapat / aç": "Mute / unmute",
    "Tuşu devre dışı bırak": "Disable button",
    "Özel kısayol…": "Custom shortcut…",
    "Uygulama aç…": "Launch app…",
    "Komut çalıştır…": "Run command…",
    # pencere
    "Tuş testi": "Button test",
    "Tuş testi — TEST MODU (eylemler kapalı)": "Button test — TEST MODE (actions off)",
    "Fare imlecini bu bölüme getirip tuşlara basın: tuşlar yalnızca renkle yanar, "
    "eylemler çalışmaz. İmleç bölümden çıkınca her şey normale döner.":
        "Move the pointer over this section and press buttons: they only light up and "
        "their actions do not run. Everything returns to normal when the pointer leaves.",
    "Son algılanan tuş": "Last detected button",
    "Henüz bir tuşa basılmadı": "No button pressed yet",
    "Mouse tuşları": "Mouse buttons",
    "Her tuşa ne yapacağını seçin. Değişiklikler anında geçerli olur.":
        "Choose what each button does. Changes apply immediately.",
    "Durum": "Status",
    "Arka plan servisi": "Background service",
    "Yakalanan fareler": "Captured mice",
    "Çalışıyor": "Running",
    "Çalışmıyor": "Not running",
    "Yok": "None",
    "Yok — mouse bağlı değil ya da erişim izni verilmemiş (README'deki kuruluma bakın)":
        "None — no mouse connected, or no access permission (see the installation section of the README)",
    "Arka plan servisi çalışmıyor; tuşlar çevrilmez.":
        "The background service is not running; buttons will not be remapped.",
    "Başlat": "Start",
    "Kısayol (örn. ctrl+alt+t)": "Shortcut (e.g. ctrl+alt+t)",
    "Komut (örn. firefox)": "Command (e.g. firefox)",
    "Uygulama": "Application",
    "Bir uygulama seçin…": "Choose an application…",
    "Tanınmayan tuş: kod {kod} ({ad}). Bu kodu listeye eklemek gerekir.":
        "Unrecognised button: code {kod} ({ad}). This code needs to be added to the list.",
    "normal çalışır (dokunulmuyor)": "works normally (left untouched)",
    "kısayol gönderir: {}": "sends shortcut: {}",
    "uygulama açar: {}": "launches app: {}",
    "uygulama açar (henüz seçilmedi)": "launches an app (none chosen yet)",
    "komut çalıştırır: {}": "runs command: {}",
    "  •  test alanı: eylem çalıştırılmadı": "  •  test area: action not run",
    "Geliştirici": "Developer",
    "Geri bildirim ve iletişim": "Feedback and contact",
    "Geri bildirim, hata bildirimi ve öneriler için bana yazabilirsiniz.":
        "You can write to me for feedback, bug reports and suggestions.",
    "E-postayı kopyala": "Copy email",
    "E-posta gönder": "Send email",
    "GitHub sayfası": "GitHub page",
    "Kapat": "Close",
}


def T(text):
    """Seçili dile göre metni döndürür (Türkçe kaynak metin -> gerekirse İngilizce)."""
    return EN.get(text, text) if LANGUAGE == "en" else text


def system_language():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return "tr" if value.lower().startswith("tr") else "en"
    return "en"


def load_settings():
    try:
        return json.loads(SETTINGS.read_text())
    except (OSError, ValueError):
        return {}


def save_settings(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(SETTINGS)


def set_language(choice):
    """choice: 'auto' | 'tr' | 'en'"""
    global LANGUAGE
    LANGUAGE = system_language() if choice not in ("tr", "en") else choice


# (evdev adı, ekranda görünen ad)
BUTTONS = [
    ("BTN_SIDE", "Sol yan tuş (geri tuşu)"),
    ("BTN_EXTRA", "Sağ yan tuş (ileri tuşu)"),
    ("BTN_MIDDLE", "Orta tuş (tekerleğe basma)"),
    ("BTN_FORWARD", "Ek tuş 1 (BTN_FORWARD)"),
    ("BTN_BACK", "Ek tuş 2 (BTN_BACK)"),
    ("BTN_TASK", "Ek tuş 3 (BTN_TASK)"),
]

# (kimlik, ekranda görünen ad, gönderilecek kısayol)
ACTIONS = [
    ("default", "Varsayılan", None),
    ("workspace_prev", "Önceki sanal masaüstü", "super+pageup"),
    ("workspace_next", "Sonraki sanal masaüstü", "super+pagedown"),
    ("overview", "Etkinlikler ekranı", "super"),
    ("back", "Geri (Alt+←)", "alt+left"),
    ("forward", "İleri (Alt+→)", "alt+right"),
    ("close", "Pencereyi kapat", "alt+f4"),
    ("copy", "Kopyala (Ctrl+C)", "ctrl+c"),
    ("paste", "Yapıştır (Ctrl+V)", "ctrl+v"),
    ("playpause", "Oynat / duraklat", "playpause"),
    ("mute", "Sesi kapat / aç", "mute"),
    ("disabled", "Tuşu devre dışı bırak", ""),
    ("keys", "Özel kısayol…", None),
    ("app", "Uygulama aç…", None),
    ("command", "Komut çalıştır…", None),
]
ACTION_KEYS = {a[0]: a[2] for a in ACTIONS}

KEY_ALIASES = {
    "ctrl": "KEY_LEFTCTRL", "control": "KEY_LEFTCTRL",
    "alt": "KEY_LEFTALT", "shift": "KEY_LEFTSHIFT",
    "super": "KEY_LEFTMETA", "win": "KEY_LEFTMETA", "meta": "KEY_LEFTMETA",
    "enter": "KEY_ENTER", "esc": "KEY_ESC", "space": "KEY_SPACE", "tab": "KEY_TAB",
    "del": "KEY_DELETE", "pgup": "KEY_PAGEUP", "pgdn": "KEY_PAGEDOWN",
}


def parse_keys(text):
    """'ctrl+alt+t' -> [tuş kodları]. Anlaşılmazsa None."""
    codes = []
    for part in (text or "").lower().replace(" ", "").split("+"):
        if not part:
            continue
        code = getattr(e, KEY_ALIASES.get(part, "KEY_" + part.upper()), None)
        if not isinstance(code, int):
            return None
        codes.append(code)
    return codes or None


# sanal masaüstü eylemi -> GNOME'daki karşılık gelen kısayol ayarı
WORKSPACE_SETTINGS = {
    "workspace_prev": "switch-to-workspace-left",
    "workspace_next": "switch-to-workspace-right",
}
ACCEL_MODS = {"super": "super", "alt": "alt", "control": "ctrl", "primary": "ctrl", "shift": "shift"}


def gnome_shortcut(action_id):
    """GNOME'un o an kullandığı masaüstü değiştirme kısayolunu ('super+pageup' gibi) döndürür.
    Okunamazsa ya da uygun kısayol yoksa None (o zaman varsayılan kullanılır)."""
    setting = WORKSPACE_SETTINGS.get(action_id)
    if not setting:
        return None
    try:
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.wm.keybindings", setting],
            capture_output=True, text=True, timeout=1).stdout.strip()
        accels = ast.literal_eval(out[3:].strip() if out.startswith("@as") else out)
    except (OSError, ValueError, SyntaxError, subprocess.SubprocessError):
        return None
    adaylar = []
    for accel in accels:
        mods = [ACCEL_MODS.get(m.lower()) for m in re.findall(r"<(\w+)>", accel)]
        tus = accel.rsplit(">", 1)[-1]
        if None in mods or tus.startswith("KP_"):  # tuş takımı kısayollarını atla
            continue
        text = "+".join(mods + [tus.replace("_", "").lower()])
        if parse_keys(text):
            adaylar.append((len(mods), text))
    # en az tuşlu olanı seç (örn. Super+PageUp, Super+Alt+Left'ten önce gelir)
    return min(adaylar, key=lambda a: a[0])[1] if adaylar else None


def load_config_file():
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- servis

def looks_like_mouse_sysfs(path):
    """İzin olmadan bile: bu event dosyası fare gibi mi? (göreli hareket var mı)"""
    try:
        rel = Path(f"/sys/class/input/{os.path.basename(path)}/device/capabilities/rel")
        return int(rel.read_text().strip().split()[-1], 16) != 0
    except (OSError, ValueError, IndexError):
        return False


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def find_desktop_file(desktop_id):
    """'firefox.desktop' -> kurulu uygulamanın .desktop dosyasının yolu (yoksa None)."""
    if not desktop_id:
        return None
    dirs = [Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")]
    dirs += [Path(d) for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":") if d]
    dirs += [Path("/var/lib/flatpak/exports/share"), Path.home() / ".local/share/flatpak/exports/share"]
    for d in dirs:
        f = d / "applications" / desktop_id
        if f.is_file():
            return f
    return None


def is_mouse(dev):
    caps = dev.capabilities()
    return e.EV_REL in caps and e.BTN_LEFT in caps.get(e.EV_KEY, [])


class Engine:
    def __init__(self):
        self.map = {}          # tuş kodu -> {"action":..., "value":...}
        self.mtime = -1
        self.tasks = {}        # event yolu -> asyncio görevi
        self.devices = {}      # event yolu -> fare adı
        self.perm_denied = False
        self.kbd = UInput(
            {e.EV_KEY: list(range(1, 249))}, name=f"{VIRTUAL_PREFIX} virtual keyboard"
        )
        self.bildirim = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.bildirim.setblocking(False)
        self.cocuklar = []     # başlattığımız uygulamalar (bitince temizlenir)
        self.dugum_kimligi = {}  # event yolu -> aygıt düğümünün oluşma zamanı (değiştiyse aygıt yenilenmiştir)

    def test_modu(self):
        """Pencerenin test alanı şu an açık mı? (bayrak dosyası taze mi)"""
        try:
            return time.time() - TEST_FLAG.stat().st_mtime < TEST_TTL
        except OSError:
            return False

    def bildir(self, code, value):
        """Basılan tuşu açık pencereye haber ver (pencere kapalıysa sessizce geç)."""
        if value == 2:  # tuş tekrarı
            return
        try:
            self.bildirim.sendto(f"{code} {value}".encode(), str(SOCKET_PATH))
        except OSError:
            pass

    def load_config(self):
        try:
            m = CONFIG.stat().st_mtime
        except FileNotFoundError:
            m = 0
        if m == self.mtime:
            return
        try:
            data = json.loads(CONFIG.read_text()) if m else {}
        except (OSError, ValueError):
            return  # yarım yazılmış dosya: eski ayar geçerli kalsın
        self.mtime = m
        new = {}
        for name, act in data.items():
            code = getattr(e, name, None)
            if isinstance(code, int) and isinstance(act, dict) and act.get("action") not in (None, "default"):
                new[code] = act
        self.map = new

    def spawn(self, coro):
        """Görevi başlat; ölürse nedenini günlüğe yaz (sessizce yutulmasın)."""
        task = asyncio.create_task(coro)

        def bitti(t):
            if not t.cancelled() and t.exception():
                log("TASK CRASHED:", "".join(traceback.format_exception(t.exception())))

        task.add_done_callback(bitti)
        return task

    def baslat(self, argv):
        """Uygulamayı servisten bağımsız bir systemd kapsamında başlat: servis yeniden
        başlatılınca ya da durdurulunca açtığı uygulamalar kapanmasın."""
        self.cocuklar.append(subprocess.Popen(
            ["systemd-run", "--user", "--scope", "--collect", "--quiet", *argv],
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

    async def perform(self, act):
        kind = act.get("action")
        if kind == "command":
            cmd = (act.get("value") or "").strip()
            if cmd:
                self.baslat(["sh", "-c", cmd])
            return
        if kind == "app":
            path = find_desktop_file(act.get("value"))
            if path:
                self.baslat(["gio", "launch", str(path)])
            else:
                log(f"app not found: {act.get('value')!r}")
            return
        if kind in WORKSPACE_SETTINGS:
            text = await asyncio.to_thread(gnome_shortcut, kind) or ACTION_KEYS.get(kind)
        else:
            text = act.get("value") if kind == "keys" else ACTION_KEYS.get(kind)
        keys = parse_keys(text)
        if not keys:
            return
        for k in keys:
            self.kbd.write(e.EV_KEY, k, 1)
            self.kbd.syn()
        await asyncio.sleep(0.02)
        for k in reversed(keys):
            self.kbd.write(e.EV_KEY, k, 0)
            self.kbd.syn()

    async def run_device(self, dev):
        ui = None
        try:
            ui = UInput.from_device(dev, name=f"{VIRTUAL_PREFIX} – {dev.name}")
            dev.grab()
            self.devices[dev.path] = dev.name
            log(f"{dev.name}: grabbed")
            async for ev in dev.async_read_loop():
                if ev.type == e.EV_KEY:
                    self.bildir(ev.code, ev.value)
                    act = self.map.get(ev.code)
                    if act is not None:
                        if ev.value == 1 and not self.test_modu():
                            self.spawn(self.perform(act))
                        continue  # tuşu yut: uygulamaya "geri/ileri" gitmesin
                ui.write_event(ev)
        except OSError as ex:
            log(f"{dev.name}: released ({ex})")  # çıkarıldı ya da başkası tuttu; tekrar denenir
        finally:
            log(f"{dev.name}: forwarding ended")
            self.devices.pop(dev.path, None)
            for fn in (dev.ungrab, dev.close):
                try:
                    fn()
                except OSError:
                    pass
            if ui:
                ui.close()

    def scan(self):
        self.perm_denied = False
        # evdev.list_devices() izni olmayanları gizler; izin sorununu görebilmek için kendimiz tarıyoruz
        for path in sorted(glob.glob("/dev/input/event*")):
            task = self.tasks.get(path)
            if task and not task.done():
                # Fare çıkarılıp takıldıysa aynı yol yeni bir aygıta verilmiş olabilir; o durumda
                # eski (ölü) görevi bırak, bir sonraki taramada yenisi yakalanır.
                try:
                    kimlik = os.stat(path).st_ctime_ns
                except OSError:
                    kimlik = None
                if kimlik != self.dugum_kimligi.get(path):
                    log(f"{path}: device replaced, will be grabbed again")
                    task.cancel()
                continue
            try:
                dev = InputDevice(path)
            except PermissionError:
                if looks_like_mouse_sysfs(path):
                    self.perm_denied = True
                continue
            except OSError:
                continue
            if dev.name.startswith(VIRTUAL_PREFIX) or not is_mouse(dev):
                dev.close()
                continue
            try:
                self.dugum_kimligi[path] = os.stat(path).st_ctime_ns
            except OSError:
                dev.close()
                continue
            self.tasks[path] = self.spawn(self.run_device(dev))
        # artık var olmayan yolların görevlerini temizle (fare çıkarıldı)
        for path, task in list(self.tasks.items()):
            if not os.path.exists(path):
                if not task.done():
                    log(f"{path}: device removed")
                    task.cancel()
                del self.tasks[path]
                self.dugum_kimligi.pop(path, None)

    def write_status(self):
        data = {
            "zaman": time.time(),
            "fareler": sorted(self.devices.values()),
            "izin_yok": self.perm_denied,
            "kural_sayisi": len(self.map),
        }
        tmp = STATUS.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(STATUS)

    async def run(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tick = 0
        while True:
            self.load_config()
            self.cocuklar = [p for p in self.cocuklar if p.poll() is None]  # biteni topla
            if tick % 3 == 0:
                self.scan()
            self.write_status()
            tick += 1
            await asyncio.sleep(1)


# ------------------------------------------------------------------ arayüz

def run_gui():
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gio, GLib, Gtk

    set_language(load_settings().get("language", "auto"))

    CSS = """
    .tus-etiket { padding: 12px 6px; border-radius: 10px; font-weight: 600;
                  background: alpha(currentColor, 0.08); }
    .tus-etiket.basili { background: @accent_bg_color; color: @accent_fg_color; }
    .tus-satir-basili { background: alpha(@accent_bg_color, 0.30); }
    .test-alani { border-radius: 12px; padding: 6px; }
    .test-alani-aktif { background: alpha(@accent_bg_color, 0.16); }
    """
    # canlı test kutucukları: (evdev adı, ekranda görünen kısa ad)
    TILES = [
        ("BTN_LEFT", "Sol tık"), ("BTN_RIGHT", "Sağ tık"), ("BTN_MIDDLE", "Orta tuş"),
        ("BTN_SIDE", "Sol yan"), ("BTN_EXTRA", "Sağ yan"),
        ("BTN_FORWARD", "Ek 1"), ("BTN_BACK", "Ek 2"), ("BTN_TASK", "Ek 3"),
    ]
    ACTION_LABELS = {a[0]: a[1] for a in ACTIONS}
    TEST_ACIKLAMA = ("Fare imlecini bu bölüme getirip tuşlara basın: tuşlar yalnızca renkle yanar, "
                     "eylemler çalışmaz. İmleç bölümden çıkınca her şey normale döner.")
    DIL_SECENEKLERI = ["Auto / Otomatik", "Türkçe", "English"]   # her dil kendi adıyla (çevrilmez)

    class Pencere(Adw.ApplicationWindow):
        def __init__(self, app):
            super().__init__(application=app, title="Mouse Buttons",
                             default_width=640, default_height=820)
            Gtk.Window.set_default_icon_name(APP_ID)  # görev çubuğunda kendi simgemiz görünsün
            self.config = load_config_file()
            # kurulu uygulamalar: [(desktop kimliği, görünen ad)], ada göre sıralı
            self.uygulamalar = sorted(
                ((a.get_id(), a.get_name()) for a in Gio.AppInfo.get_all()
                 if a.should_show() and a.get_id()),
                key=lambda x: x[1].casefold())
            self.uygulama_adi = dict(self.uygulamalar)

            css = Gtk.CssProvider()
            try:
                css.load_from_string(CSS)
            except AttributeError:  # eski GTK
                css.load_from_data(CSS.encode())
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

            self.test_aktif = False
            self.test_zamanlayici = None
            self.arayuz_kur()
            GLib.timeout_add_seconds(2, self.durum_guncelle)

            # servisten gelen "şu tuşa basıldı" mesajlarını dinle
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            try:
                SOCKET_PATH.unlink()
            except FileNotFoundError:
                pass
            self.sock.bind(str(SOCKET_PATH))
            GLib.io_add_watch(self.sock.fileno(), GLib.PRIORITY_DEFAULT,
                              GLib.IOCondition.IN, self.tus_geldi)
            self.connect("close-request", self.kapaniyor)

        def arayuz_kur(self):
            """Pencerenin içini seçili dilde kurar; dil değişince yeniden çağrılır."""
            if hasattr(self, "test_grup"):
                self.test_kapat()
            self.satirlar = {}   # tuş kodu -> ayar satırı (basınca renklenir)
            self.etiketler = {}  # tuş kodu -> test kutucuğu
            self.basma_no = {}   # tuş kodu -> son basış sayacı (ışığı geç söndürmek için)
            self.kod_adi = {getattr(e, n): n for n, _ in TILES}
            self.kisa_ad = {getattr(e, n): T(t) for n, t in TILES}

            view = Adw.ToolbarView()
            view.add_top_bar(Adw.HeaderBar())
            self.banner = Adw.Banner(revealed=False)
            self.banner.connect("button-clicked", self.servisi_baslat)
            view.add_top_bar(self.banner)

            page = Adw.PreferencesPage()

            test = Adw.PreferencesGroup(title=T("Tuş testi"), description=T(TEST_ACIKLAMA))
            self.test_grup = test
            # imleç bu bölümün üzerindeyken servise "eylem çalıştırma" bayrağı gönder
            hareket = Gtk.EventControllerMotion()
            hareket.connect("notify::contains-pointer", self.test_alani_degisti)
            test.add_controller(hareket)
            flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                               min_children_per_line=2, max_children_per_line=4,
                               row_spacing=6, column_spacing=6)
            flow.add_css_class("test-alani")
            self.test_kutu = flow
            for name, text in TILES:
                lbl = Gtk.Label(label=T(text), hexpand=True)
                lbl.add_css_class("tus-etiket")
                flow.append(lbl)
                self.etiketler[getattr(e, name)] = lbl
            test.add(flow)
            self.son_row = Adw.ActionRow(title=T("Son algılanan tuş"),
                                         subtitle=T("Henüz bir tuşa basılmadı"))
            self.son_row.set_subtitle_lines(2)
            self.son_row.set_size_request(-1, 80)
            test.add(self.son_row)
            page.add(test)

            grup = Adw.PreferencesGroup(
                title=T("Mouse tuşları"),
                description=T("Her tuşa ne yapacağını seçin. Değişiklikler anında geçerli olur."))
            for code, label in BUTTONS:
                self.satir_ekle(grup, code, T(label))
            page.add(grup)

            durum = Adw.PreferencesGroup(title=T("Durum"))
            self.servis_row = Adw.ActionRow(title=T("Arka plan servisi"))
            self.fare_row = Adw.ActionRow(title=T("Yakalanan fareler"))
            self.fare_row.set_subtitle_lines(2)
            self.fare_row.set_size_request(-1, 80)
            durum.add(self.servis_row)
            durum.add(self.fare_row)
            page.add(durum)

            dil = Adw.PreferencesGroup()
            self.dil_row = Adw.ComboRow(title="Language / Dil")
            self.dil_row.set_model(Gtk.StringList.new(DIL_SECENEKLERI))
            secim = load_settings().get("language", "auto")
            self.dil_row.set_selected(LANG_CHOICES.index(secim) if secim in LANG_CHOICES else 0)
            self.dil_row.connect("notify::selected", self.dil_degisti)
            dil.add(self.dil_row)
            gelistirici = Adw.ActionRow(title=T("Geliştirici"), subtitle=T("Geri bildirim ve iletişim"),
                                        activatable=True)
            gelistirici.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            gelistirici.connect("activated", self.gelistirici_goster)
            dil.add(gelistirici)
            page.add(dil)

            view.set_content(page)
            self.set_content(view)
            self.durum_guncelle()

        def gelistirici_goster(self, *_):
            govde = (T("Geri bildirim, hata bildirimi ve öneriler için bana yazabilirsiniz.")
                     + f"\n\n{DEVELOPER_EMAIL}\n{PROJECT_URL}")
            diyalog_sinifi = Adw.AlertDialog if hasattr(Adw, "AlertDialog") else Adw.MessageDialog
            diyalog = (diyalog_sinifi(heading=T("Geliştirici"), body=govde) if diyalog_sinifi is Adw.AlertDialog
                       else Adw.MessageDialog(transient_for=self, heading=T("Geliştirici"), body=govde))
            for kimlik, yazi in (("kopyala", "E-postayı kopyala"), ("gonder", "E-posta gönder"),
                                 ("github", "GitHub sayfası"), ("kapat", "Kapat")):
                diyalog.add_response(kimlik, T(yazi))
            diyalog.set_default_response("kapat")
            diyalog.set_close_response("kapat")
            diyalog.connect("response", self.gelistirici_yanit)
            diyalog.present(self) if diyalog_sinifi is Adw.AlertDialog else diyalog.present()
            self.diyalog = diyalog  # elde tut

        def gelistirici_yanit(self, _diyalog, cevap):
            if cevap == "kopyala":
                # metni birkaç standart metin biçiminde sun: her uygulama yapıştırabilsin
                veri = GLib.Bytes.new(DEVELOPER_EMAIL.encode())
                Gdk.Display.get_default().get_clipboard().set_content(Gdk.ContentProvider.new_union([
                    Gdk.ContentProvider.new_for_bytes(mime, veri)
                    for mime in ("text/plain;charset=utf-8", "text/plain", "UTF8_STRING")]))
            elif cevap == "gonder":
                Gio.AppInfo.launch_default_for_uri(f"mailto:{DEVELOPER_EMAIL}", None)
            elif cevap == "github":
                Gio.AppInfo.launch_default_for_uri(PROJECT_URL, None)

        def dil_degisti(self, satir, _pspec):
            secim = LANG_CHOICES[satir.get_selected()]
            ayar = load_settings()
            if ayar.get("language", "auto") == secim:
                return
            ayar["language"] = secim
            save_settings(ayar)
            set_language(secim)
            # pencere öğesini kendi sinyalinin içinde yıkmamak için işi sıraya al
            GLib.idle_add(self.arayuz_kur)

        def test_alani_degisti(self, kontrol, _pspec):
            if kontrol.props.contains_pointer:
                self.test_aktif = True
                self.test_bayragi_yenile()
                if self.test_zamanlayici is None:
                    self.test_zamanlayici = GLib.timeout_add(500, self.test_bayragi_yenile)
                self.test_kutu.add_css_class("test-alani-aktif")
                self.test_grup.set_title(T("Tuş testi — TEST MODU (eylemler kapalı)"))
            else:
                self.test_kapat()

        def test_bayragi_yenile(self):
            try:
                TEST_FLAG.touch()  # "hâlâ test alanındayım" işareti (dosya zamanını günceller)
            except OSError:
                pass
            return self.test_aktif

        def test_kapat(self):
            self.test_aktif = False
            if self.test_zamanlayici is not None:
                GLib.source_remove(self.test_zamanlayici)
                self.test_zamanlayici = None
            try:
                TEST_FLAG.unlink()
            except OSError:
                pass
            self.test_kutu.remove_css_class("test-alani-aktif")
            self.test_grup.set_title(T("Tuş testi"))

        def kapaniyor(self, *_):
            self.test_kapat()
            try:
                SOCKET_PATH.unlink()
            except OSError:
                pass
            return False

        def tus_geldi(self, *_):
            while True:
                try:
                    data = self.sock.recv(64)
                except BlockingIOError:
                    break
                try:
                    code, value = (int(x) for x in data.split())
                except ValueError:
                    continue
                self.tus_isle(code, value)
            return True

        def isik(self, code, yansin):
            for widget, sinif in ((self.etiketler.get(code), "basili"),
                                  (self.satirlar.get(code), "tus-satir-basili")):
                if widget:
                    (widget.add_css_class if yansin else widget.remove_css_class)(sinif)

        def tus_isle(self, code, value):
            if value == 1:
                self.basma_no[code] = self.basma_no.get(code, 0) + 1
                self.isik(code, True)
                bilgi = self.eylem_aciklamasi(code)
                atanmis = self.config.get(self.kod_adi.get(code), {}).get("action", "default") != "default"
                if self.test_aktif and atanmis:
                    bilgi += T("  •  test alanı: eylem çalıştırılmadı")
                self.son_row.set_subtitle(bilgi)
            elif value == 0:
                no = self.basma_no.get(code, 0)

                def sondur():
                    if self.basma_no.get(code) == no:  # arada yeniden basılmadıysa
                        self.isik(code, False)
                    return False

                GLib.timeout_add(200, sondur)  # çok kısa tıklamalar da görünsün

        def eylem_aciklamasi(self, code):
            ad = self.kod_adi.get(code)
            if ad is None:
                evdev_adi = e.BTN.get(code) or e.KEY.get(code) or "?"
                if isinstance(evdev_adi, list):
                    evdev_adi = evdev_adi[0]
                return T("Tanınmayan tuş: kod {kod} ({ad}). Bu kodu listeye eklemek gerekir.").format(
                    kod=code, ad=evdev_adi)
            kayit = self.config.get(ad, {})
            aid = kayit.get("action", "default")
            deger = kayit.get("value", "")
            if aid == "default":
                sonuc = T("normal çalışır (dokunulmuyor)")
            elif aid == "keys":
                sonuc = T("kısayol gönderir: {}").format(deger)
            elif aid == "app":
                uyg = self.uygulama_adi.get(deger)
                sonuc = T("uygulama açar: {}").format(uyg) if uyg else T("uygulama açar (henüz seçilmedi)")
            elif aid == "command":
                sonuc = T("komut çalıştırır: {}").format(deger)
            else:
                sonuc = T(ACTION_LABELS.get(aid, aid))
            return f"{self.kisa_ad[code]} ({ad})  →  {sonuc}"

        def satir_ekle(self, grup, code, label):
            kayit = self.config.get(code, {})
            ids = [a[0] for a in ACTIONS]
            combo = Adw.ComboRow(title=label, subtitle=code)
            self.satirlar[getattr(e, code)] = combo
            combo.set_model(Gtk.StringList.new([T(a[1]) for a in ACTIONS]))
            combo.set_selected(ids.index(kayit["action"]) if kayit.get("action") in ids else 0)
            entry = Adw.EntryRow()
            entry.set_text(kayit.get("value", "") if kayit.get("action") != "app" else "")

            # "Uygulama aç" için aranabilir uygulama listesi (0. sıra: henüz seçilmedi)
            app_ids = [""] + [i for i, _ in self.uygulamalar]
            app_row = Adw.ComboRow(title=T("Uygulama"), enable_search=True)
            app_row.set_model(Gtk.StringList.new(
                [T("Bir uygulama seçin…")] + [n for _, n in self.uygulamalar]))
            app_row.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
            if kayit.get("action") == "app" and kayit.get("value") in app_ids:
                app_row.set_selected(app_ids.index(kayit["value"]))

            def gorunum():
                aid = ids[combo.get_selected()]
                app_row.set_visible(aid == "app")
                entry.set_visible(aid in ("keys", "command"))
                entry.set_title(T("Kısayol (örn. ctrl+alt+t)") if aid == "keys"
                                else T("Komut (örn. firefox)"))
                gecersiz = aid == "keys" and entry.get_text() and parse_keys(entry.get_text()) is None
                (entry.add_css_class if gecersiz else entry.remove_css_class)("error")

            def degisti(*_):
                gorunum()
                aid = ids[combo.get_selected()]
                if aid == "default":
                    self.config.pop(code, None)
                else:
                    deger = app_ids[app_row.get_selected()] if aid == "app" else entry.get_text()
                    self.config[code] = {"action": aid, "value": deger}
                self.kaydet()

            combo.connect("notify::selected", degisti)
            app_row.connect("notify::selected", degisti)
            entry.connect("changed", degisti)
            gorunum()
            grup.add(combo)
            grup.add(app_row)
            grup.add(entry)

        def kaydet(self):
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = CONFIG.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.config, indent=2, ensure_ascii=False))
            tmp.replace(CONFIG)

        def servisi_baslat(self, *_):
            subprocess.run(["systemctl", "--user", "enable", "--now", "mouse-buttons.service"])
            self.durum_guncelle()

        def durum_guncelle(self):
            try:
                st = json.loads(STATUS.read_text())
            except (OSError, ValueError):
                st = None
            calisiyor = bool(st) and time.time() - st["zaman"] < 6
            self.servis_row.set_subtitle(T("Çalışıyor") if calisiyor else T("Çalışmıyor"))
            fareler = st["fareler"] if calisiyor else []
            if fareler:
                metin = ", ".join(fareler)
            elif calisiyor and st["izin_yok"]:
                metin = T("Yok — mouse bağlı değil ya da erişim izni verilmemiş (README'deki kuruluma bakın)")
            else:
                metin = T("Yok")
            self.fare_row.set_subtitle(metin)
            if not calisiyor:
                self.banner.set_title(T("Arka plan servisi çalışmıyor; tuşlar çevrilmez."))
                self.banner.set_button_label(T("Başlat"))
                self.banner.set_revealed(True)
            else:
                self.banner.set_revealed(False)
            return True

    app = Adw.Application(application_id=APP_ID)
    app.connect("activate", lambda a: (a.props.active_window or Pencere(a)).present())
    app.run(None)


def single_instance_lock():
    """Servisin ikinci kopyası açılmasın (iki kopya aynı fareyi tutmaya çalışır).
    Kilit dosyası açık kaldığı sürece geçerlidir; süreç bitince kendiliğinden kalkar."""
    import fcntl
    handle = open(Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "mouse-buttons.lock", "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return handle


if __name__ == "__main__":
    if "--version" in sys.argv:
        print(f"Mouse Buttons {VERSION}")
    elif "--servis" in sys.argv:
        lock = single_instance_lock()
        if lock is None:
            log("another instance of the service is already running; exiting")
            sys.exit(0)
        asyncio.run(Engine().run())
    else:
        run_gui()
