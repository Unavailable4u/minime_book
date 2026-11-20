#!/usr/bin/env python3
"""Tests for the figure layer (patch P06). Run: python scripts/test_figures.py

Covers assets/js/figures.js (its pure helpers, run in Node with no browser), assets/css/figures.css, the committed manifests in
content/figures/ and the SVGs next to them, the figure rules of scripts/check_site.py, the hook in assets/js/shell.js and
scripts/vendor_mermaid.py. The tests that need Node are skipped, not failed, when `node` is not on PATH.
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
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import test_check_site as tcs  # noqa: E402  (its Site / SiteCase helpers build throwaway sites)
import test_reader as trd      # noqa: E402  (its Stylesheet.selectors reads a stylesheet's rules)
import vendor_mermaid          # noqa: E402

cs = tcs.cs
NODE = shutil.which("node")
FIGURES_JS = ROOT / "assets" / "js" / "figures.js"
FIGURES_CSS = ROOT / "assets" / "css" / "figures.css"
SHELL_JS = ROOT / "assets" / "js" / "shell.js"
FIG_DIR = ROOT / "content" / "figures"
NAV = ROOT / "content" / "nav.json"


def run_node(body: str, data=None):
    """Run `body` (ES module code that can use `F`, the figures.js exports, and `data`) next to a copy of figures.js; return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(FIGURES_JS, tmp / "figures.mjs")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text(
            "import * as F from './figures.mjs'; import fs from 'node:fs';\n"
            "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def manifests():
    return sorted(p for p in FIG_DIR.glob("*.json"))


def chapter_ids():
    return {it["id"]: it for w in load_json(NAV)["wings"] for it in w["items"] if it.get("chapter") is not None}


# ---------------------------------------------------------------- the pure helpers
GOOD = [
    {"id": "a1", "after": "intro", "type": "archify", "src": "architecture/x.html", "size": [1200, 620], "caption": "C", "alt": "A"},
    {"id": "b-2", "after": "intro", "type": "svg", "src": "content/figures/svg/b.svg", "caption": "C", "alt": "A", "wide": True, "place": "start"},
    {"id": "c3", "after": "intro", "type": "mermaid", "code": "flowchart LR\n A-->B", "caption": "C", "alt": "A"},

]

# P26: the arch type (a generated architecture view): view is required, flow and focus are optional
ARCH_GOOD = [
    {"id": "d4", "after": "intro", "type": "arch", "view": "system", "caption": "C", "alt": "A", "wide": True},
    {"id": "e5", "after": "intro", "type": "arch", "view": "unified", "flow": "task-pipeline", "focus": "backend/eo", "caption": "C", "alt": "A"},
]

# (entry, a piece of the message that must appear in `problems`)
BAD = [
    ({"id": "Bad Id", "after": "h", "type": "svg", "code": "<svg/>", "caption": "c", "alt": "a"}, "id"),
    ({"id": "x", "type": "svg", "code": "<svg/>", "caption": "c", "alt": "a"}, "after"),
    ({"id": "x", "after": "h", "type": "svg", "code": "<svg/>", "alt": "a"}, "caption"),
    ({"id": "x", "after": "h", "type": "chart", "code": "{}", "caption": "c", "alt": "a"}, "not available yet"),
    ({"id": "x", "after": "h", "type": "graph-slice", "caption": "c", "alt": "a"}, "not available yet"),
    ({"id": "x", "after": "h", "type": "gif", "caption": "c", "alt": "a"}, "unknown type"),
    ({"id": "x", "after": "h", "type": "archify", "src": "architecture/x.html", "caption": "c", "alt": "a"}, "size"),
    ({"id": "x", "after": "h", "type": "archify", "src": "architecture/x.html", "size": [50, 50], "caption": "c", "alt": "a"}, "size"),
    ({"id": "x", "after": "h", "type": "archify", "src": "https://evil.example/x.html", "size": [1200, 620], "caption": "c", "alt": "a"}, "architecture/"),
    ({"id": "x", "after": "h", "type": "archify", "src": "architecture/../secret.html", "size": [1200, 620], "caption": "c", "alt": "a"}, "architecture/"),
    ({"id": "x", "after": "h", "type": "svg", "caption": "c", "alt": "a"}, "exactly one"),
    ({"id": "x", "after": "h", "type": "svg", "src": "content/figures/a.svg", "code": "<svg/>", "caption": "c", "alt": "a"}, "exactly one"),
    ({"id": "x", "after": "h", "type": "svg", "src": "content/figures/a.png", "caption": "c", "alt": "a"}, ".svg"),
    ({"id": "x", "after": "h", "type": "svg", "src": "content/figures/../../secret.svg", "caption": "c", "alt": "a"}, ".svg"),
    ({"id": "x", "after": "h", "type": "svg", "src": "assets/x.svg", "caption": "c", "alt": "a"}, ".svg"),
    ({"id": "x", "after": "h", "type": "svg", "code": "<div>no</div>", "caption": "c", "alt": "a"}, "<svg"),
    ({"id": "x", "after": "h", "type": "mermaid", "src": "content/figures/a.svg", "caption": "c", "alt": "a"}, ".mmd"),
    ({"id": "x", "after": "h", "type": "arch", "caption": "c", "alt": "a"}, "view"),
    ({"id": "x", "after": "h", "type": "arch", "view": "Bad View", "caption": "c", "alt": "a"}, "view"),
    ({"id": "x", "after": "h", "type": "arch", "view": "system", "flow": "no good", "caption": "c", "alt": "a"}, "flow"),
    ({"id": "x", "after": "h", "type": "arch", "view": "system", "focus": "", "caption": "c", "alt": "a"}, "focus"),
    ("not an object", "not an object"),
]

# (text, safe?) : figures.js and check_site.py must give the same verdict on every one of these
SVG_SAMPLES = [
    ('<svg viewBox="0 0 10 10"><rect width="4" height="4"/></svg>', True),
    ('<?xml version="1.0"?>\n<!-- made by hand -->\n<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>', True),
    ('<svg><style>.a{fill:var(--ink)}</style><path class="a" d="M0 0"/></svg>', True),
    ('<svg><defs><marker id="m"><path d="M0 0"/></marker></defs><path marker-end="url(#m)" d="M0 0"/></svg>', True),
    ('<svg><use href="#m"/><use xlink:href="#m"/></svg>', True),
    ('<svg><animateTransform attributeName="transform"/></svg>', True),        # not on the deny list: only <animate> and <set> are
    ('<svg><script>alert(1)</script></svg>', False),
    ('<svg><SCRIPT src="x.js"></SCRIPT></svg>', False),
    ('<svg onload="x()"></svg>', False),
    ('<svg><rect onclick = "x()"/></svg>', False),
    ('<svg><foreignObject><div/></foreignObject></svg>', False),
    ('<svg><image href="a.png"/></svg>', False),
    ('<svg><a href="https://example.com"><g/></a></svg>', False),
    ('<svg><use href="other.svg#m"/></svg>', False),
    ('<svg><a xlink:href="javascript:alert(1)"><g/></a></svg>', False),
    ('<svg><style>@import "x.css";</style></svg>', False),
    ('<svg><rect style="fill:url(http://x.example/a)"/></svg>', False),
    ('<svg><rect fill="url( \'http://x\')"/></svg>', False),
    ('<svg><animate attributeName="x"/></svg>', False),
    ('<svg><set attributeName="x"/></svg>', False),
    ('<iframe src="x"></iframe>', False),
    ('<div><svg/></div>', False),
    ('', False),
]


@unittest.skipUnless(NODE, "node is not installed")
class PureHelpers(unittest.TestCase):
    def test_a_good_manifest_is_accepted_whole(self):
        out = run_node("console.log(JSON.stringify(F.normalizeManifest({figures: data})));", GOOD)
        self.assertEqual(out["problems"], [])
        a, b, c = out["figures"]
        self.assertEqual((a["place"], a["wide"], a["size"], a["src"]), ("end", False, [1200, 620], "architecture/x.html"))
        self.assertEqual((b["place"], b["wide"], b["code"]), ("start", True, None))
        self.assertEqual((c["type"], c["src"], c["code"].startswith("flowchart")), ("mermaid", None, True))

    def test_arch_figures_need_a_view_and_nothing_else(self):
        out = run_node("console.log(JSON.stringify(F.normalizeManifest({figures: data})));", ARCH_GOOD)
        self.assertEqual([], out["problems"])
        a, b = out["figures"]
        self.assertEqual(("system", None, None), (a["view"], a["flow"], a["focus"]))
        self.assertEqual(("unified", "task-pipeline", "backend/eo"), (b["view"], b["flow"], b["focus"]))
        self.assertTrue(a["wide"])
        self.assertIsNone(a["src"]); self.assertIsNone(a["size"])

    def test_a_bare_list_works_like_the_wrapped_form(self):
        out = run_node("console.log(JSON.stringify([F.normalizeManifest(data).figures.length, F.normalizeManifest({figures: data}).figures.length]));", GOOD)
        self.assertEqual(out, [3, 3])

    def test_every_bad_entry_is_dropped_with_a_reason(self):
        for entry, why in BAD:
            with self.subTest(entry=entry):
                out = run_node("console.log(JSON.stringify(F.normalizeManifest({figures: [data]})));", entry)
                self.assertEqual(out["figures"], [])
                self.assertTrue(any(why in p for p in out["problems"]), out["problems"])

    def test_one_bad_entry_does_not_take_its_neighbours_down(self):
        out = run_node("console.log(JSON.stringify(F.normalizeManifest({figures: [data[0], {id: 'x'}, data[2]]})));", GOOD)
        self.assertEqual([f["id"] for f in out["figures"]], ["a1", "c3"])
        self.assertEqual(len(out["problems"]), 1)

    def test_duplicate_ids_keep_the_first(self):
        out = run_node("console.log(JSON.stringify(F.normalizeManifest({figures: [data[0], data[0]]})));", GOOD)
        self.assertEqual(len(out["figures"]), 1)
        self.assertTrue(any("duplicate" in p for p in out["problems"]))

    def test_the_manifest_itself_may_be_garbage(self):
        out = run_node("console.log(JSON.stringify([null, 5, 'x', {}, {figures: 3}].map((m) => F.normalizeManifest(m))));")
        for r in out:
            self.assertEqual(r["figures"], [])
            self.assertEqual(len(r["problems"]), 1)

    def test_a_missing_alt_warns_and_falls_back_to_the_caption(self):
        entry = {"id": "x", "after": "h", "type": "svg", "code": "<svg viewBox='0 0 1 1'></svg>", "caption": "The caption"}
        out = run_node("console.log(JSON.stringify(F.normalizeManifest({figures: [data]})));", entry)
        self.assertEqual(out["figures"][0]["alt"], "The caption")
        self.assertTrue(any("no \"alt\"" in p for p in out["problems"]))

    def test_chapter_item_and_labels(self):
        out = run_node("""
            const nav = {wings: [{items: [{id: 'doc-a', chapter: 4}, {id: 'doc-z', chapter: 'A'}]}, {items: [{id: 'docs'}]}]};
            console.log(JSON.stringify({
              a: F.chapterItem(nav, 'doc-a'), b: F.chapterItem(nav, 'nope'), c: F.chapterItem(null, 'x'), d: F.chapterItem({wings: [{}]}, 'x'),
              l1: F.figureLabel(4, 2), l2: F.figureLabel('A', 1), l3: F.figureLabel(undefined, 3), l4: F.figureLabel('', 3),
            }));""")
        self.assertEqual((out["a"]["chapter"], out["b"], out["c"], out["d"]), (4, None, None, None))
        self.assertEqual((out["l1"], out["l2"], out["l3"], out["l4"]), ("Figure 4.2", "Figure A.1", "Figure 3", "Figure 3"))

    def test_archify_urls_follow_the_reader_theme(self):
        out = run_node("""
            console.log(JSON.stringify([F.archifyUrl('architecture/x.html', 'dark'), F.archifyUrl('architecture/x.html', 'paper'),
              F.archifyUrl('architecture/x.html', 'anything'), F.ratioOf([1200, 620]), F.ratioOf([1000, 500])]));""")
        self.assertEqual(out, ["architecture/x.html?embed=1&theme=dark", "architecture/x.html?embed=1&theme=light", "architecture/x.html?embed=1&theme=dark", 0.5167, 0.5])

    def test_svg_size_prefers_the_viewbox(self):
        out = run_node("""
            console.log(JSON.stringify([F.svgSize({viewBox: '0 0 760 420', width: '5', height: '5'}), F.svgSize({viewBox: '0,0,100,50'}),
              F.svgSize({width: '300px', height: '200'}), F.svgSize({}), F.svgSize({viewBox: '0 0 0 0'}), F.svgSize({viewBox: null})]));""")
        self.assertEqual(out[0], {"w": 760, "h": 420})
        self.assertEqual(out[1], {"w": 100, "h": 50})
        self.assertEqual(out[2], {"w": 300, "h": 200})
        self.assertEqual(out[3], {"w": 800, "h": 500})
        self.assertEqual(out[4], {"w": 800, "h": 500})
        self.assertEqual(out[5], {"w": 800, "h": 500})

    def test_viewer_maths(self):
        out = run_node("""
            const box = {w: 1000, h: 600}, size = {w: 800, h: 400};
            const fit = F.fitTransform(box, size);
            const tiny = F.fitTransform(box, {w: 10, h: 10});
            const t = {k: 1, x: 100, y: 50};
            const z = F.zoomAt(t, 2, 300, 250, 0.1);            // the content point under (300, 250) must stay there
            const under = (tr) => [(300 - tr.x) / tr.k, (250 - tr.y) / tr.k];
            const clampHi = F.zoomAt({k: 7, x: 0, y: 0}, 10, 0, 0, 0.1), clampLo = F.zoomAt({k: 0.2, x: 0, y: 0}, 0.001, 0, 0, 0.1);
            const kv = F.keepVisible({k: 1, x: -5000, y: 9000}, box, size);
            const keep = F.keepVisible({k: 1, x: 100, y: 100}, box, size);
            const pinch = F.pinchStep({x: 0, y: 0}, {x: 100, y: 0}, {x: 0, y: 0}, {x: 200, y: 0});
            console.log(JSON.stringify({fit, tiny, z, before: under(t), after: under(z), clampHi, clampLo, kv, keep, pinch,
              wDown: F.wheelFactor(100) < 1, wUp: F.wheelFactor(-100) > 1, wNone: F.wheelFactor(0), wPinch: F.wheelFactor(-10, 0, true) > F.wheelFactor(-10, 0, false),
              wLine: F.wheelFactor(-3, 1) > F.wheelFactor(-3, 0), wHuge: F.wheelFactor(-1e9) === F.wheelFactor(-120)}));""")
        self.assertAlmostEqual(out["fit"]["k"], 1.19)                     # (1000 - 48) / 800: 24 px of padding on each side
        self.assertAlmostEqual(out["fit"]["x"], (1000 - 800 * 1.19) / 2)
        self.assertAlmostEqual(out["fit"]["y"], (600 - 400 * 1.19) / 2)
        self.assertEqual(out["tiny"]["k"], 2.5)                           # never blown up past 2.5x
        for a, b in zip(out["before"], out["after"]):
            self.assertAlmostEqual(a, b)
        self.assertEqual(out["clampHi"]["k"], 8)
        self.assertEqual(out["clampLo"]["k"], 0.1)
        self.assertEqual((out["kv"]["x"], out["kv"]["y"]), (80 - 800, 600 - 80))   # at least 80 px of the figure stays on screen
        self.assertEqual((out["keep"]["x"], out["keep"]["y"]), (100, 100))
        self.assertEqual(out["pinch"], {"factor": 2, "from": {"x": 50, "y": 0}, "dx": 50, "dy": 0})
        self.assertTrue(out["wDown"] and out["wUp"] and out["wPinch"] and out["wLine"] and out["wHuge"])
        self.assertEqual(out["wNone"], 1)

    def test_mermaid_theme_variables_come_from_the_tokens_with_fallbacks(self):
        out = run_node("""
            const tokens = {'--ink': '#eee', '--flow': '#0ff'};
            const v = F.mermaidThemeVariables((n) => tokens[n] || '');
            const d = F.mermaidThemeVariables(() => '');
            console.log(JSON.stringify({v, d}));""")
        self.assertEqual((out["v"]["primaryTextColor"], out["v"]["lineColor"]), ("#eee", "#0ff"))
        for key, val in out["d"].items():
            self.assertTrue(val, key)                                      # nothing is ever undefined or empty

    def test_semantic_classes_for_mermaid(self):
        out = run_node("""
            const get = (n) => ({'--flow': '#0ff', '--gate': '#fa0', '--brand': '#f05', '--ok': '#0f0', '--graph': '#a7f'}[n] || '');
            console.log(JSON.stringify({
              flow: F.withSemanticClasses('flowchart LR\\n A:::gate --> B', get),
              graph: F.withSemanticClasses('graph TD\\n A --> B', get),
              state: F.withSemanticClasses('stateDiagram-v2\\n [*] --> A', get),
              seq: F.withSemanticClasses('sequenceDiagram\\n A->>B: hi', get),
              own: F.withSemanticClasses('flowchart LR\\n A --> B\\n classDef gate fill:#000', get),
              commented: F.withSemanticClasses('%% note\\nflowchart LR\\n A --> B', get),
            }));""")
        self.assertIn("classDef gate stroke:#fa0,stroke-width:2px,stroke-dasharray:5 3", out["flow"])
        self.assertIn("classDef here stroke:#f05,stroke-width:4px", out["flow"])
        self.assertEqual(out["flow"].count("classDef"), 5)
        self.assertIn("classDef flow ", out["graph"])
        self.assertIn("classDef ok ", out["state"])
        self.assertEqual(out["seq"], "sequenceDiagram\n A->>B: hi")         # other diagram kinds have no classes: untouched
        self.assertNotIn("classDef gate stroke", out["own"])               # the author's own classDef wins
        self.assertEqual(out["own"].count("classDef"), 5)                  # 4 of ours + the author's
        self.assertEqual(out["commented"].count("classDef"), 5)


@unittest.skipUnless(NODE, "node is not installed")
class SvgSafety(unittest.TestCase):
    def test_javascript_and_python_agree_on_every_sample(self):
        js = run_node("console.log(JSON.stringify(data.map((t) => F.svgLooksSafe(t))));", [t for t, _ in SVG_SAMPLES])
        for (text, safe), got_js in zip(SVG_SAMPLES, js):
            with self.subTest(text=text[:60]):
                self.assertEqual(got_js, safe, "figures.js")
                self.assertEqual(cs.svg_problem(text) is None, safe, f"check_site.py: {cs.svg_problem(text)}")

    def test_python_says_why(self):
        self.assertIn("<svg", cs.svg_problem("<div/>"))
        self.assertIn("script", cs.svg_problem("<svg><script/></svg>").lower())

    def test_well_formedness(self):
        self.assertIsNone(cs.svg_not_well_formed('<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>'))
        self.assertIsNone(cs.svg_not_well_formed('\ufeff<svg><g/></svg>'))
        self.assertIsNotNone(cs.svg_not_well_formed("<svg><defs></defs></defs></svg>"))     # the stray </defs> an early draft had
        self.assertIsNotNone(cs.svg_not_well_formed("<svg><g></svg>"))


# ---------------------------------------------------------------- what is committed
class CommittedFigures(unittest.TestCase):
    def test_the_first_deliverable_is_there(self):
        got = {p.stem: [f["id"] for f in load_json(p)["figures"]] for p in manifests()}
        self.assertIn("pricing-tiers", got.get("doc-rulebook", []))
        self.assertIn("tech-chain", got.get("doc-tech-roadmap", []))
        self.assertEqual(sorted(got.get("doc-minime-feature-guide", [])),
                         sorted(["system-architecture", "task-run-lifecycle", "workspace-lifecycle", "task-pipeline", "approval-gate", "api-surface"]))

    def test_every_manifest_is_for_a_real_chapter(self):
        chapters = chapter_ids()
        for p in manifests():
            self.assertIn(p.stem, chapters, f"{p.name}: no chapter with that id in nav.json")
            self.assertTrue((ROOT / chapters[p.stem]["url"]).is_file())

    @unittest.skipUnless(NODE, "node is not installed")
    def test_figures_js_accepts_every_manifest_without_a_single_problem(self):
        for p in manifests():
            with self.subTest(p.name):
                raw = load_json(p)
                out = run_node("console.log(JSON.stringify(F.normalizeManifest(data)));", raw)
                self.assertEqual(out["problems"], [])
                self.assertEqual(len(out["figures"]), len(raw["figures"]))

    def test_check_site_finds_nothing_to_say_about_the_figures(self):
        report = cs.run_checks(ROOT, allow=cs.load_allow(cs.DEFAULT_ALLOW))
        self.assertEqual([], [str(f) for f in report.findings if f.code.startswith("figure-") or f.file.startswith("content/figures/")])

    def test_every_after_is_a_heading_of_its_chapter(self):
        """Independent of check_site: read the chapter with list_headings (the same headings reader.js sees)."""
        import list_headings
        chapters = chapter_ids()
        headings_of = getattr(list_headings, "headings_of", None) or list_headings.headings
        for p in manifests():
            heads = {h["id"] for h in headings_of(ROOT / chapters[p.stem]["url"])}
            for f in load_json(p)["figures"]:
                self.assertIn(f["after"], heads, f"{p.name}: figure {f['id']} follows a heading that is not in the chapter")

    def test_figure_ids_are_unique_per_chapter_and_the_anchor_is_free(self):
        chapters = chapter_ids()
        for p in manifests():
            ids = [f["id"] for f in load_json(p)["figures"]]
            self.assertEqual(len(ids), len(set(ids)), p.name)
            html = (ROOT / chapters[p.stem]["url"]).read_text(encoding="utf-8")
            for i in ids:
                self.assertNotIn(f'id="fig-{i}"', html)

    def test_alt_text_says_something(self):
        for p in manifests():
            for f in load_json(p)["figures"]:
                self.assertGreaterEqual(len(f.get("alt", "")), 60, f"{p.name}/{f['id']}: write an alt that describes the figure")
                self.assertNotEqual(f["alt"].strip(), f["caption"].strip(), f"{p.name}/{f['id']}: alt and caption should differ")

    def test_archify_sizes_are_the_viewbox_of_the_diagram(self):
        """figures.js sizes the frame from `size`, so a wrong number means a page that jumps or a clipped diagram."""
        checked = 0
        for p in manifests():
            for f in load_json(p)["figures"]:
                if f["type"] != "archify":
                    continue
                self.assertTrue((ROOT / f["src"]).is_file(), f["src"])
                head = (ROOT / f["src"]).read_text(encoding="utf-8")
                m = re.search(r'<svg viewBox="0 0 (\d+) (\d+)"', head)
                self.assertIsNotNone(m, f["src"])
                self.assertEqual(f["size"], [int(m.group(1)), int(m.group(2))], f"{p.name}/{f['id']}: size does not match {f['src']}")
                checked += 1
        self.assertGreaterEqual(checked, 4)          # P26 replaces the derived ones (system, api-surface) with arch figures; the flow ones follow when their flow is written

    def test_every_archify_page_supports_embed_and_theme(self):
        for p in manifests():
            for f in load_json(p)["figures"]:
                if f["type"] == "archify":
                    text = (ROOT / f["src"]).read_text(encoding="utf-8")
                    self.assertIn("get('embed') === '1'", text, f["src"])
                    self.assertIn("get('theme')", text, f["src"])

    def test_the_hand_authored_svgs_are_safe_well_formed_and_use_only_tokens(self):
        tokens = set(re.findall(r"(--[a-z0-9-]+)\s*:", (ROOT / "assets" / "css" / "tokens.css").read_text(encoding="utf-8")))
        svgs = sorted((FIG_DIR / "svg").glob("*.svg"))
        self.assertGreaterEqual(len(svgs), 2)
        for s in svgs:
            text = s.read_text(encoding="utf-8")
            with self.subTest(s.name):
                self.assertIsNone(cs.svg_problem(text))
                ET.fromstring(text.encode("utf-8"))
                self.assertIn("viewBox", text)
                self.assertNotIn("\r", text, "keep LF line endings")
                used = set(re.findall(r"var\((--[a-z0-9-]+)", text))
                self.assertTrue(used)
                self.assertEqual(used - tokens, set(), "a colour token that tokens.css does not define")
                self.assertIsNone(re.search(r"(?<![\w(&])#[0-9a-fA-F]{3,8}\b", text), "raw colour: use a token, so both themes work")
                self.assertNotRegex(text, r'\b(?:width|height)="\d')       # figures.js sizes it from the viewBox


# ---------------------------------------------------------------- the stylesheet
class Stylesheet(unittest.TestCase):
    css = FIGURES_CSS.read_text(encoding="utf-8")

    @staticmethod
    def without_print(css: str) -> str:
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)          # the header comment itself mentions "@media print"
        i = css.find("@media print")
        if i < 0:
            return css
        j, d = css.find("{", i), 0
        for k in range(j, len(css)):
            d += {"{": 1, "}": -1}.get(css[k], 0)
            if d == 0:
                return css[:i] + css[k + 1:]
        return css[:i]

    def test_every_rule_belongs_to_a_figure_or_the_viewer(self):
        for sel in trd.Stylesheet.selectors(self.css):
            for part in trd.Stylesheet.split_top(sel):
                self.assertTrue(".fg" in part or ".mm-lb" in part, f"unscoped selector: {part}")

    def test_the_tokens_it_uses_exist(self):
        have = set()
        for name in ("tokens.css", "reader.css", "components.css"):
            have |= set(re.findall(r"(--[a-z0-9-]+)\s*:", (ROOT / "assets" / "css" / name).read_text(encoding="utf-8")))
        local = {"--fig-r", "--fig-w", "--fig-h", "--fig-pad"}            # set on the frame by figures.js
        used = set(re.findall(r"var\((--[a-z0-9-]+)", self.css))
        self.assertEqual(used - have - local, set())

    def test_no_raw_colours_outside_print(self):
        body = re.sub(r"/\*.*?\*/", "", self.without_print(self.css), flags=re.S)
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", body), [])

    def test_important_is_only_for_print(self):
        self.assertNotIn("!important", self.without_print(self.css))

    def test_the_viewer_sits_between_the_drawer_and_the_palette(self):
        z = int(re.search(r"\.mm-lb \{[^}]*z-index:\s*(\d+)", self.css).group(1))
        palette = (ROOT / "assets" / "css" / "shell.css").read_text(encoding="utf-8") + (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
        self.assertGreater(z, 1003)
        zs = [int(n) for n in re.findall(r"\.mmp-backdrop[^{]*\{[^}]*z-index:\s*(\d+)", palette)]
        if zs:
            self.assertLess(z, min(zs))


# ---------------------------------------------------------------- wiring
class Wiring(unittest.TestCase):
    def test_shell_loads_the_figures_after_the_reader_and_never_statically(self):
        s = SHELL_JS.read_text(encoding="utf-8")
        self.assertRegex(s, r'import\("\./reader\.js"\)[\s\S]*?import\("\./figures\.js"\)[\s\S]*?initFigures\(\{ navReady \}\)')
        self.assertNotRegex(s, r"^import .*figures\.js", re.M)
        self.assertRegex(s, r"function boot\(\)[\s\S]*?load\(\);\s*loadReader\(\);")      # P04's own test relies on this too

    def test_a_failing_reader_does_not_stop_the_figures(self):
        s = SHELL_JS.read_text(encoding="utf-8")
        i = s.index('import("./reader.js")')
        chain = s[i:s.index("}", i)]
        self.assertLess(chain.index('console.warn("[atlas reader]"'), chain.index('import("./figures.js")'))

    def test_figures_js_has_no_dependencies_and_never_leaves_the_site(self):
        s = FIGURES_JS.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^import\s", s, re.M), [])
        self.assertNotIn("http://", s)
        self.assertNotIn("https://", s)
        self.assertNotRegex(s, r"\beval\(|new Function\(")

    def test_figures_js_exports_what_the_tests_use(self):
        s = FIGURES_JS.read_text(encoding="utf-8")
        for name in ("initFigures", "normalizeManifest", "svgLooksSafe", "withSemanticClasses", "mermaidThemeVariables", "MERMAID_SRC"):
            self.assertRegex(s, rf"export (?:async )?(?:function|const) {name}\b")

    def test_mermaid_path_matches_the_vendor_script(self):
        s = FIGURES_JS.read_text(encoding="utf-8")
        path = re.search(r'MERMAID_SRC = "([^"]+)"', s).group(1)
        self.assertEqual(path, vendor_mermaid.DEST.relative_to(ROOT).as_posix() + "/mermaid.min.js")
        self.assertEqual(path, cs.MERMAID_VENDOR)

    def test_the_standard_run_includes_these_tests(self):
        self.assertIn("scripts/test_figures.py", (ROOT / "scripts" / "update_all.py").read_text(encoding="utf-8"))

    def test_chapter_bodies_are_untouched_by_this_patch(self):
        """P06 must not edit doc-*.html: they are rebuilt by an external builder. Only checks when git is available."""
        if not shutil.which("git") or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        r = subprocess.run(["git", "status", "--porcelain", "--", "doc-*.html"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.stdout.strip(), "", "a chapter page has uncommitted changes")


class VendorScript(unittest.TestCase):
    def test_the_pin_is_well_formed(self):
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", vendor_mermaid.VERSION))
        self.assertIn(f"mermaid-{vendor_mermaid.VERSION}.tgz", vendor_mermaid.TARBALL_URL)
        self.assertTrue(vendor_mermaid.TARBALL_URL.startswith("https://registry.npmjs.org/mermaid/-/"))
        self.assertRegex(vendor_mermaid.TARBALL_INTEGRITY, r"^sha512-[A-Za-z0-9+/]{86}==$")
        self.assertRegex(vendor_mermaid.MIN_SHA256, r"^[0-9a-f]{64}$")

    def test_hashing_ignores_windows_line_endings(self):
        self.assertEqual(vendor_mermaid.sha256_lf(b"a\r\nb\n"), vendor_mermaid.sha256_lf(b"a\nb\n"))

    def test_integrity_has_npms_shape(self):
        # the sha512 of the empty string, base64: what `npm view` would print for an empty tarball
        self.assertEqual(vendor_mermaid.npm_integrity(b""), "sha512-z4PhNX7vuL3xVChQ1m2AB9Yg5AULVxXcg/SpIdNs6c5H0NE8XYXysP+DGNKHfuwvY7kxvUdBeoGlODJ6+SfaPg==")

    def test_a_vendored_copy_if_present_is_the_pinned_one(self):
        if not (vendor_mermaid.DEST / "mermaid.min.js").is_file():
            self.skipTest("Mermaid is not vendored (only needed once a manifest has a mermaid figure)")
        self.assertEqual(vendor_mermaid.check(), 0)

    def test_the_vendored_copy_exists_whenever_a_manifest_needs_it(self):
        needs = [p.name for p in manifests() if any(f["type"] == "mermaid" for f in load_json(p)["figures"])]
        if needs:
            self.assertTrue((vendor_mermaid.DEST / "mermaid.min.js").is_file(), f"{needs} use mermaid: run python scripts/vendor_mermaid.py")


# ---------------------------------------------------------------- check_site's figure rules, one at a time
class CheckSiteFigureRules(tcs.SiteCase):
    NAV = json.dumps({"wings": [{"id": "w", "title": "W", "items": [
        {"id": "docs", "title": "Library", "url": "docs.html"},
        {"id": "doc-a", "title": "A", "url": "doc-a.html", "chapter": 1}]}]})
    SVG = '<svg viewBox="0 0 10 10"><rect width="4" height="4"/></svg>'

    def files(self, figures=None, extra=None, raw=None):
        f = {
            "docs.html": tcs.page("Library - MiniMe Atlas"),
            "doc-a.html": tcs.page("A - MiniMe Atlas", "<h2 id='intro'>Intro</h2><p>x</p><h2 id='next'>Next</h2>"),
            "architecture/x.html": "<html></html>",
            "content/nav.json": self.NAV,
            "content/figures/svg/a.svg": self.SVG,
        }
        if figures is not None:
            f["content/figures/doc-a.json"] = json.dumps({"figures": figures})
        if raw is not None:
            f["content/figures/doc-a.json"] = raw
        f.update(extra or {})
        return f

    def run_site(self, **kw):
        return self.site(self.files(**kw)).check()

    @staticmethod
    def fig(**kw):
        base = {"id": "one", "after": "intro", "type": "svg", "src": "content/figures/svg/a.svg", "caption": "Caption", "alt": "What it shows"}
        base.update(kw)
        return {k: v for k, v in base.items() if v is not None}

    def test_a_good_manifest_passes(self):
        archify = self.fig(id="two", type="archify", src="architecture/x.html", size=[1200, 620])
        archify.pop("alt"); archify["alt"] = "A diagram"
        r = self.run_site(figures=[self.fig(), archify, self.fig(id="three", src=None, code=self.SVG, place="start", wide=True)])
        self.assertEqual([], self.codes(r))

    def test_no_figures_at_all_is_fine(self):
        self.assertEqual([], self.codes(self.run_site()))

    def test_each_mistake_has_its_own_error(self):
        cases = [
            (self.fig(alt=None), "figure-no-alt"),
            (self.fig(alt="  "), "figure-no-alt"),
            (self.fig(after="missing"), "figure-bad-heading"),
            (self.fig(after=None), "figure-bad-heading"),
            (self.fig(caption=None), "figure-bad-entry"),
            (self.fig(id="Bad Id"), "figure-bad-entry"),
            (self.fig(type="chart"), "figure-bad-entry"),
            (self.fig(type="gif"), "figure-bad-entry"),
            (self.fig(place="middle"), "figure-bad-entry"),
            (self.fig(wide="yes"), "figure-bad-entry"),
            (self.fig(src="content/figures/svg/gone.svg"), "figure-bad-src"),
            (self.fig(src="content/figures/svg/a.png"), "figure-bad-src"),
            (self.fig(src="content/figures/../nav.json"), "figure-bad-src"),
            (self.fig(src=None), "figure-bad-entry"),
            (self.fig(code=self.SVG), "figure-bad-entry"),
            (self.fig(src=None, code="<div/>"), "figure-bad-svg"),
            (self.fig(src=None, code="<svg><script/></svg>"), "figure-bad-svg"),
            (self.fig(src=None, code="<svg><g></svg>"), "figure-bad-svg"),
            (self.fig(type="archify", src="architecture/gone.html", size=[1200, 620]), "figure-bad-src"),
            (self.fig(type="archify", src="https://x.example/a.html", size=[1200, 620]), "figure-bad-src"),
            (self.fig(type="archify", src="architecture/x.html"), "figure-bad-entry"),
            (self.fig(type="archify", src="architecture/x.html", size=[5, 5]), "figure-bad-entry"),
            (self.fig(type="archify", src="architecture/x.html", size=[True, True]), "figure-bad-entry"),
            (self.fig(type="arch", src=None), "figure-bad-entry"),
            (self.fig(type="arch", src=None, view="Not A View"), "figure-bad-entry"),
            (self.fig(type="arch", src=None, view="system", flow="bad flow"), "figure-bad-entry"),
            ("a string", "figure-bad-entry"),
        ]
        for entry, code in cases:
            with self.subTest(entry=entry):
                self.assertIn(code, self.codes(self.run_site(figures=[entry]), "ERROR"))

    def test_duplicate_ids(self):
        self.assertIn("figure-bad-entry", self.codes(self.run_site(figures=[self.fig(), self.fig()]), "ERROR"))

    def test_the_anchor_must_be_free_on_the_page(self):
        page = tcs.page("A - MiniMe Atlas", "<h2 id='intro'>Intro</h2><div id='fig-one'></div>")
        r = self.site(self.files(figures=[self.fig()], extra={"doc-a.html": page})).check()
        self.assertEqual(["figure-bad-entry"], self.codes(r, "ERROR"))

    def test_a_manifest_for_a_page_that_is_not_a_chapter(self):
        files = self.files(figures=[self.fig()])
        files["content/figures/doc-zzz.json"] = files.pop("content/figures/doc-a.json")
        self.assertEqual(["figure-bad-manifest"], self.codes(self.site(files).check(), "ERROR"))

    def test_a_manifest_that_is_not_a_list(self):
        self.assertEqual(["figure-bad-manifest"], self.codes(self.run_site(raw='{"figures": 3}'), "ERROR"))
        self.assertEqual(["figure-bad-manifest"], self.codes(self.run_site(raw='"x"'), "ERROR"))
        self.assertEqual([], self.codes(self.run_site(raw=json.dumps([self.fig()])), "ERROR"))    # the bare list is accepted too

    def test_broken_json_is_reported_once_as_bad_json(self):
        self.assertEqual(["bad-json"], self.codes(self.run_site(raw="{nope"), "ERROR"))

    def test_an_unsafe_or_broken_svg_file_is_an_error_even_if_nothing_uses_it(self):
        for text in ('<svg><script>1</script></svg>', '<svg onload="x()"/>', '<svg><g></svg>', "not svg at all"):
            with self.subTest(text=text):
                r = self.site(self.files(extra={"content/figures/svg/bad.svg": text})).check()
                self.assertEqual(["figure-bad-svg"], self.codes(r, "ERROR"))

    def test_mermaid_needs_the_vendored_library(self):
        entry = self.fig(type="mermaid", src="content/figures/flow.mmd")
        files = self.files(figures=[entry], extra={"content/figures/flow.mmd": "flowchart LR\n A-->B"})
        self.assertEqual(["figure-bad-src"], self.codes(self.site(files).check(), "ERROR"))
        files["assets/vendor/mermaid/mermaid.min.js"] = "/* stand-in */"
        self.assertEqual([], self.codes(self.site(files).check()))

    def test_the_vendor_folder_is_outside_the_size_budget(self):
        files = self.files(extra={"assets/vendor/mermaid/mermaid.min.js": "x" * (700 * 1024)})
        self.assertEqual([], self.codes(self.site(files).check()))
        files = self.files(extra={"assets/other.js": "x" * (700 * 1024)})
        self.assertEqual(["big-file"], self.codes(self.site(files).check()))


if __name__ == "__main__":
    unittest.main(verbosity=1)
