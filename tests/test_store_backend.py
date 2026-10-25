#!/usr/bin/env python3
"""Isolated tests for package discovery and guarded ISO-X Store operations."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import runpy
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts"))

from isox_store_backend import (  # noqa: E402
    FLATHUB_URL,
    OperationResult,
    StoreBackend,
    parse_dep11_file,
    parse_appstream_file,
)
_sound_generator = runpy.run_path(str(ROOT / "scripts/generate-store-sounds.py"))
SOUNDS = _sound_generator["SOUNDS"]
generate = _sound_generator["generate"]


class FakeRunner:
    def __init__(self):
        self.calls: list[list[str]] = []
        self.responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {}

    def __call__(self, argv, **_kwargs):
        self.calls.append(list(argv))
        for prefix, response in self.responses.items():
            if tuple(argv[:len(prefix)]) == prefix:
                return response
        return subprocess.CompletedProcess(argv, 0, "", "")


def completed(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class StoreBackendTests(unittest.TestCase):
    def test_parses_localized_appstream_without_remote_image_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apps.xml"
            path.write_text(
                """<components><component type="desktop-application">
                <id>org.example.Editor</id><pkgname>example-editor</pkgname>
                <name>Example Editor</name><name xml:lang="ar">محرر تجريبي</name>
                <summary>A document editor</summary><summary xml:lang="ar">محرر مستندات</summary>
                <description><p>Safe <em>local</em> description.</p></description>
                <categories><category>Graphics</category></categories>
                <icon type="remote">https://invalid.example/icon.png</icon>
                <icon type="stock">applications-graphics</icon>
                <developer_name>ISO-X test developer</developer_name>
                <project_license>GPL-3.0-or-later</project_license>
                <launchable type="desktop-id">org.example.Editor.desktop</launchable>
                <size type="download">12345</size></component></components>""",
                encoding="utf-8",
            )
            record = parse_appstream_file(path, "ar")[0]
        self.assertEqual(record["name"], "محرر تجريبي")
        self.assertEqual(record["summary"], "محرر مستندات")
        self.assertEqual(record["description"], "Safe local description.")
        self.assertEqual(record["icon"], "applications-graphics")
        self.assertEqual(record["package_names"], ["example-editor"])
        self.assertEqual(record["size_bytes"], 12345)
        self.assertEqual(record["desktop_id"], "org.example.Editor.desktop")

    def test_parses_compressed_appstream_catalog(self):
        import gzip

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.xml.gz"
            with gzip.open(path, "wb") as stream:
                stream.write(
                    b"<components><component><id>org.example.Reader</id>"
                    b"<pkgname>example-reader</pkgname><name>Reader</name>"
                    b"</component></components>"
                )
            self.assertEqual(parse_appstream_file(path, "C")[0]["name"], "Reader")

    def test_parses_debian_dep11_catalog_with_localized_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trixie_dep11_Components-amd64.yml"
            path.write_text(
                """---
Type: desktop-application
ID: org.example.Reader
Package: example-reader
Name:
  C: Reader
  ar: قارئ
Summary:
  C: Read documents
  ar: قراءة المستندات
Description:
  C: A local document reader.
Categories:
  - Office
Icon:
  stock: applications-office
Launchable:
  desktop-id: org.example.Reader.desktop
DeveloperName:
  C: ISO-X test developer
