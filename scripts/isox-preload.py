#!/usr/bin/env python3
"""Privacy-preserving, opt-in binary page-cache warmup. Never launches apps."""
from __future__ import annotations
import os, sqlite3, subprocess, time
from pathlib import Path

DB = Path.home() / ".local/share/iso-x/iso-x.db"
ALLOWLIST = {"browser": "/usr/bin/netsurf", "terminal": "/usr/bin/xterm", "files": "/usr/bin/xdg-open"}

def read_meminfo():
    out = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            key, rest = line.split(":", 1)
            values = rest.strip().split()
            if values and values[0].isdigit(): out[key] = int(values[0]) * 1024
    return out

def main():
    if not DB.exists():
        print("ISO-X preload: no local usage database; nothing to do.")
        return 0
    con = sqlite3.connect(DB)
    try:
        row = con.execute("SELECT setting_value FROM privacy_settings WHERE setting_key='preload_enabled'").fetchone()
        if not row or row[0] != "enabled":
            print("ISO-X preload is disabled. Enable it explicitly in local settings to use it.")
            return 0
        candidates = con.execute(
            "SELECT app_id, COUNT(*) AS n FROM local_app_usage "
            "WHERE used_at >= datetime('now','-30 days') AND hour_of_day BETWEEN ? AND ? "
            "GROUP BY app_id ORDER BY n DESC LIMIT 2",
            (max(0, time.localtime().tm_hour - 2), min(23, time.localtime().tm_hour + 2)),
        ).fetchall()
    finally:
        con.close()
    mem = read_meminfo()
    total, avail = mem.get("MemTotal", 0), mem.get("MemAvailable", 0)
    if not total or avail < total * 0.62:
        print(f"ISO-X preload skipped: only {avail // (1024*1024)} MB available; safety threshold is 62% of RAM.")
        return 0
    try:
        load = os.getloadavg()[0]
        cores = max(1, os.cpu_count() or 1)
        if load / cores > 0.20:
            print("ISO-X preload skipped: CPU load is not idle enough.")
            return 0
    except (OSError, AttributeError):
        pass
    warmed = []
    # This warms executable file pages only; apps are not started and no processes are injected.
    for app_id, _count in candidates:
        binary = ALLOWLIST.get(app_id)
        if not binary or not Path(binary).is_file(): continue
        try:
            with open(binary, "rb") as f:
                while f.read(1024 * 1024): pass
            warmed.append(app_id)
        except OSError:
            continue
    print("ISO-X preload page-cache warmup:", ", ".join(warmed) if warmed else "no eligible app")
    return 0

if __name__ == "__main__": raise SystemExit(main())
