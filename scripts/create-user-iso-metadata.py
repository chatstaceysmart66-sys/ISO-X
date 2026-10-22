#!/usr/bin/env python3
"""Finalize normal-boot ISO metadata from measured artifacts and boot results."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def boot_acceptance(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "NOT_RUN", "reason": "boot result file is missing"}
    result = read_object(path)
    fields = (
        "status", "desktop_seen", "shutdown_reason", "qemu_exit_code",
        "termination_requested", "termination_escalated", "process_group_clean",
        "final_screenshot_valid", "screenshots", "duration_seconds", "firmware",
    )
    return {field: result.get(field) for field in fields}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", required=True, type=Path)
    parser.add_argument("--diagnostic-metadata", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--bios-result", required=True, type=Path)
    parser.add_argument("--uefi-result", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--diagnostic-iso", required=True)
    parser.add_argument("--diagnostic-iso-path", required=True, type=Path)
    args = parser.parse_args()

    if not args.iso.is_file() or args.iso.stat().st_size == 0:
        raise ValueError(f"normal-boot ISO is missing or empty: {args.iso}")
    sidecar = args.iso.with_name(args.iso.name + ".sha256")
    if not sidecar.is_file():
        raise ValueError(f"normal-boot ISO SHA-256 sidecar is missing: {sidecar}")
    sidecar_fields = sidecar.read_text(encoding="ascii").split()
    actual_hash = digest_file(args.iso)
    if len(sidecar_fields) < 2 or sidecar_fields[0].lower() != actual_hash:
        raise ValueError("normal-boot ISO does not match its SHA-256 sidecar")
    if Path(sidecar_fields[-1]).name != args.iso.name:
        raise ValueError("normal-boot ISO sidecar names a different file")

    metadata = read_object(args.diagnostic_metadata)
    derived_hash = metadata.get("iso_sha256")
    if not isinstance(derived_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", derived_hash):
        raise ValueError("diagnostic ISO metadata has no valid SHA-256")
    if not args.diagnostic_iso_path.is_file() or args.diagnostic_iso_path.stat().st_size == 0:
        raise ValueError(f"diagnostic ISO is missing or empty: {args.diagnostic_iso_path}")
    if digest_file(args.diagnostic_iso_path) != derived_hash:
        raise ValueError("diagnostic ISO does not match its metadata SHA-256")
    size = args.iso.stat().st_size
    records = {
        "bios": boot_acceptance(args.bios_result),
        "uefi": boot_acceptance(args.uefi_result),
    }
    metadata["user_iso"] = {
        "path": args.iso.name,
        "size_bytes": size,
        "sha256": actual_hash,
        "boot_configuration": "normal boot arguments; CI nonce removed",
        "derived_from_ci_iso_sha256": derived_hash,
        "boot_acceptance": records,
    }
    metadata["iso_path"] = args.iso.name
    metadata["iso_size_bytes"] = size
    metadata["iso_sha256"] = actual_hash
    metadata["ci_boot_diagnostic_variant"] = False
    metadata.pop("ci_nonce", None)
    metadata["ci_readiness_probe"] = "included but inactive unless CI-only kernel arguments are present"
    metadata["persistence"] = {
        "status": "NOT_RUN",
        "reason": "USB persistence across a guest reboot has not been accepted.",
    }
    metadata["release_eligible"] = False
    metadata["release_eligibility_reason"] = "USB persistence across a guest reboot has not been accepted."
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"source_commit={metadata.get('commit', 'unknown')}",
        f"diagnostic_iso={args.diagnostic_iso}",
        f"user_iso={args.iso.name}",
        f"sha256={actual_hash}",
        f"size_bytes={size}",
        "variant=NORMAL_BOOT_CANDIDATE_NOT_RELEASE",
    ]
    for mode, result in records.items():
        lines.append(f"normal_iso_{mode}={result.get('status', 'NOT_RUN')}")
        lines.append(f"normal_iso_{mode}_desktop_seen={str(bool(result.get('desktop_seen'))).lower()}")
        lines.append(f"normal_iso_{mode}_final_screenshot_valid={str(bool(result.get('final_screenshot_valid'))).lower()}")
    lines.extend(("persistence=NOT_RUN", "release_eligible=false"))
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Normal-boot metadata written: {args.metadata}")
    print(f"SHA-256: {actual_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
