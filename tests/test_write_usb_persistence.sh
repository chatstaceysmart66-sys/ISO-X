#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/isox-usb-persistence.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

RAW="$TMP/hybrid-usb.raw"
truncate -s 2G "$RAW"
FILESYSTEM="$TMP/persistence.ext4"
truncate -s 32M "$FILESYSTEM"
printf 'survives simulated reboot\n' > "$TMP/reboot-marker.txt"
python3 - "$RAW" <<'PY'
import struct
import sys

mbr = bytearray(512)
struct.pack_into("<I", mbr, 440, 0x584f5349)
entries = (
    (0x80, 0x00, 64, 32704),
    (0x00, 0xef, 6860, 6656),
)
for index, (status, partition_type, start, size) in enumerate(entries):
    struct.pack_into(
        "<B3sB3sII",
        mbr,
        446 + index * 16,
        status,
        b"\x00\x02\x00",
        partition_type,
        b"\xfe\xff\xff",
        start,
        size,
    )
mbr[510:512] = b"\x55\xaa"
with open(sys.argv[1], "r+b") as device:
    device.write(mbr)
PY

source "$ROOT/scripts/write-usb.sh"
ISO_BYTES=$((16 * 1024 * 1024))

blockdev() {
  case "$1" in
    --getss) printf '512\n' ;;
    --getsz) printf '4194304\n' ;;
    *) return 2 ;;
  esac
}
partprobe() { [[ "$1" == "$RAW" ]]; }
udevadm() { [[ "$1" == settle ]]; }
is_block_device() { [[ "$1" == "${RAW}3" ]]; }
mkfs.ext4() {
  [[ "$*" == *"-L persistence"* && "${*: -1}" == "${RAW}3" ]]
  command mkfs.ext4 -q -F -m 0 -L persistence "$FILESYSTEM"
}
mount() {
  [[ "$1" == "${RAW}3" && -d "$2" ]]
  debugfs -w -R "write $TMP/reboot-marker.txt /reboot-marker.txt" "$FILESYSTEM" >/dev/null 2>&1
}
umount() {
  [[ -s "$1/persistence.conf" ]]
  debugfs -w -R "write $1/persistence.conf /persistence.conf" "$FILESYSTEM" >/dev/null 2>&1
  rm -f "$1/persistence.conf"
}
sync() { :; }

create_persistence_partition "$RAW" test-disk

debugfs -R 'cat /persistence.conf' "$FILESYSTEM" 2>/dev/null | grep -Fxq '/ union'
debugfs -R 'cat /reboot-marker.txt' "$FILESYSTEM" 2>/dev/null | cmp - "$TMP/reboot-marker.txt"
dumpe2fs -h "$FILESYSTEM" 2>/dev/null | grep -Fxq 'Filesystem volume name:   persistence'
python3 - "$RAW" <<'PY'
import json
import subprocess
import sys

table = json.loads(subprocess.check_output(["sfdisk", "--json", sys.argv[1]], text=True))
partitions = table["partitiontable"]["partitions"]
assert len(partitions) == 3, partitions
assert partitions[2]["node"] == sys.argv[1] + "3", partitions[2]
assert partitions[2]["start"] == 32768, partitions[2]
assert partitions[2]["size"] == 4161536, partitions[2]
assert partitions[2]["type"] == "83", partitions[2]
PY
printf 'PASS: persistence creates MBR partition 3 and ext4 / union; a marker survives simulated unmount/reopen.\n'
