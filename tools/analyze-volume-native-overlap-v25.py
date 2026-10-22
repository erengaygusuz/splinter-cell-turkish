#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
SYSTEM = GAME / "system"

RUNTIME = SYSTEM / "snd-waveout-fisher-lambert-v21.log"
VOLUME = SYSTEM / "snd-volume-v24-diag.log"

EVENTS = {
    "dare_play",
    "dare_play_ret",
    "diag_send",
    "diag_return",
    "runtime_trigger",
    "runtime_external_play",
    "runtime_native_stopped",
    "runtime_voice_bound",
    "runtime_stop_request",
    "waveout_stop_request",
    "runtime_global_stop_types",
    "runtime_global_stop_objects",
    "waveout_stop_all",
    "waveout_cleanup",
}

WINDOW_MS = 1200


def h(value: str):
    try:
        return int(value, 16)
    except ValueError:
        return None


def volume_window():
    ticks = []

    for line in VOLUME.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        p = line.split()

        if len(p) != 8 or p[0] != "volume_route_probe":
            continue

        ordinal = h(p[1])
        line_id = h(p[6])
        tick = h(p[7])

        if ordinal == 240 and line_id == 2 and tick is not None:
            ticks.append(tick)

    if not ticks:
        raise SystemExit("ERROR: no @240 line=2 events in V24 log")

    return min(ticks), max(ticks)


def event_tick(parts):
    # Runtime log events place GetTickCount in their final field.
    if len(parts) < 2:
        return None
    return h(parts[-1])


def main():
    print("===== V25 NATIVE/EXTERNAL OVERLAP EVIDENCE =====")
    print("Runtime:", RUNTIME)
    print("Volume :", VOLUME)

    if not RUNTIME.is_file() or not VOLUME.is_file():
        raise SystemExit("ERROR: required log is missing")

    start, end = volume_window()

    print()
    print("Speech-volume activity:")
    print(" start:", start)
    print(" end  :", end)
    print(" span :", end - start, "ms")

    lo = start - WINDOW_MS
    hi = end + WINDOW_MS

    rows = []

    for line_no, line in enumerate(
        RUNTIME.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        p = line.split()

        if not p or p[0] not in EVENTS:
            continue

        tick = event_tick(p)

        if tick is None or not (lo <= tick <= hi):
            continue

        rows.append((tick, line_no, line))

    rows.sort()

    print()
    print("===== RUNTIME EVENTS AROUND SPEECH-VOLUME CHANGES =====")
    print("count:", len(rows))

    for tick, line_no, line in rows[:250]:
        relation = (
            "BEFORE"
            if tick < start
            else "AFTER"
            if tick > end
            else "DURING"
        )
        print(
            f"{relation:<6} tick={tick} "
            f"runtime_line={line_no} {line}"
        )

    if len(rows) > 250:
        print(f"... {len(rows) - 250} more rows")

    counts = {}

    for _tick, _line_no, line in rows:
        event = line.split()[0]
        counts[event] = counts.get(event, 0) + 1

    print()
    print("===== EVENT COUNTS IN WINDOW =====")

    for event in sorted(EVENTS):
        print(f"{event:<28} {counts.get(event, 0)}")

    print()
    print("===== RESULT =====")

    if counts.get("runtime_trigger", 0):
        print("V25_NATIVE_EVIDENCE: EXTERNAL_RETRIGGER_PRESENT")
    elif counts.get("dare_play", 0) or counts.get("diag_send", 0):
        print("V25_NATIVE_EVIDENCE: DAREAUDIO_ACTIVITY_WITHOUT_EXTERNAL_MATCH")
        print(
            "A sound/voice is being requested during speech-volume changes, "
            "but it is not one of the 408 external dub matches."
        )
    else:
        print("V25_NATIVE_EVIDENCE: NO_NEW_DAREAUDIO_REQUEST")
        print(
            "The overlap is not caused by a new PlaySoundW/send-request event; "
            "inspect volume-change behavior on an already existing native voice."
        )


if __name__ == "__main__":
    main()
