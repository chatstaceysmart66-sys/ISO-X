# ISO-X 0.4.0 — تقرير التدقيق الفعلي (خط الأساس قبل الإصلاح)

**تاريخ الفحص:** 2026-10-19 UTC
**النطاق في هذه المرحلة:** النسخة الاحتياطية، هيكل المصدر، إعدادات `live-build` والإقلاع، قائمة الحزم، السكربتات والاختبارات المتاحة، وحدود دمج المصدرين المذكورين.
**حالة التقرير:** تقرير خط أساس قبل إصلاح ملفات البرنامج. لا يعني نجاح اختبارات المصدر نجاح ISO أو توافق العتاد.

## 1. النسخة الاحتياطية وسلامتها

نفّذ الأمر:

```bash
SRC=/mnt/data/ISO-X-0.4.0-TRIXIE
STAMP=20261019T195501Z
tar -czpf "/mnt/data/ISO-X-0.4.0-TRIXIE-preaudit-${STAMP}.tar.gz" -C /mnt/data ISO-X-0.4.0-TRIXIE
sha256sum /mnt/data/ISO-X-0.4.0-TRIXIE-preaudit-20261019T195501Z.tar.gz
tar -tzf /mnt/data/ISO-X-0.4.0-TRIXIE-preaudit-20261019T195501Z.tar.gz >/dev/null
```

الناتج الفعلي:

```text
path=/mnt/data/ISO-X-0.4.0-TRIXIE-preaudit-20261019T195501Z.tar.gz
backup_bytes=3317783
775a69a8243a7dbf415b844d3991ebc16b5368da8b97475a2277a011e7ba7784  /mnt/data/ISO-X-0.4.0-TRIXIE-preaudit-20261019T195501Z.tar.gz
ARCHIVE_INTEGRITY=PASS
ARCHIVE_MEMBER_FILES=80
ARCHIVE_MEMBER_DIRS=35
```

البصمة أعلاه تخص الأرشيف الاحتياطي المحدد، وليس ملف ISO. الأرشيف يحتوي المصدر قبل الاختبارات، بما في ذلك ملفات المخططات والتراخيص والأصول.

## 2. الهيكل والحجم الفعليان

ناتج فحص المجلد قبل الاختبارات:

```text
path=/mnt/data/ISO-X-0.4.0-TRIXIE type=directory size_bytes=4096
3.8M /mnt/data/ISO-X-0.4.0-TRIXIE
files=80
dirs=35
symlinks=0
```

مجموع أحجام الملفات المنطقية داخل النسخة الاحتياطية بعد استخراجها إلى مجلد مؤقت:

```text
FILES=80
DIRECTORIES=35
SYMLINKS=0
LOGICAL_FILE_BYTES=3,537,342
```

أكبر الملفات:

```text
2,749,909  assets/iso-x-desktop-wallpaper.png
  215,686  docs/previews/isox-welcome-design-preview.png
  159,081  assets/iso-x-dragon.png
   87,510  assets/iso-x-boot.png
   40,774  assets/iso-x-plymouth.png
   37,174  app/iso_x_gtk.py
   34,832  app/iso_x_shell.py
   20,638  scripts/build-iso.sh
```

إذن حجم 3.8 MB صحيح للمصدر الموجود على القرص، لكنه **ليس** حجم ISO ولا يعني أن مستودعات النظامين الأخرى موجودة داخله. شجرة النسخة الأصلية كاملة موجودة في `ISO-X-0.4.0-TRIXIE-tree.txt`، وأحجام المجلدات والملفات في `ISO-X-0.4.0-TRIXIE-directory-sizes.txt`، وكلاهما محفوظ خارج مجلد المصدر.

ملاحظة دقيقة: بعد تنفيذ `pytest` و`py_compile` أُنشئت ملفات Python bytecode تحت `__pycache__`؛ لذلك ظهر عدّاد لحظي قدره 101 ملفًا/41 مجلدًا. هذه ملفات اختبار مولّدة وليست ضمن النسخة الاحتياطية الأصلية، وستُزال بعد تسجيلها في `CHANGELOG.md`.

## 3. هل المصدران المطلوبان موجودان بالكامل؟

**لا.** لا توجد مجلدات git أو نسخ upstream كاملة داخل النسخة الاحتياطية. عند أخذ النسخة، كان `config/includes.chroot/` فارغًا، وكذلك مجلدات `licenses/` و`security/` و`docs/audit/`. الملفات الموجودة تخص ISO-X نفسه: إعدادات `auto/config`، قائمة حزم، أربعة hooks، إعدادات Openbox، تطبيقات ISO-X، سكربت بناء، واختبارات.

تم فحص المستودعات العامة عبر GitHub في 2026-10-19:

