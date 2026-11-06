#!/bin/sh
set -eu

if [ "$#" -ne 5 ]; then
  echo "Usage: isox-ci-stability.sh USER DISPLAY XAUTHORITY NONCE SECONDS" >&2
  exit 2
fi

username="$1"
display="$2"
xauthority="$3"
nonce="$4"
seconds="$5"
case "$nonce" in
  ''|*[!a-f0-9]*) echo "ISO-X CI nonce is invalid." >&2; exit 2 ;;
esac
[ "${#nonce}" -eq 32 ] || { echo "ISO-X CI nonce must contain 32 hexadecimal characters." >&2; exit 2; }
case "$seconds" in
  ''|*[!0-9]*) echo "ISO-X CI stability interval is invalid." >&2; exit 2 ;;
esac
[ "$seconds" -ge 1 ] && [ "$seconds" -le 300 ] || {
  echo "ISO-X CI stability interval must be between 1 and 300 seconds." >&2
  exit 2
}

script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
serial_device="${ISOX_CI_STABILITY_SERIAL:-/dev/ttyS0}"
console_device="${ISOX_CI_STABILITY_CONSOLE:-/dev/console}"
elapsed=0
while [ "$elapsed" -lt "$seconds" ]; do
  sleep 1
  elapsed=$((elapsed + 1))
  if ! "$script_dir/isox-desktop-window-ready.sh" "$username" "$display" "$xauthority"; then
    marker="ISOX_CI_STABILITY_FAIL nonce=$nonce elapsed=$elapsed"
    printf '%s\n' "$marker" | tee "$serial_device" "$console_device" >/dev/null
    echo "ISO-X desktop became unhealthy after readiness: $marker" >&2
    exit 1
  fi
done

marker="ISOX_CI_STABLE nonce=$nonce seconds=$seconds"
printf '%s\n' "$marker" | tee "$serial_device" "$console_device" >/dev/null
