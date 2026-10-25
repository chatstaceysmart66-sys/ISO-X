#!/usr/bin/env python3
"""Create the per-run machine-readable ISO-X acceptance report."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: str | None) -> dict[str, Any]:
    if not path or not Path(path).is_file():
        return {}
    with Path(path).open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must contain an object: {path}")
    return value


def gate_result(job_result: str, status: str) -> str:
    if job_result == "success" and status in ("success", "PASS_BOOT"):
        return "PASS"
    if job_result == "skipped":
        return "NOT_RUN"
    if job_result == "cancelled":
        return "CANCELLED"
    return "FAIL"


def unknown_serial_indicators() -> dict[str, None]:
    return {
        "bootloader": None,
        "kernel": None,
        "initramfs": None,
        "systemd": None,
        "graphical_target": None,
        "display_manager": None,
    }


def optional_exit_code(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid process exit code: {value}") from error


def boot_record(job_result: str, status: str, duration: str, accelerator: str,
                detail: dict[str, Any]) -> dict[str, Any]:
    try:
        elapsed: float | None = float(duration) if duration else detail.get("duration_seconds")
    except ValueError as error:
        raise ValueError(f"invalid boot duration: {duration}") from error
    return {
        "job_result": job_result,
        "status": status,
        "gate": gate_result(job_result, status),
        "qemu_started": detail.get("qemu_started"),
        "duration_seconds": elapsed,
        "accelerator": accelerator,
        "qemu_version": detail.get("qemu_version", "see launch log"),
        "firmware": detail.get("firmware", "see launch log"),
        "firmware_version": detail.get("firmware_version", "see launch log"),
        "qemu_exit_code": detail.get("qemu_exit_code"),
        "shutdown_reason": detail.get("shutdown_reason", "not_started"),
        "termination_requested": detail.get("termination_requested"),
        "termination_escalated": detail.get("termination_escalated"),
        "process_group_clean": detail.get("process_group_clean"),
        "final_screenshot_valid": detail.get("final_screenshot_valid"),
        "serial_bytes": detail.get("serial_bytes"),
        "marker_seen": detail.get("marker_seen"),
        "serial_indicators": detail.get("serial_indicators", unknown_serial_indicators()),
        "serial_indicator_scope": "serial observations only; false does not prove the stage did not run",
        "screenshots": detail.get("screenshots", []),
        "evidence": detail.get("serial_log"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--source-result", required=True)
    parser.add_argument("--source-summary")
    parser.add_argument("--build-result", required=True)
    parser.add_argument("--build-exit-code", default="")
    parser.add_argument("--bios-job-result", required=True)
    parser.add_argument("--bios-status", required=True)
    parser.add_argument("--bios-duration", default="")
    parser.add_argument("--bios-accelerator", default="unknown")
    parser.add_argument("--bios-result")
    parser.add_argument("--uefi-job-result", required=True)
    parser.add_argument("--uefi-status", required=True)
    parser.add_argument("--uefi-duration", default="")
    parser.add_argument("--uefi-accelerator", default="unknown")
    parser.add_argument("--uefi-result")
    parser.add_argument("--iso-sha256", default="")
    parser.add_argument("--iso-size", default="0")
    parser.add_argument("--metadata")
    args = parser.parse_args()

    metadata = read_json(args.metadata)
    bios = boot_record(args.bios_job_result, args.bios_status, args.bios_duration,
                       args.bios_accelerator, read_json(args.bios_result))
    uefi = boot_record(args.uefi_job_result, args.uefi_status, args.uefi_duration,
                       args.uefi_accelerator, read_json(args.uefi_result))
    gates = {
        "source_checks": gate_result(args.source_result, args.source_result),
        "iso_build_and_structure": gate_result(args.build_result, args.build_result),
        "bios_boot": bios["gate"],
        "uefi_boot": uefi["gate"],
    }
    gate_counts = {"passed": 0, "failed": 0, "skipped": 0, "not_run": 0}
    for status in gates.values():
        key = {"PASS": "passed", "FAIL": "failed", "NOT_RUN": "not_run",
               "CANCELLED": "skipped"}[status]
        gate_counts[key] += 1
    source_summary = read_json(args.source_summary)
    source_counts = source_summary.get("counts", {})
    if source_summary and (
        not isinstance(source_counts, dict)
        or any(key not in source_counts for key in ("passed", "failed", "skipped", "not_run"))
        or not isinstance(source_summary.get("exit_code"), int)
        or not isinstance(source_summary.get("unit"), str)
        or not isinstance(source_summary.get("checks"), list)
    ):
        raise ValueError("source test summary is malformed")
    test_counts = {
        key: source_counts.get(key, 0 if source_summary else (1 if key == "not_run" else 0))
        for key in ("passed", "failed", "skipped", "not_run")
    }
    if any(not isinstance(value, int) or value < 0 for value in test_counts.values()):
        raise ValueError("source test counts must be non-negative integers")

    try:
        iso_size = int(args.iso_size)
    except ValueError as error:
        raise ValueError(f"invalid ISO size: {args.iso_size}") from error
    if iso_size < 0:
        raise ValueError(f"ISO size cannot be negative: {iso_size}")
    issues = []
    if not source_summary:
        issues.append("Source test detail artifact is unavailable.")
    if gates["source_checks"] != "PASS":
        issues.append(f"Source checks result: {args.source_result}.")
    if gates["iso_build_and_structure"] != "PASS":
        issues.append(f"ISO build and structural validation result: {args.build_result}.")
    for mode, record in (("BIOS", bios), ("UEFI", uefi)):
        if record["gate"] != "PASS":
            issues.append(f"{mode} acceptance: {record['status']} (job {record['job_result']}).")
    issues.append("USB persistence writing is implemented, but guest boot and reboot acceptance was not run.")
    report = {
        "project": args.project,
        "release": args.release,
        "branch": args.branch,
        "commit": args.commit,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "runner": "ubuntu-24.04",
            "build_os": metadata.get("build_os", "unknown"),
            "architecture": metadata.get("architecture", platform.machine()),
            "kernel": metadata.get("kernel", "unknown"),
            "tool_versions": metadata.get("tool_versions", {}),
        },
        "checks": gates,
        "exit_codes": {
            "source_checks": source_summary.get("exit_code"),
            "iso_build": optional_exit_code(args.build_exit_code),
            "iso_sha256": 0 if args.iso_sha256 and gates["iso_build_and_structure"] == "PASS" else None,
            "xorriso_structure": 0 if gates["iso_build_and_structure"] == "PASS" else None,
            "bios_qemu": bios["qemu_exit_code"],
            "uefi_qemu": uefi["qemu_exit_code"],
        },
        "iso": {
            "path": metadata.get("iso_path"),
            "size_bytes": iso_size,
            "sha256": args.iso_sha256 or None,
            "structural_validation": "PASS" if gates["iso_build_and_structure"] == "PASS" else "NOT_PASSED",
            "ci_boot_diagnostic_variant": bool(metadata.get("ci_boot_diagnostic_variant", False)),
            "release_eligible": bool(metadata.get("release_eligible", False)),
        },
        "bios": bios,
        "uefi": uefi,
        "persistence": {
            "status": "NOT_RUN",
            "reason": "The USB writer can create an MBR/ext4 persistence partition, but guest boot and reboot persistence acceptance has not been run.",
        },
        "test_summary": test_counts,
        "test_summary_unit": source_summary.get("unit", "source test results unavailable; one test group not run"),
        "test_checks": source_summary.get("checks", []),
        "acceptance_gate_summary": gate_counts,
        "remaining_issues": issues,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote acceptance report: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
