# ISO-X File Inventory

## Snapshot

- Repository: `chatstaceysmart66-sys/ISO-X`
- Branch and HEAD at audit start: `fix/isox-build-and-runtime`, `22b9fc116ee278be22c5bbe30782f980100d85a1`
- `git status --short --branch`: clean before this audit's edits.
- Tracked paths at snapshot: 130. Ignored Python bytecode existed from prior test execution and is not source.
- Build/test processes at snapshot: none locally. GitHub run `40216891064` had `source-check=success`, `build=in_progress`.
- Inventory is path-complete for the Git snapshot; roles and integration evidence are based on source inspection and listed tests, not proof that each path executed in the ISO.

## Root, Workflow, Application Sources

| Path | Actual role and integration | Verification boundary |
|---|---|---|
| `.github/workflows/iso-build.yml` | Source checks, build, BIOS, UEFI, promotion and artifacts. | CI evidence for run `40216891064`; build was still running when first inspected. |
| `.gitignore` | Excludes build outputs, ISO artifacts, keys, caches and evidence. | Git status; not runtime. |
| `AUDIT.md` | Historical audit log. | Contains older snapshots; not current state authority. |
| `CHANGELOG.md` | Historical changes. | Documentation only. |
| `LICENSE.txt` | Project license/permission notice. | Does not replace third-party notices. |
| `README.md` | English build/use overview; selected copy is staged to `/usr/share/doc/iso-x`. | Static documentation. |
| `README_AR.md` | Arabic build/use overview; selected copy is staged. | Static documentation. |
| `STATUS_AR.md` | Older project status. | Historical, not current acceptance evidence. |
| `THIRD_PARTY_NOTICES.md` | Attribution and upstream boundary; staged to ISO docs. | Static documentation. |
| `app/iso_x_gtk.py` | Main GTK3 shell; file manager, editor, terminal, settings, search and launch callbacks; staged and launched by Openbox autostart. | GTK/Xvfb CI runtime covers window controls/input; other features have focused source/unit tests, not all ISO runtime-tested. |
| `app/iso_x_shell.py` | Legacy Tk shell. | Not staged by the current build; not a runtime component. |
| `app/isox_appcenter.py` | GTK app center, callbacks, background catalog/package operations and result display; staged under `/usr/share/iso-x`. | `tests/test_store_backend.py` covers backend operations with a fake runner; actual package operations require a VM. |
| `app/isox_keyboard.py` | Reads XKB group via libX11 and changes layout using `setxkbmap`; used by GTK and tint2 helper. | GTK/Xvfb test exercises actual AR/EN input in CI. |
| `app/isox_store_backend.py` | AppStream/DEP-11 discovery, package state, APT/Flatpak operations and launch requests. | Backend tests cover parsing, argv safety and simulated failures; not an actual network repository install. |
| `app/isox_welcome.py` | GTK first-run launcher and installer confirmation; app commands are argv lists. | Static source contract; runtime buttons not all exercised in CI. |
| `build.sh` | Small user entry point delegating to `scripts/build-iso.sh`. | Build-contract tests; actual build delegated to CI. |

## Assets and Build Configuration

