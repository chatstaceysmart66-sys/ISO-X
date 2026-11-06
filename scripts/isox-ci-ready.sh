#!/bin/sh
set -eu

CMDLINE="$(cat /proc/cmdline)"
case " $CMDLINE " in
  *" isox.ci=1 "*) ;;
  *) exit 1 ;;
esac
NONCE="$(printf '%s\n' "$CMDLINE" | sed -n 's/.*isox\.ci\.nonce=\([a-f0-9]*\).*/\1/p')"
case "$NONCE" in
  ''|*[!a-f0-9]*) exit 1 ;;
esac
[ "${#NONCE}" -eq 32 ] || exit 1
STABILITY_SECONDS="$(printf '%s\n' "$CMDLINE" | sed -n 's/.*isox\.ci\.stability=\([0-9]*\).*/\1/p')"
case "$STABILITY_SECONDS" in
  ''|*[!0-9]*) echo "ISO-X CI stability interval is missing or invalid." >&2; exit 1 ;;
esac
[ "$STABILITY_SECONDS" -ge 1 ] && [ "$STABILITY_SECONDS" -le 300 ] || {
  echo "ISO-X CI stability interval must be between 1 and 300 seconds." >&2
  exit 1
}
SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
DESKTOP_READY_CHECK="$SCRIPT_DIR/isox-desktop-window-ready.sh"

deadline=$(( $(date +%s) + 120 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if systemctl is-active --quiet graphical.target \
    && systemctl is-active --quiet lightdm.service \
    && pgrep -x Xorg >/dev/null 2>&1; then
    for session in $(loginctl list-sessions --no-legend 2>/dev/null | awk '$3 == "user" {print $1}'); do
      properties="$(loginctl show-session "$session" -p Name -p Type -p State -p Display 2>/dev/null || true)"
      if printf '%s\n' "$properties" | grep -qx 'Name=user' \
        && printf '%s\n' "$properties" | grep -Eq '^Type=(x11|wayland)$' \
        && printf '%s\n' "$properties" | grep -qx 'State=active'; then
        display="$(printf '%s\n' "$properties" | sed -n 's/^Display=//p')"
        xorg="$(pgrep -a -x Xorg 2>/dev/null | sed -n '1p' || true)"
        xauthority="$(printf '%s\n' "$xorg" | sed -n 's/.* -auth \([^ ]*\).*/\1/p')"
        if "$DESKTOP_READY_CHECK" user "$display" "$xauthority" 2>/dev/null; then
          marker="ISOX_CI_READY nonce=$NONCE"
          printf '%s\n' "$marker" > /dev/ttyS0
          printf '%s\n' "$marker" > /dev/console
          "$SCRIPT_DIR/isox-ci-stability.sh" user "$display" "$xauthority" "$NONCE" "$STABILITY_SECONDS" || exit 1
          exit 0
        fi
      fi
    done
  fi
  sleep 1
done

echo "ISO-X CI readiness probe timed out before the ISO-X GTK window was visible in the active LightDM session." >&2
exit 1
