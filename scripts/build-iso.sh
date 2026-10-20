#!/usr/bin/env bash
set -Eeuo pipefail

# ISO-X 0.4.0 Debian Trixie Live build.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ISOX_BUILD_DIR:-${PROJECT_DIR}/build-live}"
DIST="trixie"
KEY_IN="${ISOX_RELEASE_KEY:-}"
WATERMARK_ENABLED="${ISOX_ENABLE_WATERMARK:-0}"
STAGED_KEY="${BUILD_DIR}/config/includes.chroot/var/lib/isox-build-secrets/isox-release.key"
STAGED_CERT="${BUILD_DIR}/config/includes.chroot/var/lib/isox-build-secrets/isox-release.crt"
CLEAN_STAGED=0

cleanup() {
  # Only remove staged secrets if this invocation created/staged them. In
  # particular, an existing build directory is never modified by the error path.
  if [[ "$CLEAN_STAGED" -eq 1 ]]; then
    rm -f "$STAGED_KEY" "$STAGED_CERT"
    # A failed live-build can leave copied secrets in its working chroot. Remove
    # only the two known build-only files; never wipe the build directory.
    rm -f "$BUILD_DIR/chroot/var/lib/isox-build-secrets/isox-release.key" \
          "$BUILD_DIR/chroot/var/lib/isox-build-secrets/isox-release.crt"
    rmdir "$(dirname "$STAGED_KEY")" 2>/dev/null || true
    rmdir "$BUILD_DIR/chroot/var/lib/isox-build-secrets" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ "${EUID}" -ne 0 ]]; then
  echo "شغّل البناء على Linux بصلاحيات root: sudo $0" >&2; exit 2
fi
# When invoked through sudo, retain the caller's rustup-managed stable toolchain.
BUILD_USER="${SUDO_USER:-root}"
BUILD_USER_HOME="$(getent passwd "$BUILD_USER" | cut -d: -f6 || true)"
if [[ -n "$BUILD_USER_HOME" && "$BUILD_USER" != root && -x "$BUILD_USER_HOME/.cargo/bin/cargo" ]]; then
  export PATH="$BUILD_USER_HOME/.cargo/bin:$PATH"
  export CARGO_HOME="$BUILD_USER_HOME/.cargo"
  export RUSTUP_HOME="$BUILD_USER_HOME/.rustup"
fi
OS_ID="$(. /etc/os-release; printf '%s' "${ID:-unknown}")"
OS_CODENAME="$(. /etc/os-release; printf '%s' "${VERSION_CODENAME:-unknown}")"
if [[ "$OS_ID" != debian || "$OS_CODENAME" != trixie ]]; then
  if [[ "${ISOX_ALLOW_FOREIGN_BUILD_HOST:-0}" == 1 && ( "$OS_ID" == ubuntu || "$OS_ID" == debian ) ]]; then
    echo "تحذير: مضيف البناء ${OS_ID}/${OS_CODENAME} غير Trixie؛ صورة الهدف تبقى Debian Trixie، لكن القبول النهائي يتطلب اختبارًا مستقلًا." >&2
  else
    echo "مضيف البناء المطلوب Debian 13 Trixie؛ الموجود: ${OS_ID}/${OS_CODENAME}. لبناء محلي، استخدم Debian 13 Trixie؛ السماح بمضيف آخر مخصص لبناء CI فقط." >&2; exit 2
  fi
fi
[[ "$(dpkg --print-architecture)" == amd64 ]] || { echo "يتطلب البناء معمارية amd64." >&2; exit 2; }
[[ "$WATERMARK_ENABLED" == 0 || "$WATERMARK_ENABLED" == 1 ]] || { echo "ISOX_ENABLE_WATERMARK يقبل 0 أو 1 فقط." >&2; exit 2; }
FREE_KB="$(df -Pk "$PROJECT_DIR" | awk 'NR==2 {print $4}')"
MEM_KB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
(( FREE_KB >= 20*1024*1024 )) || { echo "تحتاج مساحة فارغة لا تقل عن 20 GiB؛ المتاح: $((FREE_KB/1024/1024)) GiB." >&2; exit 2; }
(( MEM_KB >= 4*1024*1024 )) || { echo "تحتاج ذاكرة RAM لا تقل عن 4 GiB؛ المتاح: $((MEM_KB/1024/1024)) MiB." >&2; exit 2; }
for cmd in lb xorriso debootstrap mksquashfs openssl; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "المتطلب غير موجود: $cmd" >&2; exit 3; }
done
if [[ "$WATERMARK_ENABLED" == 1 ]]; then
  for cmd in make openssl; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "المتطلب الاختياري غير موجود: $cmd" >&2; exit 3; }
  done
  if [[ -z "$KEY_IN" || -z "$CERT_IN" || ! -r "$KEY_IN" || ! -r "$CERT_IN" ]]; then
    echo "عند تفعيل watermark، مرّر ISOX_RELEASE_KEY وISOX_RELEASE_CERT من خارج المستودع." >&2
    exit 5
  fi
