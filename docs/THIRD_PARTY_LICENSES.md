# ISO-X third-party license and attribution register

**Scope:** this is the source-tree license register for ISO-X 0.4.0. It records the third-party sources identified during this review. It is not a substitute for the per-package copyright/license texts included by Debian inside `/usr/share/doc/*/copyright`; the completed ISO's installed package manifest has not been generated until a real build succeeds. Do not remove individual license or copyright files from a built image.

## ISO-X project source

- `LICENSE.txt` is the license notice currently present for the ISO-X project starter files. It permits study, modification and testing of those files and explicitly says it does not replace upstream notices or grant rights to third-party names, artwork or package trademarks. It is not a blanket license for every bundled dependency.
- `THIRD_PARTY_NOTICES.md` is retained and copied into the image's documentation directory. It contains the existing attribution and review notes for the previously studied Windows-Lite references. Those source files and Windows ISO artifacts are not bundled.

## Debian Live Config (reviewed reference; repository not vendored)

- Source: https://github.com/nodiscc/debian-live-config
- Repository revision inspected: `4856d0f`; the complete 238-entry GitHub tree was reviewed, including the live-build config, package lists, hooks, boot and desktop/service configuration.
- Reviewed repository `LICENSE`: GNU General Public License version 3.0 (GPL-3.0), and the license text says resulting images contain software packages under various individual licenses.
- The upstream repository/config tree is **not copied wholesale** into ISO-X. ISO-X has its own `auto/config`, package list and hooks. Therefore the upstream GPL file is recorded as a reviewed reference rather than a license for code copied into this project. If any upstream file is copied in a future change, preserve its copyright headers, the full GPL-3.0 license, and the fact that ISO-X modified it.

## OxyOS main repository (reviewed reference; code not bundled)

- Source: https://github.com/OxyHQ/OxyOS
- Repository revision inspected: `815c65f`; the complete 315-entry GitHub tree and the README, live-build config and React/Tauri shell areas were reviewed.
- The reviewed GitHub repository metadata reported no recognized license (`license: null`) and the 315-entry repository tree did not contain a `LICENSE`, `COPYING`, `COPYRIGHT`, `NOTICE`, or `AUTHORS` file. This does not prove the owner has no separate license grant; it means this audit could not establish permission to redistribute its main-repository source.
- No OxyOS source files, shell code or artwork have been copied into ISO-X from that repository. Do not vendor/rebrand those files unless a clear license or written permission covering redistribution and modification is obtained. Separate OxyOS sibling repositories may have separate licenses and must be reviewed individually before their contents are used.

## Debian packages and other runtime dependencies

- The image is based on Debian Trixie and package names in `config/package-lists/iso-x.list.chroot`. Each installed package retains its own license and copyright notices. Debian packages normally provide these under `/usr/share/doc/<package>/copyright`; some packages ship additional `LICENSE`, `COPYING`, or `NOTICE` files. The license obligations vary by package, so this report does not claim that one project-level license covers them all.
- Relevant project-specific dependencies include Bevy/Rust crates used by `three-d-login/` and Python/GTK bindings. Their resolved package manifests and licenses must be archived from the actual lock/resolution state during build; a final dependency/license inventory remains pending until toolchain dependency resolution and the ISO build have run.
- Firmware and browser packages must be considered separately from the ISO-X source license; redistribution conditions follow each Debian package's own terms and the configured Debian repositories.

## Required release checks

1. Preserve `/usr/share/doc/*/copyright` and upstream `LICENSE` / `COPYING` / `NOTICE` files in the built image.
2. Save the successful build's package manifest and generate a release-specific license inventory from the installed package copyright files.
3. If importing code/assets from a third-party repository, record exact repository URL, commit/tag, path, license, modifications and attribution before adding those files to ISO-X.
4. Do not claim complete third-party license collection until these release checks have been run against a successfully built image.
