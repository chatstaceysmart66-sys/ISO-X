#!/usr/bin/env python3
import importlib.util
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/create-user-iso.py"
METADATA_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/create-user-iso-metadata.py"
SPEC = importlib.util.spec_from_file_location("create_user_iso", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

NONCE = "0123456789abcdef0123456789abcdef"


class UserIsoTests(unittest.TestCase):
    def test_strips_ci_arguments_from_all_kernel_entries_not_only_live_entries(self):
        syslinux = (
            "label live-amd64-failsafe\n"
            f"append boot=live components username=user console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 isox.ci=1 "
            f"isox.ci.nonce={NONCE} nomodeset\n"
        )
        grub = (
            'menuentry "Verify integrity of the boot medium" {\n'
            f" linux /live/vmlinuz boot=live components verify-checksums console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 isox.ci=1 "
            f"isox.ci.nonce={NONCE}\n}}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            cases = (
                ("live.cfg", syslinux, "syslinux", "append "),
                ("grub.cfg", grub, "grub", "linux /live/vmlinuz "),
            )
            for name, content, kind, prefix in cases:
                with self.subTest(kind=kind):
                    path = Path(temporary) / name
                    path.write_text(content, encoding="utf-8")
                    changed = MODULE.strip_ci_arguments_from_kernel_entries(path, NONCE, kind)
                    self.assertEqual(changed, 1)
                    commands = [
                        line.strip()
                        for line in path.read_text(encoding="utf-8").splitlines()
                        if line.lstrip().startswith(prefix)
                    ]
                    self.assertEqual(len(commands), 1)
                    self.assertNotIn("isox.ci", commands[0])
                    self.assertNotIn("console=tty0", commands[0])
                    self.assertNotIn("loglevel=7", commands[0])
                    self.assertIn("console=ttyS0,115200n8", commands[0])
                    self.assertIn(
                        "nomodeset" if kind == "syslinux" else "verify-checksums",
                        commands[0],
                    )

    def test_ci_argument_scrubber_rejects_wrong_nonce_without_mutating_file(self):
        content = (
            "label live-amd64-failsafe\n"
            f"append boot=live isox.ci=1 isox.ci.nonce={'f' * 32} nomodeset\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "live.cfg"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not match the supplied nonce"):
                MODULE.strip_ci_arguments_from_kernel_entries(path, NONCE, "syslinux")
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_final_metadata_records_boot_evidence_and_stays_not_release_eligible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            iso = root / "normal.iso"
            iso.write_bytes(b"normal boot iso fixture")
            digest = hashlib.sha256(iso.read_bytes()).hexdigest()
            iso.with_name(iso.name + ".sha256").write_text(f"{digest}  {iso.name}\n", encoding="ascii")
            diagnostic_iso = root / "ci.iso"
            diagnostic_iso.write_bytes(b"verified diagnostic iso fixture")
            diagnostic_digest = hashlib.sha256(diagnostic_iso.read_bytes()).hexdigest()
            diagnostic_metadata = root / "diagnostic.json"
            diagnostic_metadata.write_text(json.dumps({
                "commit": "deadbeef",
                "iso_sha256": diagnostic_digest,
                "ci_boot_diagnostic_variant": True,
                "ci_nonce": NONCE,
                "release_eligible": True,
            }), encoding="utf-8")
            boot_result = {
                "status": "PASS_BOOT",
                "desktop_seen": True,
                "shutdown_reason": "desktop_rendered",
                "qemu_exit_code": -15,
                "termination_requested": True,
                "termination_escalated": False,
                "process_group_clean": True,
                "final_screenshot_valid": True,
                "screenshots": ["qemu-bios-desktop-final.ppm"],
                "duration_seconds": 70.0,
                "firmware": "BIOS",
            }
            bios_result = root / "bios.json"
            uefi_result = root / "uefi.json"
            bios_result.write_text(json.dumps(boot_result), encoding="utf-8")
            uefi_result.write_text(json.dumps({**boot_result, "firmware": "UEFI/OVMF"}), encoding="utf-8")
            metadata = root / "build-metadata.json"
            manifest = root / "validation-manifest.txt"
            command = [
                sys.executable, str(METADATA_SCRIPT),
                "--iso", str(iso),
                "--diagnostic-metadata", str(diagnostic_metadata),
                "--metadata", str(metadata),
                "--bios-result", str(bios_result),
                "--uefi-result", str(uefi_result),
                "--manifest", str(manifest),
                "--diagnostic-iso", "ci.iso",
                "--diagnostic-iso-path", str(diagnostic_iso),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            final = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual(final["iso_sha256"], digest)
            self.assertFalse(final["ci_boot_diagnostic_variant"])
            self.assertNotIn("ci_nonce", final)
            self.assertFalse(final["release_eligible"])
            self.assertEqual(final["persistence"]["status"], "NOT_RUN")
            self.assertTrue(final["user_iso"]["boot_acceptance"]["bios"]["desktop_seen"])
            self.assertTrue(final["user_iso"]["boot_acceptance"]["uefi"]["final_screenshot_valid"])
            contents = manifest.read_text(encoding="utf-8")
            self.assertIn("normal_iso_bios=PASS_BOOT", contents)
            self.assertIn("normal_iso_uefi=PASS_BOOT", contents)
            self.assertIn("persistence=NOT_RUN", contents)
            self.assertIn("release_eligible=false", contents)

    def test_final_metadata_rejects_wrong_hash_sidecar(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            iso = root / "normal.iso"
            iso.write_bytes(b"bad hash fixture")
            iso.with_name(iso.name + ".sha256").write_text(f"{'0' * 64}  {iso.name}\n", encoding="ascii")
            diagnostic_iso = root / "ci.iso"
            diagnostic_iso.write_bytes(b"diagnostic fixture")
            diagnostic_metadata = root / "diagnostic.json"
            diagnostic_metadata.write_text(json.dumps({
                "iso_sha256": hashlib.sha256(diagnostic_iso.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(METADATA_SCRIPT),
                "--iso", str(iso), "--diagnostic-metadata", str(diagnostic_metadata),
                "--metadata", str(root / "out.json"),
                "--bios-result", str(root / "missing-bios.json"),
                "--uefi-result", str(root / "missing-uefi.json"),
                "--manifest", str(root / "manifest.txt"), "--diagnostic-iso", "ci.iso",
                "--diagnostic-iso-path", str(diagnostic_iso),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match its SHA-256 sidecar", result.stderr)
            self.assertFalse((root / "out.json").exists())

    def test_normalizes_syslinux_live_entries(self):
        original = (
            "label live-amd64\nmenu default\n"
            f"append boot=live config components username=user hostname=iso-x console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE}\n"
            "label live-amd64-persistence\n"
            f"append boot=live config components username=user hostname=iso-x console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} persistence\n"
            "label live-amd64-failsafe\nappend boot=live components username=user nomodeset\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "live.cfg"
            path.write_text(original, encoding="utf-8")
            MODULE.normalize_config(path, NONCE, "syslinux")
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertIn("append " + " ".join(MODULE.EXPECTED_BASE), lines)
        self.assertIn("append " + " ".join(MODULE.EXPECTED_BASE + ["persistence"]), lines)
        self.assertIn("append boot=live components username=user nomodeset", lines)
        self.assertFalse(any("isox.ci" in line for line in lines))

    def test_normalizes_grub_live_entries(self):
        original = (
            "set timeout=10\n"
            f'menuentry "Live system (amd64)" {{\n linux /live/vmlinuz '
            f'{" ".join(MODULE.EXPECTED_BASE[:3] + MODULE.EXPECTED_BASE[5:7])} '
            f"console=tty0 console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} findiso=${{iso_path}}\n}}\n"
            f'menuentry "Live system (amd64) with Persistence" {{\n'
            f" linux /live/vmlinuz "
            f"{' '.join(MODULE.EXPECTED_BASE[:3] + MODULE.EXPECTED_BASE[5:7])} console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} findiso=${{iso_path}} persistence\n}}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grub.cfg"
            path.write_text(original, encoding="utf-8")
            MODULE.normalize_config(path, NONCE, "grub")
            lines = path.read_text(encoding="utf-8").splitlines()
        linux_lines = [line.strip() for line in lines if line.lstrip().startswith("linux ")]
        self.assertEqual(len(linux_lines), 2)
        self.assertIn(" ".join(MODULE.EXPECTED_BASE + ["findiso=${iso_path}"]), linux_lines[0])
        self.assertIn(" ".join(MODULE.EXPECTED_BASE + ["findiso=${iso_path}", "persistence"]), linux_lines[1])

    def test_rejects_wrong_nonce_and_unexpected_arguments(self):
        content = (
            "label live-amd64\nmenu default\n"
            f"append {' '.join(MODULE.EXPECTED_BASE)} isox.ci=1 "
            f"isox.ci.nonce={'f' * 32}\n"
            "label live-amd64-persistence\n"
            f"append {' '.join(MODULE.EXPECTED_BASE)} isox.ci=1 "
            f"isox.ci.nonce={NONCE} persistence unexpected=1\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "live.cfg"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "supplied nonce"):
                MODULE.normalize_config(path, NONCE, "syslinux")
            path.write_text(content.replace(f"isox.ci.nonce={'f' * 32}", f"isox.ci.nonce={NONCE}"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected boot arguments"):
                MODULE.normalize_config(path, NONCE, "syslinux")

    def test_normalizes_read_only_extracted_syslinux_and_grub_configs(self):
        syslinux = (
            "label live-amd64\nmenu default\n"
            f"append boot=live config components username=user hostname=iso-x console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE}\n"
            "label live-amd64-persistence\n"
            f"append boot=live config components username=user hostname=iso-x console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} persistence\n"
        )
        grub = (
            'menuentry "Live system (amd64)" {\n'
            f" linux /live/vmlinuz boot=live config components username=user hostname=iso-x console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} findiso=${{iso_path}}\n}}\n"
            'menuentry "Live system (amd64) with Persistence" {\n'
            f" linux /live/vmlinuz boot=live config components username=user hostname=iso-x console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} findiso=${{iso_path}} persistence\n}}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            for name, content, kind in (
                ("live.cfg", syslinux, "syslinux"),
                ("grub.cfg", grub, "grub"),
            ):
                with self.subTest(kind=kind):
                    path = Path(temporary) / name
                    path.write_text(content, encoding="utf-8")
                    path.chmod(0o444)
                    original_inode = path.stat().st_ino
                    with mock.patch.object(Path, "write_text", side_effect=PermissionError("read-only extracted file")):
                        MODULE.normalize_config(path, NONCE, kind)
                    normalized = path.read_text(encoding="utf-8").splitlines()
                    self.assertNotEqual(path.stat().st_ino, original_inode)
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o444)
                    self.assertFalse(any("isox.ci" in line or "console=tty0" in line or "loglevel=7" in line for line in normalized))
                    commands = [line.strip() for line in normalized if line.lstrip().startswith(("append ", "linux "))]
                    expected_prefix = "append " if kind == "syslinux" else "linux /live/vmlinuz "
                    expected = MODULE.EXPECTED_BASE + (["findiso=${iso_path}"] if kind == "grub" else [])
                    self.assertIn(expected_prefix + " ".join(expected), commands)
                    self.assertIn(expected_prefix + " ".join(expected + ["persistence"]), commands)

    def test_rejects_unexpected_grub_live_entry_changes(self):
        content = (
            f'menuentry "Live system (amd64)" {{\n linux /live/vmlinuz {" ".join(MODULE.EXPECTED_BASE)} '
            f"findiso=${{iso_path}} isox.ci=1 isox.ci.nonce={NONCE}\n}}\n"
            f'menuentry "Live system (amd64) with Persistence" {{\n linux /live/vmlinuz {" ".join(MODULE.EXPECTED_BASE)} '
            f"findiso=${{iso_path}} isox.ci=1 isox.ci.nonce={NONCE} persistence unexpected=1\n}}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grub.cfg"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected boot arguments"):
                MODULE.normalize_config(path, NONCE, "grub")
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_rejects_unexpected_grub_findiso_value(self):
        content = (
            f'menuentry "Live system (amd64)" {{\n linux /live/vmlinuz {" ".join(MODULE.EXPECTED_BASE)} '
            f"findiso=/dev/sda isox.ci=1 isox.ci.nonce={NONCE}\n}}\n"
            f'menuentry "Live system (amd64) with Persistence" {{\n linux /live/vmlinuz {" ".join(MODULE.EXPECTED_BASE)} '
            f"findiso=${{iso_path}} isox.ci=1 isox.ci.nonce={NONCE} persistence\n}}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grub.cfg"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected boot arguments"):
                MODULE.normalize_config(path, NONCE, "grub")
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    @unittest.skipUnless(shutil.which("xorriso"), "xorriso is required for ISO integration coverage")
    def test_rewrites_only_boot_configs_and_preserves_el_torito(self):
        with tempfile.TemporaryDirectory(prefix="isox-user-iso-test-") as temporary:
            root = Path(temporary)
            tree = root / "tree"
            (tree / "isolinux").mkdir(parents=True)
            (tree / "boot/grub").mkdir(parents=True)
            (tree / "live").mkdir()
            (tree / "isolinux/isolinux.cfg").write_text(
                "include menu.cfg\ndefault vesamenu.c32\nprompt 0\ntimeout 100\n", encoding="utf-8"
            )
            syslinux = (
                "label live-amd64\n\tmenu default\n"
                f"\tappend boot=live config components username=user hostname=iso-x console=tty0 "
                f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
                f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE}\n"
                "label live-amd64-persistence\n"
                f"\tappend boot=live config components username=user hostname=iso-x console=tty0 "
                f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
                f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} persistence\n"
                "label live-amd64-failsafe\n\tappend boot=live components username=user nomodeset\n"
            )
            (tree / "isolinux/live.cfg").write_text(syslinux, encoding="utf-8")
            grub = (
                'set timeout=10\nmenuentry "Live system (amd64)" {\n'
                f" linux /live/vmlinuz boot=live config components username=user hostname=iso-x console=tty0 "
                f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
                f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} findiso=${{iso_path}}\n}}\n"
                'menuentry "Live system (amd64) with Persistence" {\n'
                f" linux /live/vmlinuz boot=live config components username=user hostname=iso-x console=tty0 "
                f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
                f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} findiso=${{iso_path}} persistence\n}}\n"
                'menuentry "Live system (amd64 fail-safe mode)" {\n'
                " linux /live/vmlinuz boot=live components username=user nomodeset\n}\n"
            )
            (tree / "boot/grub/grub.cfg").write_text(grub, encoding="utf-8")
            (tree / "isolinux/live.cfg").chmod(0o444)
            (tree / "boot/grub/grub.cfg").chmod(0o444)
            for image in ("isolinux/isolinux.bin", "boot/grub/efi.img", "live/vmlinuz", "live/initrd.img"):
                path = tree / image
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes(65536 if image.endswith("efi.img") else 4096))
            mbr = root / "mbr.bin"
            data = bytearray(512)
            data[510:512] = b"\x55\xaa"
            mbr.write_bytes(data)
            source = root / "ci.iso"
            subprocess.run([
                "xorriso", "-as", "mkisofs", "-R", "-V", "ISOX040_LIVE", "-o", str(source),
                "-isohybrid-mbr", str(mbr), "-b", "isolinux/isolinux.bin", "-c", "isolinux/boot.cat",
                "-no-emul-boot", "-boot-load-size", "4", "-boot-info-table", "-eltorito-alt-boot",
                "-e", "boot/grub/efi.img", "-no-emul-boot", str(tree),
            ], check=True, capture_output=True, text=True)
            for config in ("isolinux/live.cfg", "boot/grub/grub.cfg"):
                extracted = root / Path(config).name
                subprocess.run(
                    ["xorriso", "-osirrox", "on", "-indev", str(source), "-extract", f"/{config}", str(extracted)],
                    check=True, capture_output=True, text=True,
                )
                self.assertEqual(stat.S_IMODE(extracted.stat().st_mode), 0o444)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            (root / "ci.iso.sha256").write_text(f"{digest}  ci.iso\n", encoding="ascii")
            output = root / "user.iso"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), str(output), NONCE],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            output_digest = hashlib.sha256(output.read_bytes()).hexdigest()
            output_sidecar = (root / "user.iso.sha256").read_text(encoding="ascii").split()
            self.assertEqual(output_sidecar[0], output_digest)
            self.assertEqual(output_sidecar[-1], "user.iso")
            extracted = root / "release-live.cfg"
            subprocess.run(
                ["xorriso", "-osirrox", "on", "-indev", str(output),
                 "-extract", "/isolinux/live.cfg", str(extracted)],
                check=True, capture_output=True, text=True,
            )
            released_config = extracted.read_text(encoding="utf-8")
            self.assertNotRegex(released_config, r"isox\.ci|console=tty0|loglevel=7")
            self.assertIn("append boot=live components username=user nomodeset", released_config)
            self.assertIn("append " + " ".join(MODULE.EXPECTED_BASE), released_config.splitlines())
            self.assertIn("append " + " ".join(MODULE.EXPECTED_BASE + ["persistence"]), released_config.splitlines())
            extracted_grub = root / "release-grub.cfg"
            subprocess.run(
                ["xorriso", "-osirrox", "on", "-indev", str(output), "-extract", "/boot/grub/grub.cfg", str(extracted_grub)],
                check=True, capture_output=True, text=True,
            )
            released_grub = extracted_grub.read_text(encoding="utf-8").splitlines()
            self.assertFalse(any("isox.ci" in line or "console=tty0" in line or "loglevel=7" in line for line in released_grub))
            grub_commands = [line.strip() for line in released_grub if line.lstrip().startswith("linux ")]
            grub_expected = MODULE.EXPECTED_BASE + ["findiso=${iso_path}"]
            self.assertIn("linux /live/vmlinuz " + " ".join(grub_expected), grub_commands)
            self.assertIn("linux /live/vmlinuz " + " ".join(grub_expected + ["persistence"]), grub_commands)
            boot = subprocess.run(
                ["xorriso", "-indev", str(output), "-report_el_torito", "plain"],
                check=True, capture_output=True, text=True,
            ).stdout
            area = subprocess.run(
                ["xorriso", "-indev", str(output), "-report_system_area", "plain"],
                check=True, capture_output=True, text=True,
            ).stdout
            self.assertRegex(boot, r"El Torito boot img\s*:.*BIOS")
            self.assertRegex(boot, r"El Torito boot img\s*:.*UEFI")
            self.assertRegex(area, r"System area summary:.*\bMBR\b")
            output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
            self.assertEqual(output_hash, output.with_name("user.iso.sha256").read_text().split()[0])

            diagnostic_metadata = root / "diagnostic-metadata.json"
            diagnostic_metadata.write_text(json.dumps({
                "commit": "deadbeef",
                "iso_sha256": digest,
                "ci_boot_diagnostic_variant": True,
                "ci_nonce": NONCE,
                "release_eligible": True,
            }), encoding="utf-8")
            boot_result = {
                "status": "PASS_BOOT",
                "desktop_seen": True,
                "shutdown_reason": "desktop_rendered",
                "qemu_exit_code": -15,
                "termination_requested": True,
                "termination_escalated": False,
                "process_group_clean": True,
                "final_screenshot_valid": True,
                "screenshots": ["desktop.ppm"],
                "duration_seconds": 60.0,
            }
            bios_result = root / "bios-result.json"
            uefi_result = root / "uefi-result.json"
            bios_result.write_text(json.dumps({**boot_result, "firmware": "BIOS"}), encoding="utf-8")
            uefi_result.write_text(json.dumps({**boot_result, "firmware": "UEFI/OVMF"}), encoding="utf-8")
            final_metadata = root / "final-build-metadata.json"
            manifest = root / "validation-manifest.txt"
            metadata_result = subprocess.run([
                sys.executable, str(METADATA_SCRIPT),
                "--iso", str(output),
                "--diagnostic-metadata", str(diagnostic_metadata),
                "--metadata", str(final_metadata),
                "--bios-result", str(bios_result),
                "--uefi-result", str(uefi_result),
                "--manifest", str(manifest),
                "--diagnostic-iso", source.name,
                "--diagnostic-iso-path", str(source),
            ], capture_output=True, text=True)
            self.assertEqual(metadata_result.returncode, 0, metadata_result.stdout + metadata_result.stderr)
            final = json.loads(final_metadata.read_text(encoding="utf-8"))
            self.assertEqual(final["iso_sha256"], output_hash)
            self.assertEqual(final["iso_size_bytes"], output.stat().st_size)
            self.assertFalse(final["ci_boot_diagnostic_variant"])
            self.assertNotIn("ci_nonce", final)
            self.assertFalse(final["release_eligible"])
            self.assertEqual(final["persistence"]["status"], "NOT_RUN")
            self.assertTrue(final["user_iso"]["boot_acceptance"]["bios"]["desktop_seen"])
            manifest_text = manifest.read_text(encoding="utf-8")
            self.assertIn(f"sha256={output_hash}", manifest_text)
            self.assertIn("normal_iso_bios=PASS_BOOT", manifest_text)
            self.assertIn("normal_iso_uefi=PASS_BOOT", manifest_text)
            self.assertIn("persistence=NOT_RUN", manifest_text)
            self.assertIn("release_eligible=false", manifest_text)


if __name__ == "__main__":
    unittest.main()