ProjectLicense: GPL-3.0-or-later
---
""",
                encoding="utf-8",
            )
            records = parse_dep11_file(path, "ar")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "قارئ")
        self.assertEqual(records[0]["summary"], "قراءة المستندات")
        self.assertEqual(records[0]["package_names"], ["example-reader"])
        self.assertEqual(records[0]["desktop_id"], "org.example.Reader.desktop")

    def test_catalog_refresh_invalidates_cached_appstream_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = StoreBackend(appstream_roots=[root], architecture="amd64")
            self.assertEqual(backend._appstream_records(), [])
            (root / "new_dep11_Components-amd64.yml").write_text(
                "---\nID: org.example.Reader\nPackage: example-reader\nName:\n  C: Reader\n",
                encoding="utf-8",
            )
            self.assertEqual(backend._appstream_records(), [])
            backend.invalidate_catalog_cache()
            self.assertEqual(backend._appstream_records()[0]["name"], "Reader")

    def test_apt_results_are_source_verified_and_include_real_package_metadata(self):
        runner = FakeRunner()
        runner.responses.update({
            ("apt-cache", "policy", "example-editor"): completed(
                [], stdout="example-editor:\n  Installed: 1.0\n  Candidate: 1.2\n"
            ),
            ("dpkg-query", "-W"): completed(
                [], stdout="install ok installed\t1.0\n"
            ),
            ("apt-cache", "show", "example-editor"): completed(
                [], stdout="Package: example-editor\nVersion: 1.2\nArchitecture: amd64\nSize: 2048\n\n"
            ),
            ("dpkg", "--compare-versions"): completed([], returncode=0),
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.xml"
            path.write_text(
                "<components><component><id>org.example.Editor</id>"
                "<pkgname>example-editor</pkgname><name>Example Editor</name>"
                "<summary>Write documents</summary><categories><category>Office</category></categories>"
                "<size type='download'>99</size></component></components>",
                encoding="utf-8",
            )
            backend = StoreBackend(runner=runner, appstream_roots=[Path(directory)], architecture="amd64")
            result = backend.search("Example Editor", "Office", source="APT")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].package_id, "example-editor")
        self.assertEqual(result[0].source, "apt")
        self.assertEqual(result[0].version, "1.2")
        self.assertTrue(result[0].installed)
        self.assertTrue(result[0].update_available)
        self.assertEqual(result[0].size_bytes, 2048)
        self.assertEqual(result[0].architecture, "amd64")

    def test_apt_catalog_excludes_packages_for_other_architectures(self):
        runner = FakeRunner()
        runner.responses.update({
            ("apt-cache", "policy", "foreign-app"): completed(
                [], stdout="Candidate: 1.0\n"
            ),
            ("dpkg-query", "-W"): completed(
                [], stdout="unknown ok not-installed\t\n"
            ),
            ("apt-cache", "show", "foreign-app"): completed(
                [], stdout="Package: foreign-app\nVersion: 1.0\nArchitecture: arm64\nSize: 2048\n\n"
            ),
        })
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "catalog.xml").write_text(
                "<components><component><id>org.example.Foreign</id>"
                "<pkgname>foreign-app</pkgname><name>Foreign App</name>"
                "</component></components>",
                encoding="utf-8",
            )
            backend = StoreBackend(runner=runner, appstream_roots=[Path(directory)], architecture="amd64")
            self.assertEqual(backend.search(source="APT"), [])

    def test_install_rejects_invalid_id_and_stale_candidate_without_privilege(self):
        runner = FakeRunner()
        runner.responses[("apt-cache", "policy", "safe-app")] = completed(
            [], stdout="Candidate: 2.0\n"
        )
        backend = StoreBackend(runner=runner, architecture="amd64")
        self.assertFalse(backend.install_apt("safe-app;id", "2.0").success)
        self.assertFalse(backend.install_apt("safe-app", "1.0").success)
        self.assertFalse(any(call[0] == "pkexec" for call in runner.calls))

    def test_apt_install_uses_fixed_argv_after_candidate_revalidation(self):
        runner = FakeRunner()
        runner.responses[("apt-cache", "policy", "safe-app")] = completed(
            [], stdout="Candidate: 2.0\n"
        )
        runner.responses[("pkexec", "/usr/bin/apt-get")] = completed(
            [], stdout="installed"
        )
        backend = StoreBackend(runner=runner, architecture="amd64")
        with patch("isox_store_backend.shutil.which", return_value="/usr/bin/pkexec"):
            result = backend.install_apt("safe-app", "2.0")
        self.assertTrue(result.success)
        self.assertIn(
            ["pkexec", "/usr/bin/apt-get", "install", "--yes", "--no-install-recommends", "--", "safe-app=2.0"],
            runner.calls,
        )

    def test_flatpak_install_requires_a_matching_enabled_remote_entry(self):
        runner = FakeRunner()
        runner.responses[("flatpak", "remote-ls")] = completed(
            [], stdout="org.example.Reader\tstable\tx86_64\n"
        )
        runner.responses[("flatpak", "remotes", "--user")] = completed(
            [], stdout="verified\n"
        )
        runner.responses[("flatpak", "install")] = completed([], stdout="installed")
        backend = StoreBackend(runner=runner, architecture="x86_64")
        with patch("isox_store_backend.shutil.which", return_value="/usr/bin/flatpak"):
            result = backend.install_flatpak("verified", "org.example.Reader", "stable")
            invalid = backend.install_flatpak("verified", "org.attacker.Reader", "stable")
            backend.search(source="Flatpak")
        self.assertTrue(result.success)
        self.assertFalse(invalid.success)
        self.assertIn(
            ["flatpak", "install", "--user", "--assumeyes", "--noninteractive", "--branch",
             "stable", "verified", "org.example.Reader"],
            runner.calls,
        )
        self.assertTrue(any(call[:3] == ["flatpak", "remotes", "--user"] for call in runner.calls))
        self.assertFalse(any("org.attacker.Reader" in call for call in runner.calls if call[:2] == ["flatpak", "install"]))

    def test_flathub_add_is_explicitly_user_scoped_and_uses_official_url(self):
        runner = FakeRunner()
        runner.responses[("flatpak", "remote-add")] = completed([], stdout="added")
        backend = StoreBackend(runner=runner)
        with patch("isox_store_backend.shutil.which", return_value="/usr/bin/flatpak"):
            result = backend.enable_flathub()
        self.assertTrue(result.success)
        self.assertIn(
            ["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB_URL],
            runner.calls,
        )

    def test_flatpak_update_is_scoped_to_verified_user_application(self):
        runner = FakeRunner()
        runner.responses[("flatpak", "update")] = completed([], stdout="updated")
        backend = StoreBackend(runner=runner)
        with patch("isox_store_backend.shutil.which", return_value="/usr/bin/flatpak"):
            result = backend.update_flatpak("org.example.Reader")
            invalid = backend.update_flatpak("org.example.Reader;id")
        self.assertTrue(result.success)
        self.assertFalse(invalid.success)
        self.assertIn(
            ["flatpak", "update", "--user", "--assumeyes", "--noninteractive", "org.example.Reader"],
            runner.calls,
        )
        self.assertFalse(any("org.example.Reader;id" in call for call in runner.calls))

    def test_failed_package_action_preserves_real_error(self):
        runner = FakeRunner()
        runner.responses[("pkexec", "/usr/bin/apt-get")] = completed(
            [], returncode=100, stderr="repository unavailable"
        )
        backend = StoreBackend(runner=runner)
        with patch("isox_store_backend.shutil.which", return_value="/usr/bin/pkexec"):
            result = backend._privileged_apt(["update"])
        self.assertFalse(result.success)
        self.assertEqual(result.returncode, 100)
        self.assertIn("repository unavailable", result.message)

    def test_update_check_does_not_report_network_failure_as_no_updates(self):
        runner = FakeRunner()
        runner.responses[("apt-get", "-s", "upgrade")] = completed(
            [], returncode=100, stderr="Temporary failure resolving deb.debian.org"
        )
        backend = StoreBackend(runner=runner)
        with patch("isox_store_backend.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Temporary failure resolving"):
                backend.updates()

    def test_update_check_skips_flatpak_without_enabled_user_remote(self):
        runner = FakeRunner()
        runner.responses[("flatpak", "remotes", "--user", "--columns=name")] = completed([])
        backend = StoreBackend(runner=runner)
        with patch("isox_store_backend.shutil.which", return_value="/usr/bin/flatpak"):
            self.assertEqual(backend.updates(), [])
        self.assertFalse(any(call[:2] == ["flatpak", "remote-ls"] for call in runner.calls))

    def test_sound_generator_creates_five_distinct_audible_wav_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sounds"
            generate(output)
            self.assertEqual({path.name for path in output.glob("*.wav")}, set(SOUNDS))
            digests = set()
            for path in output.glob("*.wav"):
                with wave.open(str(path), "rb") as audio:
                    self.assertEqual(audio.getnchannels(), 1)
                    self.assertEqual(audio.getsampwidth(), 2)
                    self.assertEqual(audio.getframerate(), 24000)
                    self.assertGreater(audio.getnframes(), 5000)
                    self.assertLess(audio.getnframes(), 30000)
                    samples = audio.readframes(audio.getnframes())
                    self.assertTrue(any(samples), path.name)
                    self.assertLessEqual(max(abs(value) for value in memoryview(samples).cast("h")), 32767)
                digests.add(hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(len(digests), 5)

    def test_packaged_store_sounds_match_the_original_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "sounds"
            packaged = ROOT / "assets/sounds"
            generate(generated)
            self.assertEqual({path.name for path in packaged.glob("*.wav")}, set(SOUNDS))
            for name in SOUNDS:
                self.assertEqual((packaged / name).read_bytes(), (generated / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
