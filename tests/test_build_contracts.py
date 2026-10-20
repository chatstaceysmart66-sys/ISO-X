#!/usr/bin/env python3
"""Static regression checks; these do not imply successful ISO build or boot."""
from pathlib import Path
import re
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
auto = (ROOT / "auto/config").read_text(encoding="utf-8")
build = (ROOT / "scripts/build-iso.sh").read_text(encoding="utf-8")
packages_text = (ROOT / "config/package-lists/iso-x.list.chroot").read_text(encoding="utf-8")
packages = {line.strip() for line in packages_text.splitlines() if line.strip() and not line.lstrip().startswith("#")}
licenses = (ROOT / "docs/THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")

# BIOS-compatible SYSLINUX plus UEFI GRUB are explicit for deterministic output.
assert '--binary-images iso-hybrid' in auto
assert '--bootloaders "syslinux grub-efi"' in auto

# All source SQL migration files must be installed into the image at their matching paths.
migrations = sorted((ROOT / "db/migrations").glob("*.sql"))
assert migrations, "No database migrations found"
for migration in migrations:
    source_ref = f'"$PROJECT_DIR/db/migrations/{migration.name}"'
    destination_ref = f'config/includes.chroot/usr/share/iso-x/db/migrations/{migration.name}'
    assert source_ref in build and destination_ref in build, f"Build staging omits database migration: {migration.name}"
assert '004_isox_040.sql' in (ROOT / "app/iso_x_gtk.py").read_text(encoding="utf-8")

# The package set names exactly one top-level WM, login manager, network manager and audio stack.
for package in ("openbox", "lightdm", "network-manager", "pipewire-audio", "pipewire-pulse", "wireplumber"):
    assert package in packages, f"Expected desktop component missing: {package}"
for package in ("xfwm4", "lxde", "lxqt", "wicd", "connman", "pulseaudio"):
    assert package not in packages, f"Unexpected second core manager/audio server present: {package}"

assert "nodiscc/debian-live-config" in licenses and "GPL-3.0" in licenses
assert "OxyHQ/OxyOS" in licenses and "No OxyOS source files" in licenses
upstream_report = (ROOT / "docs/UPSTREAM_INTEGRATION_AR.md").read_text(encoding="utf-8")
assert "nodiscc/debian-live-config" in upstream_report and "OxyHQ/OxyOS" in upstream_report
assert 'THIRD_PARTY_LICENSES.md" config/includes.chroot/usr/share/doc/iso-x/THIRD_PARTY_LICENSES.md' in build
assert 'UPSTREAM_INTEGRATION_AR.md" config/includes.chroot/usr/share/doc/iso-x/UPSTREAM_INTEGRATION_AR.md' in build
assert 'README.md" config/includes.chroot/usr/share/doc/iso-x/README.md' in build

print("PASS: explicit BIOS+UEFI bootloader config, all SQL migrations staged, core package managers non-duplicated, and upstream license boundary documented.")


def test_browser_homepage_is_staged_and_configured():
    build_script = (ROOT / "scripts/build-iso.sh").read_text(encoding="utf-8")
    hook = (ROOT / "config/hooks/live/0400-isox-firefox-defaults.hook.chroot").read_text(encoding="utf-8")
    page = (ROOT / "assets/iso-x-start.html").read_text(encoding="utf-8")
    assert 'assets/iso-x-start.html" config/includes.chroot/usr/share/iso-x/start.html' in build_script
    assert '0400-isox-firefox-defaults.hook.chroot' in build_script
    assert 'pref("browser.startup.homepage", "%s");' in hook
    assert 'file:///usr/share/iso-x/start.html' in hook
    assert 'lang="ar" dir="rtl"' in page
    assert 'name="q"' in page and 'action="https://duckduckgo.com/"' in page


def test_firefox_defaults_hook_applies_after_existing_packaged_prefs():
    hook = ROOT / "config/hooks/live/0400-isox-firefox-defaults.hook.chroot"
    with tempfile.TemporaryDirectory(prefix="isox-firefox-hook-") as temporary:
        rootfs = Path(temporary)
        prefs_dir = rootfs / "etc/firefox-esr"
        page = rootfs / "usr/share/iso-x/start.html"
        prefs_dir.mkdir(parents=True)
        page.parent.mkdir(parents=True)
        (prefs_dir / "firefox-esr.js").write_text('pref("browser.startup.homepage", "about:blank");\n', encoding="utf-8")
        page.write_text('<html lang="ar" dir="rtl"></html>\n', encoding="utf-8")
        env = os.environ.copy()
        env["ISOX_HOOK_ROOT"] = str(rootfs)
        subprocess.run(["/bin/sh", str(hook)], env=env, check=True, capture_output=True, text=True)
        result = (prefs_dir / "firefox-esr.js").read_text(encoding="utf-8")
        assert result.rstrip().endswith('pref("browser.startup.page", 1);')
        assert result.count("ISO-X local start page") == 1
        assert 'pref("browser.startup.homepage", "file:///usr/share/iso-x/start.html");' in result
        subprocess.run(["/bin/sh", str(hook)], env=env, check=True, capture_output=True, text=True)
        result_again = (prefs_dir / "firefox-esr.js").read_text(encoding="utf-8")
        assert result_again == result, "Firefox defaults hook should be idempotent"
