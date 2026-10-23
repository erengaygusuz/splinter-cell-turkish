#!/usr/bin/env python3
"""Inspect font PCX pixels and the active subtitle draw code without changing game files.

No UCC build, game launch, or installation. Pure Python standard library.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

DEFAULT_PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
DEFAULT_GAME = Path("/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell")
SOURCE_FONTS = (
    "build/font-poc-full/Textures/Font/txt_integration.pcx",
    "build/font-poc-full/Textures/Font/txt_hud.pcx",
    "build/font-poc-full/Textures/Font/txt_mission.pcx",
)
HUD_SOURCE = "build/gameplay-subtitle-hud-poc-fullwork/EchelonHUD/Classes/EchelonMainHUD.uc"

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def decode_pcx(data):
    """Return (width, height, RGB bytes, metrics) from an 8-bit, single-plane PCX."""
    if len(data) < 897 or data[0] != 10 or data[2] != 1 or data[3] != 8:
        raise ValueError("Expected 8-bit RLE PCX, with 256-color palette")
    if data[65] != 1 or data[-769] != 12:
        raise ValueError("Expected one color plane and trailing 256-color palette")
    x0, y0, x1, y1 = struct.unpack_from("<4H", data, 4)
    width, height = x1 - x0 + 1, y1 - y0 + 1
    bytes_per_line = struct.unpack_from("<H", data, 66)[0]
    if not (0 < width <= bytes_per_line <= 8192 and 0 < height <= 8192):
        raise ValueError("Invalid PCX dimensions or stride")
    if width * height > 4194304:
        raise ValueError("Refusing oversized font bitmap")
    stream, offset, row_size = memoryview(data)[128:-769], 0, bytes_per_line
    indices = bytearray()
    for _ in range(height):
        row = bytearray()
        while len(row) < row_size:
            if offset >= len(stream):
                raise ValueError("Truncated PCX RLE stream")
            value = stream[offset]
            offset += 1
            if value & 0xC0 == 0xC0:
                run = value & 0x3F
                if run == 0 or offset >= len(stream):
                    raise ValueError("Invalid PCX RLE run")
                value = stream[offset]
                offset += 1
            else:
                run = 1
            if len(row) + run > row_size:
                raise ValueError("PCX RLE row overflow")
            row.extend(bytes([value]) * run)
        indices.extend(row[:width])
    palette = memoryview(data)[-768:]
    rgb = bytearray()
    counts = Counter(indices)
    for index in indices:
        rgb.extend(palette[index * 3:index * 3 + 3])
    palette_top = [
        {"index": value, "count": count,
         "rgb": list(palette[value * 3:value * 3 + 3])}
        for value, count in counts.most_common(8)
    ]
    return width, height, bytes(rgb), {
        "pcx_size": [width, height],
        "palette_entries_used": len(counts),
        "most_common_palette_indices": palette_top,
        "rle_trailing_bytes": len(stream) - offset
    }

def png_rgb(width, height, rgb):
    """PNG encoding for generated visual previews (no Pillow dependency)."""
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload +
                struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))
    stride = width * 3
    image = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(image, 9)) +
            chunk(b"IEND", b""))

def hud_evidence(path):
    if not path.is_file() or path.is_symlink():
        return {"present": False}
    raw = path.read_bytes()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    names = ("DrawGameplaySubtitle", "Canvas.Font", "Canvas.ETextFont", "TakeGameplaySubtitleLine")
    selected = [
        {"line": i + 1, "text": line.strip()[:240]}
        for i, line in enumerate(lines)
        if any(name in line for name in names)
    ]
    return {"present": True, "sha256": sha256(raw),
            "relevant_lines": selected[:100],
            "truncated": len(selected) > 100}

def produce(project, output):
    report = {"schema": "sc-turkish-font-atlas-audit/1", "fonts": {},
              "hud": hud_evidence(project / HUD_SOURCE)}
    for rel in SOURCE_FONTS:
        file = project / rel
        if not file.is_file() or file.is_symlink():
            report["fonts"][rel] = {"present": False}
            continue
        raw = file.read_bytes()
        entry = {"present": True, "bytes": len(raw), "sha256": sha256(raw)}
        try:
            width, height, rgb, metrics = decode_pcx(raw)
            dest = output / (file.stem + ".png")
            dest.write_bytes(png_rgb(width, height, rgb))
            entry.update(metrics)
            entry["preview"] = str(dest)
        except ValueError as error:
            entry["error"] = str(error)
        report["fonts"][rel] = entry
    (output / "font-detail.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output-dir", type=Path,
                        default=Path.home() / "Downloads" / "sc-font-atlas-audit")
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    for protected in (args.project.resolve(), args.game.resolve()):
        if root == protected or protected in root.parents:
            parser.error("Output must be outside the project and installed game.")
    root.mkdir(parents=True, exist_ok=True)
    result = produce(args.project, root)
    print("Read-only atlas review:", root)
    for file, entry in result["fonts"].items():
        print(Path(file).name, "OK" if "preview" in entry else entry.get("error", "MISSING"))
    print("HUD source:", "FOUND" if result["hud"]["present"] else "MISSING")
    print("Report:", root / "font-detail.json")

if __name__ == "__main__":
    main()
