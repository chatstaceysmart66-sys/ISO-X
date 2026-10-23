#!/bin/sh
set -eu

username="${1:-user}"
display="${2:-}"
xauthority="${3:-}"
[ -n "$display" ] && [ -r "$xauthority" ] || exit 1
uid="$(id -u "$username")" || exit 1
pgrep -u "$uid" -f '/usr/share/iso-x/iso_x_gtk[.]py' >/dev/null 2>&1 || exit 1
pgrep -u "$uid" -x openbox >/dev/null 2>&1 || exit 1
DISPLAY="$display" XAUTHORITY="$xauthority" wmctrl -l -G 2>/dev/null |
  awk '
    NF >= 8 {
      title = $8
      for (field = 9; field <= NF; field++) title = title " " $field
      if ($5 >= 640 && $6 >= 480 && title ~ /ISO-X/) visible = 1
    }
    END { exit !visible }
  '