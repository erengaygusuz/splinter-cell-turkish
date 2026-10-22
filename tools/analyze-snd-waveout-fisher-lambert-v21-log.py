#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-fisher-lambert-v21.log"

EVENTS = [
    "runtime_trigger",
    "waveout_started",
    "runtime_voice_bound",
    "runtime_native_stopped",
    "runtime_pause_all_types",
    "runtime_pause_all_types_but_one",
    "waveout_pause",
    "runtime_resume_all_types",
    "runtime_resume_all_types_but_one",
    "waveout_resume",
    "runtime_stop_request",
    "waveout_stop_request",
    "runtime_global_stop_types",
    "runtime_global_stop_objects",
    "waveout_stop_all",
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


def parse_hex(parts, index):
    try:
        return int(parts[index], 16)
    except (IndexError, ValueError):
        return None


def main():
    print("===== V21 LOG PRECHECK =====")

    if not LOG.is_file():
        raise SystemExit(f"ERROR: missing V21 log: {LOG}")

    size = LOG.stat().st_size

    print(f"Log: {LOG}")
    print(f"Bytes: {size}")

    if size == 0:
        raise SystemExit(
            "ERROR: V21 log is empty; trigger a dubbed line first"
        )

    lines = LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    counts = Counter()
    failures = []
    pause_api_failures = []
    resume_api_failures = []
    resume_durations = []

    for line_no, line in enumerate(lines, start=1):
        parts = line.split()

        if not parts:
            continue

        event = parts[0]
        counts[event] += 1

        if event in FAILURES:
            failures.append((line_no, line))

        if event == "waveout_pause":
            result = parse_hex(parts, 5)
            if result is None or result != 0:
                pause_api_failures.append((line_no, line))

        if event == "waveout_resume":
            result = parse_hex(parts, 5)
            paused_ms = parse_hex(parts, 6)

            if result is None or result != 0:
                resume_api_failures.append((line_no, line))

            if paused_ms is not None:
                resume_durations.append(paused_ms)

    print()
    print("===== EVENT COUNTS =====")

    for event in EVENTS:
        print(f"{event:<36} {counts[event]}")

    triggers = counts["runtime_trigger"]

    print()
    print("===== BASELINE =====")

    baseline_ok = True

    for label, actual in [
        ("waveOut starts", counts["waveout_started"]),
        ("request bindings", counts["runtime_voice_bound"]),
        ("native stops", counts["runtime_native_stopped"]),
    ]:
        if actual == triggers:
            print(f"PASS: {label}: {actual}/{triggers}")
        else:
            print(f"FAIL: {label}: {actual}/{triggers}")
            baseline_ok = False

    pause_calls = (
        counts["runtime_pause_all_types"]
        + counts["runtime_pause_all_types_but_one"]
    )
    resume_calls = (
        counts["runtime_resume_all_types"]
        + counts["runtime_resume_all_types_but_one"]
    )

    print()
    print("===== PAUSE / RESUME ROUTES =====")
    print(
        "PauseAllSoundObjectTypes calls      : "
        f"{counts['runtime_pause_all_types']}"
    )
    print(
        "PauseAllSoundObjectTypesButOne calls: "
        f"{counts['runtime_pause_all_types_but_one']}"
    )
    print(
        "ResumeAllSoundObjectTypes calls      : "
        f"{counts['runtime_resume_all_types']}"
    )
    print(
        "ResumeAllSoundObjectTypesButOne calls: "
        f"{counts['runtime_resume_all_types_but_one']}"
    )
    print(f"waveOut pause operations              : {counts['waveout_pause']}")
    print(f"waveOut resume operations             : {counts['waveout_resume']}")

    if pause_calls:
        print("PASS: game pause lifecycle route observed")
    else:
        print("INFO: no hooked pause lifecycle route observed")

    if counts["waveout_pause"]:
        print("PASS: active external dialogue was paused")
    elif pause_calls:
        print(
            "INFO: pause route ran without an active external dialogue"
        )

    if counts["waveout_resume"]:
        print("PASS: paused external dialogue was resumed")
    elif resume_calls:
        print(
            "INFO: resume route ran without a paused external dialogue"
        )

    if resume_durations:
        print(
            "Observed pause duration(s) ms        : "
            + ", ".join(map(str, resume_durations[:12]))
        )

    print()
    print("===== GLOBAL STOP RETENTION =====")
    print(
        "KillAllSoundObjectTypes calls: "
        f"{counts['runtime_global_stop_types']}"
    )
    print(
        "KillAllSoundObjects calls    : "
        f"{counts['runtime_global_stop_objects']}"
    )
    print(
        "Global waveOut stops         : "
        f"{counts['waveout_stop_all']}"
    )

    print()
    print("===== FAILURE CHECK =====")

    if failures:
        for line_no, line in failures[:40]:
            print(f"FAIL runtime line={line_no}: {line}")

    if pause_api_failures:
        for line_no, line in pause_api_failures[:20]:
            print(f"FAIL waveOutPause line={line_no}: {line}")

    if resume_api_failures:
        for line_no, line in resume_api_failures[:20]:
            print(f"FAIL waveOutRestart line={line_no}: {line}")

    if failures or pause_api_failures or resume_api_failures:
        raise SystemExit(
            "ERROR: V21 runtime/pause API failure event(s) found"
        )

    print("PASS: no runtime failure events")
    print("PASS: no waveOutPause errors")
    print("PASS: no waveOutRestart errors")

    if not baseline_ok:
        raise SystemExit(
            "ERROR: V21 baseline lifecycle consistency failed"
        )

    print()
    print("===== RESULT =====")
    print("V21_RUNTIME_SMOKE: PASS")

    if (
        counts["waveout_pause"] > 0
        and counts["waveout_resume"] > 0
    ):
        print("V21_PAUSE_RESUME: PASS")
    elif pause_calls == 0:
        print(
            "NEXT: pause the game while a long Fisher/Lambert line "
            "is definitely audible"
        )
    elif counts["waveout_pause"] == 0:
        print(
            "NEXT: repeat pause while an external dubbed line is active"
        )
    else:
        print(
            "NEXT: resume gameplay after the pause so waveOutRestart "
            "can be observed"
        )


if __name__ == "__main__":
    main()
