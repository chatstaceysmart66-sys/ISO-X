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
import isox_keyboard
from isox_keyboard import current_group, current_layout, toggle_layout


MAXIMIZE_BUTTON_RIGHT_OFFSET = 28
MINIMIZE_BUTTON_RIGHT_OFFSET = 52


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
        f"XKB did not switch to {expected!r}; expected_layout={expected_layout};\n{xkb_diagnostics()}"
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


def wait_for_window_state(window_id: str, state: str, present: bool, timeout: float = 3) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        states = run(["xprop", "-id", window_id, "_NET_WM_STATE"])
        if (state in states) is present:
            return
        time.sleep(0.05)
    raise AssertionError(
        f"window state {state!r} did not become present={present}; "
        f"actual state: {run(['xprop', '-id', window_id, '_NET_WM_STATE'])}"
    )


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

        click_titlebar_button(MAXIMIZE_BUTTON_RIGHT_OFFSET)
        wait_for_window_state(window_id, "MAXIMIZED_VERT", True)
        click_titlebar_button(MAXIMIZE_BUTTON_RIGHT_OFFSET)
        wait_for_window_state(window_id, "MAXIMIZED_VERT", False)

        click_titlebar_button(MINIMIZE_BUTTON_RIGHT_OFFSET)
        wait_for_window_state(window_id, "HIDDEN", True)
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


def exercise_click_to_focus_content() -> None:
    if int(run(["xdotool", "getdisplaygeometry"]).split()[0]) < 1050:
        raise AssertionError("Openbox click-to-focus test needs a virtual display at least 1050 pixels wide")
    with tempfile.TemporaryDirectory(prefix="isox-focus-") as directory:
        root = Path(directory)
        source = textwrap.dedent("""
            import os
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk, GLib
            from pathlib import Path
            name = os.environ["ISOX_FOCUS_NAME"]
            window = Gtk.Window(title=name)
            window.set_default_size(440, 240)
            window.move(int(os.environ["ISOX_FOCUS_X"]), 80)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            box.set_border_width(20)
            entry = Gtk.Entry()
            entry.connect(
                "changed",
                lambda widget: Path(os.environ["ISOX_FOCUS_ENTRY"]).write_text(
                    widget.get_text(), encoding="utf-8"
                ),
            )
            button = Gtk.Button(label="Click me")
            button.connect(
                "clicked",
                lambda _widget: Path(os.environ["ISOX_FOCUS_BUTTON"]).write_text(
                    "clicked", encoding="utf-8"
                ),
            )
            box.pack_start(entry, False, False, 0)
            box.pack_start(button, False, False, 0)
            window.add(box)
            window.connect("destroy", Gtk.main_quit)
            window.show_all()
            Gtk.main()
        """)
        processes = []
        try:
            for name, x in (("Focus Probe A", 40), ("Focus Probe B", 550)):
                app_root = root / name.replace(" ", "-")
                app_root.mkdir()
                env = os.environ.copy()
                env.update({
                    "ISOX_FOCUS_NAME": name,
                    "ISOX_FOCUS_X": str(x),
                    "ISOX_FOCUS_ENTRY": str(app_root / "entry.txt"),
                    "ISOX_FOCUS_BUTTON": str(app_root / "button.txt"),
                })
                process = subprocess.Popen(
                    [sys.executable, "-c", source], env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                )
                processes.append((process, app_root, name))
                run(["xdotool", "search", "--sync", "--onlyvisible", "--name", name], timeout=10)

            ids = {}
            for _process, _app_root, name in processes:
                ids[name] = run(
                    ["xdotool", "search", "--onlyvisible", "--name", name], timeout=5
                ).splitlines()[0]

            def window_origin(window_id: str) -> tuple[int, int]:
                output = run(["xwininfo", "-id", window_id])
                coordinates = [
                    re.search(pattern, output)
                    for pattern in (
                        r"Absolute upper-left X:\s+(\d+)",
                        r"Absolute upper-left Y:\s+(\d+)",
                    )
                ]
                assert all(coordinates), f"Could not read GTK client origin:\n{output}"
                return int(coordinates[0][1]), int(coordinates[1][1])

            def click(window_id: str, offset_y: int) -> str:
                origin_x, origin_y = window_origin(window_id)
                x, y = origin_x + 220, origin_y + offset_y
                run(["xdotool", "mousemove", str(x), str(y), "click", "1"])
                return f"{x},{y}"

            second = root / "Focus-Probe-B"
            run(["wmctrl", "-ia", ids["Focus Probe A"]])
            assert run(["xdotool", "getwindowfocus"]) == ids["Focus Probe A"]
            entry_point = click(ids["Focus Probe B"], 37)
            try:
                wait_for_window_focus(ids["Focus Probe B"])
            except AssertionError as error:
                raise AssertionError(
                    f"{error}; entry click={entry_point}; windows={run(['wmctrl', '-lG'])}; "
                    f"pointer={run(['xdotool', 'getmouselocation', '--shell'])}; "
                    f"target={run(['xwininfo', '-id', ids['Focus Probe B']])}"
                ) from error
            run(["xdotool", "type", "--clearmodifiers", "content-click"])
            _wait_for_text(second / "entry.txt", "content-click")

            run(["wmctrl", "-ia", ids["Focus Probe A"]])
            click(ids["Focus Probe B"], 83)
            wait_for_window_focus(ids["Focus Probe B"])
            _wait_for_text(second / "button.txt", "clicked")
        finally:
            for process, _app_root, name in processes:
                if process.poll() is None:
                    windows = subprocess.run(
                        ["xdotool", "search", "--onlyvisible", "--name", name],
                        capture_output=True, text=True, check=False, timeout=5,
                    )
                    if windows.returncode == 0:
                        subprocess.run(
                            ["wmctrl", "-ic", windows.stdout.splitlines()[0]],
                            capture_output=True, check=False, timeout=5,
                        )
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=5)


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
            gi.require_version("Gdk", "3.0")
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
            run(["xdotool", "key", "25"])
            _wait_for_text(result_path, "شص")
            run(["xdotool", "type", "--clearmodifiers", "و"])
            _wait_for_text(result_path, "شصو")
            assert toggle_layout() == "EN"
            wait_for_layout("us")
            run(["xdotool", "key", "ctrl+a", "BackSpace"])
            run(["xdotool", "key", "38"])
            _wait_for_text(result_path, "a")
            run(["xdotool", "key", "w"])
            _wait_for_text(result_path, "aw")
            assert run(["xdotool", "getwindowfocus"]) == window_id, (
                "typing W opened an Openbox menu instead of reaching the focused entry"
            )
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


