#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'if [[ "${KEEP_TMP:-0}" == 1 ]]; then printf "TEST_TMP=%s\n" "$TMP"; else rm -rf "$TMP"; fi' EXIT
mkdir -p "$TMP/bin"
printf 'not a bootable ISO; only tests the failure detector\n' > "$TMP/test.iso"
cat > "$TMP/bin/qemu-system-x86_64" <<'QEMU'
#!/usr/bin/env python3
import json
import os
import shlex
import signal
import socket
import sys
import threading
import time
from pathlib import Path

if sys.argv[1:] == ["-version"]:
    print("QEMU emulator version 9.2.0 (fake test binary)")
    raise SystemExit(0)

if os.environ.get("FAKE_QEMU_ARGS_FILE"):
    Path(os.environ["FAKE_QEMU_ARGS_FILE"]).write_text(json.dumps(sys.argv[1:]))

serial = next(sys.argv[i + 1][5:] for i, arg in enumerate(sys.argv[:-1]) if arg == "-serial")
qmp_arg = next(sys.argv[i + 1] for i, arg in enumerate(sys.argv[:-1]) if arg == "-qmp")
qmp_path = qmp_arg.removeprefix("unix:").split(",", 1)[0]
kind = os.environ.get("FAKE_QEMU_KIND", "timeout")

def qmp_server():
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(qmp_path)
    server.listen(1)
    connection, _ = server.accept()
    screenshot_count = 0
    with connection:
        reader = connection.makefile("rb")
        connection.sendall(b'{"QMP":{"version":{},"capabilities":[]}}\r\n')
        for line in reader:
            request = json.loads(line)
            command = request.get("execute")
            if command == "human-monitor-command":
                words = shlex.split(request["arguments"]["command-line"])
                if words[0] == "screendump":
                    screenshot_count += 1
                    if kind == "small-boot-frame" and screenshot_count == 1:
                      pixels = b"\x00\x00\x00" * (720 * 400)
                      Path(words[1]).write_bytes(b"P6\n720 400\n255\n" + pixels)
                    elif kind == "no-screenshot":
                        pass
                    elif kind == "malformed-screenshot":
                        Path(words[1]).write_bytes(b"P6\nnot-an-image")
                    elif kind == "small-screenshot":
                        Path(words[1]).write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")
                    elif kind == "black-screenshot":
                        Path(words[1]).write_bytes(b"P6\n640 480\n255\n" + b"\x00" * (640 * 480 * 3))
                    elif kind == "unrelated-screenshot":
                      Path(words[1]).write_bytes(b"P6\n640 480\n255\n" + b"\xff" * (640 * 480 * 3))
                    else:
                        pixels = bytearray(bytes((10, 10, 15)) * (640 * 480))
                        pixels[:1500] = bytes((18, 18, 28)) * 500
                        pixels[1500:1560] = bytes((0, 229, 255)) * 20
                        Path(words[1]).write_bytes(b"P6\n640 480\n255\n" + pixels)
                    if kind == "marker-exit-error" and screenshot_count == 2:
                        time.sleep(0.5)
                response = (
                  {"error": {"class": "GenericError", "desc": "fake screendump error"}}
                  if kind == "qmp-command-error" and command == "human-monitor-command"
                  else {"return": ""}
                )
            else:
                response = {"return": {}}
            connection.sendall(json.dumps(response).encode() + b"\r\n")
    server.close()

if os.environ.get("FAKE_QEMU_NO_QMP") != "1":
    threading.Thread(target=qmp_server, daemon=True).start()

if kind == "success-zero-on-term":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

if kind == "immediate-error":
    print("qemu-system-x86_64: test infrastructure error", file=sys.stderr)
    raise SystemExit(42)
if kind == "misleading":
    with open(serial, "a", encoding="utf-8") as stream:
        stream.write("Reached target Graphical Interface\n")
        stream.write("ISOX_CI_READY nonce=ffffffffffffffffffffffffffffffff\n")
elif kind in ("success", "success-zero-on-term", "small-boot-frame", "qmp-failure", "qmp-command-error"):
    time.sleep(1)
    with open(serial, "a", encoding="utf-8") as stream:
        stream.write(f"ISOX_CI_READY nonce={os.environ['FAKE_QEMU_NONCE']}\n")
elif kind == "marker-exit-error":
    with open(serial, "a", encoding="utf-8") as stream:
        stream.write(f"ISOX_CI_READY nonce={os.environ['FAKE_QEMU_NONCE']}\n")
    time.sleep(0.2)
    raise SystemExit(42)
elif kind == "timeout":
  with open(serial, "a", encoding="utf-8") as stream:
    stream.write("Boot remains in progress\n")
while True:
    time.sleep(1)
QEMU
chmod 0755 "$TMP/bin/qemu-system-x86_64"
NONCE=0123456789abcdef0123456789abcdef
export ISOX_QEMU_RENDER_GRACE=0

FAKE_QEMU_KIND=success FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=20 \
  ISOX_QEMU_MEMORY_MIB=6144 ISOX_QEMU_CPUS=4 FAKE_QEMU_ARGS_FILE="$TMP/success-args.json" \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/success" \
  >"$TMP/success.log" 2>&1
