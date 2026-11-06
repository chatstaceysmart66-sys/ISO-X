#!/usr/bin/env python3
"""Extract and verify artwork embedded in the checked-in ISO-X design reference."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as error:
    raise SystemExit("Missing image dependency; install Debian package python3-pil.") from error

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "design/reference/iso-x-reference.html"
DATA_URI = re.compile(rb"data:([^;,]+);base64,([A-Za-z0-9+/=]+)")
ROLES = ("desktop-wallpaper", "boot-screen", "dragon-mark")
IMAGE_FORMATS = {
    "image/jpeg": ("JPEG", ".jpg"),
    "image/jpg": ("JPEG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/gif": ("GIF", ".gif"),
    "image/webp": ("WEBP", ".webp"),
    "image/bmp": ("BMP", ".bmp"),
    "image/tiff": ("TIFF", ".tiff"),
}


def _role(context: bytes) -> str | None:
    tail = context[-500:].lower()
    if b"--wp:url(" in tail:
        return "desktop-wallpaper"
    if b"--bp:url(" in tail:
        return "boot-screen"
    if b'id="start"' in tail:
        return "dragon-mark"
    return None


def _usage(context: bytes) -> str:
    tail = context[-500:].lower()
    if b"--wp:url(" in tail:
        return "#wall CSS variable --wp"
    if b"--bp:url(" in tail:
        return "#boot CSS variable --bp"
    if b'id="start"' in tail:
        return "#start image"
    if b"pic:" in tail:
        return "Pictures view"
    if b"about:" in tail:
        return "About view"
    return "Inline HTML/CSS image"


def _magic_matches(data: bytes, mime: str) -> bool:
    return {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/jpg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": data.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
        "image/bmp": data.startswith(b"BM"),
        "image/tiff": data.startswith((b"II*\x00", b"MM\x00*")),
    }.get(mime, False)


def _image_metadata(data: bytes, mime: str) -> dict:
    expected_format = IMAGE_FORMATS.get(mime)
    if expected_format is None or not _magic_matches(data, mime):
        raise ValueError(f"Unsupported MIME type or mismatched magic bytes: {mime}")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != expected_format[0]:
                raise ValueError(f"MIME says {expected_format[0]} but decoder found {image.format}")
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            rgb = image.convert("RGB")
            sample = rgb.copy()
            sample.thumbnail((128, 128), Image.Resampling.LANCZOS)
            quantized = sample.quantize(colors=5)
            palette = quantized.getpalette() or []
            color_counts = quantized.getcolors() or []
            colors = []
            for _, palette_index in sorted(color_counts, reverse=True)[:5]:
                start = palette_index * 3
                if start + 2 < len(palette):
                    colors.append("#{0:02x}{1:02x}{2:02x}".format(*palette[start:start + 3]))
    except (OSError, ValueError) as error:
        raise ValueError(f"Could not decode embedded {mime} image: {error}") from error
    return {
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}:{height}",
        "aspect_ratio_decimal": round(width / height, 6),
        "dominant_colors_rgb_approx": colors,
    }


def extract(source: Path, destination: Path) -> dict:
    source = source.resolve()
    html = source.read_bytes()
    matches = list(DATA_URI.finditer(html))
    if not matches:
        raise ValueError("No base64 image data URIs were found in the reference")

    decoded: list[dict] = []
    primary_by_hash: dict[str, str] = {}
    for match in matches:
        mime = match.group(1).decode("ascii").lower()
        try:
            data = base64.b64decode(match.group(2), validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("An embedded data URI contains invalid base64") from error
        sha256 = hashlib.sha256(data).hexdigest()
        context = html[max(0, match.start() - 500):match.start()]
        role = _role(context)
        if role:
            existing = primary_by_hash.get(sha256)
            if existing and existing != role:
                raise ValueError(f"One image is assigned to conflicting roles: {existing}, {role}")
            primary_by_hash[sha256] = role
        decoded.append({
            "mime_type": mime,
            "bytes": data,
            "sha256": sha256,
            "role": role,
            "offset": match.start(),
            "usage": _usage(context),
        })

    for item in decoded:
        if item["role"] is None:
            item["role"] = primary_by_hash.get(
                item["sha256"], f"embedded-{item['sha256'][:12]}"
            )
    if not set(ROLES) <= {item["role"] for item in decoded}:
        missing = sorted(set(ROLES) - {item["role"] for item in decoded})
        raise ValueError(f"Required design image roles are missing: {', '.join(missing)}")

    destination.mkdir(parents=True, exist_ok=True)
    assets = []
    image_groups: dict[str, list[dict]] = {}
    for item in decoded:
        image_groups.setdefault(item["sha256"], []).append(item)
    for sha256, occurrences in image_groups.items():
        item = occurrences[0]
        role = item["role"]
        if any(occurrence["role"] != role for occurrence in occurrences):
            raise ValueError(f"One identical image is assigned conflicting roles: {sha256}")
        if any(occurrence["mime_type"] != item["mime_type"] for occurrence in occurrences):
            raise ValueError(f"One identical image has conflicting MIME types: {sha256}")
        data = item["bytes"]
        details = _image_metadata(data, item["mime_type"])
        stem = role if role in ROLES else f"embedded-{sha256[:12]}"
        extension = IMAGE_FORMATS[item["mime_type"]][1]
        original = destination / f"{stem}-original{extension}"
        original.write_bytes(data)
        derived = []
        if role in ("boot-screen", "dragon-mark"):
            png_name = f"{role}.png"
            png_path = destination / png_name
            with Image.open(io.BytesIO(data)) as image:
                image.convert("RGB").save(png_path, format="PNG", optimize=False, compress_level=9)
            derived.append({
                "file": png_name,
                "sha256": hashlib.sha256(png_path.read_bytes()).hexdigest(),
                "width": details["width"],
                "height": details["height"],
                "transformation": "Lossless PNG encoding of decoded JPEG pixels; no crop or resize.",
                "rootfs_path": {
                    "boot-screen": "/usr/share/plymouth/themes/isox/iso-x-plymouth.png",
                    "dragon-mark": None,
                }[role],
            })
        if role == "dragon-mark":
            icon_path = destination / "dragon-mark-icon-96.png"
            with Image.open(io.BytesIO(data)) as image:
                mark = image.convert("RGBA")
                mark.thumbnail((96, 96), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
                canvas.alpha_composite(mark, ((96 - mark.width) // 2, (96 - mark.height) // 2))
                canvas.save(icon_path, format="PNG", optimize=False, compress_level=9)
            derived.append({
                "file": icon_path.name,
                "sha256": hashlib.sha256(icon_path.read_bytes()).hexdigest(),
                "width": 96,
                "height": 96,
                "transformation": "Proportional downscale/contain within transparent 96x96 canvas; no crop or upscale.",
                "rootfs_path": "/usr/share/icons/hicolor/96x96/apps/iso-x.png",
            })
        assets.append({
            "role": role,
            "element": {
                "desktop-wallpaper": "#wall CSS variable --wp; repeated in Pictures view",
                "boot-screen": "#boot CSS variable --bp; repeated in Pictures view",
                "dragon-mark": "#start image; repeated in About/Pictures view",
            }.get(role, item["usage"]),
            "mime_type": item["mime_type"],
            "original_file": original.name,
            "original_sha256": item["sha256"],
            "size_bytes": len(data),
            **details,
            "data_uri_occurrences": len(occurrences),
            "usages": [
                {"element": occurrence["usage"], "source_byte_offset": occurrence["offset"]}
                for occurrence in occurrences
            ],
            "rootfs_original_path": {
                "desktop-wallpaper": "/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.jpg",
                "boot-screen": "/usr/share/iso-x/assets/reference/boot-screen-original.jpg",
                "dragon-mark": "/usr/share/iso-x/assets/reference-dragon-mark.jpg",
            }.get(role, f"/usr/share/iso-x/assets/reference/{original.name}"),
            "derived_files": derived,
            "system_integration": {
                "desktop-wallpaper": {
                    "desktop_path": "/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.jpg",
                    "lightdm_background_path": "/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.jpg",
                },
                "boot-screen": {
                    "plymouth_path": "/usr/share/plymouth/themes/isox/iso-x-plymouth.png",
                },
                "dragon-mark": {
                    "application_asset_path": "/usr/share/iso-x/assets/reference-dragon-mark.jpg",
                    "icon_theme_path": "/usr/share/icons/hicolor/96x96/apps/iso-x.png",
                    "optional_cinematic_asset_path": "/usr/share/iso-x/cinematic-assets/images/iso-x-dragon.png",
                },
            }.get(role, {"reference_only": True}),
        })

    manifest = {
        "schema_version": 1,
        "source": {
            "file": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else source.name,
            "reported_attachment_name": "iso-x (1).txt",
            "reported_attachment_found": False,
            "source_identity_verified_as_attachment": False,
            "sha256": hashlib.sha256(html).hexdigest(),
            "size_bytes": len(html),
            "data_uri_count": len(matches),
            "unique_image_count": len(image_groups),
            "note": "The preserved source is the repository candidate iso-x 22.html; the specifically named task attachment was not available for byte comparison.",
        },
        "assets": assets,
    }
    manifest_path = destination / "reference-assets.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = extract(args.source, args.output_dir)
    except (OSError, ValueError) as error:
        print(f"Reference asset extraction failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Extracted {len(manifest['assets'])} image roles from "
        f"{manifest['source']['file']} ({manifest['source']['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
