# تدقيق الملفات الفردية — ISO-X 0.4.0

## حدود اللقطة والنتيجة

- تاريخ الفحص: 2026-11-06 UTC؛ الفرع `fix/isox-build-and-runtime`؛ رأس اللقطة المرجعية `b15647056fc609fba9e2d26748864dcc5ec50487`.
- قبل التعديل: 163 مساراً متتبعاً، بلا ملفات غير متتبعة، والـstash الموجود لم يُطبق أو يُحذف. لا توجد symlinks متتبعة.
- أُزيلت سبعة أصول مرئية قديمة بعد فحص استدعاءاتها. أضيفت وثائق التدقيق الثلاث وسكربت مراقبة الاستقرار؛ العدد المتوقع بعد تثبيت هذه التغييرات 160 مساراً. ملفات `.pyc` و`.pytest_cache` الظاهرة محلياً مولدة ومهملة في Git وليست مدخلات بناء.
- جرد المسارات كامل على لقطة Git؛ الفحص الدلالي المفصل أدناه يميز بين العلاقات التي اختُبرت وبين كل ما بقي غير متحقق. **لا أدّعي أن كل سطر من كل وثيقة تاريخية أو كل تطبيق قد خضع لمراجعة يدوية كاملة أو لاختبار runtime.**
- كان `HEAD` متزامناً مع `origin` قبل التغيير، والـstash السابق بقي محفوظاً. اكتمل CI `42221229398` على `b15647056fc609fba9e2d26748864dcc5ec50487`: source-check وbuild وBIOS وUEFI وpromote وacceptance-summary كلها **SUCCESS**. هذه النتيجة لا تشمل التغييرات المحلية اللاحقة.

## تصنيف الملفات ومسؤولياتها

