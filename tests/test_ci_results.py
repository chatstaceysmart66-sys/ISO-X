#!/usr/bin/env python3
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "tests/ci-results.schema.json").read_text(encoding="utf-8"))


def validate_report(report):
    required = set(SCHEMA["required"])
    if not isinstance(report, dict) or not required.issubset(report):
        raise ValueError("missing top-level required fields")
    if report["project"] != "ISO-X":
        raise ValueError("unexpected project")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT.+", report["timestamp_utc"]):
        raise ValueError("invalid UTC timestamp")
    if set(report["checks"]) != {"source_checks", "iso_build_and_structure", "bios_boot", "uefi_boot"}:
        raise ValueError("invalid acceptance gates")
    statuses = {"PASS", "FAIL", "NOT_RUN", "CANCELLED"}
    if any(value not in statuses for value in report["checks"].values()):
        raise ValueError("invalid gate status")
    for key in ("bios", "uefi"):
        if report[key].get("gate") not in statuses:
            raise ValueError(f"invalid {key} gate")
        indicators = report[key].get("serial_indicators", {})
        if set(indicators) != {"bootloader", "kernel", "initramfs", "systemd", "graphical_target", "display_manager"}:
            raise ValueError(f"incomplete {key} serial indicators")
    if report["persistence"].get("status") not in {"PASS", "FAIL", "NOT_IMPLEMENTED", "NOT_RUN"}:
        raise ValueError("invalid persistence status")
    if set(report["test_summary"]) != {"passed", "failed", "skipped", "not_run"}:
        raise ValueError("invalid test summary counts")
    if any(not isinstance(value, int) or value < 0 for value in report["test_summary"].values()):
        raise ValueError("test summary counts must be non-negative integers")
    if not isinstance(report["test_summary_unit"], str) or not isinstance(report["test_checks"], list):
        raise ValueError("source test summary metadata is missing")
    if set(report["acceptance_gate_summary"]) != {"passed", "failed", "skipped", "not_run"}:
        raise ValueError("invalid acceptance gate summary")
    if set(report["exit_codes"]) != {"source_checks", "iso_build", "iso_sha256", "xorriso_structure", "bios_qemu", "uefi_qemu"}:
        raise ValueError("invalid process exit-code report")


def main():
    if len(sys.argv) > 1:
        try:
            with Path(sys.argv[1]).open(encoding="utf-8") as stream:
                validate_report(json.load(stream))
        except (json.JSONDecodeError, OSError, ValueError) as error:
            print(f"Invalid results.json: {error}", file=sys.stderr)
            return 1
        print("PASS: results.json is valid.")
        return 0

    with tempfile.TemporaryDirectory(prefix="isox-results-test-") as temporary:
        report_path = Path(temporary) / "results.json"
        command = [
            sys.executable, str(ROOT / "scripts/create-ci-results.py"),
            "--output", str(report_path), "--project", "ISO-X",
            "--release", "0.4.0 TRIXIE", "--branch", "test",
            "--commit", "deadbeef", "--run-id", "1", "--run-attempt", "1",
            "--source-result", "success", "--build-result", "failure",
            "--bios-job-result", "failure", "--bios-status", "NO_SERIAL_OUTPUT",
            "--uefi-job-result", "skipped", "--uefi-status", "NOT_RUN",
            "--iso-sha256", "", "--iso-size", "0",
        ]
        import subprocess
        subprocess.run(command, check=True, env={"PYTHONDONTWRITEBYTECODE": "1"})
        with report_path.open(encoding="utf-8") as stream:
            report = json.load(stream)
        validate_report(report)
        assert report["checks"]["source_checks"] == "PASS"
        assert report["checks"]["bios_boot"] == "FAIL"
        assert report["checks"]["uefi_boot"] == "NOT_RUN"
        assert report["persistence"]["status"] == "NOT_RUN"
        assert "reboot persistence acceptance has not been run" in report["persistence"]["reason"]
        assert report["test_summary"]["not_run"] == 1

        source_summary_path = Path(temporary) / "source-tests.json"
        source_summary_path.write_text(json.dumps({
            "unit": "pytest cases plus check executions",
            "counts": {"passed": 12, "failed": 1, "skipped": 2, "not_run": 3},
            "exit_code": 1,
            "checks": [{"name": "shellcheck", "status": "NOT_RUN", "exit_code": None}],
        }), encoding="utf-8")
        complete_report_path = Path(temporary) / "results-with-source.json"
        source_command = list(command)
        source_command[source_command.index(str(report_path))] = str(complete_report_path)
        source_command.extend(["--source-summary", str(source_summary_path)])
        subprocess.run(source_command, check=True, env={"PYTHONDONTWRITEBYTECODE": "1"})
        complete_report = json.loads(complete_report_path.read_text(encoding="utf-8"))
        validate_report(complete_report)
        assert complete_report["test_summary"] == {"passed": 12, "failed": 1, "skipped": 2, "not_run": 3}
        assert complete_report["test_checks"][0]["status"] == "NOT_RUN"

        malformed = Path(temporary) / "malformed.json"
        malformed.write_text("{broken", encoding="utf-8")
        try:
            json.loads(malformed.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("malformed JSON was accepted")
        incomplete = dict(report)
        incomplete.pop("bios")
        try:
            validate_report(incomplete)
        except ValueError:
            pass
        else:
            raise AssertionError("report missing required fields was accepted")

        for invalid_args in (
            ["--iso-size", "not-a-number"],
            ["--bios-duration", "not-a-duration"],
        ):
            invalid_output = Path(temporary) / f"invalid-{len(list(Path(temporary).glob('invalid-*')))}.json"
            invalid_command = list(command)
            invalid_command[invalid_command.index(str(report_path))] = str(invalid_output)
            invalid_command.extend(invalid_args)
            failed = subprocess.run(
                invalid_command,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
            )
            assert failed.returncode != 0, invalid_args
            assert "invalid" in failed.stderr.lower(), failed.stderr

        non_object = Path(temporary) / "non-object.json"
        non_object.write_text("[]", encoding="utf-8")
        non_object_command = list(command)
        non_object_command[non_object_command.index(str(report_path))] = str(Path(temporary) / "non-object-results.json")
        non_object_command.extend(["--source-summary", str(non_object)])
        failed = subprocess.run(
            non_object_command,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
        )
        assert failed.returncode != 0, "non-object source summary was accepted"
        assert "must contain an object" in failed.stderr, failed.stderr
    print("PASS: report generation, required fields, gate states, and malformed JSON rejection.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
