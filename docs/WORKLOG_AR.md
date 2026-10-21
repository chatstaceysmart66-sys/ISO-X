# سجل تدقيق وإصلاح ISO-X

## الجولة الحالية — 2026-10-21

### المرحلة 1: الجرد — قيد التنفيذ

#### الحالة عند البدء

- `git status --short --branch`: `## fix/isox-build-and-runtime...origin/fix/isox-build-and-runtime`؛ لا تغييرات محلية ظاهرة قبل إنشاء هذا السجل.
- `git rev-parse HEAD`: `4f27287bf0cb438ce1dc334c7b65763dcc7a6e04`.
- الفرع البعيد المحلي `origin/fix/isox-build-and-runtime` عند commit نفسه؛ `origin/main` عند `5a4c11951dfbe2ef021710376a41a7fcf535a419`.
- `git diff --stat origin/main...HEAD`: 114 مسارًا متغيرًا (113 ملفًا حاليًا وملف ZIP محذوفًا من الفرع)، 10,466 سطر إضافة في إحصاء Git؛ منها 10 أصول ثنائية حالية.
- `git ls-files`: 113 ملفًا متتبعًا حاليًا. ملفات PNG/WAV العشرة ثنائية؛ يجري فحص النوع والأبعاد/الحجم فقط، ولا تُقرأ كمحتوى نصي.
- commits الفرع العشرة منذ `origin/main`، من الأقدم إلى الأحدث:
  `34696ba`، `cca8531`، `842713c`، `569b0d5`، `caf5859`، `b5b444d`، `598c3c6`، `dba48b5`، `a28d26f`، `4f27287`.
- يوجد ISO محلي سابق بحجم `2,657,157,120` بايت، مع sidecar؛ لم يُعَد بعد فحص بصمته أو هيكله في هذه الجولة. لا يُضمّن في commits.
- تنزيل أدلة run `39558122675` لم يبدأ: `gh run download ...` exit 4 لأن GitHub CLI غير مصادق. لا يجوز استنتاج الفحص الذي فشل من وصف سابق؛ يلزم سجل CI أو ملفات الأدلة.

#### تغطية القراءة

بدأت القراءة المنهجية، واكتملت قراءة الملفات الآتية بالكامل: `.github/workflows/iso-build.yml`، `auto/config`، `config/package-lists/iso-x.list.chroot`، hooks الخمسة تحت `config/hooks/live/`، `build.sh`، `scripts/ci-build-in-trixie.sh`، `scripts/build-iso.sh`، `scripts/install-build-deps.sh`. لم تكتمل بعد قراءة بقية الملفات.

| الحالة | العدد الحالي |
|---|---:|
| قُرئ بالكامل | 67 |
| قُرئ جزئيًا | 0 |
| ثنائي (فُحصت بياناته فقط) | 10 |
| لم يُقرأ بعد | 36 |

#### تحديث تغطية القراءة — 2026-10-21

بعد مراجعة بقية ملفات المستودع:

| الحالة | العدد |
|---|---:|
| قُرئ بالكامل | 103 ملفًا نصيًا |
| قُرئ جزئيًا | 0 |
| ثنائي (فُحصت بيانات النوع/الأبعاد/الحجم فقط) | 10 |
| لم يُقرأ | 0 |
| الإجمالي المتتبع من `git ls-files` | 113 |

شملت الدفعة الوثائق التاريخية وتقارير البناء، وملفات SVG/HTML، ومصدر Bevy، ومدخل متجر سطح المكتب ومولّد الأصوات واختبارات المتجر. ملفات WAV/PNG العشرة فُحصت كبيانات ثنائية ولم تُقرأ بايتاتها كنص. لم تُجر اختبارات أو بناء خلال هذه الدفعة.

بعد إضافة الملفات الخمسة التالية في worktree وقبل commit، قُرئت/راجعت كلها بالكامل: `config/bootloaders/grub-pc/grub.cfg`، `config/bootloaders/isolinux/isolinux.cfg`، `config/bootloaders/syslinux_common/live.cfg.in`، `scripts/validate-iso-boot-config.sh`، و`tests/test_write_usb_persistence.sh`. مع `docs/WORKLOG_AR.md` الجديد تصبح تغطية worktree المحلي 109 ملفات نصية كاملة + 10 ملفات ثنائية مفحوصة بياناتها = 119 مسارًا؛ 0 جزئي و0 غير مقروء. عدد HEAD السابق يبقى 113 ملفًا متتبعًا.

ظهرت اختلافات توثيقية مهمة يلزم عدم التعامل معها كحالة HEAD الحالي:

