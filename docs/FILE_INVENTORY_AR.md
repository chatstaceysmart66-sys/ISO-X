# جرد ملفات ISO-X

## الحالة الابتدائية

- الفرع: `fix/isox-build-and-runtime`
- HEAD: `caf58594bea006c983d45751f113dfe6ed8b89eb`
- `git status --short --branch`: شجرة نظيفة عند بدء الفحص.
- جدول التغطية بعد ملحق الاستئناف يقارن المسارات الحالية مباشرةً مع `git ls-files`.
- جرى جرد الملفات المتتبعة بـ `git ls-files`، وقياس الأسطر/البايتات بـ `wc -lc` وفحص النوع بـ `file`. لم تظهر ملفات غير متتبعة في الحالة الابتدائية.
- جرد بداية المرحلة صفر: 92 ملفاً متتبعاً، 87 ملفاً نصياً و5 صور PNG ثنائية.
- بعد إضافة ملفات CI والتقارير في الالتزام السابق، أصبح الجرد الحالي 104 ملفات: 99 ملفاً نصياً و5 صور PNG ثنائية. عُرض نوع الصور وأبعادها وحجمها بدلاً من عدد أسطر غير ذي معنى.

## الدفعة 1: إعدادات البناء، الحزم، hooks

| المسار | الحجم/الأسطر | الوظيفة والاعتماديات | المستدعي / مكان ISO | الاختبار / الملاحظات |
|---|---:|---|---|---|
| `auto/config` | 1926 بايت / 43 سطراً (نسخة العمل الحالية) | يضبط live-build لـ Debian Trixie amd64 وصورة iso-hybrid ومحملات BIOS/UEFI؛ يضيف معاملات تشخيص serial/VGA وnonce عند ISOX_CI_BOOT=1 فقط. | يستدعيه `scripts/build-iso.sh`; لا يدخل ISO كملف. | اختبارات المصدر وbash syntax ناجحة؛ لا يثبت المصدر وحده معاملات ISO مبنية. |
| `build.sh` | 151 بايت / 4 أسطر | نقطة دخول رفيعة تحدد جذر المشروع ثم تنفذ `scripts/build-iso.sh` مع تمرير الوسائط. يعتمد على Bash. | يُشغله المستخدم؛ لا يدخل ISO. | لا يوجد اختبار تنفيذي مباشر حتى الآن؛ تغطيه اختبارات عقود المصدر جزئياً. |
| `config/package-lists/iso-x.list.chroot` | 2747 بايت / 154 سطراً | قائمة حزم chroot تشمل النظام الرسومي، الشبكة، الصوت، الطباعة، firmware، تطبيقات وبيئة المكتب. | يقرأها live-build أثناء البناء؛ الحزم الناتجة تثبت في ISO. | `tests/test_source_config.py`؛ لا تثبت وجود كل الحزم في Trixie ولا اختبار التطبيق بيانياً. |
| `config/hooks/live/0050-isox-locales.hook.chroot` | 367 بايت / 11 سطراً | يولّد ar_IQ/ar_SA/en_US ويضبط locale الافتراضي ar_IQ. يعتمد على locale-gen/update-locale عند توفرهما. | ينفذه live-build في chroot؛ تأثيره إعداد داخل ISO. | لا اختبار تكاملي معروف؛ يحوي حراسة لأوامر locale. |
| `config/hooks/live/0100-isox-watermark.hook.chroot` | 2701 بايت / 47 سطراً | يتطلب مفتاحاً وشهادة staged، يبني ويوقّع وحدة watermark لكل kernel ذي build dir، يثبتها، يوقّع detached signature ويعيد بناء initramfs؛ يحذف مواد المفتاح في النهاية. يعتمد على kernel headers/build، make، openssl، depmod، update-initramfs. | `scripts/build-iso.sh` لا ينسخه إلا مع `ISOX_ENABLE_WATERMARK=1`؛ عندها يدخل ضمن hooks. | اختبارات watermark/secureboot جزئية؛ مسار watermark غير منفذ في ISO فعلية. عولج في مراجعة 2026-10-20 غياب تعريف `CERT_IN` تحت `set -u`؛ أضيف ربطه بـ`ISOX_RELEASE_CERT` واختبار عقد، ولم يُختبر بناء watermark فعلي بمفتاح/شهادة. |
| `config/hooks/live/0200-isox-plymouth.hook.chroot` | 597 بايت / 14 سطراً | ينسخ theme/assets إلى `/usr/share/plymouth/themes/isox` ويختاره ثم يحدث initramfs. يعتمد على assets المضمنة وPlymouth/update-initramfs. | hook build؛ ينسخ الثيم إلى ISO. | لا اختبار إقلاع مرئي؛ التحقق النصي وحده لا يثبت عرض Plymouth. |
| `config/hooks/live/0300-isox-services.hook.chroot` | 746 بايت / 25 سطراً | يكتب إعداد NetworkManager وLightDM greeter، ويفعّل NetworkManager وBluetooth، وcups.socket اختيارياً. | hook build؛ يكتب إلى `/etc` داخل ISO. | لا اختبار جلسة؛ فشل enable cups مخفي عمداً. |
| `config/hooks/live/0400-isox-firefox-defaults.hook.chroot` | 913 بايت / 22 سطراً | يضيف Firefox ESR homepage محلية `file:///usr/share/iso-x/start.html` كإعداد افتراضي. يدعم `ISOX_HOOK_ROOT` للاختبار. | hook build؛ يكتب إعداد Firefox داخل ISO. | لا اختبار تشغيل متصفح. |

### ترتيب hooks

بحسب الأسماء الرقمية التي تمت قراءتها: `0050-isox-locales` ثم `0100-isox-watermark` ثم `0200-isox-plymouth` ثم `0300-isox-services` ثم `0400-isox-firefox-defaults`. هذا ترتيب أسماء الملفات؛ لم يُثبت بعد ترتيب تنفيذ live-build الفعلي من سجل بناء.

## الدفعة 2: نقطة البناء والسكربتات