python3 - "$TMP/success/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "PASS_BOOT", r
assert r["marker_seen"] is True and r["process_group_clean"] is True, r
assert r["shutdown_reason"] == "readiness_marker" and r["termination_requested"] is True, r
assert r["final_screenshot_valid"] is True, r
assert r["duration_seconds"] < 5, r
assert r["serial_bytes"] > 0, r
assert r["screenshots"] == ["qemu-bios-headless-early.ppm", "qemu-bios-headless-final.ppm"], r
args = json.loads(Path(sys.argv[1]).parent.parent.joinpath("success-args.json").read_text())
assert args[args.index("-m") + 1] == "6144", args
assert args[args.index("-smp") + 1] == "4", args
for screenshot in r["screenshots"]:
    image = Path(sys.argv[1]).parent / screenshot
    assert image.read_bytes().startswith(b"P6\n640 480\n255\n"), image
PY

FAKE_QEMU_KIND=success-zero-on-term FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=20 \
  FAKE_QEMU_ARGS_FILE="$TMP/default-args.json" \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/success-zero" \
  >"$TMP/success-zero.log" 2>&1
python3 - "$TMP/success-zero/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "PASS_BOOT" and r["qemu_exit_code"] == 0, r
assert r["termination_requested"] is True and r["process_group_clean"] is True, r
args = json.loads(Path(sys.argv[1]).parent.parent.joinpath("default-args.json").read_text())
assert args[args.index("-m") + 1] == "1024", args
assert args[args.index("-smp") + 1] == "2", args
PY

for setting in ISOX_QEMU_MEMORY_MIB ISOX_QEMU_CPUS; do
  for invalid in 0 bad; do
    if env "$setting=$invalid" PATH="$TMP/bin:$PATH" \
      bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
      "$TMP/test.iso" "$TMP/invalid-$setting-$invalid" \
      >"$TMP/invalid-$setting-$invalid.log" 2>&1; then
      echo "FAIL: invalid $setting=$invalid was accepted." >&2
      exit 1
    fi
    grep -Fq "$setting must be a positive integer." "$TMP/invalid-$setting-$invalid.log"
  done
done

FAKE_QEMU_KIND=small-boot-frame FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=20 \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/small-boot-frame" \
  >"$TMP/small-boot-frame.log" 2>&1
python3 - "$TMP/small-boot-frame/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "PASS_BOOT" and r["final_screenshot_valid"] is True, r
assert (Path(sys.argv[1]).parent / "qemu-bios-headless-early.ppm").read_bytes().startswith(b"P6\n720 400\n255\n")
PY

FAKE_QEMU_KIND=desktop ISOX_QEMU_TIMEOUT=5 ISOX_QEMU_RENDER_GRACE=0 \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-desktop \
  "$TMP/test.iso" "$TMP/desktop" >"$TMP/desktop.log" 2>&1
python3 - "$TMP/desktop/qemu-bios-desktop-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "PASS_BOOT" and r["marker_seen"] is False, r
assert r["desktop_seen"] is True and r["shutdown_reason"] == "desktop_rendered", r
assert r["termination_requested"] is True and r["final_screenshot_valid"] is True, r
PY

if FAKE_QEMU_KIND=black-screenshot ISOX_QEMU_TIMEOUT=2 ISOX_QEMU_RENDER_GRACE=0 \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-desktop \
  "$TMP/test.iso" "$TMP/desktop-black" >"$TMP/desktop-black.log" 2>&1; then
  echo "FAIL: a black normal-boot desktop was accepted." >&2
  exit 1
fi

