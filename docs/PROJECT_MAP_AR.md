# خريطة ISO-X 0.4.0 — حالة الفهم قبل أي إصلاح

## نطاق الدليل والحالة

- المستودع: `chatstaceysmart66-sys/ISO-X`، الفرع `fix/isox-build-and-runtime`.
- HEAD عند بدء القراءة: `caf58594bea006c983d45751f113dfe6ed8b89eb`؛ آخر السجل وقت القراءة: `caf5859`, `569b0d5`, `842713c`, `cca8531`, `34696ba`.
- كان العمل نظيفاً عند بدء المرحلة. أُنشئ ملفا المعرفة فقط، ولم يُعدّل مصدر أو إعداد بناء، ولم يُنفذ commit أو push أو بناء ISO.
- مرجع المصدر: 92 ملفاً متتبعاً، منها 87 نصياً قُرئت كاملةً و5 PNG فُحصت بياناتها فقط. التفصيل في [FILE_INVENTORY_AR.md](./FILE_INVENTORY_AR.md).
- أنشئت نسخة احتياطية خارج المستودع قبل التعديل: `/tmp/isox-stage0-backup/ISO-X-pre-change.tar.gz`؛ نجح فحص `tar -tzf`. بصمة SHA-256: `eda51357f9d106bbae46098f6fe7f4cebce2961dea5fcefb0ecdfc5cafffc7da`.
- ملف تشغيل CI المطلوب `39474948006` لم يتوفر محلياً. محاولة تنزيله عبر `gh run download 39474948006 -n isox-build-diagnostics-39474948006 -D /tmp/isox-ci-39474948006` انتهت بالرمز 4 مع رسالة `gh auth login` أو `GH_TOKEN`، ولم يوجد ملف ZIP محلي. لذلك لا أتعامل مع محتويات التشغيل كما وصفها نص الطلب على أنها سجل قرأته أو تحققت منه. يلزم توفير Artifact أو تهيئة وصول GitHub قبل حسم سبب فشل ذلك التشغيل.
- لا توجد ISO أو `build-live/` أو مجلد `evidence/` في الشجرة عند فحصها. المخرجات التاريخية في AUDIT/التقرير لا تعادل وجود ISO قابلة للفحص الآن.

## 1. الهوية والبنية

المشروع يبني ISO حيّة باسم ISO-X 0.4.0، هدفها Debian GNU/Linux 13 Trixie على amd64، مع Live system ومثبت Debian، Openbox وLightDM وواجهة GTK عربية/إنجليزية. واجهة الاستخدام في `app/iso_x_gtk.py`؛ التطبيق `app/iso_x_shell.py` نموذج Tkinter قديم لا ينسخه البناء ولا تحتوي قائمة الحزم على `python3-tk`. لذلك وجوده في المستودع لا يعني وجوده في الصورة.

الأجزاء المقصودة للصورة هي قائمة الحزم، واجهة GTK وApp Center والترحيب، سكربتات التشغيل، إعداد Openbox/tint2، صفحة Firefox، DB والترحيلات، وثائق محددة، الأصول، إعدادات النظام ووحدات systemd. لا تدخل الشجرة كلها إلى الصورة؛ ملفات الاختبار والتوثيق التاريخي وأدوات التطوير/التوقيع اليدوية ومصادر البناء ليست كلها staged.

لا توجد في المستودع صورة ISO ناتجة أو مجلد build صالح في الحالة الحالية. اسم ISO المقصود `ISO-X-0.4.0-live-amd64.iso`، ومخرجات SHA المقصودة sidecar بالاسم نفسه مع `.sha256`.

## 2. سلسلة البناء وملفات الصورة

1. `build.sh:1-4` يحدد جذر المشروع وينفذ `scripts/build-iso.sh`.
2. `scripts/build-iso.sh:2-77` يفرض root، Debian/Trixie (مع سماح مضبوط لمضيف CI مختلف)، amd64، 20 GiB مساحة حرة و4 GiB RAM، ووجود `lb`, `xorriso`, `debootstrap`, `mksquashfs`, `openssl`. يرفض build dir غير فارغ وISO/sidecar سابقة كي لا يخلط نواتج.
3. `scripts/build-iso.sh:83-104` يجعل مشهد Bevy اختيارياً بـ `ISOX_BUILD_CINEMATIC=1`؛ غياب Rust أو الخط يخرجه من الصورة مع تحذير.
4. `scripts/build-iso.sh:130-137` ينشئ build dir وسجل البناء ويستدعي `auto/config`. إعداد live-build في `auto/config:5-35` يستخدم `lb config noauto`، Debian Trixie، amd64، `iso-hybrid`، syslinux وgrub-efi، live-boot، Debian installer، firmware، وحزم المصدر.
5. `scripts/build-iso.sh:140-150` يجهز staging وقائمة الحزم. إعداد الماء/التوقيع الاختياري يعمل فقط مع `ISOX_ENABLE_WATERMARK=1`: يضيف build-essential وlinux-headers، ويجهز ملفات المفتاح والشهادة وinitramfs hooks. كان `CERT_IN` مستخدماً دون تعريف؛ أُصلح في مراجعة 2026-10-20 بربطه بـ`ISOX_RELEASE_CERT`، لكن المسار الاختياري لم يُبنَ فعلياً بعد.
6. `scripts/build-iso.sh:154-217` ينسخ البرنامج والوثائق وقاعدة البيانات والأصول والخدمات وhooks وملفات Openbox إلى `build-live/config/`. التفاصيل:
   - التطبيقات الثلاثة GTK وصفحة البدء وDB/migrations إلى `/usr/share/iso-x/` و`/usr/share/iso-x/db/`.
   - الوثائق المنقولة: README الإنجليزي والعربي، THIRD_PARTY_NOTICES، THIRD_PARTY_LICENSES، UPSTREAM_INTEGRATION، ARCHITECTURE، BUILD_AND_TEST_RESULTS، HARDWARE_ACCEPTANCE_CHECKLIST، UPSTREAM_REVIEW، تحت `/usr/share/doc/iso-x/`.
   - `isox-speedtest`, `isox-write-usb`, `isox-run`, `isox-welcome`, `isox-snap-window`, `isox-toggle-airplane`, `isox-vault`, `apply-windows-look`, وملفا preload وzram إلى مسارات `/usr/local/bin`, `/usr/local/sbin`, و`/usr/share/iso-x/` المحددة في أوامر `install`.
   - PNG/SVG للشعار والإقلاع والخلفية إلى `/usr/share/iso-x/assets`, `/usr/share/backgrounds/iso-x`, وأيقونة scalable؛ Plymouth assets تُنسخ إلى assets ثم يستخدمها hook `0200`.
   - إعداد Openbox/tint2 إلى `/etc/xdg/openbox`, `/etc/skel/.config/openbox`, `/etc/skel/.config/tint2`, `/etc/iso-x`. ينشئ السكربت desktop entries وملفات locale/keyboard/timezone/environment ويولّد autostart بدلاً من وجود autostart مصدري مستقل.
   - watermark source/hook/initramfs لا تُنسخ إلا مع الخيار أعلاه. ملفات `kernel/isox-watermark/dkms.conf` و`watermark_bytes.h` ليست ضمن أوامر النسخ المباشر.
   - Bevy executable/assets لا تُنسخ إلا إذا بُني الثنائي ووجد خط عربي مناسب.
