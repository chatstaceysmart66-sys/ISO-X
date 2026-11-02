#!/usr/bin/env python3
"""Render ISO-X brand PNGs from one dragon SVG source."""
from __future__ import annotations

import argparse
import copy
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import cairosvg
except ImportError as error:
    raise SystemExit("Missing build dependency: install python3-cairosvg") from error


ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
SVG_TAG = f"{{{SVG_NS}}}svg"
IMAGE_TAG = f"{{{SVG_NS}}}image"


def _image_href(element: ET.Element) -> str:
    return element.get("href", element.get(f"{{{XLINK_NS}}}href", ""))


def inline_master_mark(root: ET.Element, master: ET.Element) -> None:
    parents = {child: parent for parent in root.iter() for child in parent}
    references = [element for element in root.iter(IMAGE_TAG) if _image_href(element) == "iso-x-dragon.svg"]
    if not references:
        raise ValueError("Brand scene must reference the master iso-x-dragon.svg artwork")
    for reference in references:
        parent = parents.get(reference)
        if parent is None:
            raise ValueError("Could not locate parent for master dragon image")
        attrs = {
            name: reference.attrib[name]
            for name in ("x", "y", "width", "height", "preserveAspectRatio")
            if name in reference.attrib
        }
        nested = ET.Element(SVG_TAG, {**attrs, "viewBox": master.get("viewBox", "0 0 512 512")})
        for child in master:
            nested.append(copy.deepcopy(child))
        index = list(parent).index(reference)
        parent.remove(reference)
        parent.insert(index, nested)


def render(root: ET.Element, destination: Path, width: int, height: int) -> None:
    source = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    cairosvg.svg2png(bytestring=source, write_to=str(destination), output_width=width, output_height=height)
    contents = destination.read_bytes()
    if len(contents) < 64 or contents[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Renderer produced an invalid PNG: {destination}")
    actual = struct.unpack(">II", contents[16:24])
    if actual != (width, height):
        raise ValueError(f"Unexpected dimensions for {destination}: {actual}, expected {(width, height)}")


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    master_path = ROOT / "assets/iso-x-dragon.svg"
    master = ET.parse(master_path).getroot()

    ET.register_namespace("", SVG_NS)
    render(master, output / "iso-x-dragon.png", 1024, 1024)

    boot = ET.parse(ROOT / "assets/iso-x-boot.svg").getroot()
    inline_master_mark(boot, master)
    (output / "iso-x-boot.svg").write_bytes(ET.tostring(boot, encoding="utf-8", xml_declaration=True))
    render(boot, output / "iso-x-boot.png", 1024, 1024)
    render(boot, output / "iso-x-plymouth.png", 512, 512)

    wallpaper = ET.parse(ROOT / "assets/iso-x-desktop-wallpaper.svg").getroot()
    inline_master_mark(wallpaper, master)
    (output / "iso-x-desktop-wallpaper.svg").write_bytes(
        ET.tostring(wallpaper, encoding="utf-8", xml_declaration=True)
    )
    render(wallpaper, output / "iso-x-desktop-wallpaper.png", 3840, 2160)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        generate(args.output_dir.resolve())
    except (OSError, ET.ParseError, ValueError) as error:
        print(f"Brand asset generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Generated five ISO-X brand assets from {ROOT / 'assets/iso-x-dragon.svg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())