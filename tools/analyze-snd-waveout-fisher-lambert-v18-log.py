#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-fisher-lambert-v18.log"

IMPORTANT = {
    "runtime_trigger",
    "waveout_started",
    "runtime_external_play",
    "runtime_native_stopped",
    "runtime_extend_playing",
    "runtime_release",
    "waveout_cleanup",
    "runtime_native_fallback",
    "runtime_request_slot_full",
    "runtime_no_request",
    "waveout_fail",
}

FAILURE_EVENTS = {
    "runtime_native_fallback",
    "runtime_request_slot_full",
    "runtime_no_request",
    "waveout_fail",
}


def parse_hex(value: str) -> int:
    return int(value, 16)


def main() -> None:
    print("===== V18 LOG PRECHECK =====")

    if not LOG.is_file():
        raise SystemExit(f"ERROR: missing V18 log: {LOG}")

    size = LOG.stat().st_size
    print(f"Log: {LOG}")
    print(f"Bytes: {size}")

    if size == 0:
        raise SystemExit(
            "ERROR: V18 log is empty; run the game and trigger dialogue first"
        )

    lines = LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    events = Counter()
    editors = Counter()
    editor_banks = Counter()
    repeated_editors = Counter()
    native_intervals = []
    failures = []
    triggers = []

    for line_number, line in enumerate(lines, start=1):
        parts = line.split()

        if not parts:
            continue

        label = parts[0]
        events[label] += 1

        if label == "runtime_trigger" and len(parts) >= 7:
            editor = parse_hex(parts[1])
            now = parse_hex(parts[6])

            editors[editor] += 1
            editor_banks[editor & 0xFFFF0000] += 1
            triggers.append((now, editor, line_number, line))

        elif label == "runtime_native_stopped" and len(parts) >= 6:
            editor = parse_hex(parts[1])
            request_id = parse_hex(parts[2])
            duration_ms = parse_hex(parts[3])
            until = parse_hex(parts[4])
            now = parse_hex(parts[5])

            native_intervals.append(
                {
                    "editor": editor,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "start": now,
                    "until": until,
                    "line": line_number,
                }
            )

        if label in FAILURE_EVENTS:
            failures.append((line_number, line))

    for editor, count in editors.items():
        if count > 1:
            repeated_editors[editor] = count

    print()
    print("===== EVENT COUNTS =====")

    for label in sorted(IMPORTANT):
        print(f"{label:<28} {events[label]}")

    print()
    print("===== COVERAGE =====")
    print(f"Runtime triggers       : {events['runtime_trigger']}")
    print(f"Unique editor IDs      : {len(editors)}")
    print(f"Unique editor banks    : {len(editor_banks)}")

    if editor_banks:
        print(
            "Banks                  : "
            + ", ".join(
                f"{bank:04X}={count}"
                for bank, count in sorted(editor_banks.items())
            )
        )

    print()
    print("===== REPLAY CHECK =====")

    if repeated_editors:
        print(
            f"PASS: repeated editor IDs observed: {len(repeated_editors)}"
        )

        for editor, count in repeated_editors.most_common(12):
            print(f"REPLAY {editor:08X} x{count}")
    else:
        print(
            "INFO: no editor ID repeated yet; replay safety not exercised"
        )

    print()
    print("===== LOGICAL REQUEST CONCURRENCY =====")

    points = []

    for row in native_intervals:
        points.append((row["start"], 1, row))
        points.append((row["until"], -1, row))

    # End before start at the same tick so back-to-back requests do not
    # count as overlapping.
    points.sort(key=lambda x: (x[0], x[1]))

    active = 0
    peak = 0
    peak_rows = []
    current = {}

    for tick, delta, row in points:
        key = (row["request_id"], row["start"], row["line"])

        if delta < 0:
            current.pop(key, None)
            active = max(0, active - 1)
        else:
            current[key] = row
            active += 1

            if active > peak:
                peak = active
                peak_rows = list(current.values())

    print(f"Tracked runtime requests: {len(native_intervals)}")
    print(f"Peak concurrent requests: {peak}")

    if peak >= 2:
        print("PASS: multi-request overlap exercised")

        for row in sorted(
            peak_rows,
            key=lambda x: (x["start"], x["request_id"]),
        )[:8]:
            print(
                "OVERLAP "
                f"editor={row['editor']:08X} "
                f"request={row['request_id']:08X} "
                f"duration_ms={row['duration_ms']} "
                f"start={row['start']:08X} "
                f"until={row['until']:08X}"
            )
    else:
        print(
            "INFO: no overlapping logical requests observed yet"
        )

    print()
    print("===== FAILURE CHECK =====")

    if failures:
        for line_number, line in failures[:40]:
            print(f"FAIL line={line_number}: {line}")

        raise SystemExit(
            f"ERROR: {len(failures)} V18 failure/fallback event(s) found"
        )

    print("PASS: no waveOut failures")
    print("PASS: no native fallback events")
    print("PASS: no request-slot exhaustion")
    print("PASS: no runtime_no_request events")

    print()
    print("===== LIFECYCLE CHECK =====")

    trigger_count = events["runtime_trigger"]
    external_count = events["runtime_external_play"]
    stopped_count = events["runtime_native_stopped"]
    release_count = events["runtime_release"]
    started_count = events["waveout_started"]
    cleanup_count = events["waveout_cleanup"]

    if trigger_count == 0:
        raise SystemExit("ERROR: no V18 runtime triggers found")

    if external_count != trigger_count:
        raise SystemExit(
            "ERROR: runtime_external_play count does not match triggers: "
            f"{external_count} != {trigger_count}"
        )

    if started_count != trigger_count:
        raise SystemExit(
            "ERROR: waveout_started count does not match triggers: "
            f"{started_count} != {trigger_count}"
        )

    if stopped_count != trigger_count:
        raise SystemExit(
            "ERROR: runtime_native_stopped count does not match triggers: "
            f"{stopped_count} != {trigger_count}"
        )

    if release_count > stopped_count:
        raise SystemExit(
            "ERROR: more releases than tracked runtime requests"
        )

    if cleanup_count > started_count:
        raise SystemExit(
            "ERROR: more waveOut cleanups than starts"
        )

    print("PASS: every trigger started external playback")
    print("PASS: every trigger captured and stopped its native request")
    print(
        f"Release progress       : {release_count}/{stopped_count}"
    )
    print(
        f"waveOut cleanup progress: {cleanup_count}/{started_count}"
    )

    print()
    print("===== RESULT =====")
    print("V18_RUNTIME_SMOKE: PASS")

    if peak < 2:
        print("NEXT: exercise at least one overlapping dialogue sequence")

    if not repeated_editors:
        print("NEXT: replay at least one previously triggered dialogue line")


if __name__ == "__main__":
    main()