| المسارات | التصنيف والدور الفعلي | المدخلات/المخرجات والاعتماديات | الاختبار/النتيجة الحالية |
|---|---|---|---|
| `.github/workflows/iso-build.yml`, `auto/config`, `build.sh`, `scripts/build-iso.sh`, `scripts/ci-build-in-trixie.sh`, `config/package-lists/*`, `config/bootloaders/*`, `config/hooks/live/*` | بناء المصدر والصورة؛ hooks تعدّل rootfs داخل live-build ولا تعمل كخدمات جلسة. | إعدادات Debian Trixie/amd64، حزم Debian، staging، ثم ISO تشخيصية؛ يستهلك CI artifacts عبر أسماء متفق عليها. | أحدث CI `42221229398` اجتاز على الأساس؛ المصدر الحالي 93 PASS/0 FAIL/1 SKIP، لكن build وإقلاع هذه التغييرات لم ينفذا بعد. |
| `app/iso_x_gtk.py`, `app/isox_appcenter.py`, `app/isox_store_backend.py`, `app/isox_launcher.py`, `app/isox_keyboard.py`, `app/isox_welcome.py` | مصادر تطبيقات GTK وواجهاتها الخلفية؛ تنسخ معظمها إلى `/usr/share/iso-x` وتطلق عبر `/usr/local/bin` أو Openbox. | GTK/GI وGIO وAPT/Flatpak وXKB وملفات قاعدة البيانات وDesktop Entries؛ التأثيرات تشمل عمليات ملفات/حزم/تطبيقات. | اختبارات الوحدات وXvfb وCI موجودة، لكنها لا تثبت نجاح كل عملية حقيقية، ولا معاملة APT/Polkit فعلية. |
| `app/iso_x_shell.py` | واجهة Tk القديمة؛ ليست ضمن staging الحالي. | لا مستهلك بناء/جلسة معروف في `scripts/build-iso.sh`. | `tests/test_build_contracts.py` يثبت عدم تقديمها كواجهة ثانية؛ غير مطلوبة كمسار runtime. |
| `assets/iso-x.html` | صفحة بدء Firefox محلية، وليست سطح المكتب أو واجهة HTML الأساسية. لا تحتوي JavaScript ولا صوراً مضمنة؛ CSS داخل الملف وصورة الشعار وREADME محليان عبر `file:///`. | ينسخها البناء إلى `/usr/share/iso-x/start.html`؛ hook Firefox يحددها كصفحة بدء؛ الملف المحلي يقرأ `/usr/share/iso-x/assets/reference-dragon-mark.jpg` و`/usr/share/doc/iso-x/README_AR.md`. | عقد staging أُضيف إلى `tests/test_build_contracts.py`. لم يُثبت فتحها داخل Firefox من ISO نهائية. |
| `design/reference/iso-x-reference.html`, `iso-x 22.html` | مرجع بصري محفوظ ومرشح مصدر تاريخي؛ ليسا واجهة المنتج المشغّلة. ملف المرجع 1,181,650 بايت، يحوي ستة Data URI وثلاث صور فريدة (خلفية/إقلاع/شعار)، CSS وJavaScript مضمنين. | `scripts/generate-brand-assets.py` → `scripts/extract-reference-assets.py` → `assets/reference/reference-assets.json` والأصول المشتقة. هوية هذا المرشح ليست مثبتة كهوية المرفق المحدد `iso-x (1).txt`. | فحوص المصدر والـmanifest/rootfs الاصطناعي متاحة؛ اختبار العرض الكامل والتطابق مع المرفق **UNVERIFIED**. |
| `assets/reference/*`, `assets/sounds/*` | صور المرجع الرسمية الحالية ومشتقاتها، وأصوات متجر؛ لا تُحذف لمجرد أنها صور. | ملفات المرجع الأصلية تذهب إلى الخلفية وLightDM وPlymouth والشعار؛ WAV ينسخ إلى `/usr/share/iso-x/assets/sounds`. | فُحصت صور JPEG/PNG المتبقية بــPillow: MIME/decoder/الأبعاد/mode؛ manifest يحمل SHA-256. التحقق النهائي من كل نسخة داخل SquashFS واستخدام كل عنصر على جهاز فعلي **UNVERIFIED**. |
| `desktop/*`, `plymouth/isox/*`, `scripts/apply-windows-look.sh`, `config/hooks/live/0300-isox-services.hook.chroot` | إعدادات Openbox وTint2 وDesktop Entries وخلفية PCManFM/LightDM وثيم Plymouth. | Openbox يملك النوافذ والقائمة؛ Tint2 اللوحة؛ PCManFM سطح المكتب والأيقونات؛ GTK التطبيقات الأصلية؛ LightDM/NetworkManager/PipeWire خدمات منفصلة. | اختبارات XML/Desktop Entry وعقود المصدر ولقطات QEMU متاحة؛ لا تثبت كل زر/خدمة أو العتاد الحقيقي. |
| `scripts/*.py`, `scripts/*.sh`, `scripts/isox-*`, `scripts/write-usb.sh` | أدوات بناء وتشغيل واختبار وUSB وصيانة؛ بعضها فقط يدخل الصورة. | المدخلات ومسارات النسخ موضحة في `FILE_RELATIONSHIP_MATRIX_AR.md`؛ أوامر النظام تنفذ بامتيازات المستخدم أو عبر Polkit/`sudo` عند الحاجة. | فحوص syntax واختبارات وحدات/fixtures؛ كتابة USB حقيقية ممنوعة وغير منفذة، واختبار Persistence بعد reboot غير منفذ. |
| `systemd/*`, `initramfs/*`, `kernel/isox-watermark/*` | خدمات preload/zram وقياس readiness التشخيصي، ومراقبة استقرار بعد marker، ومسار watermark اختياري. | وحدات systemd تستدعي executables المنسوخة من build؛ مراقب CI يعيد فحص Openbox وTint2 ونافذة ISO-X؛ watermark مشروط بـ`ISOX_ENABLE_WATERMARK=1` ومفاتيح خارج الشجرة. | مراقبة الاستقرار واختباراتها المصدرية مضافة؛ لم تُبنَ/تُختبر بعد داخل guest. قياس الأداء ودمج watermark الفعلي **UNVERIFIED/NOT_RUN**. |
| `db/*` | مخطط SQLite وترقيات التطبيق. | `app/iso_x_gtk.py` يقرأ المخطط والترقيات؛ `scripts/build-iso.sh` ينسخها إلى `/usr/share/iso-x/db`. | `tests/test_schema.py` وعقود النسخ؛ ترقية قاعدة مستخدم فعلية لكل حالة قديمة غير مثبتة. |
| `tests/*` | وحدات/عقود/اختبارات Xvfb/QEMU وUSB وwatermark؛ لا تدخل ISO. | تستهلك ملفات المصدر وfixtures، وبعضها يتطلب QEMU أو Xvfb أو أدوات نظام. | CI `42221229398` اجتاز المصدر والبناء وBIOS/UEFI والترويج على commit الأساس؛ اختبارات المراقبة الجديدة ناجحة محلياً، والـguest CI على التغيير غير منفذ بعد. |
| `README*`, `AUDIT.md`, `CHANGELOG.md`, `STATUS_AR.md`, `docs/*`, `LICENSE.txt`, `THIRD_PARTY_*` | توثيق/ترخيص؛ بعض الوثائق التاريخية مبنية على لقطات قديمة. | لا تتحكم في runtime إلا الوثائق التي ينسخها build صراحة إلى `/usr/share/doc/iso-x`. | الوثائق التاريخية يجب ألا تُقرأ كحالة قبول حالية؛ أُضيفت هذه الوثيقة والمصفوفات لتكون مرجع الحالة الراهنة. |
| `three-d-login/Cargo.toml`, `three-d-login/src/main.rs` | مشهد Rust/Bevy اختياري، لا يحل محل GTK في الإقلاع العادي. | يتطلب `ISOX_BUILD_CINEMATIC=1` وRust/Cargo وخط؛ يدخل binary/موارد عند نجاح البناء فقط. | اختبارات العقود فقط؛ ليس مسار إقلاع افتراضي ولا تحقق بصرياً. |

