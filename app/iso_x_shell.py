#!/usr/bin/env python3
"""ISO-X desktop shell prototype. Standard-library-only UI for low-resource Linux."""
from __future__ import annotations
import os, sys, time, json, sqlite3, subprocess, webbrowser, platform
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "ISO-X"
DEVELOPER = "عبدالله لازم"  # Branding for ISO-X shell; not compiled into the Linux kernel.
BG = "#0A0A0F"
PANEL = "#12121C"
PANEL2 = "#191927"
CYAN = "#00E5FF"
PURPLE = "#7C4DFF"
ORANGE = "#FF6D00"
WHITE = "#F5F5F5"
MUTED = "#9AA5B8"
GREEN = "#62E6B5"
HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "iso-x"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "iso-x.db"


def read_text(path: Path, limit: int = 180_000) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except Exception as exc:
        return f"تعذرت القراءة: {exc}"


def command_exists(name: str) -> bool:
    from shutil import which
    return which(name) is not None


def resource_stats() -> dict[str, str]:
    mem_total = mem_available = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) * 1024
            elif line.startswith("MemAvailable:"):
                mem_available = int(line.split()[1]) * 1024
    except Exception:
        pass
    def human(value):
        if value is None: return "غير متاح"
        if value >= 1024**3: return f"{value / 1024**3:.2f} GB"
        return f"{value / 1024**2:.0f} MB"
    try:
        uptime = float(Path("/proc/uptime").read_text().split()[0])
        uptime_text = f"{int(uptime // 3600)} س {int((uptime % 3600) // 60)} د"
    except Exception:
        uptime_text = "غير متاح"
    return {
        "ram_total": human(mem_total),
        "ram_available": human(mem_available),
        "cores": str(os.cpu_count() or "غير معروف"),
        "uptime": uptime_text,
        "kernel": platform.release(),
        "system": platform.system(),
    }


