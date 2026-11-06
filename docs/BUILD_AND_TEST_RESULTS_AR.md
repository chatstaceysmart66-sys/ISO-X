# نتائج البناء والاختبارات — ISO-X 0.4.0

## تدقيق الحالة والبوابة — 2026-11-06

| الأمر/الفحص | النتيجة | الدليل/القيد |
|---|---|---|
| `python3 -m pytest -q` | **PASS**, exit 0 — 65 passed، 1 skipped، 4 subtests passed | `/tmp/isox-source-audit-final.NAU83z/pytest.log` |
| `bash tests/smoke.sh` | **PASS**, exit 0 — 27 اختبارًا | `/tmp/isox-source-audit-final.NAU83z/smoke.log` |
| `python3 scripts/run-source-checks.py /tmp/isox-source-audit-final.NAU83z /tmp/isox-source-audit-final.NAU83z/pycache` | **89 PASS، 0 FAIL، 1 SKIP، 4 NOT_RUN**؛ exit 1 بسبب NOT_RUN | `source-tests.json` وسجلات الأوامر في مجلد الأدلة نفسه. المفقود: `sfdisk` و`xvfb-run`/`xdotool`/`wmctrl`/`openbox` و`shellcheck` و`desktop-file-validate`. |
| `bash tests/test_desktop_readiness.sh` | **PASS**, exit 0 | يشترط وجود Openbox وTint2 وتطبيق ISO-X ونافذته؛ سيناريو غياب Tint2 يجب أن يفشل. |
| `bash tests/test_qemu_headless_validation.sh` | **PASS**, exit 0 | يثبت أن وجود `segfault` في سجل الضيف يفشل التصنيف كـ`GUEST_RUNTIME_CRASH` حتى بعد علامة الجاهزية. |
| `git diff --check` | **PASS**, exit 0 | لا يثبت صحة build أو تشغيل ISO. |
| CI `42172193542` على `be001c0` | jobs كلها **SUCCESS** | أقدم من التغييرات غير الملتزمة الحالية. سجلا BIOS/UEFI يثبتان segfault لـTint2 قبل readiness رغم نجاح البوابتين؛ لا يُحتسب هذا دليلاً على حالة التغييرات الحالية. |
| بناء ISO محلي وفحص SquashFS | **NOT_RUN** | UID 1000، مساحة متاحة 18 GiB مقابل 20 GiB حد البناء، وأدوات `lb`, `xorriso`, `debootstrap`, `mksquashfs`, `qemu-system-x86_64` غير موجودة. |
| BIOS/UEFI للتغييرات المحلية | **NOT_RUN** | يتطلب CI/build جديدًا؛ يجب التحقق من بقاء Tint2 حيًا بعد readiness، وأن سجل segfault يفشل البوابة. |

## تحقيق CI — 2026-11-06، التشغيل 42206164401

| المسألة | الدليل | الاستنتاج/التغيير |
|---|---|---|
| UEFI `wmctrl` segfault | `evidence/uefi/qemu-uefi-headless-serial.log` يسجل عمليتي segfault عند 134.222499 و138.077028 ثانية. مسبار الجاهزية يستدعي `wmctrl -l -G` كل ثانية أثناء الانتظار. | الارتباط بين الانهيار والاستدعاء مثبت بالتوقيت والسياق، لكن سبباً داخلياً في wmctrl أو libc غير مثبت. استبدل فحص النافذة بـ`xwininfo -root -tree` وأضيفت حزمة `x11-utils`؛ الاختبار الحقيقي ينتظر إعادة CI. |
| BIOS cancelled | `bios-job.log` يبين أن apt كان ينزل `qemu-system-x86` والتبعيات، وانتهى الأمر بـ`The operation was canceled` عند 20 دقيقة قبل تنزيل ISO. أظهر الحل 85 حزمة و46.3MB، منها توصيات رسومية. | السبب مهلة الوظيفة أثناء تثبيت QEMU، لا فشل BIOS boot. أضيف `--no-install-recommends` ورفعت المهلة إلى 30 دقيقة؛ يلزم إعادة CI للتحقق. |
| تثبيت الأصول وصحة البناء | artifact `results.json`: البناء وفحص البنية PASS، الحجم 2,785,017,856 بايت، SHA-256 `d3330d055e006f02096d931bf2eb634dc20834b4bf67af390ffc3359eb808453`. | ISO مرشح CI تشخيصي فقط. لا تعني نتيجة البناء أن UEFI/BIOS اجتازا. |

