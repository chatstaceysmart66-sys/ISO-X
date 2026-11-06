# مصفوفة علاقات الملفات — ISO-X

تصف هذه المصفوفة المنتج → العقد/المورد → المستهلك. `PASS-source` يعني أن العلاقة فُحصت في المصدر أو اختبار fixture؛ لا يعني أنها اختُبرت داخل ISO فعلية. حالة CI الحالية مذكورة مع commit/run حتى لا تختلط بأدلة اللقطة السابقة.

| المنتج | العقد/المسار | المستهلك | التحقق | الحالة والحد |
|---|---|---|---|---|
| `assets/iso-x.html` | ينسخ إلى `config/includes.chroot/usr/share/iso-x/start.html` | `config/hooks/live/0400-isox-firefox-defaults.hook.chroot` يكتب `file:///usr/share/iso-x/start.html` كـFirefox ESR homepage | `tests/test_build_contracts.py::test_browser_homepage_is_staged_and_configured` | PASS-source بعد إضافة assertions لموارد `file:///`؛ فتح Firefox من ISO غير متحقق. |
| `assets/iso-x.html` | `file:///usr/share/iso-x/assets/reference-dragon-mark.jpg` | `<img>` في صفحة البدء | `scripts/build-iso.sh` ينسخ الشعار المولد إلى المسار؛ اختبار build contract يتحقق من destination | PASS-source؛ بصمة الملف داخل ISO لا تزال UNVERIFIED. |
| `assets/iso-x.html` | `file:///usr/share/doc/iso-x/README_AR.md` | رابط دليل ISO-X المحلي | `scripts/build-iso.sh` ينسخ `README_AR.md` إلى المسار نفسه؛ اختبار build contract يتحقق من destination | PASS-source؛ لا يوجد اختبار نقر داخل Firefox. |
| `design/reference/iso-x-reference.html` | بصمة المصدر و6 Data URI/3 صور فريدة | extractor → generator → manifest وأصول JPEG/PNG | `tests/test_build_contracts.py`; `scripts/verify-reference-assets.py` على rootfs اصطناعي | PASS-source/fixture؛ ليس دليلاً على مطابقة المرفق `iso-x (1).txt` ولا على العرض الكامل للـHTML. |
| `assets/reference/desktop-wallpaper-original.jpg` | `/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.jpg` | PCManFM `desktop-items-0.conf` وLightDM greeter | manifest + build staging + `tests/test_build_contracts.py` | سلسلة المصدر→staging متحققة؛ قراءة hash من SquashFS/اختبار جهاز فعلي UNVERIFIED. |
| `assets/reference/boot-screen-original.jpg` | تحويل lossless إلى `/usr/share/plymouth/themes/isox/iso-x-plymouth.png` | `plymouth/isox/isox.script` عبر `Image("iso-x-plymouth.png")` | manifest واختبار أبعاد/مشتق + build staging | PASS-source؛ ظهور Plymouth بصرياً ضمن boot الحديث غير مثبت بلقطة مخصصة. |
| `assets/reference/dragon-mark-original.jpg` | `/usr/share/iso-x/assets/reference-dragon-mark.jpg` وPNG مشتقة | LightDM، GTK/welcome، صفحة Firefox، أيقونة Hicolor | manifest، build، hook، تطبيقات GTK، اختبار الصور | PASS-source؛ اختبار استهلاك كل موضع بصرياً UNVERIFIED. |
| `assets/reference/reference-assets.json` | بيانات SHA/MIME/أبعاد/مسارات | extractor/generator ثم verify-reference-assets.py | تحقق rootfs fixture؛ اختبار manifest | PASS-fixture؛ لا تحقق hash من SquashFS النهائي. |
| `config/package-lists/iso-x.list.chroot` | أسماء حزم Trixie | live-build/apt داخل chroot | build source-check في CI | تم حل القائمة وبناء ISO على `b156470`؛ لا يثبت أن كل تطبيق يعمل أو أن تعديل الأصول لا يكسر البناء. |
| `scripts/build-iso.sh` | `config/includes.chroot`, hooks, package list, bootloader templates | `lb build` ثم xorriso والتحقق البنيوي | run `42221229398` على الأساس `b156470`؛ contracts/syntax | build PASS على الأساس فقط؛ build النسخة المعدلة NOT_RUN. |
| `auto/config` + `config/bootloaders/*` | Trixie/amd64، ISO hybrid، syslinux وGRUB EFI | live-build؛ BIOS وUEFI | source contracts وCI QEMU BIOS/UEFI | PASS على `b156470`؛ يلزم إعادة CI بعد التغيير. |
| `desktop/openbox-rc.xml` + `desktop/openbox-menu.xml` | إعدادات WM ومداخل التطبيقات | Openbox في جلسة LightDM | XML/source checks وGTK/Openbox Xvfb CI | PASS للعمليات الأساسية في CI؛ ست نوافذ مستقلة/كل عمليات القائمة ليست مثبتة. |
| `desktop/tint2rc` | إعداد panel/tasklist/launchers/clock | `Openbox autostart` يشغّل Tint2؛ مراقب CI يعيد فحص وجوده بعد marker | readiness/stability tests وCI boot logs | فحص الاستمرار كل ثانية لـ30 ثانية مضاف ومختبر بمحرّكات وهمية؛ تشغيله داخل guest على التغييرات الحالية NOT_RUN. السبب الجذري للـsegfault التاريخي غير محسوم. |
| `scripts/isox-ci-ready.sh` | readiness ثم `ISOX_CI_READY` ثم `isox-ci-stability.sh` حتى 30 ثانية ثم `ISOX_CI_STABLE` أو `ISOX_CI_STABILITY_FAIL` | `systemd/isox-ci-ready.service` و`isox-ci-ready.timer` في تشخيص CI فقط | `tests/test_desktop_readiness.sh`, `tests/test_qemu_headless_validation.sh` | PASS-source للاختبار؛ لا يوجد حتى الآن دليل guest على تشغيل المسار بعد marker. |
| `scripts/isox-desktop-window-ready.sh` | X session + Openbox + Tint2 + نافذة ISO-X؛ `xwininfo` | خدمة readiness | `x11-utils` في package list واختبار fake | PASS على CI السابق؛ `wmctrl` أزيل من probe وليس من استخدام window snap/test. |
| `tests/qemu-runner.py` | QMP/serial/screenshot/nonce، انتظار stable/failure marker، و`segfault` classification | `tests/qemu-acceptance.sh` ثم BIOS/UEFI jobs | fake QEMU tests وCI actual boots | fake-QEMU regression يغطي stable/unstable والمبكر/المدة الخاطئة؛ runner يتحقق من تطابق المدة وانقضاء المهلة تقريباً. تشغيل CI `42221229398` على الأساس لا يستخدم العقد الجديد. |
| workflow `build` | artifacts `ISO-X-0.4.0-ci-diagnostic-candidate-*` وoutputs hash/size | BIOS/UEFI ثم `promote` | `tests/test_workflow_contracts.py`; CI run | run `42221229398` اكتمل SUCCESS لكل الوظائف على `b156470`؛ لا يشمل حذف الأصول ومراقبة الاستقرار المضافة محلياً. |
| `config/hooks/live/0300-isox-services.hook.chroot` | NetworkManager/LightDM/Bluetooth/CUPS؛ greeter paths | خدمات النظام والحساب live `user` | shell syntax وsource checks وCI boot | LightDM/Openbox boot مرئي في CI؛ الشبكة/الطابعة/Bluetooth على أجهزة حقيقية غير مختبرة. |
| `systemd/isox-zram.service` | `/usr/local/sbin/isox-zram-setup` | systemd قبل الجلسة الرسومية | build source contract | لا قياس zram/RAM داخل guest حديث؛ أداء 5/6/8GB NOT_RUN. |
| `systemd/isox-preload.timer` | خدمة user و`isox-preload.py` | جلسة المستخدم؛ no-op حتى تفعيل المستخدم | source contracts | لا قياس أثر/موارد، NOT_RUN. |
| `app/isox_store_backend.py` | واجهة catalog/install/remove عبر APT أو Flatpak وPolkit | `app/isox_appcenter.py` | backend fake-runner tests | PASS للمسارات/argv والأخطاء؛ معاملة حزم واقعية وشبكة/Polkit NOT_RUN. |
| `app/iso_x_gtk.py` | handlers GTK للملفات والإعدادات/التطبيقات | Openbox autostart وDesktop entries | tests GTK/Xvfb وsource checks | بعض عمليات الملفات مختبرة ساكناً فقط؛ لم تُختبر كل الأخطاء والصلاحيات على ISO. |
| `scripts/write-usb.sh` | تحقق ISO/hash/وجهة/تأكيد وكتابة/قسم persistence | مستخدم USB | validation وpartition fixtures | الكتابة على أقراص حقيقية لم تُنفذ؛ اختبار reboot/persistence NOT_RUN. |
| `kernel/isox-watermark/*` و`initramfs/*` | تجميع bytes وhook/guard مشروط | build اختياري مع توقيع خارجي | watermark/guard fixtures | ليس جزءاً من الإقلاع العادي؛ module حقيقي في Trixie غير مبني. |

