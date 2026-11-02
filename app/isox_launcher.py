#!/usr/bin/env python3
"""Small GTK launcher backed by the installed desktop-entry catalog."""
from __future__ import annotations

import os
from pathlib import Path

import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango


def _application_roots() -> tuple[str, ...]:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path(GLib.get_home_dir()) / ".local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    roots = [
        data_home / "applications",
        data_home / "flatpak/exports/share/applications",
    ]
    for data_dir in data_dirs.split(os.pathsep):
        if data_dir:
            root = Path(data_dir)
            roots.extend((
                root / "applications",
                root / "flatpak/exports/share/applications",
            ))
    return tuple(dict.fromkeys(str(root) for root in roots))


APPLICATION_ROOTS = _application_roots()
PREFERRED_IDS = (
    "firefox-esr.desktop",
    "thunar.desktop",
    "isox-store.desktop",
    "galculator.desktop",
    "xfce4-terminal.desktop",
    "xfce4-settings-manager.desktop",
    "vlc.desktop",
    "xfce4-screenshooter.desktop",
)
PAGE_SIZE = 8
INTERNAL_DESKTOP_IDS = frozenset({"iso-x.desktop", "isox-launcher.desktop"})


def installed_applications() -> list[Gio.DesktopAppInfo]:
    apps: dict[str, Gio.DesktopAppInfo] = {}
    seen_entries: set[str] = set()
    for root in APPLICATION_ROOTS:
        root_path = Path(root)
        try:
            entries = sorted(
                root_path.rglob("*.desktop"),
                key=lambda path: path.relative_to(root_path).as_posix().casefold(),
            )
        except OSError:
            continue
        for path in entries:
            relative = path.relative_to(root_path)
            entry = "-".join(part.replace("-", "--") for part in relative.parts)
            if (
                not entry.endswith(".desktop")
                or entry in INTERNAL_DESKTOP_IDS
                or entry in seen_entries
                or not path.is_file()
            ):
                continue
            app = Gio.DesktopAppInfo.new_from_filename(str(path))
            if app is None:
                continue
            seen_entries.add(entry)
            if app.get_is_hidden() or not app.should_show() or not app.get_executable():
                continue
            apps[entry] = app
    return sorted(
        apps.values(),
        key=lambda app: (
            (app.get_categories() or "Other").split(";", 1)[0].casefold(),
            app.get_display_name().casefold(),
            app.get_id() or "",
        ),
    )


