# ISO-X 0.4.0 — Debian Trixie Live system

ISO-X is a source project for a lightweight, Arabic-first desktop live system targeting **amd64**. It uses Debian Live Build, Openbox, GTK applications, NetworkManager, PipeWire/WirePlumber, Firefox ESR, and ISO-X branding. The included source can configure and build an image; it is **not itself a verified or prebuilt ISO**. See [AUDIT.md](AUDIT.md) for executed checks and known blockers, and [README_AR.md](README_AR.md) for the Arabic guide.

## One-command build

On a Debian 13 (Trixie) amd64 build host with the required packages, stable Rust toolchain, at least 20 GiB free disk, at least 4 GiB RAM, and a release key/certificate stored **outside this source tree**:

```bash
./scripts/install-build-deps.sh
./scripts/generate-dev-signing-key.sh "$HOME/.local/share/isox-signing"
export ISOX_RELEASE_KEY="$HOME/.local/share/isox-signing/isox-release.key"
export ISOX_RELEASE_CERT="$HOME/.local/share/isox-signing/isox-release.crt"
sudo --preserve-env=ISOX_RELEASE_KEY,ISOX_RELEASE_CERT ./build.sh
```

The development key above is only for test builds; it does not establish trust on a machine with Secure Boot enabled. `build.sh` does not bypass the safety checks in `scripts/build-iso.sh`. Expected output: `ISO-X-0.4.0-live-amd64.iso` plus a `.sha256` file, **only after a successful build**.

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

Static source tests do not prove the desktop works at runtime. Test BIOS/UEFI boot, networking, audio, browser rendering, settings, shutdown, restart and installation in a disposable VM before installing to real hardware. Record actual results in `AUDIT.md`; never infer success from a source-only test.

## Upstream references and licensing

The project reviewed [Debian Live Config](https://github.com/nodiscc/debian-live-config) and [OxyOS](https://github.com/OxyHQ/OxyOS) as references. The former publishes a GPL-3.0 license; the main OxyOS repository did not expose a license file or SPDX license in the repository metadata reviewed for this audit. No OxyOS code or assets are bundled from that unlicensed main repository. See [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Existing package copyright notices must be retained in any redistributed ISO.
