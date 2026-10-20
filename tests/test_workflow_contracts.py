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
build_helper = (Path(__file__).resolve().parents[1] / "scripts/ci-build-in-trixie.sh").read_text()

assert "needs: build" in bios and "needs: build" in uefi
assert "scripts/run-source-checks.py" in source
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
assert "xorriso -indev" in build_helper and "iso-validated.ok" in build
assert "qemu-acceptance.sh bios-headless" in bios
assert "qemu-acceptance.sh uefi-headless" in uefi
assert "boot_status != 'PASS_BOOT'" in bios and "boot_status != 'PASS_BOOT'" in uefi
assert "needs.bios.result == 'success'" in summary
assert "needs.uefi.result == 'success'" in summary
assert "not a release ISO" in summary
assert "scripts/create-ci-results.py" in summary
assert "hashFiles(" not in workflow
for ref in re.findall(r"uses: actions/[^\s@]+@([0-9a-f]{40})", workflow):
    assert len(ref) == 40
assert workflow.count("Node.js 24") >= 3
print("PASS: workflow keeps boot gates independent and protects candidate/final artifact conditions.")
