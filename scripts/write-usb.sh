#!/usr/bin/env bash
set -Eeuo pipefail
# ISO-X USB Writer 0.4.0. Persistence creation is deliberately not offered
# until partition-table handling can be verified across BIOS/UEFI USB layouts.
validate_iso() {
  ISO="$1"
  [[ -r "$ISO" && -f "$ISO" && -s "$ISO" ]] || { echo "ملف ISO غير موجود أو فارغ أو غير قابل للقراءة." >&2; return 2; }
  [[ -r "${ISO}.sha256" && -f "${ISO}.sha256" ]] || { echo "ملف البصمة المطلوب غير موجود: ${ISO}.sha256" >&2; return 3; }
  EXPECTED_SHA256="$(awk 'NR == 1 { print $1 }' "${ISO}.sha256")"
  [[ "$EXPECTED_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || { echo "صيغة SHA-256 غير صالحة في ${ISO}.sha256" >&2; return 3; }
  ACTUAL_SHA256="$(sha256sum "$ISO" | awk '{ print $1 }')"
  [[ "${ACTUAL_SHA256,,}" == "${EXPECTED_SHA256,,}" ]] || { echo "فشل SHA-256: المتوقع $EXPECTED_SHA256 والموجود $ACTUAL_SHA256" >&2; return 3; }
  command -v xorriso >/dev/null 2>&1 || { echo "الأداة xorriso غير موجودة." >&2; return 4; }
  xorriso -indev "$ISO" -pvd_info >/dev/null || { echo "الملف لا يجتاز فحص بنية ISO؛ لم تتم الكتابة." >&2; return 4; }
  ISO_BYTES="$(stat -c '%s' "$ISO")"
}

main() {
  local iso="${1:-}" mode="${2:-no}" disk device capacity model
  [[ -n "$iso" ]] || { echo "الاستخدام: $0 /path/to/ISO-X-0.4.0-live-amd64.iso [no]" >&2; return 2; }
  [[ "$mode" == "no" ]] || { echo "وضع persistence غير مدعوم بأمان في هذا الإصدار." >&2; return 3; }
  command -v sha256sum >/dev/null 2>&1 || { echo "الأداة sha256sum غير موجودة." >&2; return 4; }
  validate_iso "$iso" || return $?
  command -v lsblk >/dev/null 2>&1 || { echo "الأداة lsblk غير موجودة." >&2; return 4; }
  command -v blockdev >/dev/null 2>&1 || { echo "الأداة blockdev غير موجودة." >&2; return 4; }
  command -v dd >/dev/null 2>&1 || { echo "الأداة dd غير موجودة." >&2; return 4; }
  [[ "$EUID" -eq 0 ]] || { echo "شغّل من root بعد مراجعة اسم القرص." >&2; return 5; }
  echo "الأقراص: الاسم، الحجم، النوع، الناقل"
  lsblk -d -o NAME,SIZE,MODEL,TRAN
  read -rp "أدخل اسم القرص الكامل من عمود NAME (مثال sdb): " disk
  [[ "$disk" =~ ^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|nvme[0-9]+n[0-9]+)$ ]] || { echo "رفض اسم جهاز القرص؛ لم تتم الكتابة." >&2; return 6; }
  device="/dev/$disk"
  [[ -b "$device" ]] || { echo "رفض: $device ليس جهاز block موجودًا." >&2; return 7; }
  [[ "$(lsblk -dn -o TYPE "$device" | tr -d '[:space:]')" == "disk" ]] || { echo "رفض: اختر القرص الكامل، لا قسمًا." >&2; return 8; }
  [[ "$(lsblk -dn -o TRAN "$device" | tr -d '[:space:]')" == "usb" ]] || { echo "رفض: القرص غير معرّف كجهاز USB؛ لم تتم الكتابة." >&2; return 9; }
  if lsblk -nr -o MOUNTPOINT "$device" | grep -q '[^[:space:]]'; then
    echo "رفض: توجد أقسام مركّبة على $device. افصلها أولاً؛ لم تتم الكتابة." >&2; return 10
  fi
  capacity="$(blockdev --getsize64 "$device")"
  (( capacity >= ISO_BYTES )) || { echo "رفض: سعة $device ($capacity bytes) أصغر من ISO ($ISO_BYTES bytes)." >&2; return 12; }
  model="$(lsblk -dn -o MODEL "$device" | sed 's/[[:space:]]*$//')"
  echo "الهدف المحدد: $device | $model | $capacity bytes"
  echo "تحذير نهائي: سيتم استبدال جدول الأقسام ومحتويات $device بالكامل."
  read -rp "اكتب بالضبط WIPE $disk للمتابعة: " CONF
  [[ "$CONF" == "WIPE $disk" ]] || { echo "أُلغي؛ لم تتم الكتابة."; return 11; }
  printf '%s  %s\n' "$ACTUAL_SHA256" "$iso"
  dd if="$iso" of="$device" bs=4M status=progress conv=fsync
  sync
  echo "اكتمل نسخ الصورة إلى $device. افحص جدول الأقسام قبل فصل الفلاشة."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