7. ترتيب أسماء hooks المنسوخة إلى `config/hooks/live/`: `0050-isox-locales`, ثم `0200-isox-plymouth`, `0300-isox-services`, `0400-isox-firefox-defaults`. `0100-isox-watermark` يدخل بينهما فقط عند تفعيل watermark. هذا ترتيب أسماء hooks؛ لم يتوفر log حديث يثبت ترتيب التنفيذ داخل run المطلوب.
8. `scripts/build-iso.sh:401-410` ينفذ `lb build`, يتحقق من وجود ISO، يمرر فحص `xorriso -pvd_info`, ينسخ ISO إلى جذر المشروع، وينشئ ويتحقق من SHA-256 sidecar. في هذا الطلب لم ينفذ البناء.

لا ينسخ البناء `app/iso_x_shell.py` أو اختبارات `tests/` أو `AUDIT.md` أو `CHANGELOG.md` أو `STATUS_AR.md` أو كل الوثائق التاريخية، ولا ينسخ أدوات جمع الأداء/تسجيل العرض/التحقق اليدوي Secure Boot. لا ينسخ إعدادات المصدر إلى `/etc` كما هي؛ hooks وأوامر staging تنتج إعدادات داخل rootfs.

## 3. ترتيب hooks وأثرها

| الترتيب الاسمي | hook | الأثر في chroot |
|---|---|---|
| 0050 | `config/hooks/live/0050-isox-locales.hook.chroot` | توليد locales وضبط ar_IQ الافتراضي. |
| 0100 (اختياري) | `config/hooks/live/0100-isox-watermark.hook.chroot` | بناء وحدة watermark وتوقيعها وتحديث initramfs؛ يتطلب مواد سرية ورؤوس نواة عند تفعيل الخيار. |
| 0200 | `config/hooks/live/0200-isox-plymouth.hook.chroot` | تثبيت/اختيار theme ISO-X ثم تحديث initramfs. |
| 0300 | `config/hooks/live/0300-isox-services.hook.chroot` | ضبط NetworkManager وLightDM greeter، enable NetworkManager وBluetooth، ومحاولة enable لـ `cups.socket` دون فشل إذا لم يتوفر. |
| 0400 | `config/hooks/live/0400-isox-firefox-defaults.hook.chroot` | وضع صفحة بدء محلية كإعداد Firefox ESR الافتراضي. |

المصدر الفعلي لتمكين الوحدات الإضافية: `scripts/build-iso.sh:205-217` يضيف symlink لـ`isox-zram.service` إلى `multi-user.target.wants`، ويضع preload timer للمستخدم في skeleton. لم يُثبت هذا أن خدمات systemd تعمل في ISO فعلية.

## 4. مسار الإقلاع والدخول والجلسة

- مصدر الإعداد يقول `--binary-images iso-hybrid` و`--bootloaders "syslinux grub-efi"` في `auto/config:14-16`. هذا اختيار بناء فقط، وليس إثباتاً على مدخل BIOS/UEFI داخل ISO الناتجة.
- معاملات live الدائمة المصدرية في `auto/config:32`: `boot=live config components quiet splash username=user hostname=iso-x console=ttyS0,115200n8 systemd.show_status=yes systemd.log_target=console`. معاملات failsafe في السطر 33: `boot=live components username=user hostname=iso-x nomodeset noapic noacpi nosmp noapm nodma nomce nosplash`.
- لا توجد ملفات isolinux أو grub.cfg في source tracked. لذلك القيم النهائية التي تم توليدها داخل ISO، timeout/prompt لقائمة BIOS، إعداد GRUB، أسماء kernel/initrd وملفات EFI غير معروفة دون Artifact ISO.
- لا يصح استنتاج H1 (قائمة BIOS تنتظر إدخالاً إلى ما لا نهاية) من المصدر المتاح؛ يلزم استخراج `/isolinux/*` و`/boot/grub/*` من ISO المعنية. وبالمثل لا يصح استنتاج نجاح أو فشل Secure Boot من خيار live-build فقط.
- قائمة الحزم تتضمن `live-boot`, `live-config`, `live-config-systemd`, `lightdm`, `lightdm-gtk-greeter`, و`systemd-sysv` (`config/package-lists/iso-x.list.chroot:8-19`). `username=user` في bootappend، وhook يهيئ greeter artwork فقط؛ لا يحدد المصدر كلمة مرور أو إعداد LightDM autologin صريحاً. المستخدم الفعلي، صلاحيات sudo، طريقة autologin، وتسلسل PAM تحتاج قراءة rootfs/اختبار إقلاع.
- خدمة LightDM مثبتة كحزمة، لكن hook لا ينفذ `systemctl enable lightdm` صراحة. ما إذا كان package maintainer/live-config يفعّلها في image غير متحقق منه هنا.
- zram خدمة system-level مفعلة عبر symlink. `isox-preload.timer` يُضاف لحسابات skeleton ليبدأ بعد تسجيل الدخول، والبرنامج لا يعمل إلا إذا وافق المستخدم من إعدادات ISO-X.
- `scripts/build-iso.sh:359-397` يولد Openbox autostart: PCManFM desktop، tint2، nm-applet، blueman-applet، volumeicon، xfce4-power-manager، lxpolkit، IBus ثم `exec /usr/local/bin/iso-x`. هذه البرامج تُشغّل عند فتح جلسة Openbox؛ لم يُثبت دخول مستخدم حي أو ظهور Xorg فعلياً.
- إعداد plymouth/theme موجود في hooks، لكن لا يثبت ظهور splash أو تسلسل الانتقال الرسومي.