- [`nodiscc/debian-live-config`](https://github.com/nodiscc/debian-live-config): شجرة المصدر البعيدة احتوت 238 مدخلًا، والمستودع يحتوي `LICENSE` تحت GPL-3.0. النسخة الكاملة غير موجودة داخل المجلد الحالي؛ الموجود فقط إعدادات ISO-X الخاصة، وليست نسخة من هذا المشروع.
- [`OxyHQ/OxyOS`](https://github.com/OxyHQ/OxyOS): شجرة المصدر البعيدة احتوت 315 مدخلًا. يذكر README أن المصدر يتضمن إعداد live-build وواجهة سطح مكتب React/Tauri ضمن `shell/`. واجهة GitHub API لم تعرض ترخيصًا للمستودع (`license: null`) ولم تُظهر الشجرة ملف `LICENSE`, `COPYING`, `NOTICE` أو `AUTHORS`. لهذا لا يجوز افتراض وجود إذن لإعادة توزيع/إعادة تسمية شيفرته؛ يلزم ترخيص مكتوب من صاحب الحقوق قبل نسخ الشيفرة، أو الاقتصار على توافقات نظيفة التنفيذ مستندة إلى السلوك العام بدل نسخ الكود.
- يوجد عدم تطابق موثّق داخل المشروع الحالي: `docs/UPSTREAM_REVIEW_AR.md` و`tests/test_upstream_integration.py` يراجعان مستودعين متعلقين بـ Windows Lite، وليس `nodiscc/debian-live-config` و`OxyHQ/OxyOS`. اختبار integration الحالي لا يثبت أن هذين المصدرين اندمجا.

لا أحتاج منك ملفات ZIP إضافية لإجراء التدقيق؛ الروابط العامة كافية لمراجعة المحتوى الظاهر. ما ينقص لنسخ كود OxyOS حرفيًا هو **إذن/ترخيص صالح من صاحب الحقوق**، لا مجرد رفع الملفات أو تغيير الأسماء. لن تُحذف إشعارات GPL أو نسب المصدر.

## 4. إعداد live-build والإقلاع

الملفات المفحوصة:

- `auto/config`
- `config/package-lists/iso-x.list.chroot`
- `config/hooks/live/*.hook.chroot`
- `scripts/build-iso.sh`
- `scripts/install-build-deps.sh`
- `tests/qemu-acceptance.sh`

ملاحظات وعيوب خط الأساس:

1. **[حرج قبل الإصدار] لا يوجد إعداد صريح لاختيار محمّلات BIOS وUEFI معًا في `auto/config`.** الإعداد يحدد `--binary-images iso-hybrid` لكنه لا يحدد `--bootloaders`. لا يمكن إثبات دعم UEFI من اسم `iso-hybrid` وحده. دليل Live-build يذكر أن خيار `--bootloaders` يقبل أكثر من محمّل لإدراج BIOS وEFI: [دليل `lb_config` الخاص بـ Debian Trixie](https://dyn.manpages.debian.org/trixie/live-build/lb_config.1.en.html#--bootloaders). يجب تعديل الإعداد ثم بناء الصورة وفحص El Torito/system area والإقلاع الفعلي.
2. خيار `--binary-filesystem ext4` لا يثبت أن ISO ستكون ext4؛ توثيق Debian يوضح أن خيار نظام الملفات لا يؤثر إلا في أنواع الصور التي تسمح باختياره، بينما وسيط ISO يكون ISO9660. لذلك لم أعدّه وحده خطأ مانعًا.
3. `scripts/build-iso.sh` يتطلب مفتاحًا وشهادة توقيع يمرّران عبر `ISOX_RELEASE_KEY` و`ISOX_RELEASE_CERT`. هذا شرط متعمّد لمنع إنشاء إصدار غير موقّع، لكنه يجعل البناء غير ممكن دون تهيئة هوية توقيع خارج المصدر.
4. البناء يثبت ملفي الترحيل `002_isox_020.sql` و`003_isox_031.sql` إلى الصورة، لكنه لا ينسخ `004_isox_040.sql` رغم وجود الملف واستدعائه من `app/iso_x_gtk.py`. المخطط الحالي قد يسجّل 0.4.0 عند قاعدة جديدة، لكن ترحيل قاعدة موجودة يجب ألا يعتمد على هذا الأثر الجانبي؛ ينبغي نسخ الملف والتحقق منه باختبار تثبيت.
5. السكربت يبني مشهد Bevy ثلاثي الأبعاد باسم `isox-cinematic`، لكن لم يتوفر Cargo/Rust ولم يُبنَ الملف التنفيذي؛ هذه الميزة غير مثبتة التشغيل في ISO.
6. يوجد فشل إقلاع مقصود عند غياب/عدم التحقق من وحدة watermark. هذا ليس Secure Boot كاملًا: `scripts/secureboot-enroll.sh` يقول صراحةً إنه لا يسجل مفاتيح MOK، ولا يوقّع bootloader أو يفعّل Secure Boot. الوحدة تعرض وسمًا داخل سجل kernel؛ إخفاء النص بـ XOR ليس تشفيرًا ولا حاجز أمان. يجب التعامل مع هذا بوصفه آلية نسبة/سلامة إضافية، لا ضمانًا ضد root.
7. `config/hooks/live/0100-isox-watermark.hook.chroot` يرفض البناء ما لم يوجد مفتاح وشهادة داخل chroot، ولذلك لا يمكن تجاهل التوقيع بمجرد تجاوز فحص المتطلبات. لم تُختبر هذه السلسلة فعليًا داخل ISO في هذه المرحلة.

## 5. تعارضات الحزم وتوافق الواجهة

ناتج فحص قائمة الحزم:

```text
noncomment_package_lines=150
unique_packages=150
duplicates=[]
window_manager ['openbox']
display_manager ['lightdm']
network ['network-manager']
audio ['pipewire-audio', 'pipewire-pulse', 'wireplumber']
```

لا يوجد تكرار مباشر في قائمة الحزم، ولم يظهر مدير نافذة أو مدير شاشة أو مدير شبكة ثانٍ مصرح به بالاسم. التكوين الظاهر هو Openbox مع LightDM، وNetworkManager مع `wpa_supplicant` بوصفه مكوّن Wi-Fi، وPipeWire/WirePlumber للصوت. وجود حزم تطبيقات GTK/XFCE و`lxpolkit` لا يثبت وحده تعارضًا، لكن يجب اختبار جلسة الرسوميات الفعلية.

مخاوف أداء لم تُحسم بقياس فعلي:

- القائمة تحوي 150 حزمة صريحة، ومنها Firefox وNetSurf وLibreOffice (ثلاثة تطبيقات)، وGIMP وVLC وThunderbird وأدوات GNOME/XFCE متعددة. هذا أوسع من صورة مصغّرة جدًا؛ لا توجد قياسات RAM أو حجم ISO بعد، لذا لا يمكن الادعاء أنها مناسبة لأجهزة 2GB قبل قياسها.
- لا يمكن حاليًا التحقق آليًا من توفر كل حزمة في مستودع Trixie عبر البيئة المحلية، لأن فهارس apt المحلية فارغة (مثلًا `apt-cache policy firefox-esr` أعاد `Candidate: (none)`). يجب إجراء حلّ تبعيات حقيقي أثناء البناء بعد تفعيل فهارس Debian.

## 6. فحص الاختصارات وOpenbox واللغة

- `xmlstarlet val desktop/openbox-menu.xml` — خرج `valid`, exit 0.
- `xmlstarlet val desktop/openbox-rc.xml` — خرج `valid`, exit 0.
- فحص ساكن لـ16 أمرًا فريدًا داخل قائمة Openbox واختصاراتها لم يجد أمرًا غير مربوط بحزمة أو سكربت يجري تثبيته بواسطة `scripts/build-iso.sh`. هذا فحص ربط نصّي فقط، وليس تشغيلًا لكل تطبيق.
- سكربت البناء ينشئ `autostart` داخل chroot وينسخ wallpaper وdesktop launchers. الملف غير موجود كمصدر مستقل في الشجرة الأساسية؛ يجب فحص النسخة الناتجة بعد الـ staging.
- إعداد لوحة المفاتيح المولّد: `XKBLAYOUT="us,ara"` و`XKBOPTIONS="grp:alt_shift_toggle"`. المنطقة الزمنية `Asia/Baghdad` واللغة الافتراضية `ar_IQ.UTF-8` مع `en_US.UTF-8` معرفة في سكربت البناء. لم تُختبر عمليًا داخل سطح مكتب حي.
- المتصفحان مذكوران في قائمة الحزم: `firefox-esr`, `firefox-esr-l10n-ar`, و`netsurf-gtk`. لا توجد إعدادات واضحة للصفحة الرئيسية الافتراضية في ملفات المصدر التي فُحصت، ولم يُشغّل متصفح لعدم وجود ISO. دعم الخطوط العربية مطلوب من حزم الخطوط وإعدادات اللغة لكنه غير مثبت بصريًا.
- لا توجد حسابات OS مُنشأة ومختبرة ضمن المصدر نفسه؛ `username=user` وارد في kernel boot parameters. العضوية الفعلية في sudo/كلمة المرور وشاشة تسجيل الدخول تحتاج تحققًا داخل النظام المبني.

## 7. نتائج أوامر الاختبار الفعلية

### Bash syntax

الأمر الذي نُفذ على جميع الملفات المنتهية بـ `.sh`:

```bash
find "$SRC" -type f -name '*.sh' -print0 | while IFS= read -r -d '' f; do bash -n "$f"; done
```

الناتج الملخص:

```text
BASH_N_TOTAL=15 BASH_N_FAIL=0
```

خمسة عشر ملف `.sh` اجتازت `bash -n`. لم يُشغَّل ShellCheck لأن الأداة غير مثبتة:

```text
shellcheck MISSING
SKIP: shellcheck command not installed in this environment
```

### Python tests وsmoke

```text
$ python3 -m pytest -q
..                                                                       [100%]
2 passed in 0.97s
PYTEST_EXIT=0
```

اختبار `tests/smoke.sh`:

```text
PASS: SQLite v0.4.0 schema, local privacy defaults, watermark triggers, local usage, and 0.1.0 migration
PASS: source config, live installer, app entry points, branding, locale/timezone, database migration, and package-list consistency
PASS: source-repo findings are documented, nonportable/unsafe Windows preset and ISO artifacts are not imported, and ISO-X-branded onboarding is wired into the build and desktop menu.
PASS: ISO-X dragon SVGs are valid XML and branding PNG dimensions match the documented resources.
PASS: vault encrypt/decrypt round-trip, Unicode payload, wrong-password rejection, and tamper rejection
PASS: detached signature verifies original module payload and rejects modified payload (test fixture only)
PASS: Secure Boot helper validates matching key/cert only, rejects mismatches, and never enrolls UEFI keys.
PASS: source syntax and tests complete; these do not imply ISO build or boot acceptance.
EXIT=0
```

اختبارات مستقلة:

```text
$ bash tests/test_watermark_integrity.sh
PASS: detached signature verifies original module payload and rejects modified payload (test fixture only)
EXIT=0

$ bash tests/test_secureboot_validation.sh
PASS: Secure Boot helper validates matching key/cert only, rejects mismatches, and never enrolls UEFI keys.
EXIT=0
```

هذان الاختباران يستخدمان payload/fixtures اختبارية؛ لا يثبتان توقيع نواة داخل صورة ISO حقيقية.

### Systemd units

```text
$ systemd-analyze verify systemd/*
isox-preload.service: Command /usr/local/bin/isox-preload is not executable: No such file or directory
isox-zram.service: Command /usr/local/sbin/isox-zram-setup is not executable: No such file or directory
SYSTEMD_VERIFY_EXIT=1
```

هذا الأمر شُغّل على مضيف التدقيق وليس على root filesystem الناتج؛ سكربت البناء ينسخ البرنامجين إلى تلك المسارات في الصورة. لذلك النتيجة **غير ناجحة في اختبار المضيف وغير كافية لوصف وحدات ISO بأنها سليمة أو معطوبة**. المطلوب إعادة `systemd-analyze verify` داخل root staging بعد وجود الملفين.

### XML

```text
$ xmlstarlet val desktop/openbox-menu.xml
/mnt/data/ISO-X-0.4.0-TRIXIE/desktop/openbox-menu.xml - valid
EXIT=0

$ xmlstarlet val desktop/openbox-rc.xml
/mnt/data/ISO-X-0.4.0-TRIXIE/desktop/openbox-rc.xml - valid
EXIT=0
```

### بناء ISO وQEMU

البيئة في وقت الفحص:

```text
Debian GNU/Linux 13 (trixie)
x86_64
free disk: 30G
MemTotal: 6091016 kB
MemAvailable: 4896588 kB
```

الأدوات غير الموجودة في البيئة:

```text
shellcheck MISSING
lb MISSING
live-build MISSING
debootstrap MISSING
xorriso MISSING
mksquashfs MISSING
qemu-system-x86_64 MISSING
ovmf MISSING
qemu-img MISSING
rustc MISSING
cargo MISSING
```

تم تنفيذ حارس سكربت البناء فعليًا:

```text
$ scripts/build-iso.sh
المتطلب غير موجود: lb
BUILD_GUARD_EXIT=3
```

وتحقق QEMU:

```text
$ tests/qemu-acceptance.sh check
MISSING tool: xorriso
QEMU_CHECK_EXIT=2

$ tests/qemu-acceptance.sh bios
MISSING tool: qemu-system-x86_64
QEMU_BIOS_EXIT=2
```

لم ينتج ISO في هذه المرحلة، ولم يحدث إقلاع BIOS/UEFI، أو اختبار واجهة/شبكة/صوت/طابعة/إطفاء/إعادة تشغيل. هذه نتائج **غير منفذة بسبب الأدوات الغائبة**، وليست Pass.

## 8. أولويات الإصلاح الناتجة عن هذا التدقيق

| الأولوية | الموقع | المشكلة المثبتة/المخاطرة | الإجراء المطلوب |
|---|---|---|---|
| P0 | `auto/config` | لا اختيار صريح لمحمّلات BIOS وUEFI معًا | إضافة bootloaders المقصودة، ثم التحقق من الصورة الفعلية وBIOS/UEFI |
| P0 | بيئة البناء | `lb`, `xorriso`, `debootstrap`, `mksquashfs`, `cargo`, `rustc` غير متوفرة | تجهيز بناء Debian Trixie ثم إعادة بناء نظيفة؛ ليس هناك ISO حالي لاختباره |
| P0 | `OxyHQ/OxyOS` | لا يوجد ترخيص ظاهر في بيانات/شجرة المستودع | لا تنسخ مصدره حتى يتوفر إذن/ترخيص؛ لا تمسح النسب أو الإشعارات |
| P1 | `scripts/build-iso.sh` | `004_isox_040.sql` موجود ولكنه غير منسوخ إلى root filesystem | إضافة install للترحيل واختبار مساره في الصورة |
| P1 | `tests/test_upstream_integration.py`, `THIRD_PARTY_NOTICES.md`, `docs/UPSTREAM_REVIEW_AR.md` | يغطي مراجع Windows Lite القديمة ولا يختبر المستودعين المطلوبين | فصل تقرير المصادر القديمة عن مراجعة Debian Live Config/OxyOS وبناء اختبارات صحيحة |
| P1 | `systemd/` واختبارات البناء | `systemd-analyze verify` لا يعمل في root staging ويُظهر مسارات host مفقودة | اختبار الوحدات مع rootfs اصطناعي أو بعد staging |
| P1 | أدوات التدقيق | ShellCheck وQEMU/OVMF غير متوفرة | تثبيتها/تشغيلها ثم حفظ السجلات |
| P1 | `config/package-lists/iso-x.list.chroot` | 150 حزمة صريحة مع تطبيقات كبيرة؛ لا توجد قياسات أداء 2GB | قياس حجم ISO وRAM والبدء في جلسة 1024MB، ثم تقليل الاختيارات إذا فشل الهدف |
| P2 | المتصفح واللغة والصوت والطباعة والعتاد | إعدادات ثابتة فقط دون اختبار تشغيل حقيقي | مصفوفة قبول داخل QEMU ثم اختبارات جهاز واقعي للأجهزة الطرفية |
| P2 | Secure Boot / watermark | مساعد Secure Boot للتحقق فقط، وليس إعداد سلسلة إقلاع موثوقة كاملة | وصف الميزة بدقة واختبار التوقيع/الرفض/المفاتيح الموثوقة بعد تثبيت البيئة |

## 9. متابعة الإصلاح والتحقق — 2026-10-20

هذا القسم أحدث من خط الأساس أعلاه، ويصحح الحالات التي تغيرت. يحتفظ القسم السابق كسجل تاريخي للاختبارات التي أجريت في 2026-10-19؛ لا تُعامل نتائجه كاختبار للتغييرات الحالية.

| المسار | السبب والدليل | الإصلاح المنفذ | اختبار ما بعد الإصلاح |
|---|---|---|---|
| `scripts/build-iso.sh` | كانت ملفات `etc/default/locale` و`keyboard` تُكتب قبل ضمان وجود `etc/default`، ما يفشل في تجهيز جديد | إنشاء `config/includes.chroot/etc/default` قبل الكتابة؛ يبقى مجلد البناء غير الفارغ مرفوضاً ولا يمسح تلقائياً | `tests/test_build_contracts.py` يتحقق من ترتيب الإنشاء؛ تشغيل بناء ISO غير متاح حتى الآن |
| `config/package-lists/iso-x.list.chroot` | أسماء `libgles2-mesa`, `policykit-1`, `fonts-kacst`, `pinta` لم تظهر في فهرس Trixie amd64 الذي فُحص؛ كانت بدائل `libgles2`, `polkitd` ووجود `lxpolkit` محددة في الفهرس | استبدال الاسمين الأولين بأسماء الحزم المؤكدة، حذف `fonts-kacst` و`pinta` بعد تأكيد عدم وجود استعمال لـ Pinta وأن خطوط Noto موجودة | فحص فهرس Debian Trixie amd64 المذكور في سجل الجلسة؛ يلزم إعادة حل كامل للقائمة ضمن `lb build` |
| `scripts/build-iso.sh`, `config/hooks/live/0100-isox-watermark.hook.chroot`, `initramfs/hooks/isox-watermark`, `initramfs/scripts/init-premount/isox-watermark-guard` | watermark كانت مساراً إلزامياً في صورة البناء؛ غياب الوحدة أو بياناتها كان يمكن أن يحجب الإقلاع، كما كان hook يفرض مفاتيح ورؤوساً على البناء الأساسي | جعل الوحدة والتوقيع اختيارياً عبر `ISOX_ENABLE_WATERMARK=1`، وقصر نسخ hook على الخيار، وتحويل أخطاء حارس initramfs إلى تحذير مع متابعة الإقلاع؛ لا يُدّعى Secure Boot | `bash tests/test_watermark_integrity.sh`, `bash tests/test_secureboot_validation.sh` واختبارات smoke؛ صورة فعلية لم تُبنَ |
| `scripts/build-iso.sh`, `scripts/install-build-deps.sh` | بناء Bevy/Rust كان مطلوباً ضمن المسار الأساسي ويجري خطر تشغيل تبعيات Rust كـ root | تعطيل المشهد في البناء الافتراضي؛ البناء الاختياري يستخدم حساب صاحب الاستدعاء عند تشغيل السكربت عبر sudo، وتجهيز التبعيات لا يثبت Rust | فحص إعداد المصدر واختبارات البناء؛ Bevy غير مبني ولم يختبر تشغيله |
| `app/iso_x_gtk.py` | اختصار أرقام 1–4 كان يعترض الكتابة؛ البحث/نسخ الملفات/حفظ المستند قد ينفذ عملاً حاجباً؛ فك ترميز النص قد يستبدل بايتات غير مفهومة | السماح بالاختصارات فقط خارج أدوات إدخال النص، نقل العمليات الثقيلة للخلفية، ورفض حفظ بيانات غير مفكوكة مع كتابة آمنة | ترجمة Python واختبارات المصدر؛ يلزم اختبار GUI بعد بناء ISO |
| `app/isox_appcenter.py` | الاستعلام عن الحزم كان متزامناً، ولم يظهر تحديث فهارس APT أو تأكيد الإزالة، وكان فشل `pkexec` غير معالج | التحقق بالخلفية، تحديث الفهارس قبل التثبيت وإتاحة تحديث صريح، تأكيد الإزالة، معالجة أخطاء الصلاحية/الشبكة، وتمرير كل تغييرات النظام عبر `pkexec apt-get` | `python3 tests/test_build_contracts.py` و`python3 -m py_compile app/isox_appcenter.py`؛ لم تُختبر GTK على سطح مكتب حي |
| `auto/config` | كان يطلب `linux-headers` حتى في الصورة الافتراضية رغم جعل وحدة kernel اختيارية | الاقتصار على `linux-image`؛ يضيف إعداد watermark الاختياري `linux-headers-amd64` عند طلبه | `python3 tests/test_source_config.py` — exit 0؛ يلزم بناء الصورة للتحقق من حل live-build |
| `initramfs/scripts/init-premount/isox-watermark-guard` | `echo /dev/console` وحده لا يضمن ظهور الخطأ عند وجود Plymouth | إرسال الرسالة إلى Plymouth ثم إنهاء splash، مع طباعة console والاستمرار | `bash tests/test_initramfs_watermark_guard.sh` ضمن smoke — exit 0؛ لم يُختبر عرض حقيقي على جهاز |
| `scripts/secure-vault.py` | أرشيف tar والبيانات المشفرة المؤقتة قد تستهلك tmpfs `/tmp` على أجهزة قليلة الذاكرة | وضع العمل المؤقت بجانب ملف الخزنة/مجلد الاستعادة على قرص الوجهة، مع نقل البيانات على دفعات | `python3 tests/test_secure_vault.py` — exit 0؛ مساحة القرص الفعلية تظل قيد المستخدم |
| `app/iso_x_gtk.py` | مدير الملفات المخصص كان يوفّر نسخاً فقط، ولا ينفذ النقل أو الحذف المطلوبين | إضافة نقل/حذف مع تأكيد للمستخدم وتشغيل في thread خلفي، ورفض الوجهة الموجودة والنقل إلى مجلد فرعي؛ الحذف دائم ومعلن قبل التأكيد | اختبار عقد في `tests/test_build_contracts.py`؛ ترجمة Python ناجحة؛ لا اختبار GTK تفاعلي في هذه البيئة |
| `app/isox_appcenter.py` | بطاقتا Evince كانتا تمثلان الحزمة نفسها وتنتجان حالة/اختصارات متكررة | الإبقاء على بطاقة واحدة واختبار تفرد أسماء الحزم في الكتالوج | `python3 tests/test_build_contracts.py` — exit 0 |
| `scripts/write-usb.sh` | لم يتحقق من sidecar SHA-256 أو سلامة ISO أو سعة القرص قبل `dd` | التحقق من SHA-256 وبنية ISO بواسطة `xorriso`، مقارنة حجم القرص، عرض الهدف والحصول على تأكيد حرفي قبل الكتابة | `bash tests/test_write_usb_validation.sh` — exit 0؛ لا كتابة وسيط حقيقي |
| `config/hooks/live/0300-isox-services.hook.chroot` | هوية شاشة LightDM لم تكن مضبوطة صراحةً | إعداد خلفية ISO-X وشعارها في LightDM GTK Greeter | اختبار مصدر في `tests/test_source_config.py` — exit 0؛ لا إقلاع مرئي بعد |
| `scripts/build-iso.sh`, `app/isox_welcome.py`, `three-d-login/src/main.rs` | المشهد الاختياري لم يكن متاحاً من واجهة الترحيب، ونصه يدّعي الانتقال إلى جلسة آمنة رغم أن Bevy ينهي العملية | إضافته للوحة فقط عند وجود executable، مراقبة خروجه، وتصحيح النص ليقول العودة للوحة؛ منع Cargo بصلاحيات root | اختبار عقد/ترجمة Python وBash — exit 0؛ لا GPU أو مشهد مبني للتحقق |
| `scripts/build-iso.sh`, `app/iso_x_shell.py` | نسخة Tkinter محفوظة كانت تُنسخ إلى ISO دون مشغّل أو `python3-tk`، بينما GTK هي الواجهة الفعلية | إبقاء المصدر التاريخي وعدم تضمينه في الصورة | `python3 tests/test_build_contracts.py` — exit 0 |
| `scripts/encode-watermark.py`, `scripts/build-iso.sh` | مولّد header كان يكتب إلى شجرة المصدر؛ استدعاء مبكر غير مقصود قبل فحوص البناء جعل اختبار UID يكتشف إنشاء staging قبل الرفض | إضافة output path اختياري وتوليد الرأس داخل staging، ونقل الاستدعاء إلى فرع watermark بعد الحواجز؛ رفض ISO/sidecar سابق بدل استبداله أو الخلط بينه وبين ناتج جديد | `python3 tests/test_build_contracts.py` — exit 0؛ يثبت رفض UID دون إنشاء staging وتطابق header المولّد مع المصدر دون تغييره |
| `scripts/build-iso.sh`, Openbox autostart | كان IBus يُطلق من autostart مرتين | الاحتفاظ بمشغل Openbox وإزالة ملف XDG الذي ينشئه البناء | اختبار عقد في `tests/test_build_contracts.py` — exit 0 |
| `README.md`, `docs/ARCHITECTURE_AR.md`, `docs/UPSTREAM_INTEGRATION_AR.md`, `docs/THIRD_PARTY_LICENSES.md` | الوثائق السابقة اشترطت Rust/مفتاحاً دائماً ووصفت watermark كشرط إقلاع، ولم تميز بدقة بين مراجعة مصدر ونسخ كود | تصحيح مسار البناء الاختياري وإضافة مصفوفة توافق/قرار ترخيص مع التزامات المصادر المفحوصة | مراجعة نصية واختبارات التوثيق في `tests/test_build_contracts.py` |

### نتائج البيئة الحالية

- الفرع الحالي `fix/isox-build-and-runtime`؛ التعديلات السابقة محفوظة في شجرة العمل ولم تُدفع إلى remote أثناء هذه الجلسة.
- الهدف المعلن في `auto/config`: Debian Trixie، amd64، ISO hybrid، Syslinux وGRUB EFI. هذا إعداد وليس إثبات تشغيل.
- `python3 -m py_compile app/isox_appcenter.py` — exit 0.
- `python3 tests/test_build_contracts.py` و`python3 tests/test_secure_vault.py` و`bash tests/smoke.sh` — exit 0.
- تكررت نتيجة `python3 tests/test_build_contracts.py` بعد إصلاح خلل الترتيب الذي أنشأ staging قبل حاجز root؛ exit 0.
- فحص 146 اسم حزمة من ملفات فهارس Debian Trixie amd64 الرسمية عبر المكونات الأربعة — 0 أسماء مفقودة.
- فحص 148 اسماً، شاملاً تبعيات watermark الاختيارية (`build-essential`, `linux-headers-amd64`) من فهارس Trixie amd64 — 0 أسماء مفقودة.
- جولة التسليم الأخيرة: `bash tests/smoke.sh`, Python `py_compile`, Bash/POSIX syntax, XML/SVG، `systemd-analyze verify` داخل staging، و`git diff --check` — جميعها exit 0.
- `python3 -m pytest -q` — exit 1 (`No module named pytest`)، و`desktop-file-validate`/ShellCheck غير مثبتتين. لم تُجرَ محاولة `sudo` تفاعلية.
- `bash tests/test_write_usb_validation.sh` — exit 0؛ checksum مطابق قُبل، والمعدل رُفض قبل الكتابة.
- `python3 tests/test_source_config.py` — exit 0؛ يتضمن فحص ربط desktop/Openbox Exec إلى حزم أو staged launchers.
- `systemd-analyze verify` على rootfs مؤقت تضمن الوحدات والثنائيات وtargets القياسية — exit 0. ShellCheck و`desktop-file-validate` غير مثبتين.
- `python3 -m pytest -q` — exit 1 لأن pytest غير مثبت (`No module named pytest`).
- `./build.sh` — exit 2 عند حاجز root؛ لم يصل إلى `lb build`. فحص QEMU — exit 2 بسبب غياب `xorriso`، ولا تتوفر أدوات QEMU/OVMF.
- نتيجة الاختبار الكامل والبناء الحالي موثقة في `docs/BUILD_AND_TEST_RESULTS_AR.md`.

## 11. تحقق Debian Trixie وCI — 2026-10-20

- أُثبتت تبعيات الاختبار في Debian Trixie داخل Docker، وشُغلت الاختبارات على Python 3.13.5 / pytest 8.3.5: `python3 -m pytest -q` — 11 passed؛ `tests/smoke.sh` وجميع اختبارات المشروع المحددة exit 0.
- `bash -n` لكل سكربتات Bash/hooks و`sh -n` لسكربتات initramfs — exit 0. ShellCheck مع `-S warning`, `desktop-file-validate`, `xmllint` لـXML/SVG، و`systemd-analyze verify` داخل rootfs مؤقت — exit 0.
- `scripts/install-build-deps.sh` اكتمل داخل Trixie وثبت أدوات Live Build وQEMU وOVMF والاختبار. بعد التثبيت: `df -h /workspace` أظهر 16 GiB حرة، وRAM إجمالية 7.8 GiB. شرط البناء 20 GiB لم يتحقق؛ `./build.sh` لم يُشغّل داخل الحاوية.
- على المضيف كانت مساحة workspace 19 GiB وUID 1000. لا يوجد تجاوز لشرط الحجم أو محاولة كتابة ISO وهمية.
- أُضيف `.github/workflows/iso-build.yml` إلى الدفع التلقائي و`workflow_dispatch`: تنظيف مساحة على runner مؤقت، إعادة قياس الموارد على المضيف وداخل Trixie، تشغيل الاختبارات والبناء وEl Torito/System Area وBIOS/UEFI headless. YAML ونصوص Bash اجتازت التحليل، لكن GitHub Actions لم يُشغّل بعد.
- الجولة الأخيرة داخل Trixie: `python3 -m pytest -q` — 11 passed؛ `bash tests/smoke.sh`, اختبارات العقود والمصدر والخزنة وUSB وQEMU failure detector — exit 0؛ ShellCheck `-S warning`, desktop-file-validate, xmllint، وsystemd verify — exit 0. Python هو 3.13.5.
- بعد تنصيب متطلبات البناء الكاملة كان المتاح 16 GiB فقط، فقُطع المسار قبل `./build.sh` برمز 32؛ لم تُنتج ISO ولم تُختبر BIOS/UEFI فعلياً. Workflow YAML وhost/container Bash اجتازا التحليل؛ لا run أو artifact بعد.
- لم تنتج ISO، ولم يجر QEMU boot أو اختبار BIOS/UEFI. ينتظر ذلك runner CI ينجح في فحوص 20 GiB/4 GiB؛ اختبار GUI والأجهزة الحقيقية باقٍ.
- لا يُسجل نجاح بناء ISO أو إقلاع BIOS/UEFI قبل ظهور ملف ISO واختباره فعلياً؛ قائمة اختبارات العتاد في `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` لا تزال غير منفذة.

## 9. حدود هذا التقرير

هذا التقرير خط أساس من الأوامر التي نُفذت فعليًا وفحص ملفات المصدر الموجودة. لم تُجر تغييرات على منطق التطبيقات قبل تدوين هذه النتائج. المرحلة التالية ستنفذ الإصلاحات المسجلة واحدًا تلو الآخر، وتضيف لكل إصلاح السبب والمكان والدليل وإعادة الاختبار في `CHANGELOG.md` و`AUDIT.md`. لن توصف صورة بأنها جاهزة قبل وجود ISO ذي بصمة، وفحص بنية الوسيط، واختبار إقلاع BIOS وUEFI، وتسجيل الحالات غير القابلة للاختبار على هذه البيئة.

---

# 10. تنفيذ الإصلاحات وإعادة الفحص (2026-10-19 UTC)

القسمان أعلاه 1–9 يحفظان سجل خط الأساس قبل إصلاحات هذا اليوم. النتائج التالية هي آخر نتائج المصدر بعد تطبيق التغييرات الموضحة، وتُقدّم على أي حالة قديمة عند التعارض.

## 10.1 ما تغيّر فعليًا

| المكان | السبب المكتشف | التعديل | حالة التحقق |
|---|---|---|---|
| `auto/config` | لم يكن اختيار محمّلات الإقلاع صريحًا | إضافة `--bootloaders "syslinux grub-efi"` مع `iso-hybrid`، بالترتيب الذي يدعمه دليل Debian Live-build لتجهيز BIOS وUEFI | النص والفحص الساكن صحيحان؛ لم يجرِ `lb config` لأن `lb` غير مثبت، ولم يُختبر إقلاع ISO |
| `scripts/build-iso.sh` | التطبيق يبحث عن `004_isox_040.sql` لكن البناء لم ينسخه إلى root filesystem | إضافة أمر `install` للمهاجرة 004 بجانب 002 و003 | اختبار رجعي يتحقق من وجود كل ملف مصدر وهدف staging؛ لم يُنشأ chroot حقيقي بسبب غياب live-build |
| `assets/iso-x-start.html` و`config/hooks/live/0400-isox-firefox-defaults.hook.chroot` | لم توجد صفحة رئيسية محددة لمتصفح Firefox في المصدر | إنشاء صفحة بدء عربية RTL محلية؛ hook يضيف تفضيل Firefox ESR في `/etc/firefox-esr/firefox-esr.js` بعد التفضيلات الموجودة، مع بقائها قابلة للتجاوز من ملف المستخدم | اختبار Python يشغّل hook على root filesystem مؤقت، ويتحقق من أولوية الصفحة وعدم تكرار الإضافة؛ ليس تشغيل Firefox فعليًا. مرجع مسار التفضيلات: [Debian Firefox wiki](https://wiki.debian.org/Firefox) |
| `build.sh` | لم يكن هناك مدخل بناء باسم واحد في جذر المشروع | إضافة wrapper ينفذ `scripts/build-iso.sh` دون تجاوز الحواجز | نُفّذ فعليًا؛ توقف بالسبب المتوقع لأن `lb` غير مثبت (exit 3) |
| `README.md`, `README_AR.md`, `docs/ARCHITECTURE_AR.md`, `docs/BUILD_AND_CONTINUE_AR.md`, `STATUS_AR.md` | وثائق الدخول الرئيسية أشارت إلى Bookworm/0.3.1 أو إلى تاريخ قديم | تحديث متطلبات النسخة الحالية إلى Debian Trixie/0.4.0، ووضع إشارة واضحة على تقرير الحالة التاريخي | فحص `grep` على الوثائق النشطة لم يجد Bookworm أو مسارات ISO-X 0.3.1 القديمة |
| `docs/THIRD_PARTY_LICENSES.md`, `docs/UPSTREAM_INTEGRATION_AR.md` | لا يوجد توثيق واضح يفصل المراجع الخارجية عن الشيفرة المضمّنة، وغياب الترخيص من مستودع OxyOS الرئيسي | إضافة سجل تراخيص/نسب وجدول حالة دمج، وتوثيقهما أيضًا داخل image staging | اختبار ساكن يتحقق من وجود المصدرين والحد القانوني، لكنه لا يحوّل المراجعة إلى دمج كامل للشيفرة |
| `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` | لم يكن هناك سجل موحد لاختبارات العتاد الحقيقي | إضافة قائمة لكل محاور الإقلاع والأجهزة الطرفية والأداء والإطفاء وإعادة التشغيل | كلها موسومة «لم يُختبر بعد» لعدم وجود ISO للإقلاع |
| `scripts/install-build-deps.sh` | يحتاج المدقق المستقبلي ShellCheck؛ الأداة غير مثبتة هنا | إضافة `shellcheck` إلى قائمة التثبيت والتحقق بعد التجهيز | لم يمكن تثبيته لأن `apt-get update` لم يصل إلى مستودعات Debian في هذه البيئة |
| `tests/test_build_contracts.py`, `tests/test_source_config.py` | يجب ألا يعود نقص مهاجرة 004 أو غموض محمّلات الإقلاع أو فقد توثيق الرخص | إضافة تأكيدات ارتدادية لهذه العقود، واختبار فعلي لسلوك hook الصفحة الرئيسية عبر root مؤقت | `pytest` النهائي: 4 passed |

## 10.2 أوامر إعادة الاختبار ومخرجاتها

السجل النصي الكامل للمرحلة الأخيرة: [`evidence/PHASE2_RETEST_20261019.txt`](evidence/PHASE2_RETEST_20261019.txt)، وتوجد نسخة منفصلة للتنزيل باسم `ISO-X-0.4.0-FINAL-RETEST-20261019.txt`. أهم نواتج التنفيذ:

```text
$ find . -type f -name "*.sh" -print0 | ... bash -n
BASH_N_TOTAL=16 BASH_N_FAIL=0

$ sh -n all config/hooks/live/*.hook.chroot
HOOK_SYNTAX_TOTAL=5 HOOK_SYNTAX_FAIL=0

$ python3 AST parse all .py
PY_AST_FILES=13 PY_AST_ERRORS=0
PY_AST_EXIT=0

$ PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q
....                                                                     [100%]
4 passed in 0.87s
PYTEST_EXIT=0

$ PYTHONDONTWRITEBYTECODE=1 bash tests/smoke.sh
PASS: SQLite v0.4.0 schema, local privacy defaults, watermark triggers, local usage, and 0.1.0 migration
PASS: source config, live installer, app entry points, branding, locale/timezone, database migration, and package-list consistency
PASS: source-repo findings are documented, nonportable/unsafe Windows preset and ISO artifacts are not imported, and ISO-X-branded onboarding is wired into the build and desktop menu.
PASS: ISO-X dragon SVGs are valid XML and branding PNG dimensions match the documented resources.
PASS: vault encrypt/decrypt round-trip, Unicode payload, wrong-password rejection, and tamper rejection
PASS: detached signature verifies original module payload and rejects modified payload (test fixture only)
PASS: Secure Boot helper validates matching key/cert only, rejects mismatches, and never enrolls UEFI keys.
PASS: source syntax and tests complete; these do not imply ISO build or boot acceptance.
SMOKE_EXIT=0

$ xmlstarlet val desktop/openbox-menu.xml desktop/openbox-rc.xml assets/iso-x-dragon.svg assets/iso-x-boot.svg assets/iso-x-desktop-wallpaper.svg
... - valid (all five documents)
XML_EXIT=0

$ HTMLParser(assets/iso-x-start.html)
HTML_PARSE=PASS

$ systemd-analyze verify --root="$STAGE" isox-preload.service isox-preload.timer isox-zram.service
SYSTEMD_STAGED_VERIFY_EXIT=0
PRELOAD_EXECUTABLE=PASS
ZRAM_EXECUTABLE=PASS
```

ملاحظة عن Systemd: التحقق الأخير استعمل root staging مؤقتًا لتوفير ملفات `ExecStart` المطلوبة، والـ preload/timer نُسخا إلى مجلد systemd للنطاق الساكن لأن `systemd-analyze --user --root=...` لم يدعم هذا السياق هنا (`Failed to initialize unit search paths ... Invalid argument`). لذلك هذا دليل تحليل صياغة ومسارات فقط، وليس تفعيلًا فعليًا لخدمات user manager أثناء جلسة رسومية.

## 10.3 الحزم وملفات سطح المكتب بعد الإصلاح

```text
package_lines=150 unique=150
window manager: ['openbox']
display manager: ['lightdm']
network manager: ['network-manager']
audio stack: ['pipewire-audio', 'pipewire-pulse', 'wireplumber']
```

هذا يثبت عدم وجود تكرار مباشر لأسماء الحزم الأساسية ضمن القائمة الساكنة، لا نجاح حلّ تبعيات apt. شجرة المصدر تحتوي `desktop/isox-welcome.desktop` واحدًا فقط، و`Exec=/usr/local/bin/isox-welcome`؛ سكربت البناء ينشئ اختصارات إضافية نصيًا، وقد راجعت الربط بينها وبين الحزم/الملفات التي ينسخها. لم تُفتح أي واجهة داخل صورة ISO غير مبنية.

إعدادات locale/keyboard/timezone موجودة نصيًا كما في قسم 6: `ar_IQ.UTF-8`, `en_US.UTF-8`, `XKBLAYOUT="us,ara"`, `grp:alt_shift_toggle`, و`Asia/Baghdad`. Firefox يحتوي الآن صفحة محلية محددة في مصدر البناء. لا توجد نتائج تشغيل فعلية للحسابات، sudo، Wi-Fi، صوت PipeWire، كاميرا أو طابعة قبل بناء الصورة.

## 10.4 الحواجز التي ما زالت تمنع بناء/إقلاع حقيقي

```text
$ apt-get update
Ign:1 http://deb.debian.org/debian trixie InRelease
Ign:2 http://deb.debian.org/debian trixie-updates InRelease
Ign:3 http://deb.debian.org/debian-security trixie-security InRelease
... تكررت Ign ثم أداة الطرفية أوقفت العملية بسبب timeout ...
```

لم أُجرِ تثبيت حزم لأن فهارس المستودعات لم تُجلب. لم يُشغّل ShellCheck:

```text
$ command -v shellcheck
shellcheck: MISSING
SHELLCHECK_EXIT=127
```

البناء عبر مدخل الجذر:

```text
$ ./build.sh
المتطلب غير موجود: lb
BUILD_GUARD_EXIT=3
```

QEMU:

```text
$ bash tests/qemu-acceptance.sh check
MISSING tool: xorriso
QEMU_CHECK_EXIT=2

$ bash tests/qemu-acceptance.sh bios
MISSING tool: qemu-system-x86_64
QEMU_BIOS_EXIT=2
```

لم يتم إنتاج `ISO-X-0.4.0-live-amd64.iso`، ولا توجد بصمة ISO، ولا سجلات/صور إقلاع BIOS أو UEFI، ولم تُختبر الواجهة أو الشبكة أو الصوت أو الطباعة أو المتصفح أو الإطفاء وإعادة التشغيل داخل نظام حي. لا تُصنّف هذه البنود Pass.

## 10.5 وضع دمج المصادر والرخص

- `docs/UPSTREAM_INTEGRATION_AR.md` يوضح أن الموجود حاليًا هو دمج توافقات انتقائي، وليس استيراد شجرتي `nodiscc/debian-live-config` و`OxyHQ/OxyOS` بالكامل. مصدر Debian Live Config مرخّص GPL-3.0 لكنه غير منسوخ بالكامل؛ لم تُحذف حقوقه. مستودع OxyOS الرئيسي الذي فُحص لم يعرض رخصة ضمن البيانات/الشجرة؛ لذلك لم تُنسخ منه شيفرة أو أصول. لا يمكن قانونيًا وصف شيفرته بأنها أصبحت «ملك ISO-X» بمجرد إعادة التسمية.
- `docs/THIRD_PARTY_LICENSES.md` سجل المصادر المعروفة وقواعد حفظ إشعارات حزم Debian. لا يدّعي اكتمال فهرس تراخيص كل حزمة نهائية؛ يلزم توليده من manifest حقيقي بعد بناء ISO.
- ميزتا Secure Boot وwatermark ليستا سلسلة إقلاع موثوقة كاملة: سكربت Secure Boot يتحقق من تطابق المفتاح والشهادة ولا يسجل MOK ولا يوقّع محمل الإقلاع. وسم XOR ليس تشفيرًا قويًا. هذان القيدان لم يتغيرا.

## 10.6 الحالة الحالية الصريحة

تم إصلاح العيوب المصدرية القابلة للتحقق التي ظهرت في هذه المرحلة، وأصبحت الاختبارات الساكنة النهائية ناجحة. تبقى المرحلة الحاسمة غير منفذة لأن بيئة التنفيذ لا تستطيع الوصول إلى Debian package repositories ولم تتوفر أدوات البناء/المحاكاة. يلزم مضيف Debian 13 Trixie amd64 مع إنترنت لتثبيت المتطلبات، ثم تشغيل `./build.sh` بمفتاح اختبار خارج مجلد المصدر، وتوثيق أخطاء البناء وإصلاحها قبل تجربة BIOS وUEFI. قائمة الاختبارات العملية في `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md`.

## 11. نتيجة التنفيذ الآلي الفعلي — 2026-10-20

- GitHub Actions run [`39471524581`](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/39471524581) نجح في تنظيف Runner وتثبيت متطلبات Debian Trixie amd64 وتشغيل فحوص المصدر، ثم نفذ `./build.sh` و`lb build` بنجاح.
- ISO الناتجة داخل Runner: `2,617,245,696` بايت؛ SHA-256: `989adb37d5b178f27951ac4ca3c9d4b8d9ae0c23862b585095411db32eda648b`. تحقق `sha256sum --check` و`xorriso` ناجحان.
- تقرير El Torito أثبت BIOS `/isolinux/isolinux.bin` وUEFI `/boot/grub/efi.img`. System Area أظهر MBR isohybrid وGPT/APM. وُجد `/live/filesystem.squashfs` وmanifest للحزم.
- إقلاع BIOS لم يبدأ: QEMU رفض `usb-tablet` لأن helper لم ينشئ USB bus، ثم خرج helper 10 لغياب سجل `graphical.target`. لم يُشغّل UEFI بسبب توقف التسلسل عند BIOS. لذلك لم يرفع Workflow ISO artifact؛ رفع diagnostics artifact `isox-build-diagnostics-39471524581` فقط.
- أصلح commit `842713c` هذا الخطأ بإضافة `qemu-xhci` وربط tablet به، وأضيف اختبار عقد محلي. ينتظر الإصلاح run جديداً؛ حتى ذلك الحين لا يُعد BIOS أو UEFI boot مقبولاً.
- الملف المرحلي كان داخل Runner المؤقت وانتهى عمره؛ لا رابط تنزيل ISO صالح حالياً، رغم أن ملفاً حقيقياً بُني وفُحص أثناء run.

## 12. تحديث تشخيص QEMU وتقسيم CI — 2026-10-20

هذا سجل للعمل المحلي بعد خط الأساس أعلاه؛ لا يغيّر أو يمحو تاريخ run `39471524581` ولا يدّعي الاطلاع على Artifact run `39474948006`. كان `HEAD` عند `caf58594bea006c983d45751f113dfe6ed8b89eb` والفرع `fix/isox-build-and-runtime` وقت إعداد السجل؛ حالة commit/push المذكورة هنا تخص تلك اللقطة السابقة.

### تغييرات مصدرية قيد التحقق

- `auto/config` و`scripts/build-iso.sh`: مسار `ISOX_CI_BOOT=1` منفصل، يزيل `quiet splash` ويضيف console VGA/serial وloglevel ومُعرّف CI وnonce فقط للنسخة التشخيصية. الإعداد العادي لا يضم خدمة probe.
- أضيف `scripts/isox-ci-ready.sh` وخدمة systemd/timer: marker لا يصدر إلا بعد أن يتحقق guest من target الرسومي وLightDM وXorg وجلسة `user` النشطة. لا يوجد دليل تشغيل حقيقي لهذه الخدمة حتى الآن.
- `tests/qemu-acceptance.sh` يستخدم `tests/qemu-runner.py` في headless. المشغّل يسجل serial وstdout/stderr منفصلين وQEMU version وأمر التشغيل والمسرّع وJSON، ويدير QMP لصور VGA، ويوقف QEMU عند marker مطابق أو timeout. الحالات لا تعتبر timeout نجاحاً.
- `tests/test_qemu_headless_validation.sh` صار يشغّل fake QEMU بحالات marker صحيح مبكر، marker مضلل، serial فارغ، timeout، وخطأ QEMU مباشر.
- workflow مقسّم إلى source-check/build/BIOS/UEFI/report. BIOS وUEFI وظيفتان منفصلتان لا تعتمد إحداهما على الأخرى، ويرفع build مرشحاً موسوماً CI diagnostic بعد فحصه الهيكلي والبصمة دون انتظار البوابتين. لا يسمى هذا المرشح إصداراً نهائياً؛ لا توجد بعد صورة عادية غير تشخيصية مؤهلة للنشر.
- actions مثبّتة إلى SHAs: checkout `v7.0.1`, upload-artifact `v7.0.2`, download-artifact `v8.0.2`؛ المصادر العامة للإصدارات تشير إلى Node.js 24.
- أضيف مولد تقرير machine-readable ومخطط JSON واختبار رفض JSON التالف. العدادات في التقرير تخص بوابات jobs الأربع، وليست مجموع حالات pytest الفردية؛ هذا معلن في `test_summary_unit`. USB Persistence تبقى غير منفذة.
- نُقل محتوى بناء الحاوية إلى `scripts/ci-build-in-trixie.sh` لتجنب اقتباسات shell متداخلة داخل workflow. وأُصلح sidecar ليحتوي basename نسبياً؛ الاسم المطلق `/workspace/...` الذي ينتجه container غير قابل للتحقق على runner host بعد نقل الملف.

### النتائج التي نُفذت محلياً بعد التغييرات

| الفحص | الرمز/النتيجة |
|---|---|
| `git diff --check` | 0، PASS. |
| `ruby`/Psych لتحليل `.github/workflows/iso-build.yml` | 0، صياغة YAML فقط. |
| `bash -n` على السكربتات المعدلة | 0، PASS. |
| `tests/test_qemu_headless_validation.sh` | 0، PASS لسيناريوهات fake QEMU؛ لا يقلع ISO. |
| `tests/test_ci_results.py` و`tests/test_workflow_contracts.py` | 0، PASS؛ فحص schema الأساسي وعقود workflow النصية. |
| `tests/smoke.sh` واختبارات المصدر/USB/Secure Boot/watermark/upstream/schema المنفذة مباشرة | 0، PASS؛ لا تثبت بناء أو تشغيل النظام. |
| `python3 -m pytest -p no:cacheprovider -q` | `12 passed in 2.60s`, exit 0؛ استخدم venv مؤقتاً في `/tmp` لأن pytest غير موجود على المضيف. |
| `systemd-analyze verify --root=<temp>` مع ملفات ExecStart staged | exit 0؛ صياغة الوحدة والمسارات اجتازت على rootfs مصطنع باستخدام أداة المضيف، وليس Debian Trixie rootfs حقيقياً. |
| `tests/smoke.sh` مع cache prefix مؤقت | exit 0؛ فحص `find` و`git status` بعده لم يظهر bytecode أو مخرجات اختبار داخل المستودع. |
| `gh auth status` | exit 1؛ لا تسجيل دخول، فلا يمكن dispatch أو مراقبة GitHub Actions من هذه البيئة. |

لم يُشغّل بناء ISO ولا QEMU ولا CI في هذه الجولة. الأدوات `qemu-system-x86_64`, `qemu-img`, `xorriso`, `shellcheck`, `desktop-file-validate`, و`actionlint` غير متوفرة على المضيف. لذلك لا توجد هنا نتائج BIOS/UEFI، ولا SHA لصورة جديدة، ولا Screenshots أو OVMF logs، ولا دليل على أن artifact workflow رُفع.

**تظل نتيجة run 39474948006 كما هي مثبتة في التكليف فقط:** QEMU انتهى بمهلة/exit 124 وملف serial فارغ. ملف Artifact لم يكن متاحاً للتنزيل (المحاولة السابقة أعادت 401، و`gh` الآن غير مصادق)، فلا يجوز تحديد bootloader/kernel/initramfs/GUI بوصفه السبب الجذري. يلزم ZIP تشخيص صالح أو صلاحية GitHub Actions، ثم تشغيل workflow على runner فعلي لإكمال التشخيص.

### متابعة التحقق بعد تصحيح عقد Workflow — 2026-10-20

- عُدّل اختبار العقد كي يختبر استدعاء جامع فحوص المصدر في وظيفة `source-check` واستهلاك `source-tests.json` في وظيفة ملخص القبول، بدلاً من اشتراط أن يظهر اسم الملف الناتج ضمن نص وظيفة المصدر نفسها.
- `pytest -p no:cacheprovider -q`: **12 passed**، exit 0. اختبارات عقود workflow وJSON وQEMU الوهمي نجحت منفردة أيضاً، كلٌ exit 0.
- شغّل `scripts/run-source-checks.py` المجموعة الكاملة: `30 PASS`, `0 FAIL`, و`2 NOT_RUN` (exit 1). الفحوص غير المنفذة هي `shellcheck` و`desktop-file-validate` لأن الأداتين غير موجودتين. ملفات الأدلة وpytest XML وملف JSON الناتج في `/tmp/isox-source-check-evidence-final2/`، وملفات bytecode في cache خارجي تحت `/tmp`.
- تحليل YAML، ترجمة Python النحوية، وفحص `git diff --check` نجحت؛ لم يُجر اختبار workflow على GitHub.
- في لقطة الفحص السابقة ظل `HEAD` والفرع كما هما ولم يكن قد حدث commit أو push. `gh auth status` exit 1 بسبب غياب المصادقة. لم يُنفّذ `lb build` أو QEMU، ولم تُنتج ISO أو سجل إقلاع جديد. لذلك تظل حالة تشغيل `39474948006` والسبب الجذري الدقيق غير محسومين.

### نتائج مراجعة كاملة إضافية — 2026-10-20

- أصلحت مراجعة المشغّل امتداد لقطات `screendump` إلى `.ppm` (بدلاً من `.png` غير المطابق لصيغة QEMU HMP)، وأزيل مفتاح JSON المكرر وبعض الشيفرة غير المستخدمة في `tests/qemu-runner.py`.
- عُدّل مولد نتائج القبول كي يرفض ISO size أو boot duration غير الرقمي وملف JSON المصدر غير object برسالة خطأ واضحة؛ أضيفت اختبارات رفض لهذه الحالات.
- عُرّف `CERT_IN` من `ISOX_RELEASE_CERT` في `scripts/build-iso.sh` وأضيف عقد اختبار. هذا يصلح استعمال متغير غير معرّف في المسار الاختياري، لكنه لا يثبت نجاح بناء watermark.
- بعد ذلك: pytest **12 passed**؛ مجمّع فحوص المصدر **30 PASS / 0 FAIL / 2 NOT_RUN** ورمزه 1 لأن `shellcheck` و`desktop-file-validate` غير متاحين. bash/sh syntax وPython compile وYAML و`xmllint` و`systemd-analyze verify` على rootfs مؤقت اجتازت. QEMU الحقيقي و`lb build` لم ينفذا.
- بقيت أدوات غير متاحة على المضيف: `shellcheck`, `desktop-file-validate`, `qemu-system-x86_64`, `qemu-img`, `xorriso`, `actionlint`. كما أن `gh auth status` exit 1؛ لم يُشغّل CI ولم تُرفع ملفات.
- راجعت مرجع GitHub الرسمي لمواصفات hosted runners في 2026-10-20: SSD القياسي 14 GB، وهو أقل من شرط البناء 20 GiB. أُعيدت خطوة تنظيف مسارات أدوات محددة وغير لازمة على VM المستضافة المؤقتة (`/usr/local/lib/android`, `/usr/share/dotnet`, `/opt/ghc`, `/usr/local/share/boost`, `/usr/local/share/chromium`, `/usr/local/share/powershell`) قبل قياس السعة؛ الاختبار الساكن يتحقق من وجودها وترتيبها، ولا يثبت مقدار المساحة الذي ستوفره أو نجاح البناء. المصدر: [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

### استئناف الإصلاح والتحقق — 2026-10-20

- الحالة عند الاستئناف: `HEAD=b5b444d56d14075743beb069ab6d92d2d316261f`، والفرع البعيد وفق `git ls-remote` كان `caf58594bea006c983d45751f113dfe6ed8b89eb`. تغييرات هذه الجولة محلية؛ لم يُستبدل commit سابق.
- عُولج تأخر readiness probe بإضافة `TimeoutStartSec=130s`، مع عقد اختبار يطابقها بمهلة probe ذات 120 ثانية.
- أُحكمت أدلة QEMU: عدم توفر QMP/لقطة VGA مبكرة يصنف كفشل بنية تحتية، لا يعاد استخدام ملفات PPM قديمة، والخروج غير الصفري بعد marker لا يمر كنجاح. أضيف اختبار fake-QEMU يستخدم QMP ويكتب PPM ويغطي marker متبوعاً بخروج 42.
- أدى تشغيل ShellCheck إلى كشف SC2054 في تعريف وسيطات USB؛ اقتُبست كل حجة device بشكل صحيح وحُدّث عقد الاختبار. اكتشف `actionlint` 1.7.12 لاحقاً SC2129 في تجميع مخرجات GitHub، فجمعت الكتابات في redirect واحد. اجتاز الفحصان بعد الإصلاح.
- تشغيل جامع الفحوص الأخير: **32 PASS، 0 FAIL، 0 NOT_RUN، exit 0**؛ pytest **12 passed**، smoke والاختبارات المحددة وفحوص bash/sh وPython وShellCheck وdesktop-file-validate وXML/SVG اجتازت. اجتاز `actionlint` وتحليل YAML، كما اجتاز `systemd-analyze verify --root=<temp>` بعد stage للوحدات والملفات التنفيذية الفعلية. لم تُنشأ bytecode داخل المستودع.
- لا يمكن بناء ISO هنا: المساحة المتاحة 19 GiB على filesystem workspace/Docker مقابل 20 GiB مطلوبة؛ لذا لم يبدأ `lb build`. لم يُجر إقلاع BIOS أو UEFI ولا توجد صورة/بصمة/artifact جديدة. لم يُشغّل USB writer ولم تُكتب بيانات على جهاز قرص حقيقي؛ نُفذت فحوص على ملفات مؤقتة في `/tmp`.
- `gh auth status` كان exit 1 عند التحقق؛ انتهت محاولة تسجيل الدخول الرسمية عبر الويب بـ`context deadline exceeded` قبل المصادقة. لا push ولا GitHub Actions run جديد؛ لا رابط run أو artifact للإبلاغ عنه. لم تُدرج بيانات اعتماد أو رمز جهاز. سبب run `39474948006` التاريخي ما زال غير محسوم.