| المسار | الحجم/الأسطر | الوظيفة والاعتماديات | المستدعي / مكان ISO | الاختبار / الملاحظات |
|---|---:|---|---|---|
| `scripts/build-iso.sh` | 24252 بايت / 435 سطراً (نسخة العمل الحالية) | يفحص مضيف Trixie وamd64 والذاكرة والمساحة والأدوات، يجهز staging، ينسخ الملفات وينفذ `lb build` ثم يفحص ISO/SHA؛ يضيف readiness probe فقط عند `ISOX_CI_BOOT=1`، ويكتب sidecar باسم ISO نسبي قابل للنقل. | مستدعى من `build.sh`؛ ملفات probe تُنسخ إلى staging فقط في نسخة CI. | اختبارات المصدر/العقود ناجحة؛ عُرّف `CERT_IN` من `ISOX_RELEASE_CERT` في مراجعة 2026-10-20؛ لم يُشغّل build حقيقي أو watermark build. |
| `scripts/install-build-deps.sh` | 1977 بايت / 34 سطراً | يثبت أدوات البناء/الاختبار على Debian Trixie ويفحص وجود مجموعة أوامر. يعتمد على apt/sudo. | تشغيل يدوي على مضيف البناء؛ لا يدخل ISO. | لا اختبار تثبيت؛ يطلب من ضمن أدواته xmllint وsystemd-analyze وdesktop-file-validate، ويفحص grub-mkrescue. |
| `scripts/apply-windows-look.sh` | 3085 بايت / 85 سطراً | ينشئ تفضيلات GTK داكنة، PCManFM wallpaper profile ومجلدات XDG عربية وتفضيلات home. يعتمد على bash وrealpath. | يستدعيه `build-iso.sh` على `etc/skel`؛ الإعدادات تُنسخ إلى ISO. | تغطية مصدرية غير مباشرة. `wallpaper_mode=stretch` السطر 49 قد يشوه نسب العرض. |
| `scripts/collect-performance.sh` | 1037 بايت / 27 سطراً | يجمع معلومات الأداء والنظام وzram وSecure Boot إلى `performance.txt`. يعتمد على systemd-analyze, free, top, ps, zramctl, mokutil. | يدوي؛ لا يُنسخ بواسطة بناء ISO حسب قائمة نسخ `build-iso.sh`. | لا اختبار معروف؛ بعض أوامر الفحص اختيارية وتُخفى أخطاؤها بـ `|| true`. |
| `scripts/encode-watermark.py` | 777 بايت / 16 سطراً | يحول نسبة المطور إلى مصفوفة C XOR obfuscated؛ ليس تشفيراً. يعتمد على Python وملف وجهة. | يستدعيه البناء عند watermark=1؛ الإخراج تحت includes.chroot لملف kernel. | اختبارات watermark جزئية؛ الافتراضي يكتب في شجرة المصدر `kernel/.../watermark_bytes.h` إن لم تحدد متغير البيئة، لذا التشغيل الاختباري يجب أن يوجهه للخارج. |
| `scripts/generate-dev-signing-key.sh` | 863 بايت / 19 سطراً | ينشئ مفتاح RSA-3072 وشهادة self-signed بلا passphrase في `$HOME/.local/share/isox-signing` افتراضياً. يعتمد على OpenSSL. | تشغيل يدوي؛ لا يدخل ISO بذاته. | `tests/test_secureboot_validation.sh` لا يثبت أمان المفتاح. المفتاح غير محمي بكلمة مرور، والشهادة لغرض توقيع عام وليست دليلاً على Secure Boot. |
| `scripts/isox-preload.py` | 2623 بايت / 64 سطراً | يقرأ إعداد opt-in وإحصاءات استعمال SQLite ثم يقرأ صفحات ثنائية من allowlist (`netsurf`, `xterm`, `xdg-open`) عند توفر الذاكرة/الخمول. يعتمد على schema، SQLite، procfs. | يثبت إلى `/usr/local/bin/isox-preload`؛ timer خدمة user يطلب تشغيله. | لا اختبار مباشر واضح. المتصفح الفعلي في الحزم Firefox ESR وليس Netsurf، وقد لا توجد الحزمة `netsurf` لأن قائمة الحزم تحتوي `netsurf-gtk`. |
| `scripts/isox-run.py` | 2565 بايت / 61 سطراً | نافذة GTK لتشغيل أمر بعد shlex والتحقق من وجود الملف التنفيذي ثم `Popen(argv)` دون shell. يعتمد على GTK3/PyGObject. | يثبت باسم `/usr/local/bin/isox-run` ويظهر كـ desktop entry. | لا اختبار GUI؛ الأمر يُنفذ بصلاحيات المستخدم الحالي. |
| `scripts/isox-snap-window.sh` | 757 بايت / 13 سطراً | يحدد الشاشة النشطة عبر xrandr ثم يغير موضع وحجم النافذة بـ wmctrl إلى نصف الشاشة. | يثبت داخل ISO باسم `isox-snap-window`، لكن عدم وجود binding واضح لم يُحسم بعد. | يعتمد على `xrandr`, `wmctrl`; package list بها wmctrl وليس x11-xserver-utils التي توفر xrandr. يستخدم ارتفاعاً ثابتاً 42px (السطر 8). |
| `scripts/isox-speedtest` | 3962 بايت / 114 سطراً | يقيس ping وتنزيل ملف Release صغير، مع واجهة GTK اختيارية وخيط عامل. يعتمد على ping/curl وGTK3. | يثبت إلى `/usr/local/bin/isox-speedtest`. | لا اختبار شبكة فعلية معروف؛ النتيجة عينة اتصال لا قياس سرعة ISP كاملة. |
| `scripts/isox-zram-setup` | 810 بايت / 18 سطراً | ينشئ zram بحجم نصف RAM وخوارزمية zstd ويفعل swap priority 100 ثم يضبط swappiness=10. يعتمد على zramctl/modprobe/mkswap/swapon/sysctl. | يستدعيه `systemd/isox-zram.service` داخل ISO. | لا اختبار على جهاز حي؛ لا يثبت حزمة zstd هنا. |
| `scripts/record-demo.sh` | 883 بايت / 12 سطراً | يسجل شاشة X11 عبر ffmpeg/x11grab إلى mp4. يعتمد على ffmpeg وxdpyinfo وDISPLAY. | تشغيل يدوي؛ لا يظهر ضمن قائمة النسخ إلى ISO. | لا اختبار ملف فيديو؛ ffmpeg غير موجود في package-list المقروءة. |
| `scripts/secure-vault.py` | 9950 بايت / 201 سطراً | ينشئ أرشيفات tar مشفرة بـ OpenSSL AES-256-CBC/PBKDF2 مع HMAC، ويفكها بعد التحقق، ويمنع path traversal وأنواع الملفات غير العادية. | `secure-vault.sh` يشغله؛ البناء ينسخه إلى `/usr/share/iso-x/secure-vault.py`. | `tests/test_secure_vault.py`. مجلدات مؤقتة في parent الوجهة وليس بالضرورة `/tmp`؛ كلمة المرور الفارغة مرفوضة لكن لا حد أدنى للطول. |
| `scripts/secure-vault.sh` | 266 بايت / 7 أسطر | wrapper يمرر المعاملات إلى نسخة ISO أو نسخة المصدر من secure-vault.py. | يثبت باسم `/usr/local/bin/isox-vault`. | لا اختبار wrapper مستقل؛ القائمة Openbox تحتاج فحص المعاملات التي تمررها. |
| `scripts/secureboot-enroll.sh` | 2133 بايت / 45 سطراً | يتحقق من تطابق مفتاح خاص وشهادة X.509 ولا يسجل MOK ولا يغير UEFI. يعتمد على OpenSSL وcmp. | تشغيل يدوي؛ لا يُنسخ من build script. | `tests/test_secureboot_validation.sh`; الاسم "enroll" مضلل جزئياً لكنه يصرح أنه validation-only. |
| `scripts/toggle-airplane.sh` | 1841 بايت / 35 سطراً | يبدل rfkill لجميع الأجهزة ويطلب pkexec عند عدم root ثم يتحقق من الحالة. يعتمد على rfkill وpkexec واختيارياً notify-send. | يثبت إلى `/usr/local/bin/isox-toggle-airplane` ويظهر desktop entry. | لا اختبار عتاد؛ الأجهزة غير الموجودة تؤدي exit 3. |
| `scripts/write-usb.sh` | 4073 بايت / 54 سطراً | يتحقق من ISO وبصمتها وبنية xorriso، ثم يطلب القرص الكامل USB وتأكيد WIPE ويكتب بـ dd. يرفض persistence صراحة. | يثبت باسم `/usr/local/sbin/isox-write-usb`. | `tests/test_write_usb_validation.sh`; لا اختبار كتابة قرص فعلي أو virtual disk معلوم هنا. |

### آثار البناء المصرح بها بالمصدر