else
  echo "وحدة watermark معطّلة افتراضيًا ولا تشارك في الإقلاع الأساسي."
fi
if [[ -e "${BUILD_DIR}/config" || ( -d "$BUILD_DIR" && -n "$(find "$BUILD_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ) ]]; then
  echo "مجلد بناء غير فارغ: ${BUILD_DIR}; لن أحذفه أو أعيد استخدامه تلقائيًا. انقله/احذفه يدويًا بعد التأكد من محتوياته." >&2; exit 7
fi
for artifact in "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso" "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso.sha256"; do
  if [[ -e "$artifact" ]]; then
    echo "ناتج إصدار سابق موجود: $artifact؛ انقله يدوياً قبل بدء بناء جديد كي لا يلتبس مع ناتج هذه المحاولة." >&2
    exit 7
  fi
done

# Never place private material under the source tree permanently.
# Generate the source header as the project owner (not root where invoked via sudo).
CINEMATIC_BIN="$PROJECT_DIR/three-d-login/target/release/isox-cinematic"
CINEMATIC_READY=0
if [[ "${ISOX_BUILD_CINEMATIC:-0}" == 1 ]]; then
  if command -v cargo >/dev/null 2>&1 && command -v rustc >/dev/null 2>&1; then
    if [[ "$BUILD_USER" != root && -n "$BUILD_USER_HOME" ]]; then
      if sudo -u "$BUILD_USER" env HOME="$BUILD_USER_HOME" \
        CARGO_HOME="$BUILD_USER_HOME/.cargo" RUSTUP_HOME="$BUILD_USER_HOME/.rustup" \
        PATH="$BUILD_USER_HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin" \
        cargo build --release --manifest-path "$PROJECT_DIR/three-d-login/Cargo.toml"; then
        CINEMATIC_READY=1
      fi
    else
      echo "تحذير: لن تُبنى تبعيات Bevy بصلاحيات root؛ استخدم sudo من حساب عادي أو عطّل المشهد." >&2
    fi
    if [[ "$CINEMATIC_READY" -ne 1 ]]; then
      echo "تحذير: تعذر بناء مشهد Bevy الاختياري؛ سيستمر بناء سطح المكتب بدونه." >&2
    fi
  else
    echo "تحذير: ISOX_BUILD_CINEMATIC=1 لكن Rust/Cargo غير متوفرين؛ سيُبنى النظام من دونه." >&2
  fi
else
  echo "مشهد Bevy معطّل افتراضيًا؛ استخدم ISOX_BUILD_CINEMATIC=1 لبنائه اختياريًا."
fi

mkdir -p "$BUILD_DIR"
BUILD_LOG="${ISOX_BUILD_LOG:-${BUILD_DIR}/isox-build.log}"
mkdir -p "$(dirname -- "$BUILD_LOG")"
exec > >(tee -a "$BUILD_LOG") 2>&1
cd "$BUILD_DIR"
printf 'ISO-X build started: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'Host: %s/%s %s\n' "$OS_ID" "$OS_CODENAME" "$(dpkg --print-architecture)"
uname -a
for cmd in lb xorriso debootstrap mksquashfs openssl; do
  printf '%s: ' "$cmd"
  "$cmd" --version 2>&1 | sed -n '1p' || true
done
dpkg-query -W -f='${Package}=${Version}\n' live-build debootstrap squashfs-tools xorriso openssl
df -h "$PROJECT_DIR"
"$PROJECT_DIR/auto/config"

