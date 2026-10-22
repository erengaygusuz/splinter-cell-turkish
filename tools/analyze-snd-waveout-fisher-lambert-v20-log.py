#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-fisher-lambert-v20.log"

EVENTS = [
    "runtime_trigger",
    "waveout_started",
    "runtime_external_play",
    "runtime_voice_bound",
    "runtime_native_stopped",
    "runtime_extend_playing",
    "runtime_stop_request",
    "waveout_stop_request",
    "runtime_global_stop_types",
    "runtime_global_stop_objects",
    "waveout_stop_all",
    "runtime_release",
    "waveout_cleanup",
    "runtime_voice_bind_failed",
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


def main():
    print("===== V20 LOG PRECHECK =====")

    if not LOG.is_file():
        raise SystemExit(f"ERROR: missing V20 log: {LOG}")

    size = LOG.stat().st_size

    print(f"Log: {LOG}")
    print(f"Bytes: {size}")

    if size == 0:
        raise SystemExit(
            "ERROR: V20 log is empty; trigger a dubbed line first"
        )

    lines = LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    counts = Counter()
    failures = []

    for line_no, line in enumerate(lines, start=1):
        parts = line.split()

        if not parts:
            continue

        event = parts[0]
        counts[event] += 1

        if event in FAILURES:
            failures.append((line_no, line))

    print()
    print("===== EVENT COUNTS =====")

    for event in EVENTS:
        print(f"{event:<30} {counts[event]}")

    triggers = counts["runtime_trigger"]
    starts = counts["waveout_started"]
    bound = counts["runtime_voice_bound"]
    native = counts["runtime_native_stopped"]

    print()
    print("===== BASELINE =====")

    baseline_ok = True

    for label, actual in [
        ("waveOut starts", starts),
        ("request bindings", bound),
        ("native stops", native),
    ]:
        if actual == triggers:
            print(f"PASS: {label}: {actual}/{triggers}")
        else:
            print(f"FAIL: {label}: {actual}/{triggers}")
            baseline_ok = False

    request_stops = counts["runtime_stop_request"]
    request_wave_stops = counts["waveout_stop_request"]

    global_types = counts["runtime_global_stop_types"]
    global_objects = counts["runtime_global_stop_objects"]
    global_calls = global_types + global_objects
    global_wave_stops = counts["waveout_stop_all"]

    print()
    print("===== LIFECYCLE ROUTES =====")
    print(f"Request-level stops          : {request_stops}")
    print(f"Request waveOut stops        : {request_wave_stops}")
    print(f"KillAllSoundObjectTypes calls: {global_types}")
    print(f"KillAllSoundObjects calls    : {global_objects}")
    print(f"Global waveOut voices stopped: {global_wave_stops}")

    if global_calls:
        print("PASS: at least one global kill lifecycle route was observed")
    else:
        print("INFO: no global kill lifecycle route observed yet")

    if global_wave_stops:
        print("PASS: global lifecycle actually terminated external waveOut")
    elif global_calls:
        print(
            "INFO: global kill ran when no external dubbed voice "
            "was active"
        )
    else:
        print(
            "INFO: interrupt a long Fisher/Lambert line with save/load "
            "or a level transition"
        )

    print()
    print("===== TERMINAL VOICE STATE =====")

    terminal = (
        counts["waveout_cleanup"]
        + request_wave_stops
        + global_wave_stops
    )

    print(f"Normal cleanup    : {counts['waveout_cleanup']}")
    print(f"Request early stop: {request_wave_stops}")
    print(f"Global early stop : {global_wave_stops}")
    print(f"Terminal total    : {terminal}/{starts}")

    if terminal == starts:
        print("PASS: every started waveOut voice reached a terminal state")
    elif terminal < starts:
        print(
            "INFO: one or more voices were still active when "
            "the log was inspected"
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
            f"ERROR: {len(failures)} V20 failure event(s) found"
        )

    print("PASS: no runtime failure events")

    if not baseline_ok:
        raise SystemExit(
            "ERROR: V20 baseline lifecycle consistency failed"
        )

    print()
    print("===== RESULT =====")
    print("V20_RUNTIME_SMOKE: PASS")

    if global_wave_stops:
        print("V20_GLOBAL_STOP: PASS")
    elif global_calls:
        print(
            "NEXT: repeat interruption while a long dubbed line "
            "is definitely still audible"
        )
    else:
        print(
            "NEXT: exercise save/load or level transition during "
            "a long dubbed line"
        )


if __name__ == "__main__":
    main()