## 5. خريطة الحزم والميزات

`config/package-lists/iso-x.list.chroot` يحتوي 154 سطراً فعلياً: 146 إدخال حزمة غير فارغ وغير تعليق، وكلها فريدة في فحص المصدر الحالي. هذا يختلف عن AUDIT التاريخي الذي يذكر 150 اسماً؛ تُقدّم القائمة الحالية ويُسجل اختلاف العد بدلاً من نقل الرقم القديم. تشمل الحزم Linux/live-boot، Xorg/Openbox/LightDM، GTK/Python، شبكة وBluetooth، PipeWire، طباعة وfirmware، ملفات/إعدادات XFCE، Firefox ESR وNetSurf، LibreOffice، VLC، GIMP، Thunderbird، FileZilla وأدوات النظام.

- `galculator` موجود صراحةً في القائمة عند السطر 133؛ لذا ادعاء غياب الآلة الحاسبة في وصف التشغيل 39474948006 (إن كان موجوداً كما جاء في prompt) غير مثبت من المصدر، ويجب حسمه من installed-packages.txt الخاص بذلك التشغيل.
- `xfce4-screenshooter` موجود عند 134، لكن لا تظهر حزمة تسجيل شاشة أو `ffmpeg` في القائمة؛ `scripts/record-demo.sh` يعتمد عليهما لكنه غير منسوخ.
- `scripts/isox-snap-window.sh` يستدعي `xrandr` و`wmctrl`؛ `wmctrl` موجود عند 154، ولا يظهر `x11-xserver-utils` الذي يوفر عادةً xrandr ضمن القائمة، فيلزم فحص binary manifest قبل تأكيد عمل الاختصار.
- `arandr`, `qemu-guest-agent`, و`zstd` لا تظهر في القائمة. لا يوجد اختبار تثبيت لهذه الأدوات ضمن هذه القراءة.
- `hplip` موجود عند السطر 59، وتعريفات `xserver-xorg-video-intel/amdgpu/radeon/nouveau/vesa/fbdev` في 67-72. لا يُستنتج عطل رسومي منها دون تجربة على ISO وعتاد.
- `--apt-indices false` في `auto/config:8`: مركز التطبيقات يعتمد على تحديث apt index قبل التثبيت. التطبيقات المثبتة مسبقاً في القائمة والكتالوج قد تتكرر؛ ذلك ليس خطأ بالضرورة لكنه يقلل جدوى بعض عناصر App Center.
- `python3-tk` غير موجود؛ Tkinter source لا يدخل الصورة أصلاً.
- `netsurf-gtk` موجود، لكن `scripts/isox-preload.py` وواجهة الترحيب تستخدم أسماء أوامر NetSurf. اسم الحزمة لا يكفي لإثبات اسم executable في filesystem الناتج؛ manifest هو الفيصل.
- نُفذ `apt-cache policy` على جميع أسماء القائمة من المضيف الحالي، لكنه Ubuntu 24.04 Noble وليس Trixie؛ معظم الأسماء أعادت `NO LOCAL POLICY DATA`، وبعض الحزم أعادت candidate من Ubuntu أو `(none)`. هذه النتيجة لا تثبت وجود الحزمة أو غيابها في Debian Trixie، لذلك صلاحية resolver في الهدف غير محسومة.

## 6. الواجهة والأوامر

- القائمة في `desktop/openbox-menu.xml:4-17` تطلق الترحيب، GTK shell، installer، Firefox، Thunar، XFCE terminal، App Center، run command، airplane toggle، vault، settings، و`dm-tool lock`.
- اختصارات `desktop/openbox-rc.xml:12-24`: `W` للقائمة؛ `W-e` مدير الملفات؛ `W-w` ترحيب؛ `W-r` تشغيل أمر؛ `W-d` إظهار سطح المكتب؛ `W-l` قفل؛ `W-a` وضع الطيران؛ `Ctrl-W-Escape` مدير المهام؛ `W-i` الإعدادات؛ `Print` لقطة؛ `W-Return` طرفية؛ `W-Left/Right` snap.
- قائمة Secure Vault تشغّل `xterm -e /usr/local/bin/isox-vault` دون `enc|dec` أو مسارات، بينما wrapper يمرر المعاملات ويعرض usage عند النقص؛ بالتالي هذا العنصر لا يبدأ عملية مفيدة دون وسيطات. مطلوب تعديل تجربة الاستخدام إذا قرر المستخدم ذلك.
- اختصارا snap يطلقان سكربت يعتمد على xrandr؛ توفره في image غير مؤكد من القائمة. صلاحية `W`، أحداث Openbox، وتوفر `dm-tool`/`xfce4-settings-manager` داخل الصورة تحتاج تحقق executable أو إقلاعاً.
- `app/isox_welcome.py` يوفر واجهة ترحيب وأزرارًا تفحص الأوامر. `app/isox_appcenter.py` يعرض كتالوج حزم ويستخدم pkexec/apt. `app/iso_x_gtk.py` هي واجهة النظام الأساسية؛ لا توجد اختبارات GTK تفاعلية في المصدر.
- أوامر desktop التي يولدها البناء تتضمن `iso-x`, `debian-installer-launcher`, `isox-run`, `isox-toggle-airplane`, `thunar`, `nm-connection-editor`، وروابط Home/Trash/Network. التحقق الفعلي من كل Exec في rootfs/ISO غير متاح دون بناء.

