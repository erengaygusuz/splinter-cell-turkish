#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import struct
from collections import defaultdict
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
SYSTEM = GAME / "system"

RUNTIME_LOG = SYSTEM / "snd-waveout-fisher-lambert-v21.log"
VOLUME_LOG = SYSTEM / "snd-volume-v24-diag.log"
MANIFEST = PROJECT / "manifests/runtime-dub-authoritative.csv"

NEAR_MS = 900
TRANSITION_EPSILON = 0.0005


def as_float(value: int) -> float:
    return struct.unpack("<f", value.to_bytes(4, "little"))[0]


def parse_hex(value: str) -> int | None:
    try:
        return int(value, 16)
    except ValueError:
        return None


def load_editor_labels() -> dict[int, str]:
    labels: dict[int, str] = {}

    if not MANIFEST.is_file():
        return labels

    with MANIFEST.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        for row in csv.DictReader(handle):
            raw = (row.get("editor_id") or "").strip()

            if not raw:
                continue

            try:
                editor = int(raw, 0)
            except ValueError:
                try:
                    editor = int(raw)
                except ValueError:
                    continue

            uid = (row.get("id") or "").strip()
            speaker = (row.get("speaker") or "").strip()
            sound_object = (row.get("sound_object") or "").strip()

            parts = [
                part
                for part in (uid, speaker, sound_object)
                if part
            ]

            if parts:
                labels[editor] = " | ".join(parts)

    return labels


def parse_volume_transitions():
    groups: dict[int, list[tuple[int, float]]] = defaultdict(list)

    for line in VOLUME_LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        parts = line.split()

        if len(parts) != 8 or parts[0] != "volume_route_probe":
            continue

        ordinal = parse_hex(parts[1])

        if ordinal != 240:
            continue

        a1 = parse_hex(parts[4])
        line_id = parse_hex(parts[6])
        tick = parse_hex(parts[7])

        if None in (a1, line_id, tick):
            continue

        value = as_float(a1)

        if not math.isfinite(value):
            continue

        groups[line_id].append((tick, value))

    candidates = []

    for line_id, rows in groups.items():
        if len(rows) < 2:
            continue

        transitions = []
        last_value = None

        for tick, value in rows:
            if (
                last_value is None
                or abs(value - last_value) > TRANSITION_EPSILON
            ):
                transitions.append((tick, value))
                last_value = value

        values = [value for _tick, value in rows]
        value_range = max(values) - min(values)

        candidates.append(
            (
                len(transitions),
                value_range,
                len(rows),
                line_id,
                transitions,
            )
        )

    if not candidates:
        return None

    candidates.sort(reverse=True)
    _count, _range, calls, line_id, transitions = candidates[0]

    return {
        "line_id": line_id,
        "calls": calls,
        "transitions": transitions,
    }