`build-iso.sh` ينشئ `BUILD_DIR` (افتراضياً `build-live`)، ويكتب إعداد live-build تحت `config/` داخله، وسجل بناء، ثم نسخة ISO وملف بصمة في جذر المشروع. ينشئ مجلدات عدة قبل معظم عمليات `install`، لكن يلزم اختبار contract تشغيل فعلي بأدوات وهمية لتأكيد كل مسار كتابة كما طلب البرومت. لا تُعرف حالة بناء حالي في الجذر لأن الحالة الابتدائية نظيفة.

## الدفعة 3: initramfs، kernel، Plymouth، systemd، التطبيقات والواجهة

| المسار | الحجم/الأسطر | الوظيفة والاعتماديات | المستدعي / مكان ISO | الاختبار / الملاحظات |
|---|---:|---|---|---|
| `initramfs/hooks/isox-watermark` | 1627 بايت / 24 سطراً | يضيف module وOpenSSL وsha256sum وملفات سياسة/توقيع إلى initramfs إذا اكتملت metadata؛ يتجاوز التحديثات المبكرة التي تسبق بناء module. | ينسخه البناء شرطياً عند `ISOX_ENABLE_WATERMARK=1` إلى initramfs-tools hooks. | `tests/test_watermark_integrity.sh` جزئي؛ الميزة اختيارية. |
| `initramfs/scripts/init-premount/isox-watermark-guard` | 1775 بايت / 42 سطراً | يتحقق من توقيع/hash module ثم يحاول modprobe، وفي كل فشل يرسل تحذيراً ويكمل الإقلاع. | ينسخه البناء شرطياً إلى initramfs-tools init-premount. | `tests/test_initramfs_watermark_guard.sh`؛ لا يثبت تحميل module على ISO فعلي. |
| `kernel/isox-watermark/Makefile` | 198 بايت / 9 أسطر | يبني module عبر kernel build tree مع `-Werror`. | hook عند watermark؛ source فقط حتى النسخ المشروط. | لا اختبار منفرد. |
| `kernel/isox-watermark/dkms.conf` | 221 بايت / 7 أسطر | تعريف DKMS لوحدة isox-watermark 0.3.1 مع AUTOINSTALL. | لا ينسخه `build-iso.sh` حسب قائمة النسخ؛ الاستخدام الفعلي غير معروف. | لا اختبار؛ يمكن أن يكون أثراً غير مستخدم. |
| `kernel/isox-watermark/isox_watermark.c` | 1184 بايت / 36 سطراً | module يعرض attribution في kernel log بعد فك XOR؛ يصرح أن هذا ليس حد أمان. | ينسخه البناء إلى `/usr/src/isox-watermark-0.3.1` شرطياً ثم hook يبنيه. | اختبارات watermark جزئية. |
| `kernel/isox-watermark/watermark_bytes.h` | 357 بايت / 2 سطر | بيانات C مشوشة XOR نصها نسبة المطور. | تضمين من C؛ لا ينسخه البناء صراحة، بل مولد watermark يصنع header داخل مجلد البناء. | ليس تشفيراً؛ الملف الحالي source header committed. |
| `plymouth/isox/isox.plymouth` | 237 بايت / 8 أسطر | تعريف Plymouth theme من نوع script ومسار script. | ينسخه البناء إلى assets ثم hook يضعه في theme directory. | لا اختبار بصري؛ لا يظهر تنفيذ message/password callback في الثيم. |
| `plymouth/isox/isox.script` | 582 بايت / 13 سطراً | خلفية سوداء وصورة ثابتة متمركزة وrefresh callback. | يُنسخ إلى theme عبر hook؛ يعتمد على plymouth script API وصورة PNG. | لا يعرض تقدم/رسائل برمجياً ولا توجد حركة. |
| `systemd/isox-preload.service` | 174 بايت / 7 أسطر | خدمة user oneshot لتشغيل isox-preload إذا وجد DB. | ينسخ إلى `/usr/lib/systemd/user`; timer المستخدم يفعّله. | لا اختبار تشغيل خدمة. |
| `systemd/isox-preload.timer` | 177 بايت / 11 سطراً | يبدأ بعد 8 دقائق ثم دورياً بعد 6 ساعات بعشوائية، WantedBy timers.target. | نسخ إلى user unit وإضافة symlink في `/etc/skel`. | مربوط بالحسابات الجديدة؛ الخدمة لا تُنفّذ إن لم DB، والبرنامج نفسه opt-in. |
| `systemd/isox-zram.service` | 303 بايت / 13 سطراً | oneshot system service قبل display manager لتشغيل zram setup ومثبتة بعد multi-user. | ينسخ إلى `/etc/systemd/system` ويمكّنها البناء symlink. | لا اختبار حي؛ نجاح الخدمة يعتمد على أدوات zram. |
| `app/iso_x_gtk.py` | 43045 بايت / 683 سطراً | واجهة GTK3 الأساسية: home، مدير ملفات ثنائي، editor، terminal VTE، browser launch، إعدادات، بحث، Dev Mode، preload/watermark status. يعتمد على GI وSQLite وschema والملفات التنفيذية. | ينسخه البناء إلى `/usr/share/iso-x/iso_x_gtk.py` ويطلقه `/usr/local/bin/iso-x` في autostart. | لا اختبار GUI؛ يحتوي بحثاً متزامناً مع GTK callback (threaded worker موجود)، وeditor يقرأ UTF-8 فقط ولا يدعم اختيار file chooser في الحقل الظاهر؛ أمر الأداء يبدل GTK animation للنافذة فقط. |
| `app/iso_x_shell.py` | 34830 بايت / 543 سطراً | نموذج Tkinter قديم بصفحات وتطبيقات توضيحية وعمليات ملفات وterminal مبسط. | لا يظهر في `build-iso.sh` كملف منسوخ ولا package-list لـ python3-tk؛ يبدو غير مستخدم في ISO من دليل النسخ الحالي. | لا اختبار؛ أربع جلسات shell تشغل `subprocess.run(..., shell=True)`، ومفاتيح 1-4 عامة؛ الإصدار المعروض 0.1.0. |
| `app/isox_appcenter.py` | 11112 بايت / 236 سطراً | مركز GTK لقائمة ثابتة من الحزم، يفحص dpkg-query ويستدعي pkexec apt-get update/install/remove وينشئ اختصارات سطح المكتب. | ينسخ إلى `/usr/share/iso-x/isox_appcenter.py`؛ يستدعى من Openbox menu وwelcome. | لا اختبار UI/apt؛ لا قفل عالمي لعمليات apt؛ ينشئ Exec ثابت من كتالوج بدلاً من قراءة desktop entry، وبعض التطبيقات مثبّتة أصلاً. |
| `app/isox_welcome.py` | 11814 بايت / 267 سطراً | نافذة ترحيب GTK تعرض system summary وأزرار تكتشف الأوامر المتاحة ثم تطلقها بأ argv. | يُنسخ إلى `/usr/share/iso-x/isox_welcome.py` ويُشغل من desktop/menu/autostart seed. | لا اختبار GUI؛ ACTIONS تتوقع `thunar`, `xfce4-settings-manager`, `debian-installer-launcher` وغيرها، ويوجد fallback browser إلى netsurf-gtk executable. |
| `desktop/openbox-menu.xml` | 1684 بايت / 21 سطراً | قائمة Openbox لبدء ISO-X/apps والإعدادات والقفل والخروج. | ينسخ إلى `/etc/skel/.config/openbox/menu.xml`, `/etc/xdg/openbox/menu.xml`, و`/etc/iso-x/openbox-menu.xml`. | لا تحقق Exec آلي شامل بعد؛ `isox-vault` يطلق عبر `xterm -e` مع أمر بلا معاملات، والبرنامج يعرض usage وينتهي؛ `dm-tool lock` وxfce settings تحتاج تحقق. |
| `desktop/openbox-rc.xml` | 4229 بايت / 34 سطراً | إعداد Openbox: theme، desktop، dock، margins 42، keybinds/mouse. | ينسخ إلى `/etc/xdg/openbox/rc.xml` وskel. | لا تحقق XML/desktop keys بعد؛ key `W` والاختصارات تتطلب تحقق Openbox فعلي، ويستخدم xrandr script. |
| `desktop/tint2rc` | 1855 بايت / 72 سطراً | تعريف شريط taskbar bottom 42px ومشغلات/task list/tray/clock بتوقيت بغداد. | ينسخ إلى skel وإلى `/etc/iso-x/tint2rc`; autostart يشغله. | لا اختبار GUI؛ يكرر launcher PCManFM مقابل مدير ملفات Thunar في بقية الواجهة. |
| `desktop/isox-welcome.desktop` | 349 بايت / 11 سطراً | Desktop entry للترحيب Exec `/usr/local/bin/isox-welcome`. | ينسخ إلى applications ونسخة إلى Desktop المحلي في skel. | لا desktop-file-validate منفذ حتى الآن. |

