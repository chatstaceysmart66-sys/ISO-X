#!/usr/bin/env bash
set -Eeuo pipefail
DURATION="${1:-60}"
OUT="${2:-$(cd "$(dirname "$0")/.." && pwd)/evidence/isox-demo-$(date +%Y%m%d-%H%M%S).mp4}"
if ! command -v ffmpeg >/dev/null 2>&1; then echo "ffmpeg is required on the screen-recording host." >&2; exit 2; fi
if [[ -z "${DISPLAY:-}" ]]; then echo "DISPLAY is unset. Run this from the graphical host showing the VM; boot evidence must capture the VM display." >&2; exit 3; fi
mkdir -p "$(dirname "$OUT")"
SIZE="$(xdpyinfo 2>/dev/null | awk '/dimensions:/{print $2; exit}')"
[[ -n "$SIZE" ]] || { echo "Cannot determine display dimensions; install xdpyinfo." >&2; exit 4; }
echo "Recording ${DURATION}s from ${DISPLAY} at ${SIZE}; ensure the ISO-X VM is on-screen."
ffmpeg -y -f x11grab -framerate 30 -video_size "$SIZE" -i "$DISPLAY" -t "$DURATION" -c:v libx264 -preset veryfast -pix_fmt yuv420p "$OUT"
echo "Recorded: $OUT"
