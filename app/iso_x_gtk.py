#!/usr/bin/env python3
"""ISO-X GTK3 desktop shell, 0.4.0. All telemetry is local-only and opt-in."""
from __future__ import annotations
import os, sys, time, json, shutil, subprocess, platform, sqlite3, hashlib, threading, tempfile
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango
try:
    gi.require_version("Vte", "2.91")
    from gi.repository import Vte
except Exception:
    Vte = None
try:
    gi.require_version("GtkSource", "3.0")
    from gi.repository import GtkSource
except Exception:
    GtkSource = None

APP_NAME = "ISO-X"
DEVELOPER = "عبدالله لازم"
BG, PANEL, PANEL2 = "#0A0A0F", "#12121C", "#191927"
CYAN, PURPLE, ORANGE, WHITE = "#00E5FF", "#7C4DFF", "#FF6D00", "#F5F5F5"
MUTED, GREEN = "#9AA5B8", "#62E6B5"
HOME = Path.home()
DATA_DIR = HOME / ".local/share/iso-x"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "iso-x.db"

CSS = f"""
window, .background {{ background: {BG}; color: {WHITE}; }}
headerbar {{ background: {PANEL}; color: {WHITE}; border: 0; min-height: 48px; }}
button {{ background: {PANEL2}; color: {WHITE}; border: 1px solid #2c2c41; border-radius: 8px; padding: 7px 12px; }}
button:hover {{ background: #222237; border-color: {CYAN}; color: {CYAN}; }}
entry, textview, treeview, list, notebook {{ background: {PANEL}; color: {WHITE}; }}
entry {{ border: 1px solid #31314a; border-radius: 7px; padding: 7px; }}
label {{ color: {WHITE}; }}
.iso-title {{ color: {CYAN}; font-weight: bold; font-size: 20px; }}
.iso-muted {{ color: {MUTED}; }}
.iso-card {{ background: {PANEL}; border: 1px solid #29293a; border-radius: 12px; padding: 14px; }}
.iso-highlight {{ color: {CYAN}; }}
separator {{ background: #29293a; }}
"""

