#!/usr/bin/env python3
"""
Tests for scripts/refresh_atlas.py. Standard library only.

    python scripts/test_refresh_atlas.py
    python -m unittest discover -s scripts

The first test checks the repo itself: the committed pages must match the
committed data/census.json. If you replaced the census and it fails, run
`python scripts/refresh_atlas.py`. The rest work on a temporary copy of the
pages with a modified census, to pin down behaviour that must not regress:
refreshing is idempotent, --check notices stale pages, and the parts of the
Atlas that come from Graphify (not the census) are preserved.
"""
import copy
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("refresh_atlas", ROOT / "scripts" / "refresh_atlas.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)

FILES = [f"{name}.html" for name in ra.PAGES] + ["data/census.json", "data/summary.md"]


def read(p):
    return Path(p).read_text(encoding="utf-8")


class RepoState(unittest.TestCase):
    def test_committed_pages_match_the_committed_census(self):
        census = json.loads(read(ROOT / "data" / "census.json"))
        stale = sorted(p.name for p in ra.refresh_all(ROOT, census))
        self.assertEqual([], stale, "pages are out of date with data/census.json; run: python scripts/refresh_atlas.py")


class OnACopy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        for rel in FILES:
            shutil.copy(ROOT / rel, self.tmp / rel)
        self.census = json.loads(read(self.tmp / "data" / "census.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def save_census(self):
        (self.tmp / "data" / "census.json").write_text(json.dumps(self.census, separators=(",", ":")), encoding="utf-8")

    def refresh(self):
        changes = ra.refresh_all(self.tmp, self.census)
        for p, text in changes.items():
            p.write_bytes(text.encode("utf-8"))
        return changes

    def newer_census(self):
        """A census that differs from the committed one: a later snapshot with one more commit."""
        self.census["meta"]["generated"] = "2099-01-02T03:04:05"
        self.census["git"]["head"] = "abc1234"
        self.census["git"]["commits"].insert(0, {"hash": "abc12345", "author": "x", "date": "2099-01-02", "subject": "later commit",
                                                 "files": 1, "added": 5, "deleted": 2})
        self.save_census()

    # ----------------------------------------------------------------- behaviour
    def test_refresh_is_idempotent(self):
        self.newer_census()
        first = self.refresh()
        self.assertTrue(first, "a newer census should change the pages")
        self.assertEqual({}, self.refresh(), "a second refresh must change nothing")

    def test_check_mode_notices_stale_pages_and_passes_once_refreshed(self):
        self.newer_census()
        self.assertEqual(1, ra.main(["--root", str(self.tmp), "--check"]))
        self.assertEqual(0, ra.main(["--root", str(self.tmp)]))
        self.assertEqual(0, ra.main(["--root", str(self.tmp), "--check"]))

    def test_snapshot_label_and_counts_follow_the_census(self):
        self.newer_census()
        self.refresh()
        index = read(self.tmp / "index.html")
        self.assertIn("Built 2099-01-02 from commit abc1234.", index)
        self.assertIn(f'<div class="k">{ra.fmt(len(self.census["git"]["commits"]))}</div><div class="l">commits</div>', index)
        self.assertIn("2099-01-02", read(self.tmp / "history.html"))

    def test_graphify_derived_content_is_preserved(self):
        before = {n: read(self.tmp / f"{n}.html") for n in ("index", "api", "explore")}
        self.newer_census()
        self.refresh()
        index = read(self.tmp / "index.html")
        for label in ("graph nodes", "graph links", "guides"):
            pat = r'<div class="k">([^<]*)</div><div class="l">' + label + "</div>"
            self.assertEqual(re.search(pat, before["index"]).group(1), re.search(pat, index).group(1), label)
        a, b = ra.find_card(before["index"], "Graph hubs"), ra.find_card(index, "Graph hubs")
        self.assertEqual(before["index"][a[0]:a[1]], index[b[0]:b[1]], "Graph hubs card must be untouched")
        a, b = ra.find_card(before["api"], "Frontend files that call"), ra.find_card(read(self.tmp / "api.html"), "Frontend files that call")
        self.assertEqual(before["api"][a[0]:a[1]], read(self.tmp / "api.html")[b[0]:b[1]])
        self.assertEqual(ra.read_literal(before["explore"], ",DC="), ra.read_literal(read(self.tmp / "explore.html"), ",DC="), "doc sections must be untouched")

    def test_new_route_has_blank_callers_and_existing_callers_are_kept(self):
        old_rows = ra.read_literal(read(self.tmp / "api.html"), "ROWS=")
        old_callers = {(r[0], r[1]): r[7] for r in old_rows}
        r0 = copy.deepcopy(self.census["routes"][0])
        r0.update(path="/api/brand-new-route", handler="brand_new")
        self.census["routes"].append(r0)
        self.save_census()
        self.refresh()
        rows = ra.read_literal(read(self.tmp / "api.html"), "ROWS=")
        new = [r for r in rows if r[1] == "/api/brand-new-route"]
        self.assertEqual(1, len(new))
        self.assertEqual("", new[0][7], "no Graphify data for a new route: blank, not a made-up number")
        for r in rows:
            if (r[0], r[1]) in old_callers:
                self.assertEqual(old_callers[(r[0], r[1])], r[7])

    def test_explore_edges_follow_their_files_when_indexes_shift(self):
        def path_edges(html):
            F, EG = ra.read_literal(html, "const F="), ra.read_literal(html, ",EG=")
            return {(F[int(k)][0], F[t][0], w) for k, v in EG.items() for t, w in v["o"]}
        before = path_edges(read(self.tmp / "explore.html"))
        template = next(f for f in self.census["files"] if f["path"].endswith(".py") and not f.get("binary"))
        new_file = copy.deepcopy(template)
        new_file["path"] = ".0000_brand_new_file.py"   # sorts before ".dockerignore", so every other file's index shifts by one
        self.census["files"].append(new_file)
        self.save_census()
        self.refresh()
        html = read(self.tmp / "explore.html")
        F = ra.read_literal(html, "const F=")
        self.assertEqual(".0000_brand_new_file.py", F[0][0])
        self.assertEqual(before, path_edges(html), "every edge must still connect the same two files")

    def test_crlf_pages_are_not_seen_as_stale_and_stay_crlf(self):
        """A Windows checkout (core.autocrlf) has CRLF files. In-sync pages must not look changed, and
        pages that do change must keep CRLF rather than silently becoming LF."""
        for rel in ("code.html", "infra.html"):
            p = self.tmp / rel
            p.write_bytes(read(p).replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual({}, ra.refresh_all(self.tmp, self.census), "CRLF alone must not count as out of date")
        self.newer_census()
        changes = ra.refresh_all(self.tmp, self.census)
        for rel in ("code.html", "infra.html"):
            raw = changes[self.tmp / rel].encode("utf-8")
            self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"), f"{rel}: a bare LF was introduced")

    def test_summary_keeps_windows_line_endings(self):
        sp = self.tmp / "data" / "summary.md"
        sp.write_bytes(read(sp).replace("\n", "\r\n").encode("utf-8"))
        self.newer_census()
        self.refresh()
        raw = sp.read_bytes()
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"), "no bare LF may be introduced")
        self.assertIn(b"commit abc1234.", raw)


class CensusValidation(unittest.TestCase):
    def test_the_repo_census_is_trustworthy(self):
        c = json.loads(read(ROOT / "data" / "census.json"))
        self.assertEqual([], [p for p in ra.census_problems(c) if "uncommitted" not in p])

    def test_a_degraded_census_is_flagged(self):
        bad = {"meta": {"js_parser": "heuristic-fallback"}, "docker_compose": [{"name": "backend_data"}],
               "ci": {"x.yml": {"jobs": [{"id": "test"}]}}, "git": {"dirty_files": 3}}
        problems = ra.census_problems(bad)
        self.assertEqual(3, len(problems))
        self.assertTrue(any("tree-sitter" in p for p in problems))
        self.assertTrue(any("pyyaml" in p for p in problems))
        self.assertTrue(any("uncommitted" in p for p in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