## 7. قاعدة البيانات

`db/schema.sql` يعرّف: `schema_migrations`, `users`, `app_registry`, `installed_app_permissions`, `fs_index`, `perf_logs`, `sys_snapshots`, `dev_envs`, `privacy_settings`, `kernel_watermark`, `local_app_usage`، إضافة إلى فهارس وtriggers. لا يخزن كلمات مرور نظام وفق التعليق/المخطط؛ PAM ومدير الدخول مسؤولان عنها.

- `app/iso_x_gtk.py` يحتوي واجهة Store محلية، يهيئ schema، يجري migrations ويقرأ/يكتب إعدادات الخصوصية واستخدام التطبيقات وعلامة watermark.
- `scripts/isox-preload.py` يقرأ موافقة preload قبل أي عمل، ويعمل كـ no-op عند الإيقاف؛ الخدمة timer ليست telemetry ولا تطلق تطبيقات تلقائياً في الوضع الافتراضي.
- Tkinter القديم يشير إلى استخدام مختلف لقاعدة البيانات، لكنه لا يدخل الصورة حسب أوامر النسخ.
- لا يظهر استهلاك واضح لجداول `users`, `installed_app_permissions`, `fs_index`, `sys_snapshots`, `dev_envs` في مسارات GTK المقروءة؛ `perf_logs` له استعمال legacy. هذا يعني عدم الاستخدام في المسارات المقروءة، وليس إثبات عدم وجود كل مرجع نصي بالمشروع.
- migrations 002/003/004 موجودة وتُنسخ جميعاً إلى مسار DB حسب `scripts/build-iso.sh:163-165`; `004` يسجل version فقط. `tests/test_schema.py` لا يغطي كل migration/ترحيل upgrade فعلي للنظام الحي.

## 8. الاختبارات وحدود ما تثبته

- `tests/test_schema.py`: سلوك schema/trigger/بيانات DB المحددة؛ لا يثبت GUI.
- `tests/test_secure_vault.py`: roundtrip وتلف/كلمة مرور؛ لا يقيس واجهة GTK أو ملفات ضخمة.
- `tests/test_build_contracts.py`, `tests/test_source_config.py`, `tests/test_upstream_integration.py`: عقود نصية ومسارات/تكوين/ربط؛ لا تنفذ `lb build` ولا تثبت برامج image.
- اختبارات shell للـ watermark وSecure Boot تستخدم مفاتيح/بيانات fixture؛ لا تثبت boot chain موثوقة أو MOK.
- `tests/test_write_usb_validation.sh` يرفض ISO ذات hash خاطئ باستخدام أدوات وهمية؛ لا يكتب وسيطاً ولا يختبر partition/persistence.
- `tests/test_qemu_headless_validation.sh` يختبر كاشفاً سلبياً فقط، وليس تشغيل ISO.
- `tests/qemu-acceptance.sh` headless يستخدم `timeout` ثم يفحص serial بحثاً عن نص graphical.target؛ لا يلتقط الشاشة ولا يملك guest marker أو إيقافاً مبكراً عند النجاح. لذلك serial الفارغ لا يبين أين توقف النظام.
- الاختبارات المصدرية التاريخية في AUDIT تسجل نجاحات مختلفة عبر تواريخ/بيئات، كما تسجل محاولة pytest فاشلة عند غياب الحزمة في مضيف آخر. يجب إعادة الاختبارات الحالية لتقديم نتائج الجولة الحالية.
- لا توجد اختبارات حالية تثبت persistence، BIOS boot، UEFI boot، Secure Boot chain، الوصول لسطح المكتب، تثبيت تطبيق عبر الإنترنت، shutdown/reboot، أو الكتابة إلى صورة قرص افتراضية.

## 9. CI وArtifacts

`.github/workflows/iso-build.yml` يشغل push على الفرع و`workflow_dispatch`، ويستخدم Ubuntu 24.04 ثم Docker `debian:trixie`. خطوة داخل الحاوية تتحقق من الموارد، تثبت أدوات البناء، تشغل smoke/pytest وفحوص shell/XML/desktop/systemd، ثم `./build.sh`، checksum وxorriso، manifest الحزم، وفحص BIOS ثم UEFI.

- البناء والفحص وBIOS وUEFI جميعها داخل خطوة Docker طويلة واحدة. `set -Eeuo pipefail` يجعل فشل اختبار BIOS ينهي الأمر قبل UEFI.
- الحاوية تربط workspace، لذا الملف/الأدلة التي كُتبت قبل فشل QEMU تبقى في مساحة runner؛ لكنها لا تضمن artifact ISO.
- diagnostics تُرفع بـ`if: always()` إلى `isox-build-diagnostics-${run_id}`؛ الـ ISO ترفع فقط عند `success()` باسم ثابت. فشل BIOS يمنع رفع الصورة رغم نجاح build/preflight.
- لا يوجد `results.json` أو علامة `iso-validated.ok` في workflow الحالي. لا يوجد فصل بين artifact candidate وartifact release verified.
- أسماء Actions هي `actions/checkout@v4` و`actions/upload-artifact@v4`. لم أتحقق من صفحات الإصدارات الرسمية الحالية أو صلاحية runner لـNode 24 خلال هذه المرحلة.
- AUDIT و`docs/BUILD_AND_TEST_RESULTS_AR.md` يذكران التشغيل التاريخي `39471524581` وبصمة `989adb37d5b178f27951ac4ca3c9d4b8d9ae0c23862b585095411db32eda648b`. المطلوب `39474948006` لم يُقرأ Artifact الخاص به؛ لا أستبدل البصمة أو أصفها بأنها الأحدث دون الدليل.

## 10. الأمان والتراخيص

