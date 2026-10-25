#!/usr/bin/env bash
set -Eeuo pipefail
# ISO-X USB Writer 0.4.0.

PERSISTENCE_MOUNT=""
PERSISTENCE_MOUNTED=0

cleanup() {
  if [[ "$PERSISTENCE_MOUNTED" -eq 1 && -n "$PERSISTENCE_MOUNT" ]]; then
    if ! umount "$PERSISTENCE_MOUNT"; then
      echo "تحذير: تعذر فصل قسم persistence من $PERSISTENCE_MOUNT أثناء التنظيف." >&2
    fi
  fi
  if [[ -n "$PERSISTENCE_MOUNT" && -d "$PERSISTENCE_MOUNT" ]]; then
    if ! rmdir -- "$PERSISTENCE_MOUNT"; then
      echo "تحذير: تعذر إزالة مجلد التركيب المؤقت $PERSISTENCE_MOUNT." >&2
    fi
  fi
}
trap cleanup EXIT

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

is_block_device() {
  [[ -b "$1" ]]
}

is_system_disk() {
  local selected_device="$1" mountpoint source devices path type found_source=0
  for mountpoint in / /boot /boot/efi /run/live/medium /lib/live/mount/medium; do
    [[ -e "$mountpoint" ]] || continue
    source="$(findmnt --noheadings --raw --output SOURCE --target "$mountpoint" 2>/dev/null)" || continue
    source="${source%%\[*}"
    is_block_device "$source" || continue
    found_source=1
    devices="$(lsblk --inverse --noheadings --raw --paths --output NAME,TYPE "$source" 2>/dev/null)" || return 2
    while read -r path type; do
      if [[ "$type" == disk && "$path" == "$selected_device" ]]; then
        return 0
      fi
    done <<< "$devices"
  done
  [[ "$found_source" -eq 1 ]] || return 2
  return 1
}

create_persistence_partition() {
  local device="$1" first_free partition_size partition_spec partition

  read -r first_free partition_size < <(persistence_partition_bounds "$device") ||
    { echo "تعذر حساب مساحة قسم persistence." >&2; return 22; }

  # The ISO hybrid GPT entries overlap by design; append to its DOS MBR instead.
  partition_spec="$(sfdisk_partition_node "$device" before)" ||
    { echo "رفض: لا يمكن إثبات جدول MBR hybrid المتوقع؛ لم يُنشأ قسم persistence." >&2; return 24; }
  [[ "$partition_spec" == 3 ]] ||
    { echo "رفض: لم يتبقّ موضع MBR ثالث للقسم؛ لم يُنشأ قسم persistence." >&2; return 24; }
  printf 'start=%s, size=%s, type=83\n' "$first_free" "$partition_size" |
    sfdisk --append --no-reread --wipe never "$device" ||
    { echo "فشل إضافة قسم Linux رقم 3 إلى جدول MBR." >&2; return 25; }
  partition="$(sfdisk_partition_node "$device" after "$first_free" "$partition_size")" ||
    { echo "فشل التحقق من قسم MBR الجديد بعد كتابته." >&2; return 26; }
  partprobe "$device" || { echo "تعذر تحديث جدول الأقسام في النواة." >&2; return 27; }
  udevadm settle || { echo "فشل انتظار استقرار أجهزة udev." >&2; return 28; }
  is_block_device "$partition" || { echo "لم يظهر جهاز القسم المتوقع: $partition." >&2; return 27; }

  mkfs.ext4 -F -m 0 -L persistence "$partition"
  PERSISTENCE_MOUNT="$(mktemp -d "${TMPDIR:-/tmp}/isox-persistence.XXXXXX")"
  mount "$partition" "$PERSISTENCE_MOUNT"
  PERSISTENCE_MOUNTED=1
  printf '/ union\n' > "$PERSISTENCE_MOUNT/persistence.conf"
  sync
  umount "$PERSISTENCE_MOUNT"
  PERSISTENCE_MOUNTED=0
  rmdir -- "$PERSISTENCE_MOUNT"
  PERSISTENCE_MOUNT=""
  printf 'Persistence partition created: %s (label persistence; / union).\n' "$partition"
}

persistence_partition_bounds() {
  local device="$1" sector_size disk_sectors iso_sectors first_free last_free min_sectors
  sector_size="$(blockdev --getss "$device")"
  disk_sectors="$(blockdev --getsz "$device")"
  [[ "$sector_size" == 512 && "$disk_sectors" =~ ^[0-9]+$ ]] || return 1
  iso_sectors=$(( (ISO_BYTES + 511) / 512 ))
  first_free=$(( ((iso_sectors + 2047) / 2048) * 2048 ))
  last_free=$(( disk_sectors - 1 ))
  (( last_free > 4294967295 )) && last_free=4294967295
  min_sectors=$(( 1024*1024*1024 / 512 ))
  (( last_free >= first_free && last_free - first_free + 1 >= min_sectors )) || return 1
  printf '%s %s\n' "$first_free" "$((last_free - first_free + 1))"
}

