#!/usr/bin/env python3
# ISO-X App Center 0.4.0 — تثبيت/إزالة تطبيقات مع اختصارات على سطح المكتب
import gi, os, subprocess, threading
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

DESKTOP_DIR = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or os.path.expanduser('~/Desktop')

CATALOG = [
    {"name": "Firefox ESR", "pkg": "firefox-esr", "exec": "firefox-esr", "cat": "إنترنت", "desc": "متصفح كامل للمواقع الحديثة"},
    {"name": "LibreOffice", "pkg": "libreoffice-writer", "exec": "libreoffice --writer", "cat": "مكتب", "desc": "معالج نصوص وجداول وعروض"},
    {"name": "VLC", "pkg": "vlc", "exec": "vlc", "cat": "وسائط", "desc": "مشغل فيديو وصوتيات"},
    {"name": "GIMP", "pkg": "gimp", "exec": "gimp", "cat": "وسائط", "desc": "تحرير صور احترافي"},
    {"name": "Evince", "pkg": "evince", "exec": "evince", "cat": "مكتب", "desc": "عارض PDF"},
    {"name": "FileZilla", "pkg": "filezilla", "exec": "filezilla", "cat": "أدوات", "desc": "نقل ملفات FTP/SFTP"},
    {"name": "Thunderbird", "pkg": "thunderbird", "exec": "thunderbird", "cat": "إنترنت", "desc": "بريد إلكتروني"},
    {"name": "Git GUI", "pkg": "git-gui", "exec": "git gui", "cat": "أدوات", "desc": "واجهة رسومية لـ Git"},
    {"name": "Hardware Information", "pkg": "hardinfo", "exec": "hardinfo", "cat": "النظام", "desc": "معلومات الأجهزة ومكوناتها"},
    {"name": "GNOME Calendar", "pkg": "gnome-calendar", "exec": "gnome-calendar", "cat": "شخصي", "desc": "التقويم والمواعيد"},
    {"name": "GNOME Disks", "pkg": "gnome-disk-utility", "exec": "gnome-disks", "cat": "النظام", "desc": "إدارة الأقراص والأقسام"},
    {"name": "Archive Manager", "pkg": "file-roller", "exec": "file-roller", "cat": "أدوات", "desc": "إنشاء واستخراج الأرشيفات"},
    {"name": "Image Viewer", "pkg": "ristretto", "exec": "ristretto", "cat": "وسائط", "desc": "عرض الصور"},
    {"name": "Audio Player", "pkg": "audacious", "exec": "audacious", "cat": "وسائط", "desc": "تشغيل الصوتيات"},
    {"name": "Disk Partitioner", "pkg": "gparted", "exec": "gparted", "cat": "النظام", "desc": "تقسيم الأقراص مع صلاحيات الإدارة"},
]

def pkg_installed(pkg):
    result = subprocess.run(
        ['dpkg-query', '-W', '-f=${Status}', pkg],
        capture_output=True, text=True, timeout=15,
    )
    return result.returncode == 0 and 'install ok installed' in result.stdout

def shortcut_path(name):
    return os.path.join(DESKTOP_DIR, f"{name.replace(' ','_')}.desktop")

def remove_desktop_shortcut(name):
    try:
        os.unlink(shortcut_path(name))
    except FileNotFoundError:
        pass

def make_desktop_shortcut(name, exec_cmd, icon='application-x-executable'):
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    path = shortcut_path(name)
    with open(path, 'w') as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name={name}
