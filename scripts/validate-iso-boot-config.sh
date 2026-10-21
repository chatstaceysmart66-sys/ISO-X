#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  local check="$1" file="$2" contents
  contents="$(cat "$file" 2>/dev/null || printf '<missing>')"
  contents="${contents//$'\n'/ }"
  printf 'BOOT CONFIG ERROR: %s; file=%s; contents=%s\n' "$check" "$file" "$contents" >&2
  exit 1
}

[[ "$#" -eq 5 ]] || {
  echo "Usage: $0 ISOLINUX_CFG LIVE_CFG GRUB_CFG CI_BOOT NONCE" >&2
  exit 2
}

isolinux_cfg="$1"
live_cfg="$2"
grub_cfg="$3"
ci_boot="$4"
nonce="$5"

for config in "$isolinux_cfg" "$live_cfg" "$grub_cfg"; do
  [[ -s "$config" ]] || fail "required boot configuration is missing or empty" "$config"
done
[[ "$ci_boot" == 0 || "$ci_boot" == 1 ]] || fail "invalid CI boot mode" "$isolinux_cfg"
if [[ "$ci_boot" == 1 && ! "$nonce" =~ ^[a-f0-9]{32}$ ]]; then
  fail "CI boot requires a 32-character lowercase hexadecimal nonce" "$live_cfg"
fi

grep -Eq '^[[:space:]]*timeout[[:space:]]+[1-9][0-9]*[[:space:]]*$' "$isolinux_cfg" ||
  fail "BIOS timeout must be finite and non-zero" "$isolinux_cfg"
grep -Eq '^[[:space:]]*default[[:space:]]+vesamenu\.c32[[:space:]]*$' "$isolinux_cfg" ||
  fail "BIOS default menu is missing" "$isolinux_cfg"

awk '
  /^label[[:space:]]/ { label = $2 }
  /^menu default[[:space:]]*$/ && label ~ /^live-/ && label !~ /-persistence$/ { default_live = 1 }
  /^append[[:space:]]/ && label ~ /^live-/ && label !~ /failsafe/ {
    if (label ~ /-persistence$/) {
      if ($0 ~ /(^|[[:space:]])persistence([[:space:]]|$)/) persistence = 1
      else invalid = 1
    } else {
      if ($0 ~ /boot=live/ && $0 !~ /(^|[[:space:]])persistence([[:space:]]|$)/) normal = 1
      else invalid = 1
    }
  }
  END { if (!default_live || !normal || !persistence || invalid) exit 1 }
' "$live_cfg" || fail "BIOS normal and persistence entries are invalid" "$live_cfg"

grep -Eq '^set timeout=[1-9][0-9]*$' "$grub_cfg" ||
  fail "UEFI GRUB timeout must be finite and non-zero" "$grub_cfg"
awk '
  /^menuentry / {
    in_live = ($0 ~ /Live system/)
    is_persistence = (tolower($0) ~ /persistence/)
  }
  in_live && /^[[:space:]]*linux[[:space:]]/ {
    if (is_persistence) {
      if ($0 ~ /(^|[[:space:]])persistence([[:space:]]|$)/) persistence = 1
      else invalid = 1
    } else {
      if ($0 ~ /boot=live/ && $0 !~ /(^|[[:space:]])persistence([[:space:]]|$)/) normal = 1
      else invalid = 1
    }
  }
  /^}/ { in_live = 0 }
  END { if (!normal || !persistence || invalid) exit 1 }
' "$grub_cfg" || fail "UEFI normal and persistence entries are invalid" "$grub_cfg"

for config in "$live_cfg" "$grub_cfg"; do
  if [[ "$ci_boot" == 1 ]]; then
    grep -Fq 'isox.ci=1' "$config" || fail "CI diagnostic parameter is missing" "$config"
    grep -Fq "isox.ci.nonce=$nonce" "$config" || fail "CI nonce parameter is missing or incorrect" "$config"
  elif grep -Eq 'isox\.ci(=|\.nonce=)' "$config"; then
    fail "release boot configuration contains CI-only parameters" "$config"
  fi
done

printf 'PASS: BIOS and UEFI have finite timeouts, normal and persistence entries, and correct CI argument isolation.\n'