class Store:
    def __init__(self):
        self.db = sqlite3.connect(DB_PATH)
        self.db.execute("PRAGMA foreign_keys=ON")
        base = Path(__file__).resolve().parent.parent
        schema_candidates = [base / "db/schema.sql", Path("/usr/share/iso-x/schema.sql"), Path("/usr/share/iso-x/db/schema.sql")]
        schema = next((p for p in schema_candidates if p.exists()), None)
        # Migrate an existing 0.1.0 database before running CREATE TABLE IF NOT EXISTS
        # statements; otherwise the old kernel_watermark table would miss the new columns.
        existing_tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "kernel_watermark" in existing_tables:
            existing_columns = {r[1] for r in self.db.execute("PRAGMA table_info(kernel_watermark)")}
            self.db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY)")
            if "module_version" not in existing_columns:
                migration_candidates = [base / "db/migrations/002_isox_020.sql", Path("/usr/share/iso-x/db/migrations/002_isox_020.sql")]
                migration = next((p for p in migration_candidates if p.exists()), None)
                if migration:
                    self.db.executescript(migration.read_text(encoding="utf-8"))
            applied = {r[0] for r in self.db.execute("SELECT version FROM schema_migrations")}
            if "0.3.1" not in applied:
                migration_candidates = [base / "db/migrations/003_isox_031.sql", Path("/usr/share/iso-x/db/migrations/003_isox_031.sql")]
                migration = next((p for p in migration_candidates if p.exists()), None)
                if migration:
                    self.db.executescript(migration.read_text(encoding="utf-8"))
            applied = {r[0] for r in self.db.execute("SELECT version FROM schema_migrations")}
            if "0.4.0" not in applied:
                migration_candidates = [base / "db/migrations/004_isox_040.sql", Path("/usr/share/iso-x/db/migrations/004_isox_040.sql")]
                migration = next((p for p in migration_candidates if p.exists()), None)
                if migration:
                    self.db.executescript(migration.read_text(encoding="utf-8"))
        if schema:
            self.db.executescript(schema.read_text(encoding="utf-8"))
        self.db.execute("INSERT OR IGNORE INTO kernel_watermark(watermark_key,watermark_value) VALUES('developer_name',?)", (DEVELOPER,))
        self.db.execute("INSERT OR IGNORE INTO app_registry(app_id,display_name,state,executable_path) VALUES(?,?,?,?)", ("browser", "Firefox ESR / NetSurf", "available", shutil.which("firefox-esr") or shutil.which("netsurf") or "firefox-esr"))
        self.refresh_watermark_status()
        self.db.commit()

    def refresh_watermark_status(self):
        """Locally verify the release module for display only; never send data remotely."""
        metadata = Path("/etc/isox")
        public_key = metadata / "watermark-public.pem"
        signature = metadata / "isox_watermark.ko.sig"
        checksum_file = metadata / "isox_watermark.sha256"
        fingerprint_file = metadata / "watermark-fingerprint.txt"
        if not all(p.is_file() and os.access(p, os.R_OK) for p in (public_key, signature, checksum_file, fingerprint_file)):
            return
        try:
            expected_hash = checksum_file.read_text(encoding="ascii").split()[0].lower()
            fingerprint = fingerprint_file.read_text(encoding="ascii").split("=", 1)[-1].replace(":", "").strip().lower()
            if not Path("/sys/module/isox_watermark").exists():
                return
            module_candidates = [Path("/lib/modules") / platform.release() / "updates/isox-watermark/isox_watermark.ko"]
            for module in module_candidates:
                actual_hash = hashlib.sha256(module.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    continue
                verified = subprocess.run(
                    ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", str(signature), str(module)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=3)
                if verified.returncode == 0 and len(fingerprint) == 64:
                    self.db.execute(
                        "UPDATE kernel_watermark SET module_sha256=?, signing_cert_fingerprint=?, verification_state='verified' WHERE watermark_key='developer_name'",
                        (actual_hash, fingerprint))
                    return
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            # The UI reports no result rather than assuming the module is verified.
            return

    def close(self): self.db.close()
    def app_used(self, app_id: str):
        # A local record only; no hostname, account identity, or remote endpoint.
        self.db.execute("CREATE TABLE IF NOT EXISTS local_app_usage(app_id TEXT NOT NULL, hour_of_day INTEGER NOT NULL, used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        self.db.execute("INSERT INTO local_app_usage(app_id,hour_of_day) VALUES(?,?)", (app_id, time.localtime().tm_hour))
        self.db.commit()

class ISOXGtk(Gtk.Window):
    def __init__(self):
        super().__init__(title="ISO-X — نظام عبدالله لازم")
        self.set_default_size(1160, 740)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name("iso-x")
        self.store = Store()
        self.page_index = 0
        self.last_ctrl = 0.0
        self.performance_mode = False
        self.left_path = HOME
        self.right_path = HOME
        self.connect("destroy", self.on_destroy)
        self.connect("key-press-event", self.on_key_press)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._build()
        self.switch_page(0)
        GLib.timeout_add_seconds(3, self.update_status)

    def on_destroy(self, *_):
        try: self.store.close()
        except Exception: pass
        Gtk.main_quit()

    def on_key_press(self, _widget, event):
        key = Gdk.keyval_name(event.keyval) or ""
        if key in ("1", "2", "3", "4") and not (event.state & Gdk.ModifierType.CONTROL_MASK):
            focus = self.get_focus()
            accepts_text = isinstance(focus, (Gtk.Entry, Gtk.TextView))
            if Vte and isinstance(focus, Vte.Terminal): accepts_text = True
            if not accepts_text:
                self.switch_page(int(key) - 1); return True
        if key in ("Control_L", "Control_R"):
            now = time.monotonic()
            if now - self.last_ctrl < 0.6: self.open_search()
            self.last_ctrl = now
        if key == "F12": self.open_dev_mode(); return True
        if key == "Escape": self.unfullscreen(); return True
        return False

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(outer)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_top(10); header.set_margin_bottom(10); header.set_margin_start(18); header.set_margin_end(18)
        header.get_style_context().add_class("iso-card")
        logo_path = Path("/usr/share/iso-x/assets/iso-x-dragon.svg")
        if logo_path.is_file():
            logo = Gtk.Image.new_from_file(str(logo_path)); logo.set_pixel_size(46)
            header.pack_start(logo, False, False, 0)
        brand = Gtk.Label(label="ISO-X"); brand.get_style_context().add_class("iso-title")
        header.pack_start(brand, False, False, 0)
        developer = Gtk.Label(label=f"المطور: {DEVELOPER}"); developer.get_style_context().add_class("iso-muted")
        header.pack_start(developer, False, False, 6)
        self.status = Gtk.Label(label="جارٍ فحص النظام…"); self.status.get_style_context().add_class("iso-highlight")
        header.pack_end(self.status, False, False, 3)
        outer.pack_start(header, False, False, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_margin_start(18); controls.set_margin_end(18); controls.set_margin_bottom(10)
        self.search_entry = Gtk.Entry(); self.search_entry.set_placeholder_text("بحث سريع في الأدوات والملفات… اضغط Enter")
        self.search_entry.connect("activate", lambda *_: self.run_search(self.search_entry.get_text()))
        controls.pack_start(self.search_entry, True, True, 0)
        b = Gtk.Button(label="بحث عالمي"); b.connect("clicked", lambda *_: self.open_search()); controls.pack_start(b, False, False, 0)
        browser = Gtk.Button(label="فتح المتصفح"); browser.connect("clicked", lambda *_: self.open_browser()); controls.pack_start(browser, False, False, 0)
        outer.pack_start(controls, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE)
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        self.stack.add_named(self._home_page(), "home")
        self.stack.add_named(self._files_page(), "files")
        self.stack.add_named(self._editor_page(), "editor")
        self.stack.add_named(self._terminal_page(), "terminal")
        self.stack.add_named(self._settings_page(), "settings")
        self.stack.add_named(self._browser_page(), "browser-page")
        outer.pack_start(self.stack, True, True, 0)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        bar.set_margin_start(18); bar.set_margin_end(18); bar.set_margin_top(10); bar.set_margin_bottom(6)
        for idx, label in enumerate(("1 · العمل", "2 · التطوير", "3 · الترفيه", "4 · شخصي")):
            button = Gtk.Button(label=label); button.connect("clicked", lambda _b, i=idx: self.switch_page(i)); bar.pack_start(button, False, False, 0)
        for label, callback in (("الملفات", self.show_files), ("المحرر", self.show_editor), ("الأوامر", self.show_terminal), ("الإعدادات", self.show_settings)):
            button = Gtk.Button(label=label); button.connect("clicked", lambda _b, cb=callback: cb()); bar.pack_start(button, False, False, 0)
        self.performance_button = Gtk.Button(label="⚡ الأداء الأقصى"); self.performance_button.connect("clicked", self.toggle_performance); bar.pack_end(self.performance_button, False, False, 0)
        outer.pack_start(bar, False, False, 0)
        footer = Gtk.Label(label=f"ISO-X 0.4.0  ·  {DEVELOPER}  ·  لا توجد قياسات بعيدة أو Telemetry")
        footer.get_style_context().add_class("iso-muted"); footer.set_margin_bottom(8)
        outer.pack_start(footer, False, False, 0)

    def card(self, title, description, button_text, callback):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        box.get_style_context().add_class("iso-card")
        heading = Gtk.Label(label=title, xalign=0); heading.get_style_context().add_class("iso-title")
        desc = Gtk.Label(label=description, xalign=0, yalign=0); desc.set_line_wrap(True); desc.set_max_width_chars(48); desc.get_style_context().add_class("iso-muted")
        btn = Gtk.Button(label=button_text); btn.connect("clicked", lambda *_: callback())
        box.pack_start(heading, False, False, 0); box.pack_start(desc, True, True, 0); box.pack_start(btn, False, False, 0)
        return box

    def _home_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(22); page.set_margin_end(22); page.set_margin_top(18); page.set_margin_bottom(18)
        title = Gtk.Label(label="مساحة ISO-X", xalign=0); title.get_style_context().add_class("iso-title"); page.pack_start(title, False, False, 0)
        note = Gtk.Label(label="واجهة GTK3 منخفضة التعقيد. خدمات المصادقة وإدارة النوافذ تبقى من Debian.", xalign=0); note.get_style_context().add_class("iso-muted"); page.pack_start(note, False, False, 0)
        grid = Gtk.Grid(column_spacing=12, row_spacing=12); grid.set_column_homogeneous(True); grid.set_row_homogeneous(True)
        cards = [
            ("ISO-FM · الملفات", "استعراض بمسارين ومعاينة نصية للملفات.", "فتح الملفات", self.show_files),
            ("ISO-Code · المحرر", "تحرير النصوص والشفرة وحفظها محليًا.", "فتح المحرر", self.show_editor),
            ("ISO-Terminal", "جلسة طرفية واحدة عند الطلب.", "فتح الطرفية", self.show_terminal),
            ("Firefox ESR / NetSurf", "يُفتح Firefox ESR عند توفره، وإلا NetSurf الخفيف.", "فتح المتصفح", self.open_browser),
            ("ISO-Control", "معلومات النظام ووضع تقليل المؤثرات.", "الإعدادات", self.show_settings),
            ("F12 · Dev Mode", "قياسات يدوية محلية فقط عند طلب المستخدم.", "مراقبة النظام", self.open_dev_mode),
        ]
        for i, item in enumerate(cards): grid.attach(self.card(*item), i % 3, i // 3, 1, 1)
        page.pack_start(grid, True, True, 0)
        return page

    def _files_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        title = Gtk.Label(label="ISO-FM · مدير الملفات ثنائي اللوحين", xalign=0); title.get_style_context().add_class("iso-title")
        page.pack_start(title, False, False, 4)
        paths = Gtk.Box(spacing=8); self.left_label = Gtk.Label(label=str(self.left_path), xalign=0); self.right_label = Gtk.Label(label=str(self.right_path), xalign=0)
        paths.pack_start(self.left_label, True, True, 3); paths.pack_start(self.right_label, True, True, 3); page.pack_start(paths, False, False, 0)
        toolbar = Gtk.Box(spacing=6)
        for label, callback in (("أعلى اليسار", lambda: self.go_up("left")), ("أعلى اليمين", lambda: self.go_up("right")), ("تحديث", self.refresh_files), ("نسخ ←", lambda: self.copy_selected("left")), ("نسخ →", lambda: self.copy_selected("right")), ("نقل للجهة الأخرى", self.move_selected), ("حذف المحدد", self.delete_selected)):
            b = Gtk.Button(label=label); b.connect("clicked", lambda _b, cb=callback: cb()); toolbar.pack_start(b, False, False, 0)
        page.pack_start(toolbar, False, False, 0)
        panes = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.left_store, self.left_tree = self._file_tree(self.left_path, "left")
        self.right_store, self.right_tree = self._file_tree(self.right_path, "right")
        for tree in (self.left_tree, self.right_tree):
            sc = Gtk.ScrolledWindow(); sc.set_hexpand(True); sc.set_vexpand(True); sc.add(tree); panes.pack1(sc, True, False) if tree is self.left_tree else panes.pack2(sc, True, False)
        page.pack_start(panes, True, True, 0)
        self.preview = Gtk.TextView(); self.preview.set_editable(False); self.preview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); self.preview.set_size_request(-1, 100)
        pv = Gtk.ScrolledWindow(); pv.set_min_content_height(92); pv.add(self.preview); page.pack_start(pv, False, True, 0)
        for tree, side in ((self.left_tree, "left"), (self.right_tree, "right")):
            tree.connect("row-activated", self.on_file_activated, side)
            tree.get_selection().connect("changed", self.on_file_selected, side)
        return page

    def _file_tree(self, path, side):
        store = Gtk.ListStore(str, str, str)
        tree = Gtk.TreeView(model=store)
        for i, name in enumerate(("الاسم", "النوع", "الحجم")):
            col = Gtk.TreeViewColumn(name, Gtk.CellRendererText(), text=i); col.set_resizable(True); tree.append_column(col)
        self._fill_tree(store, path)
        return store, tree

    def _fill_tree(self, store, path):
        store.clear(); path = Path(path).expanduser()
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
        except Exception:
            entries = []
        if path.parent != path:
            store.append(["..", "المجلد الأعلى", "—"])
        for p in entries[:1500]:
            try: typ = "مجلد" if p.is_dir() else ("رابط" if p.is_symlink() else "ملف")
            except Exception: typ = "غير معروف"
            try: size = "—" if p.is_dir() else f"{p.stat().st_size:,} B"
            except Exception: size = "—"
            store.append([p.name, typ, size])

    def on_file_activated(self, tree, path, column, side):
        model = tree.get_model(); row = model[path]
        base = self.left_path if side == "left" else self.right_path
        if row[0] == "..":
            target = base.parent
        else:
            target = (base / row[0]).resolve()
        try:
            if target.is_dir():
                if side == "left": self.left_path = target; self.left_label.set_text(str(target)); self._fill_tree(self.left_store, target)
                else: self.right_path = target; self.right_label.set_text(str(target)); self._fill_tree(self.right_store, target)
            else: self.preview_file(target)
        except Exception as exc: self.notify(f"تعذر فتح المسار: {exc}")

    def go_up(self, side):
        current = self.left_path if side == "left" else self.right_path
        parent = current.parent
        if parent == current: return
        if side == "left": self.left_path = parent; self.left_label.set_text(str(parent)); self._fill_tree(self.left_store, parent)
        else: self.right_path = parent; self.right_label.set_text(str(parent)); self._fill_tree(self.right_store, parent)

    def refresh_files(self):
        self._fill_tree(self.left_store, self.left_path); self._fill_tree(self.right_store, self.right_path)

    def copy_selected(self, destination_side):
        source_side = "left" if destination_side == "right" else "right"
        tree = self.left_tree if source_side == "left" else self.right_tree
        selection = tree.get_selection(); model, itr = selection.get_selected()
        if itr is None or model[itr][0] == "..":
            self.notify("حدد ملفًا أو مجلدًا عاديًا أولًا."); return
        source_base = self.left_path if source_side == "left" else self.right_path
        dest_base = self.right_path if destination_side == "right" else self.left_path
        source = source_base / model[itr][0]
        try:
            if source.is_symlink(): raise ValueError("نسخ الروابط الرمزية غير مدعوم من هذه الواجهة.")
            source = source.resolve(strict=True)
            dest_base = dest_base.resolve(strict=True)
            if source.is_dir() and (dest_base == source or source in dest_base.parents):
                raise ValueError("لا يمكن نسخ مجلد إلى داخله أو إلى أحد مجلداته الفرعية.")
            destination = dest_base / source.name
            if destination.exists() or destination.is_symlink(): raise FileExistsError(f"يرفض الكتابة فوق موجود: {destination}")
            confirm = Gtk.MessageDialog(transient_for=self, flags=Gtk.DialogFlags.MODAL, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text="تأكيد نسخ الملف")
            confirm.set_default_response(Gtk.ResponseType.NO)
            confirm.format_secondary_text(f"من: {source}\nإلى: {destination}")
            response = confirm.run(); confirm.destroy()
            if response != Gtk.ResponseType.YES: return
            self.status.set_text(f"جارٍ نسخ {source.name}…")
            threading.Thread(target=self._copy_worker, args=(source, destination), daemon=True).start()
        except Exception as exc: self.notify(f"تعذر النسخ: {exc}")

    def _copy_worker(self, source, destination):
        error = None
        try:
            if source.is_dir(): shutil.copytree(source, destination, symlinks=True)
            else: shutil.copy2(source, destination)
        except Exception as exc:
            error = str(exc)
        GLib.idle_add(self._copy_finished, destination, error)

    def _copy_finished(self, destination, error):
        self.refresh_files()
        if error:
            self.notify(f"تعذر النسخ: {error}")
        else:
            self.notify(f"تم النسخ إلى: {destination}")
        return False

    def on_file_selected(self, selection, side):
        self.active_side = side
        model, itr = selection.get_selected()
        if itr is None: return
        base = self.left_path if side == "left" else self.right_path
        p = (base / model[itr][0]).resolve()
        if p.is_file(): self.preview_file(p)

    def _selected_path(self):
        side = getattr(self, "active_side", "left")
        tree = self.left_tree if side == "left" else self.right_tree
        model, itr = tree.get_selection().get_selected()
        if itr is None or model[itr][0] == "..":
            raise ValueError("حدد ملفًا أو مجلدًا عاديًا أولًا.")
        base = self.left_path if side == "left" else self.right_path
        return side, base / model[itr][0]

    def move_selected(self, *_args):
        try:
            source_side, source = self._selected_path()
            if source.is_symlink():
                raise ValueError("نقل الروابط الرمزية غير مدعوم من هذه الواجهة.")
            source = source.resolve(strict=True)
            destination_base = (self.right_path if source_side == "left" else self.left_path).resolve(strict=True)
            if source.is_dir() and (destination_base == source or source in destination_base.parents):
                raise ValueError("لا يمكن نقل مجلد إلى داخله أو إلى أحد مجلداته الفرعية.")
            destination = destination_base / source.name
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f"يرفض الكتابة فوق موجود: {destination}")
            dialog = Gtk.MessageDialog(transient_for=self, flags=Gtk.DialogFlags.MODAL,
                                       message_type=Gtk.MessageType.QUESTION,
                                       buttons=Gtk.ButtonsType.YES_NO, text="تأكيد نقل الملف")
            dialog.format_secondary_text(f"من: {source}\nإلى: {destination}")
            dialog.set_default_response(Gtk.ResponseType.NO)
            response = dialog.run(); dialog.destroy()
            if response != Gtk.ResponseType.YES:
                return
            self.status.set_text(f"جارٍ نقل {source.name}…")
            threading.Thread(target=self._file_operation_worker,
                             args=("move", source, destination), daemon=True).start()
        except Exception as exc:
            self.notify(f"تعذر النقل: {exc}")

    def delete_selected(self, *_args):
        try:
            _side, source = self._selected_path()
            if not source.exists() and not source.is_symlink():
                raise FileNotFoundError(f"المسار غير موجود: {source}")
            dialog = Gtk.MessageDialog(transient_for=self, flags=Gtk.DialogFlags.MODAL,
                                       message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.YES_NO, text="حذف نهائي")
            dialog.format_secondary_text(f"سيُحذف هذا العنصر نهائيًا ولا يمكن استعادته:\n{source}")
            dialog.set_default_response(Gtk.ResponseType.NO)
            response = dialog.run(); dialog.destroy()
            if response != Gtk.ResponseType.YES:
                return
            self.status.set_text(f"جارٍ حذف {source.name}…")
            threading.Thread(target=self._file_operation_worker,
                             args=("delete", source, None), daemon=True).start()
        except Exception as exc:
            self.notify(f"تعذر الحذف: {exc}")

    def _file_operation_worker(self, operation, source, destination):
        error = None
        try:
            if operation == "move":
                shutil.move(str(source), str(destination))
            elif source.is_symlink() or source.is_file():
                source.unlink()
            else:
                shutil.rmtree(source)
        except Exception as exc:
            error = str(exc)
        GLib.idle_add(self._file_operation_finished, operation, source, destination, error)

    def _file_operation_finished(self, operation, source, destination, error):
        self.refresh_files()
        if error:
            self.notify(f"تعذر {('النقل' if operation == 'move' else 'الحذف')}: {error}")
        else:
            result = destination if operation == "move" else source
            self.notify(f"اكتمل {('النقل' if operation == 'move' else 'الحذف')}: {result}")
        return False

    def preview_file(self, path: Path):
        buf = self.preview.get_buffer()
        try:
            if path.stat().st_size > 512_000: text = "المعاينة النصية محدودة للملفات دون 512KB.\n" + str(path)
            else: text = path.read_text(encoding="utf-8", errors="replace")[:30000]
        except Exception as exc: text = f"لا تتوفر معاينة نصية لهذا الملف.\n{path}\n{exc}"
        buf.set_text(text)

    def _editor_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        row = Gtk.Box(spacing=8)
        self.editor_path = Gtk.Entry(); self.editor_path.set_placeholder_text("المسار الكامل للملف المراد تحريره")
        open_btn = Gtk.Button(label="فتح"); open_btn.connect("clicked", self.editor_open)
        save_btn = Gtk.Button(label="حفظ"); save_btn.connect("clicked", self.editor_save)
        row.pack_start(self.editor_path, True, True, 0); row.pack_start(open_btn, False, False, 0); row.pack_start(save_btn, False, False, 0)
        page.pack_start(row, False, False, 0)
        if GtkSource:
            self.editor = GtkSource.View(); self.editor.set_direction(Gtk.TextDirection.LTR); self.editor.set_show_line_numbers(True); self.editor.set_auto_indent(True)
            self.editor.set_highlight_current_line(True)
        else:
            self.editor = Gtk.TextView(); self.editor.set_direction(Gtk.TextDirection.LTR); self.editor.set_monospace(True)
        self.editor.set_wrap_mode(Gtk.WrapMode.NONE)
        sc = Gtk.ScrolledWindow(); sc.set_hexpand(True); sc.set_vexpand(True); sc.add(self.editor); page.pack_start(sc, True, True, 0)
        return page

    def editor_open(self, *_):
        path = Path(self.editor_path.get_text()).expanduser()
        try:
            text = path.read_text(encoding="utf-8")
            self.editor.get_buffer().set_text(text)
        except Exception as exc: self.notify(f"فشل فتح الملف: {exc}")

    def editor_save(self, *_):
        path = Path(self.editor_path.get_text()).expanduser()
        try:
            buf = self.editor.get_buffer(); start, end = buf.get_bounds()
            content = buf.get_text(start, end, True)
            path.parent.mkdir(parents=False, exist_ok=True)
            mode = path.stat().st_mode & 0o777 if path.exists() else None
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=f".{path.name}.", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            if mode is not None: os.chmod(temporary_path, mode)
            os.replace(temporary_path, path)
            self.notify(f"تم حفظ {path}")
        except Exception as exc:
            if "temporary_path" in locals(): temporary_path.unlink(missing_ok=True)
            self.notify(f"فشل الحفظ؛ بقي الملف الأصلي دون استبدال: {exc}")

    def _terminal_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        title = Gtk.Label(label="ISO-Terminal", xalign=0); title.get_style_context().add_class("iso-title"); page.pack_start(title, False, False, 0)
        self.terminal_grid = Gtk.Grid()
        self.terminals = []
        new_session = Gtk.Button(label="جلسة طرفية جديدة")
        new_session.connect("clicked", lambda *_: self._spawn_terminal())
        page.pack_start(new_session, False, False, 0)
        page.pack_start(self.terminal_grid, True, True, 0)
        return page

    def _spawn_terminal(self):
        if not Vte:
            self.launch_app("terminal", ["xterm"])
            return
        terminal = Vte.Terminal()
        terminal.set_scrollback_lines(1500)
        terminal.set_direction(Gtk.TextDirection.LTR)
        try:
            terminal.spawn_async(Vte.PtyFlags.DEFAULT, str(HOME), [os.environ.get("SHELL", "/bin/bash")], None,
                                 GLib.SpawnFlags.DEFAULT, None, None, -1, None, None, None)
        except Exception as exc:
            terminal.feed_child((f"تعذر إنشاء shell: {exc}\r\n").encode())
        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.add(terminal)
        self.terminal_grid.attach(scroller, 0, len(self.terminals), 1, 1)
        self.terminals.append(terminal)
        self.terminal_grid.show_all()

    def _browser_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_margin_start(24); page.set_margin_top(24)
        title = Gtk.Label(label="3 · الترفيه والويب", xalign=0); title.get_style_context().add_class("iso-title")
        desc = Gtk.Label(label="يتوفر Firefox ESR للمواقع الحديثة، وNetSurf كمتصفح خفيف مستقل.\nيفتح المتصفح كتطبيق مستقل؛ لا نعرض صفحات الويب داخل واجهة النظام.", xalign=0)
        desc.set_line_wrap(True); desc.get_style_context().add_class("iso-muted")
        btn = Gtk.Button(label="فتح المتصفح"); btn.set_halign(Gtk.Align.START); btn.connect("clicked", lambda *_: self.open_browser())
        # ISO-X 0.4.0: متصفح قوي اختياري + قياس سرعة الإنترنت
        row = Gtk.Box(spacing=8); row.set_halign(Gtk.Align.START)
        b_ff = Gtk.Button(label="Firefox ESR")
        b_ff.connect("clicked", lambda *_: self.open_or_install_firefox())
        b_sp = Gtk.Button(label="قياس سرعة الإنترنت")
        b_sp.connect("clicked", lambda *_: self.launch_app("speedtest", ["isox-speedtest", "--gui"]))
        row.pack_start(b_ff, False, False, 0); row.pack_start(b_sp, False, False, 0)
        page.pack_start(title, False, False, 0); page.pack_start(desc, False, False, 0)
        page.pack_start(btn, False, False, 0); page.pack_start(row, False, False, 0)
        return page

    def _settings_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(24); page.set_margin_top(22)
        title = Gtk.Label(label="ISO-Control · الإعدادات", xalign=0); title.get_style_context().add_class("iso-title"); page.pack_start(title, False, False, 0)
        info = Gtk.Label(label="النظام الأساسي: Debian Linux\nواجهة ISO-X: GTK3 + Openbox\nالمتصفحات: Firefox ESR وNetSurf\nالتحليلات البعيدة: معطلة\nاسم المطور المعروض: عبدالله لازم", xalign=0); info.set_line_wrap(True); page.pack_start(info, False, False, 0)
        btn = Gtk.Button(label="تبديل وضع الأداء الأقصى"); btn.connect("clicked", self.toggle_performance); page.pack_start(btn, False, False, 0)
        preload = Gtk.CheckButton(label="السماح بالتحميل المسبق الذكي (محلي فقط، اختياري)")
        current = self.store.db.execute("SELECT setting_value FROM privacy_settings WHERE setting_key='preload_enabled'").fetchone()
        preload.set_active(bool(current and current[0] == "enabled"))
        def update_preload(widget):
            value = "enabled" if widget.get_active() else "disabled"
            self.store.db.execute("UPDATE privacy_settings SET setting_value=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE setting_key='preload_enabled'", (value,))
            self.store.db.commit()
            self.notify("التحميل المسبق سيعمل محليًا فقط عند تحقق شروط الذاكرة والحمل." if value == "enabled" else "تم تعطيل التحميل المسبق.")
        preload.connect("toggled", update_preload); page.pack_start(preload, False, False, 0)
        zram = Gtk.Label(label="ZRAM يُدار عبر خدمة systemd مستقلة؛ تأكد من حالة الخدمة بعد الإقلاع.", xalign=0); zram.get_style_context().add_class("iso-muted"); page.pack_start(zram, False, False, 0)
        return page

    def switch_page(self, index):
        self.page_index = index
        name = ("home", "editor", "browser-page", "settings")[index % 4]
        self.stack.set_visible_child_name(name)
    def show_files(self): self.stack.set_visible_child_name("files"); self.store.app_used("files")
    def show_editor(self): self.stack.set_visible_child_name("editor"); self.store.app_used("editor")
    def show_terminal(self):
        self.stack.set_visible_child_name("terminal")
        if not self.terminals: self._spawn_terminal()
        self.store.app_used("terminal")
    def show_settings(self): self.stack.set_visible_child_name("settings")

    def open_search(self):
        dialog = Gtk.Dialog(title="ISO-X · البحث العالمي", transient_for=self, flags=Gtk.DialogFlags.MODAL)
        dialog.add_button("إغلاق", Gtk.ResponseType.CLOSE); dialog.add_button("بحث", Gtk.ResponseType.ACCEPT)
        entry = Gtk.Entry(); entry.set_placeholder_text("اسم تطبيق أو ملف ضمن مجلد المنزل")
        area = dialog.get_content_area(); area.set_spacing(8); area.set_margin_top(12); area.set_margin_bottom(12); area.set_margin_start(12); area.set_margin_end(12); area.pack_start(entry, False, False, 0); entry.show()
        entry.connect("activate", lambda *_: dialog.response(Gtk.ResponseType.ACCEPT))
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.ACCEPT: self.run_search(entry.get_text())
        dialog.destroy()

    def run_search(self, query):
        q = query.strip()
        if not q: return
        routes = {"ملفات": self.show_files, "files": self.show_files, "محرر": self.show_editor, "code": self.show_editor,
                  "طرفية": self.show_terminal, "terminal": self.show_terminal, "إعدادات": self.show_settings, "settings": self.show_settings}
        if q.casefold() in routes: routes[q.casefold()](); return
        if q.casefold() in ("netsurf", "firefox", "متصفح", "browser"): self.open_browser(); return
        self.status.set_text(f"جارٍ البحث عن: {q}")
        threading.Thread(target=self._search_worker, args=(q,), daemon=True).start()

    def _search_worker(self, query):
        results = []
        try:
            for root, dirs, files in os.walk(HOME):
                current = Path(root).resolve()
                trash = (HOME / ".local/share/Trash").resolve()
                if current == trash or trash in current.parents:
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs if d not in {".cache", ".git", "node_modules", ".venv"}]
                for name in files + dirs:
                    if query.casefold() in name.casefold(): results.append(str(Path(root) / name))
                    if len(results) >= 80: break
                if len(results) >= 80: break
        except Exception as exc: results.append(f"تعذّر البحث: {exc}")
        GLib.idle_add(self._show_search_results, query, results)

    def _show_search_results(self, query, results):
        self.status.set_text("بحث ISO-X")
        dlg = Gtk.MessageDialog(transient_for=self, flags=Gtk.DialogFlags.MODAL, message_type=Gtk.MessageType.INFO,
                                buttons=Gtk.ButtonsType.CLOSE, text=f"نتائج البحث: {query}")
        dlg.format_secondary_text("\n".join(results[:30]) if results else "لا توجد نتائج ضمن مجلد المنزل.")
        dlg.run(); dlg.destroy()
        return False

    def open_dev_mode(self):
        dlg = Gtk.Dialog(title="ISO-X · Dev Mode (F12)", transient_for=self, flags=Gtk.DialogFlags.MODAL)
        dlg.add_button("إغلاق", Gtk.ResponseType.CLOSE)
        box = dlg.get_content_area(); box.set_spacing(8); box.set_margin_top(12); box.set_margin_start(12); box.set_margin_end(12)
        text = Gtk.TextView(); text.set_editable(False); text.set_monospace(True)
        buf = text.get_buffer(); buf.set_text("اجمع القياسات عند الطلب فقط. لا يتم إرسالها إلى الإنترنت.\n\n" + self.collect_stats())
        sc = Gtk.ScrolledWindow(); sc.set_min_content_height(300); sc.add(text); box.pack_start(sc, True, True, 0)
        refresh = Gtk.Button(label="تحديث القياسات المحلية"); refresh.connect("clicked", lambda *_: buf.set_text(self.collect_stats())); box.pack_start(refresh, False, False, 0)
        dlg.show_all(); dlg.run(); dlg.destroy()

    def collect_stats(self):
        lines = [f"system={platform.platform()}", f"kernel={platform.release()}", f"cores={os.cpu_count()}"]
        try:
            for line in Path("/proc/meminfo").read_text().splitlines()[:5]: lines.append(line)
            lines.append(f"uptime={Path('/proc/uptime').read_text().split()[0]} sec")
            if shutil.which("uptime"): lines.append(subprocess.run(["uptime"], capture_output=True, text=True, timeout=2).stdout.strip())
            if shutil.which("ps"): lines.extend(subprocess.run(["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%mem"], capture_output=True, text=True, timeout=2).stdout.splitlines()[:11])
        except Exception as exc: lines.append(f"error={exc}")
        return "\n".join(lines)

    def toggle_performance(self, *_):
        self.performance_mode = not self.performance_mode
        Gtk.Settings.get_default().set_property("gtk-enable-animations", not self.performance_mode)
        self.performance_button.set_label("✓ الأداء الأقصى مفعل" if self.performance_mode else "⚡ الأداء الأقصى")
        self.notify("تم تقليل مؤثرات GTK." if self.performance_mode else "تمت استعادة مؤثرات GTK.")

    def open_browser(self):
        if shutil.which("firefox-esr"):
            self.launch_app("browser", ["firefox-esr"])
        elif shutil.which("firefox"):
            self.launch_app("browser", ["firefox"])
        elif shutil.which("netsurf"):
            self.launch_app("browser", ["netsurf"])
        else:
            self.notify("لم يُعثر على Firefox ESR أو NetSurf. افتح متجر ISO-X وتحقق من اتصال الإنترنت.")

    def open_or_install_firefox(self):
        if shutil.which("firefox-esr") or shutil.which("firefox"):
            self.open_browser(); return
        self.launch_app("appcenter", ["python3", "/usr/share/iso-x/isox_appcenter.py"])

    def launch_app(self, app_id, argv):
        executable = shutil.which(argv[0])
        if not executable:
            self.notify(f"التطبيق غير مثبت: {argv[0]}")
            return
        try:
            subprocess.Popen(argv, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.store.app_used(app_id)
        except Exception as exc: self.notify(f"فشل تشغيل التطبيق: {exc}")

    def update_status(self):
        try:
            avail = next((line.split(":",1)[1].strip() for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")), "غير متاح")
            self.status.set_text(f"النواة {platform.release()}  ·  متاح {avail}")
        except Exception: self.status.set_text("ISO-X GTK3")
        return True

    def notify(self, message):
        dlg = Gtk.MessageDialog(transient_for=self, flags=Gtk.DialogFlags.MODAL,
                                message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text=message)
        dlg.run(); dlg.destroy()

def main():
    Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)
    win = ISOXGtk()
    win.show_all()
    win.maximize()
    # This is a user session shell, not a PAM login greeter. LightDM performs authentication.
    Gtk.main()

if __name__ == "__main__": main()