mkdir -p config/package-lists \
  config/includes.chroot/usr/share/iso-x/assets \
  config/includes.chroot/usr/share/doc/iso-x \
  config/includes.chroot/usr/share/backgrounds/iso-x \
  config/includes.chroot/usr/share/icons/hicolor/scalable/apps \
  config/includes.chroot/usr/local/bin \
  config/includes.chroot/usr/local/sbin \
  config/includes.chroot/usr/share/applications \
  config/includes.chroot/usr/lib/systemd/user \
  config/includes.chroot/usr/share/iso-x/db/migrations \
  config/includes.chroot/etc/systemd/system/multi-user.target.wants \
  config/includes.chroot/etc/skel/.config/openbox \
  config/includes.chroot/etc/skel/.config/tint2 \
  config/includes.chroot/etc/skel/.config/systemd/user/timers.target.wants \
  "config/includes.chroot/etc/skel/سطح المكتب" \
  config/includes.chroot/etc/xdg/openbox \
  config/hooks/live \
  config/includes.chroot/etc/NetworkManager

install -m 0644 "$PROJECT_DIR/config/package-lists/iso-x.list.chroot" config/package-lists/iso-x.list.chroot
if [[ "$WATERMARK_ENABLED" == 1 ]]; then
  mkdir -p config/includes.chroot/usr/src/isox-watermark-0.3.1 \
    config/includes.chroot/etc/initramfs-tools/hooks \
    config/includes.chroot/etc/initramfs-tools/scripts/init-premount \
    config/includes.chroot/var/lib/isox-build-secrets
  printf '%s\n' build-essential linux-headers-amd64 >> config/package-lists/iso-x.list.chroot
  ISOX_WATERMARK_OUTPUT="$BUILD_DIR/config/includes.chroot/usr/src/isox-watermark-0.3.1/watermark_bytes.h" \
    "$PROJECT_DIR/scripts/encode-watermark.py"
  CLEAN_STAGED=1
  install -m 0600 "$KEY_IN" "$STAGED_KEY"
  install -m 0644 "$CERT_IN" "$STAGED_CERT"
fi


