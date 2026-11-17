#!/usr/bin/env python3
"""Tests for the Explorer page (P13): router.js and model.js (pure), and explorer.html in jsdom.

    python scripts/test_explorer.py

Needs Node 18+. The page tests also need jsdom, installed once and kept out of git:
    npm install --prefix scripts/explorer_tests jsdom
Without jsdom those tests are skipped, the pure tests still run."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent / "explorer_tests"
NODE = shutil.which("node")


def run(script: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    return subprocess.run([NODE, str(HERE / script)], capture_output=True, text=True, timeout=120, env=env)


@unittest.skipUnless(NODE, "node is not on PATH")
class ExplorerTests(unittest.TestCase):
    def test_router_and_model(self):
        r = run("pure.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_page(self):
        r = run("page.mjs")
        if r.returncode == 77:
            self.skipTest("jsdom is not installed: npm install --prefix scripts/explorer_tests jsdom")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
