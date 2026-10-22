#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
SYSTEM = GAME / "system"

RUNTIME_LOG = SYSTEM / "snd-waveout-fisher-lambert-v21.log"
V23_LOG = SYSTEM / "snd-waveout-fisher-lambert-v23.log"

TARGET_EDITORS = {
    0x00840000,
    0x00840001,
    0x00840002,
}

SEARCH_ROOTS = [
    PROJECT / "manifests",
    PROJECT / "dubbing",
]


def parse_hex(value: str):
    try:
        return int(value, 16)
    except ValueError:
        return None


def collect_metadata_hits():
    hits = []

    patterns = {
        f"{editor:08X}".lower()
        for editor in TARGET_EDITORS
    }
    patterns |= {
        str(editor)
        for editor in TARGET_EDITORS
    }

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".csv", ".tsv", ".txt", ".md", ".json"
            }:
                continue

            try:
                text = path.read_text(
                    encoding="utf-8-sig",
                    errors="replace",
                )
            except OSError:
                continue

            for line_no, line in enumerate(
                text.splitlines(),
                start=1,
            ):
                low = line.lower()

                if any(pattern in low for pattern in patterns):
                    hits.append(
                        (
                            path.relative_to(PROJECT),
                            line_no,
                            line,
                        )
                    )

    return hits


def parse_target_triggers():
    rows = []

    if not RUNTIME_LOG.is_file():
        return rows

    for line_no, line in enumerate(
        RUNTIME_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        p = line.split()

        if (
            len(p) < 7
            or p[0] != "runtime_trigger"
        ):
            continue

        editor = parse_hex(p[1])
        duration_ms = parse_hex(p[4])
        tick = parse_hex(p[6])

        if (
            editor in TARGET_EDITORS
            and duration_ms is not None
            and tick is not None
        ):
            rows.append(
                {
                    "line": line_no,
                    "editor": editor,
                    "duration_ms": duration_ms,
                    "tick": tick,
                    "end": tick + duration_ms,
                }
            )

    return rows


def parse_v23_events():
    rows = []

    if not V23_LOG.is_file():
        return rows

    for line_no, line in enumerate(
        V23_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        p = line.split()

        if not p or p[0] not in {
            "v23_pause",
            "v23_resume",
            "v23_pause_route",
            "v23_resume_route",
        }:
            continue

        tick = parse_hex(p[-1])

        if tick is None:
            continue

        rows.append((tick, line_no, line))

    rows.sort()
    return rows


def main():
    print("===== V25 VOLUME OVERLAP CONTEXT =====")

    print()
    print("===== TARGET EDITOR METADATA =====")

    hits = collect_metadata_hits()

    if not hits:
        print("No manifest/dubbing text hit found.")
    else:
        for path, line_no, line in hits[:120]:
            print(f"{path}:{line_no}: {line}")

        if len(hits) > 120:
            print(f"... {len(hits) - 120} more metadata hits")

    triggers = parse_target_triggers()

    print()
    print("===== TARGET RUNTIME TRIGGERS =====")

    for row in triggers:
        print(
            f"editor={row['editor']:08X} "
            f"duration_ms={row['duration_ms']} "
            f"tick={row['tick']} "
            f"audio_end={row['end']} "
            f"runtime_line={row['line']}"
        )

    print()
    print("===== PAIRWISE AUDIO WINDOW CHECK =====")

    for previous, current in zip(triggers, triggers[1:]):
        delta = current["tick"] - previous["tick"]
        overlap = previous["end"] - current["tick"]

        print(
            f"{previous['editor']:08X} -> "
            f"{current['editor']:08X}: "
            f"start_delta_ms={delta} "
            f"previous_audio_overlap_ms={overlap}"
        )

    pause_events = parse_v23_events()

    print()
    print("===== V23 PAUSE/RESUME NEAR TARGET TRIGGERS =====")

    if not pause_events:
        print("No V23 pause/resume events available.")
    else:
        printed = 0

        for row in triggers:
            lo = row["tick"] - 5000
            hi = row["end"] + 5000

            nearby = [
                event
                for event in pause_events
                if lo <= event[0] <= hi
            ]

            print()
            print(
                f"editor={row['editor']:08X} "
                f"window={lo}..{hi}"
            )

            if not nearby:
                print("  no nearby V23 pause/resume events")
                continue

            for tick, line_no, line in nearby:
                print(
                    f"  tick={tick} "
                    f"v23_line={line_no} {line}"
                )
                printed += 1

        if printed == 0:
            print(
                "No pause/resume event intersects any target trigger window."
            )

    print()
    print("===== CONCLUSION HINTS =====")
    print(
        "Negative previous_audio_overlap_ms means the prior external WAV "
        "finished before the next target started."
    )
    print(
        "A positive value is direct external/external timing overlap."
    )
    print(
        "Pause/resume events inside the same window can instead indicate "
        "an ESC/options lifecycle interaction."
    )


if __name__ == "__main__":
    main()