install -m 0644 "$PROJECT_DIR/app/iso_x_gtk.py" config/includes.chroot/usr/share/iso-x/iso_x_gtk.py
install -m 0644 "$PROJECT_DIR/app/isox_appcenter.py" config/includes.chroot/usr/share/iso-x/isox_appcenter.py
install -m 0644 "$PROJECT_DIR/app/isox_welcome.py" config/includes.chroot/usr/share/iso-x/isox_welcome.py
install -m 0644 "$PROJECT_DIR/assets/iso-x-start.html" config/includes.chroot/usr/share/iso-x/start.html
install -m 0644 "$PROJECT_DIR/README.md" config/includes.chroot/usr/share/doc/iso-x/README.md
install -m 0644 "$PROJECT_DIR/README_AR.md" config/includes.chroot/usr/share/doc/iso-x/README_AR.md
install -m 0644 "$PROJECT_DIR/THIRD_PARTY_NOTICES.md" config/includes.chroot/usr/share/doc/iso-x/THIRD_PARTY_NOTICES.md
install -m 0644 "$PROJECT_DIR/docs/THIRD_PARTY_LICENSES.md" config/includes.chroot/usr/share/doc/iso-x/THIRD_PARTY_LICENSES.md
install -m 0644 "$PROJECT_DIR/docs/UPSTREAM_INTEGRATION_AR.md" config/includes.chroot/usr/share/doc/iso-x/UPSTREAM_INTEGRATION_AR.md
install -m 0644 "$PROJECT_DIR/docs/ARCHITECTURE_AR.md" config/includes.chroot/usr/share/doc/iso-x/ARCHITECTURE_AR.md
install -m 0644 "$PROJECT_DIR/docs/BUILD_AND_TEST_RESULTS_AR.md" config/includes.chroot/usr/share/doc/iso-x/BUILD_AND_TEST_RESULTS_AR.md
install -m 0644 "$PROJECT_DIR/docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md" config/includes.chroot/usr/share/doc/iso-x/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md
install -m 0644 "$PROJECT_DIR/docs/UPSTREAM_REVIEW_AR.md" config/includes.chroot/usr/share/doc/iso-x/UPSTREAM_REVIEW_AR.md
install -m 0755 "$PROJECT_DIR/scripts/isox-speedtest" config/includes.chroot/usr/local/bin/isox-speedtest
install -m 0755 "$PROJECT_DIR/scripts/write-usb.sh" config/includes.chroot/usr/local/sbin/isox-write-usb
install -m 0644 "$PROJECT_DIR/db/schema.sql" config/includes.chroot/usr/share/iso-x/db/schema.sql
install -m 0644 "$PROJECT_DIR/db/migrations/002_isox_020.sql" config/includes.chroot/usr/share/iso-x/db/migrations/002_isox_020.sql
install -m 0644 "$PROJECT_DIR/db/migrations/003_isox_031.sql" config/includes.chroot/usr/share/iso-x/db/migrations/003_isox_031.sql
install -m 0644 "$PROJECT_DIR/db/migrations/004_isox_040.sql" config/includes.chroot/usr/share/iso-x/db/migrations/004_isox_040.sql
install -m 0644 "$PROJECT_DIR/assets/iso-x-dragon.svg" config/includes.chroot/usr/share/iso-x/assets/iso-x-dragon.svg
install -m 0644 "$PROJECT_DIR/assets/iso-x-dragon.png" config/includes.chroot/usr/share/iso-x/assets/iso-x-dragon.png
install -m 0644 "$PROJECT_DIR/assets/iso-x-boot.svg" config/includes.chroot/usr/share/iso-x/assets/iso-x-boot.svg
install -m 0644 "$PROJECT_DIR/assets/iso-x-boot.png" config/includes.chroot/usr/share/iso-x/assets/iso-x-boot.png
install -m 0644 "$PROJECT_DIR/plymouth/isox/isox.plymouth" config/includes.chroot/usr/share/iso-x/assets/isox.plymouth
install -m 0644 "$PROJECT_DIR/plymouth/isox/isox.script" config/includes.chroot/usr/share/iso-x/assets/isox.script
install -m 0644 "$PROJECT_DIR/assets/iso-x-desktop-wallpaper.svg" config/includes.chroot/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.svg
install -m 0644 "$PROJECT_DIR/assets/iso-x-desktop-wallpaper.png" config/includes.chroot/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.png
install -m 0644 "$PROJECT_DIR/assets/iso-x-dragon.svg" config/includes.chroot/usr/share/icons/hicolor/scalable/apps/iso-x.svg
if [[ "$CINEMATIC_READY" -eq 1 && -x "$CINEMATIC_BIN" ]]; then
  FONT_SOURCE="$(find /usr/share/fonts -type f \( -iname 'NotoSansArabic-Regular.ttf' -o -iname 'NotoSansArabic-VF.ttf' \) -print -quit 2>/dev/null || true)"
  if [[ -n "$FONT_SOURCE" ]]; then
    install -m 0755 "$CINEMATIC_BIN" config/includes.chroot/usr/local/bin/isox-cinematic
    install -D -m 0644 "$FONT_SOURCE" config/includes.chroot/usr/share/iso-x/cinematic-assets/fonts/NotoSansArabic-Regular.ttf
    install -D -m 0644 "$PROJECT_DIR/assets/iso-x-dragon.png" config/includes.chroot/usr/share/iso-x/cinematic-assets/images/iso-x-dragon.png
  else
    echo "تحذير: لا يوجد خط مشهد Bevy على المضيف؛ سيُستبعد المشهد من الصورة." >&2
  fi
fi
install -m 0644 "$PROJECT_DIR/assets/iso-x-plymouth.png" config/includes.chroot/usr/share/iso-x/assets/iso-x-plymouth.png
if [[ "$WATERMARK_ENABLED" == 1 ]]; then
  install -m 0644 "$PROJECT_DIR/kernel/isox-watermark/isox_watermark.c" config/includes.chroot/usr/src/isox-watermark-0.3.1/isox_watermark.c
  install -m 0644 "$PROJECT_DIR/kernel/isox-watermark/Makefile" config/includes.chroot/usr/src/isox-watermark-0.3.1/Makefile
  install -m 0644 "$PROJECT_DIR/initramfs/hooks/isox-watermark" config/includes.chroot/etc/initramfs-tools/hooks/isox-watermark
  install -m 0755 "$PROJECT_DIR/initramfs/scripts/init-premount/isox-watermark-guard" config/includes.chroot/etc/initramfs-tools/scripts/init-premount/isox-watermark-guard
