# ISO-X — سجل التغييرات

## 2026-10-20 — إصلاح البناء والتشغيل (قيد التحقق النهائي)

- `.github/workflows/iso-build.yml`: CI بنى ISO فعلية وفحص SHA-256 وEl Torito/System Area، لكنه فشل في QEMU BIOS قبل الإقلاع بسبب USB bus مفقود في helper؛ لذلك رُفع diagnostics ولم تُرفع ISO artifact. أصلح helper في `tests/qemu-acceptance.sh` بإضافة xHCI صريح، ويحتاج إعادة CI لإثبات BIOS وUEFI.
- `scripts/install-build-deps.sh`: إضافة pytest وdesktop-file-utils وxmllint وsystemd وprocps وفحص الأدوات ومفسر pytest. اختبارات Trixie نجحت؛ مساحة ما بعد التثبيت (16 GiB) حالت دون بناء محلي.

- `scripts/build-iso.sh`: ضمان إنشاء `etc/default` قبل توليد إعدادات locale ولوحة المفاتيح؛ إبقاء مسار الإخراج ومراجعة ISO وبصمة SHA-256 بعد نجاح `lb build` فقط.
- `config/package-lists/iso-x.list.chroot`: استخدام أسماء Trixie التي ظهرت في الفهرس (`libgles2`, `polkitd`) وحذف `fonts-kacst` و`pinta` غير المتاحتين؛ لم يُحذف ملف تطبيق مستخدم.
- `scripts/build-iso.sh`, hook/initramfs watermark: فصل وحدة watermark الاختيارية عن مسار الإقلاع والبناء الأساسي؛ تحذير واستمرار عند غيابها/تعطلها. الميزة لا تساوي Secure Boot ولا تحمي من تعديل boot chain.
- `scripts/build-iso.sh`, `scripts/install-build-deps.sh`: جعل بناء Bevy اختيارياً وعدم تثبيت Rust كـ root ضمن تجهيز المضيف؛ لا تُشغّل الجلسة أربع طرفيات تلقائياً.
- `auto/config`: جعل headers اختيارية مع watermark فقط؛ اختبار guard صار يثبت إرسال الخطأ إلى Plymouth ومتابعة الإقلاع. `scripts/secure-vault.py` يستخدم قرص المخرج للملفات الوسيطة الكبيرة لتقليل ضغط tmpfs.
- `config/hooks/live/0300-isox-services.hook.chroot`: ضبط خلفية وشعار ISO-X في LightDM GTK Greeter. إزالة تكرار IBus من XDG autostart، مع نقطة Openbox واحدة.
- `app/isox_welcome.py`, `three-d-login/src/main.rs`: إتاحة Bevy اختيارياً من لوحة الترحيب فقط عند وجوده، وتنبيه المستخدم عند فشله وتصحيح النص. البناء يمنع تشغيل Cargo كـ root.
- `scripts/write-usb.sh`: التحقق من SHA-256 وبنية ISO وسعة وسيط USB وعرض الجهاز والتأكيد النصي قبل `dd`؛ أضيف اختبار checksum لا يكتب إلى جهاز.
- `scripts/encode-watermark.py`, `scripts/build-iso.sh`: توجيه header المولد إلى staging بدلاً من تعديل المصدر، ورفض وجود ISO قديم قبل البناء حتى لا يُخلط artifact سابق بنتيجة جديدة.
- `app/iso_x_gtk.py`: السماح بكتابة الأرقام في أدوات الإدخال، وتحسين عدم إتلاف الملفات عند الترميز/الحفظ، ونقل البحث/النسخ إلى الخلفية ومنع نسخ مجلد إلى نفسه أو تحته.
- `app/iso_x_gtk.py`: إضافة نقل الملفات وحذفها بتأكيد، مع تنفيذ العمليات الثقيلة بالخلفية ومنع الكتابة فوق الوجهات؛ الحذف نهائي. إزالة بطاقة PDF المكررة من مركز التطبيقات دون حذف ملفات مصدر.
- `scripts/build-iso.sh`: عدم تضمين نسخة Tkinter التاريخية غير المستعملة في الصورة؛ بقي `app/iso_x_shell.py` في المصدر للتوافق/المرجع ولم يُحذف.
- `app/isox_appcenter.py`: فحص حالة الحزم بالخلفية؛ إتاحة تحديث الفهارس ومعالجة أخطاء الشبكة والصلاحيات، مع `pkexec` وتأكيد الإزالة.
- `tests/test_build_contracts.py`, `tests/test_initramfs_watermark_guard.sh`, `tests/test_write_usb_validation.sh`, `tests/test_secure_vault.py`, `tests/smoke.sh`: إضافة اختبارات عقود وتشغيل لحارس الإقلاع، وحاجز build غير root، والتحقق من USB، وموقع ملفات الخزنة المؤقتة، وتشغيلها من smoke حتى دون pytest.
- `README.md`, `AUDIT.md`, `docs/ARCHITECTURE_AR.md`, `docs/UPSTREAM_INTEGRATION_AR.md`, `docs/THIRD_PARTY_LICENSES.md`: تحديث الحالة وتوثيق الالتزامات ومصفوفة التوافق. لا يوجد كود من OxyOS منسوخ لعدم ظهور ترخيص يسمح بإعادة التوزيع؛ إعداد Debian Live Config لم ينسخ حرفياً.
- لم ينتج هذا السجل ISO؛ أوامر البناء/الإقلاع وملفات الخرج لا توصف بالنجاح قبل الاختبار الفعلي.