| Path | Actual role and integration | Verification boundary |
|---|---|---|
| `assets/iso-x-boot.png` | Raster boot artwork, staged. | Binary; dimensions/type can be inspected, no claim of hardware rendering. |
| `assets/iso-x-boot.svg` | Vector boot artwork, staged. | XML parser in source checks. |
| `assets/iso-x-desktop-wallpaper.png` | Desktop/greeter background, staged. | Binary; CI screenshot is evidence of desktop rendering, not every resolution. |
| `assets/iso-x-desktop-wallpaper.svg` | Vector source wallpaper, staged but profile selects PNG. | XML parser; runtime use not proven. |
| `assets/iso-x-dragon.png` | GTK/greeter logo, staged. | Binary; rendering is screenshot-level only. |
| `assets/iso-x-dragon.svg` | App icon and scalable icon, staged. | XML parser. |
| `assets/iso-x-plymouth.png` | Plymouth logo, copied into theme. | Binary; Plymouth appearance not independently asserted. |
| `assets/iso-x-start.html` | Local Firefox start page, staged and referenced by Firefox hook. | `tests/test_build_contracts.py` verifies source linkage; browser rendering is not covered. |
| `assets/sounds/download-complete.wav` | Store completion sound. | Generator-vs-asset checks in `test_store_backend.py`; actual audio device not tested. |
| `assets/sounds/error.wav` | Store error sound. | Same sound integrity test; no hardware audio proof. |
| `assets/sounds/notification.wav` | Store notification sound. | Same sound integrity test. |
| `assets/sounds/success.wav` | Store success sound. | Same sound integrity test. |
| `assets/sounds/warning.wav` | Store warning sound. | Same sound integrity test. |
| `auto/config` | Live-Build Trixie amd64, hybrid BIOS/UEFI config; CI flags add diagnostic boot args. | Build/source contracts and CI build, not a guarantee for hardware. |
| `config/bootloaders/grub-pc/grub.cfg` | GRUB live menu template consumed by the build. | Build contracts and ISO structure validation. |
| `config/bootloaders/isolinux/isolinux.cfg` | BIOS menu template. | Build contracts and ISO structure validation. |
| `config/bootloaders/syslinux_common/live.cfg.in` | Live and persistence Syslinux menu template. | Build contracts; persistence reboot not accepted. |
| `config/hooks/live/0050-isox-locales.hook.chroot` | Generates Arabic/English locales. | Shell syntax and Trixie build. |
| `config/hooks/live/0100-isox-watermark.hook.chroot` | Optional signed watermark module hook; only staged when enabled. | Fixture integrity tests; optional real module build not performed. |
| `config/hooks/live/0200-isox-plymouth.hook.chroot` | Installs/selects Plymouth theme. | Shell syntax and CI image build; splash rendering not separately tested. |
| `config/hooks/live/0300-isox-services.hook.chroot` | NetworkManager, LightDM/autologin, Bluetooth/CUPS configuration. | CI build and desktop readiness, not all hardware services. |
| `config/hooks/live/0400-isox-firefox-defaults.hook.chroot` | Idempotent local Firefox homepage prefs. | Temporary-root hook tests. |
| `config/hooks/live/0500-isox-menu-contrast.hook.chroot` | Makes Clearlooks menu base black and text white at build time. | Applied to an extracted Debian Clearlooks theme and idempotence-tested; inclusion in the currently building image was pending at snapshot. |
| `config/package-lists/iso-x.list.chroot` | Runtime package manifest. | Build resolves it in Trixie; this audit found missing `x11-xserver-utils` and `pkexec`, added locally after snapshot, awaiting build. |

## Data, Desktop, Documentation, Kernel and Initramfs

| Path | Actual role and integration | Verification boundary |
|---|---|---|
| `db/migrations/002_isox_020.sql` | Upgrade migration, staged and applied by GTK Store. | Schema tests; not all historical DB states. |
| `db/migrations/003_isox_031.sql` | 0.3.1 migration, staged. | Source/build contracts. |
| `db/migrations/004_isox_040.sql` | 0.4.0 marker migration, staged. | Source/build contracts. |
| `db/schema.sql` | SQLite schema used by GTK shell. | `tests/test_schema.py`; not all application CRUD. |
| `desktop/isox-store.desktop` | Store launcher. | Desktop validator in CI; runtime launched through menus. |
| `desktop/isox-welcome.desktop` | Welcome launcher. | Desktop validator and source config. |
| `desktop/openbox-menu.xml` | Openbox root menu; commands map to installed packages/scripts. | XML and source contracts; Vault menu path was found broken and fixed locally. |
| `desktop/openbox-rc.xml` | Openbox theme, native controls, mouse resize/move, key bindings and session config. | XML/source contracts and GTK/Openbox Xvfb test. |
| `desktop/tint2rc` | Panel, task list, launcher, tray and clock. | Source contracts; real panel interaction covered only by full desktop tests where available. |
| `docs/ARCHITECTURE_AR.md` | Architecture explanation. | Documentation, some portions historical. |
| `docs/ARTWORK_REFRESH_2026-10_AR.md` | Artwork history. | Documentation only. |
| `docs/BUILD_AND_CONTINUE_AR.md` | Build continuation guide. | Documentation may age; compare to current build script. |
| `docs/BUILD_AND_TEST_RESULTS_AR.md` | Historical build/test report. | Not current CI evidence. |
| `docs/FILE_INVENTORY_AR.md` | Older detailed inventory. | Stale counts/HEAD; superseded by this snapshot inventory. |
| `docs/GAP_ANALYSIS_0.2.0_AR.md` | Historical 0.2 gap analysis. | Not current 0.4 acceptance. |
| `docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md` | Hardware test checklist. | Checklist, not completed device evidence. |
| `docs/INTEGRATION_AUDIT.md` | Window/build integration review. | Contains valid earlier CI evidence; this audit records newer defects and repairs. |
| `docs/PROJECT_MAP_AR.md` | Older architecture map. | Stale snapshots; not current path inventory. |
| `docs/QEMU_ACCEPTANCE_AR.md` | QEMU test guidance. | Documentation only. |
| `docs/RELEASE_NOTES_0.3.0_AR.md` | Historical release notes. | Not current 0.4 proof. |
| `docs/ROADMAP_AR.md` | Roadmap. | Planned items are not implemented-state evidence. |
| `docs/RUNTIME_REPAIR_0.4.0_AR.md` | Earlier runtime repair notes. | Historical. |
| `docs/THIRD_PARTY_LICENSES.md` | Dependency/upstream licensing notes. | Not a generated license inventory for the built ISO. |
| `docs/UPSTREAM_INTEGRATION_AR.md` | Upstream integration boundary. | Documentation. |
| `docs/UPSTREAM_REVIEW_AR.md` | Upstream review. | Documentation. |
| `docs/WORKLOG_AR.md` | Historical work log. | Must not be read as current CI status. |
| `docs/previews/isox-welcome-design-preview.png` | Design preview, not runtime asset. | Binary preview only. |
| `initramfs/hooks/isox-watermark` | Optional initramfs inclusion hook. | Guard test covers synthetic behavior; optional module path not built. |
| `initramfs/scripts/init-premount/isox-watermark-guard` | Optional signature/hash guard; continues boot after warning. | `test_initramfs_watermark_guard.sh`; not actual signed guest module. |
| `kernel/isox-watermark/Makefile` | Builds optional kernel module. | No real module build in this audit. |
| `kernel/isox-watermark/dkms.conf` | DKMS metadata; not staged by the current build path. | No runtime consumer found in traced ISO build. |
| `kernel/isox-watermark/isox_watermark.c` | Optional attribution module. | Static/source tests; not a security boundary. |
| `kernel/isox-watermark/watermark_bytes.h` | Generated/committed C byte data used by module build. | Watermark tests; generation path is optional. |
| `plymouth/isox/isox.plymouth` | Plymouth theme declaration. | Source parse; visual splash not independently tested. |
| `plymouth/isox/isox.script` | Plymouth image/scene script. | Source parse; actual boot splash not independently asserted. |

