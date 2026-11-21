#!/usr/bin/env python3
"""
Tests for scripts/retire_legacy.py. Standard library only.

    python scripts/test_retire_legacy.py

Every test builds a tiny site in a temporary folder; the last class runs the checker on the committed repo.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True      # scripts/__pycache__ is tracked; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("retire_legacy", ROOT / "scripts" / "retire_legacy.py")
rl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rl)

BIG = "<!doctype html>\n<html><body>\n" + ("x" * 5000) + "\n</body></html>\n"


def w(root, rel, text, crlf=False):
    p = Path(root, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def wj(root, rel, data, crlf=False):
    w(root, rel, json.dumps(data, indent=2) + "\n", crlf)


def site(root, statuses, crlf=False):
    pages = [{"file": f"architecture/{v}.html", "title": f"Title {v}", "view": v} for v in statuses]
    wj(root, rl.REGISTRY, {"version": 1, "pages": pages, "retired": []}, crlf)
    wj(root, rl.MODEL, {"views": [{"id": v, "status": s} for v, s in statuses.items()]}, crlf)
    for v in statuses:
        w(root, f"architecture/{v}.html", BIG, crlf)
    wj(root, "content/topology.json", {"nodes": [{"id": "n", "diagram": "architecture/system.html"}, {"id": "m", "diagram": "architecture/task-pipeline.html"}]}, crlf)
    wj(root, "content/figures/doc.json", {"figures": [
        {"id": "f1", "type": "archify", "src": "architecture/system.html", "size": "1x", "after": "a", "caption": "c", "alt": "al"},
        {"id": "f2", "type": "archify", "src": "architecture/task-pipeline.html", "after": "b"}]}, crlf)


class Retire(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def test_only_ready_pages_are_retired(self):
        site(self.root, {"system": "derived", "task-pipeline": "missing"})
        done, _ = rl.retire(self.root)
        self.assertEqual([e["view"] for e in done], ["system"])
        reg = json.loads((self.root / rl.REGISTRY).read_text())
        self.assertEqual([e["view"] for e in reg["pages"]], ["task-pipeline"])
        self.assertEqual([e["view"] for e in reg["retired"]], ["system"])
        self.assertGreater((self.root / "architecture/task-pipeline.html").stat().st_size, 4000)

    def test_redirect_page_is_thin_and_self_contained(self):
        site(self.root, {"system": "derived"})
        rl.retire(self.root)
        t = (self.root / "architecture/system.html").read_text()
        self.assertLess(len(t.encode()), rl.PAGE_MAX_BYTES)
        self.assertIn("../architecture.html#system", t)
        self.assertIn("http-equiv=\"refresh\"", t)
        self.assertIn("noindex", t)
        self.assertNotIn("<script src", t)
        self.assertNotIn("<link rel=\"stylesheet\"", t)
        self.assertIn("Title system · MiniMe Atlas", t)

    def test_figures_swapped_and_links_retargeted(self):
        site(self.root, {"system": "derived", "task-pipeline": "missing"})
        rl.retire(self.root)
        figs = json.loads((self.root / "content/figures/doc.json").read_text())["figures"]
        self.assertEqual(figs[0], {"id": "f1", "type": "arch", "view": "system", "after": "a", "caption": "c", "alt": "al"})
        self.assertEqual(figs[1]["type"], "archify")             # not ready: untouched
        nodes = json.loads((self.root / "content/topology.json").read_text())["nodes"]
        self.assertEqual(nodes[0]["diagram"], "architecture.html#system")
        self.assertEqual(nodes[1]["diagram"], "architecture/task-pipeline.html")

    def test_idempotent(self):
        site(self.root, {"system": "derived"})
        rl.retire(self.root)
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        done, touched = rl.retire(self.root)
        self.assertEqual((done, touched), ([], []))
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_dry_run_changes_nothing(self):
        site(self.root, {"system": "derived"})
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        done, touched = rl.retire(self.root, dry=True)
        self.assertEqual(len(done), 1)
        self.assertIn("architecture/system.html", touched)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_crlf_checkout_stays_crlf(self):
        site(self.root, {"system": "derived"}, crlf=True)
        rl.retire(self.root)
        for rel in ("architecture/system.html", rl.REGISTRY, "content/topology.json", "content/figures/doc.json"):
            raw = (self.root / rel).read_bytes()
            self.assertIn(b"\r\n", raw, rel)
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), rel)

    def test_a_written_flow_makes_a_page_ready(self):
        site(self.root, {"task-pipeline": "missing"})
        self.assertEqual(rl.retire(self.root, dry=True)[0], [])
        wj(self.root, rl.MODEL, {"views": [{"id": "task-pipeline", "status": "fresh"}]})
        self.assertEqual([e["view"] for e in rl.retire(self.root)[0]], ["task-pipeline"])

    def test_unknown_view_is_never_ready(self):
        site(self.root, {"system": "derived"})
        wj(self.root, rl.MODEL, {"views": []})
        self.assertEqual(rl.retire(self.root)[0], [])


class Cli(unittest.TestCase):
    def run_cli(self, root, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rl.main(["--root", str(root), *argv])
        return code, out.getvalue()

    def test_check_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            site(d, {"system": "derived", "task-pipeline": "missing"})
            code, out = self.run_cli(d, "--check")
            self.assertEqual(code, 1)
            self.assertIn("architecture/system.html", out)
            rl.retire(d)
            self.assertEqual(self.run_cli(d, "--check")[0], 0)

    def test_status_lists_every_page(self):
        with tempfile.TemporaryDirectory() as d:
            site(d, {"system": "derived", "task-pipeline": "missing"})
            rl.retire(d)
            code, out = self.run_cli(d, "status")
            self.assertEqual(code, 0)
            self.assertIn("retired", out)
            self.assertIn("waiting for its flow", out)


class Repo(unittest.TestCase):
    def test_the_committed_site_has_nothing_ready_and_unretired(self):
        self.assertEqual(rl.main(["--check"]), 0)

    def test_every_registry_page_is_a_real_file_and_every_retired_one_is_thin(self):
        reg = json.loads((ROOT / rl.REGISTRY).read_text(encoding="utf-8"))
        for e in reg["pages"]:
            self.assertGreater((ROOT / e["file"]).stat().st_size, 100_000, e["file"])
        for e in reg["retired"]:
            self.assertLess((ROOT / e["file"]).stat().st_size, rl.PAGE_MAX_BYTES, e["file"])
            self.assertIn(f"architecture.html#{e['view']}", (ROOT / e["file"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