## جولة أصول المرجع — 2026-11-06

| الأمر/الفحص | الحالة | الدليل/القيد |
|---|---|---|
| `python3 scripts/extract-reference-assets.py --output-dir assets/reference` | **PASS** | استخرج 3 أدوار من 6 Data URI؛ manifest يسجل MIME/JPEG magic والأبعاد والنسب والبصمات. المصدر هو `iso-x 22.html` المرشح لا المرفق الأصلي غير المتاح. |
| `python3 -m pytest -q` | **PASS** — exit 0، `65 passed, 1 skipped, 4 subtests passed` | تشمل اختبار استخراج الصور الإضافية ومساراتها وعقد الملاءمة. |
| تحقق بصمات rootfs عبر `scripts/verify-reference-assets.py` | **PASS** في rootfs اصطناعي | اختبارات البناء تنسخ أصول generator إلى شجرة مؤقتة ثم تتحقق من SHA-256 للمصدر والأصول والنسخ المشتقة؛ هذا ليس rootfs أو SquashFS من live-build. |
| `bash tests/smoke.sh` | **PASS** — exit 0 | شغّل 27 اختبار smoke مع فحوص الخزنة والتوقيع وUSB وQEMU المصدرية؛ لا يثبت ISO/إقلاعاً. |
| `python3 tests/test_source_config.py && python3 tests/test_upstream_integration.py` | **PASS** — exit 0 | يؤكد الإعدادات المصدرية وربط الأصول الحديثة وعدم مرحّلة SVG القديم. |
| `py_compile` للملفات المعدلة، `bash -n` لسكربتات البناء/hooks، و`git diff --check` | **PASS** — exit 0 | تحقق syntax وwhitespace، وليس تشغيل واجهة أو build. |
| فحص بصري لملفات JPEG المستخرجة | **PASS** على الأصول المصدرية | Wallpaper مشهد كامل 16:9 بتنين يميناً؛ boot مشهد مستقل كامل؛ العلامة 100×106. لا تعدّ هذه لقطات Desktop/Plymouth. |
| خلفية PCManFM وLightDM من المصدر إلى rootfs | **SOURCE-CONFIGURED / ISO UNVERIFIED** | build يثبت JPEG المرجع؛ لا يوجد rootfs مبني لفحصه. |
| Plymouth من المصدر إلى initramfs | **SOURCE-CONFIGURED / BOOT UNVERIFIED** | hook يتحقق من مجلد theme ويحدّث initramfs؛ لم يُبنَ أو يُقلع. |
| دقات 1366×768، 1280×720، 1920×1080، 1920×1200، 2560×1440، 3840×2160 | **حساب الملاءمة فقط؛ لقطات NOT_RUN** | اختبار المصدر يفحص `fit` وحساب الاحتواء؛ لا توجد لقطات X11/QEMU بعد. |
| بناء ISO وفحص SquashFS وSHA-256 | **NOT_RUN** | المضيف UID 1000، Ubuntu 24.04، 18 GiB متاحة (<20 المطلوبة)، وأدوات `lb`, `xorriso`, `debootstrap`, `mksquashfs`, `qemu-system-x86_64` غير موجودة. |
| BIOS/UEFI وPersistence والصوت والعتاد الحقيقي | **NOT_RUN / UNVERIFIED** | تشغيل CI `42172193542` على HEAD الأساسي أقدم من تغييرات المصدر الحالية؛ Persistence والصوت والعتاد الحقيقي لم تختبر. |
| Tint2 segfault | **FAIL في CI السابق / إصلاح الجذر غير مثبت** | سجلا BIOS/UEFI من `42172193542` يسجلان الانهيار قبل readiness؛ أضيف فحص العملية ومصنف السجل واختباراهما محليًا فقط. |

