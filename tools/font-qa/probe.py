#!/usr/bin/env python3
"""Read-only Turkish font/encoding inventory for Splinter Cell (2002).

No game writes, no UCC compilation, no DLL injection, no game launch.
Run with python3 tools/font-qa/probe.py --output "$HOME/Downloads/sc-font-audit.json"
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

CHARS = "ÇĞİÖŞÜçğıöşü"
PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path("/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell")
PACKAGES = (
    "system/Engine.u",
    "system/EchelonMenus.u",
    "system/Enhanced/EchelonMenus.u",
    "system/EchelonHUD.u",
    "system/Enhanced/EchelonHUD.u",
)
LOCALIZATIONS = (
    "system/LOCALIZATION/HUD.int",
    "system/Enhanced/LOCALIZATION/HUD.int",
    "system/Enhanced/LOCALIZATION/Enhanced.int",
    "system/Enhanced/LOCALIZATION/P_0_0_2_Training.int",
)
FONTS = (
    "build/font-poc-full/Textures/Font/txt_integration.pcx",
    "build/font-poc-full/Textures/Font/txt_hud.pcx",
    "build/font-poc-full/Textures/Font/txt_mission.pcx",
)
HUD_SOURCES = (
    "build/gameplay-subtitle-hud-poc-fullwork/EchelonHUD/Classes/EchelonMainHUD.uc",
    "build/gameplay-subtitle-hud-poc-fullwork/EchelonHUD/Classes/EGameplaySubtitleTracker.uc",
    "subtitles/hud/EGameplaySubtitleTracker.uc",
)

def metadata(path):
    if not path.is_file() or path.is_symlink():
        return {"present": False}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return {"present": True, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}

def codepages():
    return [
        {"char": c, "unicode": "U+%04X" % ord(c),
         "cp1254_hex": c.encode("cp1254").hex().upper(),
         "cp1252_interpretation": c.encode("cp1254").decode("cp1252"),
         "mismatch": c.encode("cp1254").decode("cp1252") != c}
        for c in CHARS
    ]

def font_pcx(path):
    entry = metadata(path)
    if not entry["present"]:
        return entry
    with path.open("rb") as stream:
        header = stream.read(128)
    if len(header) < 128:
        entry["error"] = "Truncated PCX header"
    else:
        x0, y0, x1, y1 = struct.unpack_from("<HHHH", header, 4)
        entry["pcx"] = {
            "magic": header[0], "version": header[1],
            "encoding": header[2], "bits_per_plane": header[3],
            "planes": header[65], "width": x1 - x0 + 1,
            "height": y1 - y0 + 1}
    return entry

def localizations(game):
    result = {}
    for rel in LOCALIZATIONS:
        path = game / rel
        entry = metadata(path)
        if entry["present"]:
            with path.open("rb") as stream:
                data = stream.read()
            entry["bom_utf8"] = data.startswith(b"\xef\xbb\xbf")
            entry["bom_utf16le"] = data.startswith(b"\xff\xfe")
            entry["distinct_cp1254_byte_counts"] = {
                "%02X" % byte: data.count(byte)
                for byte in (0xD0, 0xDD, 0xDE, 0xF0, 0xFD, 0xFE)}
        result[rel] = entry
    return result

def package_info(path):
    entry = metadata(path)
    if not entry["present"]:
        return entry
    markers = ("ETextFont", "LocalizedTrueType", "EGameplaySubtitleTracker", "EHUDFont")
    found = {marker: False for marker in markers}
    with path.open("rb") as stream:
        previous = b""
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            joined = previous + chunk
            for marker in markers:
                if marker.encode("ascii") in joined:
                    found[marker] = True
            previous = joined[-64:]
    entry["ascii_marker_hits"] = found
    return entry

def inspect(project, game):
    mapping = codepages()
    return {
        "schema": "sc-turkish-font-readonly-probe/1",
        "project_available": project.is_dir(),
        "game_available": game.is_dir(),
        "mapping": mapping,
        "mapping_differences": "".join(row["char"] for row in mapping if row["mismatch"]),
        "packages": {rel: package_info(game / rel) for rel in PACKAGES},
        "localization": localizations(game),
        "font_pcx": {rel: font_pcx(project / rel) for rel in FONTS},
        "hud_sources": {rel: metadata(project / rel) for rel in HUD_SOURCES},
        "ucc": metadata(project / "build/font-poc-full/System/UCC.exe"),
        "limits": [
            "No assertion about the game's actual selected codepage.",
            "Package name hits do not prove a functional glyph table.",
            "A sandbox UCC build and visual gameplay test are still required."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--game", type=Path, default=GAME)
    parser.add_argument("--output", type=Path, help="JSON output outside the project and game")
    args = parser.parse_args(argv)
    if args.output:
        destination = args.output.expanduser().resolve()
        for protected in (args.project.resolve(), args.game.resolve()):
            if destination == protected or protected in destination.parents:
                parser.error("Output may not be inside game or project.")
    data = json.dumps(inspect(args.project, args.game), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
        args.output.expanduser().write_text(data, encoding="utf-8")
        print("Report: %s" % args.output)
    else:
        sys.stdout.write(data)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