- `docs/FILE_INVENTORY_AR.md` و`docs/PROJECT_MAP_AR.md` يصفان لقطات أقدم (HEAD `caf5859...` وأعداد 104/92 ملفًا)؛ الشجرة الحالية 113 ملفًا وHEAD `4f27287...`. كما أن قائمة التغطية القديمة لا تشمل ملفات متجر ISO-X والأصوات المضافة لاحقًا.
- `README_AR.md` يسرد ترحيل `004_isox_040.sql` مرتين، ويقول إن `install-build-deps.sh` يثبت Rust عبر rustup؛ هذا لا يطابق `README.md` ومسار البناء الحالي الموصوف كاختياري لمشهد Bevy.
- `README.md` يسرد مجلد `security/` ضمن بنية المستودع، لكنه غير موجود في `git ls-files`.
- `docs/RELEASE_NOTES_0.3.0_AR.md` يقدّم خيار persistence بوصفه ميزة في أمر USB، بينما `scripts/write-usb.sh` الحالي يرفض persistence.
- `docs/ARCHITECTURE_AR.md` يبدأ بفقرة مرقمة `9. Data` قبل عنوان الوثيقة، وهو ترتيب/محتوى غير متسق.
- `AUDIT.md` و`docs/BUILD_AND_TEST_RESULTS_AR.md` يسجلان بناءات وCI تاريخية من commits أقدم، منها `dba48b5...` و`39471524581`. هذه الأدلة لا تثبت بناء أو إقلاع HEAD الحالي ولا تحسم فشل run `39558122675`.

#### أدلة ونتائج ظهرت أثناء القراءة

- ملف workflow الكامل يحتوي شروط تحقق صامتة في خطوة `Validate candidate and write validation manifest`: اختبار SHA وnonce ووجود ملفات evidence وعدة `grep -Eiq`. لم يُحسم بعد أنها سبب فشل run `39558122675` لأن تنزيل أدلة run يتطلب مصادقة GitHub؛ الخطوة Exit 4 قبل الوصول إلى محتوى artifact.
- إعداد `auto/config` يستخدم `--apt-indices false`، ويضبط BIOS+UEFI (`syslinux grub-efi`). خيار `--apt-indices false` لا يلغي فهارس apt اللازمة للتثبيت؛ سيُختبر حل قائمة الحزم فعليًا بحاوية Trixie قبل الحكم.
- `build-iso.sh` لا يهيئ Persistence حاليًا؛ كما أن Openbox autostart يوجه بعض سجلات التطبيقات إلى `/tmp`. يلزم تقييم استمرار هذه المسارات بعد live-boot overlay.
- metadata في workflow تصرح حاليًا `"persistence": {"status": "NOT_IMPLEMENTED", ...}`؛ لا توجد في القائمة الحالية معاملات `persistence` أو إعداد لقسم تخزين persist.
- الـISO الموجودة سابقة لهذا الفرع النهائي؛ لا تُستخدم كدليل على محتويات commit `4f27287` قبل مقارنة بصمتها/تاريخ البناء.
- جرى فحص ملفات النظام منخفضة المستوى والـhooks و21 سكربتًا بالكامل، بما فيها ذيل `scripts/create-ci-results.py` و` scripts/secure-vault.py`.
- `scripts/write-usb.sh` يصرّح في التعليق والواجهة بأن Persistence غير مدعوم. الكتابة تستخدم `dd` إلى قرص USB بعد طلب `WIPE <disk>`؛ لا يُسمح بتجربة ذلك على جهاز حقيقي. يلزم إضافة حماية تمنع قرص النظام قبل تنفيذ أي ميزة كتابة.
- قُرئ كاملًا كل من `app/isox_appcenter.py` و`app/isox_store_backend.py`. المتجر يستخدم AppStream المحلي وAPT وFlatpak user remotes المفعّلة، وعمليات APT تمر عبر `pkexec` إلى `apt-get` بوسائط argv منفصلة، وFlatpak محدد بـ`--user`. تصنيفات Games/Windows الحالية مطابقة كلمات مفتاحية فقط وليست بيانات توافق أو اختبارات موثقة.
- إعدادات الأصوات تحفظ للمستخدم، و`paplay` يعمل عبر process غير حاجب؛ إذا تعطلت الأداة يُعرض تشخيص داخل المتجر. لا يعني ذلك أن خرج الصوت متاح في هذه البيئة.
- فُحصت صور المشروع الخمس وملفات WAV الخمسة باستخدام `file` و`stat`. النتائج: PNG (1024²، 3840×2160، 1024²، 512²، 1600×900)، وWAV mono PCM 16-bit 24 kHz؛ إجمالي الأصول الصوتية الخمسة أحجامها 20,204–41,804 بايت. لم تُفحص جودة السماع الفعلية.
- قُرئت ملفات الواجهة الأساسية `app/iso_x_gtk.py` و`app/iso_x_shell.py` و`app/isox_welcome.py` وملفات DB الأربعة، ومجموعة الاختبارات الحالية بالكامل.
- عيب اختبار ظاهر: `tests/test_source_config.py` يمر على `xml_root.iter("command")` رغم أن ملفات Openbox تستخدم default XML namespace؛ لذلك هذا المرور لا يرى عناصر `command` المؤهلة بالـnamespace، ولا يثبت وجود أوامر Exec المذكورة. سيُتحقق منه باختبار XML فعلي/إصلاح الاختبار.
- توجد ملفات قديمة/بديلة لا تدخل البناء وفق قراءة المصدر: واجهة Tkinter `app/iso_x_shell.py` ليست staged بواسطة build، بينما الواجهتان GTK هما التطبيق المكتبي/الترحيبي؛ سيُراجع ذلك مقابل staging الفعلي قبل تصنيف اليتيم.
- `git status --short --branch --ignored` يعرض الملف الجديد `docs/WORKLOG_AR.md` فقط كغير متتبع. `.venv/` وISO القديمة وملفات `__pycache__/` موجودة كملفات ignored قبل أي اختبار هذه الجولة؛ لن تُضاف أو تُحذف.