أثناء التحقق، انتهى تشغيل smoke متزامن مع الاختبارات بإشارة 143، وأظهر تشغيل لاحق معزول إخفاق assertion في فحص QEMU؛ نجح فحص `tests/test_qemu_headless_validation.sh` منفرداً، ثم نجح تشغيلان كاملان منفصلان لـ`bash tests/smoke.sh` برمز 0. لم يُحدد سبب التذبذب؛ النتائج الخضراء لا تثبت عدم وجود flake مستقبلي.

## أحدث تحقق — 2026-11-02

| العنصر | الحالة والدليل |
|---|---|
| الاختبار المستهدف لإعداد PCManFM | **PASS** — `python3 -m pytest -q tests/test_build_contracts.py::test_user_click_and_menu_contrast_settings_are_applied_and_built`؛ exit 0، `1 passed`. يؤكد أن الملف المولّد يضبط `wallpaper_mode=fit` ولا يستخدم `stretch`. |
| اختبارات إعداد البناء والمصدر بعد عزل tint2 | **PASS** — `python3 -m pytest -q tests/test_build_contracts.py`؛ exit 0، `19 passed`. `python3 tests/test_source_config.py`؛ exit 0. |
| Smoke suite بعد التعديلات | **PASS** — `bash tests/smoke.sh`؛ exit 0، 27 اختبارًا وسائر فحوص smoke المطبوعة PASS. لا يثبت ISO أو إقلاعًا. |
| اختبار عزل tint2 | أزيل عنصر البطارية الداخلي `B` من إعداد اللوحة، وأضيف عقد مصدر يتأكد من بقاء `xfce4-power-manager` مثبتًا ومشغّلًا. **لا يثبت هذا زوال segfault**؛ يتطلب ISO جديدة وإقلاع BIOS/UEFI وفحص السجلات ومؤشر البطارية. |
| CI على HEAD السابق | `41500842716` على `f7e188293ac86d10a7b2205135605a2086fe2e20`: source-check وbuild وBIOS وUEFI **SUCCESS**؛ `promote` كان **IN_PROGRESS** عند الفحص. رابط التشغيل: https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/41500842716 |
| ISO التشخيصية لذلك التشغيل | الحجم `2,782,298,112` بايت؛ SHA-256 `681df93f90cbf838720643d01b7748837b10d7f8ca9e498cf74e3fde6428e375`. لا تشمل تغيير `fit` المحلي، وليست إصدارًا. |
| أعطال tint2 | **FAIL / غير محلول** — سجل UEFI من التشغيل نفسه يظهر segfault عند `137.191616` ثانية، ثم علامة الجاهزية لاحقًا. لا تُعد علامة الجاهزية نجاحًا للشريط. |
| المرجع المرفق وData URI | **NOT_RUN / محجوب** — الملف الأصلي غير متاح؛ لا بصمة ولا استخراج أو مطابقة أصول. |
| ISO جديدة بعد التغيير | **NOT_RUN** — الاختبار المحلي لا يبني ISO؛ لا تُنسب ملفات staging/rootfs/ISO إلى هذا التعديل. |

**تاريخ مراجعة السجل:** 2026-11-02
**الفرع:** `fix/isox-build-and-runtime`  
**الهدف:** Debian GNU/Linux 13 Trixie، amd64.  
**الحالة:** CI `41494710750` اكتمل بنجاح على commit `35b65ff`: 88 فحص مصدر، وبناء ISO وفحص SHA-256 وEl Torito/System Area، وإقلاع تشخيصي BIOS/UEFI، وإقلاع عادي أظهر سطح ISO-X في BIOS وUEFI. شمل البناء تغييرات فهرس APT وgzip وحزم الصوت. الـartifacts مرشحات CI وليست إصدارًا؛ Persistence بعد reboot وAPT الفعلي والصوت على جهاز حقيقي لم تُختبر.

## تحقق التعديلات الحالية — 2026-11-02

إضافات تحقق الجولة الحالية: ضبط `--apt-indices true` وصل فعليًا إلى live-build في سجل البناء، وثُبتت حزم UCM/firmware Intel في build؛ وعولج فساد gzip الجزئي في AppStream. اجتازت الشيفرة محليًا المجموعة الكاملة (**63 passed، 1 skipped، 4 subtests passed**) و`bash tests/smoke.sh`، ثم اجتاز CI الذي شملها 88 فحص مصدر. لا يحتوي Codespace أدوات ALSA/PipeWire أو جهاز إخراج، لذا لا يوجد اختبار تشغيل/سماع للصوت.

