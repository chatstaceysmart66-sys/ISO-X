#!/usr/bin/env python3
from pathlib import Path
import re

workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/iso-build.yml").read_text()


def job(name):
    match = re.search(rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)", workflow)
    assert match, f"missing workflow job: {name}"
    return match.group(1)


build = job("build")
source = job("source-check")
bios = job("bios")
uefi = job("uefi")
summary = job("acceptance-summary")
promote = job("promote")
build_helper = (Path(__file__).resolve().parents[1] / "scripts/ci-build-in-trixie.sh").read_text()
source_runner = (Path(__file__).resolve().parents[1] / "scripts/run-source-checks.py").read_text()
ready_probe = (Path(__file__).resolve().parents[1] / "scripts/isox-ci-ready.sh").read_text()
ready_service = (Path(__file__).resolve().parents[1] / "systemd/isox-ci-ready.service").read_text()

assert "needs: build" in bios and "needs: build" in uefi
assert "scripts/run-source-checks.py" in source
assert "usb-persistence-partition" in source_runner
assert "libxml2-utils fdisk" in source
assert "source-tests.json" in summary
assert "Reclaim unused hosted-runner toolchains" in build
assert build.index("Reclaim unused hosted-runner toolchains") < build.index("Check runner capacity")
for runner_path in ("/usr/local/lib/android", "/usr/share/dotnet", "/opt/ghc",
                    "/usr/local/share/boost", "/usr/local/share/chromium",
                    "/usr/local/share/powershell"):
    assert runner_path in build, f"missing explicit disposable-runner space cleanup: {runner_path}"
assert "needs: [bios" not in uefi and "needs: [uefi" not in bios
assert "needs.build.outputs.validated == 'true'" in bios and "candidate_uploaded == 'success'" in bios
assert "needs.build.outputs.validated == 'true'" in uefi and "candidate_uploaded == 'success'" in uefi
assert "steps.validate.outputs.validated == 'true'" in build
assert "if: always()" in build and "isox-build-evidence-" in build
assert "ISO-X-0.4.0-ci-diagnostic-candidate-" in build
assert "steps.build-iso.outcome" in build and "sha256sum --check" in build
assert "report_validation_error()" in build
assert "::error title=Candidate validation::" in build
assert "require_nonempty_file()" in build and "require_match()" in build
assert '"status": "NOT_RUN"' in build
assert "USB writer can create an MBR/ext4 persistence partition" in build
assert "NOT_IMPLEMENTED" not in build
for check_name in (
    "candidate ISO must exist and be non-empty",
    "candidate SHA-256 sidecar must exist and be non-empty",
    "CI nonce must be 32 lowercase hexadecimal characters",
    "El Torito evidence must contain a BIOS boot entry",
    "El Torito evidence must contain a UEFI boot entry",
    "system-area evidence must contain MBR information",
):
    assert check_name in build, f"missing named manifest check: {check_name}"
assert "xorriso -indev" in build_helper and "iso-validated.ok" in build
assert "qemu-acceptance.sh bios-headless" in bios
assert "qemu-acceptance.sh uefi-headless" in uefi
assert "boot_status != 'PASS_BOOT'" in bios and "boot_status != 'PASS_BOOT'" in uefi
assert "::error title=BIOS boot acceptance::" in bios
assert "::error title=UEFI boot acceptance::" in uefi
assert "contents=$result" in bios and "contents=$result" in uefi
assert "needs.bios.result == 'success'" in summary
assert "needs.uefi.result == 'success'" in summary
assert "not a release ISO" in summary
assert "needs: [build, bios, uefi]" in promote
assert "needs.bios.result == 'success'" in promote and "needs.uefi.result == 'success'" in promote
assert "scripts/create-user-iso.py" in promote
assert "CI nonce removed" in promote
assert "persistence=NOT_RUN" in promote
assert "release_eligible=false" in promote
assert "ISO-X-0.4.0-live-amd64-candidate-" in promote
assert "needs: [source-check, build, bios, uefi, promote]" in workflow
assert "scripts/create-ci-results.py" in summary
assert "hashFiles(" not in workflow
for ref in re.findall(r"uses: actions/[^\s@]+@([0-9a-f]{40})", workflow):
    assert len(ref) == 40
assert workflow.count("Node.js 24") >= 3
assert "deadline=$(( $(date +%s) + 120 ))" in ready_probe
assert "TimeoutStartSec=130s" in ready_service
print("PASS: workflow keeps boot gates independent and protects candidate/final artifact conditions.")