## فحص الأصول القديمة المحذوفة

حُذفت الملفات التالية بعد `rg` شامل في `app/`, `config/`, `desktop/`, `scripts/`, `systemd/`, `plymouth/`, `three-d-login/`, `initramfs/`, و`auto/`. لم يظهر لها مستهلك runtime أو مسار staging؛ كانت المراجع الباقية في اختبارات ومواد تاريخية فقط. فُحصت بصماتها وMIME قبل الحذف:

| المسار | النوع | SHA-256 قبل الحذف | الدليل على عدم الاستخدام الحالي |
|---|---|---|---|
| `assets/iso-x-boot.png` | PNG | `4a5ff48344ad8c9f81ac37191ca411a49b4b13269bceab1ba25206508edac6a1` | لا مستهلك runtime أو staging. |
| `assets/iso-x-boot.svg` | SVG | `f4c9487e41f76a3c79804ea3eb695fd531846a00f0d501f7798647406c80d98e` | مرجعه الداخلي القديم إلى `iso-x-dragon.svg`؛ لا مستهلك runtime. |
| `assets/iso-x-desktop-wallpaper.png` | PNG | `f07c2e1d025f6b06b03959dcb3cd81a11194b0a8ecfb9be62cef5cd1975bf07d` | PCManFM وLightDM يأخذان JPEG من مرجع التصميم الحالي. |
| `assets/iso-x-desktop-wallpaper.svg` | SVG | `c04b8214835cd36b22c2a71c04fdd996e891120c07b63090c5f73b769ffbbbba` | لا consumer؛ ملف profile الحالي يستعمل JPEG المرجع. |
| `assets/iso-x-dragon.png` | PNG | `5b04761e3b61ce461c7f1f6cae600f0990e54b28bd9d7ca97352331e6353a8e5` | الشعار الحالي يأتي من `assets/reference/dragon-mark-original.jpg`؛ لا مستهلك runtime. |
| `assets/iso-x-dragon.svg` | SVG | `779b24433e420ab399b226ebf35a9cba1b1b9657d24cad318db4d21bf02e72a3` | لا مستهلك runtime؛ مشتقات المرجع هي التي تُنسخ. |
| `assets/iso-x-plymouth.png` | PNG | `06a62213e5777556c48a468582e45592e90538fe4bc4d067610b80f5e7861c92` | Plymouth يأخذ `boot-screen.png` المشتق من الأصل المرجعي. |

