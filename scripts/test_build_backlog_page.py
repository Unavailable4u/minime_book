#!/usr/bin/env python3
"""
Tests for scripts/build_backlog_page.py (the reader page of Appendix C). Standard library only, except that the tests
marked "needs markdown" are skipped, with a message, when the `markdown` package is not installed:

    pip install markdown==3.11.2
    python scripts/test_build_backlog_page.py

CI does not install that package. What CI enforces without it is the hash in the page, through check_backlog.py.
"""
import hashlib
import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True      # scripts/__pycache__ is tracked; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bp = load("build_backlog_page")
try:
    import markdown  # noqa: F401
    HAVE_MARKDOWN = True
except ImportError:
    HAVE_MARKDOWN = False
needs_markdown = unittest.skipUnless(HAVE_MARKDOWN, "needs markdown: pip install markdown==3.11.2")

TEMPLATE = ("<!doctype html><html><head><title>Old title · MiniMe Atlas</title><style>x{}</style></head><body>old</body>"
            '<script id="bk-chapter-script">\nalert(1)\n</script><script type="module" src="assets/js/shell.js"></script></body></html>')
MD = """# A Test Guide

Intro with `code`, **bold**, and an apostrophe's friend.

## 1. First part

| A | B |
|---|---|
| 1 | 2 |

### 1.1 Sub part

Text.

- one
- two

#### 1.1.1 Deep part

```bash
echo "hi"
```

## 2. Second part with a very long heading that must be cut for the table of contents list

End.
"""


def page(md=MD, **kw):
    args = dict(built="2026-11-25", commit="abc1234", source_hash="f" * 64)
    args.update(kw)
    return bp.build_page(md, TEMPLATE, **args)


class Hashing(unittest.TestCase):
    def test_crlf_and_lf_hash_the_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.md", Path(tmp) / "b.md"
            a.write_bytes(b"# T\n\ntext\n")
            b.write_bytes(b"# T\r\n\r\ntext\r\n")
            self.assertEqual(bp.source_sha256(a), bp.source_sha256(b))
            self.assertEqual(bp.source_sha256(a), hashlib.sha256(b"# T\n\ntext\n").hexdigest())

    def test_page_is_current_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, pg = Path(tmp) / "s.md", Path(tmp) / "p.html"
            src.write_bytes(b"# T\n")
            self.assertEqual(bp.page_is_current(pg, src), (True, "no page yet"))
            pg.write_text("<html></html>", encoding="utf-8")
            self.assertFalse(bp.page_is_current(pg, src)[0])
            pg.write_text(f"<!-- source: x sha256={bp.source_sha256(src)} -->", encoding="utf-8")
            self.assertTrue(bp.page_is_current(pg, src)[0])
            src.write_bytes(b"# T\nchanged\n")
            ok, message = bp.page_is_current(pg, src)
            self.assertFalse(ok)
            self.assertIn("build_backlog_page.py --write", message)


class Pieces(unittest.TestCase):
    def test_toc_html_levels_truncation_and_escaping(self):
        tokens = [
            {"level": 1, "name": "Title", "id": "title", "children": [
                {"level": 2, "name": "Alpha", "id": "alpha", "children": [
                    {"level": 3, "name": "It&#x27;s a &lt;b&gt;", "id": "its", "children": [
                        {"level": 4, "name": "Deep", "id": "deep", "children": []}]}]},
                {"level": 2, "name": "x" * 80, "id": "long", "children": []}]}]
        out = bp.toc_html(tokens)
        self.assertTrue(out.startswith('<div class="toc"><b>On this page</b>'))
        self.assertIn('<a class="t2" href="#alpha">Alpha</a>', out)
        self.assertIn('<a class="t3" href="#its">It&#x27;s a &lt;b&gt;</a>', out)
        self.assertIn('<a class="t3" href="#deep">Deep</a>', out)          # h4 uses the h3 style
        self.assertNotIn('href="#title"', out)                              # h1 is not listed
        self.assertIn("x" * 61 + "...", out)
        self.assertNotIn("x" * 62, out)

    def test_banner_has_the_numbers_and_links(self):
        b = bp.banner_html("Appendix C · X", "A description.", 12345, 7, 3, 56, ("doc-b.html", "Appendix B: B"), "data/docs/x.md")
        for piece in ("Appendix C · X", "A description.", "<b>12,345</b> words (~56 min read)", "<b>7</b> sections",
                      "<b>3</b> tables", 'href="doc-b.html" class="bk-nav-btn bk-next">Appendix B: B →', 'href="data/docs/x.md" download'):
            self.assertIn(piece, b)


