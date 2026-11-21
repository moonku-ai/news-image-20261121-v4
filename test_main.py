"""Tests for news-image-20261121 v4 — "THE FRONT PAGE".

Pure Python stdlib only. Run: python3 -m unittest test_main -v
"""
import ast
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)


def png_chunks(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG signature"
    pos = 8
    chunks = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        crc_stored = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        crc_calc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        chunks.append((ctype.decode("latin1"), length, crc_stored == crc_calc))
        pos += 12 + length
    return chunks


class TestStdlibOnly(unittest.TestCase):
    def test_only_stdlib_imports(self):
        src = open(os.path.join(REPO, "main.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        allowed = {"hashlib", "math", "os", "struct", "sys", "zlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertIn(a.name.split(".")[0], allowed, a.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], allowed, node.module)


class TestRender(unittest.TestCase):
    def test_import_and_render(self):
        import main
        img = main.render()
        self.assertEqual(img.width, 1024)
        self.assertEqual(img.height, 1024)

    def test_png_valid_and_sized(self):
        import main
        data = main.encode_png(main.render())
        self.assertLessEqual(len(data), 1048576, "over 1 MiB")
        chunks = png_chunks(data)
        self.assertTrue(all(ok for _, _, ok in chunks), "bad CRC in a chunk")
        types = [t for t, _, _ in chunks]
        self.assertEqual(types[0], "IHDR")
        self.assertEqual(types[-1], "IEND")
        w, h = struct.unpack(">II", data[16:24])
        self.assertEqual((w, h), (1024, 1024))

    def test_deterministic(self):
        import main
        a = main.encode_png(main.render())
        b = main.encode_png(main.render())
        self.assertEqual(hashlib.sha256(a).hexdigest(),
                         hashlib.sha256(b).hexdigest())

    def test_main_writes_output_dir(self):
        import main
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "entry.png")
            os.environ["MAKEFUN_OUTPUT_DIR"] = d
            try:
                main.main()
            finally:
                del os.environ["MAKEFUN_OUTPUT_DIR"]
            self.assertTrue(os.path.exists(out))
            self.assertLessEqual(os.path.getsize(out), 1048576)
            self.assertEqual(oct(os.stat(out).st_mode & 0o777), "0o644")

    def test_wrap_never_overflows(self):
        import main
        for text, scale, width in [
            ("FBI DATABASE HACKED", 9, 700),
            ("MYANMAR GUILTY OF GENOCIDE", 4, 430),
            ("128 NATIONS AGREE TO DRAFT KILLER-ROBOT RULES", 4, 900),
            ("THE BUREAU INVESTIGATES A BREACH OF ITS NATIONWIDE CRIME DATABASE", 3, 700),
        ]:
            for line in main.wrap_text(text, scale, width):
                self.assertLessEqual(main.text_width(line, scale), width, line)

    def test_all_seven_stories_present(self):
        import main
        blob = " ".join(s["headline"] + " " + s["fact"] for s in main.STORIES)
        for needle in ["FBI DATABASE HACKED", "MYANMAR", "GENOCIDE",
                       "MELTDOWN", "KYIV", "CANCER", "CHAPO ISIDRO",
                       "KILLER-ROBOT", "128 NATIONS"]:
            self.assertIn(needle, blob)
        self.assertEqual(len(main.STORIES), 7)

    def test_date_present(self):
        import main
        self.assertIn("21 NOVEMBER 2026", main.MASTHEAD_DATE)


if __name__ == "__main__":
    unittest.main()
