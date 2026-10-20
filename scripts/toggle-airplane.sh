#!/usr/bin/env bash
set -Eeuo pipefail
RFKILL="$(command -v rfkill || true)"
[[ -n "$RFKILL" ]] || { echo "rfkill is not installed" >&2; exit 2; }
STATE="$($RFKILL list 2>/dev/null || true)"
COUNT="$(grep -c 'Soft blocked:' <<<"$STATE" || true)"
[[ "$COUNT" -gt 0 ]] || {
  MESSAGE="لا توجد أجهزة لاسلكية يعرضها النظام؛ قد لا يدعمها QEMU."
  command -v notify-send >/dev/null 2>&1 && notify-send "ISO-X — وضع الطيران" "$MESSAGE" || true
  echo "$MESSAGE" >&2
  exit 3
}
BLOCKED="$(grep -c 'Soft blocked: yes' <<<"$STATE" || true)"
if [[ "$BLOCKED" -eq "$COUNT" ]]; then ACTION=unblock; MESSAGE="تم طلب إيقاف وضع الطيران"; else ACTION=block; MESSAGE="تم طلب تفعيل وضع الطيران"; fi
if [[ "$EUID" -eq 0 ]]; then
  "$RFKILL" "$ACTION" all
else
  command -v pkexec >/dev/null 2>&1 || { echo "pkexec is required to change radio state" >&2; exit 4; }
  pkexec "$RFKILL" "$ACTION" all
fi
AFTER="$($RFKILL list 2>/dev/null || true)"
if [[ "$ACTION" == block ]] && ! grep -q 'Soft blocked: yes' <<<"$AFTER"; then
  MESSAGE="لم يؤكد rfkill حظر الأجهزة؛ افحص صلاحيات النظام والعتاد."
  command -v notify-send >/dev/null 2>&1 && notify-send "ISO-X — وضع الطيران" "$MESSAGE" || true
  echo "$MESSAGE" >&2
  exit 5
fi
if [[ "$ACTION" == unblock ]] && ! grep -q 'Soft blocked: no' <<<"$AFTER"; then
  MESSAGE="لم يؤكد rfkill رفع الحظر؛ افحص صلاحيات النظام والعتاد."
  command -v notify-send >/dev/null 2>&1 && notify-send "ISO-X — وضع الطيران" "$MESSAGE" || true
  echo "$MESSAGE" >&2
  exit 6
fi
command -v notify-send >/dev/null 2>&1 && notify-send "ISO-X — وضع الطيران" "$MESSAGE" || true
echo "$MESSAGE"