- `scripts/generate-dev-signing-key.sh` يولد مفتاحاً وشهادة تطوير؛ `scripts/build-iso.sh` مصمم لتلقيهما عبر متغيرات بيئة/مسارات خارج المستودع، وstaging الخاص بالمفتاح بصلاحية 0600 مع cleanup. لا يوجد مفتاح خاص ضمن الملفات المتتبعة التي جُردت. السر الذي يجب ألا يدخل Git أو artifact أو السجل هو مفتاح التوقيع الخاص (`ISOX_RELEASE_KEY`/ملف key).
- غياب `CERT_IN` الذي كان يعطل مسار watermark اختياري عولج في تعديل محلي بتاريخ 2026-10-20، واختبار عقده يجتاز؛ ما زال يلزم بناء فعلي للمسار بمفتاح/شهادة اختبارية.
- watermark اختيارية في بناء المصدر الحالي ولا تشارك في الإقلاع الافتراضي؛ XOR في watermark ليس تشفيراً، وSQLite triggers ليست حماية من root.
- `scripts/secureboot-enroll.sh` يتحقق من تطابق المفتاح والشهادة فقط؛ لا يسجل MOK ولا يثبت تفعيل Secure Boot. لا يجوز وصفها بأنها Secure Boot كامل.
- `sudo` حزمة موجودة، لكن المصدر لا يكفي لإثبات مجموعة صلاحيات مستخدم live أو كلمة مروره. لا تسجل DB كلمات مرور.
- الرخص الخارجية محددة في مستندات النسب؛ `LICENSE.txt` المحلي قصير وغير شامل لرخص حزم Debian. `Cargo.toml` يعلن GPL-3.0-or-later. لا توجد فهرسة licenses نهائية من manifest ISO في الحالة الحالية.

## 11. التناقضات والعيوب الظاهرة التي تحتاج ربطاً أو إصلاحاً

1. في baseline الموثق كان إعداد console/quiet مشتركاً بين المنتج والتشخيص؛ أصبح `auto/config` الحالي يفصل معاملات verbose وnonce إلى `ISOX_CI_BOOT=1`، مع بقاء بناء/اختبار النسخة التشخيصية الفعلية غير منفذ.
2. كان `CERT_IN` مستعملاً دون تعريف في `scripts/build-iso.sh`؛ أضيف تعريفه بـ`ISOX_RELEASE_CERT` في تعديل 2026-10-20، ولم يُثبت تفعيل watermark ببناء فعلي.
3. Vault menu لا يمرر معاملات مطلوبة: `desktop/openbox-menu.xml:14`.
4. snap يعتمد `xrandr` و`wmctrl`: `scripts/isox-snap-window.sh:4-10`; القائمة تعلن wmctrl فقط ولا تظهر x11-xserver-utils.
5. `--apt-indices false` في `auto/config:8` يفرض تنزيل فهارس قبل استخدام App Center، والاتصال الشبكي لازم لتثبيت الحزم.
6. `README.md` يذكر مجلد `security/` في شجرة غير موجودة؛ `README_AR.md` يكرر ذكر migration 004 ويصف تثبيت Rust بما لا يطابق سكربت dependencies الحالي.
7. `docs/RELEASE_NOTES_0.3.0_AR.md` يصوغ persistence كميزة بينما `scripts/write-usb.sh` يرفضها صراحة.
8. مستند AUDIT يحوي baseline قديم قبل إصلاح `--bootloaders` وmigration 004 وwatermark، ثم sections أحدث تصححه. يجب قراءة section الأحدث وعدم اقتباس القديم كحالة حاضرة.
9. التقرير القديم `BUILD_AND_TEST_RESULTS_AR.md` يربط hash `989adb...` بتشغيل 39471524581؛ لا يوجد دليل محلي للتشغيل المطلوب 39474948006.
10. القائمة تحتوي `galculator` رغم ملاحظة التشغيل التاريخية التي تقول غياب الآلة الحاسبة؛ هذا تناقض بين source وmanifest المطلوب، لا نفي لواحد منهما.
11. الاختبارات القديمة لا تلتقط VGA ولا تثبت نجاح GUI؛ المسار المحلي الجديد يلتقط عبر QMP ويتطلب marker من الضيف، واختبار fake-QEMU يغطي الكشف فقط. لم تُشغّل workflow الجديدة أو QEMU الحقيقي بعد، لذلك لا يوجد إثبات بصري/إقلاع واقعي.

## 12. سجل الحالة التشغيلية المتاح وحدود المعرفة

| السؤال | ما يثبته المصدر/السجلات المقروءة | غير المحسوم |
|---|---|---|
| معاملات النواة النهائية؟ | المصدر أعلاه في `auto/config:32-33`. | قيم isolinux وGRUB داخل ISO التشغيل 39474948006؛ لم يستخرج Artifact. |
| hooks وترتيبها؟ | أسماء وترتيب staging مذكورة في القسم 3؛ watermark مشروط. | ترتيب live-build الفعلي في build log الحالي. |
| الخدمات وautostart؟ | NM/Bluetooth/CUPS conditional؛ zram symlink؛ user timer؛ Openbox autostart. | حالة enable النهائية في filesystem وأثر user manager/runtime. |
| ما يدخل ISO؟ | أوامر `install` و`cat` و`ln` في build script تحدد مقاصد staging. | إثبات الوجود الفعلي في ISO وmanifest هذا التشغيل. |
| أين وكيف autologin؟ | `username=user` وإعداد live-config بالحزم. | مستخدم حي فعلي، طريقة تسجيل الدخول، sudoers، حالة LightDM في صورة محددة. |
| هل بدأ BIOS/UEFI/GUI؟ | التقرير التاريخي الأقدم يوثق بناء ISO لكنه لا يثبت إقلاعاً ناجحاً؛ وصف run المطلوب لا يمكن تدقيقه دون الملفات. | كل بوابة في التشغيل 39474948006، بما في ذلك هل توقف عند boot menu أو النواة أو GUI. |
| هل قائمة BIOS تنتظر؟ | لا ملف menu مصدر هنا. | `timeout` و`prompt` الفعليان في ISO؛ H1 غير محسومة. |
| ما هو Secure Boot؟ | config يطلب bootloaders؛ المساعد local validation-only. | shim/GRUB الموقع والمفاتيح داخل ISO، وحالة Secure Boot الفعلية. |
| ما الذي يمنع build الحالي؟ | build guard يفرض موارد وأدوات ويحتاج Debian Trixie/amd64 حسب source. | موارد runner وأول خطأ حقيقي في run 39474948006 دون سجلاته. |
| ما التطبيق المتاح؟ | الحزم المعلنة والملفات التي ينوي البناء تثبيتها. | binaries الفعلية داخل image، خصوصاً `xrandr`/NetSurf، وبدء GUI. |

