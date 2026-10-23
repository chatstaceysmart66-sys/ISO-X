#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/root/etc/isox"
cat > "$TMP/bin/plymouth" <<'PLYMOUTH'
#!/bin/sh
printf '%s\n' "$*" >> "$PLYMOUTH_LOG"
PLYMOUTH
chmod 0755 "$TMP/bin/plymouth"
OUTPUT="$(PATH="$TMP/bin:$PATH" PLYMOUTH_LOG="$TMP/plymouth.log" \
  ISOX_INITRAMFS_ROOT="$TMP/root" \
  sh "$ROOT/initramfs/scripts/init-premount/isox-watermark-guard" 2>&1)"
[[ "$OUTPUT" == *"watermark optional; policy metadata is missing. Continuing boot."* ]]
grep -Fq 'message --text=ISO-X: watermark optional;' "$TMP/plymouth.log"
grep -Fxq 'quit' "$TMP/plymouth.log"
printf 'PASS: optional watermark warning is sent to Plymouth and boot continues when metadata is absent.\n'