## Scripts and Services

| Path | Actual role and integration | Verification boundary |
|---|---|---|
| `scripts/apply-windows-look.sh` | Creates GTK2/GTK3, libfm single-click, PCManFM and XDG user defaults under `/etc/skel`. | Executed on temp HOME; CI must confirm final image contains output. |
| `scripts/build-iso.sh` | Main guarded live-build staging/build/validation pipeline. | Trixie CI build; current run pending. |
| `scripts/ci-build-in-trixie.sh` | CI wrapper for build in Debian Trixie. | CI build job. |
| `scripts/collect-performance.sh` | Manual host/system performance collector. | Not part of image build; hardware execution not performed. |
| `scripts/create-ci-results.py` | Generates structured acceptance metadata. | `tests/test_ci_results.py`; reports only actual supplied inputs. |
| `scripts/create-user-iso-metadata.py` | Validates normal-boot candidate metadata. | CI workflow contract; current user ISO build status in Actions. |
| `scripts/create-user-iso.py` | Strips CI boot arguments and rebuilds normal-boot candidate. | Fixture tests and CI promotion. |
| `scripts/encode-watermark.py` | Generates optional C watermark bytes. | Contract test directs output to temp. |
| `scripts/generate-dev-signing-key.sh` | Manual development key generator, never an ISO runtime tool. | Not executed; creates secrets if run. |
| `scripts/generate-store-sounds.py` | Deterministic WAV generator; output checked against assets. | `tests/test_store_backend.py`. |
| `scripts/install-build-deps.sh` | Installs build dependencies on build host. | Not run in this audit. |
| `scripts/isox-ci-ready.sh` | CI-only guest readiness probe. | Desktop readiness tests; only staged in CI diagnostic image. |
| `scripts/isox-desktop-window-ready.sh` | Checks live ISO-X process/window geometry. | Shell fake tests; not an ISO by itself. |
| `scripts/isox-preload.py` | Opt-in executable-page cache warming. | Source only/unit boundary; not performance-tested. |
| `scripts/isox-run.py` | GTK command runner, argv-based. | Source/build contracts; arbitrary command launch is by current user. |
| `scripts/isox-snap-window.sh` | Uses xrandr+wmctrl for Super+Left/Right. | xrandr package was missing from manifest; package and contract added locally, awaiting build. |
| `scripts/isox-speedtest` | GTK/CLI network measurement using ping/curl. | No external network performance test in this audit. |
| `scripts/isox-zram-setup` | Creates zram swap and adjusts swappiness. | Not run on host/guest; service path staged. |
| `scripts/read-ci-nonce.sh` | Validates raw CI nonce. | Contract tests. |
| `scripts/record-demo.sh` | Manual X11 screen recording. | Not staged by current build; not tested. |
| `scripts/run-source-checks.py` | Runs source tests/validators and preserves logs/results. | Executed locally; reports unavailable tools as NOT_RUN and exits nonzero. |
| `scripts/secure-vault.py` | Encrypted archive CLI; interactive prompt now supports invocation without args. | Real OpenSSL roundtrip plus prompt-routing tests. |
| `scripts/secure-vault.sh` | Wrapper to staged or source Vault Python entry point. | Shell syntax; Openbox launches wrapper. |
| `scripts/secureboot-enroll.sh` | Validation helper, not MOK enrollment. | Fixture tests only. |
| `scripts/toggle-airplane.sh` | rfkill toggle with privilege escalation. | Validation/source tests; no radio hardware test. |
| `scripts/validate-iso-boot-config.sh` | Validates generated boot menus. | Fixture tests and CI build. |
| `scripts/write-usb.sh` | Validates/writes ISO and can create persistence partition. | Validation tests avoid real disks; persistence reboot acceptance not run. |
| `systemd/isox-ci-ready.service` | CI-only boot readiness service. | `systemd-analyze`/CI; only diagnostic image. |
| `systemd/isox-ci-ready.timer` | CI-only delayed readiness trigger. | Same. |
| `systemd/isox-preload.service` | Per-user optional one-shot cache warming. | Source/contract only; no usage/performance validation. |
| `systemd/isox-preload.timer` | Per-user delayed schedule. | Source/contract only. |
| `systemd/isox-zram.service` | System-level zram setup before display manager. | CI build; no measured guest behavior here. |

