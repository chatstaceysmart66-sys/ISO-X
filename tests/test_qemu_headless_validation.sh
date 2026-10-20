#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
printf 'not a bootable ISO; only tests the failure detector\n' > "$TMP/test.iso"
cat > "$TMP/bin/qemu-system-x86_64" <<'QEMU'
#!/bin/sh
while :; do sleep 1; done
QEMU
cat > "$TMP/bin/qemu-img" <<'QEMU_IMG'
#!/bin/sh
exit 0
QEMU_IMG
chmod 0755 "$TMP/bin/qemu-system-x86_64" "$TMP/bin/qemu-img"
if ISOX_QEMU_TIMEOUT=1 PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/evidence" \
  >"$TMP/output.log" 2>&1; then
  echo "FAIL: QEMU without graphical.target serial evidence was accepted." >&2
  exit 1
fi
grep -Fq 'FAIL: bios-headless did not reach graphical.target' "$TMP/output.log"
grep -Fq 'QEMU/timeout exit=124' "$TMP/output.log"
printf 'PASS: headless QEMU without graphical.target serial evidence is rejected (detector test only).\n'