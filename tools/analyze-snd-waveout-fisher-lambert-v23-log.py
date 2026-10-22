#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-fisher-lambert-v23.log"


def parse_hex(parts, index):
    try:
        return int(parts[index], 16)
    except (IndexError, ValueError):
        return None


def main():
    print("===== V23 ESC PAUSE LOG =====")

    if not LOG.is_file():
        raise SystemExit(
            f"ERROR: missing V23 log: {LOG}"
        )

    size = LOG.stat().st_size

    print(f"Log: {LOG}")
    print(f"Bytes: {size}")

    if size == 0:
        raise SystemExit(
            "ERROR: V23 log is empty; pause during a dubbed line first"
        )

    counts = Counter()
    pauses = []
    resumes = []
    pause_routes = []
    resume_routes = []

    for line_no, line in enumerate(
        LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        parts = line.split()

        if not parts:
            continue

        event = parts[0]
        counts[event] += 1

        if event == "v23_pause":
            values = [
                parse_hex(parts, i)
                for i in range(1, 5)
            ]

            if None not in values:
                pauses.append(
                    (line_no, *values)
                )

        elif event == "v23_resume":
            values = [
                parse_hex(parts, i)
                for i in range(1, 6)
            ]

            if None not in values:
                resumes.append(
                    (line_no, *values)
                )

        elif event == "v23_pause_route":
            ordinal = parse_hex(parts, 1)
            target = parse_hex(parts, 2)

            if (
                ordinal is not None
                and target is not None
            ):
                pause_routes.append(
                    (line_no, ordinal, target)
                )

        elif event == "v23_resume_route":
            ordinal = parse_hex(parts, 1)
            target = parse_hex(parts, 2)

            if (
                ordinal is not None
                and target is not None
            ):
                resume_routes.append(
                    (line_no, ordinal, target)
                )

    print()
    print("===== EVENT COUNTS =====")
    print(
        f"{'v23_pause':<24} "
        f"{counts['v23_pause']}"
    )
    print(
        f"{'v23_resume':<24} "
        f"{counts['v23_resume']}"
    )
    print(
        f"{'v23_pause_route':<24} "
        f"{counts['v23_pause_route']}"
    )
    print(
        f"{'v23_resume_route':<24} "
        f"{counts['v23_resume_route']}"
    )

    print()
    print("===== PAUSE EVENTS =====")

    if not pauses:
        print("NONE")
    else:
        for (
            line_no,
            paused_voices,
            active_requests,
            failures,
            tick,
        ) in pauses[:20]:
            print(
                f"line={line_no} "
                f"voices={paused_voices} "
                f"requests={active_requests} "
                f"failures={failures} "
                f"tick={tick}"
            )

    print()
    print("===== RESUME EVENTS =====")

    if not resumes:
        print("NONE")
    else:
        for (
            line_no,
            resumed_voices,
            resumed_requests,
            failures,
            pause_ms,
            tick,
        ) in resumes[:20]:
            print(
                f"line={line_no} "
                f"voices={resumed_voices} "
                f"requests={resumed_requests} "
                f"failures={failures} "
                f"pause_ms={pause_ms} "
                f"tick={tick}"
            )

    print()
    print("===== ROUTE CHECK =====")

    bad_routes = []

    for line_no, ordinal, target in pause_routes:
        if ordinal != 185 or target == 0:
            bad_routes.append(
                (
                    line_no,
                    "pause",
                    ordinal,
                    target,
                )
            )

    for line_no, ordinal, target in resume_routes:
        if ordinal != 212 or target == 0:
            bad_routes.append(
                (
                    line_no,
                    "resume",
                    ordinal,
                    target,
                )
            )

    if bad_routes:
        for item in bad_routes:
            print("FAIL:", item)

        raise SystemExit(
            "ERROR: V23 route mismatch or unresolved original target"
        )

    if not pause_routes:
        raise SystemExit(
            "ERROR: no V23 pause-route event observed"
        )

    if not resume_routes:
        raise SystemExit(
            "ERROR: no V23 resume-route event observed"
        )

    print("PASS: pause route resolves original @185")
    print("PASS: resume route resolves original @212")

    print()
    print("===== API FAILURE CHECK =====")

    failures = sum(
        event[3]
        for event in pauses
    ) + sum(
        event[3]
        for event in resumes
    )

    if failures:
        raise SystemExit(
            f"ERROR: V23 waveOut pause/resume failures: {failures}"
        )

    print("PASS: no waveOutPause/waveOutRestart failures")

    successful_pause = any(
        paused_voices > 0
        for (
            _,
            paused_voices,
            _,
            failures,
            _,
        ) in pauses
        if failures == 0
    )

    successful_resume = any(
        resumed_voices > 0
        for (
            _,
            resumed_voices,
            _,
            failures,
            _,
            _,
        ) in resumes
        if failures == 0
    )

    print()
    print("===== RESULT =====")

    if successful_pause and successful_resume:
        print("V23_ESC_PAUSE_RESUME: PASS")
        print(
            "External Fisher/Lambert dialogue paused and resumed "
            "through the real ESC lifecycle."
        )
    elif not successful_pause:
        print(
            "NEXT: press ESC while a long Fisher/Lambert "
            "dubbed line is actively audible"
        )
    else:
        print(
            "NEXT: return from the ESC menu while the paused "
            "dubbed line is still pending"
        )


if __name__ == "__main__":
    main()
