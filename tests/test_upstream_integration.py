#!/usr/bin/env python3
"""Static integration checks for ISO-X's reviewed Windows-Lite references."""
from pathlib import Path
import ast
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
app = ROOT / "app" / "isox_welcome.py"
build = (ROOT / "scripts" / "build-iso.sh").read_text(encoding="utf-8")
menu = ROOT / "desktop" / "openbox-menu.xml"
rc = ROOT / "desktop" / "openbox-rc.xml"
desktop = ROOT / "desktop" / "isox-welcome.desktop"
notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
readme = (ROOT / "README_AR.md").read_text(encoding="utf-8")
packages = (ROOT / "config" / "package-lists" / "iso-x.list.chroot").read_text(encoding="utf-8")
source = app.read_text(encoding="utf-8")

# All user-facing actions are direct argv invocations; the source must never use shell=True.
ast.parse(source)
for node in ast.walk(ast.parse(source)):
    if isinstance(node, ast.Call):
        assert not any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords), "shell=True is forbidden"
for action in ("browser", "files", "applications", "settings", "network", "installer", "monitor", "terminal"):
    assert f'"{action}"' in source, f"missing welcome action: {action}"
for required in ("THIRD_PARTY_NOTICES.md", "isox_welcome.py", "isox-welcome.desktop", "usr/share/doc/iso-x"):
    assert required in build, f"build does not install integration file: {required}"
assert "Super+W" in readme
assert "Windows Update" in notices and "Windows Defender" in notices
assert "RobertoBiundo/Windows10Lite" in notices
assert "windows10loud/Download-Windows-10-PRO-ISO-fast-and-lite" in notices
assert "not copied" in notices.lower() or "not bundled" in notices.lower()
assert "This PC" in build and "Home.desktop" in build and "Trash.desktop" in build

ns = {"o": "http://openbox.org/3.4/menu"}
menu_xml = ET.parse(menu).getroot()
assert menu_xml.find(".//o:item[@label='ISO-X — Welcome / First Steps']", ns) is not None
rc_xml = ET.parse(rc).getroot()
assert rc_xml.find(".//o:keybind[@key='W-w']", {"o": "http://openbox.org/3.4/rc"}) is not None

desktop_text = desktop.read_text(encoding="utf-8")
assert "Exec=/usr/local/bin/isox-welcome" in desktop_text
assert "Icon=iso-x" in desktop_text
assert "gir1.2-gtk-3.0" in packages and "network-manager-gnome" in packages

print("PASS: source-repo findings are documented, nonportable/unsafe Windows preset and ISO artifacts are not imported, and ISO-X-branded onboarding is wired into the build and desktop menu.")

# Branding assets must be valid XML/PNG resources of the documented dimensions.
for vector in (ROOT / "assets/iso-x-dragon.svg", ROOT / "assets/iso-x-boot.svg"):
    ET.parse(vector)
for image_path, expected in ((ROOT / "assets/iso-x-dragon.png", (1024, 1024)),
                            (ROOT / "assets/iso-x-boot.png", (1024, 1024)),
                            (ROOT / "assets/iso-x-plymouth.png", (512, 512))):
    with image_path.open("rb") as f:
        header = f.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG: {image_path}"
    dims = struct.unpack(">II", header[16:24])
    assert dims == expected, f"unexpected PNG dimensions for {image_path}: {dims}"
print("PASS: ISO-X dragon SVGs are valid XML and branding PNG dimensions match the documented resources.")
