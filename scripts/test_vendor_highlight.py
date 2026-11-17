#!/usr/bin/env python3
"""Tests for scripts/vendor_highlight.py (patch P14b). Run: python scripts/test_vendor_highlight.py

Offline: the pin table, the hash helpers, the tarball reader on a synthetic tarball, and (when assets/vendor/highlight/ is
present) the vendored copy against its pins. Standard library only."""
from __future__ import annotations

import hashlib
import io
import sys
import tarfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vendor_highlight as V  # noqa: E402


def make_tgz(skip=None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for member in list(V.wanted().values()) + [V.LICENSE_SRC]:
            if member == skip:
                continue
            data = f"// {member}\r\n".encode()
            info = tarfile.TarInfo(member)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class VendorHighlightTests(unittest.TestCase):
    def test_every_wanted_file_has_a_pin(self):
        self.assertEqual(set(V.wanted()), set(V.PINS))
        for rel, pin in V.PINS.items():
            self.assertRegex(pin, r"^[0-9a-f]{64}$", rel)

    def test_languages_cover_what_the_explorer_asks_for(self):
        # highlight.js (assets/js/explorer/highlight.js) maps files to these grammars, and JSX / Markdown pull in xml
        want = {"python", "javascript", "typescript", "json", "sql", "yaml", "bash", "css", "xml", "ini", "dockerfile", "powershell", "markdown"}
        self.assertEqual(set(V.LANGUAGES), want)

    def test_hashes_ignore_line_endings(self):
        self.assertEqual(V.sha256_lf(b"a\r\nb\r\n"), hashlib.sha256(b"a\nb\n").hexdigest())
        self.assertTrue(V.npm_integrity(b"x").startswith("sha512-"))

    def test_read_members_finds_every_file_and_the_licence(self):
        got = V.read_members(make_tgz())
        self.assertEqual(set(got), set(V.wanted()) | {"LICENSE"})

    def test_a_tarball_without_a_grammar_is_refused(self):
        with self.assertRaises(SystemExit):
            V.read_members(make_tgz(skip="package/es/languages/python.min.js"))

    def test_tarball_pin_is_an_npm_integrity_string(self):
        self.assertRegex(V.TARBALL_INTEGRITY, r"^sha512-[A-Za-z0-9+/]+=*$")

    @unittest.skipUnless((V.DEST / "core.min.js").is_file(), "assets/vendor/highlight is not present")
    def test_vendored_copy_matches_its_pins(self):
        self.assertEqual(V.check(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