def parse_runtime():
    triggers = []
    bound_requests: dict[tuple[int, int], int] = {}

    for line_no, line in enumerate(
        RUNTIME_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        parts = line.split()

        if not parts:
            continue

        if parts[0] == "runtime_trigger" and len(parts) >= 7:
            editor = parse_hex(parts[1])
            duration_ms = parse_hex(parts[4])
            tick = parse_hex(parts[6])

            if None in (editor, duration_ms, tick):
                continue

            triggers.append(
                {
                    "line": line_no,
                    "editor": editor,
                    "duration_ms": duration_ms,
                    "tick": tick,
                    "end": tick + duration_ms,
                }
            )

        elif parts[0] == "runtime_voice_bound" and len(parts) >= 5:
            editor = parse_hex(parts[1])
            request_id = parse_hex(parts[2])
            success = parse_hex(parts[3])
            tick = parse_hex(parts[4])

            if (
                None not in (editor, request_id, success, tick)
                and success
            ):
                bound_requests[(editor, tick)] = request_id

    triggers.sort(key=lambda row: row["tick"])
    return triggers, bound_requests


def nearest_transition(tick: int, transitions):
    if not transitions:
        return None

    best = min(
        transitions,
        key=lambda item: abs(item[0] - tick),
    )

    delta = tick - best[0]

    if abs(delta) > NEAR_MS:
        return None

    return best, delta


def label(editor: int, labels: dict[int, str]) -> str:
    extra = labels.get(editor)

    if extra:
        return f"{editor:08X} ({extra})"

    return f"{editor:08X}"


def main():
    print("===== V25 OVERLAP EVIDENCE =====")
    print("Runtime log:", RUNTIME_LOG)
    print("Volume log :", VOLUME_LOG)

    if not RUNTIME_LOG.is_file():
        raise SystemExit("ERROR: V21 runtime log is missing")

    if not VOLUME_LOG.is_file():
        raise SystemExit("ERROR: V24 volume log is missing")

    volume = parse_volume_transitions()

    if volume is None:
        raise SystemExit(
            "ERROR: could not identify changing @240 volume line"
        )

    transitions = volume["transitions"]
    labels = load_editor_labels()
    triggers, _bound = parse_runtime()

    print()
    print("===== DETECTED SPEECH-VOLUME LINE =====")
    print("line_id:", volume["line_id"])
    print("calls:", volume["calls"])
    print("transitions:", len(transitions))

    preview = transitions[:30]

    for tick, value in preview:
        print(f"  {tick}: {value:.6g}")

    if len(transitions) > len(preview):
        print(
            f"  ... {len(transitions) - len(preview)} more transitions"
        )

    near_triggers = []

    for trigger in triggers:
        near = nearest_transition(
            trigger["tick"],
            transitions,
        )

        if near is None:
            continue

        (transition_tick, volume_value), delta = near
        near_triggers.append(
            (
                trigger,
                transition_tick,
                volume_value,
                delta,
            )
        )

    print()
    print("===== DUB TRIGGERS NEAR VOLUME CHANGES =====")
    print("count:", len(near_triggers))

    for (
        trigger,
        transition_tick,
        volume_value,
        delta,
    ) in near_triggers[:60]:
        print(
            f"runtime_line={trigger['line']} "
            f"editor={label(trigger['editor'], labels)} "
            f"duration_ms={trigger['duration_ms']} "
            f"tick={trigger['tick']} "
            f"volume_tick={transition_tick} "
            f"delta_ms={delta:+d} "
            f"volume={volume_value:.6g}"
        )

    if len(near_triggers) > 60:
        print(
            f"... {len(near_triggers) - 60} more nearby triggers"
        )

    active = []
    overlaps = []

    for trigger in triggers:
        tick = trigger["tick"]

        active = [
            previous
            for previous in active
            if previous["end"] > tick
        ]

        near = nearest_transition(tick, transitions)

        if near is not None:
            for previous in active:
                overlaps.append(
                    {
                        "previous": previous,
                        "current": trigger,
                        "same_editor": (
                            previous["editor"]
                            == trigger["editor"]
                        ),
                        "overlap_ms": previous["end"] - tick,
                        "transition": near,
                    }
                )

        active.append(trigger)

    print()
    print("===== OVERLAPS NEAR VOLUME CHANGES =====")
    print("count:", len(overlaps))

    same_editor_count = sum(
        1
        for row in overlaps
        if row["same_editor"]
    )

    print("same_editor:", same_editor_count)
    print(
        "different_editor:",
        len(overlaps) - same_editor_count,
    )

    for row in overlaps[:80]:
        previous = row["previous"]
        current = row["current"]
        (transition_tick, volume_value), delta = row["transition"]

        print(
            "SAME" if row["same_editor"] else "DIFF",
            f"prev={label(previous['editor'], labels)}",
            f"cur={label(current['editor'], labels)}",
            f"prev_tick={previous['tick']}",
            f"cur_tick={current['tick']}",
            f"overlap_ms={row['overlap_ms']}",
            f"volume_tick={transition_tick}",
            f"delta_ms={delta:+d}",
            f"volume={volume_value:.6g}",
        )

    if len(overlaps) > 80:
        print(
            f"... {len(overlaps) - 80} more overlap rows"
        )

    print()
    print("===== RESULT =====")

    if same_editor_count:
        print("V25_EVIDENCE: SAME_EDITOR_RETRIGGER")
        print(
            "The same dubbed sound is retriggered before its "
            "external WAV finishes during speech-volume changes."
        )
    elif overlaps:
        print("V25_EVIDENCE: DIFFERENT_EDITOR_OVERLAP")
        print(
            "Different dubbed requests overlap near speech-volume "
            "changes; replacement/stop semantics must be mirrored."
        )
    elif near_triggers:
        print("V25_EVIDENCE: RETRIGGER_WITHOUT_DURATION_OVERLAP")
        print(
            "Speech-volume changes trigger dubbed requests, but the "
            "logged duration windows do not overlap."
        )
    else:
        print("V25_EVIDENCE: NO_DUB_TRIGGER_CORRELATION")
        print(
            "No Fisher/Lambert runtime trigger correlates with the "
            "speech-volume slider transitions."
        )


if __name__ == "__main__":
    main()
