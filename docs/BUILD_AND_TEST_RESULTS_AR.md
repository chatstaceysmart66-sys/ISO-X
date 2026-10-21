# نتائج البناء والاختبارات — ISO-X 0.4.0

**تاريخ مراجعة السجل:** 2026-10-20  
**الفرع:** `fix/isox-build-and-runtime`  
**الهدف:** Debian GNU/Linux 13 Trixie، amd64.  
**الحالة:** CI بنى ISO حقيقية وفحص SHA-256 وEl Torito/System Area؛ فشل QEMU BIOS بسبب إعداد USB ناقص في الاختبار، لذلك لم يُرفع Artifact الإصدار ولم يثبت الإقلاع الفعلي.

## نتائج الاختبارات

تُحدّث هذه القائمة بعد التنفيذ الفعلي فقط. رمز الخروج `0` يعني نجاح الأمر المذكور وحده، ولا يثبت بناء ISO أو إقلاعها.

| الأمر | النتيجة | الملاحظة |
|---|---|---|
| `python3 -m py_compile app/isox_appcenter.py` | نجاح، exit 0 | ترجمة ملف مركز التطبيقات بعد تحويل فحوص الحزم والإجراءات إلى خلفية. |
| `python3 tests/test_build_contracts.py` | نجاح، exit 0 | يثبت عقود البناء ومركز التطبيقات ويرفض تشغيل build غير root دون إنشاء مجلد staging؛ لا يستورد GTK ولا ينفذ apt. |
| `python3 tests/test_secure_vault.py` | نجاح، exit 0 | تشفير/فك، Unicode، كلمة مرور خاطئة، العبث، واستخدام مجلد الوجهة للبيانات المؤقتة. |
| `bash tests/smoke.sh` | نجاح نهائي، exit 0 على Trixie | schema والترحيلات، إعداد المصدر وربط desktop/Openbox، تكامل upstream، الخزنة، التوقيع، Secure Boot validation، حارس Plymouth، وUSB/QEMU negative tests. |
| `bash tests/test_write_usb_validation.sh` | نجاح، exit 0 | بصمة مطابقة مقبولة ومعدلّة مرفوضة؛ لا تشغيل لـ`dd` ولا لمس لوسيط حقيقي. |
| `bash tests/test_qemu_headless_validation.sh` | نجاح، exit 0 | يثبت أن QEMU الذي ينتهي دون `graphical.target` في serial log لا يُسجل كإقلاع ناجح؛ هذا اختبار للكاشف فقط وليس إقلاع ISO. |
| `python3 tests/test_source_config.py` | نجاح، exit 0 | تحقق إعدادات المصدر وربط أوامر Desktop/Openbox ببرامج staged أو حزم معلنة. |
| `python3 -m py_compile` لتطبيقات ISO-X واختباراتها | نجاح، exit 0 | شمل GTK shell والترحيب ومركز التطبيقات والخزنة وسكربتات Python والاختبارات. |
| `python3 tests/test_build_contracts.py` | نجاح، exit 0 | تحقق عقود البناء ومركز التطبيقات والحذف/النقل وBevy/autostart وعدم شحن Tkinter وحاجز UID وتوليد header في staging. |
| `find ... | xargs bash -n` لكل Shell/hooks | نجاح، exit 0 | صياغة جميع نقاط تشغيل Shell وhooks اجتازت `bash -n`. |
| فحص XML/SVG | نجاح، exit 0 | اجتاز 5 ملفات XML/SVG التحليل؛ استُبعد `.plymouth` لأنه ملف إعداد وليس XML. |
| `systemd-analyze verify --root=...` | نجاح نهائي، exit 0 | الوحدات الثلاث تحققت بعد وضعها وتعريفات targets والنصوص التنفيذية في rootfs مؤقت. |
| `python3 -m py_compile` للتطبيقات والاختبارات | نجاح نهائي، exit 0 | يشمل GTK shell القديمة المحفوظة في المصدر، الترحيب، App Center، Secure Vault ومولّد العلامة. |
| `bash -n` لكل السكربتات/hooks و`sh -n` لـinitramfs | نجاح نهائي، exit 0 | اجتازت جميع الملفات القواعدية. |
| `git diff --check` | نجاح نهائي، exit 0 | لا توجد whitespace errors. |
| Debian Trixie Docker / Python 3.13.5 / pytest 8.3.5 | نجاح، exit 0 | `python3 -m pytest -q`: 11 passed. smoke والاختبارات المحددة والمدققات نجحت. |
| `./scripts/install-build-deps.sh` داخل Trixie | نجاح، exit 0 | ثبتت الأدوات المطلوبة وتحققت الإصدارات. بعد التثبيت كانت المساحة 16 GiB متاحة. |
| مساحة Codespace داخل حاوية Trixie | رفض build المحلي، exit 32 | `df -h /workspace`: 32 GiB إجمالي و16 GiB متاح؛ أقل من 20 GiB. GitHub runner المؤقت وفّر مساحة كافية للبناء الفعلي. |
| ShellCheck `-S warning`, `desktop-file-validate`, `xmllint`, `systemd-analyze verify` | نجاح، exit 0 داخل Trixie | أزيلت ملاحظات ShellCheck ذات مستوى warning، وعولج تصنيف desktop المكرر. |
| فهارس Debian Trixie amd64 | نجاح، 148 اسماً و0 مفقود | فُحصت `main`, `contrib`, `non-free`, `non-free-firmware` مباشرةً بما في ذلك headers/build tools الاختيارية؛ البناء ما زال الاختبار النهائي لحل الاعتماديات. |
| `python3 -m pytest -q` على مفسّر المضيف | نجاح، exit 0 | 11 passed على Python 3.14.2؛ تحقق منفصل إضافي نجح على Python 3.13.5 في Trixie. |
| `./build.sh` في Codespace | رفض مسبق، exit 2 | UID 1000 ومساحة أقل من الحد؛ لم يبدأ build محلياً. البناء الفعلي جرى داخل GitHub runner. |
| `bash tests/qemu-acceptance.sh check` في CI | نجاح | sidecar SHA-256 وبيانات xorriso اجتازا الفحص. |
| QEMU BIOS headless | فشل harness، QEMU exit 1 / helper exit 10 | غياب USB bus لـ`usb-tablet`؛ serial فارغ ولم يبدأ إقلاع النظام. أضيف xHCI صريح ويحتاج run جديداً. |
| QEMU UEFI headless | لم يُنفذ | تسلسل CI توقف عند فشل BIOS؛ لا نتيجة UEFI. |
| Workflow GitHub Actions run `39471524581` | فشل، job exit 10 | [سجل التشغيل والـdiagnostics](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/39471524581)؛ ISO artifact تخطى شرط النجاح. |

