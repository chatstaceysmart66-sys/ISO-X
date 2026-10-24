#!/usr/bin/env python3
"""Static source checks. These do not claim to test a booted ISO or real hardware."""
from pathlib import Path
import tomllib
import xml.etree.ElementTree as ET
import configparser
import shlex

ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "three-d-login/Cargo.toml").open("rb") as stream:
    cargo = tomllib.load(stream)
assert cargo["package"]["version"] == "0.4.0"
assert cargo["dependencies"]["bevy"]["version"] == "0.19.1"
features = set(cargo["dependencies"]["bevy"]["features"])
assert {"3d", "2d_bevy_render", "x11"} <= features

build = (ROOT / "scripts/build-iso.sh").read_text(encoding="utf-8")
auto_config = (ROOT / "auto/config").read_text(encoding="utf-8")
packages_text = (ROOT / "config/package-lists/iso-x.list.chroot").read_text(encoding="utf-8")
packages = {line.strip() for line in packages_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")}
for required in (
    '"$PROJECT_DIR/auto/config"', 'scripts/encode-watermark.py',
    'scripts/isox-run.py', 'scripts/isox-snap-window.sh', 'scripts/secure-vault.py',
    'scripts/toggle-airplane.sh', 'scripts/apply-windows-look.sh',
    'ISO-X-0.4.0-live-amd64.iso', 'tee -a "$BUILD_LOG"',
    '004_isox_040.sql', 'docs/THIRD_PARTY_LICENSES.md',
    'isox-watermark-0.3.1', 'debian-installer-launcher',
):
    assert required in build, f"Missing build integration: {required}"
for required in ('--distribution trixie', '--architectures amd64', '--binary-images iso-hybrid',
                 '--debian-installer live', '--debian-installer-gui true',
                 '--bootloaders "syslinux grub-efi"',
                 'username=user hostname=iso-x', '--memtest none'):
    assert required in auto_config, f"Missing live-build configuration: {required}"
assert '--linux-packages "linux-image"' in auto_config
assert 'linux-headers-amd64' not in auto_config, "Kernel headers should be optional with the watermark module"
services_hook = (ROOT / "config/hooks/live/0300-isox-services.hook.chroot").read_text(encoding="utf-8")
assert "/etc/lightdm/lightdm-gtk-greeter.conf" in services_hook
assert "iso-x-desktop-wallpaper.png" in services_hook and "iso-x-dragon.png" in services_hook
assert "/etc/lightdm/lightdm.conf.d/50-isox-live-autologin.conf" in services_hook
assert "install -d -m 0755 /etc/lightdm /etc/lightdm/lightdm.conf.d" in services_hook
assert "[Seat:*]" in services_hook and "autologin-user=user" in services_hook
assert "autologin-session=openbox" in services_hook and "user-session=openbox" in services_hook
assert "/usr/share/xsessions/openbox.desktop" in services_hook
assert "username=user" in auto_config, "LightDM autologin must match the live-config account."
assert "exec /usr/local/bin/iso-x" in build, "The authenticated Openbox session must start the ISO-X desktop."
assert not any(ROOT.rglob("*.key")), "Private key must not be stored in the source tree"
assert (ROOT / "build.sh").stat().st_mode & 0o111, "Root one-command build entry point must be executable"

for asset in (
    "assets/iso-x-dragon.svg", "assets/iso-x-dragon.png",
    "assets/iso-x-boot.svg", "assets/iso-x-boot.png",
    "assets/iso-x-desktop-wallpaper.svg", "assets/iso-x-desktop-wallpaper.png",
    "assets/iso-x-plymouth.png", "docs/QEMU_ACCEPTANCE_AR.md", "tests/qemu-acceptance.sh",
    "plymouth/isox/isox.plymouth", "plymouth/isox/isox.script",
    "config/hooks/live/0050-isox-locales.hook.chroot",
    "config/hooks/live/0100-isox-watermark.hook.chroot",
    "config/hooks/live/0200-isox-plymouth.hook.chroot",
    "desktop/openbox-menu.xml", "desktop/openbox-rc.xml",
    "scripts/install-build-deps.sh", "scripts/isox-run.py", "scripts/isox-speedtest",
    "scripts/apply-windows-look.sh", "scripts/toggle-airplane.sh", "config/hooks/live/0300-isox-services.hook.chroot",
    "tests/test_secure_vault.py", "tests/test_secureboot_validation.sh",
    "README.md", "build.sh", "docs/THIRD_PARTY_LICENSES.md",
    "db/migrations/003_isox_031.sql", "db/migrations/004_isox_040.sql",
    "app/isox_store_backend.py", "scripts/generate-store-sounds.py",
    "desktop/isox-store.desktop", "tests/test_store_backend.py",
):
    assert (ROOT / asset).is_file(), f"Missing feature/integration asset: {asset}"

assert {"appstream", "python3-yaml", "flatpak", "pulseaudio-utils"} <= packages
assert "user-setup" in packages, "live-config needs user-setup to create the configured live account."
assert "isox-desktop-window-ready.sh" in build, "CI readiness must verify the ISO-X application window."
for store_asset, image_path in (
    ("$PROJECT_DIR/app/isox_store_backend.py", "config/includes.chroot/usr/share/iso-x/isox_store_backend.py"),
    ('"$PROJECT_DIR"/assets/sounds/*.wav', "config/includes.chroot/usr/share/iso-x/assets/sounds/"),
    ("$PROJECT_DIR/desktop/isox-store.desktop", "config/includes.chroot/usr/share/applications/isox-store.desktop"),
):
    assert store_asset in build and image_path in build, f"Store asset is not staged: {store_asset}"
store_menu = (ROOT / "desktop/openbox-menu.xml").read_text(encoding="utf-8")
assert '<item label="ISO-X Store">' in store_menu and "isox_appcenter.py" in store_menu

assert 'Image("iso-x-plymouth.png")' in (ROOT / "plymouth/isox/isox.script").read_text()
plymouth_dims = __import__("struct").unpack(">II", (ROOT / "assets/iso-x-plymouth.png").read_bytes()[16:24])
assert max(plymouth_dims) <= 512, f"Plymouth logo should fit low-resolution screens: {plymouth_dims}"
assert "images/iso-x-dragon.png" in (ROOT / "three-d-login/src/main.rs").read_text()
assert "png" in cargo["dependencies"]["bevy"]["features"]
for xml in (ROOT / "desktop/openbox-menu.xml", ROOT / "desktop/openbox-rc.xml",
            ROOT / "plymouth/isox/isox.plymouth", ROOT / "assets/iso-x-dragon.svg",
            ROOT / "assets/iso-x-boot.svg", ROOT / "assets/iso-x-desktop-wallpaper.svg"):
    if xml.suffix == ".xml" or xml.suffix == ".svg":
        ET.parse(xml)

openbox_root = ET.parse(ROOT / "desktop/openbox-rc.xml").getroot()
openbox_ns = {"ob": "http://openbox.org/3.4/rc"}
mouse_contexts = {
    name: context
    for context in openbox_root.findall("ob:mouse/ob:context", openbox_ns)
    for name in context.attrib["name"].split()
}

def has_mouse_action(context_name, button, gesture, action, edge=None):
    context = mouse_contexts[context_name]
    for binding in context.findall("ob:mousebind", openbox_ns):
        if binding.attrib != {"button": button, "action": gesture}:
            continue
        for requested in binding.findall("ob:action", openbox_ns):
            if requested.attrib.get("name") != action:
                continue
            requested_edge = requested.find("ob:edge", openbox_ns)
            if edge is None and requested_edge is None:
                return True
            if requested_edge is not None and requested_edge.text == edge:
                return True
    return False

assert has_mouse_action("Titlebar", "Left", "Drag", "Move"), "Titlebar must drag-move native windows."
assert has_mouse_action("Titlebar", "Left", "DoubleClick", "ToggleMaximize"), "Titlebar double-click must toggle maximize."
for edge_name in ("Top", "Bottom", "Left", "Right"):
    assert has_mouse_action(edge_name, "Left", "Drag", "Resize", edge_name.lower()), (
        f"{edge_name} edge must resize a native window on left-button drag."
    )
for corner_name in ("TLCorner", "TRCorner", "BLCorner", "BRCorner"):
    assert has_mouse_action(corner_name, "Left", "Drag", "Resize"), (
        f"{corner_name} corner must resize a native window on left-button drag."
    )
assert has_mouse_action("Iconify", "Left", "Click", "Iconify"), "The native minimize button must iconify its window."
assert has_mouse_action("Maximize", "Left", "Click", "ToggleMaximize"), "The native maximize button must toggle state."
assert has_mouse_action("Close", "Left", "Click", "Close"), "The native close button must close only its window."
assert has_mouse_action("Frame", "A-Left", "Drag", "Move"), "Keep the existing Alt+left move binding."
assert any(
    binding.attrib == {"button": "A-Right", "action": "Resize"}
    for binding in mouse_contexts["Frame"].findall("ob:mousebind", openbox_ns)
), "Keep the existing Alt+right resize binding."
keybinds = {
    keybind.attrib["key"]: keybind
    for keybind in openbox_root.findall("ob:keyboard/ob:keybind", openbox_ns)
}
assert any(action.attrib.get("name") == "Close" for action in keybinds["A-F4"].findall("ob:action", openbox_ns))
assert any(action.attrib.get("name") == "NextWindow" for action in keybinds["A-Tab"].findall("ob:action", openbox_ns))
assert any(action.attrib.get("name") == "PreviousWindow" for action in keybinds["A-S-Tab"].findall("ob:action", openbox_ns))

watermark = (ROOT / "kernel/isox-watermark/isox_watermark.c").read_text(encoding="utf-8")
assert "^ ISOX_WM_XOR_MASK" in watermark, "Watermark decoding must match the generator's XOR mask"
assert "PENDING_BUILD_DIGEST" not in watermark
assert not (ROOT / "kernel/isox-watermark/watermark_digest.h").exists(), "Obsolete fake digest header must not return"
locales_hook = (ROOT / "config/hooks/live/0050-isox-locales.hook.chroot").read_text(encoding="utf-8")
assert "printf '%s UTF-8\\n'" in locales_hook, "Locale hook must write real newlines"
build_tz = next((line for line in build.splitlines() if "Asia/Baghdad" in line and "printf" in line), "")
assert "printf '%s\\n'" in build_tz, "Timezone file must not contain a literal backslash-n"
for executable in ("scripts/build-iso.sh", "scripts/encode-watermark.py", "scripts/write-usb.sh",
                   "scripts/secure-vault.sh", "scripts/isox-run.py", "scripts/isox-snap-window.sh",
                   "scripts/install-build-deps.sh", "scripts/apply-windows-look.sh", "scripts/toggle-airplane.sh",
                   "tests/qemu-acceptance.sh", "tests/test_secureboot_validation.sh", "scripts/secureboot-enroll.sh", "scripts/isox-speedtest", "auto/config"):
    assert (ROOT / executable).stat().st_mode & 0o111, f"Entry point is not executable: {executable}"

packages = [x.strip() for x in (ROOT / "config/package-lists/iso-x.list.chroot").read_text().splitlines()
            if x.strip() and not x.strip().startswith("#")]
assert len(packages) == len(set(packages)), "Duplicate packages remain in the package list"
assert "debian-installer-launcher" in packages
for package in ("dmz-cursor-theme", "libnotify-bin", "xfce4-notifyd", "hardinfo", "gnome-calendar", "gnome-disk-utility"):
    assert package in packages, f"Missing requested desktop capability package: {package}"
assert "fonts-kacst" not in packages and "pinta" not in packages
assert "firmware-nvidia-graphics" not in packages, "A backports-only package would break the stable-only build"
assert (ROOT / "desktop/tint2rc").read_text().count("panel_padding =") == 1
assert "panel_items = LTBESC" in (ROOT / "desktop/tint2rc").read_text()
assert "execp_command = /usr/local/bin/isox-keyboard status" in (ROOT / "desktop/tint2rc").read_text()
assert "execp_lclick_command = /usr/local/bin/isox-keyboard toggle" in (ROOT / "desktop/tint2rc").read_text()
assert "pcmanfm --desktop --profile=isox" in build, "Desktop icons and the wallpaper need a desktop manager"
assert "isox-toggle-airplane" in build and "W-a" in (ROOT / "desktop/openbox-rc.xml").read_text()
assert "gxkb" not in packages and "isox-keyboard" in build
assert '"$PROJECT_DIR/app/isox_keyboard.py" config/includes.chroot/usr/share/iso-x/isox_keyboard.py' in build
assert "x11-xkb-utils" in packages
assert "xkb-switch" not in (ROOT / ".github/workflows/iso-build.yml").read_text()
assert 'setxkbmap -layout ara,us -option grp:alt_shift_toggle_bidir' in build
assert 'XKBLAYOUT="ara,us"' in build and 'XKBOPTIONS="grp:alt_shift_toggle_bidir"' in build
assert "nm-applet >/tmp/isox-nm-applet.log" in build
assert "nm-applet --indicator" not in build, "tint2 uses the XEmbed system tray"
gtk_app = (ROOT / "app/iso_x_gtk.py").read_text(encoding="utf-8")
assert gtk_app.count("set_direction(Gtk.TextDirection.LTR)") >= 5
assert "threading.Thread(\n            target=self._collect_stats_worker" in gtk_app
assert "GLib.idle_add(self._stats_loaded" in gtk_app
assert "if self.active_file_operations:" in gtk_app
assert "GLib.idle_add(self._quit_main_loops)" in gtk_app
store_app = (ROOT / "app/isox_appcenter.py").read_text(encoding="utf-8")
assert 'self.connect("delete-event", self._on_delete_event)' in store_app
assert "window.connect(\"destroy\", window._on_destroy)" in store_app
assert "Alt+Shift" in (ROOT / "README_AR.md").read_text(encoding="utf-8")
assert 'تبديل AR / EN' in gtk_app
assert 'isox-keyboard toggle' in (ROOT / "desktop/openbox-menu.xml").read_text(encoding="utf-8")

desktop = configparser.ConfigParser(interpolation=None)
desktop.optionxform = str
desktop.read(ROOT / "desktop/isox-welcome.desktop", encoding="utf-8")
welcome_exec = shlex.split(desktop["Desktop Entry"]["Exec"])[0]
assert welcome_exec == "/usr/local/bin/isox-welcome"
assert "config/includes.chroot/usr/local/bin/isox-welcome" in build
for xml_path in (ROOT / "desktop/openbox-menu.xml", ROOT / "desktop/openbox-rc.xml"):
    xml_root = ET.parse(xml_path).getroot()
    for command_node in xml_root.iter("{*}command"):
        command = shlex.split(command_node.text or "")
        assert command, f"Empty Openbox command in {xml_path}"
        executable = command[0]
        if executable.startswith("/usr/local/bin/"):
            assert executable.removeprefix("/") in build, f"Unstaged Openbox command: {executable}"
        elif executable == "dm-tool":
            assert "lightdm" in packages
        elif executable == "nm-connection-editor":
            assert "network-manager-gnome" in packages
        else:
            assert executable in packages, f"Openbox command has no package: {executable}"

schema = (ROOT / "db/schema.sql").read_text(encoding="utf-8")
assert "module_version TEXT NOT NULL DEFAULT '0.3.1'" in schema
assert "VALUES ('0.4.0')" in schema
print("PASS: source config, live installer, app entry points, branding, locale/timezone, database migration, and package-list consistency")

secureboot_script = (ROOT / "scripts/secureboot-enroll.sh").read_text(encoding="utf-8")
assert "sbctl enroll-keys" not in secureboot_script and "sbctl sign" not in secureboot_script
assert "does NOT enroll keys" in secureboot_script