fi
install -m 0755 "$PROJECT_DIR/scripts/isox-zram-setup" config/includes.chroot/usr/local/sbin/isox-zram-setup
install -m 0755 "$PROJECT_DIR/scripts/isox-preload.py" config/includes.chroot/usr/local/bin/isox-preload
install -m 0644 "$PROJECT_DIR/systemd/isox-zram.service" config/includes.chroot/etc/systemd/system/isox-zram.service
ln -sfn ../isox-zram.service config/includes.chroot/etc/systemd/system/multi-user.target.wants/isox-zram.service
install -m 0644 "$PROJECT_DIR/systemd/isox-preload.service" config/includes.chroot/usr/lib/systemd/user/isox-preload.service
install -m 0644 "$PROJECT_DIR/systemd/isox-preload.timer" config/includes.chroot/usr/lib/systemd/user/isox-preload.timer
# The timer runs only for a user's own session, but the program is a no-op unless
# the user enables preload in ISO-X settings; no telemetry or application launches.
ln -sfn /usr/lib/systemd/user/isox-preload.timer config/includes.chroot/etc/skel/.config/systemd/user/timers.target.wants/isox-preload.timer
install -m 0755 "$PROJECT_DIR/config/hooks/live/0050-isox-locales.hook.chroot" config/hooks/live/0050-isox-locales.hook.chroot
if [[ "$WATERMARK_ENABLED" == 1 ]]; then
  install -m 0755 "$PROJECT_DIR/config/hooks/live/0100-isox-watermark.hook.chroot" config/hooks/live/0100-isox-watermark.hook.chroot
fi
install -m 0755 "$PROJECT_DIR/config/hooks/live/0200-isox-plymouth.hook.chroot" config/hooks/live/0200-isox-plymouth.hook.chroot
install -m 0755 "$PROJECT_DIR/config/hooks/live/0300-isox-services.hook.chroot" config/hooks/live/0300-isox-services.hook.chroot
install -m 0755 "$PROJECT_DIR/config/hooks/live/0400-isox-firefox-defaults.hook.chroot" config/hooks/live/0400-isox-firefox-defaults.hook.chroot
install -m 0644 "$PROJECT_DIR/desktop/tint2rc" config/includes.chroot/etc/skel/.config/tint2/tint2rc
install -m 0644 "$PROJECT_DIR/desktop/openbox-menu.xml" config/includes.chroot/etc/skel/.config/openbox/menu.xml
install -m 0644 "$PROJECT_DIR/desktop/openbox-menu.xml" config/includes.chroot/etc/xdg/openbox/menu.xml
install -m 0644 "$PROJECT_DIR/desktop/openbox-rc.xml" config/includes.chroot/etc/xdg/openbox/rc.xml
install -m 0644 "$PROJECT_DIR/desktop/openbox-rc.xml" config/includes.chroot/etc/skel/.config/openbox/rc.xml
install -m 0755 "$PROJECT_DIR/scripts/isox-run.py" config/includes.chroot/usr/local/bin/isox-run
cat > config/includes.chroot/usr/local/bin/isox-welcome <<'WELCOME_LAUNCH'
#!/bin/sh
exec /usr/bin/python3 /usr/share/iso-x/isox_welcome.py "$@"
WELCOME_LAUNCH
chmod 0755 config/includes.chroot/usr/local/bin/isox-welcome
install -m 0755 "$PROJECT_DIR/scripts/isox-snap-window.sh" config/includes.chroot/usr/local/bin/isox-snap-window
install -m 0755 "$PROJECT_DIR/scripts/toggle-airplane.sh" config/includes.chroot/usr/local/bin/isox-toggle-airplane
install -m 0755 "$PROJECT_DIR/scripts/apply-windows-look.sh" config/includes.chroot/usr/local/sbin/apply-windows-look
install -m 0755 "$PROJECT_DIR/scripts/secure-vault.sh" config/includes.chroot/usr/local/bin/isox-vault
install -m 0644 "$PROJECT_DIR/scripts/secure-vault.py" config/includes.chroot/usr/share/iso-x/secure-vault.py

install -D -m 0644 "$PROJECT_DIR/desktop/tint2rc" config/includes.chroot/etc/iso-x/tint2rc
install -D -m 0644 "$PROJECT_DIR/desktop/openbox-menu.xml" config/includes.chroot/etc/iso-x/openbox-menu.xml

