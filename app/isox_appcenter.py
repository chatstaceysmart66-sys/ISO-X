#!/usr/bin/env python3
# ISO-X App Center 0.4.0 — تثبيت/إزالة تطبيقات مع اختصارات على سطح المكتب
import gi, os, subprocess, threading, json
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
    {"name": "PDF Viewer", "pkg": "evince", "exec": "evince", "cat": "مكتب", "desc": "قراءة PDF"},
    {"name": "Image Viewer", "pkg": "ristretto", "exec": "ristretto", "cat": "وسائط", "desc": "عرض الصور"},
    {"name": "Audio Player", "pkg": "audacious", "exec": "audacious", "cat": "وسائط", "desc": "تشغيل الصوتيات"},
    {"name": "Disk Partitioner", "pkg": "gparted", "exec": "gparted", "cat": "النظام", "desc": "تقسيم الأقراص مع صلاحيات الإدارة"},
]

def pkg_installed(pkg):
    r = subprocess.run(['dpkg-query','-W','-f=${Status}',pkg],
                       capture_output=True, text=True)
    return 'install ok installed' in r.stdout

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
        self.spinner = Gtk.Spinner()
        h = Gtk.Box(spacing=6)
        h.pack_start(self.spinner, False, False, 0)
        h.pack_start(self.status, False, False, 0)
        box.pack_start(h, False, False, 2)

        self.grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        sw = Gtk.ScrolledWindow(); sw.add(self.grid)
        box.pack_start(sw, True, True, 0)
        self._populate()

    def _populate(self):
        for c in self.grid.get_children(): self.grid.remove(c)
        for i, app in enumerate(CATALOG):
            card = Gtk.Frame(); v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            v.set_border_width(8)
            v.pack_start(Gtk.Label(label=f"<b>{app['name']}</b>", use_markup=True), False, False, 0)
            v.pack_start(Gtk.Label(label=f"{app['cat']} — {app['desc']}"), False, False, 0)
            installed = pkg_installed(app['pkg'])
            btn = Gtk.Button(label='مثبت — إزالة' if installed else 'تثبيت التطبيق')
            btn.set_sensitive(True)
            btn.connect('clicked', self._toggle, app, installed)
            v.pack_start(btn, False, False, 0)
            card.add(v)
            self.grid.attach(card, i % 3, i // 3, 1, 1)
        self.show_all()

    def _toggle(self, _b, app, installed):
        _b.set_sensitive(False)
        self.spinner.start()
        self.status.set_label(f"{'جارٍ إزالة' if installed else 'جارٍ تثبيت'} {app['name']} ...")
        action = ['apt-get','remove','-y'] if installed else ['apt-get','install','-y']
        def work():
            r = subprocess.run(['pkexec'] + action + [app['pkg']],
                               capture_output=True, text=True)
            def done():
                self.spinner.stop()
                if r.returncode == 0 and not installed:
                    make_desktop_shortcut(app['name'], app['exec'])
                    self.status.set_label(f"✅ تم تثبيت {app['name']} وإنشاء اختصار على سطح المكتب")
                elif r.returncode == 0:
                    remove_desktop_shortcut(app['name'])
                    self.status.set_label(f"تمت إزالة {app['name']} وحذف اختصاره إن كان موجودًا")
                else:
                    self.status.set_label('فشل التثبيت/الإزالة: ' + ((r.stderr or r.stdout or 'لا توجد تفاصيل').strip().splitlines()[-1][:180]))
                self._populate()
            GLib.idle_add(done)
        threading.Thread(target=work, daemon=True).start()

if __name__ == '__main__':
    AppCenter().connect('destroy', Gtk.main_quit)
    Gtk.main()
