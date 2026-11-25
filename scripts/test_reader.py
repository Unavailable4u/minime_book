#!/usr/bin/env python3
"""Tests for the chapter reader layer (patch P04). Run: python scripts/test_reader.py

Covers assets/js/reader.js (its pure helpers, run in Node with no browser), content/reader.json, assets/css/reader.css,
the hook in assets/js/shell.js and scripts/list_headings.py. The tests that need Node are skipped, not failed, when `node` is not on PATH.
Standard library only.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import list_headings  # noqa: E402

NODE = shutil.which("node")
READER_JS = ROOT / "assets" / "js" / "reader.js"
READER_CSS = ROOT / "assets" / "css" / "reader.css"
READER_JSON = ROOT / "content" / "reader.json"
NAV = ROOT / "content" / "nav.json"


def run_node(body: str, data=None):
    """Run `body` (ES module code that can use `R`, the reader.js exports, and `data`) next to a copy of reader.js; return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(READER_JS, tmp / "reader.mjs")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text(
            "import * as R from './reader.mjs'; import fs from 'node:fs';\n"
            "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def chapter_items():
    return [it for w in load_json(NAV)["wings"] for it in w["items"] if it.get("chapter") is not None]


@unittest.skipUnless(NODE, "node is not installed")
class PureHelpers(unittest.TestCase):
    def test_slugify_and_unique_id(self):
        out = run_node("""
            const taken = new Set(['intro']);
            console.log(JSON.stringify({
              a: R.slugify('3.2 Workspace chat docks'),
              b: R.slugify('Café — Über straße!'),
              c: R.slugify('x'.repeat(39) + ' yy zz'),
              d: R.slugify('***'),
              u1: R.uniqueId('intro', taken), u2: R.uniqueId('intro', taken), u3: R.uniqueId('fresh', taken),
            }));""")
        self.assertEqual(out["a"], "3-2-workspace-chat-docks")
        self.assertEqual(out["b"], "cafe-uber-stra-e")         # accents fold away; the sharp s has no ASCII form, so it becomes a hyphen
        self.assertEqual(out["d"], "section")
        self.assertFalse(out["c"].endswith("-"))
        self.assertLessEqual(len(out["c"]), 40)
        self.assertEqual([out["u1"], out["u2"], out["u3"]], ["intro-2", "intro-3", "fresh"])

    def test_slug_matches_the_python_listing(self):
        """list_headings.py and reader.js must make the same id for a heading without one."""
        samples = ["Hello, World", "0.5 Situation index — \"I am at X, go to Y\"", "Phase 3a (Moderate) — scale out, don't re-architect",
                   "Café déjà vu", "   ", "A" * 60, "What gets built", "§ 4 — Ünïcode & symbols ✓", "ß ø æ"]
        js = run_node("console.log(JSON.stringify(data.map((s) => R.slugify(s))));", samples)
        self.assertEqual(js, [list_headings.slugify(s) for s in samples])

    def test_starts_numbered(self):
        out = run_node("""console.log(JSON.stringify(data.map((s) => R.startsNumbered(s))));""",
                       ["4. Chat", "2.1 Sign in", "0.5 Situation index", "A.1 Scope", "12", "3) Steps",
                        "Phase 0 (now)", "What gets built", "2026 plans", "Tech-A", "A Scope"])
        # "2026 plans" counts as numbered on purpose: refusing to number is the safe side of a guess
        self.assertEqual(out, [True, True, True, True, True, True, False, False, True, False, False])

    def test_plan_toc_drops_a_lone_leading_h1(self):
        out = run_node("""
            const heads = [{id:'t',text:'Title',level:1},{id:'a',text:'A',level:2},{id:'a1',text:'A1',level:3},{id:'b',text:'B',level:2}];
            const p = R.planToc(heads);
            console.log(JSON.stringify({ items: p.items.map((i) => [i.id, i.depth]), tree: p.tree.map((g) => [g.id, g.children.map((c) => c.id)]) }));""")
        self.assertEqual(out["items"], [["a", 0], ["a1", 1], ["b", 0]])
        self.assertEqual(out["tree"], [["a", ["a1"]], ["b", []]])

    def test_plan_toc_keeps_many_h1s_like_the_rulebook(self):
        out = run_node("""
            const heads = [{id:'t',text:'T',level:1},{id:'s1',text:'S1',level:1},{id:'s1a',text:'S1a',level:2},{id:'s2',text:'S2',level:1}];
            const p = R.planToc(heads);
            console.log(JSON.stringify(p.items.map((i) => [i.id, i.depth])));""")
        self.assertEqual(out, [["t", 0], ["s1", 0], ["s1a", 1], ["s2", 0]])

    def test_plan_toc_orphan_deep_heading_is_top_level(self):
        """The feature guide opens with an h3 before any h2."""
        out = run_node("""
            const heads = [{id:'x',text:'X',level:3},{id:'a',text:'A',level:2},{id:'a1',text:'A1',level:3}];
            const p = R.planToc(heads);
            console.log(JSON.stringify({ items: p.items.map((i) => [i.id, i.depth]), tree: p.tree.map((g) => g.id) }));""")
        self.assertEqual(out["items"], [["x", 0], ["a", 0], ["a1", 1]])
        self.assertEqual(out["tree"], ["x", "a"])

    def test_plan_toc_three_levels_and_empty_text(self):
        out = run_node("""
            const heads = [{id:'a',text:'A',level:1},{id:'b',text:'B',level:1},{id:'b1',text:'B1',level:2},{id:'b11',text:'B11',level:3},{id:'e',text:'',level:2}];
            const p = R.planToc(heads);
            console.log(JSON.stringify(p.items.map((i) => [i.id, i.depth])));""")
        self.assertEqual(out, [["a", 0], ["b", 0], ["b1", 1], ["b11", 2]])

    def test_plan_numbers_and_can_number(self):
        out = run_node("""
            const heads = [{id:'a',text:'Alpha',level:2},{id:'a1',text:'Alpha one',level:3},{id:'a2',text:'Alpha two',level:3},{id:'b',text:'Beta',level:2},{id:'b1',text:'Beta one',level:3}];
            const p = R.planToc(heads);
            console.log(JSON.stringify({ n: [...R.planNumbers(p.items)], ok: R.canNumber(p.items),
              no: R.canNumber(R.planToc([{id:'x',text:'1. Intro',level:2}]).items), empty: R.canNumber([]) }));""")
        nbsp = "\u00a7\u00a0"
        self.assertEqual(out["n"], [["a", nbsp + "1"], ["a1", nbsp + "1.1"], ["a2", nbsp + "1.2"], ["b", nbsp + "2"], ["b1", nbsp + "2.1"]])
        self.assertTrue(out["ok"])
        self.assertFalse(out["no"])
        self.assertFalse(out["empty"])

    def test_matches_all(self):
        out = run_node("""console.log(JSON.stringify([
            R.matchesAll('Stage 4 Orchestrator: PLAN', 'plan orch'), R.matchesAll('Stage 4', 'plan'), R.matchesAll('anything', '   '), R.matchesAll('ABC', 'abc')]));""")
        self.assertEqual(out, [True, False, True, True])

    def test_chip_and_minutes(self):
        out = run_node("""console.log(JSON.stringify([R.chipText('Chapter 4 of 14'), R.chipText('  Appendix   A '), R.chipText(null),
            R.readMinutes('8,064 words (~37 min read)'), R.readMinutes('1,234 minutes read'), R.readMinutes('no time here'), R.readMinutes(undefined)]));""")
        self.assertEqual(out, ["Ch. 4 of 14", "App. A", "", 37, 1234, None, None])

    def test_prefs_and_config_are_forgiving(self):
        out = run_node("""
            const cfg = R.mergeConfig(null);
            const weird = R.mergeConfig({ typography: { sizes: [9, -1], defaultSize: 99, defaultFont: 'comic' }, callouts: 'x', chapters: 3, defaults: { tableFilterMinRows: 10 } });
            console.log(JSON.stringify({
              cfg: cfg.typography, weird: weird.typography, wc: weird.callouts, wch: weird.chapters, wd: weird.defaults,
              p1: R.normalizePrefs(null, cfg), p2: R.normalizePrefs({ font: 'sans', size: 99 }, cfg), p3: R.normalizePrefs({ font: 'x', size: -4 }, cfg), p4: R.normalizePrefs({ size: 1.5 }, cfg),
              c1: R.chapterConfig(cfg, 'nope'), c2: R.chapterConfig(R.mergeConfig({ chapters: { a: { numbered: true } } }), 'a'),
              c3: R.chapterConfig(R.mergeConfig({ chapters: { a: 5 } }), 'a'), c4: R.chapterConfig(cfg, 'constructor'),
            }));""")
        self.assertEqual(out["cfg"]["sizes"], [0.96, 1.02, 1.08, 1.16, 1.26])
        self.assertEqual(out["weird"]["sizes"], [0.96, 1.02, 1.08, 1.16, 1.26])     # unusable sizes fall back
        self.assertEqual(out["weird"]["defaultSize"], 4)                             # clamped to the last size
        self.assertEqual(out["weird"]["defaultFont"], "serif")
        self.assertEqual((out["wc"], out["wch"]), ([], {}))
        self.assertEqual(out["wd"]["tableFilterMinRows"], 10)
        self.assertEqual(out["wd"]["numbered"], False)
        self.assertEqual(out["p1"], {"font": "serif", "size": 2})
        self.assertEqual(out["p2"], {"font": "sans", "size": 4})
        self.assertEqual(out["p3"], {"font": "serif", "size": 0})
        self.assertEqual(out["p4"], {"font": "serif", "size": 2})
        self.assertEqual(out["c1"]["numbered"], False)
        self.assertEqual(out["c2"]["numbered"], True)
        self.assertEqual(out["c3"]["numbered"], False)
        self.assertEqual(out["c4"]["numbered"], False)                               # inherited keys are not chapters

    def test_resume_rules_and_pruning(self):
        out = run_node("""
            const ok = { id: 'x', pct: 40 };
            const many = {}; for (let i = 0; i < 60; i++) many['c' + i] = { id: 'x', pct: 10, t: i };
            many.bad = 'nope';
            const kept = R.prunePositions(many, 40);
            console.log(JSON.stringify({
              a: R.shouldOfferResume(ok, false), b: R.shouldOfferResume(ok, true), c: R.shouldOfferResume({ id: 'x', pct: 2 }, false),
              d: R.shouldOfferResume({ id: 'x', pct: 97 }, false), e: R.shouldOfferResume(null, false), f: R.shouldOfferResume({ pct: 50 }, false),
              n: Object.keys(kept).length, newest: kept.c59 !== undefined, oldest: kept.c0 !== undefined, bad: 'bad' in kept }));""")
        self.assertEqual([out[k] for k in "abcdef"], [True, False, False, False, False, False])
        self.assertEqual(out["n"], 40)
        self.assertTrue(out["newest"])
        self.assertFalse(out["oldest"])
        self.assertFalse(out["bad"])

    def test_neighbours_follow_nav_order(self):
        out = run_node("""
            const nav = data; const ids = nav.wings.flatMap((w) => w.items).filter((i) => i.chapter != null).map((i) => i.id);
            const at = (id) => { const n = R.neighbours(nav, id); return n && [n.prev && n.prev.id, n.next && n.next.id, n.item.id]; };
            console.log(JSON.stringify({ first: at(ids[0]), mid: at(ids[3]), last: at(ids[ids.length - 1]), ids, none: R.neighbours(nav, 'index'), empty: R.neighbours(null, 'x') }));""", load_json(NAV))
        ids = [it["id"] for it in chapter_items()]
        self.assertEqual(out["ids"], ids)
        self.assertEqual(out["first"], [None, ids[1], ids[0]])
        self.assertEqual(out["mid"], [ids[2], ids[4], ids[3]])
        self.assertEqual(out["last"], [ids[-2], None, ids[-1]])
        self.assertIsNone(out["none"])
        self.assertIsNone(out["empty"])
        self.assertEqual(len(ids), 17)


@unittest.skipUnless(NODE, "node is not installed")
class Callouts(unittest.TestCase):
    CFG = load_json(READER_JSON)

    def classify(self, texts):
        return run_node("""
            const rules = R.compileCallouts(data.rules);
            console.log(JSON.stringify(data.texts.map((t) => { const r = R.classifyCallout(t, rules); return r && [r.type, r.label, !!r.muted, r.href || null]; })));""",
                        {"rules": self.CFG["callouts"], "texts": texts})

    def test_every_rule_compiles(self):
        n = run_node("console.log(JSON.stringify(R.compileCallouts(data).length));", self.CFG["callouts"])
        self.assertEqual(n, len(self.CFG["callouts"]))

    def test_expected_matches(self):
        out = self.classify([
            "Purpose: the user manual and feature register for MiniMe.",
            "STATUS BASIS: this guide describes the implementation",
            "Rule: a tool's effective tier is the higher of its M2C risk level",
            "Golden Rule 7: never charge before the ledger row exists",
            "Invariant: one account, one ledger",
            "Lock: the price card is frozen",
            "Definition: a stage is one step of the orchestrator",
            "Warning: do not run this on production",
            "Risk: the sandbox may be bypassed",
            "Decision: use gVisor by default",
        ])
        self.assertEqual([o[0] for o in out], ["note", "note", "rule", "rule", "invariant", "invariant", "definition", "warning", "warning", "decision"])
        self.assertEqual(out[1][2], True)                       # Status basis is muted
        self.assertEqual(out[0][2], False)
        self.assertEqual(out[2][3], "decisions.html")           # Rule links to the decisions page

    def test_things_that_must_not_match(self):
        out = self.classify([
            "Rules: (a) bill in the currency shown on the price card; (b) annual plan = 10x monthly",   # plural "Rules" is a list, not a Rule
            "The purpose: of this section is",
            "Purposeful design: matters",
            "Files: backend/config/credits.json",
            "Rule of thumb is to keep it short",
            "Locksmith: not a callout",
            "Done when: every fixture validates",
            "   ",
            "",
        ])
        self.assertEqual(out, [None] * 9)

    def test_only_the_start_of_a_paragraph_counts(self):
        out = run_node("""
            const rules = R.compileCallouts(data);
            const far = 'x'.repeat(130) + ' Purpose: late';
            console.log(JSON.stringify([R.classifyCallout(far, rules), R.classifyCallout('  Purpose:   spaced\\n out', rules).type]));""", self.CFG["callouts"])
        self.assertEqual(out, [None, "note"])

    def test_a_bad_rule_is_skipped_not_fatal(self):
        out = run_node("""
            const rules = R.compileCallouts(data);
            console.log(JSON.stringify([rules.length, R.classifyCallout('Purpose: x', rules).type, R.compileCallouts('nope').length, R.compileCallouts(null).length]));""",
                       [{"pattern": "([", "type": "note", "label": "Broken"}, {"pattern": "^Purpose:", "type": "note", "label": "Purpose"}, {"type": "x"}, None])
        self.assertEqual(out, [1, "note", 0, 0])

    def test_real_chapter_paragraphs(self):
        """The two lead-in paragraphs of Chapter 4, taken from the page itself, are classified."""
        html = (ROOT / "doc-minime-feature-guide.html").read_text(encoding="utf-8")
        texts = []
        for label in ("Purpose:", "Status basis:"):
            m = re.search(r"<p><strong>" + re.escape(label) + r"</strong>(.*?)</p>", html, re.S)
            self.assertIsNotNone(m, label)
            texts.append(label + re.sub(r"<[^>]+>", "", m.group(1)))
        out = self.classify(texts)
        self.assertEqual([o[:3] for o in out], [["note", "Purpose", False], ["note", "Status basis", True]])


@unittest.skipUnless(NODE, "node is not installed")
class RealChapters(unittest.TestCase):
    def test_toc_plan_covers_every_chapter(self):
        data = {}
        for it in chapter_items():
            data[it["id"]] = list_headings.headings(ROOT / it["url"])
        out = run_node("""
            const res = {};
            for (const [id, hs] of Object.entries(data)) {
              const p = R.planToc(hs.filter((h) => h.level <= 3));
              const ids = p.items.map((i) => i.id);
              res[id] = { items: p.items.length, unique: new Set(ids).size === ids.length, groupsOk: p.tree.every((g) => g.depth === 0), can: R.canNumber(p.items) };
            }
            console.log(JSON.stringify(res));""", data)
        for cid, r in out.items():
            self.assertTrue(r["unique"], f"{cid}: duplicate TOC ids")
            self.assertTrue(r["groupsOk"], cid)
        # the two embed pages have no article headings, so no TOC; every other chapter has one
        for cid in ("doc-m2c-product", "doc-menux-product"):
            self.assertEqual(out[cid]["items"], 0)
        for cid, r in out.items():
            if cid not in ("doc-m2c-product", "doc-menux-product"):
                self.assertGreater(r["items"], 5, cid)
        # numbering is only ever applied where it cannot clash with the headings' own numbers
        cfg = load_json(READER_JSON)
        for cid, own in cfg["chapters"].items():
            if own.get("numbered"):
                self.assertTrue(out[cid]["can"], f"{cid} is set to numbered but its headings already carry numbers")
        self.assertFalse(out["doc-rulebook"]["can"])


class ReaderJson(unittest.TestCase):
    cfg = load_json(READER_JSON)

    def test_shape(self):
        self.assertEqual(self.cfg["version"], 1)
        t = self.cfg["typography"]
        self.assertEqual(len(t["sizes"]), 5)
        self.assertEqual(t["sizes"], sorted(t["sizes"]))
        self.assertTrue(0 <= t["defaultSize"] < len(t["sizes"]))
        self.assertIn(t["defaultFont"], ("serif", "sans"))
        self.assertFalse(self.cfg["defaults"]["numbered"], "numbering is opt-in per chapter")

    def test_callout_types_exist_in_the_component_css(self):
        css = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
        for rule in self.cfg["callouts"]:
            self.assertTrue(rule["label"].strip(), rule)
            self.assertIn(f".mm-callout--{rule['type']}", css, f"no .mm-callout--{rule['type']} in components.css")
            re.compile(rule["pattern"])                                    # at least valid for Python; Node is checked in Callouts
            if rule.get("href"):
                self.assertTrue((ROOT / rule["href"]).exists(), f"{rule['href']} does not exist")

    def test_chapter_keys_are_real_chapters(self):
        ids = {it["id"] for it in chapter_items()}
        for key in self.cfg["chapters"]:
            self.assertIn(key, ids)


class Stylesheet(unittest.TestCase):
    ALLOWED_BARE = {".rd-progress", ".rd-bar, .rd-aa"}

    @staticmethod
    def selectors(css: str, depth=0):
        """Yield every selector list of every style rule, descending into @media (the @media prelude itself is skipped)."""
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        i, n = 0, len(css)
        while i < n:
            j = css.find("{", i)
            if j < 0:
                break
            prelude = css[i:j].strip()
            k, d = j + 1, 1
            while k < n and d:
                d += {"{": 1, "}": -1}.get(css[k], 0)
                k += 1
            body = css[j + 1:k - 1]
            if prelude.startswith("@media") or prelude.startswith("@supports"):
                yield from Stylesheet.selectors(body, depth + 1)
            elif prelude.startswith("@"):
                pass
            else:
                yield prelude
            i = k

    @staticmethod
    def split_top(sel: str):
        parts, d, cur = [], 0, ""
        for ch in sel:
            if ch in "([":
                d += 1
            elif ch in ")]":
                d -= 1
            if ch == "," and d == 0:
                parts.append(cur.strip())
                cur = ""
            else:
                cur += ch
        parts.append(cur.strip())
        return [p for p in parts if p]

    def test_every_rule_is_scoped_to_the_reader(self):
        css = READER_CSS.read_text(encoding="utf-8")
        bad = []
        for prelude in self.selectors(css):
            if prelude in self.ALLOWED_BARE:
                continue
            for s in self.split_top(prelude):
                if not s.startswith("html[data-reader]"):
                    bad.append(s)
        self.assertEqual(bad, [], "selectors that would apply before reader.js has run (or with ?legacy=1)")

    def test_no_raw_colours_outside_print(self):
        css = re.sub(r"/\*.*?\*/", "", READER_CSS.read_text(encoding="utf-8"), flags=re.S)
        head, _, printed = css.partition("@media print")
        self.assertTrue(printed, "the print block is missing")
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", head), [])

    def test_the_tokens_it_uses_exist(self):
        tokens = (ROOT / "assets" / "css" / "tokens.css").read_text(encoding="utf-8")
        shell = (ROOT / "assets" / "css" / "shell.css").read_text(encoding="utf-8")
        css = READER_CSS.read_text(encoding="utf-8")
        defined_here = set(re.findall(r"(--rd-[a-z-]+)\s*:", css))
        set_by_js = {"--rd-rows", "--rd-table-max"}                      # reader.js sets these per table, and every use has a fallback
        defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", tokens + shell)) | defined_here | set_by_js
        used = set(re.findall(r"var\((--[a-z0-9-]+)", css))
        self.assertEqual(sorted(used - defined), [], "reader.css uses custom properties nothing defines")

    def test_no_important_outside_the_bottom_sheet(self):
        css = re.sub(r"/\*.*?\*/", "", READER_CSS.read_text(encoding="utf-8"), flags=re.S)
        blocks = re.findall(r"[^{}]+\{[^{}]*!important[^{}]*\}", css)
        for b in blocks:
            sel = b.split("{")[0]
            self.assertTrue(".toc.rd-toc" in sel or "@media print" in b or ".rd-bar" in sel or "html[data-reader] :is(" in sel, f"unexpected !important: {sel.strip()[:80]}")


class Wiring(unittest.TestCase):
    def test_shell_loads_the_reader_on_chapter_pages(self):
        s = (ROOT / "assets" / "js" / "shell.js").read_text(encoding="utf-8")
        self.assertIn('import("./reader.js")', s)
        self.assertIn("main .bk-banner, main .doc article", s)
        self.assertIn("navReady", s)
        self.assertRegex(s, r"function boot\(\)[\s\S]*?load\(\);\s*loadReader\(\);")

    def test_reader_is_not_imported_statically(self):
        """Only chapter pages should pay for it."""
        s = (ROOT / "assets" / "js" / "shell.js").read_text(encoding="utf-8")
        self.assertNotRegex(s, r"^import .*reader\.js", re.M)

    def test_reader_js_has_no_external_dependencies(self):
        s = READER_JS.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^import\s", s, re.M), [])
        self.assertNotIn("http://", s)
        self.assertNotIn("https://", s)

    def test_chapter_bodies_are_untouched_by_this_patch(self):
        """P04 must not edit doc-*.html: they are rebuilt by an external builder. Only checks when git is available."""
        if not shutil.which("git") or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        r = subprocess.run(["git", "status", "--porcelain", "--", "doc-*.html"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.stdout.strip(), "", "a chapter page has uncommitted changes")


class ListHeadings(unittest.TestCase):
    def test_feature_guide(self):
        rows = list_headings.headings(ROOT / "doc-minime-feature-guide.html")
        self.assertEqual(len(rows), 89)
        self.assertEqual(rows[0]["level"], 1)
        self.assertEqual(rows[0]["id"], "minime-feature-guide")
        self.assertEqual(rows[1]["id"], "ecosystem-synchronization-companion-chapters")     # the guide opens with an h3
        self.assertEqual(rows[1]["level"], 3)
        self.assertTrue(all(r["own"] for r in rows), "every heading of the guide already has an id")
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_rulebook_h1_and_h2_counts(self):
        """30 <h1> on the page, one of them the page title outside the article: the reader sees 29, as its comments say."""
        rows = list_headings.headings(ROOT / "doc-rulebook.html")
        self.assertEqual(sum(r["level"] == 1 for r in rows), 29)
        self.assertEqual(sum(r["level"] == 2 for r in rows), 128)

    def test_footer_cards_and_toc_are_not_headings(self):
        for it in chapter_items():
            for r in list_headings.headings(ROOT / it["url"]):
                self.assertNotIn("On this page", r["text"])

    def test_missing_ids_get_unique_slugs(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            page = tmp / "t.html"
            page.write_text('<main><article><h1 id="a">A</h1><h2>Same</h2><h2>Same</h2><h3 id="same">x</h3><h4>  </h4></article>'
                            '<div class="bk-footer"><h3>Skipped</h3></div></main>', encoding="utf-8")
            rows = list_headings.headings(page)
            self.assertEqual([(r["id"], r["own"]) for r in rows], [("a", True), ("same-2", False), ("same-3", False), ("same", True)])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_command_line(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "list_headings.py"), "doc-rulebook", "--max-level", "1", "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)["doc-rulebook"]
        self.assertEqual(len(rows), 29)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "list_headings.py"), "nope-not-here"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        self.assertNotEqual(r.returncode, 0)


GLOSSARY_SAMPLE = {"terms": [
    {"term": "Golden Rule", "aliases": ["Golden Rules"], "category": "Governance", "short": "A rule."},
    {"term": "Rule", "short": "Too short a word to match alone.", "match": "off"},
    {"term": "T0 to T5 approval tiers", "aliases": ["T0\u2013T5", "trust tiers"], "short": "Tiers."},
    {"term": "REAL_ACTION_ROLES", "short": "A map.", "match": "cs"},
    {"term": "work package", "aliases": ["WP"], "short": "A unit."},
    {"term": "", "short": "no name"}, {"term": "No short"},
]}


@unittest.skipUnless(NODE, "node is not installed")
class GlossaryTooltips(unittest.TestCase):
    """The pure half of the glossary tooltips (P05): which words get underlined. The DOM half is checked by hand in a browser."""

    def hits(self, text):
        return run_node("""
            const terms = R.normalizeGlossary(data.g), c = R.compileTerms(terms);
            console.log(JSON.stringify(R.findTermHits(data.t, c).map((h) => [data.t.slice(h.start, h.end), h.term.term])));""",
                        {"g": GLOSSARY_SAMPLE, "t": text})

    def test_off_and_malformed_entries_are_dropped(self):
        out = run_node("console.log(JSON.stringify(R.normalizeGlossary(data).map((t) => [t.id, t.match])));", GLOSSARY_SAMPLE)
        self.assertEqual(out, [["golden-rule", "ci"], ["t0-to-t5-approval-tiers", "ci"], ["real-action-roles", "cs"], ["work-package", "ci"]])

    def test_whole_words_any_case_aliases_and_plurals(self):
        self.assertEqual(self.hits("The golden rules say: see Golden Rule 5. Work packages and a WP."),
                         [["golden rules", "Golden Rule"], ["Golden Rule", "Golden Rule"], ["Work packages", "work package"], ["WP", "work package"]])

    def test_a_term_inside_a_longer_word_or_a_hyphenated_name_is_left_alone(self):
        self.assertEqual(self.hits("Unwp is not one, nor is subwork packager, nor my-WP-thing or GoldenRule."), [])

    def test_terms_that_contain_dashes_and_spaces_match(self):
        self.assertEqual(self.hits("T0\u2013T5 and the trust  tiers."), [["T0\u2013T5", "T0 to T5 approval tiers"], ["trust  tiers", "T0 to T5 approval tiers"]])

    def test_exact_case_terms_ignore_other_casings(self):
        self.assertEqual(self.hits("real_action_roles and REAL_ACTION_ROLES"), [["REAL_ACTION_ROLES", "REAL_ACTION_ROLES"]])

    def test_first_use_per_section_only(self):
        out = run_node("""
            const t = R.sectionTracker();
            console.log(JSON.stringify([t.take(1, 'a'), t.take(1, 'a'), t.take(1, 'b'), t.take(2, 'a'), t.take(2, 'a')]));""")
        self.assertEqual(out, [True, False, True, True, False])

    def test_the_committed_glossary_marks_words_in_at_least_two_chapters(self):
        from html.parser import HTMLParser

        class Text(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.parts, self.skip = [], 0

            def handle_starttag(self, tag, attrs):
                self.skip += tag in ("script", "style", "code", "pre", "a")

            def handle_endtag(self, tag):
                self.skip = max(0, self.skip - (tag in ("script", "style", "code", "pre", "a")))

            def handle_data(self, data):
                if not self.skip:
                    self.parts.append(data)

        texts = {}
        for ch in ("doc-rulebook", "doc-minime-feature-guide", "doc-menux-feature-guide"):
            p = Text()
            p.feed((ROOT / f"{ch}.html").read_text(encoding="utf-8"))
            texts[ch] = " ".join(p.parts)
        out = run_node("""
            const c = R.compileTerms(R.normalizeGlossary(data.g)), n = {};
            for (const [k, v] of Object.entries(data.t)) n[k] = new Set(R.findTermHits(v, c).map((h) => h.term.id)).size;
            console.log(JSON.stringify(n));""", {"g": load_json(ROOT / "content" / "glossary.json"), "t": texts})
        self.assertGreaterEqual(sum(1 for n in out.values() if n >= 3), 2, out)


class GlossaryWiring(unittest.TestCase):
    def test_reader_js_skips_headings_code_and_links_and_closes_on_escape(self):
        s = READER_JS.read_text(encoding="utf-8")
        for needle in ('"PRE"', '"CODE"', '"A"', "/^H[1-3]$/", "/^H[4-6]$/", 'e.key === "Escape" && R.tipFor'):
            self.assertIn(needle, s)

    def test_css_styles_the_term_and_the_tip_under_the_reader_attribute(self):
        css = re.sub(r"/\*.*?\*/", "", READER_CSS.read_text(encoding="utf-8"), flags=re.S)
        for sel in (".rd-term", ".rd-tip"):
            self.assertRegex(css, r"html\[data-reader\]\s+" + re.escape(sel))
        self.assertRegex(css, r"underline dotted")
        self.assertRegex(css, r"@media print\s*\{[^@]*?\.rd-tip\s*\{\s*display:\s*none")

    def test_the_switch_is_in_reader_json_and_defaults_on(self):
        self.assertIs(load_json(READER_JSON)["defaults"]["glossary"], True)


if __name__ == "__main__":
    unittest.main(verbosity=1)
