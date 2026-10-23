#!/usr/bin/env python3
"""Exercise ISO-X window management and XKB switching under a real X server."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from isox_keyboard import current_group, current_layout, toggle_layout


def run(argv: list[str], *, timeout: float = 10) -> str:
    result = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


def xkb_diagnostics() -> str:
    result = subprocess.run(
        ["setxkbmap", "-query"], capture_output=True, text=True, check=False, timeout=5
    )
    keymap = subprocess.run(
        ["xkbcomp", "-xkb", os.environ.get("DISPLAY", ":0"), "-"],
        capture_output=True, text=True, check=False, timeout=5,
    )
    try:
        active = f"active_layout={current_layout()} active_group={current_group()}"
    except RuntimeError as error:
        active = f"active_layout_error={error}"
    symbols = "\n".join(line for line in keymap.stdout.splitlines() if "xkb_symbols" in line or "ISO_Next_Group" in line or "ISO_Prev_Group" in line)
    return f"{active}\nsetxkbmap_exit={result.returncode}\n{result.stdout}{result.stderr}xkbcomp_exit={keymap.returncode}\n{symbols}\n{keymap.stderr[-1000:]}"


def wait_for_layout(expected: str) -> None:
    expected_layout = "AR" if expected == "ara" else "EN"
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if current_layout() == expected_layout:
            return
        time.sleep(0.05)
    raise AssertionError(
        f"XKB did not switch to {expected!r}; expected_group={expected_group};\n{xkb_diagnostics()}"
    )


def geometry(window_id: str) -> tuple[int, int]:
    output = run(["xdotool", "getwindowgeometry", "--shell", window_id])
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    return int(values["WIDTH"]), int(values["HEIGHT"])


def launch_window() -> tuple[subprocess.Popen[str], tempfile.TemporaryDirectory[str], str]:
    home = tempfile.TemporaryDirectory(prefix="isox-gtk-home-")
    env = os.environ.copy()
    env["HOME"] = home.name
    env["XDG_DATA_HOME"] = str(Path(home.name) / ".local/share")
    env["LANG"] = "ar_IQ.UTF-8"
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "app/iso_x_gtk.py")],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        output = run(
            ["xdotool", "search", "--sync", "--onlyvisible", "--name", "ISO-X"],
            timeout=20,
        )
        window_id = output.splitlines()[0]
    except Exception:
        process.terminate()
        _stdout, stderr = process.communicate(timeout=5)
        home.cleanup()
        raise AssertionError(f"ISO-X window did not appear; stderr={stderr}")
    return process, home, window_id


def wait_for_openbox() -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["wmctrl", "-m"], capture_output=True, text=True, check=False, timeout=5
        )
        if result.returncode == 0 and "Openbox" in result.stdout:
            return
        time.sleep(0.05)
    raise AssertionError("Openbox did not become the active window manager")


def stop_window(process: subprocess.Popen[str], home: tempfile.TemporaryDirectory[str], window_id: str, mode: str) -> None:
    try:
        if mode == "wm-close":
            run(["wmctrl", "-ic", window_id])
        else:
            run(["xdotool", "windowactivate", "--sync", window_id])
            run(["xdotool", "key", "--clearmodifiers", "alt+F4"])
        returncode = process.wait(timeout=10)
        if returncode != 0:
            _stdout, stderr = process.communicate()
            raise AssertionError(f"ISO-X exited {returncode}; stderr={stderr}")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        home.cleanup()


def exercise_window_management() -> None:
    process, home, window_id = launch_window()
    try:
        initial_width, initial_height = geometry(window_id)
        assert initial_width < 1200 and initial_height < 740, (
            f"ISO-X unexpectedly starts maximized: {initial_width}x{initial_height}"
        )

        run(["wmctrl", "-ir", window_id, "-e", "0,80,60,900,600"])
        width, height = geometry(window_id)
        assert abs(width - 900) <= 40 and abs(height - 600) <= 40, (
            f"resize was not applied within window-frame extents: {width}x{height}"
        )

        run(["xdotool", "windowminimize", window_id])
        assert run(["xdotool", "getwindowfocus"]) != window_id, "window did not minimize"
        run(["wmctrl", "-ia", window_id])
        run(["wmctrl", "-ir", window_id, "-b", "add,maximized_vert,maximized_horz"])
        width, height = geometry(window_id)
        assert width >= 1200 and height >= 650, f"maximize was not applied: {width}x{height}"
        run(["wmctrl", "-ir", window_id, "-b", "remove,maximized_vert,maximized_horz"])
        run(["wmctrl", "-ir", window_id, "-e", "0,80,60,900,600"])
        width, height = geometry(window_id)
        assert abs(width - 900) <= 40 and abs(height - 600) <= 40, (
            f"restore/resize failed within window-frame extents: {width}x{height}"
        )
    finally:
        stop_window(process, home, window_id, "wm-close")


def exercise_alt_f4() -> None:
    process, home, window_id = launch_window()
    stop_window(process, home, window_id, "alt-f4")


def exercise_close_while_modal_dialog_is_open() -> None:
    process, home, window_id = launch_window()
    run(["xdotool", "windowactivate", "--sync", window_id])
    run(["xdotool", "key", "F12"])
    dialog_id = run(
        ["xdotool", "search", "--sync", "--onlyvisible", "--name", "Dev Mode"],
        timeout=10,
    ).splitlines()[0]
    run(["wmctrl", "-ic", dialog_id])
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        dialog = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", "Dev Mode"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        if dialog.returncode != 0:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Dev Mode dialog did not close")
    stop_window(process, home, window_id, "wm-close")


def exercise_keyboard_layouts() -> None:
    run(["setxkbmap", "-layout", "ara,us", "-option", "grp:alt_shift_toggle_bidir"])
    config = run(["setxkbmap", "-query"])
    assert re.search(r"^layout:\s+ara,us$", config, re.MULTILINE), config
    assert "grp:alt_shift_toggle_bidir" in config, config
    wait_for_layout("ara")
    assert toggle_layout() == "EN", "ISO-X keyboard API did not switch AR to EN"
    wait_for_layout("us")
    assert toggle_layout() == "AR", "ISO-X keyboard API did not switch EN to AR"
    wait_for_layout("ara")
    config = run(["setxkbmap", "-query"])
    assert re.search(r"^layout:\s+ara,us$", config, re.MULTILINE), config


def _wait_for_text(path: Path, expected: str) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.is_file() and path.read_text(encoding="utf-8") == expected:
            return
        time.sleep(0.05)
    actual = path.read_text(encoding="utf-8") if path.is_file() else "<no input received>"
    raise AssertionError(f"expected typed text {expected!r}, received {actual!r}")


def exercise_gtk_text_input() -> None:
    with tempfile.TemporaryDirectory(prefix="isox-gtk-input-") as directory:
        result_path = Path(directory) / "entry.txt"
        env = os.environ.copy()
        env["ISOX_INPUT_RESULT"] = str(result_path)
        source = textwrap.dedent("""
            import os
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            from pathlib import Path
            window = Gtk.Window(title="ISO-X keyboard input probe")
            entry = Gtk.Entry()
            entry.connect("changed", lambda widget: Path(os.environ["ISOX_INPUT_RESULT"]).write_text(widget.get_text(), encoding="utf-8"))
            window.add(entry)
            window.connect("destroy", Gtk.main_quit)
            window.show_all()
            entry.grab_focus()
            Gtk.main()
        """)
        process = subprocess.Popen(
            [sys.executable, "-c", source], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        try:
            window_id = run(["xdotool", "search", "--sync", "--onlyvisible", "--name", "ISO-X keyboard input probe"], timeout=10).splitlines()[0]
            run(["xdotool", "windowactivate", "--sync", window_id])
            run(["xdotool", "key", "38"])
            _wait_for_text(result_path, "ش")
            assert toggle_layout() == "EN"
            wait_for_layout("us")
            run(["xdotool", "key", "ctrl+a", "BackSpace"])
            run(["xdotool", "key", "38"])
            _wait_for_text(result_path, "a")
        finally:
            if process.poll() is None:
                process.terminate()
                _stdout, stderr = process.communicate(timeout=5)
                if process.returncode not in (-15, 0):
                    raise AssertionError(f"GTK input probe failed: {stderr}")


def exercise_terminal_text_input() -> None:
    if not shutil.which("xterm"):
        print("NOT_RUN: xterm input probe requires xterm")
        return
    with tempfile.TemporaryDirectory(prefix="isox-terminal-input-") as directory:
        result_path = Path(directory) / "terminal.txt"
        for layout, expected in (("ara", "ش"), ("us", "a")):
            run(["setxkbmap", "-layout", "ara,us", "-option", "grp:alt_shift_toggle_bidir"])
            if layout == "us":
                assert toggle_layout() == "EN"
            else:
                assert current_layout() == "AR"
            wait_for_layout(layout)
            env = os.environ.copy()
            env["ISOX_TERMINAL_RESULT"] = str(result_path)
            command = (
                "import os; from pathlib import Path; "
                "Path(os.environ['ISOX_TERMINAL_RESULT']).write_text(input(), encoding='utf-8')"
            )
            process = subprocess.Popen(
                ["xterm", "-T", f"ISO-X terminal input {layout}", "-e", sys.executable, "-c", command],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            try:
                window_id = run(["xdotool", "search", "--sync", "--onlyvisible", "--name", f"ISO-X terminal input {layout}"], timeout=10).splitlines()[0]
                run(["xdotool", "windowactivate", "--sync", window_id])
                run(["xdotool", "key", "38", "Return"])
                _wait_for_text(result_path, expected)
                process.wait(timeout=5)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            result_path.unlink(missing_ok=True)


def main() -> int:
    openbox = subprocess.Popen(
        ["openbox", "--sm-disable"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
    )
    try:
        wait_for_openbox()
        exercise_keyboard_layouts()
        exercise_gtk_text_input()
        exercise_terminal_text_input()
        exercise_window_management()
        exercise_alt_f4()
        exercise_close_while_modal_dialog_is_open()
    finally:
        openbox.terminate()
        openbox.wait(timeout=5)
    print("PASS: XKB session map toggle switches AR↔EN; GTK Entry and xterm receive Arabic/English input; ISO-X window lifecycle checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())