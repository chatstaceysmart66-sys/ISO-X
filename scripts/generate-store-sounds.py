#!/usr/bin/env python3
"""Generate small, original ISO-X Store interface tones as PCM WAV files."""
from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 24000
SOUNDS = {
    "notification.wav": ((784, 0.00, 0.18), (1047, 0.12, 0.24)),
    "success.wav": ((523, 0.00, 0.20), (659, 0.14, 0.22), (784, 0.28, 0.34)),
    "error.wav": ((392, 0.00, 0.20), (311, 0.12, 0.26)),
    "warning.wav": ((659, 0.00, 0.18), (554, 0.21, 0.20)),
    "download-complete.wav": ((587, 0.00, 0.18), (740, 0.13, 0.19), (880, 0.26, 0.19), (1175, 0.39, 0.42)),
}


def _envelope(position: float, duration: float) -> float:
    attack = min(1.0, position / 0.018)
    release = min(1.0, max(0.0, duration - position) / 0.10)
    return attack * release * math.exp(-2.6 * position / duration)


def render_tone(notes: tuple[tuple[int, float, float], ...]) -> bytes:
    duration = max(start + length for _, start, length in notes) + 0.06
    count = round(duration * SAMPLE_RATE)
    frames = bytearray()
    for index in range(count):
        time_seconds = index / SAMPLE_RATE
        sample = 0.0
        for frequency, start, length in notes:
            relative = time_seconds - start
            if 0 <= relative <= length:
                envelope = _envelope(relative, length)
                fundamental = math.sin(2 * math.pi * frequency * relative)
                harmonic = math.sin(2 * math.pi * frequency * 2.01 * relative)
                sample += envelope * (0.78 * fundamental + 0.12 * harmonic)
        normalized = max(-1.0, min(1.0, sample * 0.34))
        frames.extend(struct.pack("<h", round(normalized * 32767)))
    return bytes(frames)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, notes in SOUNDS.items():
        with wave.open(str(output / name), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(SAMPLE_RATE)
            stream.writeframes(render_tone(notes))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets/sounds",
    )
    arguments = parser.parse_args()
    generate(arguments.output)
    print(f"Generated {len(SOUNDS)} original ISO-X Store tones in {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
