# ISO-X Audit Report

## Snapshot and Result

- Repository branch at start: `fix/isox-build-and-runtime`.
- Starting HEAD: `22b9fc116ee278be22c5bbe30782f980100d85a1`.
- Starting worktree: clean; 130 tracked paths; no local build/test process. Ignored bytecode from prior test execution was present.
- GitHub workflow `40216891064` on the starting HEAD `22b9fc1`: `source-check=success`, `build=success`, BIOS=`success`, UEFI=`success`; `promote=IN PROGRESS` at last observation. This candidate includes the previously committed menu contrast and single-click defaults, but does not include the `pkexec`, `x11-xserver-utils`, Secure Vault interactive, or audit-report edits in this review.
- The new package, Secure Vault, and documentation edits are not included in run `40216891064`; their final commit and CI result must be reported separately.

## Findings and Changes

1. Secure Vault's Openbox menu launched its CLI without required arguments and returned usage/exit 2. Added interactive TTY mode/path selection while preserving direct CLI and secret handling.
2. Openbox snap shortcuts required `xrandr`, but the manifest omitted its Debian provider `x11-xserver-utils`. Added the package and linkage test.
3. App Center's APT flow requires `pkexec`, but the manifest omitted that split package. Added `pkexec` and a source contract.
4. Menu theme and desktop single-click fixes already present on starting HEAD explicitly set dark menu colors and `libfm single_click=1`; the hook runs during image build. Their source contract was exercised, but final rendered image evidence depends on the in-progress build.
5. Existing window runtime fix restores titlebar button coordinates consistent with Openbox and waits on observed EWMH state. It passed CI run `40210339242` before this audit.

## Test Evidence

- `tests/test_source_config.py`: `PASS` after adding package linkage assertions.
- `tests/test_store_backend.py`: 16 tests `PASS` with injected command runner; this is not a real privileged package install.
- `tests/test_secure_vault.py`: `PASS` for crypto round-trip, wrong-secret/tamper rejection and interactive route dispatch.
- `tests/test_build_contracts.py`: `PASS`, including temporary HOME settings and idempotent Openbox theme hook.
- Full source runner with pytest installed under `/tmp`: 67 passed, 0 failed, 1 skipped, 4 `NOT_RUN`; exit code 1 because required test tools were absent. Missing: `sfdisk`, Xvfb/Openbox interaction tools, ShellCheck, and `desktop-file-validate`.
- Shell syntax, Python compile, XML/SVG, smoke and `git diff --check`: `PASS`.
- Real Openbox theme file from Debian package: hook changed base/active menu colors to the intended palette and was idempotent. Pixel-level rendering was not tested here.
- Existing prior window CI: `PASS` for native close/minimize/maximize, move, all resize zones, focus and keyboard input in run `40210339242`.

## Unverified / Not Run

- The local dev container lacks Xvfb/Openbox, so the modified image's single-click action and menus were not exercised in a real session. Test on touchscreen hardware remains `NOT_RUN`.
- Full `lb build` for the current dirty tree and final manifest/image inspection: `IN PROGRESS` only for the prior clean HEAD; current edits are not included in that run.
- Latest BIOS/UEFI and graphical acceptance for the new package manifest: `NOT_RUN`.
- Six independent application windows at 6GB/5GB, CPU load responsiveness and latency percentiles: `NOT_RUN`.
- Persistence reboot, physical hardware network/audio/Bluetooth/printer tests, installer-to-disk, and package transactions against a disposable VM: `NOT_RUN`.
- No physical disk was written.

## Scope Statement

The new audit files inventory every path tracked at the starting snapshot and trace critical build, desktop, package, vault, keyboard and systemd paths. The source tree and CI evidence do not support a claim that every UI button, application, physical device, or performance target is fully accepted. Continue by building/testing the exact final commit and execute the listed `NOT_RUN` acceptance cases before calling ISO-X daily-use ready.