سبب فشل التشغيل 39474948006 غير محسوم من الأدلة التي قرأتها. وصف المستخدم يشير إلى QEMU timeout وسجل serial فارغ، لكنه لا يثبت هل لم تبدأ الآلة أو توقفت عند boot menu أو أقلعت دون قناة serial. فرضية timeout/prompt BIOS، وغياب kernel console الفعلي، وغياب guest success marker، وأعطال initramfs/systemd/GUI تظل احتمالات؛ لا أختار سبباً مثبتاً قبل استخراج config وlogs من الـ Artifact.

## 13. تحقق المرحلة صفر المنفذ في هذه الجولة

كل الأوامر التالية تخص مصدر/اختبارات؛ لم يُشغّل `lb build` أو QEMU، ولم تُنتج ISO.

| الأمر | النتيجة الفعلية |
|---|---|
| `git status --short --branch` | الفرع `fix/isox-build-and-runtime`؛ بعد الإنشاء يظهر الملفان الجديدان فقط في `docs/`. |
| `git rev-parse HEAD` | `caf58594bea006c983d45751f113dfe6ed8b89eb`. |
| `git log -5 --oneline` | بدأ بـ`caf5859`, `569b0d5`, `842713c`, `cca8531`, `34696ba`. |
| `git diff --check` | exit 0؛ لا أخطاء whitespace في الفروقات المتتبعة. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/isox-stage0-pycache PYTHONPATH=/tmp/isox-stage0-pydeps python3 -m pytest -p no:cacheprovider -q` | بعد تثبيت pytest مؤقتاً خارج repo: `12 passed in 2.70s`, exit 0. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/isox-stage0-pycache bash tests/smoke.sh` | كل رسائل PASS، exit 0؛ تنص الرسالة الأخيرة أن هذا لا يثبت بناء ISO أو إقلاعها. |
| `python3 tests/test_build_contracts.py` | PASS، exit 0. |
| `python3 tests/test_source_config.py` | PASS، exit 0. |
| `python3 tests/test_secure_vault.py` | PASS، exit 0. |
| `bash tests/test_write_usb_validation.sh` | PASS، exit 0؛ لم يكتب على قرص فعلي. |
| `bash tests/test_qemu_headless_validation.sh` | PASS، exit 0؛ كاشف سلبي فقط وليس اختبار إقلاع. |
| `bash -n` لكل `.sh`, `auto/config`, hooks و`sh -n` لسكريبتَي initramfs | exit 0. |
| `python3 -m py_compile` لكل 13 ملف Python tracked مع cache prefix خارجي | exit 0. |
| `xmllint --noout desktop/openbox-menu.xml desktop/openbox-rc.xml assets/*.svg` | exit 0. |
| `desktop-file-validate desktop/*.desktop` | لم ينفذ؛ الأداة غير مثبتة. |
| `systemd-analyze verify systemd/*` على المضيف | exit 1: ملفات ExecStart غير موجودة على المضيف (`/usr/local/bin/isox-preload`, `/usr/local/sbin/isox-zram-setup`)، كما ظهرت تحذيرات world-writable على نسخ الوحدات بالمضيف. |
| `systemd-analyze verify --root=<tmp>` بعد وضع الوحدات وtargets وملفات تنفيذية placeholder في root مؤقت | exit 0؛ يثبت تحليل الصياغة والمسارات في rootfs اصطناعي فقط، لا سلوك الخدمة الفعلي. |
| فحص `apt-cache policy` لكل 146 حزمة | المضيف `ubuntu noble`، وليس Debian Trixie؛ لا يمكن اعتباره تحققاً من مستودع الهدف. |
| فحص Host PATH لأوامر Openbox وdesktop | 12 أمر/launcher غير موجود على المضيف؛ الفحص غير صالح للحكم على صورة Debian التي لم تُبنَ، وكثير منها مولّد أو مثبت بالحزم. |
| `actionlint`, `qemu-system-x86_64`, `qemu-img`, `xorriso`, `desktop-file-validate` | غير مثبتة/غير موجودة في PATH؛ `/dev/kvm` موجود لكن لا يوجد QEMU لإجراء تجربة. |
| تنزيل Artifact عبر `gh run download ...` | exit 4؛ CLI يطلب `gh auth login` أو `GH_TOKEN`. |

لم تُجرَ محاولة إقلاع، ولم تُفحص قائمة BIOS/GRUB أو EFI/Secure Boot داخل صورة run المطلوبة. الفحوص التي لم تتوفر أدواتها أو الـ Artifact الخاص بها بقيت صراحةً غير محسومة.

### فحوص إضافية للربط والمسارات