### الأصول الثنائية المقروءة نوعاً/أبعاداً/حجماً فقط

| المسار | النوع والأبعاد | الحجم |
|---|---|---:|
| `assets/iso-x-boot.png` | PNG RGB، 1024×1024 | 87510 بايت |
| `assets/iso-x-desktop-wallpaper.png` | PNG RGBA، 3840×2160 | 2749909 بايت |
| `assets/iso-x-dragon.png` | PNG RGBA، 1024×1024 | 159081 بايت |
| `assets/iso-x-plymouth.png` | PNG RGB، 512×512 | 40774 بايت |
| `docs/previews/isox-welcome-design-preview.png` | PNG RGB، 1600×900 | 215686 بايت |
| `assets/iso-x-boot.svg` | SVG، 23 سطراً / 2362 بايت | شعار متجهي خاص بمشهد الإقلاع. | ينسخه `build-iso.sh` كأصل عام؛ Plymouth يستخدم PNG منفصلة. | XML صالح مصدرًا؛ لا اختبار عرض. |
| `assets/iso-x-desktop-wallpaper.svg` | SVG، 35 سطراً / 6934 بايت | خلفية متجهية 3840×2160 بتنين/سماء وعناصر glow. | تُنسخ إلى `/usr/share/backgrounds/iso-x/`; profile يختار PNG لا SVG. | لا اختبار بصري؛ ربما نسخة مصدر غير مستخدمة في desktop profile. |
| `assets/iso-x-dragon.svg` | SVG، 56 سطراً / 4278 بايت | الشعار المتجهي للواجهة/أيقونة التطبيق. | ينسخ إلى `/usr/share/iso-x/assets` وإلى scalable app icon. | لا اختبار GTK rendering. |
| `assets/iso-x-start.html` | HTML، 38 سطراً / 3490 بايت | صفحة بداية عربية RTL فيها بحث ويب وروابط Debian/Mozilla/README محلية. | ينسخ إلى `/usr/share/iso-x/start.html` وتصبح Firefox homepage بواسطة hook. | اختبار `test_build_contracts.py` يفحص النص وhook؛ رابط README `file:///usr/share/doc/iso-x/README_AR.md` يحتاج تحقق من فتح Markdown في Firefox. |

## الدفعة 5: وثائق المشروع والملفات العامة

