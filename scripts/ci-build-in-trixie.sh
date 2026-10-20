#!/usr/bin/env bash
set -Eeuo pipefail

cd "${GITHUB_WORKSPACE:-/workspace}"
mkdir -p evidence candidate
export LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONDONTWRITEBYTECODE=1
exec > >(tee -a evidence/ci-trixie.log) 2>&1

. /etc/os-release
test "${VERSION_CODENAME:-}" = trixie
test "$(dpkg --print-architecture)" = amd64
printf 'Container OS: %s %s\n' "$PRETTY_NAME" "$VERSION_CODENAME"
uname -a
apt-get update
./scripts/install-build-deps.sh

rootfs="$(mktemp -d)"
trap 'rm -rf "$rootfs"' EXIT
mkdir -p "$rootfs/usr/lib/systemd/system"
cp -a /usr/lib/systemd/system/*.target "$rootfs/usr/lib/systemd/system/"
for unit in isox-preload.service isox-preload.timer isox-zram.service isox-ci-ready.service isox-ci-ready.timer; do
  install -D -m 0644 "systemd/$unit" "$rootfs/etc/systemd/system/$unit"
done
install -D -m 0755 scripts/isox-preload.py "$rootfs/usr/local/bin/isox-preload"
install -D -m 0755 scripts/isox-zram-setup "$rootfs/usr/local/sbin/isox-zram-setup"
install -D -m 0755 scripts/isox-ci-ready.sh "$rootfs/usr/local/sbin/isox-ci-ready"
systemd-analyze verify --root="$rootfs" \
  isox-preload.service isox-preload.timer isox-zram.service \
  isox-ci-ready.service isox-ci-ready.timer

ISOX_BUILD_LOG=/workspace/evidence/isox-build.log ./build.sh
test -s "$ISOX_OUTPUT_ISO"
(
  cd "$(dirname -- "$ISOX_OUTPUT_ISO")"
  sha256sum --check "$(basename -- "$ISOX_OUTPUT_ISO").sha256"
)
xorriso -indev "$ISOX_OUTPUT_ISO" -report_el_torito plain 2>&1 | tee evidence/eltorito.txt
xorriso -indev "$ISOX_OUTPUT_ISO" -report_system_area plain 2>&1 | tee evidence/system-area.txt
xorriso -indev "$ISOX_OUTPUT_ISO" -pvd_info > evidence/iso-pvd-info.txt 2>&1
grep -Eiq 'BIOS|Platform.*0x00' evidence/eltorito.txt
grep -Eiq 'UEFI|EFI|Platform.*0xef' evidence/eltorito.txt
grep -Eiq 'MBR|System area' evidence/system-area.txt
printf 'ISO SHA256: '
sha256sum "$ISOX_OUTPUT_ISO"
stat -c 'ISO bytes: %s' "$ISOX_OUTPUT_ISO" | tee evidence/iso-size.txt
sha256sum "$ISOX_OUTPUT_ISO" | tee evidence/iso-sha256.txt
dpkg-query -W live-build qemu-system-x86 qemu-utils ovmf xorriso | tee evidence/build-tools.txt
printf 'kernel: '
uname -r | tee evidence/build-kernel.txt
printf 'nonce: %s\n' "$ISOX_CI_NONCE" > candidate/ci-nonce.txt
test ! -e "$ISOX_BUILD_DIR/chroot/var/lib/isox-build-secrets/isox-release.key"
