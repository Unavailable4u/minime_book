#!/usr/bin/env python3
"""Tests for api/todo.js after P16: the "audit" record kind is accepted, nothing else new is, and the id the Explorer makes fits the id rule.

    python scripts/test_todo_api.py

Needs Node 18+ (skipped without it). No network: the Upstash database is replaced by a fake."""
from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent / "todo_api_tests"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node is not on PATH")
class TodoApiTests(unittest.TestCase):
    def test_audit_kind(self):
        r = subprocess.run([NODE, str(HERE / "todo_api.mjs")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env={**os.environ, "NODE_NO_WARNINGS": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