| المسار | الحجم/الأسطر | الوظيفة والاعتماديات | المستدعي / مكان ISO | الاختبار / التناقضات |
|---|---:|---|---|---|
| `.gitignore` | 265 بايت / 16 سطراً | يستثني bytecode، مفاتيح/شهادات، build-live، target، evidence وISO outputs. | Git فقط؛ لا يدخل ISO. | لا اختبار. لا يستثني كل صيغ أسرار التوقيع الممكنة أو ملف build console. |
| `AUDIT.md` | 47914 بايت / 478 سطراً | سجل تدقيق تاريخي ونتائج CI/اختبارات source وقيود البناء، مع تحديثات حتى run 39471524581. | توثيق فقط؛ build ينسخه README/docs subset وليس AUDIT إلى ISO بحسب أوامر `build-iso.sh`. | تناقض قديم: أقسام baseline تعود لغياب bootloaders/عدم بناء ISO/ملف migration 004، ثم أقسام لاحقة تصححها؛ أحدث run مسجل 39471524581 وبصمة 989adb وليس run 39474948006. |
| `CHANGELOG.md` | 9935 بايت / 49 سطراً | سجل تاريخي للإصلاحات والاختبارات حتى تعديل xHCI، مع إقرار أن run بعد الإصلاح مطلوب. | توثيق فقط؛ لا يدخل ISO حسب قائمة نسخ docs. | سجل run القديم/البصمة يحتاج تحديثاً بعد الحصول على evidence الجديد. |
| `LICENSE.txt` | 394 بايت / 3 أسطر | إشعار يسمح بدراسة وتعديل واختبار ملفات المشروع، وينبه إلى عدم منح تراخيص الأطراف الثالثة. | توثيق مصدر؛ غير مذكور ضمن ملفات النسخ إلى ISO. | ليس ترخيص SPDX شاملاً؛ `Cargo.toml` يعلن GPL-3.0-or-later، تعارض نطاق الترخيص غير محسوم قانونياً. |
| `README.md` | 3675 بايت / 43 سطراً | مدخل إنجليزي يشرح build على Trixie، اختبار USB، الشجرة والاختبارات/التراخيص. | يُنسخ إلى `/usr/share/doc/iso-x/README.md`. | `Repository layout` يسرد `security/` وهي غير موجودة بحسب جرد المسارات؛ النص العام لا يذكر persistence. |
| `README_AR.md` | 13578 بايت / 135 سطراً | دليل عربي للبناء والإقلاع والاختصارات والواجهة/الأمان. | يُنسخ إلى `/usr/share/doc/iso-x/README_AR.md`. | يكرر `004_isox_040.sql` مرتين في قائمة الملفات (السطر 30 تقريباً)، يزعم أن install-build-deps يثبت Rust عبر rustup رغم أن السكربت لا يفعل، ويستعمل صيغة `Super+W` بينما XML الفعلي يستخدم `key="W"` ويحتاج تحقق. |
| `STATUS_AR.md` | 6349 بايت / 44 سطراً | تقرير 0.3.1 تاريخي صريح بأنه مصدر فقط ولم يختبر GUI/ISO؛ يسرد تغييرات المرحلة القديمة. | لا ينسخ وفق build script. | عنوان/محتوى متقادم لكنه موسوم بوضوح تاريخي. |
| `THIRD_PARTY_NOTICES.md` | 3885 بايت / 29 سطراً | ينسب مراجع Windows-Lite ويشرح عدم نسخ مكونات Windows أو أصولها، مع تحفظات التراخيص. | يُنسخ إلى `/usr/share/doc/iso-x/THIRD_PARTY_NOTICES.md`. | الاختبار المرتبط `tests/test_upstream_integration.py` يختبر التقرير/الواجهة ساكناً وليس محتوى صورة مبنية. |
| `docs/ARCHITECTURE_AR.md` | 7871 بايت / 37 سطراً | شرح معماري لتسلسل النظام والأمان والـ DB والـ build والأداء. | يُنسخ إلى `/usr/share/doc/iso-x/ARCHITECTURE_AR.md`. | أول سطر فعلي ظاهر في الملف هو بند مرقم "9. Data" قبل عنوان الوثيقة، ما يشير إلى fragment/ترتيب غير متسق؛ كما أن ادعاء watermark hook optional يخص المسار الافتراضي فقط. |
| `docs/ARTWORK_REFRESH_2026-10_AR.md` | 1441 بايت / 10 أسطر | تقرير أصل الهوية البصرية وتجربة الترحيب وحدود preview. | لا ينسخ إلى ISO حسب build script. | لا اختبار بصري/GUI. |
| `docs/BUILD_AND_CONTINUE_AR.md` | 2541 بايت / 42 سطراً | إرشادات عربية تاريخية لتجهيز المفتاح والبناء/QEMU ورفع السجلات. | لا ينسخ بحسب build script. | يوصي بتوليد مفتاح وتفعيل watermark لكن البناء الحالي الافتراضي لا يحتاجها؛ يحتاج align مع طريقة build الحالية. |
| `docs/BUILD_AND_TEST_RESULTS_AR.md` | 8632 بايت / 58 سطراً | تقرير اختبارات وبناء وإقلاع موثق لـ run قديم وSHA قديمة. | يُنسخ إلى `/usr/share/doc/iso-x/BUILD_AND_TEST_RESULTS_AR.md`. | ما زال يعرض SHA `989adb...` وrun 39471524581، بينما طلب المستخدم evidence run 39474948006؛ يجب التحقق من artifact قبل تحديث claims. |
| `docs/GAP_ANALYSIS_0.2.0_AR.md` | 6933 بايت / 54 سطراً | سجل فجوات قديم لنسخة 0.2.0 ومراحل القبول. | لا ينسخ بحسب build script. | تاريخي، ويدعي حارس watermark يوقف الإقلاع، بينما الكود الحالي يحذر ويواصل؛ يجب عدم اعتباره وصف 0.4.0. |
| `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` | 5867 بايت / 33 سطراً | قائمة قبول فعلية للأجهزة والوظائف من BIOS حتى shutdown، وجميع الحالات الابتدائية غير مختبرة. | ينسخ إلى `/usr/share/doc/iso-x/`. | checklist فقط وليس نتائج. |
| `docs/QEMU_ACCEPTANCE_AR.md` | 3743 بايت / 37 سطراً | مصفوفة اختبار QEMU ذات 11 مجالاً وحدود محاكاة. | لا ينسخ بحسب build script. | يشرح manual GUI acceptance؛ workflow المعدل يستخدم marker ضيف وQMP، لكن تشغيله الحقيقي لم يحدث. |
| `docs/RELEASE_NOTES_0.3.0_AR.md` | 2316 بايت / 27 سطراً | ملاحظات إصدار 0.3.0 تاريخية مع تصحيحات أمنية. | لا ينسخ بحسب build script. | يذكر USB persistence كميزة/خيار في بند قديم رغم write-usb الحالي يرفضها صراحةً؛ آخر أمر تشغيل ملف يستخدم اسم ISO 0.3.0. |
| `docs/ROADMAP_AR.md` | 2602 بايت / 26 سطراً | خارطة طريق بعد 0.2.0؛ تتضمن اختبار Bevy وSecure Boot ومصادقة. | لا ينسخ إلى ISO. | خطط وليست وظائف موجودة؛ بعض المراحل قديمة. |
| `docs/THIRD_PARTY_LICENSES.md` | 4638 بايت / 35 سطراً | سجل تراخيص مراجع Debian Live Config/OxyOS وحزم Debian/Rust. | يُنسخ إلى `/usr/share/doc/iso-x/THIRD_PARTY_LICENSES.md`. | يصرح أن inventory النهائي للحزم والتراخيص ينتظر build؛ لا يثبت رخصة موحدة لكل source. |
| `docs/UPSTREAM_INTEGRATION_AR.md` | 6062 بايت / 30 سطراً | يشرح خيارات عدم نسخ upstream Debian/OxyOS والتوافقات المحلية. | يُنسخ إلى `/usr/share/doc/iso-x/UPSTREAM_INTEGRATION_AR.md`. | ادعاءات المراجعة upstream ليست قابلة للتحقق من ملفات ISO-X المحلية وحدها. |
| `docs/UPSTREAM_REVIEW_AR.md` | 5014 بايت / 38 سطراً | تقرير مراجعة مصادر Windows Lite وحدود عدم نسخها. | يُنسخ إلى `/usr/share/doc/iso-x/UPSTREAM_REVIEW_AR.md`. | لا يغطي مصادر Debian/OxyOS؛ ذلك في integration report. |
| `docs/FILE_INVENTORY_AR.md` | 53591 بايت / 288 سطراً | جرد وظائف الملفات واعتمادياتها وتغطية قراءتها. | لا يدخل ISO؛ تقرير للمستودع. | يحتوي نتائج مرحلية؛ بعض الأقسام أُعيد تحديثها في هذه الجولة، لا يمثل ذلك قراءة كاملة جديدة لكل محتواه. |
| `docs/PROJECT_MAP_AR.md` | 48312 بايت / 265 سطراً | خريطة البناء والإقلاع والاختبارات والحدود المجهولة. | لا يدخل ISO؛ تقرير للمستودع. | يحتوي نتائج مرحلية؛ أضيفت نتائج التحقق الحالية في ملحق، ولا تثبت الإقلاع أو CI. |

## الدفعة 4: Rust وSQLite والاختبارات وCI

