#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path

GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
DLL = GAME / "system/SNDDSound3DDLL_VBR_orig.dll"

KEYWORDS = (
    "vol",
    "volume",
    "gain",
    "atten",
    "mix",
    "master",
    "listener",
)


def main():
    print("===== SND VOLUME EXPORT CANDIDATES =====")

    if not DLL.is_file():
        raise SystemExit(f"ERROR: missing original DLL: {DLL}")

    output = subprocess.check_output(
        ["llvm-readobj", "--coff-exports", str(DLL)],
        text=True,
    )

    rows = []

    for block in re.findall(r"Export \{(.*?)\n\}", output, re.S):
        ordinal = re.search(r"Ordinal: (\d+)", block)
        name = re.search(r"Name: (.+)", block)

        if not ordinal or not name:
            continue

        ord_value = int(ordinal.group(1))
        export_name = name.group(1).strip()

        if any(
            keyword in export_name.lower()
            for keyword in KEYWORDS
        ):
            rows.append((ord_value, export_name))

    if not rows:
        print("No keyword-matched volume exports found.")
        print()
        print("===== ALL SET/GET STYLE EXPORTS =====")

        for block in re.findall(r"Export \{(.*?)\n\}", output, re.S):
            ordinal = re.search(r"Ordinal: (\d+)", block)
            name = re.search(r"Name: (.+)", block)

            if not ordinal or not name:
                continue

            export_name = name.group(1).strip()

            if re.search(r"(Set|Get|Change|Adjust)", export_name, re.I):
                print(
                    f"@{int(ordinal.group(1)):<3} "
                    f"{export_name}"
                )
        return

    for ordinal, export_name in rows:
        print(f"@{ordinal:<3} {export_name}")

    print()
    print("RESULT: copy this output back for the V24 volume-route probe.")


if __name__ == "__main__":
    main()