# Seed GTK/PCManFM dark theme, Arabic special folders, wallpaper, and the user desktop profile.
ISOX_TARGET_HOME="$BUILD_DIR/config/includes.chroot/etc/skel" "$PROJECT_DIR/scripts/apply-windows-look.sh"
# Arabic-first locale and Baghdad time; keep English available for mixed-language workflows.
mkdir -p config/includes.chroot/etc/default
cat > config/includes.chroot/etc/locale.gen <<'LOCALES'
ar_IQ.UTF-8 UTF-8
ar_SA.UTF-8 UTF-8
en_US.UTF-8 UTF-8
LOCALES
cat > config/includes.chroot/etc/default/locale <<'LOCALE'
LANG=ar_IQ.UTF-8
LANGUAGE=ar_IQ:ar:en_US:en
LOCALE
ln -sfn /usr/share/zoneinfo/Asia/Baghdad config/includes.chroot/etc/localtime
printf '%s\n' 'Asia/Baghdad' > config/includes.chroot/etc/timezone
cat > config/includes.chroot/etc/default/keyboard <<'KEYBOARD'
XKBMODEL="pc105"
XKBLAYOUT="us,ara"
XKBVARIANT=","
XKBOPTIONS="grp:alt_shift_toggle"
BACKSPACE="guess"
KEYBOARD
cat > config/includes.chroot/etc/environment <<'ENVIRONMENT'
GTK_IM_MODULE=ibus
QT_IM_MODULE=ibus
XMODIFIERS=@im=ibus
ENVIRONMENT
cat > config/includes.chroot/usr/local/bin/iso-x <<'LAUNCH'
#!/bin/sh
exec /usr/bin/python3 /usr/share/iso-x/iso_x_gtk.py "$@"
LAUNCH
chmod 0755 config/includes.chroot/usr/local/bin/iso-x
install -m 0644 "$PROJECT_DIR/desktop/isox-welcome.desktop" config/includes.chroot/usr/share/applications/isox-welcome.desktop
cat > config/includes.chroot/usr/share/applications/iso-x.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=ISO-X Desktop
Comment=Lightweight GTK3 desktop shell
Exec=/usr/local/bin/iso-x
Icon=iso-x
Terminal=false
Categories=System;Utility;
DESKTOP
cat > config/includes.chroot/usr/share/applications/isox-installer.desktop <<'INSTALLER_DESKTOP'
[Desktop Entry]
Type=Application
Name=Install ISO-X to Disk
Name[ar]=تثبيت ISO-X على القرص
Comment=Install the running ISO-X live system to this computer
Comment[ar]=تثبيت نظام ISO-X الحي على هذا الحاسوب
Exec=debian-installer-launcher
Icon=system-software-install
Terminal=false
Categories=System;
INSTALLER_DESKTOP
cat > config/includes.chroot/usr/share/applications/isox-run.desktop <<'RUN_DESKTOP'
[Desktop Entry]
Type=Application
Name=Run Command
Name[ar]=تشغيل أمر
Exec=/usr/local/bin/isox-run
Icon=system-run
Terminal=false
Categories=Utility;
RUN_DESKTOP
cat > config/includes.chroot/usr/share/applications/isox-airplane.desktop <<'AIRPLANE_DESKTOP'
[Desktop Entry]
Type=Application
Name=Toggle Airplane Mode
Name[ar]=تبديل وضع الطيران
Comment=Block or unblock radio devices using rfkill
Comment[ar]=حظر أو رفع حظر الأجهزة اللاسلكية بواسطة rfkill
Exec=/usr/local/bin/isox-toggle-airplane
Icon=network-wireless-offline
Terminal=false
Categories=System;Network;
AIRPLANE_DESKTOP
# Icons use the localized XDG desktop directory configured in /etc/skel/.config/user-dirs.dirs.
install -m 0644 "$PROJECT_DIR/desktop/isox-welcome.desktop" "config/includes.chroot/etc/skel/سطح المكتب/مرحباً بك في ISO-X.desktop"
cat > "config/includes.chroot/etc/skel/سطح المكتب/ISO-X.desktop" <<'ICON_ISOX'
[Desktop Entry]
Type=Application
Name=ISO-X Start
Name[ar]=ابدأ ISO-X
Exec=/usr/local/bin/iso-x
Icon=iso-x
Terminal=false
Categories=System;Utility;
ICON_ISOX
cat > "config/includes.chroot/etc/skel/سطح المكتب/This-PC.desktop" <<'ICON_PC'
[Desktop Entry]
Type=Application
Name=This PC
Name[ar]=هذا الكمبيوتر
Exec=thunar computer:///
Icon=computer
Terminal=false
Categories=System;FileManager;
ICON_PC
cat > "config/includes.chroot/etc/skel/سطح المكتب/Home.desktop" <<'ICON_HOME'
[Desktop Entry]
Type=Application
Name=Home Folder
Name[ar]=المجلد الشخصي
Exec=thunar %U
Icon=user-home
Terminal=false
Categories=System;FileManager;
ICON_HOME
cat > "config/includes.chroot/etc/skel/سطح المكتب/Trash.desktop" <<'ICON_TRASH'
[Desktop Entry]
Type=Link
Name=Trash
Name[ar]=سلة المحذوفات
URL=trash:///
Icon=user-trash
ICON_TRASH
cat > "config/includes.chroot/etc/skel/سطح المكتب/Network.desktop" <<'ICON_NETWORK'
[Desktop Entry]
Type=Application
Name=Network Connections
Name[ar]=اتصالات الشبكة
Exec=nm-connection-editor
Icon=network-workgroup
Terminal=false
Categories=System;Network;
ICON_NETWORK
for item in "مرحباً بك في ISO-X.desktop" ISO-X.desktop This-PC.desktop Home.desktop Trash.desktop Network.desktop; do
  chmod 0755 "config/includes.chroot/etc/skel/سطح المكتب/$item"