| المسار | الحجم/الأسطر | الوظيفة والاعتماديات | المستدعي / مكان ISO | الاختبار / الملاحظات |
|---|---:|---|---|---|
| `three-d-login/Cargo.toml` | 603 بايت / 18 سطراً | تعريف تطبيق Bevy اختياري إصدار 0.4.0، dependency `bevy = 0.19.1` مع 3D/X11/PNG، GPL-3.0-or-later. | لا يُبنى إلا عند `ISOX_BUILD_CINEMATIC=1`؛ `build-iso.sh` ينسخ الثنائي والأصول إلى ISO إن نجح. | المصدر config ضمن `test_source_config.py`; لا Cargo.lock متتبع، وbuild لا يستخدم `--locked`. |
| `three-d-login/src/main.rs` | 9208 بايت / 170 سطراً | مشهد Bevy بصري اختياري مع dragon asset وparticles، يغلق Enter أو بعد 9s؛ لا مصادقة. | cinematic action في welcome إذا binary موجود. | لا اختبار تشغيل/رندر؛ `test_build_contracts.py` يتحقق من optional gating ونصوص فقط. |
| `db/schema.sql` | 5360 بايت / 125 سطراً | ينشئ schema_migrations/users/app_registry/permissions/fs_index/perf_logs/sys_snapshots/dev_envs/privacy_settings/kernel_watermark/local_app_usage مع triggers وفهارس. | ينسخ إلى `/usr/share/iso-x/db/schema.sql`؛ GTK Store يقرأه، وlegacy Tk Store يقرأ موقعاً مختلفاً ثم يسقط إلى schema مبسط. | `tests/test_schema.py`; جداول عدة لا يظهر استخدامها في GTK الحالية: users, installed_app_permissions, fs_index, sys_snapshots, dev_envs. |
| `db/migrations/002_isox_020.sql` | 1937 بايت / 35 سطراً | يوسع watermark من 0.1.0، ينشئ usage/privacy settings ويعيد triggers. | ينسخ إلى ISO؛ `iso_x_gtk.py` يشغله عند اكتشاف جدول watermark قديم. | `tests/test_schema.py` يغطي مسار migration الأساسي. |
| `db/migrations/003_isox_031.sql` | 311 بايت / 6 أسطر | يضبط watermark version 0.3.1 ويسجل migration. | ينسخ ويُشغّل شرطياً من GTK. | لا اختبار مستقل. |
| `db/migrations/004_isox_040.sql` | 238 بايت / 3 أسطر | يسجل marker 0.4.0 دون تغيير schema. | ينسخ ويُشغّل شرطياً من GTK. | `test_build_contracts.py` يتحقق من ذكره؛ لا اختبار migration فعلي منفصل. |
| `tests/smoke.sh` | 2661 بايت / 52 سطراً (نسخة العمل الحالية) | يوجه `py_compile` عبر `PYTHONPYCACHEPREFIX` إلى temp خارج المستودع، يشغل اختبارات مباشرة وفحوص shell، وينظف cache عند الخروج. | CI ومستخدم محلي. | PASS؛ تحقق `find` عدم بقاء `__pycache__` بعد التشغيل؛ لا يثبت build أو boot. |
| `tests/test_build_contracts.py` | 11691 بايت / 200 سطر (نسخة العمل الحالية) | assertions لعقود staging/apps/hooks/packages/الترخيص، وإضافة CI-only gating وportable SHA sidecar وتعريف شهادة التوقيع، وعقد USB tablet/controller. | pytest وCI؛ ويمكن تشغيله كبرنامج مباشر. | PASS بعد تحديث عقد مطابقة الوسائط المقتبسة؛ static only ولا ينفذ بناء ISO. |
| `tests/test_initramfs_watermark_guard.sh` | 788 بايت / 17 سطراً | يتحقق أن guard يعرض تحذير metadata غائبة ويواصل الإقلاع باستخدام Plymouth fake. | يستدعيه smoke.sh/CI. | لا يغطي حالة module حقيقي/توقيع سليم. |
| `tests/test_qemu_headless_validation.sh` | 7722 بايت / 189 سطراً (نسخة العمل الحالية) | يشغّل QEMU وهمياً وQMP؛ يتحقق من PPM، غياب QMP، مسارات screenshots القديمة، nonce المضلل، serial الفارغ، timeout والخروج غير الصفري بعد marker. | `smoke.sh` وsource-check في CI. | PASS محلياً؛ لا يثبت إقلاع ISO حقيقية أو QMP حقيقياً. |
| `tests/test_schema.py` | 4318 بايت / 65 سطراً | يفحص schema الجارية وtriggers والبيانات المحلية وmigration 0.1.0. | pytest/smoke/CI. | لا يغطي كل استهلاك DB أو migration 003/004. |
| `tests/test_secure_vault.py` | 2613 بايت / 59 سطراً | roundtrip Unicode، wrong passphrase وtampered archive، ويتحقق tempdirs بجانب output. | pytest وCI. | اختبار وظيفي محلي؛ لا يختبر واجهة GTK أو OOM أحجام ضخمة. |
| `tests/test_secureboot_validation.sh` | 1357 بايت / 27 سطراً | ينشئ مفاتيح fixture، يتحقق من تطابق key/cert ويرفض عدم التطابق والشهادة التالفة. | smoke.sh/CI. | لا يختبر UEFI Secure Boot أو MOK. |
| `tests/test_source_config.py` | 7867 بايت / 121 سطراً | assertions للعقود النصية، XML/SVG، قائمة الحزم، Openbox Exec static presence، desktop entry. | CI ينفذه مباشرة؛ ليس test_*. | لا يفحص وجود الأوامر الفعلي داخل ISO ولا صحة اختصارات Openbox بإصدار البرنامج. |
| `tests/test_upstream_integration.py` | 3372 بايت / 60 سطراً | يتحقق من وثائق مصادر Windows-inspired، الحظر على shell=True في welcome، الأصول والربط بالـ build. | smoke.sh وpytest. | static only. |
| `tests/test_watermark_integrity.sh` | 942 بايت / 14 سطراً | اختبار توقيع RSA detached لعينة نصية ثم تعديلها. | smoke.sh/CI. | لا يبني أو يوقع module Linux حقيقياً. |
| `tests/test_write_usb_validation.sh` | 780 بايت / 24 سطراً | fake xorriso، يقبل بصمة ISO الاختبارية ويرفض بصمة خاطئة قبل كتابة جهاز. | smoke.sh وCI. | لا يختبر disk selection أو write فعلي؛ ISO وهمية. |
| `tests/qemu-acceptance.sh` | 5714 بايت / 132 سطراً (نسخة العمل الحالية) | يشغل QEMU المرئي أو headless؛ headless يفوض التشغيل إلى `qemu-runner.py` ويفصل stdout/stderr ويسجل النسخة والمسرّع. وسائط USB device مقتبسة كحجج منفصلة صحيحة. | يدوي وBIOS/UEFI jobs. | ShellCheck وfake-QEMU اجتازا؛ اختبار QEMU الحقيقي لم ينفذ. |
| `tests/qemu-runner.py` | 14425 بايت / 357 سطراً (نسخة العمل الحالية) | يشغل محاولة BIOS/UEFI في process group مستقل، يراقب nonce الضيف، يلتقط VGA بصيغة PPM عبر QMP، يرفض إعادة استخدام screenshot قديمة ويصنف خروج QEMU غير الصفري بعد marker كفشل بنية تحتية. | `qemu-acceptance.sh` في CI فقط. | اختبارات fake QEMU ناجحة؛ لا إثبات إقلاع فعلي، ووجود QMP/VGA ما زال يتطلب بيئة QEMU. |
| `scripts/isox-ci-ready.sh` | 1203 بايت / 36 سطراً | يتحقق من kernel cmdline والـnonce وgraphical target وLightDM وXorg وجلسة المستخدم النشطة. | لا يدخل ISO العادية؛ داخل `/usr/local/sbin` في CI variant. | `bash -n` ناجح؛ لم يُشغّل داخل guest. |
| `systemd/isox-ci-ready.service` | 265 بايت / 12 سطراً | oneshot مشروط بـ`isox.ci=1` وبعد target الرسومي وLightDM، بمهلة 130 ثانية تغطي انتظار probe البالغ 120 ثانية. | CI variant فقط. | `systemd-analyze verify --root=<temp>` نجح مع الملفات التنفيذية staged؛ ليس Trixie rootfs أو اختباراً زمنياً للخدمة. |
| `systemd/isox-ci-ready.timer` | 218 بايت / 11 سطراً | يؤخر تشغيل probe 15 ثانية ويفعّل من `multi-user.target`. | CI variant فقط. | `systemd-analyze verify` نجح داخل root مصطنع على المضيف؛ ليس Trixie rootfs. |
| `scripts/ci-build-in-trixie.sh` | 2229 بايت / 48 سطراً (جديد) | يبني نسخة CI التشخيصية داخل Debian Trixie، يجهز rootfs staging للتحقق من systemd، ويفحص ملف ISO والبنية والبصمة. | يستدعيه build job؛ يكتب الأدلة إلى workspace. | `bash -n` فقط؛ لم يُنفذ داخل Trixie ولم يبن ISO فعلياً. |
| `scripts/create-ci-results.py` | 8978 بايت / 210 سطراً | يجمع نتائج source/build/BIOS/UEFI والبيئة والبصمة في JSON، ويصرّح بأن Persistence غير منفذة ويرفض المدخلات العددية أو JSON غير الصالحة. | acceptance-summary في Actions. | اختبارات التوليد والحالات والمدخلات غير الصالحة ناجحة؛ لا تشغيل حقيقياً مسجلاً. |
| `scripts/run-source-checks.py` | 6354 بايت / 131 سطراً | يشغّل pytest واختبارات المصدر وsyntax وShellCheck وDesktop/XML، ويحفظ log وJSON لكل فحص مع حالة NOT_RUN صريحة للأداة المفقودة. | source-check في Actions؛ أدلة الاختبار خارج المستودع حسب وسائط التشغيل. | اجتاز التشغيل الحالي كل الفحوص المتاحة؛ يحسب pytest cases مع خطوات الفحص في summary. |
| `tests/ci-results.schema.json` | 2729 بايت / 67 سطراً | يعرّف شكل تقرير القبول machine-readable. | `tests/test_ci_results.py`. | الاختبار يغطي الحقول الأساسية وJSON المكسور، وليس validator JSON Schema عاماً. |
| `tests/test_ci_results.py` | 7176 بايت / 147 سطراً | يختبر إنشاء التقرير ورفض JSON المكسور والتقرير الناقص والمدخلات العددية غير الصالحة. | source-check. | PASS محلياً. |
| `tests/test_workflow_contracts.py` | 2735 بايت / 53 سطراً (نسخة العمل الحالية) | assertions ساكنة حول استقلال BIOS/UEFI وشروط Artifacts والبوابات وimmutable action pins ومساحة runner ومهلة جاهزية الضيف. | source-check وpytest. | PASS؛ لا يشغّل GitHub Actions. |
| `.github/workflows/iso-build.yml` | 18612 بايت / 418 سطراً (نسخة العمل الحالية) | يقسم source-check وbuild candidate وBIOS وUEFI وacceptance-summary؛ المرشح ISO تشخيصية CI معلّمة وليست إصداراً عادياً. | GitHub Actions. | اجتاز actionlint وYAML parse والعقود الساكنة؛ لم تُشغّل Actions أو يُرفع artifact. |

