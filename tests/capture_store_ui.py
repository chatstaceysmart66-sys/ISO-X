#!/usr/bin/env python3
"""Capture Arabic and English GTK store previews using explicitly synthetic catalog data."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from isox_store_backend import AppPage, StoreApp


PREVIEW_APPS = [
    StoreApp("calc", "apt", "Debian APT", "Calculator", "Perform everyday calculations", "Apps", "galculator", "13.2", True, icon="accessories-calculator"),
    StoreApp("files", "apt", "Debian APT", "Files", "Browse files and folders", "Apps", "thunar", "4.20", True, icon="system-file-manager"),
    StoreApp("browser", "apt", "Debian APT", "Firefox", "Browse the web privately", "Apps", "firefox-esr", "128", True, icon="firefox-esr"),
    StoreApp("images", "apt", "Debian APT", "Image Viewer", "View your image collection", "Apps", "ristretto", "0.13", True, icon="image-x-generic"),
    StoreApp("media", "apt", "Debian APT", "Media Player", "Play audio and video", "Apps", "parole", "4.18", True, icon="multimedia-player"),
    StoreApp("terminal", "apt", "Debian APT", "Terminal", "Run command-line tools", "Apps", "xfce4-terminal", "1.1", True, icon="utilities-terminal"),
]


class PreviewBackend:
    def search_page(self, query="", category="All", *, source="All", page=0, page_size=24):
        terms = query.casefold().split()
        apps = [
            app for app in PREVIEW_APPS
            if all(term in f"{app.name} {app.summary} {app.package_id}".casefold() for term in terms)
        ]
        start = page * page_size
        return AppPage(apps[start:start + page_size], page, page_size, len(apps))

    def all_apt_packages(self, query="", *, page=0, page_size=30):
        return AppPage([], page, page_size, 0)


def capture(window: StoreWindow, destination: Path) -> None:
    window.queue_draw()
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    native = window.get_window()
    if native is None:
        raise RuntimeError("The GTK store window has no native drawing surface.")
    width, height = window.get_size()
    pixbuf = Gdk.pixbuf_get_from_window(native, 0, 0, width, height)
    if pixbuf is None:
        raise RuntimeError("GTK could not capture the store window.")
    pixbuf.savev(str(destination), "png", [], [])


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} OUTPUT_DIR", file=sys.stderr)
        return 2
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="isox-store-preview-home-") as home:
        os.environ["HOME"] = home
        from isox_appcenter import StoreWindow

        for language in ("ar", "en"):
            os.environ["LANGUAGE"] = language
            window = StoreWindow(backend=PreviewBackend())
            attempts = 0

            def wait_for_catalog() -> bool:
                nonlocal attempts
                attempts += 1
                if (window.total_results == 0 and attempts < 50) or attempts < 5:
                    return GLib.SOURCE_CONTINUE
                try:
                    if window.total_results != len(PREVIEW_APPS):
                        raise RuntimeError(
                            f"Expected {len(PREVIEW_APPS)} preview cards, got {window.total_results}."
                        )
                    capture(window, output / f"store-{language}.png")
                except Exception as error:
                    failures.append(f"{language}: {type(error).__name__}: {error}")
                window.destroy()
                Gtk.main_quit()
                return GLib.SOURCE_REMOVE

            GLib.timeout_add(100, wait_for_catalog)
            Gtk.main()
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Captured Arabic and English GTK previews in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
