#!/usr/bin/env python3
"""Verify that generated reference artwork and manifest reached an ISO rootfs tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rootfs_path(rootfs: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Invalid absolute rootfs path in manifest: {value}")
    return rootfs / path.relative_to("/")


def verify(manifest_path: Path, rootfs: Path, source: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hash = _sha256(source)
    if source_hash != manifest["source"]["sha256"]:
        raise ValueError("Reference HTML SHA-256 does not match the generated asset manifest")
    if manifest["source"]["unique_image_count"] != len(manifest["assets"]):
        raise ValueError("Manifest unique image count does not match its asset entries")
    if sum(asset["data_uri_occurrences"] for asset in manifest["assets"]) != manifest["source"]["data_uri_count"]:
        raise ValueError("Manifest data URI occurrence count does not match its asset entries")

    installed_manifest = _rootfs_path(
        rootfs, "/usr/share/iso-x/assets/reference-assets.json"
    )
    if not installed_manifest.is_file():
        raise ValueError(f"Staged asset manifest is missing: {installed_manifest}")
    if installed_manifest.read_bytes() != manifest_path.read_bytes():
        raise ValueError("Staged reference-assets.json differs from the generated manifest")

    verified = [str(installed_manifest)]
    for asset in manifest["assets"]:
        original_value = asset.get("rootfs_original_path")
        if not original_value:
            raise ValueError(f"Original image has no rootfs path: {asset['role']}")
        original_path = _rootfs_path(rootfs, original_value)
        if not original_path.is_file():
            raise ValueError(f"Staged original image is missing: {original_path}")
        if _sha256(original_path) != asset["original_sha256"]:
            raise ValueError(f"Staged original image hash mismatch: {original_path}")
        verified.append(f"{original_path} sha256={asset['original_sha256']}")

        for derived in asset.get("derived_files", []):
            rootfs_value = derived.get("rootfs_path")
            if not rootfs_value:
                continue
            derived_path = _rootfs_path(rootfs, rootfs_value)
            if not derived_path.is_file():
                raise ValueError(f"Staged derived image is missing: {derived_path}")
            if _sha256(derived_path) != derived["sha256"]:
                raise ValueError(f"Staged derived image hash mismatch: {derived_path}")
            verified.append(f"{derived_path} sha256={derived['sha256']}")

        optional_path = asset.get("system_integration", {}).get("optional_cinematic_asset_path")
        if optional_path:
            optional_file = _rootfs_path(rootfs, optional_path)
            if optional_file.exists():
                optional_source = next(
                    (
                        item for item in asset.get("derived_files", [])
                        if item["file"] == "dragon-mark.png"
                    ),
                    None,
                )
                if optional_source is None or _sha256(optional_file) != optional_source["sha256"]:
                    raise ValueError(f"Optional cinematic logo does not match the reference: {optional_file}")
                verified.append(f"{optional_file} sha256={optional_source['sha256']}")

    return verified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    try:
        verified = verify(args.manifest, args.rootfs, args.source)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as error:
        print(f"Reference asset verification failed: {error}", file=sys.stderr)
        return 1
    print(f"PASS: verified reference source and {len(verified) - 1} installed image files.")
    for item in verified:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
