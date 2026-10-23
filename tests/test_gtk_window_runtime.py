#!/usr/bin/env python3
"""Exercise ISO-X window management and XKB switching under a real X server."""
from __future__ import annotations

import os
import re
import ctypes
import ctypes.util
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(argv: list[str], *, timeout: float = 10) -> str:
    result = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


def wait_for_layout(expected: str) -> None:
    library = ctypes.util.find_library("X11")
    if not library:
        raise AssertionError("libX11 is required to inspect the active XKB group")
    x11 = ctypes.CDLL(library)
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XkbGetState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p]
    x11.XkbGetState.restype = ctypes.c_int
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

    class XkbState(ctypes.Structure):
        _fields_ = [
            ("group", ctypes.c_ubyte),
            ("locked_group", ctypes.c_ubyte),
            ("base_group", ctypes.c_ushort),
            ("latched_group", ctypes.c_ushort),
            ("mods", ctypes.c_ubyte),
            ("base_mods", ctypes.c_ubyte),
            ("latched_mods", ctypes.c_ubyte),
            ("locked_mods", ctypes.c_ubyte),
            ("compat_state", ctypes.c_ubyte),
            ("grab_mods", ctypes.c_ubyte),
            ("compat_grab_mods", ctypes.c_ubyte),
            ("lookup_mods", ctypes.c_ubyte),
            ("compat_lookup_mods", ctypes.c_ubyte),
            ("ptr_buttons", ctypes.c_ushort),
        ]

    display = x11.XOpenDisplay(None)
    if not display:
        raise AssertionError("could not connect to the active X display")
    deadline = time.monotonic() + 3
    try:
        while time.monotonic() < deadline:
            state = XkbState()
            if x11.XkbGetState(display, 0x0100, ctypes.byref(state)) != 0:
                raise AssertionError("XkbGetState failed")
            if state.group == (0 if expected == "ara" else 1):
                return
            time.sleep(0.05)
    finally:
        x11.XCloseDisplay(display)
    raise AssertionError(f"XKB did not switch to {expected!r}")


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
        assert (width, height) == (900, 600), f"resize was not applied: {width}x{height}"

        run(["xdotool", "windowminimize", window_id])
        assert run(["xdotool", "getwindowfocus"]) != window_id, "window did not minimize"
        run(["wmctrl", "-ia", window_id])
        run(["wmctrl", "-ir", window_id, "-b", "add,maximized_vert,maximized_horz"])
        width, height = geometry(window_id)
        assert width >= 1200 and height >= 650, f"maximize was not applied: {width}x{height}"
        run(["wmctrl", "-ir", window_id, "-b", "remove,maximized_vert,maximized_horz"])
        run(["wmctrl", "-ir", window_id, "-e", "0,80,60,900,600"])
        width, height = geometry(window_id)
        assert (width, height) == (900, 600), f"restore/resize failed: {width}x{height}"
    finally:
        stop_window(process, home, window_id, "wm-close")


def exercise_alt_f4() -> None:
    process, home, window_id = launch_window()
    stop_window(process, home, window_id, "alt-f4")


def exercise_close_while_modal_dialog_is_open() -> None:
    process, home, window_id = launch_window()
    run(["xdotool", "windowactivate", "--sync", window_id])
    run(["xdotool", "key", "F12"])
    run(["xdotool", "search", "--sync", "--onlyvisible", "--name", "Dev Mode"], timeout=10)
    stop_window(process, home, window_id, "wm-close")


def exercise_keyboard_layouts() -> None:
    run(["setxkbmap", "-layout", "ara,us", "-option", "grp:alt_shift_toggle"])
    config = run(["setxkbmap", "-query"])
    assert re.search(r"^layout:\s+ara,us$", config, re.MULTILINE), config
    assert "grp:alt_shift_toggle" in config, config
    wait_for_layout("ara")
    run(["xdotool", "keydown", "Alt_L"])
    run(["xdotool", "keydown", "Shift_L"])
    run(["xdotool", "keyup", "Shift_L"])
    run(["xdotool", "keyup", "Alt_L"])
    wait_for_layout("us")
    run(["xdotool", "keydown", "Alt_L"])
    run(["xdotool", "keydown", "Shift_L"])
    run(["xdotool", "keyup", "Shift_L"])
    run(["xdotool", "keyup", "Alt_L"])
    wait_for_layout("ara")


def main() -> int:
    openbox = subprocess.Popen(
        ["openbox", "--sm-disable"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
    )
    try:
        wait_for_openbox()
        exercise_keyboard_layouts()
        exercise_window_management()
        exercise_alt_f4()
        exercise_close_while_modal_dialog_is_open()
    finally:
        openbox.terminate()
        openbox.wait(timeout=5)
    print("PASS: XKB Alt+Shift toggles active ara/us; ISO-X closes with WM_DELETE, Alt+F4, and a modal dialog open, and minimizes, restores, maximizes, and resizes at 1366x768.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())