## Tests, QEMU and Optional Rust Scene

| Path | Actual role and integration | Verification boundary |
|---|---|---|
| `tests/ci-results.schema.json` | JSON report schema. | `test_ci_results.py`. |
| `tests/qemu-acceptance.sh` | Firmware-specific QEMU acceptance launcher. | Real CI QEMU plus fake tests. |
| `tests/qemu-runner.py` | QMP/serial/screenshot/guest-marker process runner. | Fake runner tests and CI guest evidence; not local QEMU here. |
| `tests/smoke.sh` | Fast combined smoke tests. | PASS locally; not ISO boot. |
| `tests/test_build_contracts.py` | Build, workflow, package, theme and staging regression tests. | 47 pass/1 skip under temporary pytest for current dirty tree. |
| `tests/test_ci_results.py` | Validates generated result behavior. | Full source suite. |
| `tests/test_desktop_readiness.sh` | Tests desktop readiness script with fakes. | PASS; not a live session. |
| `tests/test_gtk_window_runtime.py` | Real Openbox/Xvfb window controls, movement, resize, focus, XKB and text probes. | CI passed previously; locally NOT_RUN because X11 tools are absent. |
| `tests/test_initramfs_watermark_guard.sh` | Initramfs guard failure behavior. | PASS with synthetic root. |
| `tests/test_qemu_headless_validation.sh` | Fake QEMU/QMP failure-state handling. | PASS; not real boot. |
| `tests/test_schema.py` | SQLite schema invariants. | PASS; not all application queries. |
| `tests/test_secure_vault.py` | Archive crypto/restore and interactive path selection. | PASS OpenSSL roundtrip and tamper/wrong-secret checks. |
| `tests/test_secureboot_validation.sh` | Key/certificate fixture validation. | PASS; not firmware Secure Boot. |
| `tests/test_source_config.py` | Package/staging/config contracts. | PASS; static. |
| `tests/test_store_backend.py` | Discovery and package backend with injected runner. | 16 tests PASS; actual apt/Flatpak not invoked. |
| `tests/test_upstream_integration.py` | Source/docs integration contracts. | PASS; static. |
| `tests/test_user_iso.py` | Rewrites a fixture ISO. | CI/fixture tests; not the current output unless workflow proves. |
| `tests/test_watermark_integrity.sh` | Detached signature fixture behavior. | PASS; no Linux kernel module build. |
| `tests/test_workflow_contracts.py` | Static CI gating assertions. | PASS; not Actions execution. |
| `tests/test_write_usb_persistence.sh` | Partition creation on fixture/disk image. | NOT_RUN locally (`sfdisk` missing); persistence reboot remains unproven. |
| `tests/test_write_usb_validation.sh` | ISO validation before writer. | PASS; never writes a physical user disk. |
| `three-d-login/Cargo.toml` | Optional Bevy dependency manifest. | Not part of default ISO; no cargo build in this audit. |
| `three-d-login/src/main.rs` | Optional visual scene; not the login/authentication implementation. | Not built or runtime-tested. |

## Untracked/Generated Files

- Ignored `tests/__pycache__/test_gtk_window_runtime.cpython-314.pyc` was present at the initial snapshot; it is generated and not tracked.
- CI results and logs were written to `/tmp/isox-audit-source-checks-final/`; pytest was installed under `/tmp/isox-audit-pytest/`. Neither is a project source file or an ISO artifact.
- The complete tracked-path list above reflects HEAD at audit start. This report and other `docs/audit/` records are new files created by this audit and are not part of the original 130-path count.