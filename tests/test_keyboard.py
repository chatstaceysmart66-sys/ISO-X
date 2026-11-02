#!/usr/bin/env python3
"""Tests for persisted Arabic/English XKB layout preferences."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import isox_keyboard  # noqa: E402


class KeyboardPreferenceTests(unittest.TestCase):
    def test_toggle_saves_selected_layout_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / "iso-x" / "keyboard-layout"
            with (
                patch.object(isox_keyboard, "PREFERENCE_PATH", preference),
                patch.object(isox_keyboard, "current_layout", side_effect=("AR", "EN")),
                patch.object(
                    isox_keyboard.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ) as run,
            ):
                self.assertEqual(isox_keyboard.toggle_layout(), "EN")

            self.assertEqual(preference.read_text(encoding="ascii"), "EN\n")
            self.assertEqual(preference.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                run.call_args.args[0],
                ["setxkbmap", "-layout", "us,ara", "-option", "grp:alt_shift_toggle_bidir"],
            )

    def test_restore_uses_persisted_preference(self):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / "keyboard-layout"
            preference.write_text("EN\n", encoding="ascii")
            with (
                patch.object(isox_keyboard, "PREFERENCE_PATH", preference),
                patch.object(isox_keyboard, "_apply_layout") as apply,
                patch.object(isox_keyboard, "current_layout", return_value="EN"),
            ):
                self.assertEqual(isox_keyboard.restore_layout(), "EN")
            apply.assert_called_once_with("EN")

    def test_restore_defaults_to_arabic_when_no_preference_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / "not-created"
            with (
                patch.object(isox_keyboard, "PREFERENCE_PATH", preference),
                patch.object(isox_keyboard, "_apply_layout") as apply,
                patch.object(isox_keyboard, "current_layout", return_value="AR"),
            ):
                self.assertEqual(isox_keyboard.restore_layout(), "AR")
            apply.assert_called_once_with("AR")

    def test_invalid_preference_fails_without_changing_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / "keyboard-layout"
            preference.write_text("FR\n", encoding="ascii")
            with (
                patch.object(isox_keyboard, "PREFERENCE_PATH", preference),
                patch.object(isox_keyboard, "_apply_layout") as apply,
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid keyboard layout preference"):
                    isox_keyboard.restore_layout()
            apply.assert_not_called()

    def test_failed_layout_change_does_not_save_a_preference(self):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / "iso-x" / "keyboard-layout"
            with (
                patch.object(isox_keyboard, "PREFERENCE_PATH", preference),
                patch.object(isox_keyboard, "current_layout", return_value="AR"),
                patch.object(
                    isox_keyboard.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 1, "", "X server unavailable"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "X server unavailable"):
                    isox_keyboard.toggle_layout()
            self.assertFalse(preference.exists())


if __name__ == "__main__":
    unittest.main()
