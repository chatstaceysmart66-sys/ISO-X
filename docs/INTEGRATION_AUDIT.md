# ISO-X 0.4.0 Integration Audit

## Snapshot and Scope

- Reviewed branch: `fix/isox-build-and-runtime`
- Reviewed source commit: `75eae94d8fdeaac8d9f1df30f0b47dcbe9787a21`
- Tracked files at review: 128
- Working tree before this audit: clean
- Latest completed workflow at this update: [run 40210339242](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/40210339242), commit `75eae94`
- Scope here is an integration trace of the build-to-desktop path, the failing X11 acceptance check, and current CI evidence. This is not a claim that every UI control or supported hardware configuration has been runtime-tested.

## Prioritized Findings

| Priority | Finding | Evidence and disposition |
| --- | --- | --- |
| Medium, resolved | The native maximize-button acceptance check clicked the wrong titlebar position. Commit `93d7727` changed the offsets to 52/76 while `desktop/openbox-rc.xml` still specifies title layout `NLIMC`; CI then reported that `_NET_WM_STATE` never acquired `MAXIMIZED_VERT`. The previous values 28/52 passed in run `40131668103`. The test restores 28/52 and waits on observed X11 state. The full GTK/Openbox runtime test passed in run `40210339242`. | [Failing run](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/40204931307), [fixed run](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/40210339242), `tests/test_gtk_window_runtime.py`, `desktop/openbox-rc.xml` |

No other critical or high issue was confirmed in this bounded pass. Unreviewed features are not thereby considered defect-free.

## Integration Paths

### Source to Live Image

`scripts/build-iso.sh` validates the host, architecture, signing/watermark options, disk and memory constraints, and output collisions. It invokes `auto/config`, stages the package list, desktop configuration, Python entry points, assets, database schema/migrations, systemd units, and live hooks into the Live-Build config tree, then invokes `lb` to create the image. `config/package-lists/iso-x.list.chroot` declares runtime packages; numbered files under `config/hooks/live/` apply locale, watermark (optional), Plymouth, service, and browser defaults during image construction.

The staged GTK entry point is `app/iso_x_gtk.py`; Openbox's runtime configuration is staged from `desktop/openbox-rc.xml`. The desktop application is launched under the display-manager session, while Openbox owns decoration, maximize/minimize, focus, and resize behavior. Thus a successful button test must observe the managed X11 state, not merely the GTK process or synthetic click.

### GTK and Openbox Runtime Check

`tests/test_gtk_window_runtime.py` starts Openbox with the repository configuration, launches the GTK application, locates its X11 window, drives the titlebar and frame with `xdotool`/`wmctrl`, and reads geometry, focus, and `_NET_WM_STATE` with X11 tools. The source-check runner launches it under Xvfb at 1366x1024x24. Keyboard layout, GTK text input, terminal input, Alt+Tab, maximize/restore/minimize, pointer movement, eight resize zones, titlebar double-click, close, and modal-close paths are included in that test.

The reported failure was specifically the native maximize assertion, before later window gestures ran. The offset correction is based on the repository's Openbox title layout and the regression between previously passing and failing revisions. The corrected full test passed in CI, with the log stating that Openbox window controls, titlebar movement, all eight resize zones, Alt+Tab, and GTK/xterm Arabic-English input passed. This environment itself lacks Xvfb/Openbox tooling, so the interaction was not rerun locally.

### CI Build and Boot Acceptance

The workflow separates `source-check`, `build`, `bios`, and `uefi`. The BIOS and UEFI jobs depend on a validated, uploaded build candidate, not on the source-check job; the workflow's promotion gate requires source, build, BIOS, and UEFI success. The final workflow passed all those gates and then tested a normal-boot ISO candidate independently under BIOS and UEFI. Both normal-boot results report `desktop_seen=true`, `shutdown_reason=desktop_rendered`, and a valid final screenshot. The uploaded images remain CI candidates, not release artifacts. Persistence across reboot remains explicitly untested.

## Evidence at Reviewed Commit

From workflow run `40210339242` on commit `75eae94d8fdeaac8d9f1df30f0b47dcbe9787a21`:

- Build job: `PASS`.
- BIOS job: `PASS`.
- UEFI job: `PASS`.
- Source checks: `PASS`; 67 passed, 0 failed, 0 skipped, 0 not run. GTK runtime log confirms native controls, titlebar movement, eight resize zones, and focus switching.
- Promotion: `PASS`; both normal-boot BIOS and UEFI runs reported `PASS_BOOT`, `desktop_seen=true`, `shutdown_reason=desktop_rendered`, and `final_screenshot_valid=true`.
- Diagnostic CI image size: `2,623,733,760` bytes. SHA-256: `b234d0073afb11dc889d7108c3a60a3f0db971a111e8eb75afc064e69ee8a343`. Source commit: `75eae94d8fdeaac8d9f1df30f0b47dcbe9787a21`. This is a CI diagnostic artifact, not a release ISO.
- The BIOS/UEFI headless boot-gate jobs report `desktop_seen=false`; they prove their configured readiness marker, not graphical acceptance. The separate normal-boot promotion tests provide the graphical evidence above.
- Local GTK runtime, BIOS/UEFI, graphical-session, and persistence tests: `NOT TESTED` in this Ubuntu Noble dev container. GTK runtime prerequisites (`xvfb-run`, `openbox`, `xdotool`, `wmctrl`) and `sfdisk` are absent.
- Local source runner: 20 checks passed; pytest returned `FAIL` because this Python environment has no `pytest` module; four checks were `NOT_RUN` (`sfdisk`, X11 runtime tools, ShellCheck, and `desktop-file-validate`). XML/SVG validation, shell syntax, workflow contracts, smoke checks, and the QEMU fake-validation passed.

The source-check artifact from the failing pre-fix run `40204931307` recorded “native maximize button did not maximize the ISO-X window.” The fixed run `40210339242` records the GTK runtime check as `PASS`. Evidence artifacts, including `results.json` and QEMU logs/screenshots, are available from the linked workflow; local downloads under `/tmp/isox-ci-*` are analysis copies, not repository deliverables.

## Changed Files and Revalidation

- `tests/test_gtk_window_runtime.py`: restore titlebar offsets and replace fixed post-click delay/immediate checks with bounded polling of the actual `_NET_WM_STATE` value.
- CI artifact evidence reviewed: `results.json`, source-test manifest/logs, build ISO SHA-256 and size files, and separate BIOS/UEFI evidence from run `40210339242`. The uploaded workflow artifacts include screenshots and logs.
- Code fix commit: `849537de4b4eaf662d17241c37c00907e026fedb`; final documentation commit: `75eae94d8fdeaac8d9f1df30f0b47dcbe9787a21`. The remote branch matches the latter and its workflow completed successfully.
- Persistence reboot acceptance remains `NOT RUN`; partition creation alone is not treated as proof.