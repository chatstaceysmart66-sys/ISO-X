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

deadline=$(( $(date +%s) + 120 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if systemctl is-active --quiet graphical.target \
    && systemctl is-active --quiet lightdm.service \
    && pgrep -x Xorg >/dev/null 2>&1; then
    for session in $(loginctl list-sessions --no-legend 2>/dev/null | awk '$3 == "user" {print $1}'); do
      properties="$(loginctl show-session "$session" -p Name -p Type -p State 2>/dev/null || true)"
      if printf '%s\n' "$properties" | grep -qx 'Name=user' \
        && printf '%s\n' "$properties" | grep -Eq '^Type=(x11|wayland)$' \
        && printf '%s\n' "$properties" | grep -qx 'State=active'; then
        marker="ISOX_CI_READY nonce=$NONCE"
        printf '%s\n' "$marker" > /dev/ttyS0
        printf '%s\n' "$marker" > /dev/console
        exit 0
      fi
    done
  fi
  sleep 1
done

echo "ISO-X CI readiness probe timed out before an active LightDM X session." >&2
exit 1