def exercise_application_launcher() -> None:
    with tempfile.TemporaryDirectory(prefix="isox-launcher-") as directory:
        root = Path(directory)
        first_root = root / "user-applications"
        second_root = root / "system-applications"
        first_root.mkdir()
        second_root.mkdir()
        marker = root / "launched.txt"
        ready = root / "ready.txt"
        hide_count = root / "hide-count.txt"
        result = root / "launcher-result.txt"
        refreshed_entry = first_root / "newly-installed.desktop"
        launch_script = root / "record-launch.py"
        launch_script.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('launched', encoding='utf-8')\n",
            encoding="utf-8",
        )

        def write_entry(path: Path, name: str, executable: str = "/usr/bin/true", extra: str = "") -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={name}\n"
                f"Exec={executable}\n"
                "Icon=application-x-executable\n"
                "Terminal=false\n"
                "Categories=Utility;\n"
                f"{extra}",
                encoding="utf-8",
            )

        preferred = (
            ("firefox-esr.desktop", "Firefox", f"/usr/bin/python3 {launch_script}"),
            ("thunar.desktop", "Files"),
            ("isox-store.desktop", "ISO-X Store"),
            ("galculator.desktop", "Calculator"),
            ("xfce4-terminal.desktop", "Terminal"),
            ("xfce4-settings-manager.desktop", "Settings"),
            ("vlc.desktop", "Media"),
            ("xfce4-screenshooter.desktop", "Screenshot"),
        )
        for desktop_id, name, *command in preferred:
            write_entry(
                first_root / desktop_id,
                name,
                command[0] if command else "/usr/bin/true",
            )
        for index in range(50):
            entry = first_root / f"secondary-{index:02}.desktop"
            write_entry(entry, f"Secondary Application {index:02}")
        write_entry(
            second_root / "secondary-00.desktop",
            "Duplicate that must be shadowed",
        )
        write_entry(
            second_root / "internal.desktop",
            "System copy of hidden internal tool",
        )
        write_entry(
            second_root / "hidden.desktop",
            "System copy of hidden desktop entry",
        )
        write_entry(
            first_root / "internal.desktop",
            "Hidden internal tool",
            extra="NoDisplay=true\n",
        )
        write_entry(
            first_root / "hidden.desktop",
            "Hidden desktop entry",
            extra="Hidden=true\n",
        )
        write_entry(
            first_root / "Development" / "Nested.desktop",
            "Nested utility",
        )

        source = textwrap.dedent("""
            import os
            import sys
            from pathlib import Path
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import GLib
            sys.path.insert(0, os.environ["ISOX_APP_DIR"])
            import isox_launcher

            isox_launcher.APPLICATION_ROOTS = (
                os.environ["ISOX_TEST_APPS_USER"],
                os.environ["ISOX_TEST_APPS_SYSTEM"],
            )
            application = isox_launcher.LauncherApplication()
            result_path = Path(os.environ["ISOX_LAUNCHER_RESULT"])
            ready_path = Path(os.environ["ISOX_LAUNCHER_READY"])
            hide_path = Path(os.environ["ISOX_LAUNCHER_HIDES"])
            refreshed_entry = Path(os.environ["ISOX_REFRESHED_ENTRY"])
            trace_path = Path(os.environ["ISOX_LAUNCHER_TRACE"])
            click_path = Path(os.environ["ISOX_LAUNCHER_CLICK"])
            hide_count = 0

            def reopen():
                application.window.toggle()
                expected_count = 60 if hide_count == 1 else 59
                assert len(application.window.apps) == expected_count, (
                    "launcher did not refresh installed applications when reopened"
                )
                if hide_count == 1:
                    refreshed_entry.unlink()
                return GLib.SOURCE_REMOVE

            def hidden(_window):
                global hide_count
                hide_count += 1
                hide_path.write_text(str(hide_count), encoding="utf-8")
                if hide_count < 3:
                    GLib.timeout_add(350, reopen)
                else:
                    GLib.timeout_add(350, application.quit)

            def prepare_launch_click():
                try:
                    window = application.window
                    launch_button = window.primary_grid.get_child_at(0, 0)
                    assert launch_button is not None
                    allocation = launch_button.get_allocation()
                    assert allocation.width > 1 and allocation.height > 1, (
                        f"primary app button was not allocated: {allocation.width}x{allocation.height}"
                    )
                    local_x, local_y = launch_button.translate_coordinates(
                        window, allocation.width // 2, allocation.height // 2
                    )
                    origin = window.get_position()
                    click_path.write_text(
                        f"{origin[0] + local_x + 1},{origin[1] + local_y + 1}",
                        encoding="utf-8",
                    )
                    ready_path.write_text("READY", encoding="utf-8")
                except Exception as error:
                    result_path.write_text(f"ERROR: {type(error).__name__}: {error}", encoding="utf-8")
                    application.quit()
                return GLib.SOURCE_REMOVE

            def exercise():
                try:
                    window = application.window
                    close_if_outside = window._close_if_outside

                    def trace_outside_click(x, y):
                        trace_path.write_text(f"{x},{y}", encoding="utf-8")
                        return close_if_outside(x, y)

                    window._close_if_outside = trace_outside_click
                    assert len(window.apps) == 59, (
                        f"expected 59 visible desktop entries, got {len(window.apps)}: "
                        f"{[app.get_id() for app in window.apps]}"
                    )
                    app_names = {app.get_display_name() for app in window.apps}
                    assert "System copy of hidden internal tool" not in app_names
                    assert "System copy of hidden desktop entry" not in app_names
                    assert len(window.preferred) == 8
                    assert len(window.primary_grid.get_children()) == 8
                    window.connect("hide", hidden)
                    window.more_button.emit("clicked")
                    assert len(window.all_list.get_children()) == 8
                    while window.all_more.get_visible():
                        window._load_more(None)
                    assert len(window.all_list.get_children()) == 59
                    window.search.set_text("Application 49")
                    window._search_changed(window.search)
                    assert len(window.all_list.get_children()) == 1
                    window.search.set_text("")
                    window._search_changed(window.search)
                    assert len(window.all_list.get_children()) == 8
                    window.back_button.emit("clicked")
                    assert window.primary_page.get_visible()
                    assert not window.all_page.get_visible()
                    window.more_button.emit("clicked")
                    assert len(window.all_list.get_children()) == 8
                    refreshed_entry.write_text(
                        "[Desktop Entry]\\n"
                        "Type=Application\\n"
                        "Name=Newly installed application\\n"
                        "Exec=/usr/bin/true\\n"
                        "Icon=application-x-executable\\n"
                        "Terminal=false\\n"
                        "Categories=Utility;\\n",
                        encoding="utf-8",
                    )
                    window._refresh_applications()
                    assert len(window.apps) == 60
                    result_path.write_text(
                        f"pointer-status={window.status.get_text() or '<empty>'}",
                        encoding="utf-8",
                    )
                    window.back_button.emit("clicked")
                    GLib.timeout_add(100, prepare_launch_click)
                except Exception as error:
                    result_path.write_text(f"ERROR: {type(error).__name__}: {error}", encoding="utf-8")
                    application.quit()
                return GLib.SOURCE_REMOVE

            application.connect("activate", lambda *_args: GLib.idle_add(exercise))
            raise SystemExit(application.run([]))
        """)
        env = os.environ.copy()
        env.update({
            "ISOX_APP_DIR": str(ROOT / "app"),
            "ISOX_TEST_APPS_USER": str(first_root),
            "ISOX_TEST_APPS_SYSTEM": str(second_root),
            "ISOX_LAUNCHER_RESULT": str(result),
            "ISOX_LAUNCHER_READY": str(ready),
            "ISOX_LAUNCHER_HIDES": str(hide_count),
            "ISOX_REFRESHED_ENTRY": str(refreshed_entry),
            "ISOX_LAUNCHER_TRACE": str(root / "outside-click.txt"),
            "ISOX_LAUNCHER_CLICK": str(root / "app-click.txt"),
        })
        process = subprocess.Popen(
            [sys.executable, "-c", source], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        try:
            try:
                _wait_for_text(ready, "READY")
            except AssertionError as error:
                if process.poll() is None:
                    process.terminate()
                _stdout, stderr = process.communicate(timeout=5)
                detail = result.read_text(encoding="utf-8") if result.is_file() else ""
                raise AssertionError(
                    f"{error}; launcher result={detail!r}; stderr={stderr}"
                ) from error
            click_x, click_y = (
                int(value) for value in (root / "app-click.txt").read_text(encoding="utf-8").split(",")
            )
            window_id = run(
                ["xdotool", "search", "--sync", "--onlyvisible", "--name", "ISO-X Applications"],
                timeout=10,
            ).splitlines()[0]
            x, y, width, height = screen_geometry(window_id)
            assert x <= click_x < x + width and y <= click_y < y + height, (
                f"app click target {(click_x, click_y)} is outside launcher {(x, y, width, height)}"
            )
            run(["xdotool", "mousemove", str(click_x), str(click_y), "click", "1"])
            try:
                _wait_for_text(marker, "launched")
            except AssertionError as error:
                if process.poll() is None:
                    process.terminate()
                _stdout, stderr = process.communicate(timeout=5)
                detail = result.read_text(encoding="utf-8") if result.is_file() else ""
                raise AssertionError(
                    f"{error}; launcher result={detail!r}; click={(click_x, click_y)}; "
                    f"window={(x, y, width, height)}; stderr={stderr}"
                ) from error
            _wait_for_text(hide_count, "1")
            window_id = run(
                ["xdotool", "search", "--sync", "--onlyvisible", "--name", "ISO-X Applications"],
                timeout=10,
            ).splitlines()[0]
            x, y, width, height = screen_geometry(window_id)
            assert not (x <= 2 < x + width and y <= 2 < y + height), (
                "launcher window placement overlaps the desktop click-away target"
            )
            run(["xdotool", "windowactivate", "--sync", window_id])
            run(["xdotool", "key", "Escape"])
            _wait_for_text(hide_count, "2")
            window_id = run(
                ["xdotool", "search", "--sync", "--onlyvisible", "--name", "ISO-X Applications"],
                timeout=10,
            ).splitlines()[0]
            run(["xdotool", "windowactivate", "--sync", window_id])
            run(["xdotool", "mousemove", "2", "2", "click", "1"])
            try:
                _wait_for_text(hide_count, "3")
            except AssertionError as error:
                trace = (root / "outside-click.txt").read_text(encoding="utf-8") if (root / "outside-click.txt").is_file() else "<no pointer event delivered>"
                status = result.read_text(encoding="utf-8") if result.is_file() else "<no status>"
                raise AssertionError(
                    f"{error}; outside-click trace={trace}; launcher status={status}"
                ) from error
            returncode = process.wait(timeout=10)
            if returncode != 0:
                _stdout, stderr = process.communicate()
                raise AssertionError(f"launcher GUI test exited {returncode}: {stderr}")
            assert not result.exists() or not result.read_text(encoding="utf-8").startswith("ERROR:"), (
                result.read_text(encoding="utf-8") if result.exists() else ""
            )
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


def main() -> int:
    keyboard_config = tempfile.TemporaryDirectory(prefix="isox-keyboard-runtime-")
    isox_keyboard.PREFERENCE_PATH = Path(keyboard_config.name) / "iso-x" / "keyboard-layout"
    openbox = subprocess.Popen(
        ["openbox", "--sm-disable", "--config-file", str(ROOT / "desktop/openbox-rc.xml")],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    try:
        wait_for_openbox()
        exercise_keyboard_layouts()
        exercise_gtk_text_input()
        exercise_application_launcher()
        exercise_click_to_focus_content()
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
        keyboard_config.cleanup()
    print("PASS: Openbox window controls, titlebar movement, all eight resize zones, Alt+Tab focus routing, and GTK/xterm AR↔EN input checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())