class Store:
    def __init__(self):
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        candidates = [Path(__file__).resolve().parent.parent / "db" / "schema.sql",
                      Path("/usr/share/iso-x/schema.sql")]
        schema_path = next((p for p in candidates if p.exists()), None)
        if schema_path:
            self.db.executescript(schema_path.read_text(encoding="utf-8"))
        else:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS app_registry(app_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'available');
                CREATE TABLE IF NOT EXISTS kernel_watermark(watermark_key TEXT PRIMARY KEY, watermark_value TEXT NOT NULL);
            """)
        self.db.execute("INSERT OR IGNORE INTO kernel_watermark(watermark_key,watermark_value) VALUES('developer_name',?)", (DEVELOPER,))
        apps = [
            ("files", "ISO-FM", "available"), ("terminal", "ISO-Terminal", "available"),
            ("code", "ISO-Code", "available"), ("settings", "ISO-Control", "available"),
            ("packages", "ISO-Pkg", "available"), ("containers", "ISO-Hub", "external-runtime"),
            ("vm", "ISO-VM", "optional-runtime"), ("monitor", "Dev Mode", "available"),
        ]
        self.db.executemany("INSERT OR IGNORE INTO app_registry(app_id,display_name,state) VALUES(?,?,?)", apps)
        self.db.commit()


class ISOX:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.store = Store()
        self.page = 0
        self.performance_mode = False
        self.animations_enabled = True
        self.last_ctrl = 0.0
        self.taskbar_position = "bottom"
        self._splash_start = time.monotonic()
        self._particles = []
        self._splash_canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.root.title("ISO-X | نظام عبدالله لازم")
        self.root.configure(bg=BG)
        self.root.geometry("1180x740")
        self.root.minsize(820, 560)
        try: self.root.attributes("-fullscreen", True)
        except tk.TclError: pass
        self.root.bind("<F12>", lambda _e: self.open_dev_mode())
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<KeyPress-1>", lambda _e: self.set_page(0))
        self.root.bind("<KeyPress-2>", lambda _e: self.set_page(1))
        self.root.bind("<KeyPress-3>", lambda _e: self.set_page(2))
        self.root.bind("<KeyPress-4>", lambda _e: self.set_page(3))
        self.root.bind("<Control-MouseWheel>", self.on_wheel)
        self.root.bind("<Control-Button-4>", lambda _e: self.set_page((self.page - 1) % 4))
        self.root.bind("<Control-Button-5>", lambda _e: self.set_page((self.page + 1) % 4))
        self.root.bind("<Control_L>", self.ctrl_pressed)
        self.root.bind("<Control_R>", self.ctrl_pressed)
        self._show_splash()

    def exit_fullscreen(self, _event=None):
        try: self.root.attributes("-fullscreen", False)
        except tk.TclError: pass

    def ctrl_pressed(self, _event=None):
        now = time.monotonic()
        if now - self.last_ctrl < 0.55:
            self.open_search()
            self.last_ctrl = 0.0
        else:
            self.last_ctrl = now

    def on_wheel(self, event):
        if event.delta < 0: self.set_page((self.page + 1) % 4)
        else: self.set_page((self.page - 1) % 4)

    def _show_splash(self):
        self._splash_canvas.pack(fill="both", expand=True)
        self._splash_canvas.bind("<Configure>", lambda _e: self._paint_splash())
        self._paint_splash()
        self._animate_splash()

    def _paint_splash(self):
        c = self._splash_canvas
        c.delete("all")
        self._particles = []
        w = max(c.winfo_width(), 600); h = max(c.winfo_height(), 400)
        c.create_text(w/2, h*.20, text="ISO-X", fill=CYAN, font=("DejaVu Sans", 25, "bold"))
        cx, cy = w/2, h*.43
        radius = min(w,h)*.105
        points=[]
        for i in range(6):
            a = (60*i-30)*3.14159/180
            points.extend([cx+radius*__import__('math').cos(a), cy+radius*__import__('math').sin(a)])
        c.create_polygon(points, outline=CYAN, fill=BG, width=3)
        # A stylized twin-wing emblem (visual mark, not an external logo).
        c.create_line(cx,cy-28, cx-15,cy-8, cx-30,cy-18, cx-22,cy+2, cx-34,cy+14,
                      cx-11,cy+10,cx,cy+25,cx+11,cy+10,cx+34,cy+14,cx+22,cy+2,
                      cx+30,cy-18,cx+15,cy-8,cx,cy-28, fill=PURPLE, width=4, smooth=True)
        c.create_line(cx-3,cy-12,cx+7,cy-5,cx-5,cy+7,cx+4,cy+5, fill=WHITE, width=2)
        c.create_text(w/2, h*.66, text="نظام خفيف. مساحة أوسع للإبداع.", fill=WHITE,
                      font=("DejaVu Sans", 15))
        c.create_text(w/2, h*.73, text=f"المطور: {DEVELOPER}", fill=CYAN,
                      font=("DejaVu Sans", 13, "bold"))
        for _ in range(45):
            x = __import__('random').randint(20, w-20); y = __import__('random').randint(10, h-10)
            r = __import__('random').choice([1,1,2])
            item = c.create_oval(x-r,y-r,x+r,y+r,fill=__import__('random').choice([CYAN,PURPLE,"#43506c"]),outline="")
            self._particles.append(item)

    def _animate_splash(self):
        if not self.animations_enabled:
            self._show_desktop(); return
        # Keep the splash brief and avoid an expensive 3-D renderer on weak GPUs.
        if time.monotonic() - self._splash_start >= 1.8:
            self._show_desktop(); return
        try:
            for item in self._particles:
                self._splash_canvas.move(item, 0, -1)
                coords = self._splash_canvas.coords(item)
                if coords and coords[1] < 0:
                    self._splash_canvas.move(item, 0, self._splash_canvas.winfo_height())
        except tk.TclError: pass
        self.root.after(60, self._animate_splash)

    def _show_desktop(self):
        self._splash_canvas.destroy()
        self._build_shell()
        self.set_page(0)
        self.refresh_status()

    def _build_shell(self):
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill="both", expand=True)
        self.header = tk.Frame(self.shell, bg=PANEL, height=62)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        tk.Label(self.header, text="⬡  ISO-X", bg=PANEL, fg=CYAN,
                 font=("DejaVu Sans", 18, "bold")).pack(side="left", padx=22)
        tk.Label(self.header, text=f"المطور: {DEVELOPER}", bg=PANEL, fg=MUTED,
                 font=("DejaVu Sans", 10)).pack(side="left", padx=10)
        self.status = tk.Label(self.header, text="جارٍ فحص النظام…", bg=PANEL, fg=GREEN,
                               font=("DejaVu Sans", 10))
        self.status.pack(side="right", padx=18)
        self.body = tk.Frame(self.shell, bg=BG)
        self.body.pack(fill="both", expand=True, padx=22, pady=18)
        self.page_header = tk.Frame(self.body, bg=BG)
        self.page_header.pack(fill="x", pady=(0,14))
        self.page_title = tk.Label(self.page_header, text="", bg=BG, fg=WHITE,
                                   font=("DejaVu Sans", 21, "bold"), anchor="e")
        self.page_title.pack(side="right")
        tk.Button(self.page_header, text="⌕  البحث العام  · Ctrl مرتين", command=self.open_search,
                  bg=PANEL2, fg=CYAN, activebackground=PURPLE, activeforeground=WHITE,
                  relief="flat", padx=12, pady=7, font=("DejaVu Sans", 10)).pack(side="left")
        self.cards = tk.Frame(self.body, bg=BG)
        self.cards.pack(fill="both", expand=True)
        self.taskbar = tk.Frame(self.shell, bg=PANEL, height=58)
        self.taskbar.pack(side="bottom", fill="x")
        self.taskbar.pack_propagate(False)
        pages = ["١  العمل", "٢  التطوير", "٣  الترفيه", "٤  شخصي"]
        self.page_buttons=[]
        for index, label in enumerate(pages):
            button = tk.Button(self.taskbar, text=label, command=lambda i=index: self.set_page(i),
                               bg=PANEL, fg=MUTED, activebackground=PANEL2, activeforeground=CYAN,
                               relief="flat", padx=18, font=("DejaVu Sans", 10, "bold"))
            button.pack(side="left", padx=4, pady=9)
            self.page_buttons.append(button)
        tk.Button(self.taskbar, text="الأداء", command=self.toggle_performance,
                  bg=PANEL2, fg=ORANGE, activebackground=ORANGE, activeforeground=BG,
                  relief="flat", padx=14, font=("DejaVu Sans", 10, "bold")).pack(side="right", padx=12, pady=8)
        tk.Label(self.taskbar, text="F12  وضع المطوّر", bg=PANEL, fg=MUTED,
                 font=("DejaVu Sans", 9)).pack(side="right", padx=8)

    def set_page(self, index: int):
        if not hasattr(self, "cards"): return
        self.page = index % 4
        for child in self.cards.winfo_children(): child.destroy()
        pages = [
            ("مساحة العمل", [
                ("▤", "مدير الملفات", "استعراض ثنائي للملفات", "files"),
                ("⚙", "الإعدادات", "التحكم الموحد بالنظام", "settings"),
                ("✎", "الملاحظات", "محرر نصوص سريع", "code"),
                ("⌕", "بحث الملفات", "اعثر على ملفاتك داخل مجلد المنزل", "search"),]),
            ("مختبر التطوير", [
                (">_", "ISO-Terminal", "أربع جلسات أوامر في نافذة واحدة", "terminal"),
                ("{ }", "ISO-Code", "محرر خفيف للملفات البرمجية", "code"),
                ("▦", "ISO-Pkg", "عرض معلومات الحزم المثبتة", "packages"),
                ("◉", "ISO-Hub", "فحص توفر Docker أو Podman", "containers"),
                ("▣", "ISO-VM", "فحص توفر QEMU للآلات الافتراضية", "vm"),
                ("⌁", "مراقب النظام", "المعالج والذاكرة ووقت التشغيل", "monitor"),]),
            ("الترفيه", [
                ("▶", "مشغل الوسائط", "فتح ملف صوت أو فيديو بمشغلك المثبت", "media"),
                ("◎", "الويب", "فتح المتصفح الافتراضي إن كان مثبتًا", "browser"),
                ("▤", "الملفات الحديثة", "استعرض مجلد التنزيلات", "downloads"),]),
            ("مساحتك الشخصية", [
                ("♙", "ملف المستخدم", "فتح مجلد المنزل", "home"),
                ("◈", "الخصوصية", "سياسة محلية بلا تحليلات عن بُعد", "privacy"),
                ("⟲", "نقاط الاستعادة", "التحقق من توفر أدوات اللقطات", "snapshots"),
                ("ℹ", "حول ISO-X", "معلومات النسخة ومطوريها", "about"),]),
        ]
        title, cards = pages[self.page]
        self.page_title.configure(text=title)
        for i, button in enumerate(self.page_buttons):
            button.configure(fg=CYAN if i == self.page else MUTED, bg=PANEL2 if i == self.page else PANEL)
        columns = 3
        for c in range(columns): self.cards.grid_columnconfigure(c, weight=1, uniform="card")
        for idx, (icon, name, desc, key) in enumerate(cards):
            frame = tk.Frame(self.cards, bg=PANEL, highlightbackground="#28283A", highlightthickness=1)
            row, col = divmod(idx, columns)
            frame.grid(row=row, column=col, sticky="nsew", padx=7, pady=7, ipadx=6, ipady=8)
            self.cards.grid_rowconfigure(row, weight=1, uniform="cardrow")
            tk.Label(frame, text=icon, bg=PANEL, fg=CYAN, font=("DejaVu Sans", 24, "bold")).pack(anchor="e", padx=16, pady=(12,4))
            tk.Label(frame, text=name, bg=PANEL, fg=WHITE, font=("DejaVu Sans", 12, "bold"), anchor="e").pack(fill="x", padx=16, pady=4)
            tk.Label(frame, text=desc, bg=PANEL, fg=MUTED, font=("DejaVu Sans", 9), anchor="e", justify="right", wraplength=230).pack(fill="x", padx=16, pady=(0,10))
            tk.Button(frame, text="فتح  ↗", command=lambda k=key: self.launch(k), bg=PANEL2, fg=CYAN,
                      activebackground=PURPLE, activeforeground=WHITE, relief="flat", padx=12, pady=5,
                      font=("DejaVu Sans", 9)).pack(anchor="e", padx=14, pady=(0,12))

    def launch(self, app):
        if app == "files": self.open_file_manager(HOME)
        elif app == "terminal": self.open_terminal()
        elif app == "code": self.open_editor()
        elif app == "settings": self.open_settings()
        elif app == "packages": self.open_packages()
        elif app == "containers": self.show_runtime("الحاويات", "Docker/Podman ليست مضمّنة تلقائيًا حتى يبقى النظام خفيفًا.", ["docker", "podman"])
        elif app == "vm": self.show_runtime("ISO-VM", "تشغيل Windows الافتراضي يحتاج تثبيت QEMU/KVM وصورة نظام مرخّصة منفصلة.", ["qemu-system-x86_64", "qemu-system-aarch64"])
        elif app == "monitor": self.open_dev_mode()
        elif app == "search": self.open_search()
        elif app == "media":
            path = filedialog.askopenfilename(title="اختر ملف وسائط")
            if path: self.open_path(Path(path))
        elif app == "browser": webbrowser.open("https://example.com")
        elif app == "downloads": self.open_file_manager(HOME / "Downloads")
        elif app == "home": self.open_file_manager(HOME)
        elif app == "privacy": self.show_info("الخصوصية", "لا يحتوي هذا النموذج على إرسال تحليلات عن بُعد. البيانات المحلية المساعدة مخزنة في ~/.local/share/iso-x/iso-x.db. هذا لا يغني عن مراجعة خدمات النظام والحزم الموجودة في صورة ISO الفعلية.")
        elif app == "snapshots": self.show_runtime("نقاط الاستعادة", "ميزة الاستعادة الآمنة غير مفعّلة في النموذج. لا يتم ادعاء إنشاء أو استعادة لقطة غير موجودة.", ["snapper", "btrfs"])
        elif app == "about": self.show_info("حول ISO-X", f"ISO-X — نموذج أولي مبني على Linux\nالمطور: {DEVELOPER}\nإصدار النموذج: 0.1.0\nلا يوجد ادعاء بأن متطلبات الأداء الصارمة قد تم إثباتها.")

    def refresh_status(self):
        stats = resource_stats()
        self.status.configure(text=f"RAM متاحة {stats['ram_available']}  •  الأنوية {stats['cores']}  •  {stats['uptime']}")
        self.root.after(5000, self.refresh_status)

    def _toplevel(self, title, size="760x520"):
        win = tk.Toplevel(self.root)
        win.title(f"{title} — ISO-X")
        win.geometry(size)
        win.configure(bg=BG)
        win.transient(self.root)
        return win

    def show_info(self, title, text):
        win=self._toplevel(title, "600x300")
        tk.Label(win, text=title, bg=BG, fg=CYAN, font=("DejaVu Sans",16,"bold")).pack(anchor="e", padx=18,pady=16)
        tk.Message(win, text=text, bg=PANEL, fg=WHITE, width=540, font=("DejaVu Sans",11), padx=12,pady=12).pack(fill="both", expand=True,padx=18,pady=(0,18))

    def show_runtime(self, title, description, binaries):
        results = [f"{bin_name}: {'متوفر' if command_exists(bin_name) else 'غير مثبت'}" for bin_name in binaries]
        self.show_info(title, description + "\n\n" + "\n".join(results) + "\n\nلا يتم تنزيل أو تثبيت أي شيء تلقائيًا.")

    def open_search(self):
        win=self._toplevel("البحث العام", "670x470")
        tk.Label(win,text="ابحث عن تطبيق أو إعداد أو ملف ضمن مجلد المستخدم",bg=BG,fg=WHITE,font=("DejaVu Sans",12)).pack(anchor="e",padx=16,pady=(16,8))
        var=tk.StringVar(); entry=tk.Entry(win,textvariable=var,bg=PANEL2,fg=WHITE,insertbackground=CYAN,font=("DejaVu Sans",12),relief="flat")
        entry.pack(fill="x",padx=16,ipady=8); entry.focus_set()
        results=tk.Listbox(win,bg=PANEL,fg=WHITE,selectbackground=PURPLE,relief="flat",font=("DejaVu Sans",10))
        results.pack(fill="both",expand=True,padx=16,pady=12)
        actions=[("ISO-Terminal", "terminal"),("ISO-Code", "code"),("ISO-FM", "files"),("ISO-Control", "settings"),("ISO-Pkg", "packages"),("مراقب النظام", "monitor")]
        current=[]
        def search(*_):
            q=var.get().strip().lower(); results.delete(0,"end"); current.clear()
            if not q: return
            for label,key in actions:
                if q in label.lower() or q in key.lower(): current.append((label,key,None)); results.insert("end",f"تطبيق: {label}")
            for directory in [HOME, HOME / "Documents", HOME / "Downloads", HOME / "Desktop"]:
                if not directory.exists(): continue
                count=0
                try:
                    for base, dirs, files in os.walk(directory):
                        dirs[:] = [d for d in dirs if d not in {".cache", ".git", "node_modules", "venv", ".venv"}]
                        for name in files:
                            if q in name.lower():
                                p=Path(base)/name; current.append((name,"file",p)); results.insert("end",f"ملف: {p}")
                                count+=1
                                if count>=40: break
                        if count>=40: break
                except (PermissionError, OSError): pass
            if not current: results.insert("end","لا توجد نتائج ضمن النطاق المحدد.")
        var.trace_add("write",search)
        def activate(_event=None):
            sel=results.curselection()
            if not sel: return
            item=current[sel[0]]
            win.destroy()
            if item[1]=="file": self.open_path(item[2])
            else: self.launch(item[1])
        results.bind("<Double-Button-1>",activate); entry.bind("<Return>",lambda _e: activate())

    def open_settings(self):
        win=self._toplevel("ISO-Control", "700x540")
        tk.Label(win,text="ISO-Control | الإعدادات الموحدة",bg=BG,fg=CYAN,font=("DejaVu Sans",16,"bold")).pack(anchor="e",padx=18,pady=16)
        stats=resource_stats()
        for label,value in [("المعالج/الأنوية",stats["cores"]),("إجمالي الذاكرة",stats["ram_total"]),("الذاكرة المتاحة",stats["ram_available"]),("النواة",stats["kernel"]),("نظام التشغيل المضيف",stats["system"])]:
            row=tk.Frame(win,bg=PANEL); row.pack(fill="x",padx=18,pady=4)
            tk.Label(row,text=label,bg=PANEL,fg=MUTED,font=("DejaVu Sans",10)).pack(side="right",padx=12,pady=10)
            tk.Label(row,text=value,bg=PANEL,fg=WHITE,font=("DejaVu Sans",10,"bold")).pack(side="left",padx=12,pady=10)
        tk.Button(win,text="تبديل وضع الأداء الأقصى",command=self.toggle_performance,bg=PURPLE,fg=WHITE,relief="flat",padx=16,pady=10).pack(anchor="e",padx=18,pady=14)
        tk.Label(win,text="الوضع يخفّض مؤثرات واجهة ISO-X فقط. لا يغيّر إعدادات النواة أو الطاقة دون موافقة.",bg=BG,fg=MUTED,wraplength=620,justify="right").pack(fill="x",padx=18)
        tk.Label(win,text="موضع شريط المهام في هذا النموذج: أسفل الشاشة. النقل لأعلى/الجانبين مخطط له.",bg=BG,fg=MUTED,wraplength=620,justify="right").pack(fill="x",padx=18,pady=6)

    def toggle_performance(self):
        self.performance_mode = not self.performance_mode
        self.animations_enabled = not self.performance_mode
        if hasattr(self,"status"):
            self.status.configure(fg=ORANGE if self.performance_mode else GREEN)
        message = "تم تفعيل وضع الأداء المحلي وتقليل الرسوم المتحركة في الواجهة." if self.performance_mode else "تمت إعادة الرسوم المتحركة في الواجهة."
        if hasattr(self,"shell"):
            self.show_info("وضع الأداء", message + "\nهذا ليس تحسينًا سحريًا للمعالج ولا يضمن رقم RAM معينًا.")

    def open_dev_mode(self):
        win=self._toplevel("Dev Mode", "760x520")
        tk.Label(win,text="F12 | مراقبة النظام محليًا",bg=BG,fg=CYAN,font=("DejaVu Sans",16,"bold")).pack(anchor="e",padx=16,pady=12)
        area=tk.Text(win,bg=PANEL,fg=WHITE,insertbackground=CYAN,relief="flat",font=("DejaVu Sans Mono",10),wrap="word")
        area.pack(fill="both",expand=True,padx=16,pady=(0,10))
        bar=tk.Frame(win,bg=BG); bar.pack(fill="x",padx=16,pady=(0,14))
        tk.Button(bar,text="تسجيل قياس محلي",command=lambda:self.record_metrics(area),bg=PANEL2,fg=CYAN,relief="flat",padx=12,pady=7).pack(side="right")
        tk.Button(bar,text="تحديث الآن",command=lambda: update(),bg=PANEL2,fg=WHITE,relief="flat",padx=12,pady=7).pack(side="right",padx=8)
        def update():
            data=resource_stats()
            output=("ISO-X / Dev Mode\n" + "="*42 + "\n" + "\n".join(f"{k}: {v}" for k,v in data.items()) + "\n\n" +
                    f"Python: {sys.version.split()[0]}\nPID: {os.getpid()}\nقاعدة البيانات: {DB_PATH}\n" +
                    f"Docker: {'متوفر' if command_exists('docker') else 'غير مثبت'}\n" +
                    f"QEMU: {'متوفر' if command_exists('qemu-system-x86_64') else 'غير مثبت'}\n\n" +
                    "التسجيل لا يعمل في الخلفية. استخدم زر القياس لحفظ قراءة محلية بطلبك.")
            area.configure(state="normal"); area.delete("1.0","end"); area.insert("1.0",output); area.configure(state="disabled")
        update()
        def loop():
            if win.winfo_exists(): update(); win.after(3000,loop)
        win.after(3000,loop)

    def record_metrics(self, area):
        data=resource_stats()
        try:
            self.store.db.execute("INSERT INTO perf_logs(metric_name,metric_value,unit,source) VALUES(?,?,?,?)",
                                  ("ram_available", data["ram_available"], "display-string", "user-triggered"))
            self.store.db.commit()
            messagebox.showinfo("ISO-X", "تم تسجيل قراءة محلية واحدة في قاعدة البيانات.", parent=area.winfo_toplevel())
        except sqlite3.Error as exc:
            messagebox.showerror("ISO-X", f"تعذّر تسجيل القراءة: {exc}", parent=area.winfo_toplevel())

    def open_terminal(self):
        win=self._toplevel("ISO-Terminal", "900x610")
        tk.Label(win,text="ISO-Terminal | أربع جلسات أوامر",bg=BG,fg=CYAN,font=("DejaVu Sans",15,"bold")).pack(anchor="e",padx=14,pady=10)
        book=ttk.Notebook(win); book.pack(fill="both",expand=True,padx=12,pady=(0,12))
        for index in range(4):
            tab=tk.Frame(book,bg=BG); book.add(tab,text=f"جلسة {index+1}")
            output=tk.Text(tab,bg="#070910",fg="#C8F7F5",insertbackground=CYAN,relief="flat",font=("DejaVu Sans Mono",10),wrap="word")
            output.pack(fill="both",expand=True,pady=(0,8))
            output.insert("end", f"ISO-X session {index+1}\nالأوامر تعمل بصلاحيات المستخدم الحالي فقط.\n$ ")
            entry=tk.Entry(tab,bg=PANEL2,fg=WHITE,insertbackground=CYAN,relief="flat",font=("DejaVu Sans Mono",10))
            entry.pack(fill="x",ipady=8)
            def execute(_event=None, ent=entry, out=output):
                cmd=ent.get().strip()
                if not cmd:return
                ent.delete(0,"end"); out.configure(state="normal"); out.insert("end",cmd+"\n")
                try:
                    result=subprocess.run(cmd,shell=True,cwd=str(HOME),capture_output=True,text=True,timeout=15)
                    out.insert("end",result.stdout[-20000:])
                    if result.stderr: out.insert("end",result.stderr[-8000:])
                    out.insert("end",f"\n[exit {result.returncode}]\n$ ")
                except subprocess.TimeoutExpired:
                    out.insert("end","\nانتهت مهلة الأمر بعد 15 ثانية. استخدم طرفية النظام للمهام التفاعلية.\n$ ")
                except Exception as exc: out.insert("end",f"\nخطأ: {exc}\n$ ")
                out.see("end")
            entry.bind("<Return>",execute)
        tk.Label(win,text="ملاحظة: هذه جلسات أوامر مبسطة وليست أربعة PTY تفاعلية كاملة؛ شغّل xterm للبرامج التفاعلية.",bg=BG,fg=MUTED,font=("DejaVu Sans",9)).pack(anchor="e",padx=14,pady=(0,10))

    def open_editor(self, initial: Path | None = None):
        win=self._toplevel("ISO-Code", "900x650")
        toolbar=tk.Frame(win,bg=PANEL); toolbar.pack(fill="x")
        path_var=tk.StringVar(value=str(initial) if initial else "ملف جديد")
        tk.Label(toolbar,textvariable=path_var,bg=PANEL,fg=MUTED,font=("DejaVu Sans",9)).pack(side="right",padx=10,pady=10)
        editor=tk.Text(win,bg="#090B12",fg=WHITE,insertbackground=CYAN,undo=True,wrap="none",font=("DejaVu Sans Mono",11),relief="flat")
        editor.pack(fill="both",expand=True,padx=10,pady=10)
        current=[initial]
        if initial and initial.is_file(): editor.insert("1.0",read_text(initial))
        def open_file():
            name=filedialog.askopenfilename(title="فتح ملف",parent=win)
            if name:
                p=Path(name); current[0]=p; path_var.set(str(p)); editor.delete("1.0","end"); editor.insert("1.0",read_text(p))
        def save_file():
            p=current[0]
            if not p:
                name=filedialog.asksaveasfilename(title="حفظ ملف",parent=win)
                if not name:return
                p=Path(name); current[0]=p; path_var.set(str(p))
            try: p.write_text(editor.get("1.0","end-1c"),encoding="utf-8"); messagebox.showinfo("ISO-Code","تم حفظ الملف.",parent=win)
            except Exception as exc: messagebox.showerror("ISO-Code",str(exc),parent=win)
        tk.Button(toolbar,text="فتح",command=open_file,bg=PANEL2,fg=CYAN,relief="flat",padx=14).pack(side="left",padx=4,pady=6)
        tk.Button(toolbar,text="حفظ",command=save_file,bg=PURPLE,fg=WHITE,relief="flat",padx=14).pack(side="left",padx=4,pady=6)
        tk.Label(win,text="محرر أساسي: لا يحتوي النموذج بعد على IntelliSense أو نظام إضافات أو دعم لغات مدمج كامل.",bg=BG,fg=MUTED,font=("DejaVu Sans",9)).pack(anchor="e",padx=12,pady=(0,8))

    def open_file_manager(self, start: Path):
        win=self._toplevel("ISO-FM", "980x630")
        tk.Label(win,text="ISO-FM | مدير ملفات ثنائي اللوحين",bg=BG,fg=CYAN,font=("DejaVu Sans",15,"bold")).pack(anchor="e",padx=14,pady=10)
        content=tk.Frame(win,bg=BG); content.pack(fill="both",expand=True,padx=12,pady=(0,8))
        panes=[]
        for side in range(2):
            pane=tk.Frame(content,bg=PANEL); pane.pack(side="left",fill="both",expand=True,padx=5)
            pathvar=tk.StringVar(value=str(start if start.exists() else HOME))
            tk.Entry(pane,textvariable=pathvar,bg=PANEL2,fg=WHITE,insertbackground=CYAN,relief="flat").pack(fill="x",padx=7,pady=7,ipady=6)
            listing=tk.Listbox(pane,bg=PANEL,fg=WHITE,selectbackground=PURPLE,relief="flat",font=("DejaVu Sans",10))
            listing.pack(fill="both",expand=True,padx=7,pady=(0,7))
            panes.append({"path":pathvar,"list":listing,"selected":None})
        status=tk.Label(win,text="انقر مرتين على مجلد للدخول أو على ملف لعرضه.",bg=BG,fg=MUTED,font=("DejaVu Sans",9)); status.pack(anchor="e",padx=14,pady=(0,10))
        def refresh(pane):
            base=Path(pane["path"].get()).expanduser()
            listing=pane["list"]; listing.delete(0,"end")
            try:
                if base.parent != base: listing.insert("end","📁  ..")
                for entry in sorted(base.iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold())):
                    prefix="📁 " if entry.is_dir() else "   "
                    listing.insert("end",prefix+entry.name)
            except Exception as exc: status.configure(text=f"تعذر فتح المجلد: {exc}")
        def activate(pane, _event=None):
            sel=pane["list"].curselection()
            if not sel:return
            name=pane["list"].get(sel[0]).replace("📁  ","").replace("📁 ","").strip()
            p=Path(pane["path"].get()).expanduser()
            target=p.parent if name==".." else p/name
            if target.is_dir(): pane["path"].set(str(target)); refresh(pane)
            elif target.is_file(): self.open_path(target)
        for pane in panes:
            pane["list"].bind("<Double-Button-1>",lambda ev,p=pane:activate(p,ev)); refresh(pane)
        actions=tk.Frame(win,bg=BG); actions.pack(fill="x",padx=12,pady=(0,12))
        tk.Button(actions,text="الصفحة الرئيسية",command=lambda:(panes[0]["path"].set(str(HOME)),refresh(panes[0])),bg=PANEL2,fg=CYAN,relief="flat",padx=12).pack(side="right",padx=4)
        tk.Button(actions,text="تحديث",command=lambda:[refresh(p) for p in panes],bg=PANEL2,fg=WHITE,relief="flat",padx=12).pack(side="right",padx=4)
        tk.Button(actions,text="معاينة الملف المحدد",command=lambda: [self.open_path(Path(p["path"].get())/p["list"].get(p["list"].curselection()[0]).strip().removeprefix("📁").strip()) for p in panes if p["list"].curselection()],bg=PURPLE,fg=WHITE,relief="flat",padx=12).pack(side="left",padx=4)

    def open_path(self, path: Path):
        try: path=path.expanduser().resolve()
        except Exception: pass
        if path.is_dir(): self.open_file_manager(path); return
        if not path.exists(): self.show_info("معاينة الملف", "الملف غير موجود."); return
        try:
            if path.suffix.lower() in {".txt",".py",".md",".json",".html",".css",".js",".sql",".sh",".yaml",".yml",".toml",".ini",".log",".xml",".csv"}:
                self.open_editor(path)
            elif command_exists("xdg-open"):
                subprocess.Popen(["xdg-open",str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            else:
                self.show_info("معاينة الملف",f"{path}\n\n{path.stat().st_size} bytes\nلا يوجد عارض مناسب مُكتشف لهذا النوع.")
        except Exception as exc: self.show_info("معاينة الملف",f"{path}\n{exc}")

    def open_packages(self):
        win=self._toplevel("ISO-Pkg", "760x540")
        tk.Label(win,text="ISO-Pkg | مدير الحزم",bg=BG,fg=CYAN,font=("DejaVu Sans",16,"bold")).pack(anchor="e",padx=16,pady=14)
        description="يعتمد بناء ISO-X الحالي على مدير حزم Debian APT. لا توجد تنزيلات أو تثبيتات صامتة من هذه الواجهة."
        tk.Label(win,text=description,bg=BG,fg=WHITE,wraplength=700,justify="right").pack(fill="x",padx=16,pady=6)
        info=tk.Text(win,bg=PANEL,fg=WHITE,relief="flat",font=("DejaVu Sans Mono",10),height=13)
        info.pack(fill="both",expand=True,padx=16,pady=12)
        if command_exists("dpkg-query"):
            try:
                r=subprocess.run(["dpkg-query","-W","-f=${binary:Package}\t${Version}\n"],capture_output=True,text=True,timeout=8)
                lines=r.stdout.splitlines(); info.insert("end",f"عدد الحزم المثبتة: {len(lines)}\n\n"+"\n".join(lines[:250]))
                if len(lines)>250: info.insert("end",f"\n… تمت معاينة أول 250 حزمة من {len(lines)}.")
            except Exception as exc: info.insert("end",str(exc))
        else: info.insert("end","dpkg-query غير متوفر في هذا النظام.")
        info.configure(state="disabled")
        tk.Label(win,text="للتثبيت استخدم APT يدويًا من الطرفية وراجع اسم الحزمة قبل التنفيذ.",bg=BG,fg=ORANGE).pack(anchor="e",padx=16,pady=(0,12))


def main():
    root=tk.Tk()
    try: ttk.Style().theme_use("clam")
    except tk.TclError: pass
    app=ISOX(root)
    root.mainloop()

if __name__ == "__main__":
    main()