## بناء ISO

بنى CI ملف `ISO-X-0.4.0-live-amd64.iso` فعلياً، حجمه `2,617,245,696` بايت (2.44 GiB)، وبصمته SHA-256 هي `989adb37d5b178f27951ac4ca3c9d4b8d9ae0c23862b585095411db32eda648b`. اجتاز `sha256sum --check` و`xorriso`; كشف El Torito مدخلي BIOS وUEFI، وكشف System Area ‏MBR/isohybrid/GPT/APM. لم يُرفع ISO كـArtifact صالح لأن workflow يشترط نجاح QEMU أيضاً؛ انتهت صلاحية runner وأزيلت الصورة منه.

فشل تشغيل BIOS headless قبل بدء الآلة الافتراضية: `qemu-system-x86_64: -device usb-tablet: No 'usb-bus' bus found for device 'usb-tablet'`؛ خرج QEMU 1 ثم helper 10 لغياب دليل `graphical.target`. هذا خطأ إعداد في harness وليس دليلاً على فشل أو نجاح إقلاع ISO. UEFI لم يُشغّل لأن تسلسل CI توقف عند فشل BIOS. أُضيف xHCI صريح إلى المصدر ويحتاج run جديداً لإثبات الإقلاع.

عند نجاح بناء فعلي، يجب حفظ الأمر ورمز الخروج، وجود الملف وحجمه، نتيجة `xorriso`, ومخرجات `sha256sum --check`. لا تعتبر `bash -n` أو الاختبارات المصدرية بديلاً عن ذلك.