هذه نتائج التعديلات الأخيرة على الشيفرة المصدرية، ولا تستبدل أدلة البناء التاريخية أدناه:

| الأمر | النتيجة | الملاحظة |
|---|---|---|
| `python3 -m pytest -q` | **63 passed، 1 skipped، 4 subtests passed** | مجموعة الاختبارات بعد تغييرات الفهارس وgzip وحزم الصوت، قبل مزامنة EWMH الإضافية لاختبار GTK. |
| `bash tests/smoke.sh` | **نجاح، exit 0** | فحوص المصدر والخزنة والتوقيع وUSB وQEMU السلبي؛ لا يثبت الإقلاع الفعلي. |
| `xvfb-run -a -s '-screen 0 1366x1024x24' /usr/bin/python3 tests/test_gtk_window_runtime.py` | **نجاح مرتين متتاليتين** | ينتظر الاختبار تغير حالة EWMH بعد تصغير/تكبير النافذة قبل التحقق من أبعادها؛ تحقق النوافذ وإدخال AR/EN. |
| `xvfb-run ... tests/capture_store_ui.py /tmp/isox-store-runtime-6799d5d` | **نجاح** | عرض المتجر بالعربية والإنجليزية واختبر تبويب التصنيف ببيانات تركيبية فقط؛ لا يثبت قائمة APT أو التثبيت. |
| `git diff --check`, `sh -n auto/config`, و`py_compile` | **نجاح، exit 0** | تحقق whitespace وصياغة ملف live-build وملفات Python المعدلة. |
| وسيطات `lb config` | **نجاح، exit 0** | نفّذ اختبار عقد `auto/config` مع `lb` وهمي وأثبت وصول `--apt-indices true` الفعلي. |
| `python3 -m pytest -q` بعد مزامنة EWMH | **63 passed، 1 skipped، 4 subtests passed** | أحدث اختبار محلي كامل. |
| اختبار GTK/Openbox بعد مزامنة EWMH | **نجاح مرتين متتاليتين** | يؤكد أن اختبار التكبير ينتظر تحديث حالة النافذة قبل قياس حجمها. |
| CI run `41494710750` على commit `35b65ff` | **نجاح؛ 88 فحصًا، وبناء و4 بوابات قبول** | اجتاز source-check وISO build/structure وBIOS/UEFI التشخيصيين. كما نجح إقلاع ISO العادي ورسم سطح ISO-X في BIOS وUEFI. فعّل `--apt-indices true` وثبّت الحزم الصوتية المضافة. |
| `pytest` داخل CI `41494710750` | **64 passed** | شمل اختبار xorriso المتكامل؛ المضيف المحلي لا يملك xorriso لذا يتخطى هذا الاختبار. مجموع 88 يتضمن حالات pytest وفحوص المصدر الإضافية. |
| ISO التشخيصية في CI `41494710750` | **بنية سليمة؛ ليس artifact إصدار** | الحجم `2,782,298,112` بايت؛ SHA-256: `7e825b4d26f6f8843dfa1feb35d1f8d98b4c555eccb4cb4b940dd4065f875c70`. وُسمت صراحةً `CI_BOOT_DIAGNOSTIC_NOT_RELEASE`. |
| APT على ISO الحالية بعد إبقاء الفهارس | **لم يُثبت** | يلزم بناء صورة وفحص `/var/lib/apt/lists` وحالة المتجر فيها. |
| APT فعلي، persistence بعد reboot، صوت مسموع، وعتاد حقيقي | **غير مثبتة** | بوابات BIOS/UEFI في CI نجحت لصورة CI، لكنها لا تثبت هذه الوظائف على جهاز أو عمليات الحزم الفعلية. |

تُجهّز اختصارات Google وYouTube وChatGPT كروابط سطح مكتب تفتح Firefox ESR، بينما يبقى Firefox نفسه مشغلاً مثبتاً في tint2. اختبار GTK شغّل تطبيقاً مؤقتاً عبر desktop entry تجريبي؛ لم يُختبر النقر على اختصارات المواقع في جلسة إصدار.

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
