#!/usr/bin/env python3
"""ISO-X first-run welcome panel. GTK 3 only; no shell execution or telemetry."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

APP_NAME = "ISO-X"
DEVELOPER = "عبدالله لازم"
LOGO_CANDIDATES = (
    Path("/usr/share/iso-x/assets/iso-x-dragon.png"),
    Path("/usr/share/iso-x/assets/iso-x-dragon.svg"),
)

# Every action is an argument vector. Do not use shell=True for user-facing commands.
ACTIONS = {
    "browser": (["firefox-esr"], ["netsurf-gtk"]),
    "files": (["thunar"],),
    "applications": (["/usr/bin/python3", "/usr/share/iso-x/isox_appcenter.py"],),
    "settings": (["xfce4-settings-manager"],),
    "network": (["nm-connection-editor"],),
    "installer": (["debian-installer-launcher"],),
    "monitor": (["xfce4-taskmanager"],),
    "terminal": (["xfce4-terminal"],),
    "cinematic": (["/usr/local/bin/isox-cinematic"],),
}

CSS = b"""
window { background: #080d17; color: #edf7ff; }
headerbar { background: #101a2a; color: #edf7ff; border-bottom: 1px solid #173b58; }
.title { color: #00c8ff; font-weight: 700; }
.subtitle { color: #b4c5da; }
.card { background: #101a2a; border: 1px solid #203b55; border-radius: 12px; padding: 12px; }
button.action { background: #102b42; color: #f1f8ff; border: 1px solid #24628b; border-radius: 9px; padding: 10px; }
button.action:hover { background: #124365; border-color: #00c8ff; }
button.install { background: #07568a; color: white; border: 1px solid #12b9f5; border-radius: 9px; padding: 10px; }
label.muted { color: #a8b8cb; }
"""


def command_candidates(key: str) -> list[list[str]]:
    return list(ACTIONS[key])


def find_available_command(candidates: list[list[str]]) -> list[str] | None:
    for argv in candidates:
        exe = argv[0]
        if os.path.isabs(exe):
            if os.path.isfile(exe) and os.access(exe, os.X_OK):
                return argv
        elif shutil.which(exe):
            return argv
    return None


def memory_summary() -> str:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            if k in ("MemTotal", "MemAvailable"):
                values[k] = int(v.strip().split()[0]) * 1024
        if "MemTotal" not in values:
            return "الذاكرة: غير متاحة"
        total = values["MemTotal"] / (1024 ** 3)
        free = values.get("MemAvailable")
        return f"RAM: {total:.1f} GB" + (f" · المتاح {free/(1024**3):.1f} GB" if free else "")
    except (OSError, ValueError, IndexError):
        return "الذاكرة: غير متاحة"


def system_summary() -> str:
    root = shutil.disk_usage("/")
    free_gib = root.free / (1024 ** 3)
    return (
        f"النظام: {platform.system()} {platform.release()}\n"
        f"المعمارية: {platform.machine()} · المعالجات: {os.cpu_count() or 'غير معروف'}\n"
        f"{memory_summary()}\n"
        f"المساحة الحرة في النظام: {free_gib:.1f} GB"
    )


class WelcomeWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="ISO-X | مرحباً بك")
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)
        self.set_default_size(860, 650)
        self.set_size_request(580, 480)
        self.set_border_width(18)
        self.set_position(Gtk.WindowPosition.CENTER)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(outer)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header.set_halign(Gtk.Align.CENTER)
        logo = self._load_logo()
        if logo is not None:
            logo.set_pixel_size(92)
            header.pack_start(logo, False, False, 0)
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label()
        title.set_markup('<span size="xx-large" weight="bold" foreground="#00c8ff">ISO-X</span>')
        title.set_xalign(1)
        subtitle = Gtk.Label(label="نظام خفيف بواجهة مألوفة وأدوات أساسية جاهزة")
        subtitle.get_style_context().add_class("subtitle")
        subtitle.set_xalign(1)
        names.pack_start(title, False, False, 0)
        names.pack_start(subtitle, False, False, 0)
        header.pack_start(names, False, False, 0)
        outer.pack_start(header, False, False, 0)

        rule = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(rule, False, False, 0)

        intro = Gtk.Label(label="أهلاً بك في نسختك من ISO-X. اختر ما تريد فتحه من الأدوات أدناه.")
        intro.set_line_wrap(True)
        intro.set_xalign(1)
        outer.pack_start(intro, False, False, 0)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_column_homogeneous(True)
        button_data = [
            ("الإنترنت والمتصفح", "browser", "web-browser", False),
            ("الملفات", "files", "system-file-manager", False),
            ("مركز التطبيقات", "applications", "system-software-install", False),
            ("إعدادات النظام", "settings", "preferences-system", False),
            ("إعدادات الشبكة", "network", "network-wired", False),
            ("مراقبة النظام", "monitor", "utilities-system-monitor", False),
            ("الطرفية", "terminal", "utilities-terminal", False),
            ("تثبيت ISO-X على القرص", "installer", "drive-harddisk", True),
        ]
        if find_available_command(command_candidates("cinematic")):
            button_data.insert(1, ("مشهد ISO-X الاختياري", "cinematic", "applications-graphics", False))
        for i, (label, key, icon_name, is_install) in enumerate(button_data):
            btn = Gtk.Button()
            btn.get_style_context().add_class("install" if is_install else "action")
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
            text = Gtk.Label(label=label)
            text.set_xalign(1)
            content.pack_start(icon, False, False, 0)
            content.pack_start(text, True, True, 0)
            btn.add(content)
            btn.set_tooltip_text("قبل التثبيت، احتفظ بنسخة احتياطية من ملفاتك" if is_install else label)
            btn.connect("clicked", self._run_action, key)
            grid.attach(btn, i % 2, i // 2, 1, 1)
        outer.pack_start(grid, True, True, 0)

        info_frame = Gtk.Frame(label="معلومات الجهاز")
        info_label = Gtk.Label(label=system_summary())
        info_label.set_xalign(0)
        info_label.set_selectable(True)
        info_label.set_margin_start(12)
        info_label.set_margin_end(12)
        info_label.set_margin_top(8)
        info_label.set_margin_bottom(8)
        info_frame.add(info_label)
        outer.pack_start(info_frame, False, False, 0)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        help_btn = Gtk.Button(label="دليل الاستخدام والمصادر")
        help_btn.get_style_context().add_class("action")
        help_btn.connect("clicked", self._show_sources)
        close_btn = Gtk.Button(label="إغلاق")
        close_btn.get_style_context().add_class("action")
        close_btn.connect("clicked", lambda *_: self.destroy())
        footer.pack_start(help_btn, False, False, 0)
        footer.pack_end(close_btn, False, False, 0)
        outer.pack_start(footer, False, False, 0)
        self.show_all()

    @staticmethod
    def _load_logo():
        # Scale before handing the pixbuf to GTK: set_pixel_size() does not
        # resize an arbitrary full-size PNG loaded from a file.
        for path in LOGO_CANDIDATES:
            if path.is_file():
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(path), 96, 96, True
                    )
                    return Gtk.Image.new_from_pixbuf(pixbuf)
                except GLib.Error:
                    pass
        return None

    def _run_action(self, _button, key: str):
        candidates = command_candidates(key)
        argv = find_available_command(candidates)
        if argv is None:
            names = ", ".join(items[0] for items in candidates)
            self._message(Gtk.MessageType.WARNING, "الأداة غير متوفرة", f"لم أجد الأمر: {names}\nقد تكون الحزمة غير مثبتة.")
            return
        if key == "installer":
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text="تثبيت ISO-X على القرص",
            )
            dialog.format_secondary_text(
                "قد يغيّر التثبيت أقسام القرص ويمسح البيانات حسب الخيارات المختارة. "
                "تأكد من وجود نسخة احتياطية قبل المتابعة. هل تريد فتح المثبّت؟"
            )
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
        try:
            process = subprocess.Popen(argv, close_fds=True, start_new_session=True)
            if key == "cinematic":
                threading.Thread(target=self._monitor_cinematic, args=(process,), daemon=True).start()
        except OSError as exc:
            self._message(Gtk.MessageType.ERROR, "تعذر فتح الأداة", f"{argv[0]}\n{exc}")

    def _monitor_cinematic(self, process):
        result = process.wait()
        if result:
            GLib.idle_add(
                self._message, Gtk.MessageType.WARNING, "تعذر تشغيل المشهد الاختياري",
                "أُغلقت العملية أو تعذر بدء العرض الرسومي. بقيت لوحة الترحيب متاحة؛ يمكنك متابعة استخدام ISO-X.",
            )

    def _show_sources(self, *_args):
        msg = (
            "ISO-X إصدار مخصص من إعداد عبدالله لازم.\n\n"
            "هذه الواجهة تستعير أفكاراً عامة من سهولة استخدام سطح مكتب Windows، "
            "لكنها تعمل على Debian/Linux ولا تتضمن ملفات Windows أو شعار Microsoft.\n\n"
            "يمكنك مراجعة /usr/share/doc/iso-x/README_AR.md والمستند "
            "THIRD_PARTY_NOTICES.md للحصول على المكونات ومصادرها.\n\n"
            "لا يوجد إرسال بيانات استخدام عن بعد من لوحة الترحيب هذه."
        )
        self._message(Gtk.MessageType.INFO, "عن ISO-X", msg)

    def _message(self, kind, title, body):
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=kind,
            buttons=Gtk.ButtonsType.CLOSE, text=title,
        )
        dlg.format_secondary_text(body)
        dlg.run()
        dlg.destroy()


def main() -> int:
    win = WelcomeWindow()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
