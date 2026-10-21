#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/isox-usb-persistence.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

RAW="$TMP/hybrid-usb.raw"
truncate -s 2G "$RAW"
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
}
mount() {
  [[ "$1" == "${RAW}3" && -d "$2" ]]
}
umount() {
  [[ -s "$1/persistence.conf" ]]
  cp "$1/persistence.conf" "$TMP/persistence.conf"
  rm "$1/persistence.conf"
}
sync() { :; }

create_persistence_partition "$RAW" test-disk

grep -Fxq '/ union' "$TMP/persistence.conf"
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
printf 'PASS: persistence creation appends only MBR partition 3, requests ext4 formatting, and writes / union.\n'
