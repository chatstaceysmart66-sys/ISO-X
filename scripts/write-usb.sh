#!/usr/bin/env bash
set -Eeuo pipefail
# ISO-X USB Writer 0.4.0. Persistence creation is deliberately not offered
# until partition-table handling can be verified across BIOS/UEFI USB layouts.
ISO="${1:-}"
MODE="${2:-no}"
[[ -r "$ISO" && -f "$ISO" ]] || { echo "الاستخدام: $0 /path/to/ISO-X-0.4.0-live-amd64.iso [no]" >&2; exit 2; }
[[ "$MODE" == "no" ]] || { echo "وضع persistence غير مدعوم بأمان في هذا الإصدار؛ لن أُنشئ قسمًا قد يفسد الفلاشة." >&2; exit 3; }
command -v lsblk >/dev/null 2>&1 || { echo "الأداة lsblk غير موجودة." >&2; exit 4; }
command -v dd >/dev/null 2>&1 || { echo "الأداة dd غير موجودة." >&2; exit 4; }
[[ "$EUID" -eq 0 ]] || { echo "شغّل من root بعد مراجعة اسم القرص." >&2; exit 5; }
echo "الأقراص: الاسم، الحجم، النوع، الناقل"
lsblk -d -o NAME,SIZE,MODEL,TRAN
read -rp "أدخل اسم القرص الكامل من عمود NAME (مثال sdb): " DISK
[[ "$DISK" =~ ^sd[a-z]+$ ]] || { echo "رفض: يقبل هذا السكربت أسماء أقراص SATA/USB من نمط sdb فقط؛ لم يتم مسح شيء." >&2; exit 6; }
DEVICE="/dev/$DISK"
[[ -b "$DEVICE" ]] || { echo "رفض: $DEVICE ليس جهاز block موجودًا." >&2; exit 7; }
[[ "$(lsblk -dn -o TYPE "$DEVICE" | tr -d '[:space:]')" == "disk" ]] || { echo "رفض: اختر القرص الكامل، لا قسمًا." >&2; exit 8; }
[[ "$(lsblk -dn -o TRAN "$DEVICE" | tr -d '[:space:]')" == "usb" ]] || { echo "رفض: القرص ليس مُعرّفًا كجهاز USB؛ لن أكتب عليه." >&2; exit 9; }
if lsblk -nr -o MOUNTPOINT "$DEVICE" | grep -q '[^[:space:]]'; then
  echo "رفض: توجد أقسام مركّبة على $DEVICE. افصلها أولًا؛ لم يتم مسح شيء." >&2; exit 10
fi
echo "تحذير نهائي: سيتم استبدال جدول الأقسام ومحتويات $DEVICE بالكامل."
read -rp "اكتب بالضبط WIPE $DISK للمتابعة: " CONF
[[ "$CONF" == "WIPE $DISK" ]] || { echo "أُلغي؛ لم يتم مسح شيء."; exit 11; }
sha256sum "$ISO"
dd if="$ISO" of="$DEVICE" bs=4M status=progress conv=fsync
sync
echo "اكتمل نسخ الصورة إلى $DEVICE. افحص جدول الأقسام قبل فصل الفلاشة."