حُدّثت `tests/test_source_config.py` لتفشل إن عادت هذه الأصول أو أُدخلت للبناء. لم تُحذف `assets/iso-x.html` أو `assets/reference/*` أو ملفات المعاينة؛ لكل منها مستهلك أو صفة مرجعية موثقة.

## سجل المسارات الحالي

هذه قائمة كاملة بالمسارات الموجودة بعد التعديل. الفئات في الجدول أعلاه تصنف الغرض؛ علاقات المنتج/المستهلك والاختبارات محددة في مصفوفة العلاقات. `docs/` و`tests/` توثيق واختبار وليسا ملفات runtime إلا ما ينسخه البناء صراحة.

| المجموعة | المسارات |
|---|---|
| جذر وCI | `.github/workflows/iso-build.yml`; `.gitignore`; `AUDIT.md`; `CHANGELOG.md`; `LICENSE.txt`; `README.md`; `README_AR.md`; `STATUS_AR.md`; `THIRD_PARTY_NOTICES.md`; `build.sh`; `iso-x 22.html` |
| تطبيقات | `app/iso_x_gtk.py`; `app/iso_x_shell.py`; `app/isox_appcenter.py`; `app/isox_keyboard.py`; `app/isox_launcher.py`; `app/isox_store_backend.py`; `app/isox_welcome.py` |
| الأصول | `assets/iso-x.html`; `assets/reference/boot-screen-original.jpg`; `assets/reference/boot-screen.png`; `assets/reference/desktop-wallpaper-original.jpg`; `assets/reference/dragon-mark-icon-96.png`; `assets/reference/dragon-mark-original.jpg`; `assets/reference/dragon-mark.png`; `assets/reference/reference-assets.json`; `assets/sounds/download-complete.wav`; `assets/sounds/error.wav`; `assets/sounds/notification.wav`; `assets/sounds/success.wav`; `assets/sounds/warning.wav` |
| بناء النظام | `auto/config`; `config/bootloaders/grub-pc/grub.cfg`; `config/bootloaders/isolinux/isolinux.cfg`; `config/bootloaders/syslinux_common/live.cfg.in`; `config/hooks/live/0050-isox-locales.hook.chroot`; `config/hooks/live/0100-isox-watermark.hook.chroot`; `config/hooks/live/0200-isox-plymouth.hook.chroot`; `config/hooks/live/0300-isox-services.hook.chroot`; `config/hooks/live/0400-isox-firefox-defaults.hook.chroot`; `config/hooks/live/0500-isox-menu-contrast.hook.chroot`; `config/package-lists/iso-x.list.chroot` |
| قاعدة البيانات والتصميم | `db/migrations/002_isox_020.sql`; `db/migrations/003_isox_031.sql`; `db/migrations/004_isox_040.sql`; `db/schema.sql`; `design/reference/iso-x-reference.html` |
| سطح المكتب | `desktop/chatgpt.desktop`; `desktop/google.desktop`; `desktop/isox-launcher.desktop`; `desktop/isox-store.desktop`; `desktop/isox-welcome.desktop`; `desktop/openbox-menu.xml`; `desktop/openbox-rc.xml`; `desktop/tint2rc`; `desktop/youtube.desktop` |
| الوثائق | `docs/ARCHITECTURE_AR.md`; `docs/ARTWORK_REFRESH_2026-10_AR.md`; `docs/BUILD_AND_CONTINUE_AR.md`; `docs/BUILD_AND_TEST_RESULTS_AR.md`; `docs/FILE_INVENTORY_AR.md`; `docs/GAP_ANALYSIS_0.2.0_AR.md`; `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md`; `docs/INTEGRATION_AUDIT.md`; `docs/KNOWN_WARNINGS_AR.md`; `docs/PROJECT_MAP_AR.md`; `docs/QEMU_ACCEPTANCE_AR.md`; `docs/REFERENCE_DESIGN_MAPPING_AR.md`; `docs/RELEASE_NOTES_0.3.0_AR.md`; `docs/ROADMAP_AR.md`; `docs/RUNTIME_REPAIR_0.4.0_AR.md`; `docs/SHORTCUTS_AR.md`; `docs/THIRD_PARTY_LICENSES.md`; `docs/UPSTREAM_INTEGRATION_AR.md`; `docs/UPSTREAM_REVIEW_AR.md`; `docs/UX_STANDARDS_AR.md`; `docs/WORKLOG_AR.md`; `docs/audit/DEFECT_REGISTER.md`; `docs/audit/DEPENDENCY_GRAPH.md`; `docs/audit/FEATURE_TRACEABILITY.md`; `docs/audit/FILE_BY_FILE_AUDIT_AR.md`; `docs/audit/FILE_INVENTORY.md`; `docs/audit/FILE_RELATIONSHIP_MATRIX_AR.md`; `docs/audit/FINAL_AUDIT_REPORT.md`; `docs/audit/INTEGRATION_TEST_MATRIX.md`; `docs/audit/REPAIR_LOG.md`; `docs/audit/REQUIREMENTS_TRACEABILITY_AR.md`; `docs/previews/isox-welcome-design-preview.png`; `docs/ui-evidence/README_AR.md`; `docs/ui-evidence/store-ar.png`; `docs/ui-evidence/store-en.png` |
| initramfs/kernel | `initramfs/hooks/isox-watermark`; `initramfs/scripts/init-premount/isox-watermark-guard`; `kernel/isox-watermark/Makefile`; `kernel/isox-watermark/dkms.conf`; `kernel/isox-watermark/isox_watermark.c`; `kernel/isox-watermark/watermark_bytes.h` |
| Plymouth | `plymouth/isox/isox.plymouth`; `plymouth/isox/isox.script` |
| سكربتات | `scripts/apply-windows-look.sh`; `scripts/build-iso.sh`; `scripts/ci-build-in-trixie.sh`; `scripts/collect-performance.sh`; `scripts/create-ci-results.py`; `scripts/create-user-iso-metadata.py`; `scripts/create-user-iso.py`; `scripts/encode-watermark.py`; `scripts/extract-reference-assets.py`; `scripts/generate-brand-assets.py`; `scripts/generate-dev-signing-key.sh`; `scripts/generate-store-sounds.py`; `scripts/install-build-deps.sh`; `scripts/isox-ci-ready.sh`; `scripts/isox-ci-stability.sh`; `scripts/isox-desktop-window-ready.sh`; `scripts/isox-preload.py`; `scripts/isox-run.py`; `scripts/isox-snap-window.sh`; `scripts/isox-speedtest`; `scripts/isox-zram-setup`; `scripts/read-ci-nonce.sh`; `scripts/record-demo.sh`; `scripts/run-source-checks.py`; `scripts/secure-vault.py`; `scripts/secure-vault.sh`; `scripts/secureboot-enroll.sh`; `scripts/toggle-airplane.sh`; `scripts/validate-iso-boot-config.sh`; `scripts/verify-reference-assets.py`; `scripts/write-usb.sh` |
| خدمات | `systemd/isox-ci-ready.service`; `systemd/isox-ci-ready.timer`; `systemd/isox-preload.service`; `systemd/isox-preload.timer`; `systemd/isox-zram.service` |
| اختبارات وأدواتها | `tests/capture_store_ui.py`; `tests/ci-results.schema.json`; `tests/qemu-acceptance.sh`; `tests/qemu-runner.py`; `tests/smoke.sh`; `tests/test_build_contracts.py`; `tests/test_ci_results.py`; `tests/test_desktop_readiness.sh`; `tests/test_gtk_window_runtime.py`; `tests/test_initramfs_watermark_guard.sh`; `tests/test_keyboard.py`; `tests/test_qemu_headless_validation.sh`; `tests/test_schema.py`; `tests/test_secure_vault.py`; `tests/test_secureboot_validation.sh`; `tests/test_source_config.py`; `tests/test_store_backend.py`; `tests/test_upstream_integration.py`; `tests/test_user_iso.py`; `tests/test_watermark_integrity.sh`; `tests/test_workflow_contracts.py`; `tests/test_write_usb_persistence.sh`; `tests/test_write_usb_validation.sh` |
| مشهد اختياري | `three-d-login/Cargo.toml`; `three-d-login/src/main.rs` |