- فحص آلي مؤقت من stdin لمسارات الكتابة الساكنة في `scripts/build-iso.sh` تعرّف على 86 هدف كتابة و29 إعلان mkdir/install-D؛ النتيجة `missing_parent_before_write=0`، exit 0. هذه مطابقة ساكنة للمصدر وليست تشغيل build أو اختبار المسارات تحت كل الفروع والبيئات.
- فحص قائمة الحزم في المصدر: `package_entries=146 unique=146 duplicates=[]`. فحص SHA-256 لجميع الملفات المتتبعة: `exact_duplicate_content_groups=0`.
- فحص Host PATH للعناصر في قائمة Openbox وdesktop وجد 12 أمر/launcher غائباً على مضيف Ubuntu. لا يُعامل ذلك كفشل للصورة لأن المضيف ليس ISO-X وقد تنشأ launchers أثناء البناء. المرجع غير العامل المحدد من المصدر هو Vault menu بلا معاملات، وغياب x11-xserver-utils من قائمة الحزم رغم اعتماد snap على xrandr؛ يلزم فحص rootfs/ISO.
- `/dev/kvm` موجود لكن الاختبار `test -r /dev/kvm && test -w /dev/kvm` انتهى exit 1 للمستخدم الحالي؛ لا يمكنه استخدام KVM هنا. إضافة إلى عدم وجود `qemu-system-x86_64` وOVMF، لم يُجر أي QEMU.
- لا توجد نسخ مكررة بايتياً بين الملفات الـ92 بحسب SHA-256؛ وجود PNG/SVG المتقابل مقصود لا تكرار محتوى.

## تحديث تشخيص QEMU وCI — 2026-10-20

هذا تحديث لنسخة العمل على الفرع `fix/isox-build-and-runtime` عند الأساس `caf58594bea006c983d45751f113dfe6ed8b89eb`، وليس نتيجة run GitHub جديد. الملفات المعدلة/المضافة ما زالت محلية وغير ملتزمة.

### ما تغير في المصدر

- أضيف مسار build تشخيصي صريح عبر `ISOX_CI_BOOT=1` وnonce hex فريد. `auto/config` يزيل `quiet splash` ويضيف `console=tty0`, `console=ttyS0`, `loglevel=7`, `systemd.show_status=yes`, `systemd.log_target=console`, ووسيطَي `isox.ci=1` و`isox.ci.nonce=...` في نسخة CI فقط؛ إعداد الإصدار العادي لم يتغير.
- ينسخ `scripts/build-iso.sh` probe ووحدة/timer داخل staging فقط عند تفعيل هذا المسار. المؤشر الضيف ينتظر target الرسومي وLightDM وXorg وجلسة المستخدم `user` الفعلية النشطة قبل طباعة `ISOX_CI_READY nonce=...` إلى serial/console. لم يُثبت بعد تشغيل الوحدة داخل rootfs أو وصول marker من Linux حقيقي.
- يعيد `tests/qemu-acceptance.sh` توجيه BIOS/UEFI headless إلى `tests/qemu-runner.py`. المشغّل يفصل stdout عن stderr، يسجل serial وQEMU version وأمر التشغيل والمسرّع، يلتقط VGA عبر QMP، يراقب marker المطابق، ينهي QEMU مبكراً عند نجاحه، ويكتب JSON بحالة محددة. لا يدّعي النجاح من timeout أو نص `graphical.target` وحده.
- أضيف `scripts/ci-build-in-trixie.sh` لتجنب quoting متداخل داخل Docker، وليبقى إعداد فحوص Trixie وsystemd وxorriso قابلاً لإعادة التنفيذ. حسّنت `scripts/build-iso.sh` sidecar ليحفظ اسم ISO نسبياً وقابلاً للنقل، بعد اكتشاف أن الاسم المطلق من حاوية `/workspace` لا يصلح لفحص `sha256sum --check` على runner خارجها.
- اختبار QEMU الوهمي يغطي علامة صحيحة مبكرة، nonce غير مطابق مع نص رسومي مضلل، serial فارغ، timeout، وخروج QEMU بخطأ فوري؛ وقد نجح. هذا يختبر منطق المشغّل فقط، وليس BIOS/UEFI أو QMP/VGA في QEMU حقيقي.
- أُعيد تقسيم workflow إلى `source-check`, `build`, `bios`, `uefi`, و`acceptance-summary`. BIOS وUEFI يعتمدان على build فقط، لذا لا يمنع فشل BIOS بدء UEFI. المرشح المرفوع موسوم بوضوح `ci-diagnostic-candidate` وغير مؤهل للإصدار؛ لا يوجد artifact إصدار عادي حتى تنفيذ بناء واختبارات قبول للصورة غير التشخيصية.
- يكتب `scripts/create-ci-results.py` تقرير `results.json` وفق `tests/ci-results.schema.json`. عدادات التقرير تعد بوابات workflow الأربع، لا حالات الاختبار المفردة؛ يوضّح ذلك `test_summary_unit`. Persistence مذكورة `NOT_IMPLEMENTED` ولا تُفعّل في CI.
- ثُبّتت actions إلى commit SHAs غير متحركة: checkout v7.0.1، upload-artifact v7.0.2، download-artifact v8.0.2؛ معلومات إصدار Node 24 مأخوذة من تعليقات التثبيت ومراجعة release metadata العامة.

### تحقق هذه النسخة المحلية

| الفحص | النتيجة |
|---|---|
| `git diff --check` | PASS، exit 0. |
| تحليل YAML عبر Ruby Psych | PASS؛ تحقق صياغة YAML فقط، وليس GitHub Actions runtime. |
| `bash -n` لملفات البناء/الإقلاع/الاختبار المعدلة | PASS، exit 0. |
| `tests/test_qemu_headless_validation.sh` | PASS، exit 0؛ حالات fake QEMU فقط. |
| `tests/test_ci_results.py` و`tests/test_workflow_contracts.py` | PASS؛ JSON المكسور/الحقول الناقصة مرفوضة، واستقلال job/artifact شروطه مجرّد بعقود نصية. |
| اختبارات source المباشرة و`tests/smoke.sh` | PASS، exit 0. |
| `python3 -m pytest -p no:cacheprovider -q` | PASS: `12 passed in 2.60s`، exit 0؛ pytest ثُبّت في venv مؤقت داخل `/tmp` بعد أن كان غائباً. |
| `systemd-analyze verify --root=<temp>` للوحدات والخدمات مع executable paths في rootfs مصطنع | PASS، exit 0 على أداة المضيف؛ لا يثبت تكامل الوحدة داخل Debian Trixie المبنية. |
| `tests/smoke.sh` ثم فحص `find ... __pycache__` و`git status` | PASS؛ لم يترك bytecode أو cache داخل المستودع. |
| `qemu-system-x86_64`, `qemu-img`, `xorriso`, `shellcheck`, `desktop-file-validate`, `actionlint` | غير متوفرة على المضيف. `xmllint` و`systemd-analyze` متوفران. |
| `gh auth status` | غير مصادق: `gh` يطلب `gh auth login` أو `GH_TOKEN`. لا يمكن تشغيل Actions أو تنزيل run `39474948006` من هذه البيئة حالياً. |

