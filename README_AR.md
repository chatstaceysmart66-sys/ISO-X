# ISO-X — الإصدار المصدرّي 0.4.0

**الاسم التجاري:** ISO-X
**المطور المعروض:** عبدالله لازم
**الأساس:** Debian Trixie amd64 + kernel Debian + Openbox + GTK3، مع واجهة ISO-X، شريط tint2، متصفح Firefox ESR وNetSurf.

> **الحالة بشفافية:** هذه حزمة مصدرية معدّة لبناء مرشح Live ISO، وليست صورة ISO جاهزة؛ راجع `AUDIT.md` لنتائج الفحص الفعلي الحالية. لا تعتبر ISO مبنية أو مقبولة إلا بعد أن يسجل `AUDIT.md` نتيجة بناء وإقلاع فعلية، ولا توجد بعد قياسات على VM ذات 2 نواة وRAM 1GB. راجع `AUDIT.md` للحالة الحالية و`docs/GAP_ANALYSIS_0.2.0_AR.md` كسجل تاريخي.

## أهم الملفات

- `app/iso_x_gtk.py` — واجهة GTK3 الأساسية.
- `app/iso_x_shell.py` — واجهة 0.1.0 الأصلية محفوظة كمرجع.
- `kernel/isox-watermark/` — وحدة kernel وترويسة العلامة ومخطط Makefile.
- `initramfs/` — hook لإضافة الوحدة والتحقق من توقيعها قبل مواصلة الإقلاع.
- `three-d-login/` — مصدر Rust/Bevy 0.19.1 للمشهد الترحيبي ثلاثي الأبعاد؛ لا يستقبل كلمات مرور ولا يستبدل LightDM/PAM.
- `scripts/build-iso.sh` — بناء Debian Trixie Live amd64، مع مُثبّت Debian Live.
- `auto/config` — إعداد live-build بمصدر إعداد واحد، ويتضمن خيار `--debian-installer live` لتثبيت النظام الحي على القرص.
- `desktop/openbox-rc.xml` و`desktop/openbox-menu.xml` — قائمة Start قابلة للفتح بزر Super، اختصارات لوحة مفاتيح، وقائمة زر الفأرة الأيمن.
- `scripts/isox-run.py` — نافذة تشغيل أمر بلا `shell=True`.
- `scripts/isox-snap-window.sh` — محاذاة النافذة إلى نصف الشاشة عبر `wmctrl` و`xrandr`.
- `scripts/secure-vault.py` — خزنة ملفات مشفّرة ومتحقق من سلامتها (AES-256-CBC + PBKDF2 + HMAC-SHA256)، منفصلة عن آلية الإقلاع.
- `scripts/install-build-deps.sh` — تثبيت أدوات البناء على Debian 13 Trixie والتحقق منها.
- `scripts/isox-zram-setup` + `systemd/isox-zram.service` — إعداد ZRAM بحجم 50% من RAM باستخدام zstd وswappiness=10.
- `scripts/apply-windows-look.sh` — الثيم والخلفية والأيقونات والمجلدات العربية.
- `scripts/toggle-airplane.sh` — تبديل rfkill إن كان العتاد/المحاكي يوفّر أجهزة rfkill؛ لا يدّعي النجاح إذا لم توجد.
- `scripts/isox-preload.py` — cache warmup محلي اختياري، مُعطل افتراضيًا ولا يشغل التطبيقات.
- `scripts/collect-performance.sh` — يجمع قياسات من الجهاز الجاري.
- `scripts/record-demo.sh` — تسجيل شاشة مضيف يعرض VM باستخدام ffmpeg.
- `db/schema.sql` و`db/migrations/002_isox_020.sql` و`003_isox_031.sql` و`004_isox_040.sql` و`004_isox_040.sql` — مخطط SQL ومهاجرات قواعد البيانات السابقة.
- `docs/ARCHITECTURE_AR.md` — شرح البنية والأمان.
- `docs/BUILD_AND_CONTINUE_AR.md` — أوامر البناء الفعلية وما يجب إرساله عند الفشل لاستكمال التصحيح.
- `docs/GAP_ANALYSIS_0.2.0_AR.md` — ما اكتمل وما ينقص وشروط القبول.

