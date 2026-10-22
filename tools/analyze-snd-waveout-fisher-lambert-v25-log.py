#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
SYSTEM = GAME / "system"

RUNTIME_LOG = SYSTEM / "snd-waveout-fisher-lambert-v21.log"
PAUSE_LOG = SYSTEM / "snd-waveout-fisher-lambert-v23.log"


def hx(value: str):
    try:
        return int(value, 16)
    except ValueError:
        return None


def parse_pause_log():
    pauses = []
    resumes = []

    for line_no, line in enumerate(
        PAUSE_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        p = line.split()

        if not p:
            continue

        if p[0] == "v23_pause" and len(p) == 5:
            values = [hx(value) for value in p[1:]]

            if None in values:
                continue

            voices, requests, failures, tick = values

            pauses.append(
                {
                    "line": line_no,
                    "voices": voices,
                    "requests": requests,
                    "failures": failures,
                    "tick": tick,
                    "raw": line,
                }
            )

        elif p[0] == "v23_resume" and len(p) == 6:
            values = [hx(value) for value in p[1:]]

            if None in values:
                continue

            (
                voices,
                requests,
                failures,
                pause_ms,
                tick,
            ) = values

            resumes.append(
                {
                    "line": line_no,
                    "voices": voices,
                    "requests": requests,
                    "failures": failures,
                    "pause_ms": pause_ms,
                    "tick": tick,
                    "raw": line,
                }
            )

    return pauses, resumes


def parse_releases():
    releases = []

    for line_no, line in enumerate(
        RUNTIME_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        p = line.split()

        if (
            len(p) != 4
            or p[0] != "runtime_release"
        ):
            continue

        editor = hx(p[1])
        request = hx(p[2])
        tick = hx(p[3])

        if None in (editor, request, tick):
            continue

        releases.append(
            {
                "line": line_no,
                "editor": editor,
                "request": request,
                "tick": tick,
                "raw": line,
            }
        )

    return releases


def main():
    print("===== V25 PAUSED REQUEST GUARD =====")
    print("Runtime log:", RUNTIME_LOG)
    print("Pause log  :", PAUSE_LOG)

    if not RUNTIME_LOG.is_file():
        raise SystemExit("ERROR: runtime log is missing")

    if not PAUSE_LOG.is_file():
        raise SystemExit("ERROR: pause log is missing")

    pauses, resumes = parse_pause_log()
    releases = parse_releases()

    active_pauses = [
        row
        for row in pauses
        if row["voices"] > 0
        and row["requests"] > 0
    ]

    active_resumes = [
        row
        for row in resumes
        if row["voices"] > 0
    ]

    print()
    print("===== ACTIVE PAUSES =====")
    print("count:", len(active_pauses))

    for row in active_pauses:
        print(row["raw"])

    print()
    print("===== ACTIVE RESUMES =====")
    print("count:", len(active_resumes))

    for row in active_resumes:
        print(row["raw"])

    pairs = []
    used_resume_lines = set()

    for pause in active_pauses:
        candidates = [
            resume
            for resume in active_resumes
            if resume["tick"] >= pause["tick"]
            and resume["line"] not in used_resume_lines
        ]

        if not candidates:
            continue

        resume = min(
            candidates,
            key=lambda row: row["tick"],
        )

        used_resume_lines.add(resume["line"])

        interval_releases = [
            release
            for release in releases
            if pause["tick"]
            <= release["tick"]
            <= resume["tick"]
        ]

        pairs.append(
            {
                "pause": pause,
                "resume": resume,
                "releases": interval_releases,
            }
        )

    print()
    print("===== PAUSE/RESUME PAIRS =====")
    print("count:", len(pairs))

    good_pairs = 0

    for index, pair in enumerate(pairs, start=1):
        pause = pair["pause"]
        resume = pair["resume"]
        interval_releases = pair["releases"]

        request_preserved = (
            resume["requests"] > 0
        )

        no_failures = (
            pause["failures"] == 0
            and resume["failures"] == 0
        )

        no_release = not interval_releases

        if (
            request_preserved
            and no_failures
            and no_release
        ):
            good_pairs += 1

        print(
            f"pair={index} "
            f"pause_tick={pause['tick']} "
            f"resume_tick={resume['tick']} "
            f"pause_ms={resume['pause_ms']} "
            f"pause_requests={pause['requests']} "
            f"resume_requests={resume['requests']} "
            f"releases_inside={len(interval_releases)} "
            f"failures={pause['failures'] + resume['failures']}"
        )

        for release in interval_releases:
            print(
                "  RELEASE ",
                f"editor={release['editor']:08X} ",
                f"request={release['request']:08X} ",
                f"tick={release['tick']}",
                sep="",
            )

    print()
    print("===== RESULT =====")

    if not pairs:
        raise SystemExit(
            "V25_PAUSED_REQUEST_GUARD: NO_ACTIVE_PAUSE_TEST"
        )

    if good_pairs != len(pairs):
        raise SystemExit(
            "V25_PAUSED_REQUEST_GUARD: FAIL"
        )

    print(
        "PASS: every resumed external voice retained "
        "its logical runtime request"
    )
    print(
        "PASS: no runtime_release occurred inside "
        "the tested pause interval"
    )
    print(
        "V25_PAUSED_REQUEST_GUARD: PASS"
    )


if __name__ == "__main__":
    main()
