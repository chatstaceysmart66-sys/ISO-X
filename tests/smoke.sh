#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m py_compile \
  "$ROOT/app/iso_x_shell.py" \
  "$ROOT/app/iso_x_gtk.py" \
  "$ROOT/app/isox_appcenter.py" \
  "$ROOT/app/isox_welcome.py" \
  "$ROOT/scripts/isox-preload.py" \
  "$ROOT/scripts/secure-vault.py" \
  "$ROOT/scripts/isox-run.py" \
  "$ROOT/scripts/encode-watermark.py" \
  "$ROOT/scripts/isox-speedtest" \
  "$ROOT/tests/test_upstream_integration.py" \
  "$ROOT/tests/test_build_contracts.py" \
  "$ROOT/tests/test_schema.py" \
  "$ROOT/tests/test_source_config.py" \
  "$ROOT/tests/test_secure_vault.py"
python3 "$ROOT/tests/test_schema.py"
python3 "$ROOT/tests/test_source_config.py"
python3 "$ROOT/tests/test_build_contracts.py"
python3 "$ROOT/tests/test_upstream_integration.py"
python3 "$ROOT/tests/test_secure_vault.py"
bash -n \
  "$ROOT/scripts/build-iso.sh" "$ROOT/scripts/isox-zram-setup" \
  "$ROOT/scripts/generate-dev-signing-key.sh" "$ROOT/scripts/collect-performance.sh" \
  "$ROOT/scripts/record-demo.sh" "$ROOT/scripts/write-usb.sh" \
  "$ROOT/scripts/secure-vault.sh" "$ROOT/scripts/isox-snap-window.sh" \
  "$ROOT/scripts/install-build-deps.sh" "$ROOT/scripts/apply-windows-look.sh" "$ROOT/scripts/toggle-airplane.sh" "$ROOT/scripts/secureboot-enroll.sh" \
  "$ROOT/config/hooks/live/0100-isox-watermark.hook.chroot" \
  "$ROOT/config/hooks/live/0050-isox-locales.hook.chroot" "$ROOT/config/hooks/live/0200-isox-plymouth.hook.chroot" \
  "$ROOT/config/hooks/live/0300-isox-services.hook.chroot" \
  "$ROOT/tests/test_watermark_integrity.sh" "$ROOT/tests/test_secureboot_validation.sh" \
  "$ROOT/tests/test_initramfs_watermark_guard.sh" "$ROOT/tests/qemu-acceptance.sh" "$ROOT/initramfs/hooks/isox-watermark" \
  "$ROOT/tests/test_write_usb_validation.sh" \
  "$ROOT/initramfs/scripts/init-premount/isox-watermark-guard" "$ROOT/auto/config"
sh -n "$ROOT/initramfs/hooks/isox-watermark" "$ROOT/initramfs/scripts/init-premount/isox-watermark-guard"
if command -v openssl >/dev/null 2>&1; then
  bash "$ROOT/tests/test_watermark_integrity.sh"
  bash "$ROOT/tests/test_secureboot_validation.sh"
  bash "$ROOT/tests/test_initramfs_watermark_guard.sh"
  bash "$ROOT/tests/test_write_usb_validation.sh"
else
  echo "SKIP: OpenSSL not installed"
fi
echo "PASS: source syntax and tests complete; these do not imply ISO build or boot acceptance."
