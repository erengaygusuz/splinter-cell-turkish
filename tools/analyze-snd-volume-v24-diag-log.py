#!/usr/bin/env python3
from __future__ import annotations

import struct
from collections import Counter, defaultdict
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-volume-v24-diag.log"

NAMES = {
    140: "ChangeVolumeAllSoundObjectTypes",
    146: "ChangeVolumeSoundObjectType",
    240: "SetSoundVolumeLine",
}


def as_float(value: int) -> float:
    return struct.unpack("<f", value.to_bytes(4, "little"))[0]


def main():
    print("===== V24 VOLUME ROUTE DIAGNOSTIC =====")
    print("Log:", LOG)

    if not LOG.is_file():
        raise SystemExit("ERROR: V24 log is missing")

    raw = LOG.read_text(encoding="utf-8", errors="replace")
    print("Bytes:", len(raw.encode("utf-8")))

    counts = Counter()
    samples = defaultdict(list)
    bad_targets = []

    for line_no, line in enumerate(raw.splitlines(), start=1):
        parts = line.split()

        if len(parts) != 8 or parts[0] != "volume_route_probe":
            continue

        try:
            values = [int(value, 16) for value in parts[1:]]
        except ValueError:
            continue

        ordinal, target, a0, a1, a2, a3, tick = values
        counts[ordinal] += 1

        if target == 0:
            bad_targets.append((line_no, ordinal))

        if len(samples[ordinal]) < 12:
            samples[ordinal].append((a0, a1, a2, a3, tick))

    print()
    print("===== ROUTE COUNTS =====")

    for ordinal in (140, 146, 240):
        print(
            f"@{ordinal:<3} "
            f"{NAMES[ordinal]:<32} "
            f"{counts[ordinal]}"
        )

    print()
    print("===== OBSERVED ARGUMENT SAMPLES =====")

    observed = False

    for ordinal in (140, 146, 240):
        if not samples[ordinal]:
            continue

        observed = True
        print()
        print(f"@{ordinal} {NAMES[ordinal]}")

        for a0, a1, a2, a3, tick in samples[ordinal]:
            floats = [
                as_float(value)
                for value in (a0, a1, a2, a3)
            ]

            print(
                "raw="
                f"{a0:08X} {a1:08X} {a2:08X} {a3:08X} "
                "float="
                f"{floats[0]:.6g} {floats[1]:.6g} "
                f"{floats[2]:.6g} {floats[3]:.6g} "
                f"tick={tick}"
            )

    print()
    print("===== @240 VALUE SUMMARY =====")

    if samples[240]:
        by_line = defaultdict(list)

        for line in raw.splitlines():
            parts = line.split()
            if len(parts) != 8 or parts[0] != "volume_route_probe":
                continue

            try:
                ordinal, target, a0, a1, a2, a3, tick = [
                    int(value, 16) for value in parts[1:]
                ]
            except ValueError:
                continue

            if ordinal != 240:
                continue

            by_line[a3].append((tick, as_float(a1), a0, a2))

        for line_id in sorted(by_line):
            rows = by_line[line_id]
            values = [value for _tick, value, _a0, _a2 in rows]

            finite = [
                value
                for value in values
                if value == value
                and abs(value) != float("inf")
            ]

            if not finite:
                continue

            print(
                f"line={line_id} "
                f"calls={len(rows)} "
                f"min={min(finite):.6g} "
                f"max={max(finite):.6g} "
                f"first={finite[0]:.6g} "
                f"last={finite[-1]:.6g}"
            )

            changes = []
            last_value = None

            for tick, value, _a0, _a2 in rows:
                if (
                    value != value
                    or abs(value) == float("inf")
                ):
                    continue

                if (
                    last_value is None
                    or abs(value - last_value) > 0.0005
                ):
                    changes.append((tick, value))
                    last_value = value

            preview = changes[:24]

            if preview:
                print(
                    "  transitions: "
                    + ", ".join(
                        f"{tick}:{value:.6g}"
                        for tick, value in preview
                    )
                )

                if len(changes) > len(preview):
                    print(
                        f"  ... {len(changes) - len(preview)} more transitions"
                    )

    print()
    print("===== RESULT =====")

    if bad_targets:
        raise SystemExit(
            "ERROR: one or more V24 probes could not resolve "
            "the original export target"
        )

    if not observed:
        print("V24_VOLUME_ROUTE: NOT_IN_FOCUSED_SET")
        print(
            "No @140/@146/@240 activity was observed; "
            "probe the secondary mutator group next."
        )
        return

    used = [
        f"@{ordinal} {NAMES[ordinal]}"
        for ordinal in (140, 146, 240)
        if counts[ordinal]
    ]

    print("V24_VOLUME_ROUTE: FOUND")
    print("Observed:", ", ".join(used))


if __name__ == "__main__":
    main()
