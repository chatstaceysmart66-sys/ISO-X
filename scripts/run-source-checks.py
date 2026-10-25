#!/usr/bin/env python3
"""Run source-only checks and preserve each real exit code and log."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def checks(junit_path: Path) -> list[tuple[str, list[str]]]:
    shell_files = (
        "find . -type f \\( -name '*.sh' -o -path './auto/config' -o -name '*.hook.chroot' \\) "
        "-print0 | xargs -0 -r -n1 bash -n"
    )
    shellcheck = (
        "find . -type f \\( -name '*.sh' -o -path './auto/config' -o -name '*.hook.chroot' \\) "
        "-print0 | xargs -0 -r shellcheck -S warning"
    )
    return [
        ("python-compile", [sys.executable, "-m", "compileall", "-q", "app", "scripts", "tests"]),
        ("pytest", [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", f"--junitxml={junit_path}"]),
        ("smoke", ["bash", "tests/smoke.sh"]),
        ("build-contracts", [sys.executable, "tests/test_build_contracts.py"]),
        ("source-config", [sys.executable, "tests/test_source_config.py"]),
        ("secure-vault", [sys.executable, "tests/test_secure_vault.py"]),
        ("store-backend", [sys.executable, "tests/test_store_backend.py"]),
        ("schema", [sys.executable, "tests/test_schema.py"]),
        ("upstream-integration", [sys.executable, "tests/test_upstream_integration.py"]),
        ("usb-validation", ["bash", "tests/test_write_usb_validation.sh"]),
        ("usb-persistence-partition", ["bash", "tests/test_write_usb_persistence.sh"]),
        ("qemu-fake-validation", ["bash", "tests/test_qemu_headless_validation.sh"]),
        ("desktop-readiness", ["bash", "tests/test_desktop_readiness.sh"]),
        ("gtk-window-runtime", ["xvfb-run", "-a", "-s", "-screen 0 1366x1024x24", sys.executable, "tests/test_gtk_window_runtime.py"]),
        ("secureboot-validation", ["bash", "tests/test_secureboot_validation.sh"]),
        ("initramfs-watermark-validation", ["bash", "tests/test_initramfs_watermark_guard.sh"]),
        ("watermark-integrity", ["bash", "tests/test_watermark_integrity.sh"]),
        ("workflow-contracts", [sys.executable, "tests/test_workflow_contracts.py"]),
        ("ci-results", [sys.executable, "tests/test_ci_results.py"]),
        ("bash-syntax", ["bash", "-Eeuo", "pipefail", "-c", shell_files]),
        ("initramfs-sh-syntax", ["sh", "-n", "initramfs/hooks/isox-watermark", "initramfs/scripts/init-premount/isox-watermark-guard"]),
        ("shellcheck", ["bash", "-Eeuo", "pipefail", "-c", shellcheck]),
        ("desktop-files", ["bash", "-Eeuo", "pipefail", "-c", "desktop-file-validate desktop/*.desktop"]),
        ("xml-svg", ["bash", "-Eeuo", "pipefail", "-c", "find desktop -name '*.xml' -print0 | xargs -0 -r -n1 xmllint --noout && find assets -name '*.svg' -print0 | xargs -0 -r -n1 xmllint --noout"]),
        ("diff-check", ["git", "diff", "--check"]),
    ]


def pytest_counts(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"passed": 0, "failed": 0, "skipped": 0}
    root = ET.parse(path).getroot()
    suites = list(root.iter("testsuite"))
    return {
        "passed": sum(max(0, int(suite.get("tests", "0")) - int(suite.get("failures", "0")) - int(suite.get("errors", "0")) - int(suite.get("skipped", "0"))) for suite in suites),
        "failed": sum(int(suite.get("failures", "0")) + int(suite.get("errors", "0")) for suite in suites),
        "skipped": sum(int(suite.get("skipped", "0")) for suite in suites),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} EVIDENCE_DIR PYTHON_CACHE_DIR", file=sys.stderr)
        return 2
    evidence = Path(sys.argv[1]).resolve()
    cache_dir = Path(sys.argv[2]).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    junit_path = evidence / "pytest.xml"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = str(cache_dir)
    results = []
    required_tools = {
        "shellcheck": ["shellcheck"],
        "desktop-files": ["desktop-file-validate"],
        "xml-svg": ["xmllint"],
        "usb-persistence-partition": ["sfdisk"],
        "gtk-window-runtime": ["xvfb-run", "xdotool", "wmctrl", "openbox"],
    }

    for name, command in checks(junit_path):
        logfile = evidence / f"{name}.log"
        print(f"RUN {name}: {' '.join(command)}", flush=True)
        missing_tools = [tool for tool in required_tools.get(name, []) if shutil.which(tool) is None]
        if missing_tools:
            error = f"NOT_RUN: required tool(s) unavailable: {', '.join(missing_tools)}"
            logfile.write_text(error + "\n", encoding="utf-8")
            result = {"name": name, "status": "NOT_RUN", "exit_code": None, "missing_tools": missing_tools, "log": logfile.name}
            results.append(result)
            print(f"NOT_RUN {name}: {error}", flush=True)
            continue
        try:
            completed = subprocess.run(
                command, cwd=ROOT, env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=False,
            )
            logfile.write_text(completed.stdout, encoding="utf-8")
            result = {
                "name": name,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
                "exit_code": completed.returncode,
                "log": logfile.name,
            }
        except OSError as error:
            logfile.write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
            result = {"name": name, "status": "NOT_RUN", "exit_code": None, "error": str(error), "log": logfile.name}
        results.append(result)
        print(f"{result['status']} {name}: exit={result['exit_code']}", flush=True)

    counts = pytest_counts(junit_path)
    counts["passed"] += sum(result["name"] != "pytest" and result["status"] == "PASS" for result in results)
    counts["failed"] += sum(result["name"] != "pytest" and result["status"] == "FAIL" for result in results)
    counts["not_run"] = sum(result["status"] == "NOT_RUN" for result in results)
    pytest_result = next(result for result in results if result["name"] == "pytest")
    if pytest_result["status"] == "FAIL" and counts["failed"] == 0:
        counts["failed"] = 1
    exit_code = 1 if counts["failed"] or counts["not_run"] else 0
    summary = {
        "unit": "pytest cases plus non-pytest check executions",
        "counts": counts,
        "exit_code": exit_code,
        "checks": results,
    }
    (evidence / "source-tests.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
