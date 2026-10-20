# نتائج البناء والاختبارات — ISO-X 0.4.0

**تاريخ مراجعة السجل:** 2026-10-20  
**الفرع:** `fix/isox-build-and-runtime`  
**الهدف:** Debian GNU/Linux 13 Trixie، amd64.  
**الحالة:** اختبارات المصدر في Debian Trixie ناجحة؛ لم تُبنَ ISO لأن المساحة داخل الحاوية بعد تثبيت أدوات البناء أقل من الحد الإلزامي.

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
| مساحة وذاكرة حاوية Trixie بعد اعتماديات البناء الكاملة | رفض البناء، exit 32 | `df -h /workspace`: 32 GiB إجمالي، 14 GiB مستخدم، 16 GiB متاح؛ أقل من 20 GiB. الذاكرة الكلية 7.8 GiB. لم يبدأ `./build.sh`. |
| ShellCheck `-S warning`, `desktop-file-validate`, `xmllint`, `systemd-analyze verify` | نجاح، exit 0 داخل Trixie | أزيلت ملاحظات ShellCheck ذات مستوى warning، وعولج تصنيف desktop المكرر. |
| فهارس Debian Trixie amd64 | نجاح، 148 اسماً و0 مفقود | فُحصت `main`, `contrib`, `non-free`, `non-free-firmware` مباشرةً بما في ذلك headers/build tools الاختيارية؛ البناء ما زال الاختبار النهائي لحل الاعتماديات. |
| `python3 -m pytest -q` على مفسّر المضيف | نجاح، exit 0 | 11 passed على Python 3.14.2؛ تحقق منفصل إضافي نجح على Python 3.13.5 في Trixie. |
| `./build.sh` | رفض مسبق، exit 2 | المستخدم UID 1000؛ الرسالة الفعلية: `شغّل البناء على Linux بصلاحيات root`. لم يبدأ `lb build`. |
| `bash tests/qemu-acceptance.sh check` | لم يُنفذ على ISO | لا توجد ISO ناتجة للاختبار. |
| Workflow GitHub Actions | YAML وBash اجتازا التحليل؛ سيبدأ عند دفع هذا التغيير | يتحقق من موارد runner، ويشغّل Trixie tests/build/QEMU، ويرفع التشخيص دائماً وISO فقط عند النجاح الكامل. لا يوجد run أو artifact حتى الآن. |

## بناء ISO

لا يوجد ملف `ISO-X-0.4.0-live-amd64.iso` ناتج عن هذه المراجعة، ولذلك لا توجد بصمة إصدار للإبلاغ عنها. اكتمل تثبيت أدوات Trixie داخل Docker، لكن المساحة الحرة بعد التثبيت كانت 16 GiB؛ امتنعنا عن `./build.sh` احتراماً لشرط 20 GiB. سيبدأ workflow عند الدفع، لكنه سيوقف البناء بأمان إذا بقيت مساحة runner أو Trixie دون الحد.

عند نجاح بناء فعلي، يجب حفظ الأمر ورمز الخروج، وجود الملف وحجمه، نتيجة `xorriso`, ومخرجات `sha256sum --check`. لا تعتبر `bash -n` أو الاختبارات المصدرية بديلاً عن ذلك.

## اختبارات قبول لازمة لاحقاً

- اختبار حل كل حزم `config/package-lists/iso-x.list.chroot` من مستودعات Trixie amd64 أثناء البناء.
- إقلاع صورة واحدة على BIOS وأخرى/نفس الصورة على UEFI باستخدام QEMU وOVMF، ثم اختبار المثبّت والجلسة.
- اختبار لوحة المفاتيح العربية/الإنجليزية، الصوت، الشبكة، مركز التطبيقات، المحرر والملفات داخل GTK فعلي.
- اختبار Secure Boot لا يُجرى أو يُعلن مدعوماً دون سلسلة ثقة موثقة؛ watermark معطلة افتراضياً ولا تمنع الإقلاع عند غيابها.
- اختبار أجهزة فعلية للطباعة والبلوتوث والواي فاي وبطاقات الرسوميات، وقياس الأداء على جهاز 2GB RAM.
- لم يُبنَ مشهد Bevy ولم تُختبر الواجهة الرسومية. Rust/Cargo غير مطلوبين لبناء ISO الافتراضي.

تُسجّل النتائج النهائية والأدلة في `AUDIT.md` و`docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` بعد تنفيذها.
