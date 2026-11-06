#!/usr/bin/env python3
"""Generate ISO-X brand assets from the preserved visual design reference."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "scripts/extract-reference-assets.py"
REFERENCE = ROOT / "design/reference/iso-x-reference.html"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    command = [
        sys.executable,
        str(EXTRACTOR),
        "--source",
        str(REFERENCE),
        "--output-dir",
        str(args.output_dir.resolve()),
    ]
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Brand asset generation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
