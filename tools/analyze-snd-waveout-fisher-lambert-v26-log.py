#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
LOG = GAME / "system/snd-waveout-volume-v26.log"


def hx(value: str):
    try:
        return int(value, 16)
    except ValueError:
        return None


def main():
    print("===== V26 SPEECH VOLUME BRIDGE =====")
    print("Log:", LOG)

    if not LOG.is_file():
        raise SystemExit("ERROR: V26 volume log is missing")

    raw = LOG.read_text(
        encoding="utf-8",
        errors="replace",
    )

    print("Bytes:", len(raw.encode("utf-8")))

    counts = Counter()
    speech = []
    applies = []

    for line_no, line in enumerate(
        raw.splitlines(),
        start=1,
    ):
        p = line.split()

        if not p:
            continue

        if p[0] == "v26_speech_volume" and len(p) == 8:
            values = [hx(x) for x in p[1:]]

            if any(x is None for x in values):
                continue

            (
                raw_db,
                qdb,
                volume_word,
                active,
                applied,
                failures,
                tick,
            ) = values

            speech.append(
                (
                    line_no,
                    raw_db,
                    qdb,
                    volume_word,
                    active,
                    applied,
                    failures,
                    tick,
                )
            )
            counts["speech"] += 1

        elif p[0] == "v26_voice_apply" and len(p) == 7:
            values = [hx(x) for x in p[1:]]

            if any(x is None for x in values):
                continue

            (
                request,
                qdb,
                volume_word,
                active,
                applied,
                failures,
            ) = values

            applies.append(
                (
                    line_no,
                    request,
                    qdb,
                    volume_word,
                    active,
                    applied,
                    failures,
                )
            )
            counts["apply"] += 1

    print()
    print("===== EVENT COUNTS =====")
    print("Speech-volume transitions:", counts["speech"])
    print("New-voice volume applies :", counts["apply"])

    print()
    print("===== SPEECH VOLUME TRANSITIONS =====")

    for (
        line_no,
        raw_db,
        qdb,
        volume_word,
        active,
        applied,
        failures,
        tick,
    ) in speech[:80]:
        mono = volume_word & 0xFFFF

        print(
            f"line={line_no} "
            f"raw_db_bits={raw_db:08X} "
            f"attenuation={qdb / 4:.2f}dB "
            f"waveout={mono}/65535 "
            f"active={active} "
            f"applied={applied} "
            f"failures={failures} "
            f"tick={tick}"
        )

    if len(speech) > 80:
        print(f"... {len(speech) - 80} more transitions")

    print()
    print("===== NEW VOICE INHERITANCE =====")

    for (
        line_no,
        request,
        qdb,
        volume_word,
        active,
        applied,
        failures,
    ) in applies[:40]:
        mono = volume_word & 0xFFFF

        print(
            f"line={line_no} "
            f"request={request:08X} "
            f"attenuation={qdb / 4:.2f}dB "
            f"waveout={mono}/65535 "
            f"active={active} "
            f"applied={applied} "
            f"failures={failures}"
        )

    if len(applies) > 40:
        print(f"... {len(applies) - 40} more applies")

    failures = sum(row[6] for row in speech)
    failures += sum(row[6] for row in applies)

    successful_live_changes = sum(
        1
        for row in speech
        if row[4] > 0 and row[5] > 0
    )

    successful_inheritance = sum(
        1
        for row in applies
        if row[4] > 0 and row[5] > 0
    )

    print()
    print("===== RESULT =====")

    if not speech:
        raise SystemExit(
            "V26_SPEECH_VOLUME: NO_SPEECH_VOLUME_EVENT"
        )

    if failures:
        raise SystemExit(
            f"V26_SPEECH_VOLUME: FAIL ({failures} waveOutSetVolume failures)"
        )

    if not successful_live_changes:
        print(
            "INFO: speech volume changed, but no external dub was "
            "active during a quantized transition"
        )
    else:
        print(
            "PASS: active external dub volume changed with the speech slider"
        )

    if not successful_inheritance:
        print(
            "INFO: no later dubbed voice inherited a stored volume yet"
        )
    else:
        print(
            "PASS: later dubbed voice inherited the stored speech volume"
        )

    print("PASS: no waveOutSetVolume failures")
    print("V26_SPEECH_VOLUME: PASS")


if __name__ == "__main__":
    main()
