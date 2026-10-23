# سجل إصلاح التشغيل — ISO-X 0.4.0 TRIXIE

هذا السجل يميز بين إصلاح المصدر وبين القبول على جلسة X أو جهاز فعلي. لا يثبت نجاح بناء ISO أو توافق Wi-Fi على حاسوب بعينه.

| الملف / المسار | السبب الجذري أو الفجوة | الإصلاح | اختبار الإثبات والحالة |
|---|---|---|---|
| `app/iso_x_gtk.py`، دورة `Gtk.main()` | تستخدم الحوارات `Gtk.Dialog.run()` حلقة GTK متداخلة؛ كان `Gtk.main_quit()` ينهي الحلقة النشطة فقط، وقد يترك التطبيق حيًا بعد إغلاق النافذة الرئيسية. هذا تفسير مرجح يحتاج اختبار جلسة فعلية. | تصريف مستويات الحلقة من callback خامل، مع إبقاء `delete-event` غير حاجب، وإغلاق SQLite في مسار `finally` وتسجيل الخطأ. | `py_compile` و`test_source_config.py`: PASS. اختبار Xvfb وفتح حوار F12 ثم إغلاق الأصل: `NOT_RUN` محليًا لغياب Xvfb/Openbox.
| `app/iso_x_gtk.py`، مهام الملفات والقياسات | جمع `uptime` و`ps` كان متزامنًا في خيط GTK؛ مهام الملفات تعمل بخيوط daemon ولا ينبغي قطعها عند إغلاق النافذة. | جمع القياسات في worker مع `GLib.idle_add`؛ تأجيل الإغلاق أثناء عمليات الملفات فقط، ثم السماح به بعد اكتمالها. | فحص المصدر والترجمة: PASS. اختبار زمن استجابة GTK الفعلي: `NOT_RUN`.
| `app/isox_appcenter.py` | النافذة الابتدائية `1180×780` تتجاوز المساحة العملية لشاشة `1366×768` مع زخرفة النافذة والشريط؛ إغلاق المتجر أثناء تثبيت/إزالة حزم قد يقطع واجهة العملية. | حجم ابتدائي `1120×660`، وحماية الإغلاق أثناء عملية حزم نشطة مع رسالة حالة، وإنهاء حلقات GTK المتداخلة. | ترجمة واختبارات العقود: PASS. اختبار GUI الفعلي: `NOT_RUN`.
| `app/isox_store_backend.py` | أخطاء `apt-get -s upgrade` وFlatpak كانت تتحول إلى قائمة تحديثات فارغة، ما قد يوحي بعدم وجود تحديثات عند فشل الاتصال. | تمرير رمز الخطأ والتشخيص إلى الواجهة؛ فحص Flatpak فقط عند وجود remote للمستخدم. | `tests/test_store_backend.py`: 16 اختبارًا PASS، منها فشل DNS وعدم وجود Flatpak remote.
| `scripts/build-iso.sh`، `desktop/tint2rc` | `/etc/default/keyboard` وحده لا يضمن تطبيق التخطيطات في جلسة X؛ كما أن تشغيل `nm-applet --indicator` لا يطابق systray المهيأ في tint2. | تطبيق `ara,us` و`grp:alt_shift_toggle` عبر `setxkbmap` عند بدء الجلسة، تشغيل `gxkb` للمؤشر، وتشغيل `nm-applet` بوضع XEmbed الافتراضي. | حزم `gxkb` و`x11-xkb-utils` متاحة في Trixie؛ اختبار تبديل المجموعة الفعلي مضاف إلى CI، ولم يُشغّل محليًا.
| `desktop/openbox-menu.xml`، إعدادات ISO-X | لم يكن فتح إعدادات اتصال NetworkManager متاحًا مباشرة من قائمة Openbox أو صفحة إعدادات ISO-X. | ربط `nm-connection-editor` بالقائمة وصفحة إعدادات التطبيق. | `test_source_config.py` و`xmllint`: PASS. اكتشاف Wi-Fi/الاتصال/DNS على جهاز فعلي: `NOT_RUN`.
| `.github/workflows/iso-build.yml`، `scripts/run-source-checks.py` | بوابة المصدر لم تختبر إغلاق GTK أو تخطيط XKB في جلسة عرض حقيقية. | إضافة تشغيل Xvfb/Openbox وقيادة النافذة عبر `xdotool`/`wmctrl`؛ يبقى Workflow الحالي وبوابات BIOS/UEFI والتحويل إلى ISO عادية كما هي. | عقد Workflow وYAML: PASS. تشغيل Xvfb في Codespace: `NOT_RUN` لغياب الأدوات.

## نتائج المصدر المحلية

شُغّل `scripts/run-source-checks.py` على الحالة الحالية: 65 فحصًا ناجحًا، صفر فشل، وحالة pytest واحدة متخطاة؛ أربع بوابات `NOT_RUN` بسبب غياب `sfdisk` وXvfb/أدوات X و`ShellCheck` و`desktop-file-validate`. لا تتضمن هذه النتيجة بناء ISO أو إقلاع BIOS/UEFI.

اختبار التبديل بين مجموعات XKB واختبارات إغلاق/تحجيم النوافذ ستعمل ضمن `source-check` في GitHub Actions. لا تُعد اختبارات Wi-Fi الحقيقي، اتصال الإنترنت وDNS على بطاقة فعلية، أو persistence عبر USB مقبولة حتى تُسجل أدلة مستقلة لها.