## 2026-10-19 — مرحلة خط الأساس قبل الإصلاح

- أُضيف `AUDIT.md` لتسجيل نتائج النسخة الاحتياطية وفحص ملفات البناء والحزم والإقلاع والاختبارات قبل تعديلات الكود.
- لم تُعدّل ملفات التطبيق أو إعدادات البناء الأصلية في هذه المرحلة.
- شغّلت الاختبارات ملفات Python وأنشأت مجلدات `__pycache__`/ملفات `.pyc` مؤقتة؛ هذه مخرجات مولّدة وليست مصادر أصلية. تزال بعد تسجيل التنظيف في هذا السجل.
- أُنشئ سجل شجرة المصدر وأحجام المجلدات خارج المجلد في `/mnt/data/ISO-X-0.4.0-TRIXIE-tree.txt` و`/mnt/data/ISO-X-0.4.0-TRIXIE-directory-sizes.txt` انطلاقًا من النسخة الاحتياطية الأصلية.
- بعد توثيق نتائج خط الأساس، أزيلت ثلاثة مجلدات `__pycache__` الناتجة من الاختبارات (`app/`, `scripts/`, `tests/`) لأنها bytecode مولّد/قابل لإعادة الإنشاء ومُستثنى أصلًا في `.gitignore`؛ لم تُحذف ملفات المصدر. المسارات المحذوفة موثقة في `/mnt/data/ISO-X-0.4.0-generated-pycache-removed.txt`.
- أُصلح تقرير أحجام المجلدات الخارجي ليستخدم مسارات نسبية قابلة لإعادة القراءة بدل مسار استخراج مؤقت.


## 2026-10-19 — إصلاحات التدقيق المرحلة الأولى

- `auto/config`: أُضيف `--bootloaders "syslinux grub-efi"` لضبط مسار BIOS وUEFI صراحةً في ISO الهجين؛ لم يُعتبر ذلك إثبات إقلاع قبل اختبار صورة فعلية.
- `scripts/build-iso.sh`: أُضيف تثبيت `db/migrations/004_isox_040.sql` الذي كان التطبيق يبحث عنه ولم يكن يُنسخ إلى النظام الناتج.
- `scripts/build-iso.sh`: أصبحت README الإنجليزية ودليل تراخيص الطرف الثالث يُنسخان إلى `/usr/share/doc/iso-x/`.
- أُنشئ `build.sh` كواجهة تنفيذ من أمر واحد مع إبقاء حواجز الأمان ومتطلبات `scripts/build-iso.sh`.
- أُنشئ `README.md` و`docs/THIRD_PARTY_LICENSES.md`، وصُححت إشارات الإصدار والمضيف في README_AR ووثائق البناء/الهندسة النشطة من Bookworm/0.3.1 إلى Trixie/0.4.0. لم تُمس السجلات التاريخية وإشعارات المصدر القديمة.
- أُضيف `tests/test_build_contracts.py` وعُزز `tests/test_source_config.py` لتثبيت هذه الإصلاحات كاختبارات ارتدادية.
- أزيل `.pytest_cache/` الذي أُنشئ أثناء الاختبار، لأنه ناتج اختبار قابل لإعادة الإنشاء وليس مصدرًا أصليًا. لم يُحذف أي ملف مشروع يدوي أو مكرر.

- `assets/iso-x-start.html` و`config/hooks/live/0400-isox-firefox-defaults.hook.chroot`: أُضيفت صفحة بدء عربية محلية، وتُضبط كصفحة Firefox ESR الافتراضية في تفضيلات Debian على مستوى النظام مع إبقاء إمكانية تجاوزها من ملف المستخدم. أُضيف اختبار ساكن يتأكد من نسخ الصفحة والـ hook؛ لا يثبت فتح المتصفح فعليًا قبل بناء ISO.
- أضيفت `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` كقائمة قبول منفصلة لكل اختبارات الجهاز الحقيقي، وربطت من README ونسخت إلى توثيق النظام الناتج. أضيف `shellcheck` إلى حزم تجهيز مضيف البناء والتحقق من وجوده بعد التثبيت.
- أُشير بوضوح في `STATUS_AR.md` إلى أنه تقرير 0.3.1 تاريخي، وحدّثت عنوان/فقرة المتصفح والبناء في `docs/ARCHITECTURE_AR.md`، كي لا توحي وثائق التشغيل القديمة بأن Bookworm/0.2.0 هي النسخة الحالية. حُفظت تقارير الإصدار القديمة كمرجع تاريخي.
- أُرفق سجل إعادة الاختبار الفعلية `evidence/PHASE2_RETEST_20261019.txt` داخل المشروع ليبقى التقرير والأدلة في حزمة المصدر نفسها.
- بعد تشغيل مجموعة الاختبارات النهائية، أزيلت مجددًا مجلدات `__pycache__` التي أعاد `py_compile` توليدها؛ هذه ملفات bytecode مولدة وليست مصدرًا. المسارات الدقيقة محفوظة في `ISO-X-0.4.0-generated-caches-removed-final.txt`. لم تُحذف ملفات تطبيق أو إعداد.
