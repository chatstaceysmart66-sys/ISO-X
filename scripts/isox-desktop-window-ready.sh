#!/bin/sh
set -eu

username="${1:-user}"
display="${2:-}"
xauthority="${3:-}"
[ -n "$display" ] && [ -r "$xauthority" ] || exit 1
uid="$(id -u "$username")" || exit 1
pgrep -u "$uid" -f '/usr/share/iso-x/iso_x_gtk[.]py' >/dev/null 2>&1 || exit 1
pgrep -u "$uid" -x openbox >/dev/null 2>&1 || exit 1
pgrep -u "$uid" -x tint2 >/dev/null 2>&1 || exit 1
windows="$(DISPLAY="$display" XAUTHORITY="$xauthority" xwininfo -root -tree 2>/dev/null)" || exit 1
printf '%s\n' "$windows" |
  awk '
    /"ISO-X/ {
      geometry = $0
      if (match(geometry, /[0-9]+x[0-9]+[+-][0-9]+[+-][0-9]+/)) {
        geometry = substr(geometry, RSTART, RLENGTH)
        sub(/[+-].*/, "", geometry)
        split(geometry, dimensions, "x")
        if (dimensions[1] >= 640 && dimensions[2] >= 480) visible = 1
      }
    }
    END { exit !visible }
  '