Exec={exec_cmd}
Icon={icon}
Terminal=false
Categories=Utility;
""")
    os.chmod(path, 0o755)
    return path

class AppCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title='ISO-X مركز التطبيقات')
        self.set_default_size(720, 520)
        self.set_border_width(12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(box)
        box.pack_start(Gtk.Label(label='<b><span size="x-large">مركز تثبيت التطبيقات</span></b>',
                                 use_markup=True), False, False, 4)
        self.status = Gtk.Label(label='جاهز')
        self.status.set_line_wrap(True)
        self.status.set_selectable(True)
        self.spinner = Gtk.Spinner()
        h = Gtk.Box(spacing=6)
        h.pack_start(self.spinner, False, False, 0)
        h.pack_start(self.status, False, False, 0)
        box.pack_start(h, False, False, 2)
        refresh = Gtk.Button(label='تحديث فهارس التطبيقات')
        refresh.connect('clicked', self._update_indexes)
        box.pack_start(refresh, False, False, 0)

        self.grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        sw = Gtk.ScrolledWindow(); sw.add(self.grid)
        box.pack_start(sw, True, True, 0)
        self.package_states = {}
        self.busy = False
        self._populate()
        self._refresh_states()

    def _populate(self):
        for c in self.grid.get_children(): self.grid.remove(c)
        for i, app in enumerate(CATALOG):
            card = Gtk.Frame(); v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            v.set_border_width(8)
            v.pack_start(Gtk.Label(label=f"<b>{app['name']}</b>", use_markup=True), False, False, 0)
            v.pack_start(Gtk.Label(label=f"{app['cat']} — {app['desc']}"), False, False, 0)
            installed = self.package_states.get(app['pkg'])
            label = 'جارٍ التحقق...' if installed is None else (
                'مثبت — إزالة' if installed else 'تثبيت التطبيق'
            )
            btn = Gtk.Button(label=label)
            btn.set_sensitive(installed is not None and not self.busy)
            if installed is not None:
                btn.connect('clicked', self._toggle, app, installed)
            v.pack_start(btn, False, False, 0)
            card.add(v)
            self.grid.attach(card, i % 3, i // 3, 1, 1)
        self.show_all()

    def _refresh_states(self):
        packages = sorted({app['pkg'] for app in CATALOG})

        def work():
            states = {}
            errors = []
            for package in packages:
                try:
                    states[package] = pkg_installed(package)
                except (OSError, subprocess.SubprocessError) as exc:
                    states[package] = None
                    errors.append(str(exc))

            def done():
                self.package_states.update(states)
                self._populate()
                if errors:
                    self.status.set_label('تعذر الاستعلام عن حالة بعض الحزم: ' + errors[0])
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, daemon=True).start()

    def _run_privileged(self, arguments):
        return subprocess.run(
            ['pkexec', 'apt-get', *arguments],
            capture_output=True, text=True, timeout=600,
        )

    def _update_indexes(self, _button):
        if self.busy:
            return
        self.busy = True
        self.spinner.start()
        self.status.set_label('جارٍ تحديث فهارس APT...')
        self._populate()

        def work():
            try:
                result = self._run_privileged(['update'])
                error = None
            except (OSError, subprocess.SubprocessError) as exc:
                result, error = None, str(exc)

            def done():
                self.busy = False
                self.spinner.stop()
                if error:
                    self.status.set_label('تعذر تحديث الفهارس: ' + error)
                elif result.returncode:
                    details = (result.stderr or result.stdout or 'لا توجد تفاصيل').strip()
                    self.status.set_label('فشل تحديث فهارس APT: ' + details[-500:])
                else:
                    self.status.set_label('تم تحديث فهارس APT.')
                self._populate()
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, daemon=True).start()

    def _toggle(self, _b, app, installed):
        if installed:
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK_CANCEL, text='إزالة التطبيق؟',
            )
            dialog.set_default_response(Gtk.ResponseType.CANCEL)
            dialog.format_secondary_text(
                f"سيُطلب إذن إداري لإزالة {app['name']}. قد تتأثر الحزم التي تعتمد عليه."
            )
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
        self.busy = True
        _b.set_sensitive(False)
        self.spinner.start()
        self.status.set_label(f"{'جارٍ إزالة' if installed else 'جارٍ تثبيت'} {app['name']} ...")
        self._populate()

        def work():
            try:
                if installed:
                    result = self._run_privileged(['remove', '-y', app['pkg']])
                else:
                    result = self._run_privileged(['update'])
                    if result.returncode == 0:
                        result = self._run_privileged(
                            ['install', '-y', '--no-install-recommends', app['pkg']]
                        )
                error = None
            except (OSError, subprocess.SubprocessError) as exc:
                result, error = None, str(exc)

            def done():
                self.busy = False
                self.spinner.stop()
                if error:
                    self.status.set_label('تعذر تشغيل مدير الحزم: ' + error)
                elif result.returncode == 0 and not installed:
                    self.package_states[app['pkg']] = True
                    try:
                        make_desktop_shortcut(app['name'], app['exec'])
                        self.status.set_label(f"تم تثبيت {app['name']} وإنشاء اختصار على سطح المكتب")
                    except OSError as exc:
                        self.status.set_label(f"تم تثبيت {app['name']} لكن تعذر إنشاء الاختصار: {exc}")
                elif result.returncode == 0:
                    self.package_states[app['pkg']] = False
                    try:
                        remove_desktop_shortcut(app['name'])
                        self.status.set_label(f"تمت إزالة {app['name']} وحذف اختصاره إن كان موجودًا")
                    except OSError as exc:
                        self.status.set_label(f"تمت إزالة {app['name']} لكن تعذر حذف الاختصار: {exc}")
                else:
                    details = (result.stderr or result.stdout or 'لا توجد تفاصيل').strip()
                    self.status.set_label('فشل التثبيت/الإزالة: ' + details[-500:])
                self._populate()
                if result is None or result.returncode != 0:
                    self._refresh_states()
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, daemon=True).start()

if __name__ == '__main__':
    AppCenter().connect('destroy', Gtk.main_quit)
    Gtk.main()
