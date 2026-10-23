#!/usr/bin/env bash
set -Eeuo pipefail
OUT_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)/evidence/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT_DIR"
{
  echo "ISO-X performance capture"
  date --iso-8601=seconds
  echo "Host: $(hostname)"
  echo "Kernel: $(uname -a)"
  echo "CPU: $(lscpu 2>/dev/null | grep -E '^(Model name|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket):' || true)"
  echo "--- systemd-analyze ---"
  systemd-analyze 2>&1 || true
  echo "--- systemd-analyze blame (top 20) ---"
  systemd-analyze blame 2>&1 | head -20 || true
  echo "--- free -h ---"
  free -h
  echo "--- top (5 snapshots) ---"
  top -b -n 5 -d 1 | head -100
  echo "--- ps aux --sort=-%mem | head -10 ---"
  ps aux --sort=-%mem | head -10
  echo "--- zram ---"
  zramctl 2>&1 || true
  echo "--- secure boot ---"
  mokutil --sb-state 2>&1 || true
} | tee "$OUT_DIR/performance.txt"
echo "Saved: $OUT_DIR/performance.txt"
echo "Do not label these numbers as acceptance results unless collected on the stated 2-core / 1GB test target after a fresh boot."