sfdisk_partition_node() {
  python3 - "$1" "${2:-before}" "${3:-}" "${4:-}" <<'PY'
import json
import re
import subprocess
import sys

device, expected_state, start, size = sys.argv[1:]
try:
    result = subprocess.run(
        ["sfdisk", "--json", device],
        capture_output=True,
        check=True,
        text=True,
    )
    table = json.loads(result.stdout)["partitiontable"]
except (OSError, subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as error:
    raise SystemExit(f"cannot read MBR partition table: {error}")

partitions = table.get("partitions", [])
numbers = []
for partition in partitions:
    match = re.fullmatch(re.escape(device) + r"p?([0-9]+)", partition.get("node", ""))
    if not match:
        raise SystemExit("partition node does not match the selected disk")
    numbers.append(int(match.group(1)))

if table.get("label") != "dos":
    raise SystemExit(f"expected an MBR (dos) table, found {table.get('label')!r}")
if expected_state == "before":
    if numbers != [1, 2] or partitions[0].get("type") not in ("0", "00") or partitions[1].get("type") != "ef":
        raise SystemExit("expected exactly the two ISO-X hybrid MBR entries")
    print(3)
elif expected_state == "after":
    if (
        numbers != [1, 2, 3]
        or partitions[2].get("type") != "83"
        or partitions[2].get("start") != int(start)
        or partitions[2].get("size") != int(size)
    ):
        raise SystemExit("new MBR partition does not match the requested Linux partition")
    print(partitions[2]["node"])
else:
    raise SystemExit("invalid partition-table validation mode")
PY
}

main() {
  local iso="${1:-}" mode="${2:-no}" disk device capacity model confirmation
  [[ -n "$iso" ]] || { echo "الاستخدام: $0 /path/to/ISO-X-0.4.0-live-amd64.iso [no|persistence]" >&2; return 2; }
  [[ "$mode" == "no" || "$mode" == "persistence" ]] || {
    echo "الوضع يقبل no أو persistence فقط." >&2; return 3;
  }
  for cmd in sha256sum xorriso lsblk blockdev dd findmnt; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "الأداة المطلوبة غير موجودة: $cmd" >&2; return 4; }
  done
  if [[ "$mode" == "persistence" ]]; then
    for cmd in sfdisk python3 mkfs.ext4 mount umount partprobe udevadm; do
      command -v "$cmd" >/dev/null 2>&1 || { echo "ميزة persistence تتطلب الأداة غير الموجودة: $cmd" >&2; return 4; }
    done
  fi
  validate_iso "$iso" || return $?
  if [[ "$mode" == "persistence" ]]; then
    sfdisk_partition_node "$iso" before >/dev/null ||
      { echo "رفض: ملف ISO لا يحمل جدول MBR hybrid المتوقع؛ لم تتم الكتابة." >&2; return 16; }
  fi
  [[ "$EUID" -eq 0 ]] || { echo "شغّل من root بعد مراجعة اسم القرص." >&2; return 5; }
  echo "الأقراص: الاسم، الحجم، النوع، الناقل"
  lsblk -d -o NAME,SIZE,MODEL,TRAN
  read -rp "أدخل اسم القرص الكامل من عمود NAME (مثال sdb): " disk
  [[ "$disk" =~ ^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|nvme[0-9]+n[0-9]+)$ ]] ||
    { echo "رفض اسم جهاز القرص؛ لم تتم الكتابة." >&2; return 6; }
  device="/dev/$disk"
  is_block_device "$device" || { echo "رفض: $device ليس جهاز block موجودًا." >&2; return 7; }
  [[ "$(lsblk -dn -o TYPE "$device" | tr -d '[:space:]')" == "disk" ]] ||
    { echo "رفض: اختر القرص الكامل، لا قسمًا." >&2; return 8; }
  [[ "$(lsblk -dn -o TRAN "$device" | tr -d '[:space:]')" == "usb" ]] ||
    { echo "رفض: القرص غير معرّف كجهاز USB؛ لم تتم الكتابة." >&2; return 9; }
  if is_system_disk "$device"; then
    echo "رفض: $device يحتوي نظام التشغيل أو وسيط الإقلاع الحالي؛ لم تتم الكتابة." >&2
    return 10
  else
    local system_disk_status=$?
    if [[ "$system_disk_status" -ne 1 ]]; then
      echo "رفض: تعذر تحديد قرص النظام بأمان؛ لم تتم الكتابة." >&2
      return 10
    fi
  fi
  if lsblk -nr -o MOUNTPOINT "$device" | grep -q '[^[:space:]]'; then
    echo "رفض: توجد أقسام مركّبة على $device. افصلها أولاً؛ لم تتم الكتابة." >&2; return 11
  fi
  capacity="$(blockdev --getsize64 "$device")"
  (( capacity >= ISO_BYTES )) || { echo "رفض: سعة $device ($capacity bytes) أصغر من ISO ($ISO_BYTES bytes)." >&2; return 12; }
  if [[ "$mode" == "persistence" ]] && ! persistence_partition_bounds "$device" >/dev/null; then
    echo "رفض: يلزم 1 GiB على الأقل من المساحة القابلة للعنونة بعد الصورة لقسم persistence." >&2
    return 13
  fi
  model="$(lsblk -dn -o MODEL "$device" | sed 's/[[:space:]]*$//')"
  echo "الهدف المحدد: $device | $model | $capacity bytes | mode=$mode"
  echo "تحذير نهائي: سيتم استبدال جدول الأقسام ومحتويات $device بالكامل."
  read -rp "اكتب بالضبط WIPE $disk للمتابعة: " confirmation
  [[ "$confirmation" == "WIPE $disk" ]] || { echo "أُلغي؛ لم تتم الكتابة."; return 14; }
  if [[ "$mode" == "persistence" ]]; then
    read -rp "سيُنشأ قسم persistence ext4 في المساحة المتبقية. اكتب CREATE PERSISTENCE: " confirmation
    [[ "$confirmation" == "CREATE PERSISTENCE" ]] || { echo "أُلغي؛ لم تتم الكتابة."; return 15; }
  fi

  printf '%s  %s\n' "$ACTUAL_SHA256" "$iso"
  dd if="$iso" of="$device" bs=4M status=progress conv=fsync
  sync
  if [[ "$mode" == "persistence" ]]; then
    create_persistence_partition "$device" "$disk"
  fi
  echo "اكتمل نسخ الصورة إلى $device. افحص جدول الأقسام قبل فصل الفلاشة."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