@needs_markdown
class Rendering(unittest.TestCase):
    def test_page_frame_comes_from_the_template(self):
        p = page()
        self.assertIn("<style>x{}</style>", p)
        self.assertIn("<title>A Test Guide · MiniMe Atlas</title>", p)
        self.assertNotIn("Old title", p)
        self.assertIn('<body data-page="doc-upgrade-backlog">', p)
        self.assertTrue(p.endswith("</body></html>"))
        self.assertIn('<script id="bk-chapter-script">\nalert(1)\n</script>', p)

    def test_tables_are_wrapped_and_code_has_a_language(self):
        p = page()
        self.assertIn('<div class="tw"><table>', p)
        self.assertIn("</table></div>", p)
        self.assertIn('<pre><code class="language-bash">', p)

    def test_a_list_after_a_blank_line_is_a_list(self):
        self.assertIn("<ul>\n<li>one</li>\n<li>two</li>\n</ul>", page())

    def test_headings_get_slug_ids(self):
        p = page()
        self.assertIn('<h2 id="1-first-part">1. First part</h2>', p)
        self.assertIn('<h3 id="11-sub-part">1.1 Sub part</h3>', p)

    def test_counts_in_the_banner(self):
        p = page()
        words = len(MD.split())
        self.assertIn(f"<b>{words:,}</b> words", p)
        self.assertIn("<b>4</b> sections", p)       # 2 x h2, 1 x h3, 1 x h4
        self.assertIn("<b>1</b> tables", p)
        self.assertIn(f"Appendix C. {words:,} words.", p)

    def test_toc_is_after_the_article(self):
        p = page()
        self.assertIn("</article><div class=\"toc\"><b>On this page</b>", p)
        self.assertIn('<a class="t2" href="#1-first-part">1. First part</a>', p)
        self.assertIn('<a class="t3" href="#111-deep-part">1.1.1 Deep part</a>', p)
        m = re.search(r'<a class="t2" href="#2-second-part[^"]*">([^<]*)</a>', p)
        self.assertEqual(len(m.group(1)), 64)
        self.assertTrue(m.group(1).endswith("..."))
        self.assertTrue(m.group(1).startswith("2. Second part with a very long heading"))

    def test_footer_and_hash(self):
        p = page()
        self.assertIn('<small class="mm-built">Private. Built 2026-11-25 from commit abc1234.</small>', p)
        self.assertIn("<!-- source: data/docs/upgrade_backlog.md sha256=" + "f" * 64 + " -->", p)
        self.assertEqual(bp.BUILT_RE.search(p).groups(), ("2026-11-25", "abc1234"))
        self.assertNotIn("sha256=", page(source_hash=None))

    def test_the_build_is_deterministic(self):
        self.assertEqual(page(), page())

    def test_crlf_source_builds_the_same_page(self):
        self.assertEqual(page(MD), page(MD.replace("\n", "\r\n")))

    def test_a_missing_title_is_refused(self):
        with self.assertRaises(SystemExit):
            page("No title here\n")

    def test_the_committed_page_is_what_the_source_builds(self):
        old = bp.PAGE.read_text(encoding="utf-8")
        built, commit = bp.BUILT_RE.search(old).groups()
        self.assertEqual(bp.build_for_repo(built, commit), old,
                         "doc-upgrade-backlog.html is out of date: python scripts/build_backlog_page.py --write")


class Committed(unittest.TestCase):
    def test_the_committed_page_carries_the_hash_of_the_document(self):
        ok, message = bp.page_is_current(bp.PAGE, bp.SOURCE)
        self.assertTrue(ok, message)
        self.assertTrue(bp.PAGE.exists())

    def test_the_page_is_wired_into_the_book(self):
        import json
        nav = json.loads((ROOT / "content" / "nav.json").read_text(encoding="utf-8"))
        text = json.dumps(nav)
        self.assertIn('"doc-upgrade-backlog"', text)
        self.assertIn("doc-upgrade-backlog.html", (ROOT / "docs.html").read_text(encoding="utf-8"))
        self.assertTrue(re.search(r"doc-upgrade-backlog", (ROOT / "data" / "index" / "book.json").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
