#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "gameplay-subtitle-poc"
    / "src"
    / "snd_log_probe_v2.cpp"
)

ORIGINAL = (
    ROOT
    / "build"
    / "gameplay-subtitle-poc"
    / "SNDDSound3DDLL_VBR_orig.dll"
)

OUT = ROOT / "build" / "snd-log-probe-v2"


def run(*args: str) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def exports(path: Path) -> list[tuple[int, str]]:
    text = run("llvm-readobj", "--coff-exports", str(path))

    blocks = re.findall(
        r"Export \{(.*?)\n\}",
        text,
        flags=re.S,
    )

    found: list[tuple[int, str]] = []

    for block in blocks:
        ordinal = re.search(r"Ordinal: (\d+)", block)
        name = re.search(r"Name: (.+)", block)

        if ordinal and name:
            found.append(
                (
                    int(ordinal.group(1)),
                    name.group(1).strip(),
                )
            )

    return found


def build_import_library() -> Path:
    definition = OUT / "kernel32.def"

    names = [
        ("LoadLibraryA", 4),
        ("GetProcAddress", 8),
        ("DisableThreadLibraryCalls", 4),
        ("CreateFileA", 28),
        ("WriteFile", 20),
        ("SetFilePointer", 16),
        ("CloseHandle", 4),
    ]

    definition.write_text(
        "LIBRARY kernel32.dll\nEXPORTS\n"
        + "\n".join(
            f"  {name}@{stack_bytes}"
            for name, stack_bytes in names
        )
        + "\n",
        encoding="ascii",
    )

    library = OUT / "kernel32.lib"

    run(
        "llvm-dlltool",
        "-m",
        "i386",
        "--kill-at",
        "-d",
        str(definition),
        "-l",
        str(library),
    )

    return library


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    if not ORIGINAL.is_file():
        raise SystemExit(
            f"Original DLL missing: {ORIGINAL}"
        )

    original_exports = exports(ORIGINAL)

    if len(original_exports) != 291:
        raise SystemExit(
            f"Expected 291 exports, got "
            f"{len(original_exports)}"
        )

    proxy_def = OUT / "SNDDSound3DDLL_VBR.def"

    lines = [
        "LIBRARY SNDDSound3DDLL_VBR.dll",
        "EXPORTS",
    ]

    for ordinal, name in original_exports:
        quoted = '"' + name.replace('"', '\\"') + '"'

        if name == "_SND_fn_hGetSoundEventHandleFromEditorId@4":
            target = "_probe_get_handle@4"

        elif name == "SND_fn_lSendSoundRequest":
            target = "probe_send_request"

        else:
            target = (
                f'"SNDDSound3DDLL_VBR_orig.#{ordinal}"'
            )

        lines.append(
            f"  {quoted}={target} @{ordinal}"
        )

    proxy_def.write_text(
        "\n".join(lines) + "\n",
        encoding="ascii",
    )

    kernel32 = build_import_library()

    obj = OUT / "snd_log_probe_v2.obj"

    run(
        "clang-cl",
        "--target=i686-pc-windows-msvc",
        "/nologo",
        "/c",
        "/O2",
        "/GS-",
        "/GR-",
        "/EHs-c-",
        "/Zl",
        "/utf-8",
        f"/Fo{obj}",
        str(SOURCE),
    )

    proxy = OUT / "SNDDSound3DDLL_VBR.dll"

    run(
        "lld-link",
        "/dll",
        "/nodefaultlib",
        "/machine:x86",
        "/subsystem:windows,5.1",
        "/entry:DllMain@12",
        f"/def:{proxy_def}",
        f"/out:{proxy}",
        str(obj),
        str(kernel32),
    )

    shutil.copy2(
        ORIGINAL,
        OUT / "SNDDSound3DDLL_VBR_orig.dll",
    )

    proxy_exports = exports(proxy)

    if proxy_exports != original_exports:
        raise SystemExit(
            "ERROR: proxy export ABI differs "
            "from original DLL"
        )

    print(f"Built: {proxy}")
    print(
        f"Validated {len(proxy_exports)} "
        "matching exports"
    )
    print(
        "Hooks: editor-id mapping + "
        "SendSoundRequest only"
    )


if __name__ == "__main__":
    main()
