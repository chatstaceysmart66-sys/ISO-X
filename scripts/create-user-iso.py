#!/usr/bin/env python3
"""Create a normal-boot ISO from a CI-booted ISO without rebuilding its rootfs."""
from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-iso-boot-config.sh"
EXPECTED_BASE = [
    "boot=live", "config", "components", "quiet", "splash", "username=user",
    "hostname=iso-x", "console=ttyS0,115200n8", "systemd.show_status=yes",
    "systemd.log_target=console",
]


def replace_config_atomically(path: Path, content: str) -> None:
    original = path.lstat()
    if not stat.S_ISREG(original.st_mode):
        raise ValueError(f"boot configuration is not a regular file: {path}")
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(original.st_mode))
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def normalize_config(path: Path, nonce: str, kind: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    rewritten: list[str] = []
    current_entry = ""
    changed = 0

    for line in lines:
        stripped = line.strip()
        if kind == "syslinux" and stripped.startswith("label "):
            current_entry = stripped.split(maxsplit=1)[1]
        elif kind == "grub" and stripped.startswith("menuentry "):
            current_entry = (
                "persistence" if "Live system" in stripped and "with Persistence" in stripped
                else "normal" if "Live system" in stripped and "fail-safe" not in stripped.lower()
                else ""
            )

        command = stripped.split(maxsplit=1)[0] if stripped else ""
        is_kernel_line = command == ("append" if kind == "syslinux" else "linux")
        is_live_entry = (
            current_entry.startswith("live-") and not current_entry.endswith("-failsafe")
            if kind == "syslinux"
            else bool(current_entry)
        )
        if not is_kernel_line or not is_live_entry:
            rewritten.append(line)
            continue

        tokens = stripped.split()
        prefix_size = 1 if kind == "syslinux" else 2
        prefix, args = tokens[:prefix_size], tokens[prefix_size:]
        persistence = (
            current_entry.endswith("-persistence")
            if kind == "syslinux"
            else current_entry == "persistence"
        )
        nonce_token = f"isox.ci.nonce={nonce}"
        if args.count("isox.ci=1") != 1 or args.count(nonce_token) != 1:
            raise ValueError(f"{path}: expected exactly one CI flag and the supplied nonce")
        forbidden = {"isox.ci=1", nonce_token, "console=tty0", "loglevel=7"}
        args = [argument for argument in args if argument not in forbidden]
        if "quiet" not in args:
            args.insert(args.index("components") + 1, "quiet")
        if "splash" not in args:
            args.insert(args.index("quiet") + 1, "splash")
        expected = (
            EXPECTED_BASE
            + (["findiso=${iso_path}"] if kind == "grub" else [])
            + (["persistence"] if persistence else [])
        )
        if args != expected:
            raise ValueError(f"{path}: unexpected boot arguments for {current_entry}: {args!r}")
        rewritten.append(" ".join(prefix + args))
        changed += 1

    if changed != 2:
        raise ValueError(f"{path}: expected two live kernel entries, normalized {changed}")
    replace_config_atomically(path, "\n".join(rewritten) + "\n")


def strip_ci_arguments_from_kernel_entries(path: Path, nonce: str, kind: str) -> int:
    """Remove known CI-only arguments from every kernel entry, safely."""
    if kind not in {"syslinux", "grub"}:
        raise ValueError(f"unsupported boot configuration kind: {kind}")

    nonce_token = f"isox.ci.nonce={nonce}"
    known_ci_tokens = {"isox.ci=1", nonce_token}
    diagnostic_tokens = {"console=tty0", "loglevel=7"}
    rewritten = []
    removed = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        command = stripped.split(maxsplit=1)[0] if stripped else ""

        if kind == "syslinux":
            is_kernel_line = command == "append"
            prefix_size = 1
        else:
            is_kernel_line = command in {"linux", "linuxefi", "linux16"}
            prefix_size = 2

        if not is_kernel_line:
            rewritten.append(line)
            continue

        tokens = stripped.split()
        prefix, args = tokens[:prefix_size], tokens[prefix_size:]
        ci_tokens = [arg for arg in args if arg.startswith("isox.ci")]

        if not ci_tokens:
            rewritten.append(line)
            continue

        if args.count("isox.ci=1") != 1 or args.count(nonce_token) != 1:
            raise ValueError(
                f"{path}: CI arguments on a kernel line do not match the supplied nonce"
            )

        unexpected = [arg for arg in ci_tokens if arg not in known_ci_tokens]
        if unexpected:
            raise ValueError(f"{path}: unexpected ISO-X CI arguments: {unexpected!r}")

        args = [
            arg for arg in args
            if arg not in known_ci_tokens and arg not in diagnostic_tokens
        ]
        rewritten.append(" ".join(prefix + args))
        removed += 1

    if removed:
        replace_config_atomically(path, "\n".join(rewritten) + "\n")

    return removed


def run(*args: str) -> str:
    # Preserve the original command output so a failed validation is diagnosable.
    result = subprocess.run(args, check=False, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, args, output=result.stdout, stderr=result.stderr
        )
    return result.stdout + result.stderr


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} CI_ISO OUTPUT_ISO NONCE", file=sys.stderr)
        return 2
    source, output = map(lambda value: Path(value).resolve(), sys.argv[1:3])
    nonce = sys.argv[3]
    if not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("nonce must contain exactly 32 lowercase hexadecimal characters")
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError(f"CI ISO is missing or empty: {source}")
    if source == output or output.exists():
        raise ValueError("output must be a new path distinct from the CI ISO")
    sidecar = source.with_name(source.name + ".sha256")
    if not sidecar.is_file():
        raise ValueError(f"CI ISO SHA-256 sidecar is missing: {sidecar}")
    expected_source_hash = sidecar.read_text(encoding="ascii").split()[0]
    if not re.fullmatch(r"[a-f0-9]{64}", expected_source_hash):
        raise ValueError("CI ISO SHA-256 sidecar has an invalid digest")
    if sha256(source) != expected_source_hash:
        raise ValueError("CI ISO does not match its SHA-256 sidecar")
    if not output.parent.is_dir():
        raise ValueError(f"output directory does not exist: {output.parent}")

    with tempfile.TemporaryDirectory(prefix="isox-user-iso-", dir=output.parent) as temporary:
        work = Path(temporary)
        isolinux = work / "isolinux.cfg"
        live = work / "live.cfg"
        grub = work / "grub.cfg"
        stage = work / output.name
        run(
            "xorriso", "-osirrox", "on", "-indev", str(source),
            "-extract", "/isolinux/isolinux.cfg", str(isolinux),
            "-extract", "/isolinux/live.cfg", str(live),
            "-extract", "/boot/grub/grub.cfg", str(grub),
        )
        run("bash", str(VALIDATOR), str(isolinux), str(live), str(grub), "1", nonce)
        normalize_config(live, nonce, "syslinux")
        normalize_config(grub, nonce, "grub")
        strip_ci_arguments_from_kernel_entries(grub, nonce, "grub")
        strip_ci_arguments_from_kernel_entries(live, nonce, "syslinux")
        run("bash", str(VALIDATOR), str(isolinux), str(live), str(grub), "0", "")
        run(
            "xorriso", "-indev", str(source), "-outdev", str(stage),
            "-boot_image", "any", "replay",
            "-map", str(live), "/isolinux/live.cfg",
            "-map", str(grub), "/boot/grub/grub.cfg",
            "-commit",
        )
        boot = run("xorriso", "-indev", str(stage), "-report_el_torito", "plain")
        area = run("xorriso", "-indev", str(stage), "-report_system_area", "plain")
        source_area = run("xorriso", "-indev", str(source), "-report_system_area", "plain")
        run("xorriso", "-indev", str(stage), "-pvd_info")
        if not re.search(r"El Torito boot img\s*:.*BIOS", boot):
            raise ValueError("promoted ISO is missing the El Torito BIOS boot entry")
        if not re.search(r"El Torito boot img\s*:.*UEFI", boot):
            raise ValueError("promoted ISO is missing the El Torito UEFI boot entry")
        if not re.search(r"System area summary:.*\bMBR\b", area, re.IGNORECASE):
            raise ValueError("promoted ISO is missing its MBR system area")
        if "isohybrid" in source_area.lower() and "isohybrid" not in area.lower():
            raise ValueError("promoted ISO did not preserve the source isohybrid system area")
        os.replace(stage, output)

    digest = sha256(output)
    output_sidecar = output.with_name(output.name + ".sha256")
    output_sidecar.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    print(f"ISO: {output}")
    print(f"Size bytes: {output.stat().st_size}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