## علاقات مكسورة أو حدود لم تُحسم

1. لم يظهر كسر في روابط صفحة Firefox المحلية في المصدر بعد إضافة اختبار المسارات؛ وصول الموارد إلى ISO المعدلة لم يُثبت بعد.
2. مرجع HTML الكبير ليس الملف المرفق المحدد، و`assets/iso-x.html` صفحة بدء وليست shell. تبقى متطلبات مطابقة المرفق واعتماد واجهة HTML الأساسية **UNVERIFIED/MISSING**.
3. أصول `assets/iso-x-*` السبعة القديمة كانت ميتة في مسار runtime/build؛ أزيلت، وتمنع اختبارات المصدر عودتها. صور `assets/reference/*` لم تُحذف.
4. خروج BIOS/UEFI PASS من QEMU لا يثبت Persistence أو العتاد الحقيقي. مراقبة 30 ثانية أضيفت للمصدر، لكن لم تُنفذ بعد داخل guest على التغيير الحالي.
5. rootfs fixture يفحص hash قبل البناء؛ لا يثبت hash ملفات داخل SquashFS/ISO النهائية.

## نتائج CI التاريخية ذات الصلة

- `42206164401` على `49870a8`: فشل UEFI بعد `wmctrl` segfault وإلغاء BIOS أثناء تثبيت QEMU، لا فشل BIOS boot.
- `42212462133` على `246f455`: اجتاز diagnostic وnormal-boot BIOS/UEFI. لم يكن هذا التغيير المرجعي `b156470`.
- `42221229398` على `b156470`: اكتمل workflow بـSUCCESS في source/build/BIOS/UEFI/promote/acceptance-summary. ISO التشخيصية 2,785,017,856 بايت، SHA-256 `ada797696e3ea9cbee4367bcfe8befa914cbf06ab0b876ebfd029299883c37fd`؛ `results.json` يسجل Persistence `NOT_RUN`. النتائج تسبق التغييرات المحلية.
