#!/usr/bin/env python3
"""Read and switch the active Arabic/English XKB group on the current display."""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path


XKB_USE_CORE_KBD = 0x0100
PREFERENCE_PATH = Path(
    os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
) / "iso-x" / "keyboard-layout"


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


def _x11():
    library = ctypes.util.find_library("X11")
    if not library:
        raise RuntimeError("libX11 is unavailable")
    x11 = ctypes.CDLL(library)
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XkbGetState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(XkbState)]
    x11.XkbGetState.restype = ctypes.c_int
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("cannot connect to the current X display")
    return x11, display


def current_group() -> int:
    x11, display = _x11()
    try:
        state = XkbState()
        if x11.XkbGetState(display, XKB_USE_CORE_KBD, ctypes.byref(state)) != 0:
            raise RuntimeError("XkbGetState failed")
        return int(state.group)
    finally:
        x11.XCloseDisplay(display)


def current_layout() -> str:
    query = subprocess.run(
        ["setxkbmap", "-query"], capture_output=True, text=True, check=False, timeout=5
    )
    if query.returncode != 0:
        raise RuntimeError(f"setxkbmap -query failed: {query.stderr.strip()}")
    layouts = next(
        (line.partition(":")[2].strip().split(",") for line in query.stdout.splitlines()
         if line.startswith("layout:")),
        [],
    )
    if not layouts:
        raise RuntimeError("setxkbmap returned no active layouts")
    group = current_group()
    if group >= len(layouts):
        raise RuntimeError(f"active XKB group {group} is outside layout list {layouts!r}")
    labels = {"ara": "AR", "us": "EN"}
    try:
        return labels[layouts[group]]
    except KeyError as error:
        raise RuntimeError(f"unsupported active XKB layout {layouts[group]!r}") from error


def toggle_layout() -> str:
    target = "us" if current_layout() == "AR" else "ara"
    layout = "EN" if target == "us" else "AR"
    _apply_layout(layout)
    active = current_layout()
    if active != layout:
        raise RuntimeError(f"requested {layout}, but active layout is {active}")
    _save_preference(layout)
    return active


def _apply_layout(layout: str) -> None:
    if layout not in ("AR", "EN"):
        raise ValueError(f"unsupported keyboard layout preference: {layout!r}")
    layouts = "us,ara" if layout == "EN" else "ara,us"
    result = subprocess.run(
        ["setxkbmap", "-layout", layouts, "-option", "grp:alt_shift_toggle_bidir"],
        capture_output=True, text=True, check=False, timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(f"setxkbmap could not activate {layout}: {result.stderr.strip()}")


def _save_preference(layout: str) -> None:
    if layout not in ("AR", "EN"):
        raise ValueError(f"unsupported keyboard layout preference: {layout!r}")
    PREFERENCE_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".keyboard-layout.", dir=PREFERENCE_PATH.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(layout + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, PREFERENCE_PATH)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def restore_layout() -> str:
    try:
        preference = PREFERENCE_PATH.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        preference = "AR"
    if preference not in ("AR", "EN"):
        raise RuntimeError(f"invalid keyboard layout preference in {PREFERENCE_PATH}")
    _apply_layout(preference)
    active = current_layout()
    if active != preference:
        raise RuntimeError(f"requested {preference}, but active layout is {active}")
    return active


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "toggle", "restore"))
    args = parser.parse_args()
    try:
        if args.action == "toggle":
            layout = toggle_layout()
        elif args.action == "restore":
            layout = restore_layout()
        else:
            layout = current_layout()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"ISO-X keyboard: {error}", file=sys.stderr)
        return 1
    print(layout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())