لم يُشغّل `lb build` أو QEMU أو workflow، ولم تُنتج ISO في هذه الجولة. لا توجد أدلة VGA/serial جديدة، ولا QMP/OVMF حقيقيان، ولا run URL جديد. المعلومة الوحيدة الخاصة بالتشغيل التاريخي 39474948006 تبقى كما وردت في طلب المستخدم: timeout 124 وserial فارغ؛ Artifact المباشر لا يزال غير قابل للتنزيل محلياً، لذا السبب الجذري غير محسوم.

### غير معروف وما يحسمه

- محتويات BIOS isolinux وGRUB/EFI الفعلية، ومعاملات kernel داخل ISO التشغيل 39474948006: يلزم Artifact ZIP صالح أو صلاحية قراءة artifact/logs.
- هل systemd service/timer يعملان كما صُمما داخل Debian rootfs، وهل console serial يصل من guest: يلزم staging داخل Debian Trixie وبناء CI variant.
- نتيجة الإقلاع الحقيقية للـBIOS وUEFI، زمنها، صور VGA، وإصدار OVMF المستخدم: يلزم runner مع QEMU/OVMF وArtifact مبنية.
- هل الـWorkflow يرفع المرشح ويحفظ الأدلة ويشغّل UEFI بعد فشل BIOS: لا يحسمه فحص YAML أو tests محلية؛ يلزم تشغيل Actions.
- لا تقيس هذه الجولة أداء RAM 2GB، ولا تختبر USB Persistence، أو التثبيت/إعادة الإقلاع، أو وظائف سطح المكتب داخل جلسة حقيقية.

### متابعة مراجعة التعديلات والتحقق — 2026-10-20

- عُدّل `tests/test_workflow_contracts.py` ليتحقق من استدعاء `scripts/run-source-checks.py` في وظيفة `source-check`، ومن وجود `source-tests.json` في وظيفة التقرير التي تستهلكه؛ الملف الناتج ليس اسماً literal داخل مقطع وظيفة المصدر.
- `python -m pytest -p no:cacheprovider -q`: **12 passed**، exit 0. كما اجتاز الاختبار المباشر `tests/test_workflow_contracts.py`، واختبار `tests/test_ci_results.py`، واختبار QEMU الوهمي `tests/test_qemu_headless_validation.sh`، كلٌ exit 0.
- شُغّل `scripts/run-source-checks.py` على مجموعة الفحوص كاملة: `passed=30, failed=0, not_run=2, skipped=0`، رمز الخروج 1 بسبب عدم توفر `shellcheck` و`desktop-file-validate` فقط. بقية الاختبارات/الفحوص المدرجة في المشغل نجحت، بما فيها smoke وUSB وSecure Boot وwatermark وschema/upstream وXML/SVG وbash/sh syntax. سجلات التشغيل و`source-tests.json` حُفظت تحت `/tmp/isox-source-check-evidence-final2/`، وPython cache تحت `/tmp`، لا داخل المستودع.
- تحليل YAML عبر Ruby Psych و`python3 -m py_compile` و`git diff --check` اجتازوا (exit 0). هذه فحوص ثابتة ولا تختبر تشغيل GitHub Actions.
- فحص الحالة الذي أُجري قبل إنهاء المراجعة أكد أن HEAD كان `caf58594bea006c983d45751f113dfe6ed8b89eb` على الفرع المطلوب؛ عندها كانت التغييرات محلية فقط. `gh auth status` أعاد exit 1 لعدم وجود تسجيل دخول، لذا لم يُشغّل workflow ولم تُنشأ ISO أو نتائج BIOS/UEFI. لا توجد نتيجة CI جديدة ولا رابط تشغيل؛ لا يزال سبب فشل `39474948006` غير محسوم.
- أظهرت مراجعة الكود أن HMP `screendump` يعطي صورة PPM؛ عدّل المشغل امتداد اللقطات إلى `.ppm` بدلاً من `.png`. وجرى تحسين مولّد التقرير لرفض أحجام/مدد غير رقمية وملف JSON لا يحتوي object بدلاً من إسقاطها بصمت إلى قيم افتراضية؛ أضيفت حالات اختبار لهذه المدخلات.
- أُصلح أيضاً تعريف `CERT_IN` المفقود في مسار watermark الاختياري بربطه بـ`ISOX_RELEASE_CERT`، وأضيف assertion لعقد البناء. لم يُختبر بناء watermark فعلياً.
- بعد هذه الإصلاحات: `pytest` = 12 passed؛ مجمّع الفحوص = 30 PASS، 0 FAIL، 2 NOT_RUN (exit 1 للأداتين الغائبتين). اجتاز `systemd-analyze verify --root=<temp>` للوحدات المحددة و`git diff --check`. الأدوات غير المتاحة: `shellcheck`, `desktop-file-validate`, `qemu-system-x86_64`, `qemu-img`, `xorriso`, `actionlint`. لا يثبت هذا build أو boot أو صلاحية runtime في Actions.
- أظهر توثيق GitHub الرسمي لمواصفات hosted runners، الذي فُحص بتاريخ 2026-10-20، أن مساحة SSD القياسية 14 GB ([GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)). هذا أقل من شرط 20 GiB في مشروع ISO-X؛ لذلك أضيفت خطوة تزيل ستة مسارات SDK ثابتة غير مستخدمة من الـrunner المؤقت قبل قياس المساحة. اختبار Workflow يتحقق من المسارات وترتيب الخطوة، لكن المساحة الفعلية بعد التنظيف لا تُعرف إلا من run حقيقي.