### سجل الاختبارات والنتائج

#### فحوص المصدر والصورة المحلية — 2026-10-21

| الأمر/الفحص | النتيجة الفعلية | ما لا يثبته |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q` | تعذر أول تشغيل: `No module named pytest`، exit 1. بعد تثبيت pytest 9.1.1 إلى `/tmp/isox-pydeps` فقط: `26 passed in 2.78s`، exit 0؛ cache خارج المستودع. | لا يثبت GTK runtime أو بناء/إقلاع ISO. |
| `PYTHONDONTWRITEBYTECODE=1 bash tests/smoke.sh` | 14 اختبارًا ناجحًا، إضافة لفحوص التوقيع/Secure Boot والتحقق السلبي من USB وQEMU؛ exit 0. | لا يثبت تشغيل ISO أو الإقلاع الحقيقي بحد ذاته. |
| `sha256sum ISO-X-0.4.0-live-amd64.iso` و`sha256sum --check ISO-X-0.4.0-live-amd64.iso.sha256` | الملف ignored موجود محليًا، حجمه 2,657,157,120 بايت؛ SHA-256 `ad282899b7e1c51fd96590807437d29bffa97c898c7e77e09323a2e3c9b28da1`، sidecar مطابق، exit 0. هذه بصمة تاريخية لملف محلي وليست دليلًا أنه بُني من HEAD `4f27287`. | لا يثبت تطابق source الحالي أو سلامة runtime. |
| `xorriso -indev ISO-X-0.4.0-live-amd64.iso -report_el_torito plain -report_system_area plain` | exit 0؛ وسيط ISO hybrid يحمل El Torito BIOS `/isolinux/isolinux.bin` وUEFI `/boot/grub/efi.img`، مع MBR/GPT/APM. | وجود مدخلات الإقلاع لا يثبت أن kernel/جلسة تقلع. |
| استخراج `/isolinux/isolinux.cfg`, `/isolinux/live.cfg`, `/boot/grub/grub.cfg` و`/boot/grub/config.cfg` من الصورة إلى `/tmp` | BIOS config يحتوي `prompt 0`, `timeout 0`, `default vesamenu.c32`; مدخل live الافتراضي موجود و`append` يحمل `boot=live ... console=ttyS0,115200n8`. GRUB يحدد `default=0`، لكن لا يحدد timeout في الملف المستخرج. لا توجد معاملات `isox.ci` أو nonce في هذه الصورة القديمة. | لا يصف مدخلات ISO جديدة من HEAD الحالي ولا UEFI boot فعلي. |
| `tests/qemu-acceptance.sh bios-headless ... /tmp/isox-current-iso-bios-test` | QEMU 8.2.2، BIOS، TCG (`/dev/kvm` غير قابل للقراءة/الكتابة)، 2 vCPU/1024 MiB. بعد 20.185 ثانية صنّف runner `NO_SERIAL_OUTPUT`, `timed_out=true`, `marker_seen=false`, `serial_bytes=0`, helper exit 10. التُقطت QMP/VGA snapshots مبكر/لاحق/نهائي؛ لقطة النهاية تعرض قائمة Debian “Press ENTER to boot...” وما زالت عندها. stderr لا يسجل إلا إنهاء QEMU من runner. | لا يثبت kernel/initramfs failure؛ لا يوجد serial خرج من الضيف. لا يختبر BIOS لصورة مبنية من HEAD الحالي. |
| `git status --short --branch --ignored` بعد هذه الأوامر | لا ملفات جديدة متتبعة/غير متتبعة سوى `docs/WORKLOG_AR.md`. ISO و`.venv/` و`__pycache__/` ظاهرة كـignored وكانت مسجلة قبل تشغيل هذه الاختبارات. | لا يعني أن ملفات ignored آمنة للإضافة إلى commit؛ يجب استبعادها. |

**استنتاج مضبوط:** فرضية أن BIOS في الصورة المحلية يقف عند قائمة الإقلاع مدعومة مباشرةً بملف `/isolinux/isolinux.cfg` (`timeout 0`) ولقطة شاشة QEMU النهائية التي تبقى على boot menu بعد 20 ثانية. هذا يثبت `BOOTLOADER_STALL` لتلك الصورة المحلية فقط. لا يجوز تعميم النتيجة على ISO مبنية من HEAD الحالي قبل إصلاح الإعداد، إعادة البناء، ثم إعادة QEMU.

الأدوات المتاحة على المضيف: `xorriso`, `qemu-system-x86_64`, `qemu-img`, `shellcheck`, `xmllint`, `desktop-file-validate`, `systemd-analyze`. الغائبة: `lb`, `mksquashfs`, `debootstrap`, `actionlint`. المضيف Ubuntu 24.04.5، المساحة المتاحة 15 GiB تقريبًا، والذاكرة المتاحة 4.3 GiB؛ لذلك لا يُتوقع أن يجتاز build guard المحلي الذي يشترط 20 GiB ومسار Trixie.

ما زالت فحوص الحزم في Debian Trixie، وactionlint/YAML، بقية syntax/systemd/desktop، UEFI، build الحالي وPersistence قيد التنفيذ. لم تُشغّل GitHub Actions؛ `gh auth status` exit 1 بسبب غياب تسجيل الدخول.

### العوائق المفتوحة

- GitHub Actions يتطلب مصادقة؛ `gh auth status` يقول إن الحساب غير مسجّل الدخول. لا يمكن تنزيل run المشار إليه أو تشغيل workflow قبل توفير مصادقة رسمية.
- يلزم تنفيذ القراءة المنهجية لجميع ملفات المصدر والاختبارات والوثائق، ثم تحديث التغطية بمسارات الملفات الفعلية.
- يلزم التحقق من متطلبات مساحة البناء والذاكرة قبل البناء؛ لم يبدأ أي بناء في هذه الجولة.

#### استكمال فحوص المصدر — 2026-10-21

| الأمر/الفحص | النتيجة الفعلية | ما لا يثبته |
|---|---|---|
| `actionlint` 1.7.12 على `.github/workflows/iso-build.yml` | مرّ، exit 0. | لا يشغّل workflow ولا يتحقق من منطق manifest أثناء التنفيذ. |
| `apt-get install --dry-run` لقائمة `config/package-lists/iso-x.list.chroot` في Debian Trixie | المحاولة الأولى مع `main` فقط لم تجد حزم firmware من `non-free`; بعد تفعيل `main contrib non-free non-free-firmware` حلّ APT القائمة كاملة: 1 ترقية، 1150 تثبيتًا جديدًا، 0 إزالة، exit 0. | لا يثبت نجاح بناء chroot أو توفر كل الحزم في كل مرآة لحظة البناء. |
| shell syntax وShellCheck للملفات shell فقط | اكتمل فحص جميع ملفات shell المحددة بعد تصحيح أول أمر فحص كان يمرر ملف Python إلى Bash خطأً؛ النتيجة النهائية سليمة، exit 0. | لا يختبر المسارات الفعلية في بيئة Debian Trixie أو QEMU. |
| Python compile إلى cache مؤقت | 22 ملف Python جُمعت دون أخطاء، مع `PYTHONDONTWRITEBYTECODE=1` واستخدام مجلد cache خارج المستودع؛ exit 0. | لا يثبت سلوك الواجهة أو عمليات إدارة الحزم عند التشغيل. |
| `xmllint` و`desktop-file-validate` | ملفات XML وDesktop التي فُحصت اجتازت التحقق، exit 0. | لا يثبت أن أوامر `Exec` متوفرة في صورة البناء؛ يوجد فحص/اختبار منفصل مطلوب لهذا العقد. |
| `systemd-analyze verify --root=/tmp/isox-systemd-root-check isox-zram.service isox-ci-ready.service isox-ci-ready.timer` | وحدات النظام اجتازت، exit 0. | وحدات المستخدم لم تُتحقق: المحاولة باستخدام مسارات صريحة لم تجدها في root المؤقت، والتحقق عبر user manager يحتاج بيئة D-Bus غير موجودة. النتيجة لوحدات المستخدم `NOT_RUN`. |
| `apt-indices` حسب وصف `lb_config` في live-build Trixie | `--apt-indices false` يعطّل الاحتفاظ بفهرس APT في صورة/كاش البناء للاستخدام offline؛ لا يعطّل تنزيل الفهرس المطلوب لتثبيت الحزم أثناء البناء. | لم يُشغّل `lb build` على هذا المضيف. |
| `git status --short --branch --ignored` بعد الفحوص | لا تغييرات مصدر جديدة؛ `docs/WORKLOG_AR.md` هو الملف المحلي غير المتتبع الوحيد. ملفات ISO و`.venv/` و`__pycache__/` هي ignored ظاهرة مسبقًا، ولم تُضف. | لا يجيز ضم الملفات ignored إلى commit. |

#### إصلاحات المصدر المطلوبة قبل دورة الفحص التالية

- **BIOS boot menu stall:** الصورة القديمة تتضمن `timeout 0` في `/isolinux/isolinux.cfg`، ولا يوجد override حالي في المشروع. أضيف لاحقًا override صريح بمهلة محدودة ومدخل Persistence اختياري؛ لا يُعد ذلك إثباتًا حتى تظهر الإعدادات في ISO مبنية من HEAD المعدل ويعاد اختبار QEMU.
- **UEFI GRUB timeout وPersistence:** ملف GRUB المولد في الصورة القديمة لا يحدد مهلة. يلزم قالب GRUB صريح بمهلة ومدخل عادي وآخر `persistence` مع بقاء kernel args التشخيصية محصورة في CI.
- **فحوص manifest الصامتة:** خطوة workflow تحتوي `sha256sum --check` وregex و`test -s` و`grep` بلا أسماء فحوص في رسائل `::error::`. لم تُحسم بعد أيّها أسقط run `39558122675`؛ التنزيل ما زال ممنوعًا لغياب GitHub auth.
- **Persistence USB:** لم تُنفذ. لا كتابة إلى قرص فعلي؛ اختبار التكامل المطلوب يجب أن يتم فقط على raw image افتراضية قابلة للنسخ/إعادة البناء.

#### دفعة إصلاحات الإقلاع وUSB وCI — 2026-10-21

##### نتائج جديدة كشفتها التجربة

- فُحصت الصورة المحلية القديمة للقراءة فقط عبر `xorriso -indev ISO-X-0.4.0-live-amd64.iso -report_system_area plain -report_el_torito plain`. أظهرت El Torito BIOS وUEFI، وMBR بمدخلين، وGPT entries متداخلة عمدًا (`GPT entry array ... overlapping`، و`ISOHybrid` مع `ISOHybrid1`). الصورة ما زالت تاريخية وليست بناء HEAD الحالي.
- أُنشئت نسخة raw مؤقتة بحجم 4 GiB تحت `/tmp` فقط، ووُضع محتوى ISO القديم في بدايتها. `sgdisk --verify` أعاد exit 2 بسبب تداخل MBR/GPT الخاص بالـisohybrid؛ وفشلت محاولة `sgdisk --print`/`--move-second-header` على هذه البنية. هذا أثبت أن تنفيذ Persistence المبني على `sgdisk` غير صالح لهذا النوع من الصور، فأزيل بدل الإبقاء على مسار فاشل.
- جرى اختبار `sfdisk --append` على نسخة raw فقط: أضاف مدخل MBR رقم 3 في المساحة بعد الصورة بنجاح (exit 0)، ثم `partx --show` أظهر مدخل Linux `0x83`. `mkfs.ext4` على offset بالقيمة `2657157120` بايت أنشأ ext4 label=`persistence` و`blkid -p -O ...` أكّد `TYPE=ext4`. لا يثبت هذا إقلاع النظام أو اكتشاف live-boot لقسم MBR؛ الجهاز الافتراضي loop تعذر ربطه بسبب `losetup ... Permission denied`.
- أساس اختيار MBR موثق من خرج الصورة ومن Linux 6.12 `block/partitions/efi.c`: فاحص EFI لا يقبل GPT دون Protective MBR يحتوي نوع `0xEE` عند LBA 1؛ الصورة المخرجة لا تحتوي هذا المدخل وتحتوي MBR type `0x00` و`0xEF`. لذلك يستخدم kernel مسار DOS/MBR؛ أضيف قسم Persistence كمدخل MBR ثالث مع إبقاء بيانات GPT/إقلاع الصورة الأصلية دون تعديل.

##### تغييرات المصدر المنفذة

- أضيفت قوالب BIOS/UEFI صريحة تحت `config/bootloaders/`: مهلة Syslinux مقدارها 10 ثوانٍ، مهلة GRUB مقدارها 10 ثوانٍ، ومدخل Persistence مستقل بجانب الافتراضي العادي.
- `scripts/build-iso.sh` ينسخ القوالب إلى staging ثم يستخرج إعدادات الإقلاع الفعلية من ISO الناتجة ويمررها إلى `scripts/validate-iso-boot-config.sh`. الفاحص يرفض timeout غير محدود، أو مدخل Persistence مفقود، أو تسرب معلمات CI إلى بناء الإصدار، أو nonce CI خاطئ.
- استبدل `scripts/write-usb.sh` محاولة GPT الفاشلة بمسار MBR فقط: يثبت أن مصدر ISO يحمل مدخلي MBR المتوقعين، يكتشف قرص النظام ويرفض الكتابة إذا تعذر تحديد topology، يتحقق من السعة/sector قبل `dd`، ويطلب تأكيدَي `WIPE <disk>` و`CREATE PERSISTENCE`. لا يُنشأ إلا مدخل MBR ثالث من النوع `0x83`؛ ثم ext4 label=`persistence` و`persistence.conf` بمحتوى `/ union`.
- أضيف `fdisk` (يوفر `sfdisk`) و`e2fsprogs` لقائمة الحزم؛ حُذفت إضافة `gdisk` لأنها غير مستخدمة. APT dry-run المحدّث داخل `debian:trixie` حل كامل القائمة: `1 upgraded, 1153 newly installed, 0 to remove`, exit 0؛ منها `fdisk` و`e2fsprogs`.
- أضيف فحص مسمّى ورسالة `::error::` إلى كل فحوص manifest الصامتة، وكذلك بوابتا BIOS وUEFI، لتعرض محتوى ملف الدليل عند الفشل. بقي رفع مرشح ISO قبل اختبارات BIOS/UEFI؛ فشل الإقلاع لا يحذف artifact.
- عُدّل build metadata و`create-ci-results.py` ليصنّفا Persistence على أنها `NOT_RUN` مع وصف تنفيذ writer والاختبار الطرفي غير المنفذ، بدل الادعاء بأنها `NOT_IMPLEMENTED`. بقي schema يدعم `NOT_RUN` مسبقًا، وأضيف assertion يمنع رجوع الوصف القديم.
- أضيف `tests/test_write_usb_persistence.sh` إلى source-check runner؛ ينشئ ملف MBR خامًا sparse ويختبر `sfdisk --append` ومحتوى `/ union` باستخدام mocks للتركيب/formatting. workflow يثبت حزمة `fdisk` كي يتوفر `sfdisk`، والفحص يسجل `NOT_RUN` عند غياب الأداة محليًا بدل نجاح وهمي.
- أصلح `tests/test_source_config.py` ليقرأ عناصر Openbox ذات namespace باستخدام `{*}command`. قبل الإصلاح كان الاختبار لا يرى أوامر Exec، وكان يعلن نجاحًا غير مبرر. أضيفت اختبارات سلبية للقوالب، nonce، جدول MBR المتوقع، واكتشاف قرص النظام والفشل المغلق.

##### التحقق بعد الدفعة

| الأمر | النتيجة | القيود |
|---|---|---|
| `PYTHONPATH=/tmp/isox-pydeps PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q` | 28 passed، exit 0. | اختبارات المنطق/العقود لا تثبت إقلاع ISO أو Persistence بعد restart. |
| `bash tests/test_write_usb_validation.sh` | PASS، exit 0؛ البصمة الصحيحة مقبولة، العبث مرفوض، وقرص النظام/التخطيط غير المعروف مرفوضان. | لا كتابة فعلية إلى block device. |
| `bash tests/test_qemu_headless_validation.sh` | PASS، exit 0؛ رفض nonce المضلل، serial الفارغ، timeout، QEMU error وغياب QMP/screenshots. | يختبر runner بأداة QEMU مزيفة؛ لا يثبت إقلاع صورة. |
| `bash -n scripts/build-iso.sh scripts/write-usb.sh scripts/validate-iso-boot-config.sh tests/test_write_usb_validation.sh` وShellCheck للملفات نفسها مع استثناء SC1091 المعروف في `/etc/os-release` | exit 0. | لا يشمل تشغيل build. |
| `actionlint` 1.7.12 (binary من release الرسمي، SHA-256 مطابق لملف checksums) على `.github/workflows/iso-build.yml` | exit 0. | لا يشغل GitHub Actions. محاولة `go install` الأولى تعثرت عند الاتصال بـsum.golang.org؛ لم تُعتمد، ثم تحقق الملف الرسمي بالبصمة. |
| `docker run ... debian:trixie ... apt-get install --simulate` لقائمة الحزم الحالية ومكونات المستودع `main contrib non-free non-free-firmware` | 1 upgraded, 1153 newly installed, 0 to remove، exit 0. | محاكاة حل التبعيات فقط؛ لا تثبيت أو بناء chroot. |
| `sfdisk --append` + `partx --show` + `mkfs.ext4 -E offset=...` + `blkid -p -O ...` على `/tmp/isox-usb-persistence-test.raw` فقط | MBR partition 3 ظهر من start `5189760`, type `0x83`; filesystem label `persistence`, type `ext4`؛ الأوامر نجحت. | ليس loop block device؛ لم ينشأ `persistence.conf` داخل filesystem ولم يُقلع guest بها. |
| `losetup -fP /tmp/isox-usb-persistence-test.raw` | `Permission denied`، exit 1. | يمنع اختبار kernel partition nodes/تركيب filesystem وإعادة تشغيل guest في البيئة. |
| `actionlint` على الـworkflow المعدل، `git diff --check`، وفحوص Python/Shell النهائية | كلها exit 0. | لا workflow run؛ لا توجد مصادقة GitHub. |
| `scripts/run-source-checks.py /tmp/isox-source-evidence-2 /tmp/isox-source-pycache-2` مع `PYTHONPATH=/tmp/isox-pydeps` و`PATH` يحوي `sfdisk` | جميع الفحوص 23/23 PASS، exit 0: compile, pytest, smoke, USB validation/persistence partition, QEMU fake, ShellCheck, desktop/XML, workflow contracts, CI results وdiff-check. | أول تشغيل كشف assertion خاطئًا في `test_workflow_contracts.py` (طلب اسم check من YAML لا من runner)، صُحح ليستهدف `scripts/run-source-checks.py` ثم أعيدت المجموعة كاملة ونجحت. لا يثبت بناء ISO أو hardware. |
| `gh auth status` | `You are not logged into any GitHub hosts`, exit 1. | لا يمكن تنزيل run `39558122675`، أو push، أو تشغيل workflow. |

#### متابعة بعد استكمال GitHub authentication — 2026-10-21

- `gh auth status`: مصادقة ناجحة للحساب `jnkmmdndmd-arch`، scopes تشمل `repo` و`workflow`. `gh api repos/chatstaceysmart66-sys/ISO-X` أكد `permissions.push=true`.
- الحالة قبل العمل: الفرع `fix/isox-build-and-runtime`، `HEAD=84e8b96b6e9ded0e966a68565a7f01167455d991`، لا تغييرات Git، والفرع البعيد عند نفس commit. دفع commit جرى سابقًا بنجاح بعد `gh auth setup-git`؛ لم يستخدم force. رابط commit: `https://github.com/chatstaceysmart66-sys/ISO-X/commit/84e8b96b6e9ded0e966a68565a7f01167455d991`.
- ملف `ISO-X-0.4.0-live-amd64.iso` كان موجودًا في جذر المستودع، غير متتبع ومطابقًا لقاعدة `.gitignore` `*.iso`. قبل حذفه وحده سُجل حجمه `2,657,157,120` بايت وSHA-256 `ad282899b7e1c51fd96590807437d29bffa97c898c7e77e09323a2e3c9b28da1`. حُذف من worktree بالمسار المحدد فقط؛ لا يوجد ملف ISO في Git ولم يُعدّل التاريخ.
- التشغيل `39558122675` (HEAD قديم `4f27287...`): نزّلنا `isox-build-evidence-39558122675-1` و`isox-acceptance-report-39558122675-1`. تقريره يقول source checks PASS، بناء الصورة وبنيتها FAIL، وBIOS/UEFI NOT_RUN. سجل manifest القديم يعرض `ISO-X-0.4.0-ci-39558122675-1.iso: OK` قبل exit 1، دون رسالة فحص.
- أُعيدت منفردة على ملفات الأدلة المحفوظة جميع اختبارات وجود الملفات الخمسة، ونمطي El Torito BIOS وUEFI، ونمط system-area MBR؛ كلها exit 0. sidecar SHA-256 ظهر `OK` في سجل الخطوة. الـartifact التاريخي لا يحتوي ISO المرشح أو nonce، والسجل لا يحتوي traceback/اسم check؛ لذلك الفحص الدقيق الذي أنهى الخطوة القديمة **غير معروف** ولا يجوز استنتاجه. تختلف هذه الأدلة التاريخية عن إصلاحات manifest المسمّاة المضافة في commit `84e8b96`.
- تشغيل جديد للرأس الحالي: [run 39644678919](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/39644678919)، event `push`، commit `84e8b96...`. GitHub `source-check` نجح، لكن خطوة البناء فشلت، وBIOS/UEFI تخطّيا لعدم وجود مرشح. سجل `xorriso` وصل لاستخراج ملفات boot config؛ الفشل المحدد كان `BOOT CONFIG ERROR: BIOS normal and persistence entries are invalid`. ملف `live.cfg` الفعلي يضع `menu default` و`append` بعد tab، بينما الـvalidator كان يطابق بداية السطر فقط. `lb build` وصل إلى مرحلة التحقق بعد البناء، لكن لم تُرفع ISO مرشحة ولا يمكن اعتبارها ناتجًا متاحًا.
- الفحوص المحلية بعد استعادة المتطلبات (`fdisk` عبر apt و`pytest` خارج المشروع في `/tmp/isox-pydeps`) أعادت تشغيل `scripts/run-source-checks.py` كاملة: 23 check، وكلها PASS، 50 عدًّا ناجحًا، 0 failed، 0 NOT_RUN، exit 0. لم تُكتب ملفات اختبار داخل المستودع.
- Codespace لا يزال غير مناسب لبناء ISO محلي: `/workspaces` لديه 15 GiB متاح، و`lb` و`debootstrap` و`mksquashfs` غير موجودة. `xorriso` وQEMU موجودان فقط. لذلك لا يوجد بناء محلي جديد. الـworkflow الحالي يبني صورة كاملة المصدر داخل Trixie، لكنه يصرّح بأنها **CI-only diagnostic** ويضبط `release_eligible=false`; حتى نجاحه لا يثبت قبول release عادي أو Persistence.
- إصلاح العطل الفعلي: أصبح `scripts/validate-iso-boot-config.sh` يقبل المسافة البادئة في تعليمات Syslinux، وتحوّل fixture إلى تنسيق live-build الفعلي لاكتشاف regressions. أضيف `scripts/create-user-iso.py` ومرحلة `promote` مشروطة بنجاح BIOS وUEFI: تنشئ نسخة boot عادية من نفس ISO عبر xorriso دون إعادة بناء root filesystem، تتحقق من إزالة CI nonce ومن بقاء El Torito BIOS/UEFI وMBR، وتحفظ sidecar SHA-256 وmetadata. يبقى `release_eligible=false` لأن اختبار Persistence عبر reboot غير منفذ؛ لا يُنشأ GitHub Release.
- تم اختبار الترويج محليًا على ISO fixture مؤقتة بـxorriso 1.5.6: تغيّرت ملفات boot المقصودة فقط، بقيت إدخالات El Torito BIOS وUEFI وMBR، واختفى nonce من إعدادات التشغيل، ونجح sidecar hash. أصول الإقلاع في fixture اصطناعية وليست قابلة للإقلاع؛ هذا يختبر إعادة كتابة الصورة لا إقلاع ISO المشروع.
- بعد إضافة تحويل ISO واختبار xorriso integration، `scripts/run-source-checks.py` اجتاز 23 check، 54 PASS، 0 FAIL، 0 NOT_RUN، exit 0؛ `actionlint` 1.7.12 و`git diff --check` وShellCheck اجتازوا أيضًا. اختبار xorriso أنشأ fixture اصطناعية وفحص إعادة الكتابة والـmetadata؛ لا يثبت إقلاع الصور الاصطناعية.
- عدد التغطية المرجعي من الجرد السابق يبقى 119 مسارًا (109 نصية قُرئت بالكامل، 10 ثنائية فُحصت بياناتها فقط). لم تُجرَ في هذه المتابعة إعادة قراءة شاملة للملفات؛ انصب العمل على الحالة الفعلية وملفات وأدلة CI ذات الصلة.
- الحالة التالية: التعديلات التي تصلح validator وتضيف Artifact نسخة الإقلاع العادية ما زالت محلية غير committed/unpushed، بعد اجتياز المصدر. يجب تثبيت commit ودفعه، ثم مراجعة workflow الجديد وسجل بناء Trixie وBIOS/UEFI وArtifact النسخة العادية. BIOS/UEFI على بناء `84e8b96` skipped بسبب validator، وPersistence لم يبدأ. لا Release ولا ادعاء جاهزية قبل دليلها.
- إعادة التحقق في هذه المتابعة: التشغيل الأول دون `PYTHONPATH` فشل لأن مفسر Codespace النشط لا يحتوي pytest (`No module named pytest`)، وليس بسبب فشل test. أُعيد `scripts/run-source-checks.py` مع `PYTHONPATH=/tmp/isox-pydeps`, و`PYTHONDONTWRITEBYTECODE=1` ومجلدي evidence/cache خارج المشروع: جميع 23 check PASS، منها 32 اختبار pytest، والإجمالي 54 PASS و0 FAIL و0 NOT_RUN، exit 0. شُغّل `tests.test_user_iso` منفرداً: 4/4 PASS.
- تحققات إضافية: `go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 .github/workflows/iso-build.yml` exit 0؛ ShellCheck و`git diff --check` exit 0. فحص العمل لم يجد ملفات `.pyc` جديدة بعد إزالة ملفي bytecode المحددين اللذين أنشأهما اختبار `py_compile`. لا يثبت أي من هذه الفحوص بناء ISO أو BIOS/UEFI أو الجلسة الرسومية أو Persistence عبر reboot.
- تحقق Git قبل الالتزام: `gh auth status` نجح للحساب الحالي مع scope `repo` و`workflow`، و`git fetch origin fix/isox-build-and-runtime` أظهر أن المحلي والبعيد كلاهما عند `84e8b96b6e9ded0e966a68565a7f01167455d991` (0 ahead/behind). التعديلات الحالية ما زالت غير committed وغير pushed؛ لا يوجد تشغيل CI جديد بعد هذه التغييرات.

