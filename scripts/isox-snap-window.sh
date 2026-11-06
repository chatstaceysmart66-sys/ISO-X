#!/usr/bin/env bash
set -euo pipefail
SIDE="${1:-}"
[[ "$SIDE" == left || "$SIDE" == right ]] || { echo "usage: isox-snap-window.sh left|right" >&2; exit 2; }
command -v xrandr >/dev/null 2>&1 || { echo "xrandr is not installed" >&2; exit 3; }
command -v wmctrl >/dev/null 2>&1 || { echo "wmctrl is not installed" >&2; exit 3; }
RESOLUTION="$(xrandr --current | awk '/\*/ {print $1; exit}')"
[[ "$RESOLUTION" =~ ^([0-9]+)x([0-9]+)$ ]] || { echo "Could not read screen resolution" >&2; exit 4; }
WIDTH="${BASH_REMATCH[1]}"; HEIGHT="${BASH_REMATCH[2]}"
HALF=$((WIDTH / 2)); USE_HEIGHT=$((HEIGHT - 42)); X=0
if [[ "$SIDE" == right ]]; then X=$HALF; fi
wmctrl -r :ACTIVE: -b remove,maximized_vert,maximized_horz
wmctrl -r :ACTIVE: -e "0,$X,0,$HALF,$USE_HEIGHT"
