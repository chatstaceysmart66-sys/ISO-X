#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
printf 'not a bootable ISO; only tests the failure detector\n' > "$TMP/test.iso"
cat > "$TMP/bin/qemu-system-x86_64" <<'QEMU'
#!/bin/sh
if [ "${1:-}" = -version ]; then
  echo 'QEMU emulator version 9.2.0 (fake test binary)'
  exit 0
fi
serial=''
while [ "$#" -gt 0 ]; do
  if [ "$1" = -serial ]; then
    serial=${2#file:}
    shift 2
  else
    shift
  fi
done
case "${FAKE_QEMU_KIND:-timeout}" in
  success)
    sleep 1
    printf 'ISOX_CI_READY nonce=%s\n' "$FAKE_QEMU_NONCE" >> "$serial"
    while :; do sleep 1; done
    ;;
  misleading)
    printf 'Reached target Graphical Interface\nISOX_CI_READY nonce=ffffffffffffffffffffffffffffffff\n' >> "$serial"
    while :; do sleep 1; done
    ;;
  no-serial)
    while :; do sleep 1; done
    ;;
  immediate-error)
    echo 'qemu-system-x86_64: test infrastructure error' >&2
    exit 42
    ;;
  *)
    echo "unknown fake mode" >&2
    exit 64
    ;;
esac
QEMU
chmod 0755 "$TMP/bin/qemu-system-x86_64"
NONCE=0123456789abcdef0123456789abcdef

FAKE_QEMU_KIND=success FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=20 \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/success" \
  >"$TMP/success.log" 2>&1
python3 - "$TMP/success/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "PASS_BOOT", r
assert r["marker_seen"] is True and r["process_group_clean"] is True, r
assert r["duration_seconds"] < 5, r
assert r["serial_bytes"] > 0, r
PY

if FAKE_QEMU_KIND=misleading ISOX_QEMU_TIMEOUT=2 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/misleading" >"$TMP/misleading.log" 2>&1; then
  echo "FAIL: a stale/mismatched nonce or graphical.target text was accepted." >&2
  exit 1
fi
python3 - "$TMP/misleading/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "DISPLAY_OR_LOGIN_FAILURE", r
assert r["marker_seen"] is False, r
PY

if FAKE_QEMU_KIND=no-serial ISOX_QEMU_TIMEOUT=2 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/empty" >"$TMP/empty.log" 2>&1; then
  echo "FAIL: an empty serial log was accepted." >&2
  exit 1
fi
python3 - "$TMP/empty/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "NO_SERIAL_OUTPUT", r
assert r["serial_bytes"] == 0 and r["marker_seen"] is False, r
assert all(value is None for value in r["serial_indicators"].values()), r
PY

if FAKE_QEMU_KIND=immediate-error ISOX_QEMU_TIMEOUT=5 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/error" >"$TMP/error.log" 2>&1; then
  echo "FAIL: an immediate QEMU infrastructure error was accepted." >&2
  exit 1
fi
python3 - "$TMP/error/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "QEMU_INFRASTRUCTURE_FAILURE", r
assert r["qemu_exit_code"] == 42 and r["marker_seen"] is False, r
PY

printf 'PASS: nonce marker stops QEMU early; spoofed text, empty serial, timeout, and immediate QEMU errors are rejected and classified.\n'