**تحديث:** قيس العدد الحالي من `git ls-files` بعد التزام CI السابق: 104 مسارات، منها 99 نصياً و5 PNG ثنائية. جدول التغطية أدناه يضم كل المسارات المتتبعة الآن. لا يعني تاريخ القراءة في الجدول أن كل هذه الملفات أُعيدت قراءتها في جولة الاستئناف الحالية.

## جدول التغطية الحالي للملفات المتتبعة

كان جرد بداية المرحلة صفر 92 مساراً (87 نصياً و5 صور PNG). أضيف منذ ذلك الحين 12 ملفاً نصياً متتبعاً: قُرئت 10 منها بالكامل لهذه المراجعة، بينما لم يُقرأ ملفا التقرير الحاليان كاملين؛ راجعت الأجزاء المرتبطة بالتغييرات فقط، ولذلك وُسما جزئياً صراحةً. الصور الخمس فُحصت بياناتها باستخدام `file` فقط.

| المسار | حالة التغطية |
|---|---|
| `.github/workflows/iso-build.yml` | قُرئ بالكامل |
| `.gitignore` | قُرئ بالكامل |
| `AUDIT.md` | قُرئ بالكامل |
| `CHANGELOG.md` | قُرئ بالكامل |
| `LICENSE.txt` | قُرئ بالكامل |
| `README.md` | قُرئ بالكامل |
| `README_AR.md` | قُرئ بالكامل |
| `STATUS_AR.md` | قُرئ بالكامل |
| `THIRD_PARTY_NOTICES.md` | قُرئ بالكامل |
| `app/iso_x_gtk.py` | قُرئ بالكامل |
| `app/iso_x_shell.py` | قُرئ بالكامل |
| `app/isox_appcenter.py` | قُرئ بالكامل |
| `app/isox_welcome.py` | قُرئ بالكامل |
| `assets/iso-x-boot.png` | ثنائي (فُحصت بياناته فقط) |
| `assets/iso-x-boot.svg` | قُرئ بالكامل |
| `assets/iso-x-desktop-wallpaper.png` | ثنائي (فُحصت بياناته فقط) |
| `assets/iso-x-desktop-wallpaper.svg` | قُرئ بالكامل |
| `assets/iso-x-dragon.png` | ثنائي (فُحصت بياناته فقط) |
| `assets/iso-x-dragon.svg` | قُرئ بالكامل |
| `assets/iso-x-plymouth.png` | ثنائي (فُحصت بياناته فقط) |
| `assets/iso-x-start.html` | قُرئ بالكامل |
| `auto/config` | قُرئ بالكامل |
| `build.sh` | قُرئ بالكامل |
| `config/hooks/live/0050-isox-locales.hook.chroot` | قُرئ بالكامل |
| `config/hooks/live/0100-isox-watermark.hook.chroot` | قُرئ بالكامل |
| `config/hooks/live/0200-isox-plymouth.hook.chroot` | قُرئ بالكامل |
| `config/hooks/live/0300-isox-services.hook.chroot` | قُرئ بالكامل |
| `config/hooks/live/0400-isox-firefox-defaults.hook.chroot` | قُرئ بالكامل |
| `config/package-lists/iso-x.list.chroot` | قُرئ بالكامل |
| `db/migrations/002_isox_020.sql` | قُرئ بالكامل |
| `db/migrations/003_isox_031.sql` | قُرئ بالكامل |
| `db/migrations/004_isox_040.sql` | قُرئ بالكامل |
| `db/schema.sql` | قُرئ بالكامل |
| `desktop/isox-welcome.desktop` | قُرئ بالكامل |
| `desktop/openbox-menu.xml` | قُرئ بالكامل |
| `desktop/openbox-rc.xml` | قُرئ بالكامل |
| `desktop/tint2rc` | قُرئ بالكامل |
| `docs/ARCHITECTURE_AR.md` | قُرئ بالكامل |
| `docs/ARTWORK_REFRESH_2026-10_AR.md` | قُرئ بالكامل |
| `docs/BUILD_AND_CONTINUE_AR.md` | قُرئ بالكامل |
| `docs/BUILD_AND_TEST_RESULTS_AR.md` | قُرئ بالكامل |
| `docs/GAP_ANALYSIS_0.2.0_AR.md` | قُرئ بالكامل |
| `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` | قُرئ بالكامل |
| `docs/QEMU_ACCEPTANCE_AR.md` | قُرئ بالكامل |
| `docs/RELEASE_NOTES_0.3.0_AR.md` | قُرئ بالكامل |
| `docs/ROADMAP_AR.md` | قُرئ بالكامل |
| `docs/THIRD_PARTY_LICENSES.md` | قُرئ بالكامل |
| `docs/UPSTREAM_INTEGRATION_AR.md` | قُرئ بالكامل |
| `docs/UPSTREAM_REVIEW_AR.md` | قُرئ بالكامل |
| `docs/FILE_INVENTORY_AR.md` | قُرئ جزئياً (تحديث نطاق التغطية والنتائج؛ لم يُقرأ كامل الملف في هذه الجولة) |
| `docs/PROJECT_MAP_AR.md` | قُرئ جزئياً (مراجعة الأقسام ذات الصلة وإضافة النتائج؛ لم يُقرأ كامل الملف في هذه الجولة) |
| `docs/previews/isox-welcome-design-preview.png` | ثنائي (فُحصت بياناته فقط) |
| `initramfs/hooks/isox-watermark` | قُرئ بالكامل |
| `initramfs/scripts/init-premount/isox-watermark-guard` | قُرئ بالكامل |
| `kernel/isox-watermark/Makefile` | قُرئ بالكامل |
| `kernel/isox-watermark/dkms.conf` | قُرئ بالكامل |
| `kernel/isox-watermark/isox_watermark.c` | قُرئ بالكامل |
| `kernel/isox-watermark/watermark_bytes.h` | قُرئ بالكامل |
| `plymouth/isox/isox.plymouth` | قُرئ بالكامل |
| `plymouth/isox/isox.script` | قُرئ بالكامل |
| `scripts/apply-windows-look.sh` | قُرئ بالكامل |
| `scripts/build-iso.sh` | قُرئ بالكامل |
| `scripts/ci-build-in-trixie.sh` | قُرئ بالكامل |
| `scripts/collect-performance.sh` | قُرئ بالكامل |
| `scripts/create-ci-results.py` | قُرئ بالكامل |
| `scripts/encode-watermark.py` | قُرئ بالكامل |
| `scripts/generate-dev-signing-key.sh` | قُرئ بالكامل |
| `scripts/install-build-deps.sh` | قُرئ بالكامل |
| `scripts/isox-preload.py` | قُرئ بالكامل |
| `scripts/isox-ci-ready.sh` | قُرئ بالكامل |
| `scripts/isox-run.py` | قُرئ بالكامل |
| `scripts/isox-snap-window.sh` | قُرئ بالكامل |
| `scripts/isox-speedtest` | قُرئ بالكامل |
| `scripts/isox-zram-setup` | قُرئ بالكامل |
| `scripts/record-demo.sh` | قُرئ بالكامل |
| `scripts/run-source-checks.py` | قُرئ بالكامل |
| `scripts/secure-vault.py` | قُرئ بالكامل |
| `scripts/secure-vault.sh` | قُرئ بالكامل |
| `scripts/secureboot-enroll.sh` | قُرئ بالكامل |
| `scripts/toggle-airplane.sh` | قُرئ بالكامل |
| `scripts/write-usb.sh` | قُرئ بالكامل |
| `systemd/isox-preload.service` | قُرئ بالكامل |
| `systemd/isox-preload.timer` | قُرئ بالكامل |
| `systemd/isox-ci-ready.service` | قُرئ بالكامل |
| `systemd/isox-ci-ready.timer` | قُرئ بالكامل |
| `systemd/isox-zram.service` | قُرئ بالكامل |
| `tests/qemu-acceptance.sh` | قُرئ بالكامل |
| `tests/ci-results.schema.json` | قُرئ بالكامل |
| `tests/qemu-runner.py` | قُرئ بالكامل |
| `tests/smoke.sh` | قُرئ بالكامل |
| `tests/test_build_contracts.py` | قُرئ بالكامل |
| `tests/test_ci_results.py` | قُرئ بالكامل |
| `tests/test_initramfs_watermark_guard.sh` | قُرئ بالكامل |
| `tests/test_qemu_headless_validation.sh` | قُرئ بالكامل |
| `tests/test_schema.py` | قُرئ بالكامل |
| `tests/test_secure_vault.py` | قُرئ بالكامل |
| `tests/test_secureboot_validation.sh` | قُرئ بالكامل |
| `tests/test_source_config.py` | قُرئ بالكامل |
| `tests/test_upstream_integration.py` | قُرئ بالكامل |
| `tests/test_watermark_integrity.sh` | قُرئ بالكامل |
| `tests/test_write_usb_validation.sh` | قُرئ بالكامل |
| `tests/test_workflow_contracts.py` | قُرئ بالكامل |
| `three-d-login/Cargo.toml` | قُرئ بالكامل |
| `three-d-login/src/main.rs` | قُرئ بالكامل |

