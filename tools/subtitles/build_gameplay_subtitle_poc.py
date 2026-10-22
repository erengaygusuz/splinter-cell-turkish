#!/usr/bin/env python3
"""Build and validate the 32-bit SND proxy used by the gameplay subtitle POC."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gameplay-subtitle-poc/src/gameplay_subtitle_poc.cpp"
LOAD_TEST_SOURCE = ROOT / "gameplay-subtitle-poc/src/proxy_load_test.cpp"
ORIGINAL = ROOT / "build/font-poc-clean/System/SNDDSound3DDLL_VBR.dll"
OUT = ROOT / "build/gameplay-subtitle-poc"


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def exports(path: Path) -> list[tuple[int, str]]:
    text = run("llvm-readobj", "--coff-exports", str(path))
    blocks = re.findall(r"Export \{(.*?)\n\}", text, flags=re.S)
    found: list[tuple[int, str]] = []
    for block in blocks:
        ordinal = re.search(r"Ordinal: (\d+)", block)
        name = re.search(r"Name: (.+)", block)
        if ordinal and name:
            found.append((int(ordinal.group(1)), name.group(1).strip()))
    return found


def write_import_library(dll: str, names: list[tuple[str, int]]) -> Path:
    definition = OUT / f"{dll}.def"
    definition.write_text(
        "LIBRARY " + dll + ".dll\nEXPORTS\n" +
        "\n".join(f"  {name}@{stack_bytes}" for name, stack_bytes in names) + "\n",
        encoding="ascii",
    )
    library = OUT / f"{dll}.lib"
    run(
        "llvm-dlltool", "-m", "i386", "--kill-at", "-d", str(definition),
        "-l", str(library),
    )
    return library


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    original_exports = exports(ORIGINAL)
    if len(original_exports) != 291:
        raise SystemExit(f"Expected 291 original exports, found {len(original_exports)}")

    proxy_def = OUT / "SNDDSound3DDLL_VBR.def"
    lines = ["LIBRARY SNDDSound3DDLL_VBR.dll", "EXPORTS"]
    for ordinal, name in original_exports:
        quoted_name = '"' + name.replace('"', '\\"') + '"'
        if name == "_SND_fn_hGetSoundEventHandleFromEditorId@4":
            target = "_poc_get_handle@4"
        elif name == "SND_fn_lSendSoundRequest":
            target = "poc_send_request"
        elif name == "SND_fn_lSendSoundRequestOnChannel":
            target = "poc_send_on_channel"
        elif name == "SND_fn_lSendSoundRequestOnChannelWithFadeIn":
            target = "poc_send_on_channel_fade"
        elif name == "SND_fn_lSendSoundRequestWithFadeIn":
            target = "poc_send_with_fade"
        else:
            target = f'"SNDDSound3DDLL_VBR_orig.#{ordinal}"'
        lines.append(f"  {quoted_name}={target} @{ordinal}")
    proxy_def.write_text("\n".join(lines) + "\n", encoding="ascii")

    kernel32 = write_import_library("kernel32", [
        ("LoadLibraryA", 4), ("GetModuleHandleW", 4), ("GetProcAddress", 8),
        ("DisableThreadLibraryCalls", 4), ("CreateThread", 24),
        ("GetTickCount", 0), ("Sleep", 4), ("GetCurrentProcessId", 0),
        ("CreateFileA", 28), ("WriteFile", 20), ("SetFilePointer", 16),
        ("CloseHandle", 4),
        ("FreeLibrary", 4), ("ExitProcess", 4),
    ])
    user32 = write_import_library("user32", [
        ("RegisterClassW", 4), ("CreateWindowExW", 48),
        ("DefWindowProcW", 16), ("GetMessageW", 16),
        ("TranslateMessage", 4), ("DispatchMessageW", 4),
        ("FindWindowW", 8), ("GetForegroundWindow", 0),
        ("GetWindowThreadProcessId", 8), ("GetWindowRect", 8),
        ("GetClientRect", 8), ("SetWindowPos", 28), ("ShowWindow", 8),
        ("SetLayeredWindowAttributes", 16), ("SetTimer", 16),
        ("InvalidateRect", 12), ("BeginPaint", 8), ("EndPaint", 8),
        ("FillRect", 12), ("DrawTextW", 20), ("SetBkMode", 8),
        ("SetTextColor", 8), ("PostMessageW", 16), ("GetDC", 4),
        ("ReleaseDC", 8),
    ])
    gdi32 = write_import_library("gdi32", [
        ("CreateSolidBrush", 4), ("CreateFontW", 56),
        ("SelectObject", 8), ("DeleteObject", 4),
    ])

    obj = OUT / "gameplay_subtitle_poc.obj"
    run(
        "clang-cl", "--target=i686-pc-windows-msvc", "/nologo", "/c",
        "/O2", "/GS-", "/GR-", "/EHs-c-", "/Zl", "/utf-8",
        f"/Fo{obj}", str(SOURCE),
    )
    proxy = OUT / "SNDDSound3DDLL_VBR.dll"
    run(
        "lld-link", "/dll", "/nodefaultlib", "/machine:x86",
        "/subsystem:windows,5.1", "/entry:DllMain@12",
        f"/def:{proxy_def}", f"/out:{proxy}", str(obj),
        str(kernel32), str(user32), str(gdi32),
    )
    shutil.copy2(ORIGINAL, OUT / "SNDDSound3DDLL_VBR_orig.dll")
    shutil.copy2(proxy, OUT / "SNDDSound3DDLL_VBR_poc.dll")

    load_test_obj = OUT / "proxy_load_test.obj"
    run(
        "clang-cl", "--target=i686-pc-windows-msvc", "/nologo", "/c",
        "/O2", "/GS-", "/GR-", "/EHs-c-", "/Zl",
        f"/Fo{load_test_obj}", str(LOAD_TEST_SOURCE),
    )
    load_test_exe = OUT / "proxy_load_test.exe"
    run(
        "lld-link", "/nodefaultlib", "/machine:x86",
        "/subsystem:console,5.1", "/entry:start",
        f"/out:{load_test_exe}", str(load_test_obj), str(kernel32),
    )

    proxy_exports = exports(proxy)
    original_signature = [(ordinal, name) for ordinal, name in original_exports]
    proxy_signature = [(ordinal, name) for ordinal, name in proxy_exports]
    if proxy_signature != original_signature:
        raise SystemExit("Proxy export names or ordinals differ from the original DLL")

    print(f"Built: {proxy}")
    print(f"Load test: {load_test_exe}")
    print(f"Validated {len(proxy_exports)} matching exports")
    print("Intercepted 5 Lambert/Fisher opening lines (0x003C0000-0x003C0004)")


if __name__ == "__main__":
    main()
