#!/usr/bin/env python3
"""Safe-ish desktop Run dialog: spawn an argument vector, never shell=True."""
from __future__ import annotations
import shlex
import shutil
import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class RunDialog(Gtk.Dialog):
    def __init__(self):
        super().__init__(title="ISO-X · تشغيل أمر", flags=Gtk.DialogFlags.MODAL)
        self.set_border_width(12)
        self.set_default_size(520, 130)
        self.add_button("إلغاء", Gtk.ResponseType.CANCEL)
        self.add_button("تشغيل", Gtk.ResponseType.OK)
        area = self.get_content_area()
        area.set_spacing(8)
        label = Gtk.Label(label="اكتب اسم تطبيق أو أمرًا مع معاملاته:", xalign=0)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("مثال: thunar أو xfce4-terminal")
        self.entry.connect("activate", lambda *_: self.response(Gtk.ResponseType.OK))
        area.pack_start(label, False, False, 0)
        area.pack_start(self.entry, False, False, 0)
        self.show_all()
        self.entry.grab_focus()

    def run_command(self) -> int:
        try:
            argv = shlex.split(self.entry.get_text().strip())
            if not argv:
                raise ValueError("اكتب أمرًا أولًا.")
            executable = argv[0]
            if "/" in executable:
                import os
                if not (os.path.isfile(executable) and os.access(executable, os.X_OK)):
                    raise FileNotFoundError(f"التطبيق غير موجود أو ليس قابلًا للتنفيذ: {executable}")
            elif shutil.which(executable) is None:
                raise FileNotFoundError(f"التطبيق غير موجود ضمن PATH: {executable}")
            subprocess.Popen(argv, start_new_session=True)
            return 0
        except (ValueError, OSError) as exc:
            error = Gtk.MessageDialog(transient_for=self, flags=Gtk.DialogFlags.MODAL,
                                      message_type=Gtk.MessageType.ERROR,
                                      buttons=Gtk.ButtonsType.CLOSE, text="تعذر تشغيل الأمر")
            error.format_secondary_text(str(exc))
            error.run()
            error.destroy()
            return 1

def main() -> int:
    dialog = RunDialog()
    response = dialog.run()
    result = dialog.run_command() if response == Gtk.ResponseType.OK else 0
    dialog.destroy()
    return result

if __name__ == "__main__":
    raise SystemExit(main())
