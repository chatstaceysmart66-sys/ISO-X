# خريطة ربط مرجع التصميم — ISO-X 0.4.0

## حدود المصدر وهويته

النسخة المحفوظة هي [design/reference/iso-x-reference.html](../design/reference/iso-x-reference.html)، وقد نُسخت بايتياً من مرشح المستودع `iso-x 22.html`.

| البيان | القيمة |
|---|---|
| اسم المرفق الذي حدده الطلب | `iso-x (1).txt` |
| هل عُثر على المرفق الأصلي؟ | لا؛ لذلك لا يمكن إثبات أن المرشح هو الملف المرفق |
| SHA-256 للنسخة المحفوظة | `16f2b6d8007e01c612825823eada60627ee7040b690ea9032f86ab93490f2a35` |
| SHA-256 لمرشح `iso-x 22.html` | `16f2b6d8007e01c612825823eada60627ee7040b690ea9032f86ab93490f2a35` |
| النتيجة | النسخة تطابق مرشح المستودع؛ مطابقتها للمرفق الأصلي **غير مثبتة** |

لا يُعرض هذا المرشح بوصفه مرفق المستخدم الأصلي، ولا تُنسب إليه هوية غير متحققة. أداة الاستخراج تضع هذه الحقيقة في manifest أيضاً.

## مكونات التصميم وربطها

| مكوّن المرجع | تنفيذ ISO-X المقابل | الملفات/المسارات | دليل القبول والحالة |
|---|---|---|---|
| `#wall` وصورة الخلفية `--wp` | PCManFM يضبط خلفية الجلسة الحقيقية على JPEG الأصلي بوضع `fit`؛ LightDM يستخدم الصورة نفسها عند إظهار greeter | `scripts/apply-windows-look.sh`؛ `config/hooks/live/0300-isox-services.hook.chroot`؛ `/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.jpg` | اختبار المصدر وrootfs اصطناعي للبصمات؛ rootfs/ISO الفعلي **غير متحقق حتى بناء وفحص ISO** |
| `#boot` وصورة `--bp` | Plymouth يعرض المشهد كصورة ثابتة متناسبة؛ لا يُشغّل HTML ولا مؤقت انتقال اعتباطي. ينتقل التحكم وفق Plymouth/LightDM والجلسة الفعلية | `plymouth/isox/isox.script`؛ `plymouth/isox/isox.plymouth`؛ `config/hooks/live/0200-isox-plymouth.hook.chroot`؛ `/usr/share/plymouth/themes/isox/iso-x-plymouth.png` | اختبار المصدر وrootfs اصطناعي للبصمة؛ عرض BIOS/UEFI **غير متحقق** |
| صورة زر Start | أيقونة مشتقة باحتواء متناسب إلى 96×96، مع حفظ JPEG الأصلي لتطبيقات GTK | `assets/reference/dragon-mark-original.jpg`؛ `assets/reference/dragon-mark-icon-96.png`؛ `/usr/share/iso-x/assets/reference-dragon-mark.jpg`؛ `/usr/share/icons/hicolor/96x96/apps/iso-x.png` | البصمات والأبعاد ضمن manifest واختبار المصدر؛ ظهورها في ISO **غير متحقق** |
| `#desk` وشبكة الأيقونات | PCManFM وملفات `.desktop` الحقيقية؛ يظل Openbox مدير النوافذ | `scripts/build-iso.sh`؛ `desktop/`؛ `scripts/apply-windows-look.sh` | لا تُشغّل صفحة HTML كبيئة سطح مكتب؛ لقطات الدقة وRTL/LTR **لم تُلتقط** |
| `#tb` وشريط المهام | Tint2 حقيقي بارتفاع 48px؛ launcher وDesktop Entries وصينية النظام والساعة؛ Openbox يدير النوافذ | `desktop/tint2rc`؛ `app/isox_launcher.py`؛ `/usr/share/icons/hicolor/96x96/apps/iso-x.png` | اختبار مصدر للتكوين؛ لا يوجد إقلاع جديد للتحقق من الاستقرار، وتحذير segfault السابق في سجل التحذيرات ما زال غير محسوم |
| `#menu` وStart/More/Back | GTK launcher يكتشف التطبيقات المثبتة، يعرض 8 أولاً ثم «المزيد» والرجوع والبحث، ويطلق Desktop Entry | `app/isox_launcher.py`؛ `desktop/isox-launcher.desktop` | اختبارات launcher الحالية مصدرية/تفاعلية وفق ملف النتائج؛ لم يُعد فحصها على ISO الجديدة |
| `#qs` وحالة الشبكة والصوت والطاقة | لا تُحوّل مفاتيح HTML إلى حالة نظام وهمية؛ تبقى الحالة في خدمات Linux وصينية النظام والأدوات الفعلية | NetworkManager، PipeWire/WirePlumber، UPower وخدمات الجلسة القائمة | تكامل الأجهزة والخدمات على عتاد حقيقي **غير متحقق**؛ لا يقدّم هذا التغيير لوحة HTML منافسة |
| النوافذ | نوافذ GTK فعلية يديرها Openbox؛ لا ينشئ المرجع نوافذ نظام | `desktop/openbox-rc.xml` وتطبيقات GTK | السحب والتركيز/التصغير/التكبير على ISO الجديدة **غير متحقق** |

