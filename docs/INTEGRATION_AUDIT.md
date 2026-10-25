# ISO-X 0.4.0 Integration Audit

## Snapshot and Scope

- Reviewed branch: `fix/isox-build-and-runtime`
- Reviewed source commit: `ca0ef3afa0f712ed57e60a3610a00b2eb2d31d4c`
- Tracked files at review: 128
- Working tree before this audit: clean
- Latest observed workflow: [run 40204931307](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/40204931307), commit `ca0ef3a`
- Scope here is an integration trace of the build-to-desktop path, the failing X11 acceptance check, and current CI evidence. This is not a claim that every UI control or supported hardware configuration has been runtime-tested.

## Prioritized Findings

| Priority | Finding | Evidence and disposition |
| --- | --- | --- |
| Medium | The native maximize-button acceptance check clicked the wrong titlebar position. Commit `93d7727` changed the offsets to 52/76 while `desktop/openbox-rc.xml` still specifies title layout `NLIMC`; CI then reported that `_NET_WM_STATE` never acquired `MAXIMIZED_VERT`. The previous values 28/52 passed this exact runtime test in workflow run `40131668103`. The test now restores 28/52 and waits on observed X11 state instead of a fixed sleep. Runtime revalidation after this change is pending. | [Failing run](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/40204931307), [last passing run](https://github.com/chatstaceysmart66-sys/ISO-X/actions/runs/40131668103), `tests/test_gtk_window_runtime.py`, `desktop/openbox-rc.xml` |

No other critical or high issue was confirmed in this bounded pass. Unreviewed features are not thereby considered defect-free.

## Integration Paths

### Source to Live Image

`scripts/build-iso.sh` validates the host, architecture, signing/watermark options, disk and memory constraints, and output collisions. It invokes `auto/config`, stages the package list, desktop configuration, Python entry points, assets, database schema/migrations, systemd units, and live hooks into the Live-Build config tree, then invokes `lb` to create the image. `config/package-lists/iso-x.list.chroot` declares runtime packages; numbered files under `config/hooks/live/` apply locale, watermark (optional), Plymouth, service, and browser defaults during image construction.

The staged GTK entry point is `app/iso_x_gtk.py`; Openbox's runtime configuration is staged from `desktop/openbox-rc.xml`. The desktop application is launched under the display-manager session, while Openbox owns decoration, maximize/minimize, focus, and resize behavior. Thus a successful button test must observe the managed X11 state, not merely the GTK process or synthetic click.

### GTK and Openbox Runtime Check

`tests/test_gtk_window_runtime.py` starts Openbox with the repository configuration, launches the GTK application, locates its X11 window, drives the titlebar and frame with `xdotool`/`wmctrl`, and reads geometry, focus, and `_NET_WM_STATE` with X11 tools. The source-check runner launches it under Xvfb at 1366x1024x24. Keyboard layout, GTK text input, terminal input, Alt+Tab, maximize/restore/minimize, pointer movement, eight resize zones, titlebar double-click, close, and modal-close paths are included in that test.

The reported failure was specifically the native maximize assertion, before later window gestures ran. The offset correction is based on the repository's Openbox title layout and the regression between previously passing and failing revisions. The current environment lacks Xvfb/Openbox tooling, so this edit cannot be behaviorally confirmed locally.

### CI Build and Boot Acceptance

The workflow separates `source-check`, `build`, `bios`, and `uefi`. The BIOS and UEFI jobs depend on a validated, uploaded build candidate, not on the source-check job; the workflow's promotion gate does require source, build, BIOS, and UEFI success. The build artifact is explicitly a CI boot-diagnostic variant, not a release ISO. `scripts/qemu-runner.py` and `tests/qemu-acceptance.sh` produce per-firmware acceptance evidence; actual persistence across reboot is explicitly not claimed by candidate metadata.

## Evidence at Reviewed Commit

From workflow run `40204931307`:

- Build job: `PASS`.
- BIOS job: `PASS`.
- UEFI job: `PASS`.
- Source checks: `FAIL`; 66 passed, 1 failed, 0 skipped, 0 not run. The sole failure was `gtk-window-runtime`; the other recorded source checks passed.
- Acceptance summary: `PASS` for its reporting step; this does not override the failed source gate.
- Promotion: skipped because the source-check gate failed.
- A CI ISO candidate was built and used for the BIOS/UEFI jobs. It is a diagnostic candidate, not a release-ready ISO. Size and SHA-256 were not copied into this report.
- CI candidate size: `2,623,733,760` bytes. SHA-256: `d1ea83f5ef0d76cdd344c11f0794d8bdc7b550f0976aa12e086481b26be7d19b`. Source commit: `ca0ef3afa0f712ed57e60a3610a00b2eb2d31d4c`.
- BIOS and UEFI were headless boot tests using 1 GiB RAM and QEMU TCG. Both result files say `PASS_BOOT`, but also report `desktop_seen=false` and `graphical_target=false` among serial observations. These results prove the configured boot-readiness marker was reached, not that a graphical desktop was accepted.
- Local GTK runtime, BIOS/UEFI, graphical-session, and persistence tests: `NOT TESTED` in this Ubuntu Noble dev container. GTK runtime prerequisites (`xvfb-run`, `openbox`, `xdotool`, `wmctrl`) and `sfdisk` are absent.
- Local source runner: 20 checks passed; pytest returned `FAIL` because this Python environment has no `pytest` module; four checks were `NOT_RUN` (`sfdisk`, X11 runtime tools, ShellCheck, and `desktop-file-validate`). XML/SVG validation, shell syntax, workflow contracts, smoke checks, and the QEMU fake-validation passed.

The source-check artifact recorded `gtk-window-runtime` exit code 1 and the failing assertion: “native maximize button did not maximize the ISO-X window.” Evidence was downloaded for analysis to `/tmp/isox-ci-40204931307/`; that temporary copy is not a repository deliverable.

## Changed Files and Revalidation

- `tests/test_gtk_window_runtime.py`: restore titlebar offsets and replace fixed post-click delay/immediate checks with bounded polling of the actual `_NET_WM_STATE` value.
- CI artifact evidence reviewed: `results.json`, build ISO SHA-256 and size files, BIOS/UEFI result JSON and serial logs, and the source-check artifact from run `40204931307`. The artifacts remain available from the linked workflow run; downloaded analysis copies are under `/tmp/isox-ci-40204931307/`.
- The code changes above are currently uncommitted and have not yet been run through a new CI workflow.
- Required acceptance after the change: source-check's GTK job passes against a real Xvfb/Openbox session; BIOS and UEFI remain separate and pass on the candidate generated by that same commit. Do not infer successful persistence from partition creation alone.