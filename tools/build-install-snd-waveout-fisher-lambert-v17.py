#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import time
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path("/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell")
SYSTEM = GAME / "system"

SRC = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v17.cpp"
MANIFEST = PROJECT / "manifests/fisher-lambert-runtime-v17.csv"
BASEOUT = PROJECT / "build/snd-runtime-manifest-v15-1"
OUT = PROJECT / "build/snd-waveout-fisher-lambert-v17"

def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)

print("===== PRECHECK =====")

required = [
    SRC,
    MANIFEST,
    BASEOUT / "SNDDSound3DDLL_VBR.def",
    BASEOUT / "kernel32.lib",
    BASEOUT / "kernel32-time.lib",
    BASEOUT / "winmm.lib",
    SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
]

for path in required:
    if not path.is_file():
        raise SystemExit(f"ERROR: missing required file: {path}")

with MANIFEST.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 408:
    raise SystemExit(f"ERROR: expected 408 runtime rows, got {len(rows)}")

editor_ids = [row["editor_id_hex"] for row in rows]
uids = [row["id"] for row in rows]

if len(set(editor_ids)) != 408:
    raise SystemExit("ERROR: runtime editor IDs are not unique")

if len(set(uids)) != 408:
    raise SystemExit("ERROR: runtime UIDs are not unique")

source_text = SRC.read_text(encoding="utf-8")

if source_text.count("// u") < 408:
    raise SystemExit("ERROR: V17 source does not contain 408 table rows")

if "resolve_external_audio_apis" not in source_text:
    raise SystemExit("ERROR: dynamic waveOut resolver missing")

if "PlaySoundA(\n                training->path" in source_text:
    raise SystemExit("ERROR: old runtime PlaySoundA invocation remains")

print("PASS: 408/408 runtime rows")
print("PASS: 408 unique editor IDs")
print("PASS: dynamic waveOut source checks")

OUT.mkdir(parents=True, exist_ok=True)

shutil.copy2(
    BASEOUT / "SNDDSound3DDLL_VBR.def",
    OUT / "SNDDSound3DDLL_VBR.def",
)

obj = OUT / "snd_waveout_fisher_lambert_v17.obj"
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
print("===== OBJECT CHECK =====")

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
            "ERROR: V17 unexpectedly statically imports " + forbidden
        )

for forbidden_crt in [
    "__fltused",
    "_memcpy",
    "_memset",
    "_memmove",
    "_malloc",
    "_free",
]:
    if forbidden_crt in nm:
        raise SystemExit(
            "ERROR: unexpected CRT dependency: " + forbidden_crt
        )

print("PASS: waveOut/kernel32 extensions are runtime-resolved")
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
    for block in re.findall(r"Export \{(.*?)\n\}", text, re.S):
        ordinal = re.search(r"Ordinal: (\d+)", block)
        name = re.search(r"Name: (.+)", block)
        if ordinal and name:
            result.append((int(ordinal.group(1)), name.group(1).strip()))
    return result

original_exports = exports(SYSTEM / "SNDDSound3DDLL_VBR_orig.dll")
new_exports = exports(dll)

if len(original_exports) != 291 or new_exports != original_exports:
    raise SystemExit("ERROR: export ABI mismatch")

print("PASS: 291/291 exports match")

print()
print("===== INSTALL V17 =====")

stamp = time.strftime("%Y%m%d-%H%M%S")
backup = PROJECT / "backups" / f"snd-waveout-fisher-lambert-v17-{stamp}"
backup.mkdir(parents=True)

live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

shutil.copy2(
    live,
    backup / "SNDDSound3DDLL_VBR-pre-v17.dll",
)
shutil.copy2(dll, live)

if live.read_bytes() != dll.read_bytes():
    raise SystemExit("ERROR: installed DLL verification failed")

log = SYSTEM / "snd-waveout-fisher-lambert-v17.log"
log.write_bytes(b"")

print("PASS: V17 installed")
print("Backup:", backup)
print("Runtime entries: 408")
print("Log:", log)