## اختبارات قبول لازمة لاحقاً

- اختبار حل كل حزم `config/package-lists/iso-x.list.chroot` من مستودعات Trixie amd64 أثناء البناء.
- إقلاع صورة واحدة على BIOS وأخرى/نفس الصورة على UEFI باستخدام QEMU وOVMF، ثم اختبار المثبّت والجلسة.
- اختبار لوحة المفاتيح العربية/الإنجليزية، الصوت، الشبكة، مركز التطبيقات، المحرر والملفات داخل GTK فعلي.
- اختبار Secure Boot لا يُجرى أو يُعلن مدعوماً دون سلسلة ثقة موثقة؛ watermark معطلة افتراضياً ولا تمنع الإقلاع عند غيابها.
- اختبار أجهزة فعلية للطباعة والبلوتوث والواي فاي وبطاقات الرسوميات، وقياس الأداء على جهاز 2GB RAM.
- لم يُبنَ مشهد Bevy ولم تُختبر الواجهة الرسومية. Rust/Cargo غير مطلوبين لبناء ISO الافتراضي.

تُسجّل النتائج النهائية والأدلة في `AUDIT.md` و`docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` بعد تنفيذها.

## بناء محلي جديد — ISO-X Store — 2026-10-20

هذه النتائج أحدث من سطر سجل CI أعلاه، وتخص commit `dba48b57128032a9cabefb6deb6eb1f6381cb095` الذي يتضمن ISO-X Store:

| الفحص | النتيجة الفعلية |
|---|---|
| `live-build` داخل Debian 13 Trixie amd64 | `P: Build completed successfully`، exit 0. بُنيت نسخة مصدر نظيفة في `/tmp` لأن مساحة workspace أقل من شرط البناء؛ استخدمت الحاوية صلاحيات mount اللازمة لـlive-build. |
| صورة ISO | [ISO-X-0.4.0-live-amd64.iso](../ISO-X-0.4.0-live-amd64.iso)، `2,657,157,120` بايت. |
| SHA-256 | `ad282899b7e1c51fd96590807437d29bffa97c898c7e77e09323a2e3c9b28da1`؛ تحقق `sha256sum --check` بنجاح. |
| `xorriso` | اجتاز فحص الصورة؛ مدخل BIOS ‏`/isolinux/isolinux.bin` ومدخل UEFI ‏`/boot/grub/efi.img` موجودان، مع MBR isohybrid/GPT/APM. |
| ملفات المتجر في SquashFS | تأكد وجود `isox_store_backend.py` ومدخل سطح المكتب وملفات الأصوات الخمسة داخل نظام الملفات النهائي. |
| QEMU BIOS | محاولة TCG لمدة 180 ثانية انتهت بـtimeout/exit 124؛ ملف Serial فارغ. لا إثبات لجلسة رسومية أو علامة جاهزية؛ النتيجة غير محسومة. |
| QEMU UEFI | OVMF بدأ تشغيل DVD، لكن المحاولة انتهت بـtimeout/exit 124 دون علامة جاهزية من النظام؛ النتيجة غير محسومة. |
| الكتابة على الأقراص | لم يُرفق قرص افتراضي أو جهاز حقيقي؛ لم تُنفذ كتابة على وسيط. |
| GitHub push/Actions | الدفع فشل exit 128 بسبب غياب اعتماد Git (`unable to get password from user`)، و`gh auth status` غير مصادق. لا تشغيل Actions أو Artifact جديد. |