## الأصول المضمنة

الأداة `scripts/extract-reference-assets.py` تربط كل Data URI بسياق CSS/DOM، وتفكّ Base64 وتتحقق من MIME وJPEG magic bytes والمُفكِّك والأبعاد والنسبة والألوان التقريبية وSHA-256. عدد Data URI هو 6: ثلاث صور فريدة، لكل منها استعمالان متطابقان بايتياً.

| الدور | عنصر HTML | الملف الأصلي | الأبعاد والنسبة | الحجم | SHA-256 | الملف المشتق |
|---|---|---|---|---:|---|---|
| Wallpaper | `#wall` / `--wp` | `assets/reference/desktop-wallpaper-original.jpg` | 1920×1080، 16:9 | 240,067 بايت | `34438ee49fc927e5c1cc9ffb10bcca47349d92bcb78a5beb0ebab6bd28da6391` | لا تحويل؛ يُستخدم JPEG الأصلي |
| Boot/Plymouth | `#boot` / `--bp` | `assets/reference/boot-screen-original.jpg` | 1920×1080، 16:9 | 190,033 بايت | `fe9b77769e0b3e39405b1d4419967ecf5ce307a0786d07c0d82abdfb58899f64` | `boot-screen.png`، ترميز PNG للبكسلات المفكوكة دون قص أو تغيير أبعاد |
| Start logo | صورة `#start` | `assets/reference/dragon-mark-original.jpg` | 100×106، 50:53 | 6,174 بايت | `0b889457625b2f3af0fc3e31f9484338d5091a0bc8a56047497a960f1e28b892` | PNG كامل الأبعاد لتطبيق Bevy الاختياري، وأيقونة 96×96 بتصغير متناسب واحتواء؛ الأصل محفوظ كما هو |

الملف `assets/reference/reference-assets.json` يسجل أيضاً بصمات الملفات المشتقة ومساراتها المقصودة. الخلفية لا تُعاد ضغطها ولا تُحوّل إلى PNG. لا يدّعي التكوين أن أصل 1920×1080 هو 4K native.

## الملاءمة والأمان

- الخلفية في PCManFM هي `fit` وليست `stretch`؛ وصورة Plymouth تستخدم أصغر مقياس بين عرض الشاشة وارتفاعها وتتمركز، فتحافظ على كامل المشهد والنسبة.
- اختبر عقد المصدر حسابياً دقات 1366×768 و1280×720 و1920×1080 و1920×1200 و2560×1440 و3840×2160. لقطات شاشة مرئية لكل دقة وDPI/HiDPI **لم تُلتقط**.
- HTML مرجع بصري، وليس برنامج سطح مكتب. يحتوي JavaScript على `Function()` في حاسبة تجريبية، ومحاكاة طرفية غير متصلة بـLinux، وحالات Wi-Fi/بطارية شكلية، وطلب كاميرا عند فتح نافذة النموذج، و`setTimeout` للانتقال. روابط HTTPS لا تُفتح إلا من إجراء تفاعلي.
- لذلك لا يُحمّل HTML داخل WebView ولا يُثبت في ISO كصفحة قابلة للتشغيل. يُحفظ في المستودع فقط؛ تُستخرج الصور إلى ملفات محلية، ويستخدم النظام GTK/Openbox/PCManFM/Tint2 وPlymouth الحقيقيين. لا تُنفّذ أوامر shell من النموذج.

## الحالة النهائية لهذه الجولة

| التحقق | الحالة |
|---|---|
| تطابق النسخة المحفوظة مع مرشح `iso-x 22.html` وبصمة المصدر | **PASS** — نتيجة النسخ والبصمة أعلاه |
| تطابقها مع المرفق المحدد `iso-x (1).txt` | **UNVERIFIED** — المرفق غير متاح |
| استخراج الصور والتحقق من MIME والأبعاد والبصمات | **PASS** لاختبار الاستخراج المصدري |
| إعداد build وhooks لتثبيت الأصول الرسمية في المسارات المقصودة | **PASS** على مستوى عقد المصدر فقط |
| مطابقة بصمات الأصول في rootfs اصطناعي | **PASS** عبر `scripts/verify-reference-assets.py`؛ الاختبار يحاكي نسخ source/original/derived files إلى شجرة rootfs |
| مطابقة الملفات الفعلية داخل SquashFS/ISO | **NOT_RUN** — لا توجد ISO جديدة |
| إقلاع Plymouth وLightDM والجلسة، وBIOS/UEFI | **NOT_RUN** لهذه التغييرات |
| Persistence والصوت والشبكة وعتاد حقيقي | **UNVERIFIED** |

لا يُعد وجود الأصول في `assets/` وحده إثباتاً لوصولها إلى ISO. يلزم بناء Trixie وفحص SquashFS والبصمات وسجلات إقلاع BIOS وUEFI قبل إعلان الاعتماد النهائي.