done
cat > config/includes.chroot/etc/skel/.config/openbox/autostart <<'AUTOSTART'
#!/bin/sh
# Start user-session facilities only after LightDM's actual login.
# PCManFM draws the wallpaper and the real desktop icons in the localized XDG desktop folder.
if command -v pcmanfm >/dev/null 2>&1; then
  pcmanfm --desktop --profile=isox >/tmp/isox-pcmanfm-desktop.log 2>&1 &
fi
if command -v tint2 >/dev/null 2>&1; then
  tint2 -c /etc/iso-x/tint2rc >/tmp/isox-tint2.log 2>&1 &
fi
if command -v nm-applet >/dev/null 2>&1; then
  nm-applet --indicator >/tmp/isox-nm-applet.log 2>&1 &
fi
if command -v blueman-applet >/dev/null 2>&1; then
  blueman-applet >/tmp/isox-blueman.log 2>&1 &
fi
if command -v volumeicon >/dev/null 2>&1; then
  volumeicon >/tmp/isox-volume.log 2>&1 &
fi
if command -v xfce4-power-manager >/dev/null 2>&1; then
  xfce4-power-manager >/tmp/isox-power.log 2>&1 &
fi
if command -v lxpolkit >/dev/null 2>&1; then
  lxpolkit >/tmp/isox-polkit.log 2>&1 &
fi
if command -v ibus-daemon >/dev/null 2>&1; then
  ibus-daemon -drx >/tmp/isox-ibus.log 2>&1 &
fi
exec /usr/local/bin/iso-x
AUTOSTART
chmod 0755 config/includes.chroot/etc/skel/.config/openbox/autostart

# Build, verify output exists, then create release hash.
echo "Build log: ${BUILD_LOG}"
lb build
ISO_PATH="${BUILD_DIR}/live-image-amd64.hybrid.iso"
[[ -s "$ISO_PATH" ]] || { echo "لم ينتج live-build ملف ISO متوقعًا؛ افحص سجل البناء." >&2; exit 9; }
xorriso -indev "$ISO_PATH" -pvd_info >/dev/null || { echo "فشل فحص بنية ISO الناتجة؛ لن تُنشر الصورة." >&2; exit 10; }
cp -f "$ISO_PATH" "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso"
sha256sum "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso" > "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso.sha256"
sha256sum --check "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso.sha256" >/dev/null || { echo "فشل تحقق SHA-256 للصورة الناتجة." >&2; exit 11; }
echo "ISO generated: $PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso"
echo "SHA256: $(cut -d' ' -f1 "$PROJECT_DIR/ISO-X-0.4.0-live-amd64.iso.sha256")"
echo "NOTE: boot-performance and GUI acceptance testing remain a separate required step."
