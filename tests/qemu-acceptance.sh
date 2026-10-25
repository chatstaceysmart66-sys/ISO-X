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
  bios-headless Require the CI guest readiness nonce; capture VGA and serial evidence.
  uefi-headless Require the CI guest readiness nonce with OVMF; capture VGA and serial evidence.
  bios-desktop Boot a normal-boot ISO until the ISO-X window renders; capture VGA and serial evidence.
  uefi-desktop Boot a normal-boot ISO with OVMF until the ISO-X window renders.
  install Boot with a fresh 24 GiB qcow2 TEST disk (never a host disk) attached.

Boot modes default to 1024 MiB RAM and 2 vCPUs. Set ISOX_QEMU_MEMORY_MIB
and ISOX_QEMU_CPUS to run controlled resource profiles.

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
    [[ -r "${ISO}.sha256" ]] || { echo "SHA-256 sidecar missing: ${ISO}.sha256" >&2; exit 3; }
    EXPECTED="$(awk 'NR == 1 {print $1}' "${ISO}.sha256")"
    ACTUAL="$(sha256sum "$ISO" | awk '{print $1}')"
    [[ "${EXPECTED,,}" == "${ACTUAL,,}" ]] || { echo "SHA-256 mismatch for $ISO" >&2; exit 3; }
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
  bios|uefi|install|bios-headless|uefi-headless|bios-desktop|uefi-desktop)
    need qemu-system-x86_64
    if [[ "$MODE" == install ]]; then need qemu-img; fi
    require_iso
    mkdir -p "$EVIDENCE"
    QEMU_MEMORY_MIB="${ISOX_QEMU_MEMORY_MIB:-1024}"
    QEMU_CPUS="${ISOX_QEMU_CPUS:-2}"
    [[ "$QEMU_MEMORY_MIB" =~ ^[1-9][0-9]*$ ]] || {
      echo "ISOX_QEMU_MEMORY_MIB must be a positive integer." >&2
      exit 3
    }
    [[ "$QEMU_CPUS" =~ ^[1-9][0-9]*$ ]] || {
      echo "ISOX_QEMU_CPUS must be a positive integer." >&2
      exit 3
    }
    HEADLESS=0
    [[ "$MODE" == *-headless || "$MODE" == *-desktop ]] && HEADLESS=1
    # QEMU's -nic options intentionally use commas within a single argument.
    # shellcheck disable=SC2054
    ARGS=(-m "$QEMU_MEMORY_MIB" -smp "$QEMU_CPUS" -boot order=d -cdrom "$ISO" -nic user,model=e1000)
    if [[ "$HEADLESS" -eq 0 ]]; then
      ARGS+=(-device "qemu-xhci,id=xhci" -device "usb-tablet,bus=xhci.0")
    fi
    if [[ -r /dev/kvm && -w /dev/kvm ]]; then
      QEMU_ACCEL=kvm
      ARGS+=(-accel kvm)
    else
      QEMU_ACCEL='tcg,thread=multi'
      ARGS+=(-accel "$QEMU_ACCEL")
    fi
    if [[ "$HEADLESS" -eq 1 ]]; then
      QEMU_TIMEOUT="${ISOX_QEMU_TIMEOUT:-600}"
      [[ "$QEMU_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || { echo "ISOX_QEMU_TIMEOUT must be a positive integer." >&2; exit 3; }
      QEMU_RENDER_GRACE="${ISOX_QEMU_RENDER_GRACE:-3}"
      [[ "$QEMU_RENDER_GRACE" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "ISOX_QEMU_RENDER_GRACE must be a non-negative number of seconds." >&2; exit 3; }
      READINESS=nonce
      QEMU_NONCE="${ISOX_QEMU_NONCE:-}"
      if [[ "$MODE" == *-desktop ]]; then
        READINESS=desktop
      else
        [[ "$QEMU_NONCE" =~ ^[a-f0-9]{32}$ ]] || { echo "Set ISOX_QEMU_NONCE to the nonce embedded in the CI-only ISO variant." >&2; exit 3; }
      fi
    elif [[ "$HEADLESS" -eq 0 ]]; then
      ARGS+=(-display gtk)
    fi
    if [[ "$MODE" == uefi || "$MODE" == uefi-headless || "$MODE" == uefi-desktop ]]; then
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
      echo "Expected test target: QEMU, $QEMU_CPUS vCPUs, $QEMU_MEMORY_MIB MiB RAM; accelerator=$QEMU_ACCEL."
      qemu-system-x86_64 -version
      if command -v dpkg-query >/dev/null 2>&1; then
        dpkg-query -W qemu-system-x86 ovmf 2>&1 || true
      fi
      if [[ -r /dev/kvm && -w /dev/kvm ]]; then echo 'KVM: readable+writable'; else echo 'KVM: unavailable; using TCG'; fi
      printf 'QEMU command: qemu-system-x86_64'
      printf ' %q' "${ARGS[@]}"
      printf '\n'
    } | tee "$EVIDENCE/qemu-launch-$MODE.txt"
    if [[ "$HEADLESS" -eq 1 ]]; then
      python3 "$ROOT/tests/qemu-runner.py" \
        --mode "$MODE" \
        --readiness "$READINESS" \
        --evidence "$EVIDENCE" \
        --nonce "$QEMU_NONCE" \
        --timeout "$QEMU_TIMEOUT" \
        --render-grace "$QEMU_RENDER_GRACE" \
        --accelerator "$QEMU_ACCEL" \
        -- qemu-system-x86_64 "${ARGS[@]}"
      exit $?
    fi
    qemu-system-x86_64 "${ARGS[@]}" 2>&1 | tee "$EVIDENCE/qemu-$MODE.log"
    echo "QEMU exited. Record observed outcome and any screenshot manually under: $EVIDENCE"
    ;;
  *) usage >&2; exit 2 ;;
esac