##### حالة البناء والإقلاع وPersistence

- لم يُنفذ `lb build`: المضيف Ubuntu 24.04.5 وليس Debian Trixie، والمساحة الحرة نحو 15 GiB مقابل شرط السكربت 20 GiB، وأدوات `lb`, `debootstrap`, `mksquashfs` غير مثبتة. وجود RAM كافية لا يزيل هذه القيود.
- لا يوجد ISO جديد من `HEAD` بعد تغييرات bootloader/Persistence. نتيجة BIOS القديمة `BOOTLOADER_STALL` تخص الصورة التاريخية فقط. BIOS وUEFI على النسخة الجديدة `NOT_RUN`.
- بناء قسم Persistence في ملف raw تمت تجربته حتى MBR/ext4 فقط. اكتشاف live-boot، إنشاء `persistence.conf` داخل filesystem mounted، كتابة ملف المستخدم/Firefox/الحزمة، إعادة تشغيل guest والتحقق من بقائها: `NOT_RUN`، لأن loop device ممنوع ولا توجد ISO جديدة تقلع من التعديلات.
- عند تسجيل هذه الملاحظة لم يكن قد حدث commit أو push أو تشغيل workflow. الـISO القديمة ignored، ونسخة raw وأدوات الفحص في `/tmp` فقط؛ لا تُضمّن أيًا منها في commit. `gh auth status` غير مصادق، لذلك لا push ولا تشغيل CI في هذه الجولة.
