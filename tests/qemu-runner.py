#!/usr/bin/env python3
"""Run one headless QEMU boot, capture QMP screenshots, and require a guest nonce."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


MARKER_PREFIX = "ISOX_CI_READY nonce="
MIN_SCREENSHOT_WIDTH = 640
MIN_SCREENSHOT_HEIGHT = 480


def validate_ppm(path: Path, require_visible: bool = False) -> tuple[bool, str]:
    try:
        image = path.read_bytes()
    except OSError as error:
        return False, str(error)
    if len(image) < 16 or not image.startswith(b"P6"):
        return False, "not a binary P6 PPM image"
    header = re.match(rb"P6\s+(\d+)\s+(\d+)\s+(\d+)\s", image)
    if not header:
        return False, "malformed PPM header"
    width, height, maximum = map(int, header.groups())
    if width < MIN_SCREENSHOT_WIDTH or height < MIN_SCREENSHOT_HEIGHT or maximum != 255:
        return False, f"unsupported screenshot dimensions or color depth: {width}x{height}, max={maximum}"
    pixels = image[header.end():]
    if len(pixels) != width * height * 3:
        return False, f"pixel payload size mismatch: expected {width * height * 3}, got {len(pixels)}"
    if require_visible:
        background = bytes((10, 10, 15))
        panel = bytes((18, 18, 28))
        accent = bytes((0, 229, 255))
        background_count = panel_count = accent_count = 0
        for index in range(0, len(pixels), 3):
            color = pixels[index:index + 3]
            background_count += color == background
            panel_count += color == panel
            accent_count += color == accent
        if background_count < width * height // 20 or panel_count < 500 or accent_count < 20:
            return False, (
                "screenshot does not contain the ISO-X desktop palette: "
                f"background={background_count}, panel={panel_count}, accent={accent_count}"
            )
    return True, "ok"


class QMP:
    def __init__(self, path: str, log: Path):
        self.path = path
        self.log = log
        self.connection: socket.socket | None = None
        self.reader = None

    def connect(self, process: subprocess.Popen[bytes], deadline: float) -> bool:
        while process.poll() is None and time.monotonic() < deadline:
            try:
                self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.connection.settimeout(2)
                self.connection.connect(self.path)
                self.reader = self.connection.makefile("rwb")
                greeting = self.reader.readline()
                self._write({"execute": "qmp_capabilities"})
                response = self._read_response()
                self.log.write_text(
                    f"greeting={greeting.decode(errors='replace').strip()}\n"
                    f"capabilities={response!r}\n",
                    encoding="utf-8",
                )
                return True
            except (OSError, ValueError, TimeoutError) as error:
                if self.connection:
                    self.connection.close()
                self.connection = None
                time.sleep(0.1)
        self.log.write_text("QMP did not become available before the VM exited or timed out.\n", encoding="utf-8")
        return False

    def _write(self, command: dict[str, object]) -> None:
        assert self.reader is not None
        self.reader.write(json.dumps(command).encode() + b"\r\n")
        self.reader.flush()

    def _read_response(self) -> dict[str, object]:
        assert self.reader is not None
        while True:
            line = self.reader.readline()
            if not line:
                raise OSError("QMP closed before returning a response")
            response = json.loads(line)
            if "return" in response or "error" in response:
                return response

    def screenshot(self, destination: Path, require_visible: bool = False) -> bool:
        if self.reader is None:
            return False
        try:
            if destination.exists():
                raise FileExistsError(f"refusing to reuse stale screenshot path: {destination}")
            self._write({
                "execute": "human-monitor-command",
                "arguments": {"command-line": f'screendump "{destination}"'},
            })
            response = self._read_response()
            if "error" in response:
                raise RuntimeError(str(response["error"]))
            valid, reason = validate_ppm(destination, require_visible=require_visible)
            if not valid:
                raise ValueError(reason)
            return True
        except (OSError, ValueError, RuntimeError, TimeoutError) as error:
            with self.log.open("a", encoding="utf-8") as stream:
                stream.write(f"screendump {destination.name}: {error}\n")
            return False

    def close(self) -> None:
        if self.connection:
            self.connection.close()
        self.connection = None
        self.reader = None


def classify(
    serial: str,
    timed_out: bool,
    returncode: int | None,
    marker_seen: bool,
    shutdown_reason: str,
    termination_requested: bool,
    termination_escalated: bool,
    final_screenshot_valid: bool,
) -> str:
    if returncode not in (None, 0, -signal.SIGTERM, -signal.SIGKILL):
        return "QEMU_INFRASTRUCTURE_FAILURE"
    if marker_seen:
        if (
            shutdown_reason != "readiness_marker"
            or not termination_requested
            or termination_escalated
            or not final_screenshot_valid
        ):
            return "QEMU_INFRASTRUCTURE_FAILURE"
        return "PASS_BOOT"
    if not serial.strip():
        return "NO_SERIAL_OUTPUT"
    if re.search(r"Kernel panic|Unable to mount root fs|Entering emergency mode", serial, re.I):
        return "KERNEL_OR_INITRAMFS_FAILURE"
    if re.search(r"Reached target.*(Graphical Interface|graphical\.target)", serial, re.I):
        return "DISPLAY_OR_LOGIN_FAILURE"
    if timed_out:
        return "BOOT_TIMEOUT"
    return "BOOT_FAILURE_UNRESOLVED"


def serial_indicators(serial: str) -> dict[str, bool | None]:
    if not serial.strip():
        return {
            "bootloader": None,
            "kernel": None,
            "initramfs": None,
            "systemd": None,
            "graphical_target": None,
            "display_manager": None,
        }
    patterns = {
        "bootloader": r"SYSLINUX|ISOLINUX|GRUB",
        "kernel": r"Linux version|Kernel command line",
        "initramfs": r"initramfs|live-boot|Mounting root filesystem",
        "systemd": r"systemd\[1\]|Reached target",
        "graphical_target": r"Reached target.*(Graphical Interface|graphical\.target)",
        "display_manager": r"lightdm(\.service|\[)|Light Display Manager",
    }
    return {name: bool(re.search(pattern, serial, re.I)) for name, pattern in patterns.items()}


def terminate_group(process: subprocess.Popen[bytes]) -> tuple[bool, bool]:
    if process.poll() is not None:
        return False, False
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return False, False
    termination_requested = True
    termination_escalated = False
    try:
        if process.poll() is None:
            process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    if not group_has_live_processes(process.pid):
        return termination_requested, termination_escalated
    try:
        os.killpg(process.pid, signal.SIGKILL)
        termination_escalated = True
    except ProcessLookupError:
        pass
    try:
        if process.poll() is None:
            process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    return termination_requested, termination_escalated


def group_has_live_processes(group_id: int) -> bool:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
            state, process_group = fields[0], int(fields[2])
        except (OSError, IndexError, ValueError):
            continue
        if process_group == group_id and state != "Z":
            return True
    return False


def exit_on_term(signum: int, _frame: object) -> None:
    raise SystemExit(128 + signum)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("bios-headless", "uefi-headless"))
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--timeout", required=True, type=int)
    parser.add_argument("--render-grace", type=float, default=3.0)
    parser.add_argument("--accelerator", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{32}", args.nonce):
        parser.error("nonce must be 32 lowercase hexadecimal characters")
    if args.timeout < 1:
        parser.error("timeout must be a positive integer")
    if args.render_grace < 0:
        parser.error("render grace must not be negative")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a QEMU command is required after --")
    signal.signal(signal.SIGTERM, exit_on_term)

    evidence = args.evidence
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        version = subprocess.run(
            [command[0], "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        qemu_version = (version.stdout or version.stderr).splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        qemu_version = "unavailable"
    firmware = "UEFI/OVMF" if any("OVMF_CODE" in item or "OVMF_VARS" in item for item in command) else "BIOS"
    try:
        firmware_package = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}", "ovmf"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        firmware_version = firmware_package.stdout.strip() if firmware_package.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        firmware_version = "unavailable"
    serial_path = evidence / f"qemu-{args.mode}-serial.log"
    qemu_stdout = evidence / f"qemu-{args.mode}-stdout.log"
    qemu_stderr = evidence / f"qemu-{args.mode}-stderr.log"
    qmp_log = evidence / f"qemu-{args.mode}-qmp.log"
    result_path = evidence / f"qemu-{args.mode}-result.json"
    serial_path.write_bytes(b"")
    nonce_marker = re.compile(
        rb"(?m)^" + re.escape(MARKER_PREFIX.encode()) + re.escape(args.nonce.encode()) + rb"\r?$"
    )

    with tempfile.TemporaryDirectory(prefix="isox-qmp-") as temporary:
        qmp_socket = str(Path(temporary) / "monitor.sock")
        full_command = [
            *command,
            "-display", "none",
            "-vga", "std",
            "-serial", f"file:{serial_path}",
            "-monitor", "none",
            "-qmp", f"unix:{qmp_socket},server=on,wait=off",
        ]
        started = time.monotonic()
        with qemu_stdout.open("wb") as stdout_stream, qemu_stderr.open("wb") as stderr_stream:
            try:
                process = subprocess.Popen(
                    full_command,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_stream,
                    stderr=stderr_stream,
                    start_new_session=True,
                )
            except OSError as error:
                result = {
                    "mode": args.mode,
                    "status": "QEMU_INFRASTRUCTURE_FAILURE",
                    "qemu_started": False,
                    "qemu_exit_code": None,
                    "error": str(error),
                    "serial_bytes": 0,
                    "marker_seen": False,
                    "serial_log": str(serial_path),
                    "qemu_stdout": str(qemu_stdout),
                    "qemu_stderr": str(qemu_stderr),
                    "qemu_version": qemu_version,
                    "firmware": firmware,
                    "firmware_version": firmware_version,
                    "screenshots": [],
                    "serial_indicators": serial_indicators(""),
                }
                result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(result))
                return 20

            qmp = QMP(qmp_socket, qmp_log)
            qmp_available = False
            screenshots: list[str] = []
            marker_seen = False
            timed_out = False
            shutdown_reason = "qemu_exit"
            termination_requested = False
            termination_escalated = False
            final_screenshot_valid = False
            failure = None
            try:
                qmp_available = qmp.connect(process, min(started + 1, started + args.timeout))
                if not qmp_available:
                    failure = "QMP monitor did not become available; VGA evidence cannot be captured."
                elif qmp.screenshot(evidence / f"qemu-{args.mode}-early.ppm"):
                    screenshots.append(f"qemu-{args.mode}-early.ppm")
                else:
                    failure = "Unable to capture the early VGA screenshot through QMP."
                second_snapshot_at = started + min(15, max(2, args.timeout // 3))
                while process.poll() is None:
                    serial_bytes = serial_path.read_bytes()
                    if nonce_marker.search(serial_bytes):
                        marker_seen = True
                        shutdown_reason = "readiness_marker"
                        if args.render_grace:
                            time.sleep(args.render_grace)
                        break
                    now = time.monotonic()
                    if now >= second_snapshot_at and qmp_available:
                        name = f"qemu-{args.mode}-later.ppm"
                        if qmp.screenshot(evidence / name):
                            screenshots.append(name)
                        second_snapshot_at = float("inf")
                    if now - started >= args.timeout:
                        timed_out = True
                        shutdown_reason = "timeout"
                        break
                    time.sleep(0.2)
            except Exception as error:
                failure = f"{type(error).__name__}: {error}"
                shutdown_reason = "runner_error"
            finally:
                if qmp_available:
                    name = f"qemu-{args.mode}-final.ppm"
                    final_screenshot_valid = qmp.screenshot(
                        evidence / name,
                        require_visible=marker_seen,
                    )
                    if final_screenshot_valid:
                        screenshots.append(name)
                    elif marker_seen or timed_out:
                        failure = failure or "Unable to capture valid final VGA evidence before QEMU cleanup."
                qmp.close()
                termination_requested, termination_escalated = terminate_group(process)
            process_group_clean = not group_has_live_processes(process.pid)
            qemu_exit_code = process.returncode
            duration = round(time.monotonic() - started, 3)
            try:
                serial_content = serial_path.read_bytes()
            except OSError as error:
                serial_content = b""
                failure = failure or f"{type(error).__name__}: {error}"
            serial_text = serial_content.decode("utf-8", errors="replace")
            status = classify(
                serial_text,
                timed_out,
                qemu_exit_code,
                marker_seen,
                shutdown_reason,
                termination_requested,
                termination_escalated,
                final_screenshot_valid,
            )
            if failure or not process_group_clean:
                status = "QEMU_INFRASTRUCTURE_FAILURE"
            result = {
                "mode": args.mode,
                "status": status,
                "qemu_started": True,
                "qemu_exit_code": qemu_exit_code,
                "timed_out": timed_out,
                "shutdown_reason": shutdown_reason,
                "termination_requested": termination_requested,
                "termination_escalated": termination_escalated,
                "final_screenshot_valid": final_screenshot_valid,
                "duration_seconds": duration,
                "serial_bytes": len(serial_content),
                "marker_seen": marker_seen,
                "serial_indicators": serial_indicators(serial_text),
                "process_group_clean": process_group_clean,
                "serial_log": str(serial_path),
                "qemu_stdout": str(qemu_stdout),
                "qemu_stderr": str(qemu_stderr),
                "qemu_version": qemu_version,
                "firmware": firmware,
                "firmware_version": firmware_version,
                "qmp_log": str(qmp_log),
                "screenshots": screenshots,
                "launch_command": full_command,
                "accelerator": args.accelerator,
            }
            if failure:
                result["error"] = failure
            result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2))
            return 0 if status == "PASS_BOOT" else 10


if __name__ == "__main__":
    sys.exit(main())
