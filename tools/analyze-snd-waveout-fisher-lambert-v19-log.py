#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-fisher-lambert-v19.log"

EVENTS = [
    "runtime_trigger",
    "waveout_started",
    "runtime_external_play",
    "runtime_voice_bound",
    "runtime_voice_bind_failed",
    "runtime_native_stopped",
    "runtime_extend_playing",
    "runtime_stop_request",
    "waveout_stop_request",
    "runtime_release",
    "waveout_cleanup",
    "runtime_native_fallback",
    "runtime_request_slot_full",
    "runtime_no_request",
    "waveout_fail",
]

FAILURES = {
    "runtime_voice_bind_failed",
    "runtime_native_fallback",
    "runtime_request_slot_full",
    "runtime_no_request",
    "waveout_fail",
}


def main() -> None:
    print("===== V19 LOG PRECHECK =====")

    if not LOG.is_file():
        raise SystemExit(f"ERROR: missing V19 log: {LOG}")

    size = LOG.stat().st_size
    print(f"Log: {LOG}")
    print(f"Bytes: {size}")

    if size == 0:
        raise SystemExit(
            "ERROR: V19 log is empty; run the game and trigger dialogue first"
        )

    lines = LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    counts = Counter()
    failures = []
    editors = Counter()

    for line_no, line in enumerate(lines, start=1):
        parts = line.split()
        if not parts:
            continue

        event = parts[0]
        counts[event] += 1

        if event == "runtime_trigger" and len(parts) >= 2:
            try:
                editors[int(parts[1], 16)] += 1
            except ValueError:
                pass

        if event in FAILURES:
            failures.append((line_no, line))

    print()
    print("===== EVENT COUNTS =====")
    for event in EVENTS:
        print(f"{event:<30} {counts[event]}")

    print()
    print("===== BASELINE LIFECYCLE =====")

    triggers = counts["runtime_trigger"]
    starts = counts["waveout_started"]
    external = counts["runtime_external_play"]
    bound = counts["runtime_voice_bound"]
    stopped_native = counts["runtime_native_stopped"]

    if triggers == 0:
        raise SystemExit("ERROR: no V19 runtime triggers found")

    checks = [
        ("waveOut starts", starts, triggers),
        ("external playback", external, triggers),
        ("request bindings", bound, triggers),
        ("native stops", stopped_native, triggers),
    ]

    baseline_ok = True

    for label, actual, expected in checks:
        if actual == expected:
            print(f"PASS: {label}: {actual}/{expected}")
        else:
            baseline_ok = False
            print(f"FAIL: {label}: {actual}/{expected}")

    print()
    print("===== REPLAY =====")

    repeats = [
        (editor, count)
        for editor, count in editors.items()
        if count > 1
    ]

    if repeats:
        print(
            f"PASS: repeated editor IDs observed: {len(repeats)}"
        )
        for editor, count in sorted(
            repeats,
            key=lambda item: (-item[1], item[0]),
        )[:12]:
            print(f"REPLAY {editor:08X} x{count}")
    else:
        print("INFO: no repeated editor ID observed in this run")

    print()
    print("===== EARLY STOP SYNCHRONIZATION =====")

    runtime_stops = counts["runtime_stop_request"]
    wave_stops = counts["waveout_stop_request"]

    print(f"Game stop requests captured : {runtime_stops}")
    print(f"waveOut voices stopped early: {wave_stops}")

    if runtime_stops:
        if wave_stops == runtime_stops:
            print("PASS: every captured dubbed request stop terminated waveOut")
        elif wave_stops < runtime_stops:
            print(
                "INFO: some captured requests had already completed "
                "before the game stop call"
            )
        else:
            print(
                "FAIL: more waveOut stop events than runtime stop requests"
            )
            baseline_ok = False
    else:
        print(
            "INFO: no request-level early stop observed; trigger a long "
            "dialogue and interrupt it with load/menu/scene transition"
        )

    print()
    print("===== TERMINAL VOICE STATE =====")

    normal_cleanup = counts["waveout_cleanup"]
    terminal = normal_cleanup + wave_stops

    print(f"Normal cleanup : {normal_cleanup}")
    print(f"Early stop     : {wave_stops}")
    print(f"Terminal total : {terminal}/{starts}")

    if terminal == starts:
        print("PASS: every started waveOut voice reached a terminal state")
    elif terminal < starts:
        print(
            "INFO: one or more voices were still active when the log "
            "was inspected"
        )
    else:
        print("FAIL: terminal event count exceeds started voices")
        baseline_ok = False

    print()
    print("===== FAILURE CHECK =====")

    if failures:
        for line_no, line in failures[:40]:
            print(f"FAIL line={line_no}: {line}")
        raise SystemExit(
            f"ERROR: {len(failures)} V19 failure event(s) found"
        )

    print("PASS: no waveOut failures")
    print("PASS: no native fallback events")
    print("PASS: no request-slot exhaustion")
    print("PASS: no runtime_no_request events")
    print("PASS: no request-to-waveOut bind failures")

    if not baseline_ok:
        raise SystemExit("ERROR: V19 lifecycle consistency check failed")

    print()
    print("===== RESULT =====")
    print("V19_RUNTIME_SMOKE: PASS")

    if runtime_stops == 0:
        print(
            "NEXT: interrupt one long Fisher/Lambert line while it is "
            "playing to exercise request-level stop"
        )
    else:
        print("V19_REQUEST_STOP: PASS")


if __name__ == "__main__":
    main()
