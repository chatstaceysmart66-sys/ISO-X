#!/usr/bin/env python3
"""Static regression checks; these do not imply successful ISO build or boot."""
from pathlib import Path
import ast
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
assert 'mkdir -p config/includes.chroot/etc/default' in build
assert build.index('mkdir -p config/includes.chroot/etc/default') < build.index('config/includes.chroot/etc/default/locale')
assert build.index('mkdir -p config/includes.chroot/etc/default') < build.index('config/includes.chroot/etc/default/keyboard')
assert 'ناتج إصدار سابق موجود' in build
assert build.index('if [[ "${EUID}" -ne 0 ]]') < build.index('ISOX_WATERMARK_OUTPUT=')
assert build.count('ISOX_WATERMARK_OUTPUT=') == 1
upstream_report = (ROOT / "docs/UPSTREAM_INTEGRATION_AR.md").read_text(encoding="utf-8")
assert "nodiscc/debian-live-config" in upstream_report and "OxyHQ/OxyOS" in upstream_report
assert 'THIRD_PARTY_LICENSES.md" config/includes.chroot/usr/share/doc/iso-x/THIRD_PARTY_LICENSES.md' in build
assert 'UPSTREAM_INTEGRATION_AR.md" config/includes.chroot/usr/share/doc/iso-x/UPSTREAM_INTEGRATION_AR.md' in build
assert 'ARCHITECTURE_AR.md" config/includes.chroot/usr/share/doc/iso-x/ARCHITECTURE_AR.md' in build
assert 'BUILD_AND_TEST_RESULTS_AR.md" config/includes.chroot/usr/share/doc/iso-x/BUILD_AND_TEST_RESULTS_AR.md' in build
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


def test_app_center_queries_and_package_operations_are_background_and_privileged():
    source = (ROOT / "app/isox_appcenter.py").read_text(encoding="utf-8")
    appcenter = source.split("class AppCenter(Gtk.Window):", 1)[1]
    populate = appcenter.split("    def _populate(self):", 1)[1].split("    def _refresh_states", 1)[0]
    assert "pkg_installed(" not in populate, "Package state must not block GTK population"
    assert "threading.Thread(target=work, daemon=True).start()" in appcenter
    assert "['pkexec', 'apt-get', *arguments]" in source
    assert "self._run_privileged(['update'])" in appcenter
    assert "'--no-install-recommends'" in appcenter and "app['pkg']" in appcenter
    assert "buttons=Gtk.ButtonsType.OK_CANCEL" in appcenter
    assert "subprocess.SubprocessError" in appcenter
    module = ast.parse(source)
    catalog_node = next(node for node in module.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "CATALOG" for target in node.targets))
    catalog = ast.literal_eval(catalog_node.value)
    package_names = [app["pkg"] for app in catalog]
    assert len(package_names) == len(set(package_names)), "App Center contains duplicate package entries"


def test_file_operations_are_confirmed_and_run_in_background():
    source = (ROOT / "app/iso_x_gtk.py").read_text(encoding="utf-8")
    assert '"نقل للجهة الأخرى", self.move_selected' in source
    assert '"حذف المحدد", self.delete_selected' in source
    assert '"نسخ ←", lambda: self.copy_selected("left")' in source
    assert '"نسخ →", lambda: self.copy_selected("right")' in source
    assert "def move_selected(" in source and "def delete_selected(" in source
    assert "threading.Thread(target=self._file_operation_worker" in source
    assert "buttons=Gtk.ButtonsType.YES_NO" in source
    assert source.count("set_default_response(Gtk.ResponseType.NO)") >= 3
    assert "لا يمكن نقل مجلد إلى داخله أو إلى أحد مجلداته الفرعية" in source
    assert "shutil.rmtree(source)" in source


def test_cinematic_is_optional_and_does_not_replace_the_welcome_ui():
    welcome = (ROOT / "app/isox_welcome.py").read_text(encoding="utf-8")
    scene = (ROOT / "three-d-login/src/main.rs").read_text(encoding="utf-8")
    build = (ROOT / "scripts/build-iso.sh").read_text(encoding="utf-8")
    assert "button_data.insert(1" in welcome and '"cinematic"' in welcome
    assert "_monitor_cinematic" in welcome
    assert 'ISOX_BUILD_CINEMATIC:-0' in build
    assert "لن تُبنى تبعيات Bevy بصلاحيات root" in build
    assert "العودة إلى لوحة الترحيب" in scene
    assert "المتابعة إلى الجلسة الآمنة" not in scene


def test_ibus_has_one_openbox_autostart_entry():
    build = (ROOT / "scripts/build-iso.sh").read_text(encoding="utf-8")
    assert build.count("ibus-daemon -drx") == 1
    assert "ibus-daemon.desktop" not in build


def test_legacy_tk_shell_is_not_staged_as_a_second_desktop():
    build = (ROOT / "scripts/build-iso.sh").read_text(encoding="utf-8")
    assert "iso_x_shell_0.1.py" not in build
    assert "iso_x_shell.py" not in build


def test_build_script_rejects_unprivileged_invocation_without_staging_files():
    if os.geteuid() == 0:
        return
    with tempfile.TemporaryDirectory(prefix="isox-build-guard-") as temporary:
        build_dir = Path(temporary) / "build"
        env = os.environ.copy()
        env["ISOX_BUILD_DIR"] = str(build_dir)
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/build-iso.sh")],
            env=env, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 2, result.stderr
        assert "صلاحيات root" in result.stderr
        assert not build_dir.exists(), "Rejected build must not create a staging directory"


def test_watermark_header_can_be_generated_without_mutating_the_source_tree():
    source_header = ROOT / "kernel/isox-watermark/watermark_bytes.h"
    original = source_header.read_bytes()
    with tempfile.TemporaryDirectory(prefix="isox-watermark-output-") as temporary:
        output = Path(temporary) / "staging/watermark_bytes.h"
        env = os.environ.copy()
        env["ISOX_WATERMARK_OUTPUT"] = str(output)
        subprocess.run([str(ROOT / "scripts/encode-watermark.py")], env=env, check=True,
                       capture_output=True, text=True)
        assert output.is_file()
        assert output.read_bytes() == original
    assert source_header.read_bytes() == original


def test_qemu_usb_tablet_has_an_explicit_controller():
    qemu_script = (ROOT / "tests/qemu-acceptance.sh").read_text(encoding="utf-8")
    assert "-device qemu-xhci,id=xhci" in qemu_script
    assert "-device usb-tablet,bus=xhci.0" in qemu_script


if __name__ == "__main__":
    test_browser_homepage_is_staged_and_configured()
    test_firefox_defaults_hook_applies_after_existing_packaged_prefs()
    test_app_center_queries_and_package_operations_are_background_and_privileged()
    test_file_operations_are_confirmed_and_run_in_background()
    test_cinematic_is_optional_and_does_not_replace_the_welcome_ui()
    test_ibus_has_one_openbox_autostart_entry()
    test_legacy_tk_shell_is_not_staged_as_a_second_desktop()
    test_build_script_rejects_unprivileged_invocation_without_staging_files()
    test_watermark_header_can_be_generated_without_mutating_the_source_tree()
    test_qemu_usb_tablet_has_an_explicit_controller()