python3 - "$ROOT/tests/qemu-runner.py" <<'PY'
import importlib.util, signal, sys
spec = importlib.util.spec_from_file_location("qemu_runner", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
classify = module.classify
assert classify("", False, 0, True, "readiness_marker", False, False, False, True) == "QEMU_INFRASTRUCTURE_FAILURE"
assert classify("", False, -signal.SIGTERM, True, "readiness_marker", True, False, False, True) == "PASS_BOOT"
assert classify("", False, -signal.SIGKILL, True, "readiness_marker", True, True, False, True) == "QEMU_INFRASTRUCTURE_FAILURE"
assert classify("", False, 42, True, "readiness_marker", True, False, False, True) == "QEMU_INFRASTRUCTURE_FAILURE"
assert classify("boot", True, 0, False, "timeout", True, False, False, True) == "BOOT_TIMEOUT"
assert classify("", False, 0, True, "readiness_marker", True, False, False, False) == "QEMU_INFRASTRUCTURE_FAILURE"
assert classify("", False, 0, False, "desktop_rendered", True, False, True, True) == "PASS_BOOT"
PY

if FAKE_QEMU_KIND=marker-exit-error FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=5 \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/marker-exit-error" \
  >"$TMP/marker-exit-error.log" 2>&1; then
  echo "FAIL: a guest marker followed by an unexpected QEMU exit was accepted." >&2
  exit 1
fi
python3 - "$TMP/marker-exit-error/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "QEMU_INFRASTRUCTURE_FAILURE", r
assert r["marker_seen"] is True and r["qemu_exit_code"] == 42, r
PY

if FAKE_QEMU_KIND=qmp-failure FAKE_QEMU_NONCE="$NONCE" FAKE_QEMU_NO_QMP=1 \
  ISOX_QEMU_TIMEOUT=5 ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/qmp-error" \
  >"$TMP/qmp-error.log" 2>&1; then
  echo "FAIL: a guest marker without required QMP screenshot evidence was accepted." >&2
  exit 1
fi
python3 - "$TMP/qmp-error/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "QEMU_INFRASTRUCTURE_FAILURE", r
assert r["marker_seen"] is True and r["screenshots"] == [], r
PY

if FAKE_QEMU_KIND=qmp-command-error FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=5 \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/qmp-command-error" \
  >"$TMP/qmp-command-error.log" 2>&1; then
  echo "FAIL: a QMP screendump error was accepted." >&2
  exit 1
fi
python3 - "$TMP/qmp-command-error/qemu-bios-headless-result.json" \
  "$TMP/qmp-command-error/qemu-bios-headless-qmp.log" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "QEMU_INFRASTRUCTURE_FAILURE" and r["marker_seen"] is True, r
assert "fake screendump error" in Path(sys.argv[2]).read_text()
PY

if FAKE_QEMU_KIND=timeout ISOX_QEMU_TIMEOUT=2 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/timeout" >"$TMP/timeout.log" 2>&1; then
  echo "FAIL: a boot timeout was accepted." >&2
  exit 1
fi
python3 - "$TMP/timeout/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "BOOT_TIMEOUT", r
assert r["timed_out"] is True and r["marker_seen"] is False, r
PY

mkdir -p "$TMP/stale"
printf 'old screenshot' > "$TMP/stale/qemu-bios-headless-early.ppm"
if FAKE_QEMU_KIND=success FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=5 \
  ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
  bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/stale" \
  >"$TMP/stale.log" 2>&1; then
  echo "FAIL: a reused screenshot path was accepted as fresh VGA evidence." >&2
  exit 1
fi
python3 - "$TMP/stale/qemu-bios-headless-result.json" "$TMP/stale/qemu-bios-headless-early.ppm" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "QEMU_INFRASTRUCTURE_FAILURE", r
assert r["marker_seen"] is True, r
assert Path(sys.argv[2]).read_bytes() == b"old screenshot"
assert "early.ppm" not in r["screenshots"], r
PY

for screen_kind in black-screenshot unrelated-screenshot small-screenshot malformed-screenshot no-screenshot; do
  if FAKE_QEMU_KIND="$screen_kind" FAKE_QEMU_NONCE="$NONCE" ISOX_QEMU_TIMEOUT=5 \
    ISOX_QEMU_NONCE="$NONCE" PATH="$TMP/bin:$PATH" \
    bash "$ROOT/tests/qemu-acceptance.sh" bios-headless "$TMP/test.iso" "$TMP/$screen_kind" \
    >"$TMP/$screen_kind.log" 2>&1; then
    echo "FAIL: invalid screenshot evidence was accepted ($screen_kind)." >&2
    exit 1
  fi
done

if FAKE_QEMU_KIND=misleading ISOX_QEMU_TIMEOUT=2 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/misleading" >"$TMP/misleading.log" 2>&1; then
  echo "FAIL: a stale/mismatched nonce or graphical.target text was accepted." >&2
  exit 1
fi
python3 - "$TMP/misleading/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "DISPLAY_OR_LOGIN_FAILURE", r
assert r["marker_seen"] is False, r
PY

if FAKE_QEMU_KIND=no-serial ISOX_QEMU_TIMEOUT=2 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/empty" >"$TMP/empty.log" 2>&1; then
  echo "FAIL: an empty serial log was accepted." >&2
  exit 1
fi
python3 - "$TMP/empty/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "NO_SERIAL_OUTPUT", r
assert r["serial_bytes"] == 0 and r["marker_seen"] is False, r
assert all(value is None for value in r["serial_indicators"].values()), r
PY

if FAKE_QEMU_KIND=immediate-error ISOX_QEMU_TIMEOUT=5 ISOX_QEMU_NONCE="$NONCE" \
  PATH="$TMP/bin:$PATH" bash "$ROOT/tests/qemu-acceptance.sh" bios-headless \
  "$TMP/test.iso" "$TMP/error" >"$TMP/error.log" 2>&1; then
  echo "FAIL: an immediate QEMU infrastructure error was accepted." >&2
  exit 1
fi
python3 - "$TMP/error/qemu-bios-headless-result.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r["status"] == "QEMU_INFRASTRUCTURE_FAILURE", r
assert r["qemu_exit_code"] == 42 and r["marker_seen"] is False, r
PY

printf 'PASS: a nonce marker stops QEMU early only with fresh QMP/PPM evidence; spoofed text, empty serial, timeouts, and unexpected exits are rejected.\n'
