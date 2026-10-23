"""Unit tests for the read-only Turkish font probe (standard library)."""
import tempfile
import unittest
from pathlib import Path
from probe import codepages, font_pcx, inspect

class TurkishFontProbeTests(unittest.TestCase):
    def test_character_matrix(self):
        rows = codepages()
        self.assertEqual(len(rows), 12)
        self.assertEqual("".join(x["char"] for x in rows if x["mismatch"]), "ĞİŞğış")
        self.assertEqual("".join(x["cp1252_interpretation"] for x in rows if x["mismatch"]), "ÐÝÞðýþ")
        self.assertEqual("".join(x["cp1254_hex"] for x in rows), "C7D0DDD6DEDCE7F0FDF6FEFC")

    def test_missing_local_files_are_not_marked_successful(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = inspect(root / "missing-project", root / "missing-game")
            self.assertFalse(report["game_available"])
            self.assertFalse(report["project_available"])
            self.assertFalse(report["packages"]["system/Engine.u"]["present"])

    def test_absent_pcx_not_marked_present(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(font_pcx(Path(folder) / "absent.pcx"), {"present": False})

if __name__ == "__main__":
    unittest.main()
