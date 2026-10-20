#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-help}"
ISO="${2:-$ROOT/ISO-X-0.4.0-live-amd64.iso}"
EVIDENCE="${3:-$ROOT/evidence/qemu-$(date +%Y%m%d-%H%M%S)}"

usage() {
  cat <<'EOF'
ISO-X QEMU helper (does not automatically mark GUI tests as passed)

Usage:
  tests/qemu-acceptance.sh check [ISO_PATH] [EVIDENCE_DIR]
  tests/qemu-acceptance.sh bios  [ISO_PATH] [EVIDENCE_DIR]
  tests/qemu-acceptance.sh uefi  [ISO_PATH] [EVIDENCE_DIR]
  tests/qemu-acceptance.sh install [ISO_PATH] [EVIDENCE_DIR]

Modes:
  check   Check ISO exists, SHA256, hybrid/El Torito metadata, and record output.
  bios    Boot the ISO with legacy BIOS, 2 vCPUs and 1024 MiB RAM.
  uefi    Boot with OVMF UEFI, 2 vCPUs and 1024 MiB RAM.
  install Boot with a fresh 24 GiB qcow2 TEST disk (never a host disk) attached.

BIOS/UEFI GUI checks are manual. Close QEMU to return. These modes do not
prove Wi-Fi, Bluetooth, Secure Boot, post-install boot, or performance by themselves.
EOF
}

need() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING tool: $1" >&2; exit 2; }; }
require_iso() { [[ -s "$ISO" ]] || { echo "ISO missing/empty: $ISO" >&2; exit 2; }; }

case "$MODE" in
  help|-h|--help) usage; exit 0 ;;
  check)
    need file; need sha256sum; need xorriso
    require_iso
    mkdir -p "$EVIDENCE"
    {
      echo "ISO-X release preflight"
      date --iso-8601=seconds
      printf 'Path: %s\n' "$(realpath "$ISO")"
      file "$ISO"
      sha256sum "$ISO"
      echo '--- El Torito metadata ---'
      xorriso -indev "$ISO" -report_el_torito plain
      echo '--- System area metadata ---'
      xorriso -indev "$ISO" -report_system_area plain
      echo '--- ISO directory listing (top entries) ---'
      xorriso -indev "$ISO" -ls /
    } 2>&1 | tee "$EVIDENCE/iso-preflight.txt"
    echo "Saved: $EVIDENCE/iso-preflight.txt"
    ;;
  bios|uefi|install)
    need qemu-system-x86_64; need qemu-img
    require_iso
    mkdir -p "$EVIDENCE"
    ARGS=(-m 1024 -smp 2 -boot order=d -cdrom "$ISO" -nic user,model=e1000 \
          -device usb-tablet -display gtk)
    if [[ "$MODE" == uefi ]]; then
      CODE=''
      VARS=''
      for candidate in /usr/share/OVMF/OVMF_CODE.fd /usr/share/ovmf/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE_4M.fd; do
        [[ -r "$candidate" ]] && { CODE="$candidate"; break; }
      done
      for candidate in /usr/share/OVMF/OVMF_VARS.fd /usr/share/ovmf/OVMF_VARS.fd /usr/share/OVMF/OVMF_VARS_4M.fd; do
        [[ -r "$candidate" ]] && { VARS="$candidate"; break; }
      done
      [[ -n "$CODE" && -n "$VARS" ]] || { echo "OVMF CODE/VARS templates not found; install Debian package ovmf." >&2; exit 3; }
      cp "$VARS" "$EVIDENCE/OVMF_VARS.fd"
      ARGS+=(-drive "if=pflash,format=raw,readonly=on,file=$CODE" -drive "if=pflash,format=raw,file=$EVIDENCE/OVMF_VARS.fd")
    fi
    if [[ "$MODE" == install ]]; then
      DISK="$EVIDENCE/install-test.qcow2"
      [[ ! -e "$DISK" ]] || { echo "Refusing to overwrite existing test disk: $DISK" >&2; exit 4; }
      qemu-img create -f qcow2 "$DISK" 24G | tee "$EVIDENCE/test-disk-create.txt"
      ARGS+=(-drive "file=$DISK,if=virtio,format=qcow2")
    fi
    {
      echo "Launching mode=$MODE; ISO=$ISO"
      echo 'Expected test target: QEMU, 2 vCPUs, 1024 MiB RAM.'
      echo 'Do not mark this test passed unless the screen confirms the expected result.'
      printf 'QEMU command: qemu-system-x86_64'
      printf ' %q' "${ARGS[@]}"
      printf '\n'
    } | tee "$EVIDENCE/qemu-launch-$MODE.txt"
    qemu-system-x86_64 "${ARGS[@]}" 2>&1 | tee "$EVIDENCE/qemu-$MODE.log"
    echo "QEMU exited. Record observed outcome and any screenshot manually under: $EVIDENCE"
    ;;
  *) usage >&2; exit 2 ;;
esac
