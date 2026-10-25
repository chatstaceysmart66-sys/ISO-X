#!/usr/bin/env python3
"""ISO-X Store: a GTK 3 interface to the system's configured package sources."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

from isox_store_backend import OperationResult, StoreApp, StoreBackend


APP_NAME = "ISO-X Store"
DEVELOPER = "عبدالله لازم"
SOUND_DIR = Path("/usr/share/iso-x/assets/sounds")
SOUND_FILES = {
    "notification": "notification.wav",
    "success": "success.wav",
    "error": "error.wav",
    "warning": "warning.wav",
    "download-complete": "download-complete.wav",
}
SETTINGS_PATH = Path.home() / ".config/iso-x/store.json"
DEFAULT_SETTINGS = {"sounds_enabled": True, "sound_volume": 0.35, "theme": "dark", "language": "auto"}
LANGUAGE_OVERRIDE = "auto"
SUPPORTED_CATEGORIES = (
    ("All", "الكل", "All"),
    ("Education", "الدراسة والتعليم", "Study & Education"),
    ("Office", "المستندات والمكتب وPDF", "Documents, Office & PDF"),
    ("Internet", "الإنترنت والتواصل", "Internet & Communication"),
    ("Graphics", "الصور والرسم والتصميم", "Graphics & Design"),
    ("Media", "الفيديو والصوت", "Video & Audio"),
    ("Development", "البرمجة والطرفية", "Development & Terminal"),
    ("System", "الشبكة وأدوات النظام", "Network & System"),
    ("Games", "الألعاب", "Games"),
    ("Windows", "تطبيقات Windows", "Windows Apps"),
    ("Installed", "المثبتة", "Installed"),
)
CSS = b"""
window { background: #0b1020; color: #edf4ff; }
window.light { background: #f1f5fa; color: #142236; }
headerbar { background: #101a2d; color: #f2f7ff; border-bottom: 1px solid #234264; }
headerbar .title { color: #55c9ff; font-weight: 700; }
button { border-radius: 9px; padding: 7px 11px; }
button.suggested-action { background: #0879b7; color: #fff; }
button.destructive-action { background: #8f3248; color: #fff; }
frame.card { background: #111b2e; border: 1px solid #253955; border-radius: 13px; }
frame.card > border { border: 0; }
label.muted { color: #a9b9d0; }
label.brand { color: #35c4ff; font-weight: 700; }
list { background: transparent; }
list row { border-radius: 8px; padding: 4px; }
list row:selected { background: #143c5c; }
"""
LIGHT_CSS = b"""
window.light headerbar { background: #ffffff; color: #142236; border-bottom: 1px solid #c8d8e8; }
window.light frame.card { background: #ffffff; border-color: #c9d8e8; }
window.light label.muted { color: #536579; }
window.light list row:selected { background: #d3eaff; }
"""


def _is_arabic() -> bool:
    if LANGUAGE_OVERRIDE in ("ar", "en"):
        return LANGUAGE_OVERRIDE == "ar"
    language = os.environ.get("LANGUAGE", os.environ.get("LANG", ""))
    return language.lower().startswith("ar")


def _text(arabic: str, english: str) -> str:
    return arabic if _is_arabic() else english


def _load_settings() -> dict[str, object]:
    try:
        value = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    if not isinstance(value, dict):
        return dict(DEFAULT_SETTINGS)
    result = dict(DEFAULT_SETTINGS)
    if isinstance(value.get("sounds_enabled"), bool):
        result["sounds_enabled"] = value["sounds_enabled"]
    if isinstance(value.get("sound_volume"), (int, float)) and not isinstance(value["sound_volume"], bool):
        result["sound_volume"] = max(0.0, min(1.0, float(value["sound_volume"])))
    if value.get("theme") in ("dark", "light"):
        result["theme"] = value["theme"]
    if value.get("language") in ("auto", "ar", "en"):
        result["language"] = value["language"]
    return result


def _save_settings(settings: dict[str, object]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".store-", dir=SETTINGS_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, SETTINGS_PATH)
    except OSError:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


class StoreWindow(Gtk.Window):
    def __init__(self, backend: StoreBackend | None = None):
        super().__init__(title=APP_NAME)
        self.backend = backend or StoreBackend()
        self.settings = _load_settings()
        global LANGUAGE_OVERRIDE
        LANGUAGE_OVERRIDE = str(self.settings["language"])
        self.set_default_size(1120, 660)
        self.set_size_request(780, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self._on_delete_event)
        logo_path = Path("/usr/share/iso-x/assets/iso-x-dragon.png")
        if logo_path.is_file():
            try:
                self.set_icon_from_file(str(logo_path))
            except GLib.Error:
                self.set_icon_name("applications-other")
        else:
            self.set_icon_name("applications-other")
        direction = Gtk.TextDirection.RTL if _is_arabic() else Gtk.TextDirection.LTR
        Gtk.Widget.set_default_direction(direction)
        self._install_css()

        self.busy = False
        self.package_operation_active = False
        self.generation = 0
        self.current_page = "home"
        self.current_category = "All"
        self.current_source = "All"
        self.search_text = ""
        self.apps: list[StoreApp] = []
        self.pending_updates: list[str] = []
        self.operation_history: list[tuple[str, str, str]] = []
        self._build_ui()
        self._refresh_catalog()

    def _on_delete_event(self, *_args) -> bool:
        if self.package_operation_active:
            self.status.set_text(_text(
                "انتظر اكتمال عملية الحزم قبل إغلاق المتجر.",
                "Wait for the package operation to finish before closing the store.",
            ))
            return True
        return False

    @staticmethod
    def _quit_main_loops() -> bool:
        level = Gtk.main_level()
        if level == 0:
            return False
        Gtk.main_quit()
        return level > 1

    def _on_destroy(self, *_args) -> None:
        if Gtk.main_level() > 0:
            GLib.idle_add(self._quit_main_loops)

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS + LIGHT_CSS)
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        if self.settings["theme"] == "light":
            self.get_style_context().add_class("light")

    def _build_ui(self) -> None:
        header = Gtk.HeaderBar(title=APP_NAME)
        header.set_show_close_button(True)
        header.set_subtitle(DEVELOPER)
        self.set_titlebar(header)

        shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(shell)
        self.sidebar = Gtk.ListBox()
        self.sidebar.set_selection_mode(Gtk.SelectionMode.NONE)
        self.sidebar.set_size_request(190, -1)
        self.sidebar.connect("row-activated", self._sidebar_activated)
        shell.pack_start(self.sidebar, False, False, 8)
        self.page_rows: dict[str, Gtk.ListBoxRow] = {}
        for page_id, arabic, english in (
            ("home", "الرئيسية", "Home"),
            ("games", "الألعاب", "Games"),
            ("windows", "تطبيقات Windows", "Windows Apps"),
            ("installed", "المثبتة", "Installed"),
            ("updates", "التحديثات", "Updates"),
            ("downloads", "النشاط", "Activity"),
            ("settings", "الإعدادات", "Settings"),
        ):
            row = Gtk.ListBoxRow()
            row.page_id = page_id
            row.add(Gtk.Label(label=_text(arabic, english), xalign=0))
            self.sidebar.add(row)
            self.page_rows[page_id] = row

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_border_width(14)
        shell.pack_start(content, True, True, 0)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search = Gtk.SearchEntry()
        self.search.set_direction(Gtk.TextDirection.LTR)
        self.search.set_placeholder_text(_text("ابحث عن تطبيق أو حزمة", "Search apps and packages"))
        self.search.connect("search-changed", self._search_changed)
        controls.pack_start(self.search, True, True, 0)
        self.category = Gtk.ComboBoxText()
        for key, arabic, english in SUPPORTED_CATEGORIES:
            self.category.append(key, _text(arabic, english))
        self.category.set_active_id("All")
        self.category.connect("changed", self._category_changed)
        controls.pack_start(self.category, False, False, 0)
        self.source = Gtk.ComboBoxText()
        for key, arabic, english in (
            ("All", "كل المصادر", "All sources"),
            ("APT", "حزم Debian (APT)", "Debian packages (APT)"),
            ("Flatpak", "Flatpak", "Flatpak"),
        ):
            self.source.append(key, _text(arabic, english))
        self.source.set_active_id("All")
        self.source.connect("changed", self._source_changed)
        controls.pack_start(self.source, False, False, 0)
        self.sort = Gtk.ComboBoxText()
        self.sort.append("name", _text("الاسم", "Name"))
        self.sort.append("size", _text("الحجم", "Size"))
        self.sort.set_active_id("name")
        self.sort.connect("changed", self._sort_changed)
        controls.pack_start(self.sort, False, False, 0)
        content.pack_start(controls, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.refresh_button = Gtk.Button(label=_text("تحديث الفهارس", "Refresh catalogs"))
        self.refresh_button.connect("clicked", self._refresh_indexes)
        actions.pack_start(self.refresh_button, False, False, 0)
        self.update_button = Gtk.Button(label=_text("فحص التحديثات", "Check updates"))
        self.update_button.connect("clicked", self._check_updates)
        actions.pack_start(self.update_button, False, False, 0)
        self.upgrade_button = Gtk.Button(label=_text("تثبيت التحديثات", "Install updates"))
        self.upgrade_button.connect("clicked", self._apply_updates)
        self.upgrade_button.set_no_show_all(True)
        actions.pack_start(self.upgrade_button, False, False, 0)
        self.flatpak_button = Gtk.Button(label=_text("تثبيت Flatpak", "Install Flatpak"))
        self.flatpak_button.connect("clicked", self._install_flatpak_manager)
        self.flatpak_button.set_no_show_all(True)
        if not shutil.which("flatpak"):
            self.flatpak_button.show()
        actions.pack_start(self.flatpak_button, False, False, 0)
        self.flathub_button = Gtk.Button(label=_text("إضافة Flathub…", "Add Flathub…"))
        self.flathub_button.connect("clicked", self._enable_flathub)
        self.flathub_button.set_no_show_all(True)
        self.flathub_button.show()
        actions.pack_start(self.flathub_button, False, False, 0)
        content.pack_start(actions, False, False, 0)

        self.banner = Gtk.Label(label="", xalign=0)
        self.banner.set_line_wrap(True)
        self.banner.get_style_context().add_class("muted")
        content.pack_start(self.banner, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE)
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        content.pack_start(self.stack, True, True, 0)
        self.apps_scroll = Gtk.ScrolledWindow()
        self.apps_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_min_children_per_line(1)
        self.flow.set_max_children_per_line(4)
        self.flow.set_row_spacing(10)
        self.flow.set_column_spacing(10)
        self.apps_scroll.add(self.flow)
        self.stack.add_named(self.apps_scroll, "apps")
        self.activity = Gtk.ListBox()
        activity_scroll = Gtk.ScrolledWindow()
        activity_scroll.add(self.activity)
        self.stack.add_named(activity_scroll, "activity")
        self.settings_page = self._build_settings_page()
        self.stack.add_named(self.settings_page, "settings")

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.spinner = Gtk.Spinner()
        footer.pack_start(self.spinner, False, False, 0)
        self.status = Gtk.Label(label=_text("جاهز", "Ready"), xalign=0)
        self.status.set_ellipsize(Pango.EllipsizeMode.END)
        footer.pack_start(self.status, True, True, 0)
        self.state_label = Gtk.Label(label="")
        self.state_label.get_style_context().add_class("muted")
        footer.pack_end(self.state_label, False, False, 0)
        content.pack_end(footer, False, False, 0)
        self._update_source_buttons()
        self.show_all()
        self.upgrade_button.hide()
        self.flatpak_button.set_visible(not shutil.which("flatpak"))
        self.flathub_button.set_visible(bool(shutil.which("flatpak")))

    def _build_settings_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)
        title = Gtk.Label(label=_text("إعدادات ISO-X Store", "ISO-X Store settings"), xalign=0)
        title.get_style_context().add_class("brand")
        box.pack_start(title, False, False, 0)
        self.sound_switch = Gtk.Switch(active=bool(self.settings["sounds_enabled"]))
        self.sound_switch.connect("notify::active", self._sound_enabled_changed)
        sound_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sound_row.pack_start(Gtk.Label(label=_text("الأصوات", "Store sounds"), xalign=0), True, True, 0)
        sound_row.pack_end(self.sound_switch, False, False, 0)
        box.pack_start(sound_row, False, False, 0)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
        self.volume.set_value(float(self.settings["sound_volume"]))
        self.volume.set_draw_value(True)
        self.volume.connect("value-changed", self._volume_changed)
        box.pack_start(Gtk.Label(label=_text("مستوى مؤثرات المتجر", "Store effect volume"), xalign=0), False, False, 0)
        box.pack_start(self.volume, False, False, 0)
        sounds = Gtk.Grid(column_spacing=8, row_spacing=8)
        for row, (sound_id, filename) in enumerate(SOUND_FILES.items()):
            label = _text(
                {
                    "notification": "إشعار",
                    "success": "نجاح",
                    "error": "خطأ",
                    "warning": "تحذير",
                    "download-complete": "اكتمال التنزيل",
                }[sound_id],
                sound_id.replace("-", " ").title(),
            )
            button = Gtk.Button(label=_text(f"تجربة: {label}", f"Test: {label}"))
            button.connect("clicked", self._test_sound, sound_id)
            sounds.attach(button, row % 2, row // 2, 1, 1)
        box.pack_start(sounds, False, False, 0)
        self.theme_switch = Gtk.Switch(active=self.settings["theme"] == "light")
        self.theme_switch.connect("notify::active", self._theme_changed)
        theme_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        theme_row.pack_start(Gtk.Label(label=_text("المظهر الفاتح", "Light theme"), xalign=0), True, True, 0)
        theme_row.pack_end(self.theme_switch, False, False, 0)
        box.pack_start(theme_row, False, False, 0)
        self.language = Gtk.ComboBoxText()
        for key, label in (
            ("auto", _text("لغة النظام", "System language")),
            ("ar", "العربية"),
            ("en", "English"),
        ):
            self.language.append(key, label)
        self.language.set_active_id(str(self.settings["language"]))
        self.language.connect("changed", self._language_changed)
        box.pack_start(Gtk.Label(label=_text("لغة المتجر (تُطبّق بعد إعادة الفتح)", "Store language (applies after restart)"), xalign=0), False, False, 0)
        box.pack_start(self.language, False, False, 0)
        reset = Gtk.Button(label=_text("استعادة الإعدادات الافتراضية", "Restore defaults"))
        reset.connect("clicked", self._reset_settings)
        box.pack_start(reset, False, False, 0)
        note = Gtk.Label(
            label=_text(
                "الأصوات مولّدة للمشروع، وتشغيلها اختياري. لا يُرفع مستوى صوت النظام.",
                "Original generated tones are optional. The system volume is never raised.",
            ),
            xalign=0,
        )
        note.set_line_wrap(True)
        note.get_style_context().add_class("muted")
        box.pack_start(note, False, False, 0)
        return box

    def _sidebar_activated(self, _sidebar: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        page_id = getattr(row, "page_id", "home")
        self.current_page = page_id
        self.search.set_text("")
        self.category.set_active_id("Installed" if page_id == "installed" else "All")
        self.search.set_sensitive(page_id not in ("settings", "downloads"))
        self.category.set_sensitive(page_id not in ("settings", "downloads"))
        self.source.set_sensitive(page_id not in ("settings", "downloads"))
        self.stack.set_visible_child_name("settings" if page_id == "settings" else "activity" if page_id == "downloads" else "apps")
        if page_id == "updates":
            self._check_updates()
        elif page_id in ("games", "windows"):
            self.search.set_text("")
            self.category.set_active_id("Games" if page_id == "games" else "Windows")
        elif page_id in ("home", "installed"):
            self._refresh_catalog()
        elif page_id == "downloads":
            self._show_activity()

    def _search_changed(self, _entry: Gtk.SearchEntry) -> None:
        if self.current_page in ("settings", "downloads"):
            return
        if hasattr(self, "_search_timeout"):
            GLib.source_remove(self._search_timeout)
        self._search_timeout = GLib.timeout_add(300, self._refresh_catalog)

    def _category_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.current_category = combo.get_active_id() or "All"
        if self.current_page not in ("settings", "downloads"):
            self._refresh_catalog()

    def _source_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.current_source = combo.get_active_id() or "All"
        if self.current_page not in ("settings", "downloads"):
            self._refresh_catalog()

    def _sort_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.sort_mode = combo.get_active_id() or "name"
        self._render_apps(self.apps)

    def _refresh_catalog(self) -> bool:
        if self.busy:
            return False
        self.generation += 1
        generation = self.generation
        query = self.search.get_text().strip()
        category = self.category.get_active_id() or "All"
        source = self.source.get_active_id() or "All"
        if self.current_page == "installed":
            category = "Installed"
        if self.current_page == "games":
            category = "Games"
        if self.current_page == "windows":
            category = "Windows"
        self.spinner.start()
        self.status.set_text(_text("جارٍ البحث في المصادر المحلية…", "Searching configured local sources…"))

        def work() -> None:
            try:
                apps = self.backend.search(query, category, source=source)
                error = ""
            except Exception as exc:
                apps, error = [], f"{type(exc).__name__}: {exc}"
            GLib.idle_add(self._catalog_loaded, generation, apps, error)

        threading.Thread(target=work, daemon=True).start()
        return False

    def _catalog_loaded(self, generation: int, apps: list[StoreApp], error: str) -> bool:
        if generation != self.generation:
            return False
        self.spinner.stop()
        self.apps = apps
        if error:
            self.status.set_text(_text("تعذر اكتشاف التطبيقات: ", "App discovery failed: ") + error)
        else:
            self.status.set_text(_text(f"عُثر على {len(apps)} نتيجة من المصادر المفعّلة.", f"{len(apps)} results from configured sources."))
        self._render_apps(apps)
        self._update_source_buttons()
        return False

    def _render_apps(self, apps: list[StoreApp]) -> None:
        for child in self.flow.get_children():
            self.flow.remove(child)
        selected_sort = getattr(self, "sort_mode", "name")
        if selected_sort == "size":
            apps = sorted(apps, key=lambda app: (app.size_bytes is None, app.size_bytes or 0, app.name.casefold()))
        else:
            apps = sorted(apps, key=lambda app: (not app.installed, app.name.casefold()))
        for app in apps:
            self.flow.add(self._app_card(app))
        self.flow.show_all()

    def _app_card(self, app: StoreApp) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        card.set_border_width(12)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = self._app_icon(app.icon, 48)
        header.pack_start(icon, False, False, 0)
        title = Gtk.Label(label=app.name, xalign=0, wrap=True)
        title.get_style_context().add_class("brand")
        title.set_max_width_chars(24)
        header.pack_start(title, True, True, 0)
        card.pack_start(header, False, False, 0)
        summary = Gtk.Label(label=app.summary or app.package_id, xalign=0, wrap=True)
        summary.set_lines(2)
        summary.get_style_context().add_class("muted")
        card.pack_start(summary, True, True, 0)
        details = Gtk.Label(label=f"{app.source_name} · {app.category} · {app.version or _text('الإصدار غير معروف', 'version unknown')}", xalign=0)
        details.get_style_context().add_class("muted")
        card.pack_start(details, False, False, 0)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_label = self._action_label(app)
        action = Gtk.Button(label=action_label)
        action.set_sensitive(not self.busy and action_label != _text("غير متاح", "Unavailable"))
        if app.installed and app.launchable:
            action.connect("clicked", self._launch, app)
        elif app.source in ("apt", "flatpak"):
            action.connect("clicked", self._manage_app, app)
        actions.pack_start(action, True, True, 0)
        info = Gtk.Button(label=_text("التفاصيل", "Details"))
        info.connect("clicked", self._show_details, app)
        actions.pack_start(info, False, False, 0)
        card.pack_end(actions, False, False, 0)
        frame.add(card)
        return frame

    def _action_label(self, app: StoreApp) -> str:
        if app.update_available:
            return _text("تحديث", "Update")
        if app.installed:
            return _text("فتح" if app.launchable else "مثبت", "Open" if app.launchable else "Installed")
        if app.source == "installed":
            return _text("مثبت", "Installed")
        if app.source == "apt" and not shutil.which("pkexec"):
            return _text("Polkit غير متاح", "Polkit unavailable")
        return _text("تثبيت", "Install")

    def _app_icon(self, icon_name: str, size: int) -> Gtk.Widget:
        if icon_name and Path(icon_name).is_file():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_name, size, size, True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except GLib.Error:
                pass
        theme = Gtk.IconTheme.get_default()
        if icon_name and theme and theme.has_icon(icon_name):
            return Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        return Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)

    def _show_details(self, _button: Gtk.Button, app: StoreApp) -> None:
        dialog = Gtk.Dialog(title=app.name, transient_for=self, modal=True)
        dialog.add_button(_text("إغلاق", "Close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(520, 440)
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_border_width(16)
        header = Gtk.Box(spacing=12)
        header.pack_start(self._app_icon(app.icon, 64), False, False, 0)
        title = Gtk.Label(label=app.name, xalign=0, wrap=True)
        title.get_style_context().add_class("brand")
        header.pack_start(title, True, True, 0)
        content.pack_start(header, False, False, 0)
        fields = (
            (_text("الوصف", "Description"), app.description or app.summary),
            (_text("المصدر", "Source"), app.source_name),
            (_text("المعرّف", "Package ID"), app.package_id),
            (_text("الإصدار", "Version"), app.version or _text("غير معروف", "Unknown")),
            (_text("المطور", "Developer"), app.developer or _text("غير متوفر من المصدر", "Not provided by source")),
            (_text("الترخيص", "License"), app.license or _text("غير متوفر من المصدر", "Not provided by source")),
            (_text("المعمارية", "Architecture"), app.architecture or _text("غير معروفة", "Unknown")),
            (_text("حجم التنزيل", "Download size"), self._format_size(app.size_bytes)),
        )
        for label_text, value in fields:
            label = Gtk.Label(label=f"{label_text}: {value}", xalign=0, wrap=True)
            label.set_selectable(True)
            content.pack_start(label, False, False, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    @staticmethod
    def _format_size(size: int | None) -> str:
        if size is None:
            return _text("غير متوفر من المصدر", "Not provided by source")
        amount = float(size)
        for unit in ("B", "KiB", "MiB", "GiB"):
            if amount < 1024 or unit == "GiB":
                return f"{amount:.1f} {unit}"
            amount /= 1024
        return _text("غير معروف", "Unknown")

    def _confirm(self, title: str, body: str) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=title,
        )
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        dialog.format_secondary_text(body)
        self.play_sound("warning")
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _manage_app(self, _button: Gtk.Button, app: StoreApp) -> None:
        if app.source == "apt":
            operation = "update" if app.update_available else "remove" if app.installed else "install"
            if operation == "update":
                prompt = _text(f"تحديث {app.name} إلى {app.version} عبر APT؟", f"Update {app.name} to {app.version} through APT?")
            elif operation == "remove":
                prompt = _text(f"إزالة حزمة {app.package_id} فقط؟ لن تُحذف إعدادات المستخدم.", f"Remove package {app.package_id} only? User settings are not purged.")
            else:
                prompt = _text(f"تثبيت {app.name} من مستودعات APT المفعّلة؟\nالإصدار: {app.version}\nالحجم: {self._format_size(app.size_bytes)}", f"Install {app.name} from enabled APT repositories?\nVersion: {app.version}\nDownload size: {self._format_size(app.size_bytes)}")
            if not self._confirm(_text("تأكيد العملية", "Confirm package operation"), prompt):
                return
            if operation == "remove":
                work = lambda: self.backend.remove_apt(app.package_id, app.version)
            else:
                work = lambda: self.backend.install_apt(app.package_id, app.version)
        elif app.source == "flatpak":
            operation = "update" if app.update_available else "remove" if app.installed else "install"
            prompt = _text(
                f"{'تحديث' if operation == 'update' else 'إزالة' if app.installed else 'تثبيت'} {app.name} من Flatpak؟ المصدر: {app.source_name}",
                f"{'Update' if operation == 'update' else 'Remove' if app.installed else 'Install'} {app.name} with Flatpak? Source: {app.source_name}",
            )
            if not self._confirm(_text("تأكيد Flatpak", "Confirm Flatpak operation"), prompt):
                return
            if operation == "update":
                work = lambda: self.backend.update_flatpak(app.package_id)
            elif app.installed:
                work = lambda: self.backend.remove_flatpak(app.package_id)
            else:
                work = lambda: self.backend.install_flatpak(app.remote, app.package_id, app.branch)
        else:
            return

        def operation_with_verification() -> OperationResult:
            result = work()
            if not result.success:
                return result
            installed = self.backend.is_installed(app.source, app.package_id)
            expected = operation != "remove"
            if installed != expected:
                return OperationResult(False, _text("انتهى مدير الحزم دون تأكيد الحالة المطلوبة؛ أُعيد فحص الحالة.", "The package manager exited without confirming the requested state; the current state was rechecked."))
            return result

        self._begin_operation(app.name, operation_with_verification, "download-complete" if operation != "remove" else "success")

    def _launch(self, _button: Gtk.Button, app: StoreApp) -> None:
        result = self.backend.launch(app)
        self.status.set_text(result.message)
        if not result.success:
            self.play_sound("error")

    def _begin_operation(self, title: str, operation, success_sound: str) -> None:
        if self.busy:
            return
        self.busy = True
        self.package_operation_active = True
        self.generation += 1
        self._set_controls_sensitive(False)
        self.spinner.start()
        self.status.set_text(_text("جارٍ تنفيذ: ", "Working: ") + title)

        def work() -> None:
            try:
                result = operation()
                if not isinstance(result, OperationResult):
                    result = OperationResult(False, "Operation returned an invalid result.")
            except Exception as exc:
                result = OperationResult(False, f"{type(exc).__name__}: {exc}")
            GLib.idle_add(self._operation_finished, title, result, success_sound)

        threading.Thread(target=work, daemon=True).start()

    def _operation_finished(self, title: str, result: OperationResult, success_sound: str) -> bool:
        self.busy = False
        self.package_operation_active = False
        self.spinner.stop()
        self._set_controls_sensitive(True)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.operation_history.insert(0, (timestamp, title, result.message))
        if result.success:
            self.status.set_text(_text("اكتملت العملية: ", "Completed: ") + title)
            self.play_sound(success_sound)
        else:
            self.status.set_text(_text("فشلت العملية: ", "Operation failed: ") + result.message[-350:])
            self.play_sound("error")
        self._show_activity()
        self._refresh_catalog()
        self.flatpak_button.set_visible(not shutil.which("flatpak"))
        self.flathub_button.set_visible(bool(shutil.which("flatpak")))
        return False

    def _set_controls_sensitive(self, sensitive: bool) -> None:
        for widget in (self.refresh_button, self.update_button, self.upgrade_button, self.flatpak_button, self.flathub_button):
            widget.set_sensitive(sensitive)
        self.search.set_sensitive(sensitive and self.current_page not in ("settings", "downloads"))
        self.category.set_sensitive(sensitive and self.current_page not in ("settings", "downloads"))
        self.source.set_sensitive(sensitive and self.current_page not in ("settings", "downloads"))
        self.flow.set_sensitive(sensitive)

    def _refresh_indexes(self, _button: Gtk.Button) -> None:
        if not self._confirm(
            _text("تحديث فهارس APT؟", "Refresh APT catalogs?"),
            _text("سيتم الاتصال بمستودعات Debian المفعّلة. لا تُضاف مصادر جديدة.", "This contacts the enabled Debian repositories. No new source will be added."),
        ):
            return

        def refresh() -> OperationResult:
            result = self.backend.update_indexes()
            if result.success:
                self.backend.invalidate_catalog_cache()
            return result

        self._begin_operation(_text("فهارس APT", "APT catalogs"), refresh, "success")

    def _check_updates(self, _button: Gtk.Button | None = None) -> None:
        if self.busy:
            return
        self.busy = True
        self._set_controls_sensitive(False)
        self.spinner.start()
        self.status.set_text(_text("جارٍ فحص التحديثات المتاحة…", "Checking available updates…"))

        def work() -> None:
            try:
                updates = self.backend.updates()
                installed_apps = self.backend.installed_apps()
                apps = [app for app in installed_apps if app.update_available]
                flatpak_updates = {
                    update.removeprefix("flatpak:")
                    for update in updates
                    if update.startswith("flatpak:")
                }
                known_flatpak_apps = {
                    app.package_id for app in apps if app.source == "flatpak"
                }
                for app in installed_apps:
                    if (
                        app.source == "flatpak"
                        and app.package_id in flatpak_updates
                        and app.package_id not in known_flatpak_apps
                    ):
                        apps.append(replace(app, update_available=True))
                        known_flatpak_apps.add(app.package_id)
                error = ""
            except Exception as exc:
                updates, apps, error = [], [], f"{type(exc).__name__}: {exc}"
            GLib.idle_add(self._updates_loaded, updates, apps, error)

        threading.Thread(target=work, daemon=True).start()

    def _updates_loaded(self, updates: list[str], apps: list[StoreApp], error: str) -> bool:
        self.busy = False
        self.spinner.stop()
        self._set_controls_sensitive(True)
        self.pending_updates = updates
        self._show_activity()
        apt_updates = any(not update.startswith("flatpak:") for update in updates)
        flatpak_updates = any(update.startswith("flatpak:") for update in updates)
        self.upgrade_button.set_visible(
            (apt_updates and bool(shutil.which("pkexec")))
            or (flatpak_updates and bool(shutil.which("flatpak")))
        )
        self.apps = apps
        self._render_apps(apps)
        if error:
            self.status.set_text(_text("تعذر فحص التحديثات: ", "Update check failed: ") + error)
            self.play_sound("error")
        elif not updates:
            self.status.set_text(_text("لا توجد تحديثات متاحة وفق المصادر المحلية.", "No updates are available from the local package sources."))
        else:
            self.status.set_text(_text(f"تحديثات متاحة: {len(updates)}", f"Updates available: {len(updates)}"))
            self.play_sound("notification")
        self.stack.set_visible_child_name("apps")
        return False

    def _apply_updates(self, _button: Gtk.Button) -> None:
        if not self._confirm(
            _text("تثبيت تحديثات النظام؟", "Install system updates?"),
            _text(
                "سيُحدّث APT الحزم المثبتة دون إزالة حزم. ستُحدّث أيضاً تطبيقات Flatpak المثبتة للمستخدم، إذا وُجدت.",
                "APT will upgrade installed packages without removing packages. User Flatpak applications will also be updated if present.",
            ),
        ):
            return

        def upgrade() -> OperationResult:
            details = []
            if any(not update.startswith("flatpak:") for update in self.pending_updates):
                apt_result = self.backend.upgrade_apt()
                if not apt_result.success:
                    return apt_result
                details.append(f"APT: {apt_result.message[-1200:]}")
            if any(update.startswith("flatpak:") for update in self.pending_updates):
                flatpak_result = self.backend.upgrade_flatpak()
                if not flatpak_result.success:
                    return OperationResult(
                        False,
                        f"{'; '.join(details)}; Flatpak update failed: {flatpak_result.message}",
                        flatpak_result.returncode,
                    )
                details.append(f"Flatpak: {flatpak_result.message[-1200:]}")
            if not details:
                return OperationResult(False, "No update candidates remain; check for updates again.")
            return OperationResult(True, "; ".join(details))

        self._begin_operation(_text("تحديثات النظام", "System updates"), upgrade, "success")

    def _install_flatpak_manager(self, _button: Gtk.Button) -> None:
        candidate = self.backend.package_candidate("flatpak")
        if not candidate:
            self.status.set_text(_text("حزمة Flatpak غير متاحة في مستودعات APT المفعّلة.", "Flatpak is not available in enabled APT repositories."))
            self.play_sound("error")
            return
        if not self._confirm(
            _text("تثبيت Flatpak؟", "Install Flatpak?"),
            _text(f"سيتم تثبيت Flatpak من APT، الإصدار المرشح {candidate}.", f"Flatpak will be installed from APT, candidate version {candidate}."),
        ):
            return

        def install() -> OperationResult:
            result = self.backend.install_apt("flatpak", candidate)
            if result.success and not self.backend.is_installed("apt", "flatpak"):
                return OperationResult(False, "APT completed but Flatpak is not installed.")
            return result

        self._begin_operation("Flatpak", install, "download-complete")

    def _enable_flathub(self, _button: Gtk.Button) -> None:
        if not shutil.which("flatpak"):
            self.status.set_text(_text("ثبّت Flatpak أولاً.", "Install Flatpak first."))
            return
        if not self._confirm(
            _text("إضافة Flathub لحسابك؟", "Add Flathub for your user?"),
            _text(
                "سيُضاف المصدر الرسمي https://dl.flathub.org/repo/flathub.flatpakrepo إلى إعداد Flatpak الخاص بالمستخدم فقط. ستظهر التطبيقات بعد موافقتك على هذا التغيير.",
                "The official https://dl.flathub.org/repo/flathub.flatpakrepo remote will be added to this user's Flatpak configuration only.",
            ),
        ):
            return
        self._begin_operation("Flathub", self.backend.enable_flathub, "success")

    def _show_activity(self) -> None:
        for child in self.activity.get_children():
            self.activity.remove(child)
        for timestamp, title, message in self.operation_history:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_border_width(10)
            box.pack_start(Gtk.Label(label=f"{timestamp} · {title}", xalign=0), False, False, 0)
            detail = Gtk.Label(label=message, xalign=0, wrap=True)
            detail.set_selectable(True)
            detail.get_style_context().add_class("muted")
            box.pack_start(detail, False, False, 0)
            row.add(box)
            self.activity.add(row)
        self.activity.show_all()

    def _update_source_buttons(self) -> None:
        self.state_label.set_text(
            _text(
                "Flathub غير مفعّل" if shutil.which("flatpak") else "Flatpak غير مثبت",
                "Flathub is not enabled" if shutil.which("flatpak") else "Flatpak is not installed",
            )
        )
        if not shutil.which("flatpak"):
            self.banner.set_text(_text(
                "يُعرض محتوى Debian من الفهارس المحلية. Flatpak غير مثبت؛ لا تُعرض تطبيقات خارج المصادر المفعّلة.",
                "Debian results use local catalog metadata. Flatpak is not installed; apps from inactive sources are not listed.",
            ))
        else:
            self.banner.set_text(_text(
                "النتائج من المصادر المفعّلة فقط. لا تُعرض تقييمات أو أعداد تنزيل غير موثقة.",
                "Results come only from enabled sources. No unverified ratings or download counts are shown.",
            ))

    def _sound_enabled_changed(self, switch: Gtk.Switch, _property) -> None:
        self.settings["sounds_enabled"] = switch.get_active()
        self._persist_settings()

    def _volume_changed(self, scale: Gtk.Scale) -> None:
        self.settings["sound_volume"] = scale.get_value()
        self._persist_settings()

    def _theme_changed(self, switch: Gtk.Switch, _property) -> None:
        self.settings["theme"] = "light" if switch.get_active() else "dark"
        self.get_style_context().remove_class("light")
        if switch.get_active():
            self.get_style_context().add_class("light")
        self._persist_settings()

    def _language_changed(self, combo: Gtk.ComboBoxText) -> None:
        self.settings["language"] = combo.get_active_id() or "auto"
        self._persist_settings()
        self.status.set_text(_text(
            "حُفظت اللغة؛ أعد فتح المتجر لتطبيقها بالكامل.",
            "Language saved; reopen the store to apply it fully.",
        ))

    def _persist_settings(self) -> None:
        try:
            _save_settings(self.settings)
        except OSError as exc:
            self.status.set_text(_text("تعذر حفظ التفضيلات: ", "Could not save preferences: ") + str(exc))

    def _reset_settings(self, _button: Gtk.Button) -> None:
        self.settings = dict(DEFAULT_SETTINGS)
        self.sound_switch.set_active(True)
        self.volume.set_value(float(DEFAULT_SETTINGS["sound_volume"]))
        self.theme_switch.set_active(False)
        self.language.set_active_id("auto")
        self.status.set_text(_text("تمت استعادة الإعدادات الافتراضية.", "Default settings restored."))
        self._persist_settings()

    def _test_sound(self, _button: Gtk.Button, sound_id: str) -> None:
        if not self.settings["sounds_enabled"]:
            self.status.set_text(_text("الأصوات معطّلة.", "Sounds are muted."))
            return
        if not self.play_sound(sound_id):
            self.status.set_text(_text(
                "تعذر تشغيل الصوت؛ تحقق من pulseaudio-utils وخرج الصوت. يستمر المتجر بالعمل.",
                "Could not play sound; check pulseaudio-utils and the audio output. The store remains usable.",
            ))

    def play_sound(self, sound_id: str) -> bool:
        if not self.settings["sounds_enabled"] or sound_id not in SOUND_FILES:
            return False
        path = SOUND_DIR / SOUND_FILES[sound_id]
        if not path.is_file() or not shutil.which("paplay"):
            return False
        volume = round(float(self.settings["sound_volume"]) * 65536)
        try:
            process = subprocess.Popen(
                ["paplay", f"--volume={volume}", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except OSError:
            return False

        def monitor() -> None:
            _stdout, stderr = process.communicate()
            if process.returncode:
                GLib.idle_add(self._sound_failed, stderr.strip() or f"paplay exited {process.returncode}")

        threading.Thread(target=monitor, daemon=True).start()
        return True

    def _sound_failed(self, diagnostic: str) -> bool:
        self.status.set_text(
            _text("تعذر تشغيل مؤثر صوتي: ", "Store sound could not be played: ") + diagnostic[-180:]
        )
        return False

    def close(self) -> None:
        Gtk.main_quit()


if __name__ == "__main__":
    window = StoreWindow()
    window.connect("destroy", window._on_destroy)
    window.show_all()
    Gtk.main()
