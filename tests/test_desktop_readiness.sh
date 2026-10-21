#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/isox-desktop-ready.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
: > "$TMP/xauthority"

cat > "$TMP/bin/id" <<'ID'
#!/bin/sh
[ "${1:-}" = "-u" ] && [ "${2:-}" = "user" ] || exit 2
printf '1000\n'
ID
cat > "$TMP/bin/pgrep" <<'PGREP'
#!/bin/sh
case "$*" in
  *'/usr/share/iso-x/iso_x_gtk[.]py'*) [ "${FAKE_APP_PRESENT:-0}" = 1 ] ;;
  *'-x openbox'*) [ "${FAKE_OPENBOX_PRESENT:-0}" = 1 ] ;;
  *) exit 2 ;;
esac
PGREP
cat > "$TMP/bin/wmctrl" <<'WMCTRL'
#!/bin/sh
[ "${1:-}" = "-l" ] && [ "${2:-}" = "-G" ] || exit 2
printf '%s\n' "${FAKE_WINDOWS:-}"
WMCTRL
chmod 0755 "$TMP/bin/id" "$TMP/bin/pgrep" "$TMP/bin/wmctrl"

VALID_WINDOW='0x03a00007  0  0  0  1160  740 host ISO-X Desktop'
if ! FAKE_APP_PRESENT=1 FAKE_OPENBOX_PRESENT=1 FAKE_WINDOWS="$VALID_WINDOW" PATH="$TMP/bin:$PATH" \
  sh "$ROOT/scripts/isox-desktop-window-ready.sh" user :0 "$TMP/xauthority"; then
  echo "FAIL: a running ISO-X window with desktop dimensions was rejected." >&2
  exit 1
fi

for scenario in missing-app missing-openbox missing-window small-window wrong-title missing-auth; do
  app_present=1
  openbox_present=1
  windows="$VALID_WINDOW"
  auth="$TMP/xauthority"
  case "$scenario" in
    missing-app) app_present=0 ;;
    missing-openbox) openbox_present=0 ;;
    missing-window) windows='' ;;
    small-window) windows='0x03a00007 0 0 0 100 100 host ISO-X Desktop' ;;
    wrong-title) windows='0x03a00007 0 0 0 1160 740 host Terminal' ;;
    missing-auth) auth="$TMP/missing" ;;
  esac
  if FAKE_APP_PRESENT="$app_present" FAKE_OPENBOX_PRESENT="$openbox_present" FAKE_WINDOWS="$windows" PATH="$TMP/bin:$PATH" \
    sh "$ROOT/scripts/isox-desktop-window-ready.sh" user :0 "$auth"; then
    echo "FAIL: invalid desktop readiness was accepted ($scenario)." >&2
    exit 1
  fi
done

echo 'PASS: readiness requires a live ISO-X process and a titled, desktop-sized X11 window.'