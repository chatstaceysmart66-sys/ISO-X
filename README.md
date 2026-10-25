# ISO-X 0.4.0 — Debian Trixie Live system

ISO-X is a source project for a lightweight, Arabic-first desktop live system targeting **amd64**. It uses Debian Live Build, Openbox, GTK applications, NetworkManager, PipeWire/WirePlumber, Firefox ESR, and ISO-X branding. The included source can configure and build an image; it is **not itself a verified or prebuilt ISO**. See [AUDIT.md](AUDIT.md) for executed checks and known blockers, and [README_AR.md](README_AR.md) for the Arabic guide.

## One-command build

On a Debian 13 (Trixie) amd64 build host with the required packages, at least 20 GiB free disk and at least 4 GiB RAM:

```bash
./scripts/install-build-deps.sh
sudo ./build.sh
```

The default image does not build or include the optional watermark kernel module, so no release key or Rust toolchain is required. `ISOX_ENABLE_WATERMARK=1` opts into the separately signed watermark feature and requires `ISOX_RELEASE_KEY` and `ISOX_RELEASE_CERT` from outside the repository. `ISOX_BUILD_CINEMATIC=1` separately opts into the optional Bevy scene and requires a compatible Rust toolchain and network/cache access to its crates. Neither option is part of the default desktop or boot path. The build script rejects an existing non-empty build directory rather than deleting it. A successful run prints the output ISO path and SHA-256; this source checkout has not yet produced a verified ISO.

The USB writer requires the generated sidecar `${ISO}.sha256`, validates it and the ISO structure, checks that the selected whole USB disk is large enough, then requires the exact confirmation `WIPE <disk-name>`. This overwrites the selected device. Review the device model and data before confirming:

```bash
sudo /usr/local/sbin/isox-write-usb /path/to/ISO-X-0.4.0-live-amd64.iso
```

## Repository layout

- `auto/`, `config/`: live-build configuration, package list and chroot hooks.
- `app/`, `desktop/`, `assets/`, `plymouth/`: desktop launchers, Openbox setup and ISO-X artwork.
- `db/`: SQLite schema and ordered migrations.
- `kernel/`, `initramfs/`, `security/`, `scripts/`, `systemd/`: watermark module, initramfs integration, secure vault, build and system helpers.
- `three-d-login/`: optional Bevy-based startup scene; it is not the login/authentication boundary.
- `tests/`, `evidence/`, `docs/`: static checks, recorded evidence, acceptance plan, real-hardware checklist and reports. Start with [the real hardware acceptance checklist](docs/HARDWARE_ACCEPTANCE_CHECKLIST_AR.md).

## Testing

```bash
bash tests/smoke.sh
python3 -m pytest -q
bash tests/qemu-acceptance.sh check
```

The smoke script runs the source-level checks without requiring pytest. Static source tests do not prove the desktop works at runtime. Test BIOS/UEFI boot, networking, audio, browser rendering, settings, shutdown, restart and installation in a disposable VM before installing to real hardware. Record actual results in `AUDIT.md`; never infer success from a source-only test. See [the latest build and test record](docs/BUILD_AND_TEST_RESULTS_AR.md).

## Upstream references and licensing

The project reviewed [Debian Live Config](https://github.com/nodiscc/debian-live-config) and [OxyOS](https://github.com/OxyHQ/OxyOS) as references. The former publishes a GPL-3.0 license; the main OxyOS repository did not expose a license file or SPDX license in the repository metadata reviewed for this audit. No OxyOS code or assets are bundled from that unlicensed main repository. See [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Existing package copyright notices must be retained in any redistributed ISO.