## حالة الفحص الفردي

| المستوى | النتيجة |
|---|---|
| تعداد tracked paths وignored caches وsymlinks | **PASS** على اللقطة المذكورة؛ لا symlinks متتبعة، 163 tracked قبل التعديل، و160 مساراً بعد 7 حذف و4 إضافات؛ لا untracked قبل التعديل. |
| MIME/magic/أبعاد الصور الحالية | **PASS** للصور الست تحت `assets/reference/` بأداة Pillow؛ صور المعاينة واللقطات تحت `docs/` ليست موارد runtime. |
| JSON manifest وPython syntax وXML/YAML/desktop/workflow validators | **93 PASS، 0 FAIL، 1 SKIP، 0 NOT_RUN** محلياً؛ يشمل compileall وpytest وShellCheck وdesktop-file-validate وXML/SVG. اختبارات المصدر لا تغني عن إعادة CI للبناء والضيف. |
| قراءة كل ملف نصي وكل test يدوياً | **غير مكتمل**؛ فُحصت الملفات المرتبطة مباشرة والتوثيق/الاختبارات المذكورة، لكن لم تُراجع كل أسطر جميع الوثائق التاريخية والبرامج والاختبارات منفردة. |
| بناء ISO الحالي وقراءة SquashFS بعد حذف الأصول | **NOT_RUN بعد هذه التغييرات**؛ أحدث CI `42221229398` بني على `b156470` قبل حذف الأصول وتعديل عقود الاستقرار. |
| BIOS/UEFI وواجهة مرئية وPersistence على النسخة المعدلة | **NOT_RUN بعد هذه التغييرات**؛ run `42221229398` نجح على `b156470` قبل التعديلات الحالية؛ persistence reboot لم يُختبر في ذلك التشغيل أيضاً. |

## النتيجة

الملفات السبعة القديمة التي ثبت أنها غير مستخدمة أزيلت، وموارد المرجع الحالية بقيت. أضيفت مراقبة 30 ثانية بعد readiness، مع اختبارات مصدرية للفقد والاستقرار. صفحة `assets/iso-x.html` تعمل كصفحة بدء Firefox ولا تحقق وحدها مطلب سطح مكتب HTML؛ الواجهة الأساسية الحالية تظل GTK/Openbox. لا يكتمل قبول النظام قبل CI جديد على التغييرات، فحص موارد ISO/SquashFS، واختبارات Persistence والست نوافذ/الذاكرة المطلوبة.
