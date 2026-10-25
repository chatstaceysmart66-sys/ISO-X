# Integration Test Matrix

This matrix distinguishes local run status from prior/current CI evidence. The full local source runner was executed against the dirty audit tree; artifacts are under `/tmp/isox-audit-source-checks-final/`. Local required tools are incomplete, so the runner exits nonzero when any required tool is `NOT_RUN`.

| Chain / command | What it checks and how | Status | Limit |
|---|---|---|---|
| `python3 -m compileall -q app scripts tests` | Python syntax in source directories. | `PASS`, exit 0 | Does not resolve runtime-only imports. |
| `python3 -m pytest -p no:cacheprovider -q` | 48 tests, 47 passed, 1 skipped, 0 failures. | `PASS` test execution | pytest installed into `/tmp/isox-audit-pytest`; one skip is recorded in `pytest.xml`. |
| `bash tests/smoke.sh` | Combined smoke path. | `PASS`, exit 0 | Explicitly not ISO build/boot acceptance. |
| `python3 tests/test_build_contracts.py` | Build staging, hooks, package and workflow contracts; includes Secure Vault interactive dispatch and theme hook temp-root test. | `PASS`, exit 0 | Static/fixture contracts. |
| `python3 tests/test_source_config.py` | Source config, package presence, launcher and assets contracts; now asserts `pkexec` and `x11-xserver-utils`. | `PASS`, exit 0 | Does not inspect built rootfs. |
| `python3 tests/test_secure_vault.py` | Actual OpenSSL archive encryption/decryption, wrong key, tamper, safe extraction, plus menu route. | `PASS`, exit 0 | Interactive actual TTY invocation was not run. |
| `python3 tests/test_store_backend.py` | 16 backend tests for parser, argv, candidate validation, source scope, errors. | `PASS`, exit 0 | Uses injected fake runner; no apt/network/polkit transaction. |
| `python3 tests/test_schema.py` | SQLite schema. | `PASS`, exit 0 | Does not test every production migration path. |
| `python3 tests/test_upstream_integration.py` | Upstream and source boundary. | `PASS`, exit 0 | Static. |
| `bash tests/test_write_usb_validation.sh` | Hash/ISO validation before writing. | `PASS`, exit 0 | No physical media touched. |
| `bash tests/test_write_usb_persistence.sh` | Persistence partition logic on disposable test input. | `NOT_RUN` | `sfdisk` missing locally. |
| `bash tests/test_qemu_headless_validation.sh` | Fake QEMU/QMP failure detection and exit classification. | `PASS`, exit 0 | Not a real VM boot. |
| `bash tests/test_desktop_readiness.sh` | Readiness script behavior with fake process/window tools. | `PASS`, exit 0 | Not a live LightDM/Openbox session. |
| `xvfb-run ... tests/test_gtk_window_runtime.py` | Native controls, pointer movement, 8 resize zones, focus, keyboard/input. | `NOT_RUN` locally; `PASS` in prior CI run `40210339242` | Local lacks xvfb-run, xdotool, wmctrl, Openbox. Prior pass predates this audit's package/Vault changes. |
| `bash tests/test_secureboot_validation.sh` | Key/cert validation fixtures. | `PASS`, exit 0 | Not Secure Boot firmware enrollment. |
| `bash tests/test_initramfs_watermark_guard.sh` | Guard behavior with synthetic initramfs root. | `PASS`, exit 0 | Not a real signed module/boot. |
| `bash tests/test_watermark_integrity.sh` | Detached-signature fixture. | `PASS`, exit 0 | Not kernel module signature in an ISO. |
| `python3 tests/test_workflow_contracts.py` | Workflow job dependencies and gates. | `PASS` in focused local run | Static contract only. |
| `python3 tests/test_ci_results.py` | CI JSON handling. | `PASS`, exit 0 | Does not prove Actions execution. |
| Bash/sh syntax and `xmllint` XML/SVG | Syntax checks. | `PASS`, exit 0 | Does not prove rendering. |
| ShellCheck | Shell diagnostics. | `NOT_RUN` locally | Binary missing; CI source-check installs it. |
| `desktop-file-validate desktop/*.desktop` | Desktop entry syntax. | `NOT_RUN` locally | Tool missing; CI source-check installs it. |
| `git diff --check` | Patch whitespace. | `PASS`, exit 0 | Not behavior validation. |
| Debian Clearlooks hook smoke | Applies menu theme changes to actual package theme under `/tmp`; checks idempotence. | `PASS` | Does not load Openbox or render pixels. |
| GitHub `source-check` run `40216891064` | Current HEAD `22b9fc1`, source checks. | `PASS` | Does not include local edits made after that HEAD. |
| GitHub `build` run `40216891064` | Trixie ISO build and validation. | `IN PROGRESS` at last observation | Do not claim final build until completed. |
| BIOS/UEFI + desktop in run `40210339242` | Earlier source commit `75eae94`; normal-boot QEMU desktop detection. | `PASS` for that commit | Not the current audit changes/HEAD. |
| Six windows 6GB/5GB CPU/load profile | Independent apps, focus/input latencies and resource data. | `NOT_RUN` | No workload harness or measurements executed. |

### Current local aggregate

Runner manifest: 67 passed, 0 failed, 1 skipped, 4 not run; process exit 1 because missing required tools are a gate. The four unavailable checks are persistence-partition (`sfdisk`), GTK runtime (`xvfb-run`, `xdotool`, `wmctrl`, `openbox`), ShellCheck, and desktop-file validation. pytest itself passed after installation under `/tmp`.