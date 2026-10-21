#!/usr/bin/env python3
import importlib.util
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/create-user-iso.py"
SPEC = importlib.util.spec_from_file_location("create_user_iso", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

NONCE = "0123456789abcdef0123456789abcdef"


class UserIsoTests(unittest.TestCase):
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
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE}\n}}\n"
            f'menuentry "Live system (amd64) with Persistence" {{\n'
            f" linux /live/vmlinuz "
            f"{' '.join(MODULE.EXPECTED_BASE[:3] + MODULE.EXPECTED_BASE[5:7])} console=tty0 "
            f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
            f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} persistence\n}}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grub.cfg"
            path.write_text(original, encoding="utf-8")
            MODULE.normalize_config(path, NONCE, "grub")
            lines = path.read_text(encoding="utf-8").splitlines()
        linux_lines = [line.strip() for line in lines if line.lstrip().startswith("linux ")]
        self.assertEqual(len(linux_lines), 2)
        self.assertIn(" ".join(MODULE.EXPECTED_BASE), linux_lines[0])
        self.assertIn(" ".join(MODULE.EXPECTED_BASE + ["persistence"]), linux_lines[1])

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
                f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE}\n}}\n"
                'menuentry "Live system (amd64) with Persistence" {\n'
                f" linux /live/vmlinuz boot=live config components username=user hostname=iso-x console=tty0 "
                f"console=ttyS0,115200n8 loglevel=7 systemd.show_status=yes "
                f"systemd.log_target=console isox.ci=1 isox.ci.nonce={NONCE} persistence\n}}\n"
                'menuentry "Live system (amd64 fail-safe mode)" {\n'
                " linux /live/vmlinuz boot=live components username=user nomodeset\n}\n"
            )
            (tree / "boot/grub/grub.cfg").write_text(grub, encoding="utf-8")
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
            self.assertIn(output_digest, (root / "user.iso.sha256").read_text(encoding="ascii"))
            extracted = root / "release-live.cfg"
            subprocess.run(
                ["xorriso", "-osirrox", "on", "-indev", str(output),
                 "-extract", "/isolinux/live.cfg", str(extracted)],
                check=True, capture_output=True, text=True,
            )
            released_config = extracted.read_text(encoding="utf-8")
            self.assertNotRegex(released_config, r"isox\.ci|console=tty0|loglevel=7")
            self.assertIn("append boot=live components username=user nomodeset", released_config)


if __name__ == "__main__":
    unittest.main()