class LauncherWindow(Gtk.Window):
    def __init__(self, application: Gtk.Application):
        super().__init__(application=application, type=Gtk.WindowType.TOPLEVEL)
        self.set_title("ISO-X Applications")
        self.set_direction(
            Gtk.TextDirection.RTL if self._is_arabic() else Gtk.TextDirection.LTR
        )
        self.set_default_size(420, 560)
        self.set_size_request(340, 420)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.get_style_context().add_class("isox-launcher")
        self._install_css()
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.TOUCH_MASK)
        self.connect("key-press-event", self._key_pressed)
        self.connect("focus-out-event", self._focus_out)
        self.connect("button-press-event", self._outside_button_press)
        self.connect("touch-event", self._outside_touch)
        self.connect("map-event", self._window_mapped)

        self.apps = installed_applications()
        self.preferred = self._preferred_apps()
        self.filtered_apps = self.apps
        self.visible_count = PAGE_SIZE
        self.showing_all = False
        self.status = Gtk.Label(xalign=0, wrap=True)
        self.status.set_no_show_all(True)
        self._build_ui()

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(b"""
            window.isox-launcher { background: #0b1020; color: #edf4ff; }
            .isox-launcher .title { color: #55c9ff; font-weight: 700; font-size: 15pt; }
            .isox-launcher button.launcher-app {
                background: #132239; color: #edf4ff; border: 1px solid #294563;
                border-radius: 10px; padding: 8px; min-height: 54px;
            }
            .isox-launcher button.launcher-app:hover {
                background: #1b3858; border-color: #35c4ff;
            }
            .isox-launcher button.suggested-action {
                background: #0879b7; color: white; border-radius: 9px;
            }
        """)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _preferred_apps(self) -> list[Gio.DesktopAppInfo]:
        by_id = {
            (app.get_id() or "").casefold(): app
            for app in self.apps
        }
        selected: list[Gio.DesktopAppInfo] = []
        seen: set[str] = set()
        for app_id in PREFERRED_IDS:
            app = by_id.get(app_id.casefold())
            if app is not None:
                selected.append(app)
                seen.add(app.get_id() or app_id)
        for app in self.apps:
            app_id = app.get_id() or ""
            if len(selected) >= 8:
                break
            if app_id not in seen:
                selected.append(app)
                seen.add(app_id)
        return selected[:8]

    def _build_ui(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_border_width(14)
        outer.get_style_context().add_class("launcher")
        self.add(outer)

        self.primary_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        title = Gtk.Label(label="التطبيقات" if self._is_arabic() else "Applications")
        title.get_style_context().add_class("title")
        self.primary_page.pack_start(title, False, False, 4)
        self.primary_grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        self.primary_grid.set_column_homogeneous(True)
        self._render_primary()
        self.primary_page.pack_start(self.primary_grid, False, False, 0)
        self.more_button = Gtk.Button(label="المزيد" if self._is_arabic() else "More")
        self.more_button.get_style_context().add_class("suggested-action")
        self.more_button.connect("clicked", self._show_all)
        self.primary_page.pack_end(self.more_button, False, False, 0)
        outer.pack_start(self.primary_page, True, True, 0)

        self.all_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.back_button = Gtk.Button(label="رجوع" if self._is_arabic() else "Back")
        self.back_button.connect("clicked", self._show_primary)
        top.pack_start(self.back_button, False, False, 0)
        all_title = Gtk.Label(label="كل التطبيقات" if self._is_arabic() else "All applications")
        all_title.get_style_context().add_class("title")
        top.pack_start(all_title, True, True, 0)
        self.all_page.pack_start(top, False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text(
            "ابحث في التطبيقات" if self._is_arabic() else "Search applications"
        )
        self.search.connect("search-changed", self._search_changed)
        self.all_page.pack_start(self.search, False, False, 0)
        self.all_list = Gtk.ListBox()
        self.all_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.all_list)
        self.all_page.pack_start(scroll, True, True, 0)
        self.all_more = Gtk.Button(label="تحميل المزيد" if self._is_arabic() else "Load more")
        self.all_more.connect("clicked", self._load_more)
        self.all_page.pack_end(self.all_more, False, False, 0)
        outer.pack_start(self.all_page, True, True, 0)
        outer.pack_end(self.status, False, False, 0)
        self.all_page.hide()
        self._render_all()

    def _render_primary(self) -> None:
        for child in self.primary_grid.get_children():
            self.primary_grid.remove(child)
        for index, app in enumerate(self.preferred):
            button = self._app_button(app, compact=True)
            self.primary_grid.attach(button, index % 2, index // 2, 1, 1)
        if not self.preferred:
            empty = Gtk.Label(
                label="لا توجد تطبيقات قابلة للتشغيل." if self._is_arabic()
                else "No launchable applications are installed."
            )
            empty.set_line_wrap(True)
            self.primary_grid.attach(empty, 0, 0, 2, 1)
        self.primary_grid.show_all()

    def _refresh_applications(self) -> None:
        self.apps = installed_applications()
        self.preferred = self._preferred_apps()
        self.filtered_apps = self.apps
        self.visible_count = PAGE_SIZE
        self._render_primary()
        self._render_all()

    @staticmethod
    def _is_arabic() -> bool:
        return os.environ.get("LANGUAGE", os.environ.get("LANG", "")).lower().startswith("ar")

    def _app_button(self, app: Gio.DesktopAppInfo, *, compact: bool) -> Gtk.Button:
        button = Gtk.Button()
        button.get_style_context().add_class("launcher-app")
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL if compact else Gtk.Orientation.VERTICAL,
            spacing=9,
        )
        app_icon = app.get_icon()
        icon = (
            Gtk.Image.new_from_gicon(app_icon, Gtk.IconSize.DIALOG)
            if app_icon is not None
            else Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
        )
        icon.set_pixel_size(40 if compact else 36)
        box.pack_start(icon, False, False, 0)
        label = Gtk.Label(label=app.get_display_name(), xalign=0 if compact else 0.5)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(22)
        box.pack_start(label, True, True, 0)
        button.add(box)
        description = app.get_description() or app.get_display_name()
        button.set_tooltip_text(description)
        button.connect("clicked", self._launch_app, app)
        return button

    def _show_all(self, _button: Gtk.Button) -> None:
        self.showing_all = True
        self.primary_page.hide()
        self.all_page.show_all()
        self.search.grab_focus()

    def _show_primary(self, _button: Gtk.Button) -> None:
        self.showing_all = False
        self.all_page.hide()
        self.primary_page.show_all()

    def _search_changed(self, entry: Gtk.SearchEntry) -> None:
        terms = entry.get_text().casefold().split()
        self.filtered_apps = [
            app for app in self.apps
            if all(
                term in " ".join((
                    app.get_display_name(),
                    app.get_description() or "",
                    app.get_executable() or "",
                    app.get_categories() or "",
                    app.get_id() or "",
                )).casefold()
                for term in terms
            )
        ]
        self.visible_count = PAGE_SIZE
        self._render_all()

    def _render_all(self) -> None:
        for row in self.all_list.get_children():
            self.all_list.remove(row)
        self._append_apps(0, self.visible_count)
        self._update_load_more()

    def _append_apps(self, start: int, end: int) -> None:
        for app in self.filtered_apps[start:end]:
            row = Gtk.ListBoxRow()
            row.add(self._app_button(app, compact=True))
            self.all_list.add(row)
            row.show_all()

    def _update_load_more(self) -> None:
        self.all_more.set_visible(self.visible_count < len(self.filtered_apps))

    def _load_more(self, _button: Gtk.Button) -> None:
        previous_count = self.visible_count
        self.visible_count += PAGE_SIZE
        self._append_apps(previous_count, self.visible_count)
        self._update_load_more()

    def _launch_app(self, _button: Gtk.Button, app: Gio.DesktopAppInfo) -> None:
        try:
            if not app.launch([], None):
                self.status.set_text(
                    "تعذر تشغيل التطبيق." if self._is_arabic()
                    else "The application did not accept the launch request."
                )
                self.status.show()
                return
        except GLib.Error as error:
            self.status.set_text(str(error))
            self.status.show()
            return
        self._hide()

    def _key_pressed(self, _window: Gtk.Window, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self._hide()
            return True
        return False

    def _focus_out(self, *_args) -> bool:
        GLib.idle_add(self._hide)
        return False

    def _window_mapped(self, *_args) -> bool:
        self._grab_pointer()
        return False

    def _outside_button_press(self, _window: Gtk.Window, event: Gdk.EventButton) -> bool:
        return self._close_if_outside(event.x_root, event.y_root)

    def _outside_touch(self, _window: Gtk.Window, event: Gdk.Event) -> bool:
        if event.type != Gdk.EventType.TOUCH_BEGIN:
            return False
        x_root, y_root = event.get_root_coords()
        return self._close_if_outside(x_root, y_root)

    def _close_if_outside(self, x_root: float, y_root: float) -> bool:
        x, y = self.get_position()
        width, height = self.get_size()
        if x <= x_root < x + width and y <= y_root < y + height:
            return False
        self._hide()
        return True

    def _grab_pointer(self) -> None:
        display = Gdk.Display.get_default()
        seat = display.get_default_seat() if display is not None else None
        window = self.get_window()
        status = Gdk.GrabStatus.FAILED
        if seat is not None and window is not None:
            status = seat.grab(
                window,
                Gdk.SeatCapabilities.POINTER | Gdk.SeatCapabilities.TOUCH,
                True,
                None,
                None,
                None,
            )
            if status != Gdk.GrabStatus.SUCCESS:
                status = seat.grab(
                    window,
                    Gdk.SeatCapabilities.POINTER,
                    True,
                    None,
                    None,
                    None,
                )
        if status != Gdk.GrabStatus.SUCCESS:
            self.status.set_text(
                "تعذر تفعيل إغلاق النقر الخارجي." if self._is_arabic()
                else f"Could not grab pointer input ({status.value_nick})."
            )
            self.status.show()

    @staticmethod
    def _ungrab_pointer() -> None:
        display = Gdk.Display.get_default()
        seat = display.get_default_seat() if display is not None else None
        if seat is not None:
            seat.ungrab()

    def _hide(self) -> bool:
        self._ungrab_pointer()
        self.hide()
        return GLib.SOURCE_REMOVE

    def toggle(self) -> None:
        if self.get_visible():
            self._hide()
        else:
            self._refresh_applications()
            self.show_all()
            if self.showing_all:
                self.primary_page.hide()
                self.all_page.show_all()
                self.search.grab_focus()
            else:
                self.all_page.hide()
                self.primary_page.show_all()
                self.grab_focus()
            screen = Gdk.Screen.get_default()
            if screen is not None:
                width, height = self.get_size()
                x = (
                    screen.get_width() - width - 24
                    if self._is_arabic()
                    else 24
                )
                y = screen.get_height() - height - 58
                self.move(max(0, x), max(0, y))
                self.present()


class LauncherApplication(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="org.iso-x.AppLauncher",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.window: LauncherWindow | None = None

    def do_activate(self) -> None:
        if self.window is None:
            self.window = LauncherWindow(self)
        self.window.toggle()


if __name__ == "__main__":
    raise SystemExit(LauncherApplication().run(None))
