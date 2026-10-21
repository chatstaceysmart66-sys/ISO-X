#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
cat > "$TMP/bin/xorriso" <<'XORRISO'
#!/bin/sh
exit 0
XORRISO
chmod 0755 "$TMP/bin/xorriso"
export PATH="$TMP/bin:$PATH"
ISO="$TMP/test.iso"
printf 'test ISO image payload\n' > "$ISO"
sha256sum "$ISO" > "$ISO.sha256"
source "$ROOT/scripts/write-usb.sh"
validate_iso "$ISO"
[[ "$ISO_BYTES" -eq "$(stat -c '%s' "$ISO")" ]]
printf '%064d  %s\n' 0 "$ISO" > "$ISO.sha256"
if validate_iso "$ISO" 2>"$TMP/error.log"; then
  echo "FAIL: mismatched SHA-256 was accepted" >&2
  exit 1
fi
grep -Fq 'فشل SHA-256' "$TMP/error.log"

cat > "$TMP/bin/findmnt" <<'FINDMNT'
#!/bin/sh
printf '/dev/test-root\n'
FINDMNT
cat > "$TMP/bin/lsblk" <<'LSBLK'
#!/bin/sh
printf '/dev/sdb disk\n'
LSBLK
chmod 0755 "$TMP/bin/findmnt" "$TMP/bin/lsblk"
is_block_device() { [[ "$1" == /dev/test-root ]]; }
if ! is_system_disk /dev/sdb; then
  echo "FAIL: a disk backing the running system was not rejected." >&2
  exit 1
fi
cat > "$TMP/bin/lsblk" <<'LSBLK'
#!/bin/sh
printf '/dev/sda disk\n'
LSBLK
chmod 0755 "$TMP/bin/lsblk"
if is_system_disk /dev/sdb; then
  echo "FAIL: an unrelated disk was marked as the system disk." >&2
  exit 1
fi
is_block_device() { return 1; }
if is_system_disk /dev/sdb; then
  echo "FAIL: an unresolved system-disk topology was treated as safe." >&2
  exit 1
else
  status=$?
  [[ "$status" -eq 2 ]] || { echo "FAIL: expected unsafe-topology status 2, got $status." >&2; exit 1; }
fi
printf 'PASS: USB writer validates the ISO, rejects tampering, detects the system disk, and fails closed when topology is unknown.\n'