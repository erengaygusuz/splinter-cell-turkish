#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path("/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell")
SYSTEM = GAME / "system"

SRC = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_training_v16.cpp"
BASEOUT = PROJECT / "build/snd-runtime-manifest-v15-1"
OUT = PROJECT / "build/snd-waveout-training-v16"

def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)

print("===== PRECHECK =====")

required = [
    SRC,
    BASEOUT / "SNDDSound3DDLL_VBR.def",
    BASEOUT / "kernel32.lib",
    BASEOUT / "kernel32-time.lib",
    BASEOUT / "winmm.lib",
    SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
]

for path in required:
    if not path.exists():
        raise SystemExit(f"ERROR: missing required file: {path}")

source_text = SRC.read_text(encoding="utf-8")
training_rows = re.findall(r"// u(?:0000(?:1[3-9]|2[0-9]))\s*$", source_text, re.M)

if len(training_rows) != 17:
    raise SystemExit(
        f"ERROR: expected 17 Training entries, got {len(training_rows)}"
    )

if "resolve_external_audio_apis" not in source_text:
    raise SystemExit("ERROR: dynamic API resolver missing")

if "PlaySoundA(\n                training->path" in source_text:
    raise SystemExit("ERROR: runtime PlaySoundA call still present")

print("PASS: V16 source checks")
print("PASS: 17/17 Training entries")

OUT.mkdir(parents=True, exist_ok=True)

shutil.copy2(
    BASEOUT / "SNDDSound3DDLL_VBR.def",
    OUT / "SNDDSound3DDLL_VBR.def",
)

obj = OUT / "snd_waveout_training_v16.obj"
dll = OUT / "SNDDSound3DDLL_VBR.dll"

for path in [
    obj,
    dll,
    OUT / "SNDDSound3DDLL_VBR.lib",
    OUT / "SNDDSound3DDLL_VBR.exp",
]:
    try:
        path.unlink()
    except FileNotFoundError:
        pass

print()
print("===== COMPILE =====")

run([
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
    str(SRC),
])

print("PASS: compile")

print()
print("===== OBJECT IMPORT CHECK =====")

nm = subprocess.check_output(
    ["llvm-nm", str(obj)],
    text=True,
)

for forbidden in [
    "_waveOutOpen@",
    "_waveOutPrepareHeader@",
    "_waveOutWrite@",
    "_waveOutReset@",
    "_waveOutUnprepareHeader@",
    "_waveOutClose@",
    "_ReadFile@",
    "_GetFileSize@",
    "_VirtualAlloc@",
    "_VirtualFree@",
]:
    if forbidden in nm:
        raise SystemExit(
            "ERROR: V16 unexpectedly statically imports "
            + forbidden
        )

undefined_symbols = {
    parts[-1]
    for line in nm.splitlines()
    if (parts := line.split())
    and "U" in parts[:-1]
}

for forbidden_crt in {
    "__fltused",
    "_memcpy",
    "_memset",
    "_memmove",
    "_malloc",
    "_free",
}:
    if forbidden_crt in undefined_symbols:
        raise SystemExit(
            "ERROR: unexpected CRT dependency: "
            + forbidden_crt
        )

print("PASS: new waveOut/kernel32 APIs are runtime-resolved")
print("PASS: no forbidden CRT dependency")

print()
print("===== LINK =====")

run([
    "lld-link",
    "/dll",
    "/nodefaultlib",
    "/machine:x86",
    "/subsystem:windows,5.1",
    "/entry:DllMain@12",
    f"/def:{OUT / 'SNDDSound3DDLL_VBR.def'}",
    f"/out:{dll}",
    str(obj),
    str(BASEOUT / "kernel32.lib"),
    str(BASEOUT / "kernel32-time.lib"),
    str(BASEOUT / "winmm.lib"),
])

print("PASS: link")

print()
print("===== VERIFY EXPORT ABI =====")

def exports(path: Path):
    text = subprocess.check_output(
        ["llvm-readobj", "--coff-exports", str(path)],
        text=True,
    )
    result = []
    for block in re.findall(r"Export \\{(.*?)\\n\\}", text, re.S):
        ordinal = re.search(r"Ordinal: (\\d+)", block)
        name = re.search(r"Name: (.+)", block)
        if ordinal and name:
            result.append(
                (int(ordinal.group(1)), name.group(1).strip())
            )
    return result

original_exports = exports(
    SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
)
v16_exports = exports(dll)

if len(original_exports) != 291 or v16_exports != original_exports:
    raise SystemExit("ERROR: export ABI mismatch")

print("PASS: 291/291 exports match")

print()
print("===== INSTALL V16 =====")

stamp = time.strftime("%Y%m%d-%H%M%S")
backup = (
    PROJECT /
    "backups" /
    f"snd-waveout-training-v16-{stamp}"
)
backup.mkdir(parents=True)

live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

shutil.copy2(
    live,
    backup / "SNDDSound3DDLL_VBR-pre-v16.dll",
)
shutil.copy2(dll, live)

if live.read_bytes() != dll.read_bytes():
    raise SystemExit("ERROR: installed DLL verification failed")

log = SYSTEM / "snd-waveout-training-v16.log"
log.write_bytes(b"")

print("PASS: V16 installed")
print("Backup:", backup)
print()
print("Test the Lambert/Fisher Training conversation.")
print("Log:", log)
