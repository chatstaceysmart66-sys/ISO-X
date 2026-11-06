# شلون نكمل اختبار ISO-X فعليًا؟

## المهم قبل البداية

هذه الحزمة مصدر برنامج، وليست ISO جاهز. بناء Debian Live يحتاج Debian 13 Trixie amd64 حقيقيًا أو VM، اتصال إنترنت، RAM لا تقل عن 4 GiB، ومساحة فارغة لا تقل عن 20 GiB. لا ترفع كلمة مرور أو مفتاح توقيع خاص إلى المحادثة.

## أوامر البناء

بعد تنزيل وفك `ISO-X-0.4.0-TRIXIE.zip` داخل Debian 13 Trixie، افتح الطرفية داخل مجلد `ISO-X-0.4.0-TRIXIE` ونفّذ:

```bash
./scripts/install-build-deps.sh
./scripts/generate-dev-signing-key.sh "$HOME/.local/share/isox-signing"
export ISOX_RELEASE_KEY="$HOME/.local/share/isox-signing/isox-release.key"
export ISOX_RELEASE_CERT="$HOME/.local/share/isox-signing/isox-release.crt"
set -o pipefail
sudo --preserve-env=ISOX_RELEASE_KEY,ISOX_RELEASE_CERT ./scripts/build-iso.sh 2>&1 | tee build-console.txt
```

إذا توقف البناء بسبب الخطأ، لا تحذف مجلد البناء ولا تعِد تسمية ISO قديم. احفظ السجلين التاليين إن وُجدا:

```bash
cp /tmp/lb-build.log ./lb-build.log 2>/dev/null || true
bash tests/smoke.sh > ./source-tests.txt 2>&1
```

## بعد نجاح إنتاج ISO

```bash
./tests/qemu-acceptance.sh check ./ISO-X-0.4.0-live-amd64.iso
./tests/qemu-acceptance.sh bios ./ISO-X-0.4.0-live-amd64.iso
./tests/qemu-acceptance.sh uefi ./ISO-X-0.4.0-live-amd64.iso
./tests/qemu-acceptance.sh install ./ISO-X-0.4.0-live-amd64.iso
```

كل من BIOS وUEFI وinstall يفتح QEMU بنافذة رسومية. افحص الشاشة بنفسك واحفظ صور الأخطاء أو النجاح وسجلات مجلد `evidence/qemu-*`. وضع install ينشئ قرص اختبار qcow2 جديدًا؛ لا تختَر قرصًا فعليًا.

## شنو ترجع ترفعه بالمحادثة؟

ارفع `build-console.txt` و`lb-build.log` إذا فشل البناء. إذا نجح البناء، ارفع `ISO-X-0.4.0-live-amd64.iso.sha256` مع ملفات السجلات/صور QEMU التي ظهر فيها العطل. لا ترفع `isox-release.key`؛ المفتاح الخاص يبقى عندك.

نجاح اختبارات المصدر وحده ما يكفي لإعلان النظام 100%؛ يلزم بناء ISO فعلي واختباره على BIOS وUEFI والتثبيت وإعادة الإقلاع، ثم إصلاح كل خطأ يظهر في السجلات.
