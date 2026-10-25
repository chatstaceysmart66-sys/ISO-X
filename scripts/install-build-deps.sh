#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=/etc/os-release
source /etc/os-release
if [[ "${ID:-}" != debian || "${VERSION_CODENAME:-}" != trixie ]]; then
  echo "يجب تشغيل هذا السكربت داخل Debian 13 Trixie؛ الموجود ${ID:-unknown}/${VERSION_CODENAME:-unknown}." >&2
  exit 2
fi
if [[ ${EUID} -eq 0 ]]; then
  SUDO=()
else
  command -v sudo >/dev/null 2>&1 || { echo "sudo غير مثبت؛ ثبّته أو شغّل السكربت كمستخدم root." >&2; exit 3; }
  SUDO=(sudo)
fi
"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y \
  live-build debootstrap squashfs-tools xorriso isolinux syslinux-common syslinux-efi \
  grub-pc-bin grub-efi-amd64-bin grub-efi-amd64-signed mtools dosfstools \
  qemu-system-x86 qemu-utils ovmf openssl fonts-noto-core build-essential pkg-config \
  python3-pytest desktop-file-utils libxml2-utils systemd file procps \
  clang lld cmake ninja-build libudev-dev libasound2-dev libx11-dev libx11-xcb-dev \
  libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev libxkbcommon-dev \
  libxkbcommon-x11-dev libxcursor-dev libxi-dev libxrandr-dev \
  libxinerama-dev libvulkan-dev git curl wget rsync python3 python3-venv shellcheck
for cmd in lb debootstrap mksquashfs xorriso qemu-system-x86_64 qemu-img openssl \
  shellcheck pytest desktop-file-validate xmllint systemd-analyze file grub-mkrescue free; do
  command -v "$cmd" >/dev/null || { echo "Missing required command after setup: $cmd" >&2; exit 4; }
done
python3 -c 'import pytest; print("python3 pytest module:", pytest.__version__)'
python3 -m pytest --version
dpkg-query -W -f='${Package}=${Version}\n' live-build debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin isolinux syslinux-efi qemu-system-x86 qemu-utils ovmf \
  python3-pytest desktop-file-utils shellcheck
printf '\nPASS: Debian Live Build and test dependencies were installed/verified. Bevy/Rust is optional and is not installed as root.\n'
