"""Synthetic decoder tests; never touch installed game assets."""
import struct
import unittest

from atlas_audit import decode_pcx, png_rgb

def pcx_fixture():
    header = bytearray(128)
    header[0] = 10  # PCX
    header[1] = 5
    header[2] = 1  # RLE
    header[3] = 8  # bits/plane
    struct.pack_into("<4H", header, 4, 0, 0, 1, 1)
    header[65] = 1
    struct.pack_into("<H", header, 66, 2)
    palette = bytearray(768)
    palette[3:6] = bytes((255, 0, 0))  # red index 1
    palette[6:9] = bytes((0, 0, 255))  # blue index 2
    return bytes(header) + bytes((1, 2, 2, 1)) + b"\x0c" + bytes(palette)

class AtlasAuditTests(unittest.TestCase):
    def test_decode_pixels_and_palette(self):
        width, height, rgb, meta = decode_pcx(pcx_fixture())
        self.assertEqual((width, height), (2, 2))
        self.assertEqual(rgb, bytes((255, 0, 0, 0, 0, 255,
                                     0, 0, 255, 255, 0, 0)))
        self.assertEqual(meta["palette_entries_used"], 2)

    def test_png_format(self):
        width, height, rgb, _ = decode_pcx(pcx_fixture())
        png = png_rgb(width, height, rgb)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II", png[16:24]), (2, 2))

    def test_reject_unsupported_pcx(self):
        bad = bytearray(pcx_fixture())
        bad[65] = 3
        with self.assertRaises(ValueError):
            decode_pcx(bytes(bad))

    def test_reject_truncated_rle(self):
        bad = pcx_fixture()[:128] + b"\xC4\x01" + pcx_fixture()[-769:]
        with self.assertRaises(ValueError):
            decode_pcx(bad)

if __name__ == "__main__":
    unittest.main()