## دمج مرجعَي Windows Lite

راجعت [RobertoBiundo/Windows10Lite](https://github.com/RobertoBiundo/Windows10Lite) و[windows10loud/Download-Windows-10-PRO-ISO-fast-and-lite](https://github.com/windows10loud/Download-Windows-10-PRO-ISO-fast-and-lite). المشروع الأول يحوي إعداد NTLite قديمًا لـ Windows 10 Pro 64-bit وملف README يحذّر من فقدان Windows Update وWindows Defender والمتصفح وبعض دعم التعريفات؛ والثاني يعرض روابط تنزيل خارجية وملف تورنت وليس إصدار ISO موثّقًا داخل GitHub Release.

الدمج في ISO-X هو دمج **للأفكار العامة لتجربة الاستخدام** وليس دمج ملفات Windows نفسها: أضيفت لوحة ترحيب باسم ISO-X بأيقونة التنين، اختصارات إلى الأدوات المثبتة، معلومات عتاد محلية، وتأكيد قبل فتح المثبّت. لم أنقل ملف Windows ISO أو ملف التورنت أو إعداد NTLite؛ لأن إعداد Windows لا يعمل على Debian/Linux، والإعداد القديم يحذف مكونات حماية وإمكانية وصول وتعريفات وتحديثات، كما أن مصادر Windows المذكورة لا تثبت هنا سلامة صورة النظام أو حقوق إعادة توزيعها. التفاصيل موثقة في `THIRD_PARTY_NOTICES.md`. بقيت ISO-X توزيعة Debian/Linux بواجهة مستوحاة من Windows، وليست نسخة Windows X-Lite.

## متصفح الويب

الصورة المهيأة تتضمن `firefox-esr` لتوافق أفضل مع المواقع الحديثة و`netsurf-gtk` كمتصفح خفيف مستقل. حزم Debian Trixie تتيح NetSurf ضمن المستودعات الرسمية؛ الحزمة المثبتة صغيرة نسبيًا، لكن توافق JavaScript بالمواقع الحديثة محدود مقارنة بالمتصفحات الأكبر؛ راجع قائمة الحزم المضمنة في سكربت البناء. [مصدر حزمة Debian Trixie](https://packages.debian.org/trixie/amd64/netsurf-gtk)

## متطلبات مضيف البناء

مضيف البناء المطلوب Debian 13 Trixie amd64، بصلاحيات `sudo`، اتصال إنترنت، مساحة فارغة لا تقل عن 20 GiB وذاكرة RAM لا تقل عن 4 GiB. شغّل سكربت تجهيز الأدوات:

```bash
cd /path/to/ISO-X-0.4.0-TRIXIE
./scripts/install-build-deps.sh
```

السكربت يثبت أدوات Debian المطلوبة ويثبت/يختار Rust stable عبر rustup، لأن [دليل Bevy الرسمي](https://bevy.org/learn/quick-start/getting-started/setup/) ينص على استخدام Rust stable حديث. ابقَ على Debian 13 Trixie لمضيف البناء كما يفرضه السكربت.

## مفتاح توقيع العميل

إنشاء هوية اختبار محلية خارج المشروع:

```bash
./scripts/generate-dev-signing-key.sh "$HOME/.local/share/isox-signing"
```

هذا ينشئ مفتاحًا خاصًا وشهادة X.509 للتطوير في مجلد خاص. لا ترفع المفتاح إلى Git أو ZIP أو ISO. في إصدار العميل استخدم مفتاحه المحفوظ في مخزن آمن. ثم:

```bash
export ISOX_RELEASE_KEY="$HOME/.local/share/isox-signing/isox-release.key"
export ISOX_RELEASE_CERT="$HOME/.local/share/isox-signing/isox-release.crt"
sudo --preserve-env=ISOX_RELEASE_KEY,ISOX_RELEASE_CERT ./scripts/build-iso.sh
```

قد يحتاج `sudo` على توزيعتك إلى إعداد صريح لتمرير هذه المتغيرات؛ يمكن تشغيل جلسة root ثم تصديرها هناك. السكربت يفشل إذا لم يُعطَ مفتاح وشهادة، ولا يخلق هوية إصدار ضمنية.

### Secure Boot

إذا كانت سياسة kernel صارمة، يجب أن تكون شهادة توقيع الوحدة موثوقة من النواة (مثلاً عبر MOK في جهاز الاختبار أو ببناء kernel/boot chain مناسبة). مجرد توقيع ملف `.ko` لا يضمن قبوله تلقائيًا. `scripts/secureboot-enroll.sh` يفحص فقط أن المفتاح الخاص والشهادة متطابقان؛ لا يغير إعدادات UEFI ولا يسجل مفاتيح ولا يثبت أن Secure Boot مفعّل. لا تستخدم مفتاح العميل في أي جهاز عام ولا تضمّن المفتاح الخاص في الصورة. المرجع الرسمي: [Linux Kernel Module Signing](https://www.kernel.org/doc/html/latest/admin-guide/module-signing.html).

## البناء

أمر البناء الرئيسي بعد تجهيز المتطلبات والمفتاح:

```bash
sudo --preserve-env=ISOX_RELEASE_KEY,ISOX_RELEASE_CERT ./scripts/build-iso.sh
```

الهدف هو `ISO-X-0.4.0-live-amd64.iso` في مجلد المشروع. إن تعثر البناء، لا تستخدم ملفًا قديمًا على أنه جديد؛ احفظ مخرجات الطرفية و`/tmp/lb-build.log` وأرسلها مع رسالة الخطأ. مجلد `build-live/config` الموجود يجعل السكربت يتوقف عمدًا بدل حذف بنية بناء سابقة تلقائيًا.

## الاختبارات المحلية

```bash
bash tests/smoke.sh
python3 tests/test_secure_vault.py
bash tests/test_watermark_integrity.sh
python3 -m py_compile scripts/isox-speedtest
```

اختبار التوقيع يثبت فقط أن التوقيع المنفصل يرفض حمولة معدّلة؛ لا يثبت الإقلاع من ISO. بعد بناء فعلي، شغّل `tests/qemu-acceptance.sh check` ثم نفّذ مصفوفة القبول في `docs/QEMU_ACCEPTANCE_AR.md`. لا تُسجّل أي خانة Pass إلا بعد التجربة الفعلية. بعد ذلك اجمع الأدلة:

```bash
sudo ./scripts/collect-performance.sh
./scripts/record-demo.sh 60 /path/to/evidence/isox-demo.mp4
```

سجل الفيديو من المضيف الذي يعرض VM، كي يظهر الإقلاع نفسه. لا تسجّل كلمة مرور في الفيديو.

## سطح المكتب والاختصارات

قائمة Openbox هي قائمة Start: اضغط مفتاح Windows/Super أو زر الفأرة الأيمن على سطح المكتب. عند الإقلاع الحي تظهر أيقونات ISO-X، هذا الكمبيوتر، المجلد الشخصي، سلة المحذوفات والشبكة؛ ويظهر مُثبّت Debian Live في القائمة. توجد اختصارات Super+E للملفات، Super+R لتشغيل أمر، Super+D لإظهار سطح المكتب، Super+L للقفل، Ctrl+Super+Esc لمدير المهام، Super+I للإعدادات، Print للشاشة، وSuper+أسهم لمحاذاة النافذة. هذه واجهة مستوحاة من Windows وليست مطابقة بكسل-بكسل، ولم تُقَس دقتها فعليًا هنا.

تبدأ الجلسة بتخطيط العربية، ويبدّل `Alt+Shift` بين العربية `ara` والإنجليزية `us`. يعرض مؤشر لوحة المفاتيح في الشريط التخطيط النشط.

## معاينة واجهة الترحيب

الملف `docs/previews/isox-welcome-design-preview.png` معاينة شكلية لتوضيح الهوية البصرية وتوزيع الأدوات فقط؛ ليست لقطة شاشة من تشغيل فعلي، لأن تشغيل GTK والإقلاع لم يُختبرا في بيئة هذه الجلسة.

## البدء السريع

من سطح المكتب افتح «مرحباً بك في ISO-X»، أو اضغط `Super+W`. اللوحة تفتح المتصفح وإدارة الملفات ومركز التطبيقات والإعدادات والشبكة ومراقبة النظام والطرفية. قبل تشغيل المثبّت، تعرض تحذيرًا واضحًا لأن تثبيت نظام على القرص قد يمسح بيانات وفق اختيارات المستخدم. لا تجمع هذه اللوحة بيانات استخدام ولا تتصل بخدمات خارجية.

### متجر ISO-X

يعرض «ISO-X Store» بيانات التطبيقات المحلية من فهارس AppStream وDEP-11 YAML وAPT المفعّلة، ويعرض Flatpak من remotes الخاصة بالمستخدم فقط عند تثبيت Flatpak. لا يُضاف Flathub تلقائيًا؛ يطلب المتجر موافقة صريحة قبل إضافته. عمليات APT تمر عبر `pkexec`، وعمليات Flatpak محدودة بحساب المستخدم، مع إعادة التحقق من هوية الحزمة والإصدار قبل التنفيذ. تتوفر صفحات البحث والتصنيفات والمثبتة والتحديثات وسجل النشاط وإعدادات اللغة والمظهر والأصوات. بيانات الصور البعيدة لا تُنفذ أو تُحمّل.

تُولّد نغمات الإشعار والنجاح والخطأ والتحذير واكتمال التنزيل محليًا من المصدر وتُضمّن كملفات WAV. اختبار المصدر لا يثبت تشغيلها على جهاز صوت؛ كما أن التوافق الرسومي، وحل الاعتماديات داخل صورة Trixie، وعمليات APT/Flatpak الفعلية تحتاج اختبارًا داخل ISO مبنية وجلسة مستخدم حقيقية.

تصنيفا الألعاب وتطبيقات Windows يعتمدان على بيانات الحزم/الأسماء المتاحة، ولا يمثلان شهادة توافق أو ضمان تشغيل. لا تتوفر حاليًا بيانات تقييم موثقة أو صور معاينة خارجية، ولا يُدّعى دعم برامج Windows أو الألعاب أو حفظ ملفات Office بتطابق كامل.

## الاختصارات في واجهة GTK3

- `1` العمل، `2` التطوير، `3` الويب/الترفيه، `4` شخصي/الإعدادات.
- الضغط مرتين على Ctrl: البحث العام.
- `F12`: Dev Mode.
- أزرار أسفل الواجهة لفتح الملفات والطرفية والمحرر والإعدادات.
- NetSurf يُفتح كتطبيق مستقل.

## ملاحظات أداء وأمان

- لا توجد Telemetry بعيدة أو إعلانات في الكود المضاف.
- التحميل المسبق اختياري ومغلق افتراضيًا، ويكتفي بتدفئة صفحات ملفات تنفيذية من قائمة سماح محلية عندما تكون الذاكرة المتاحة مرتفعة والحمل منخفضًا؛ ويحلل نشاط آخر 30 يومًا فقط.
- ZRAM تهيئة مصدرية؛ تحقق من `zramctl` بعد الإقلاع.
- هدف ≤180MB RAM و≤30 ثانية إقلاع لم يتم إثباته. لا تعرضه كميزة محققة دون قياس حقيقي.
- اسم المطور يظهر في الواجهة ووحدة kernel وSQL، لكن لا يمكن لأي جدول SQL أو وحدة خارجية ضمان عدم تعديله من قبل مالك الجهاز/من يتحكم بسلسلة الإقلاع. هذه حماية سلامة مدمجة في build وليست حماية قانونية تلقائية.

## قائمة اختبار الجهاز الحقيقي

قبل اعتبار النظام جاهزًا، استخدم `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` لتسجيل تجارب BIOS وUEFI والشبكة والصوت والطباعة والمتصفح والإطفاء وإعادة التشغيل وذاكرة 2GB. جميع هذه التجارب ما زالت غير مقبولة حتى يُسجَّل دليل فعلي. راجع `AUDIT.md` و`docs/UPSTREAM_INTEGRATION_AR.md` للحالة الحالية وحدود الدمج.
