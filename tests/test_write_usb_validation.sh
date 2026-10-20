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
printf 'PASS: USB writer accepts a matching digest and rejects tampering before any device write.\n'