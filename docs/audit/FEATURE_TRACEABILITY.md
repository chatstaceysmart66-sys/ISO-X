# Feature Traceability

Status at audit time: working tree includes local changes not present in HEAD `22b9fc1`; CI run `40216891064` source-check passed on HEAD and image build was in progress. `PASS` below means the named test ran, not blanket feature acceptance.

| Feature | UI/event -> handler/service -> effect | State | Evidence and remaining boundary |
|---|---|---|---|
| Native window close/minimize/maximize | Openbox decoration -> mouse context action -> ICCCM/EWMH operation on target window | `IMPLEMENTED_AND_TESTED` | `tests/test_gtk_window_runtime.py` passed in CI `40210339242`; actual current user image awaits build. |
| Move and resize | Openbox titlebar/frame/corner bindings -> Move/Resize action | `IMPLEMENTED_AND_TESTED` | Same CI runtime test checks movement and all eight resize zones; cursor shape not separately asserted. |
| Alt+Tab and input routing | Openbox A-Tab/A-S-Tab -> active-window focus -> GTK/xterm probes | `IMPLEMENTED_AND_TESTED` | CI test verifies two GTK windows and directed text input; six independent application windows not tested. |
| ISO-X UI buttons | GTK `clicked` callbacks -> GTK methods or launch helpers | `IMPLEMENTED_UNVERIFIED` | Source paths inspected; no exhaustive UI automation of every button. |
| Desktop icon launch by single click | PCManFM -> libfm config -> desktop entry Exec | `IMPLEMENTED_UNVERIFIED` | Config test verifies `single_click=1`; no real touchscreen interaction. |
| Openbox right-click menu contrast | Openbox theme `themerc` -> menu rendering | `IMPLEMENTED_UNVERIFIED` | Hook applied to Debian Clearlooks theme extracted from package; actual image render is pending. |
| Snap active window | Openbox Super+Left/Right -> script -> xrandr/wmctrl | `PARTIAL` | Script exists and is staged, but manifest lacked xrandr provider. Added `x11-xserver-utils` locally with contract assertion; new ISO not built yet. |
| Secure Vault from menu | Openbox -> xterm -> wrapper -> Python interactive prompt -> encrypt/decrypt | `BROKEN` at baseline; `IMPLEMENTED_UNVERIFIED` after local fix | Baseline no-args call returned exit 2/usage. New path selection and actual encrypt/decrypt roundtrip pass. A real TTY menu session has not been run. |
| App Center catalog | Search/filter -> worker -> AppStream/DEP-11, apt-cache and dpkg-query -> GTK cards | `IMPLEMENTED_UNVERIFIED` | 16 backend tests pass with injected runner; actual live repo/catalog availability not proven. |
| APT install/remove | Card action -> confirmation -> worker -> candidate/state revalidation -> `pkexec apt-get` -> state recheck | `PARTIAL` | Backend tests validate fixed argv and errors; `pkexec` was missing from image manifest. Added package and source contract locally; real polkit flow not tested. |
| Flatpak operations | Card action -> remote/app/architecture validation -> user-scoped `flatpak` command | `IMPLEMENTED_UNVERIFIED` | Fake-runner tests cover identity/remote; no real Flathub operation. |
| Store updates | Update button -> backend `apt-get -s upgrade` and user remotes -> errors shown instead of “no updates” | `IMPLEMENTED_UNVERIFIED` | Backend tests cover DNS failure as failure; real update check not run. |
| Arabic/English XKB | GTK/tint2 callback -> XKB group read/change -> current group validation | `IMPLEMENTED_AND_TESTED` | GTK CI test typed Arabic and English in GTK and xterm. |
| GTK file copy/move/delete | Toolbar -> selection/path checks -> confirmation -> worker -> completion callback | `IMPLEMENTED_UNVERIFIED` | Source has checks and worker; destructive/edge filesystem cases not fully runtime-tested. |
| USB image validation/write | CLI -> ISO/hash/target checks -> explicit WIPE confirmation -> dd | `PARTIAL` | Validation tests passed without physical disk writes; persistence-partition test requires `sfdisk`; reboot persistence remains `NOT_RUN`. |
| BIOS/UEFI and graphical session | Build -> candidate -> independent firmware jobs -> normal-boot desktop gates | `PASS` on earlier commit; current audit tree `IN_PROGRESS` | Run `40210339242` passed source/build/BIOS/UEFI and normal-boot `desktop_seen=true`; current changes are not that run. |
| Six-window 5/6GB performance | Six independent apps -> focus/input/load -> response/resource metrics | `NOT_RUN` | No current test or measurements found in this audit. |
| CPU multicore under load | Controlled parallel stress -> focus/input latency and per-CPU metrics | `NOT_RUN` | `lscpu` alone is not evidence; no test executed. |
| Secure Boot enrollment | `secureboot-enroll.sh` only validates matching key/cert | `NOT_IMPLEMENTED` | It does not enroll MOK or prove signed boot; tests are fixtures only. |