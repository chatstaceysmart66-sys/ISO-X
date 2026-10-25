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


MAXIMIZE_BUTTON_RIGHT_OFFSET = 52
MINIMIZE_BUTTON_RIGHT_OFFSET = 76


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


def screen_geometry(window_id: str) -> tuple[int, int, int, int]:
    output = run(["xwininfo", "-id", window_id])
    coordinates = [
        re.search(pattern, output)
        for pattern in (
            r"Absolute upper-left X:\s+(\d+)",
            r"Absolute upper-left Y:\s+(\d+)",
            r"Width:\s+(\d+)",
            r"Height:\s+(\d+)",
        )
    ]
    assert all(coordinates), f"Could not read X11 window geometry:\n{output}"
    return tuple(int(match[1]) for match in coordinates)


def pointer_drag(x: int, y: int, dx: int, dy: int) -> None:
    steps = max(4, (max(abs(dx), abs(dy)) + 7) // 8)
    command = ["xdotool", "mousemove", str(x), str(y), "mousedown", "1", "sleep", "0.2"]
    for step in range(1, steps + 1):
        next_x = x + round(dx * step / steps)
        next_y = y + round(dy * step / steps)
        command.extend(("mousemove", str(next_x), str(next_y), "sleep", "0.025"))
    command.extend(("mouseup", "1"))
    run(command)
    time.sleep(0.25)


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


def wait_for_window_focus(window_id: str, timeout: float = 3) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if run(["xdotool", "getwindowfocus"]) == window_id:
            return
        time.sleep(0.05)
    actual = run(["xdotool", "getwindowfocus"])
    raise AssertionError(f"window focus did not move to {window_id}; actual focus is {actual}")


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

        def click_titlebar_button(right_offset: int) -> None:
            output = run(["xwininfo", "-id", window_id])
            x = int(re.search(r"Absolute upper-left X:\s+(\d+)", output)[1])
            y = int(re.search(r"Absolute upper-left Y:\s+(\d+)", output)[1])
            width = int(re.search(r"Width:\s+(\d+)", output)[1])
            extents = run(["xprop", "-id", window_id, "_NET_FRAME_EXTENTS"])
            top = int(re.search(r"=\s*\d+,\s*\d+,\s*(\d+)", extents)[1])
            run(["xdotool", "mousemove", str(x + width - right_offset), str(y - top // 2), "click", "1"])
            time.sleep(0.25)

        click_titlebar_button(MAXIMIZE_BUTTON_RIGHT_OFFSET)
        assert "MAXIMIZED_VERT" in run(["xprop", "-id", window_id, "_NET_WM_STATE"]), (
            "native maximize button did not maximize the ISO-X window"
        )
        click_titlebar_button(MAXIMIZE_BUTTON_RIGHT_OFFSET)
        assert "MAXIMIZED_VERT" not in run(["xprop", "-id", window_id, "_NET_WM_STATE"]), (
            "native maximize button did not restore the ISO-X window"
        )

        click_titlebar_button(MINIMIZE_BUTTON_RIGHT_OFFSET)
        assert "HIDDEN" in run(["xprop", "-id", window_id, "_NET_WM_STATE"]), (
            "native minimize button did not iconify the ISO-X window"
        )
        assert process.poll() is None, "native minimize button terminated the ISO-X application"
        run(["wmctrl", "-ia", window_id])
        wait_for_window_focus(window_id)

        run(["wmctrl", "-ir", window_id, "-e", "0,80,60,900,660"])
        width, height = geometry(window_id)
        assert abs(width - 900) <= 40 and abs(height - 660) <= 20, (
            f"resize target 900x660 was not applied: {width}x{height}"
        )

        run(["xdotool", "windowminimize", window_id])
        assert run(["xdotool", "getwindowfocus"]) != window_id, "window did not minimize"
        run(["wmctrl", "-ia", window_id])
        run(["wmctrl", "-ir", window_id, "-b", "add,maximized_vert,maximized_horz"])
        width, height = geometry(window_id)
        assert width >= 1200 and height >= 650, f"maximize was not applied: {width}x{height}"
        run(["wmctrl", "-ir", window_id, "-b", "remove,maximized_vert,maximized_horz"])
        run(["wmctrl", "-ir", window_id, "-e", "0,80,60,900,660"])
        width, height = geometry(window_id)
        assert abs(width - 900) <= 40 and abs(height - 660) <= 20, (
            f"restore/resize target 900x660 failed: {width}x{height}"
        )
    finally:
        stop_window(process, home, window_id, "wm-close")


def exercise_pointer_move_and_resize() -> None:
    process, home, window_id = launch_window()
    try:
        resize_extents = run(["xprop", "-id", window_id, "_NET_FRAME_EXTENTS"])
        extents_match = re.search(r"=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", resize_extents)
        assert extents_match, f"Could not read Openbox frame extents: {resize_extents}"
        left, right, top, bottom = map(int, extents_match.groups())
        gestures = (
            ("top", lambda x, y, width, height: (x + width // 2, y - top), (0, -20), "height"),
            ("bottom", lambda x, y, width, height: (x + width // 2, y + height + bottom - 1), (0, 20), "height"),
            ("left", lambda x, y, width, height: (x - left, y + height // 2), (-20, 0), "width"),
            ("right", lambda x, y, width, height: (x + width + right - 1, y + height // 2), (20, 0), "width"),
            ("top-left", lambda x, y, width, height: (x - left, y - top), (-20, -20), "both"),
            ("top-right", lambda x, y, width, height: (x + width + right - 1, y - top), (20, -20), "both"),
            ("bottom-left", lambda x, y, width, height: (x - left, y + height + bottom - 1), (-20, 20), "both"),
            ("bottom-right", lambda x, y, width, height: (x + width + right - 1, y + height + bottom - 1), (20, 20), "both"),
        )

        run(["wmctrl", "-ir", window_id, "-e", "0,180,30,900,620"])
        time.sleep(0.2)
        x, y, width, height = screen_geometry(window_id)
        pointer_drag(x + width // 2, y - top // 2, 28, 20)
        moved = screen_geometry(window_id)
        assert abs(moved[0] - x - 28) <= 4 and abs(moved[1] - y - 20) <= 4, (
            f"titlebar drag did not move the window: {(x, y)} => {moved[:2]}"
        )

        for name, point, delta, dimensions in gestures:
            run(["wmctrl", "-ir", window_id, "-e", "0,180,30,900,620"])
            time.sleep(0.15)
            before = screen_geometry(window_id)
            pointer_drag(*point(*before), *delta)
            after = screen_geometry(window_id)
            changed_width = before[2] != after[2]
            changed_height = before[3] != after[3]
            assert (
                changed_width and changed_height if dimensions == "both"
                else changed_width if dimensions == "width"
                else changed_height
            ), f"{name} pointer drag did not resize the expected dimension: {before} => {after}"
    finally:
        stop_window(process, home, window_id, "wm-close")


def exercise_titlebar_double_click() -> None:
    process, home, window_id = launch_window()
    try:
        output = run(["xwininfo", "-id", window_id])
        x = int(re.search(r"Absolute upper-left X:\s+(\d+)", output)[1])
        y = int(re.search(r"Absolute upper-left Y:\s+(\d+)", output)[1])
        width = int(re.search(r"Width:\s+(\d+)", output)[1])
        extents = run(["xprop", "-id", window_id, "_NET_FRAME_EXTENTS"])
        top = int(re.search(r"=\s*\d+,\s*\d+,\s*(\d+)", extents)[1])

        def double_click_titlebar() -> None:
            run(["xdotool", "mousemove", str(x + width // 2), str(y - top // 2),
                 "click", "--repeat", "2", "--delay", "100", "1"])

        double_click_titlebar()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if "MAXIMIZED_VERT" in run(["xprop", "-id", window_id, "_NET_WM_STATE"]):
                break
            time.sleep(0.05)
        else:
            raise AssertionError("titlebar double-click did not maximize the ISO-X window")

        output = run(["xwininfo", "-id", window_id])
        x = int(re.search(r"Absolute upper-left X:\s+(\d+)", output)[1])
        y = int(re.search(r"Absolute upper-left Y:\s+(\d+)", output)[1])
        width = int(re.search(r"Width:\s+(\d+)", output)[1])
        double_click_titlebar()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if "MAXIMIZED_VERT" not in run(["xprop", "-id", window_id, "_NET_WM_STATE"]):
                return
            time.sleep(0.05)
        raise AssertionError("titlebar double-click did not restore the ISO-X window")
    finally:
        stop_window(process, home, window_id, "wm-close")


def exercise_close_button() -> None:
    process, home, window_id = launch_window()
    try:
        output = run(["xwininfo", "-id", window_id])
        x = int(re.search(r"Absolute upper-left X:\s+(\d+)", output)[1])
        y = int(re.search(r"Absolute upper-left Y:\s+(\d+)", output)[1])
        width = int(re.search(r"Width:\s+(\d+)", output)[1])
        extents = run(["xprop", "-id", window_id, "_NET_FRAME_EXTENTS"])
        top = int(re.search(r"=\s*\d+,\s*\d+,\s*(\d+)", extents)[1])
        run(["xdotool", "mousemove", str(x + width - 12), str(y - top // 2), "click", "1"])
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired as error:
            raise AssertionError("Openbox close button did not close the ISO-X window") from error
        assert returncode == 0, f"ISO-X exited {returncode} after clicking its close button"
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        home.cleanup()


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


def exercise_alt_tab_focus_routing() -> None:
    source = textwrap.dedent("""
        import os
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        from pathlib import Path
        window = Gtk.Window(title=os.environ["ISOX_PROBE_TITLE"])
        entry = Gtk.Entry()
        entry.connect("changed", lambda widget: Path(os.environ["ISOX_INPUT_RESULT"]).write_text(widget.get_text(), encoding="utf-8"))
        window.add(entry)
        window.connect("destroy", Gtk.main_quit)
        window.show_all()
        entry.grab_focus()
        Gtk.main()
    """)
    with tempfile.TemporaryDirectory(prefix="isox-focus-routing-") as directory:
        processes: list[subprocess.Popen[str]] = []
        windows: dict[str, str] = {}
        results = {name: Path(directory) / f"{name}.txt" for name in ("first", "second")}
        try:
            for name in ("first", "second"):
                env = os.environ.copy()
                env["ISOX_PROBE_TITLE"] = f"ISO-X focus probe {name}"
                env["ISOX_INPUT_RESULT"] = str(results[name])
                process = subprocess.Popen(
                    [sys.executable, "-c", source], env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                )
                processes.append(process)
                windows[name] = run(
                    ["xdotool", "search", "--sync", "--onlyvisible", "--name", env["ISOX_PROBE_TITLE"]],
                    timeout=10,
                ).splitlines()[0]

            run(["xdotool", "windowactivate", "--sync", windows["first"]])
            run(["xdotool", "type", "--clearmodifiers", "first"])
            _wait_for_text(results["first"], "first")
            run(["xdotool", "windowactivate", "--sync", windows["second"]])
            run(["xdotool", "type", "--clearmodifiers", "second"])
            _wait_for_text(results["second"], "second")
            assert results["first"].read_text(encoding="utf-8") == "first", "background GTK window received input"

            run(["xdotool", "key", "--clearmodifiers", "alt+Tab"])
            assert run(["xdotool", "getwindowfocus"]) == windows["first"], "Alt+Tab did not focus the other GTK window"
            run(["xdotool", "type", "--clearmodifiers", "!"])
            _wait_for_text(results["first"], "first!")
            assert results["second"].read_text(encoding="utf-8") == "second", "Alt+Tab sent input to the wrong GTK window"
        finally:
            for window_id in windows.values():
                subprocess.run(["wmctrl", "-ic", window_id], check=False, capture_output=True, timeout=5)
            for process in processes:
                if process.poll() is None:
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=5)


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
        ["openbox", "--sm-disable", "--config-file", str(ROOT / "desktop/openbox-rc.xml")],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    try:
        wait_for_openbox()
        exercise_keyboard_layouts()
        exercise_gtk_text_input()
        exercise_alt_tab_focus_routing()
        exercise_terminal_text_input()
        exercise_window_management()
        exercise_pointer_move_and_resize()
        exercise_titlebar_double_click()
        exercise_close_button()
        exercise_alt_f4()
        exercise_close_while_modal_dialog_is_open()
    finally:
        openbox.terminate()
        openbox.wait(timeout=5)
    print("PASS: Openbox window controls, titlebar movement, all eight resize zones, Alt+Tab focus routing, and GTK/xterm AR↔EN input checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())