**حصيلة التغطية الحالية:** قُرئ بالكامل: 97؛ قُرئ جزئياً: 2؛ لم يُقرأ: 0؛ ثنائي فُحصت بياناته فقط: 5؛ الإجمالي: 104.

## التصنيف الوظيفي

- **مصدر وبرامج:** `app/`, `scripts/`, `kernel/`, `initramfs/`, `three-d-login/`، مع `db/` لتعريف البيانات والترحيلات.
- **إعدادات البناء وCI:** `auto/config`, `build.sh`, `scripts/build-iso.sh`, `.github/workflows/iso-build.yml`, `.gitignore`.
- **قوائم الحزم:** `config/package-lists/iso-x.list.chroot`.
- **Hooks البناء:** ملفات `config/hooks/live/*.hook.chroot` الخمسة؛ watermark hook مصدر موجود لكنه لا يُنسخ إلا عند تفعيل الخيار.
- **خدمات systemd:** `systemd/` (ثلاث وحدات/مؤقتات) مع إعدادات تفعيلها وتثبيتها في سكربت البناء.
- **Desktop وواجهة المكتب:** `desktop/` (Openbox menu/rc وtint2 وdesktop entry)، التطبيقات GTK، وملفات desktop التي يولدها `scripts/build-iso.sh`.
- **أصول:** خمس صور PNG، وثلاثة SVG، وHTML واحد تحت `assets/`، إضافة إلى معاينة PNG في `docs/previews/`.
- **Plymouth:** ملف إعداد `.plymouth` وscript، مع assets ذات صلة في `assets/`.
- **توثيق:** ملفات الجذر Markdown وملفات `docs/`؛ منها تقارير حالة/نتائج تاريخية لا تُعامل كدليل تشغيل حالي.
- **اختبارات:** 16 ملفاً في `tests/`؛ لا يوجد اختبار إقلاع موثوق كامل في مصدر الاختبارات الحالي.

## الملفات غير المتتبعة والنواتج والمكررات

- عند بدء الفحص لم يوجد untracked حسب الحالة الأولية. ملفا المعرفة الحاليان أصبحا متتبعين في الالتزام السابق؛ التغييرات الحالية تعديلات على ملفات متتبعة، ولم تُنشأ ملفات غير متتبعة في هذه الجولة.
- لا يوجد حالياً `build-live/`, `evidence/`, ISO/sidecar أو مجلدات cache معروفة داخل المستودع. إنشاء هذه النواتج لم يُجر.
- لم يظهر من مراجعة المسارات تطابق ملفين متتبعين بوصفهما نسختين متطابقتين. وجود PNG وSVG للهوية نفسها مقصود كتنويعين، لا يثبت تكراراً بايتياً.
- أمثلة ملفات مصدرية يتيمة/غير مضمّنة بحسب أوامر النسخ: `app/iso_x_shell.py` (واجهة Tkinter القديمة)، `scripts/collect-performance.sh`, `scripts/record-demo.sh`, `scripts/secureboot-enroll.sh`, و`kernel/isox-watermark/dkms.conf`. وكذلك `assets/iso-x-desktop-wallpaper.svg` يُنسخ لكن ملف wallpaper profile يختار PNG. هذه نتائج ربط source/build لا دليل على تعطل ميزة ضمن image.
