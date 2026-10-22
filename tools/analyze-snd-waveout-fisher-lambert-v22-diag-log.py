#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-fisher-lambert-v22-diag.log"

NAMES = {
    183: "PauseClientBuffer",
    184: "PauseSoundObject",
    185: "PauseSoundObjectType",
    186: "PauseSxd",
    187: "PauseTimer",
    188: "PauseTransitionSxd",
    210: "ResumeClientBuffer",
    211: "ResumeSoundObject",
    212: "ResumeSoundObjectType",
    213: "ResumeSxd",
    214: "ResumeTimer",
    215: "ResumeTransitionSxd",
}


def main():
    print("===== V22 PAUSE ROUTE DIAGNOSTIC =====")

    if not LOG.is_file():
        raise SystemExit(f"ERROR: missing V22 log: {LOG}")

    size = LOG.stat().st_size

    print(f"Log: {LOG}")
    print(f"Bytes: {size}")

    if size == 0:
        raise SystemExit(
            "ERROR: V22 log is empty; open and close ESC pause first"
        )

    counts = Counter()
    samples = []

    for line in LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        parts = line.split()

        if not parts or parts[0] != "pause_route_probe":
            continue

        if len(parts) < 4:
            continue

        try:
            ordinal = int(parts[1], 16)
            target = int(parts[2], 16)
            tick = int(parts[3], 16)
        except ValueError:
            continue

        counts[ordinal] += 1

        if len(samples) < 40:
            samples.append((ordinal, target, tick))

    print()
    print("===== ROUTE COUNTS =====")

    for ordinal in sorted(NAMES):
        print(
            f"@{ordinal:<3} {NAMES[ordinal]:<24} "
            f"{counts[ordinal]}"
        )

    observed = [
        ordinal
        for ordinal in sorted(NAMES)
        if counts[ordinal]
    ]

    print()
    print("===== OBSERVED ROUTES =====")

    if not observed:
        print("NONE")
        print()
        print("V22_PAUSE_ROUTE: NOT_IN_SND_PAUSE_EXPORTS")
        print(
            "ESC pause did not use any of the 12 candidate "
            "SND pause/resume exports."
        )
        return

    for ordinal in observed:
        print(
            f"OBSERVED @{ordinal} {NAMES[ordinal]} "
            f"x{counts[ordinal]}"
        )

    bad_target = [
        item
        for item in samples
        if item[1] == 0
    ]

    if bad_target:
        raise SystemExit(
            "ERROR: a diagnostic route failed to resolve its original export"
        )

    print()
    print("===== RESULT =====")
    print("V22_PAUSE_ROUTE: FOUND")
    print(
        "Candidates used by ESC: "
        + ", ".join(
            f"@{ordinal} {NAMES[ordinal]}"
            for ordinal in observed
        )
    )


if __name__ == "__main__":
    main()
