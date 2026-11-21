#!/usr/bin/env python3
"""
Tests for scripts/check_site.py, scripts/serve.py and vercel.json. Standard library only.

    python scripts/test_check_site.py
    python -m unittest discover -s scripts

The first class runs the checker on the repo itself: the committed site must have no un-allowed errors.
The others build tiny sites in a temporary folder, so each rule is pinned on its own.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True      # scripts/__pycache__ is tracked; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = load("check_site")
serve = load("serve")


def page(title="Page - MiniMe Atlas", body="", head=""):
    return f'<!doctype html><html lang="en"><head><meta charset=utf-8><title>{title}</title>{head}</head><body><main>{body}</main></body></html>'


class Site:
    """A throwaway site: Site({'index.html': page(...), 'data/x.json': '{}'})."""

    def __init__(self, files):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, text in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))

    def close(self):
        self._tmp.cleanup()

    def check(self, allow_text=None, **kw):
        allow = []
        if allow_text is not None:
            f = self.root / "_allow.txt"
            f.write_text(allow_text, encoding="utf-8")
            allow = cs.load_allow(f)
        return cs.run_checks(self.root, allow=allow, **kw)


class SiteCase(unittest.TestCase):
    def site(self, files):
        s = Site(files)
        self.addCleanup(s.close)
        return s

    def codes(self, report, level=None, a11y=False):
        """a11y-* findings (P23) are left out unless asked for: older tests build bare pages on purpose."""
        return sorted(f.code for f in report.findings if level in (None, f.level) and (a11y or not f.code.startswith("a11y-")))


class RepoState(unittest.TestCase):
    def test_committed_site_has_no_unallowed_errors(self):
        report = cs.run_checks(ROOT, allow=cs.load_allow(cs.DEFAULT_ALLOW))
        self.assertEqual([], [str(f) for f in report.errors],
                         "fix the page, or (if it is a known issue) add a line to scripts/check_site.allow")

    def test_allow_file_has_no_dead_lines(self):
        report = cs.run_checks(ROOT, allow=cs.load_allow(cs.DEFAULT_ALLOW))
        self.assertEqual([], [f.detail for f in report.findings if f.code == "unused-allow"],
                         "these allow lines match nothing any more; delete them")


class Links(SiteCase):
    def test_clean_site_is_clean(self):
        s = self.site({
            "index.html": page("Home - MiniMe Atlas", '<a href="other.html">x</a><a href="other.html#sec">y</a><a href="#top">t</a>'),
            "other.html": page("Other - MiniMe Atlas", '<h2 id="sec">s</h2><img src="img/a.png" alt=""><link rel=stylesheet href="/css/a.css">'),
            "img/a.png": b"\x89PNG", "css/a.css": "a{}",
        })
        r = s.check()
        self.assertEqual([], [str(f) for f in r.findings])
        self.assertEqual(2, r.stats["pages"])

    def test_broken_link_and_src(self):
        s = self.site({"index.html": page(body='<a href="nope.html">x</a><script src="a/missing.js"></script>')})
        r = s.check()
        self.assertEqual(["broken-link", "broken-link"], self.codes(r, "ERROR"))
        self.assertEqual(1, r.exit_code())

    def test_repeated_broken_link_is_reported_once_with_a_count(self):
        s = self.site({"index.html": page(body='<a href="nope.html">1</a><a href="nope.html">2</a><a href="nope.html">3</a>')})
        f = s.check().errors
        self.assertEqual(1, len(f))
        self.assertIn("(x3)", f[0].message)

    def test_link_is_case_exact_because_vercel_is_case_sensitive(self):
        s = self.site({"index.html": page(body='<a href="Other.html">x</a>'), "other.html": page()})
        r = s.check()
        self.assertEqual(["broken-link"], self.codes(r, "ERROR"))
        self.assertIn("case differs", r.errors[0].message)

    def test_relative_to_the_page_folder_and_parent_folder(self):
        s = self.site({
            "index.html": page(), "top.html": page("Top - X"),
            "guides/g.html": page("G - X", '<a href="../top.html">up</a><a href="h.html">side</a>'),
            "guides/h.html": page("H - X"),
        })
        self.assertEqual([], self.codes(s.check()))

    def test_escaping_the_site_root_is_broken(self):
        s = self.site({"index.html": page(body='<a href="../../etc/passwd">x</a>')})
        self.assertEqual(["broken-link"], self.codes(s.check(), "ERROR"))

    def test_external_and_special_schemes_and_templates_are_ignored(self):
        body = ('<a href="https://example.com/x">1</a><a href="//cdn.example.com/y">2</a><a href="mailto:a@b.c">3</a>'
                '<a href="vscode://file/C:/x">4</a><a href="javascript:void(0)">5</a><a href="data:text/plain,hi">6</a>'
                '<a href="${row.url}">7</a><a href="">8</a><a href="#">9</a>')
        self.assertEqual([], self.codes(self.site({"index.html": page(body=body)}).check()))

    def test_urls_are_decoded_and_query_strings_dropped(self):
        s = self.site({"index.html": page(body='<a href="my%20page.html?x=1#a">x</a>'), "my page.html": page("M - X", '<i id="a"></i>')})
        self.assertEqual([], self.codes(s.check()))

    def test_directory_links_need_an_index(self):
        s = self.site({"index.html": page(body='<a href="guides/">a</a><a href="empty/">b</a>'),
                       "guides/index.html": page("G - X"), "empty/x.txt": "x"})
        r = s.check()
        self.assertEqual(["broken-link"], self.codes(r, "ERROR"))
        self.assertIn("empty/", r.errors[0].detail)

    def test_links_inside_script_and_style_are_not_scanned(self):
        body = '<script>var s = \'<a href="ghost.html">x</a>\';</script><style>a{background:url(ghost.png)}</style>'
        self.assertEqual([], self.codes(self.site({"index.html": page(body=body)}).check()))


class Anchors(SiteCase):
    def test_missing_anchor_on_other_page(self):
        s = self.site({"index.html": page(body='<a href="b.html#nope">x</a>'), "b.html": page("B - X", '<h2 id="yes">h</h2>')})
        self.assertEqual(["broken-anchor"], self.codes(s.check(), "ERROR"))

    def test_missing_anchor_on_same_page(self):
        s = self.site({"index.html": page(body='<a href="#nope">x</a><a href="#here">y</a><i id="here"></i>')})
        r = s.check()
        self.assertEqual(["broken-anchor"], self.codes(r, "ERROR"))
        self.assertIn("nope", r.errors[0].detail)

    def test_named_anchor_and_top_are_valid(self):
        s = self.site({"index.html": page(body='<a href="#top">t</a><a href="b.html#old">o</a>'), "b.html": page("B - X", '<a name="old"></a>')})
        self.assertEqual([], self.codes(s.check()))

    def test_id_built_inside_a_javascript_string_counts(self):
        # journey.html writes ids as id=\"doc-x\" inside a JS string
        js = '<script>const h = "<div id=\\"doc-x\\">";</script>'
        s = self.site({"index.html": page(body='<a href="j.html#doc-x">x</a>'), "j.html": page("J - X", js)})
        self.assertEqual([], self.codes(s.check()))

    def test_client_side_routes_are_not_checked(self):
        s = self.site({"index.html": page(body='<a href="e.html#/f/backend/a.py@10-20">x</a><a href="e.html#!x">y</a>'), "e.html": page("E - X")})
        self.assertEqual([], self.codes(s.check()))

    def test_anchor_into_a_skipped_page_still_resolves(self):
        s = self.site({"index.html": page(body='<a href="architecture/a.html#n1">x</a><a href="architecture/a.html#n9">y</a>'),
                       "architecture/a.html": page("A - X", '<g id="n1"></g>')})
        r = s.check()
        self.assertEqual(["broken-anchor"], self.codes(r, "ERROR"))
        self.assertIn("n9", r.errors[0].detail)


class Titles(SiteCase):
    def test_missing_and_empty_title(self):
        s = self.site({"index.html": "<html><body>x</body></html>", "b.html": page(title="   ")})
        self.assertEqual(["no-title", "no-title"], self.codes(s.check(), "ERROR"))

    def test_title_that_repeats_itself(self):
        s = self.site({"index.html": page(title="MiniMe Atlas - MiniMe Atlas"), "b.html": page(title="Overview \u00b7 MiniMe Atlas")})
        r = s.check()
        self.assertEqual(["dup-title-part"], self.codes(r, "ERROR"))
        self.assertEqual("index.html", r.errors[0].file)

    def test_hyphen_inside_a_word_is_not_a_separator(self):
        self.assertEqual([], self.codes(self.site({"index.html": page(title="Tech-A - Tech-B - MiniMe Atlas")}).check()))

    def test_svg_title_is_not_the_page_title(self):
        s = self.site({"index.html": '<html><head></head><body><svg><title>icon</title></svg></body></html>'})
        self.assertEqual(["no-title"], self.codes(s.check(), "ERROR"))

    def test_identical_titles_on_two_pages_warn(self):
        s = self.site({"index.html": page("Same - X"), "b.html": page("Same - X")})
        r = s.check()
        self.assertEqual(["dup-title"], self.codes(r, "WARN"))
        self.assertEqual(0, r.exit_code())
        self.assertEqual(1, r.exit_code(strict=True))


class JsonAndSize(SiteCase):
    def test_bad_json(self):
        s = self.site({"index.html": page(), "data/a.json": '{"a": 1,}', "data/ok.json": '{"a": 1}'})
        r = s.check()
        self.assertEqual(["bad-json"], self.codes(r, "ERROR"))
        self.assertEqual("data/a.json", r.errors[0].file)

    def test_json_with_bom_is_fine(self):
        s = self.site({"index.html": page(), "data/a.json": b'\xef\xbb\xbf{"a": 1}'})
        self.assertEqual([], self.codes(s.check()))

    def test_big_file_is_only_a_warning(self):
        s = self.site({"index.html": page(), "data/big.bin": b"x" * 3000})
        r = s.check(max_size_kb=2)
        self.assertEqual(["big-file"], self.codes(r, "WARN"))
        self.assertEqual(0, r.exit_code())

    def test_non_utf8_page_is_an_error_not_a_crash(self):
        s = self.site({"index.html": page(), "b.html": b"<title>x</title>\xff\xfe"})
        self.assertEqual(["read-error"], self.codes(s.check(), "ERROR"))


class Scope(SiteCase):
    def test_architecture_and_templates_are_skipped_unless_deep(self):
        s = self.site({"index.html": page(), "architecture/a.html": "<html>no title <a href=nope.html>x</a></html>",
                       "scripts/t.html": "<html>template <a href=nope.html>x</a></html>", "guides/g.html": page("G - X")})
        r = s.check()
        self.assertEqual([], self.codes(r))
        self.assertEqual(2, r.stats["pages"])
        self.assertEqual(2, r.stats["skipped"])
        deep = s.check(deep=True)
        self.assertEqual(["broken-link", "no-title"], self.codes(deep, "ERROR"))   # architecture only; scripts/ stays out

    def test_hidden_and_vendor_folders_are_ignored(self):
        s = self.site({"index.html": page(), "node_modules/x/a.json": "{bad", ".git/x.json": "{bad"})
        self.assertEqual([], self.codes(s.check()))


class Navigation(SiteCase):
    def nav(self, urls):
        return json.dumps({"wings": [{"id": "w", "items": [{"id": u, "url": u} for u in urls]}]})

    def test_no_nav_file_means_no_nav_check(self):
        self.assertEqual([], self.codes(self.site({"index.html": page(), "b.html": page("B - X")}).check()))

    def test_page_missing_from_nav_and_dead_nav_url(self):
        s = self.site({"index.html": page(), "b.html": page("B - X"), "404.html": page("Gone - X"),
                       "content/nav.json": self.nav(["index.html", "ghost.html"])})
        r = s.check()
        self.assertEqual(["nav-dead-url", "not-in-nav"], self.codes(r, "ERROR"))
        self.assertEqual("b.html", [f for f in r.errors if f.code == "not-in-nav"][0].file)      # 404.html is exempt

    def test_nav_urls_may_carry_fragments_and_leading_slash(self):
        s = self.site({"index.html": page(), "b.html": page("B - X"), "content/nav.json": self.nav(["/index.html#x", "b.html"])})
        self.assertEqual([], self.codes(s.check()))


class GlossaryAndPaths(SiteCase):
    """content/glossary.json and content/reading-paths.json (P05): every target they point at must exist."""

    NAV = json.dumps({"wings": [{"id": "w", "title": "W", "items": [
        {"id": "docs", "title": "Library", "url": "docs.html"},
        {"id": "doc-a", "title": "A", "url": "doc-a.html", "chapter": 1}]}]})
    CENSUS = json.dumps({"files": [{"path": "backend/x.py", "functions": [{"name": "run", "qual": "Agent.run"}], "classes": [{"name": "Agent", "qual": "Agent"}]}]})

    def files(self, glossary=None, paths=None, census=True):
        f = {
            "docs.html": page("Library - MiniMe Atlas"),
            "doc-a.html": page("A - MiniMe Atlas", "<h2 id='intro'>Intro</h2>"),
            "content/nav.json": self.NAV,
        }
        if census:
            f["data/census.json"] = self.CENSUS
        if glossary is not None:
            f["content/glossary.json"] = json.dumps(glossary)
        if paths is not None:
            f["content/reading-paths.json"] = json.dumps(paths)
        return f

    def run_site(self, **kw):
        return self.site(self.files(**kw)).check()

    def test_a_good_glossary_and_paths_pass(self):
        r = self.run_site(
            glossary={"terms": [{"term": "Golden Rule", "short": "A rule.", "see": ["doc-a", "doc-a#intro", "backend/x.py", "backend/x.py::Agent.run"]}]},
            paths={"paths": [{"id": "p", "title": "P", "steps": [{"chapter": "doc-a", "heading": "intro"}, {"file": "backend/x.py", "qual": "Agent"}]}]})
        self.assertEqual([], self.codes(r))

    def test_see_targets_that_do_not_exist_are_errors(self):
        r = self.run_site(glossary=[{"term": "T", "short": "s", "see": ["doc-zzz", "doc-a#nope", "backend/gone.py", "backend/x.py::Agent.missing", ""]}])
        self.assertEqual(["glossary-bad-see"] * 5, self.codes(r, "ERROR"))

    def test_entries_need_a_term_and_a_short_definition(self):
        r = self.run_site(glossary=[{"short": "no name"}, {"term": "No short"}, {"term": "Bad", "short": "s", "match": "sometimes"}, "nonsense"])
        self.assertEqual(["glossary-bad-entry"] * 4, self.codes(r, "ERROR"))

    def test_two_terms_with_the_same_anchor_are_an_error(self):
        r = self.run_site(glossary=[{"term": "Work package", "short": "a"}, {"term": "work-package!", "short": "b"}])
        self.assertEqual(["glossary-dup-term"], self.codes(r, "ERROR"))

    def test_long_text_and_shared_aliases_only_warn(self):
        r = self.run_site(glossary=[{"term": "A", "short": "x" * 161, "long": "y" * 601, "aliases": ["shared"]}, {"term": "B", "short": "ok", "aliases": ["Shared"]}])
        self.assertEqual([], self.codes(r, "ERROR"))
        self.assertEqual(["glossary-dup-alias", "glossary-long", "glossary-long"], self.codes(r, "WARN"))

    def test_without_a_census_code_targets_are_not_judged(self):
        r = self.run_site(glossary=[{"term": "T", "short": "s", "see": ["backend/anything.py::x"]}], census=False)
        self.assertEqual([], self.codes(r))

    def test_reading_path_problems(self):
        r = self.run_site(paths={"paths": [
            {"id": "p", "title": "P", "steps": [{"chapter": "doc-a", "heading": "nope"}, {"file": "backend/gone.py"}, {"chapter": "doc-a", "file": "x"}, {}]},
            {"id": "p", "title": "Dup", "steps": [{"chapter": "doc-a"}]},
            {"id": "empty", "title": "Empty", "steps": []},
            {"title": "No id"},
        ]})
        self.assertEqual(["path-bad-entry"] * 5 + ["path-bad-target"] * 2, self.codes(r, "ERROR"))

    def test_nothing_to_check_without_the_files(self):
        self.assertEqual([], self.codes(self.run_site()))

    def test_the_committed_glossary_and_paths_are_clean(self):
        report = cs.run_checks(ROOT, allow=cs.load_allow(cs.DEFAULT_ALLOW))
        bad = [str(f) for f in report.findings if f.code.startswith(("glossary", "path-"))]
        self.assertEqual([], bad)


class OverviewContent(SiteCase):
    """content/subsystems.json, content/system/request-path.json, content/overview/vitals.json and index.html's data-fragment names (P07)."""

    NAV = json.dumps({"wings": [{"id": "w", "title": "W", "items": [
        {"id": "index", "title": "Overview", "url": "index.html"},
        {"id": "docs", "title": "Library", "url": "docs.html"},
        {"id": "doc-a", "title": "A", "url": "doc-a.html", "chapter": 1}]}]})
    CENSUS = json.dumps({"files": [{"path": "backend/x.py", "functions": [{"name": "run", "qual": "Agent.run"}], "classes": [{"name": "Agent", "qual": "Agent"}]},
                                   {"path": "daemon/d.py", "functions": []}]})
    GOOD_SUB = {"id": "eo", "name": "Orchestrator", "what": "Runs tasks.", "match": ["backend/"], "chapter": "doc-a#intro", "pages": ["docs"],
                "key_files": [{"path": "backend/x.py", "qual": "Agent.run"}, {"path": "backend/x.py"}]}
    GOOD_STEP = {"id": "s1", "title": "T", "what": "W", "chapter": "doc-a#intro", "diagram": "doc-a.html#intro", "gate": False, "code": [{"path": "backend/x.py", "qual": "Agent"}]}

    def run_site(self, subsystems=None, request=None, vitals=None, index=None, fragments=()):
        f = {"docs.html": page("Library - MiniMe Atlas"), "doc-a.html": page("A - MiniMe Atlas", "<h2 id='intro'>Intro</h2>"),
             "content/nav.json": self.NAV, "data/census.json": self.CENSUS}
        if subsystems is not None:
            f["content/subsystems.json"] = json.dumps({"subsystems": subsystems})
        if request is not None:
            f["content/system/request-path.json"] = json.dumps({"steps": request})
        if vitals is not None:
            f["content/overview/vitals.json"] = json.dumps({"vitals": vitals})
        if index is not None:
            f["index.html"] = page("Overview - MiniMe Atlas", index)
        for name in fragments:
            f[f"content/overview/{name}.html"] = "<p>x</p>"
        return self.site(f).check()

    def errors(self, r):
        return [(f.code, f.detail) for f in r.findings if f.level == "ERROR" and f.code.startswith("overview-")]

    def test_good_content_passes(self):
        r = self.run_site([self.GOOD_SUB], [self.GOOD_STEP], {"files": {"label": "Files", "href": "docs.html"}},
                          index='<div data-fragment="hero"></div><div data-fragment="abstract"></div>', fragments=("hero", "abstract"))
        self.assertEqual([], self.codes(r, "ERROR"))

    def test_subsystem_entries_need_an_id_a_name_text_and_a_match(self):
        bad = [{"name": "No id", "what": "w", "match": ["backend/"]},
               {"id": "other", "name": "Reserved", "what": "w", "match": ["daemon/"]},
               {"id": "Bad Id!", "name": "n", "what": "w", "match": ["daemon/"]},
               {"id": "a", "what": "no name", "match": ["daemon/d.py"]},
               {"id": "b", "name": "n", "what": " ", "match": ["backend/x.py"]},
               {"id": "c", "name": "n", "what": "w", "match": []},
               "nonsense"]
        r = self.run_site(bad)
        self.assertEqual(["overview-bad-entry"] * 7, sorted(c for c, _ in self.errors(r)))

    def test_two_subsystems_with_one_id_or_one_match_are_errors(self):
        r = self.run_site([self.GOOD_SUB, dict(self.GOOD_SUB, name="Again")])
        self.assertEqual(["overview-bad-entry"] * 1, [c for c, d in self.errors(r) if d == "eo"])
        r = self.run_site([self.GOOD_SUB, {"id": "two", "name": "Two", "what": "w", "match": ["backend/"]}])
        self.assertEqual([("overview-bad-entry", "two|backend/")], self.errors(r))

    def test_a_match_that_no_census_file_has_is_an_error_but_without_a_census_it_is_not_judged(self):
        r = self.run_site([dict(self.GOOD_SUB, match=["backend/", "gone/", "backend/gone.py"])])
        self.assertEqual([("overview-bad-target", "eo|gone/"), ("overview-bad-target", "eo|backend/gone.py")], self.errors(r))

    def test_subsystem_targets_that_do_not_exist_are_errors(self):
        sub = dict(self.GOOD_SUB, chapter="doc-zzz#x", pages=["docs", "doc-a", "ghost"],
                   key_files=[{"path": "backend/gone.py"}, {"path": "backend/x.py", "qual": "Agent.missing"}, {"qual": "no path"}, "nonsense"])
        r = self.run_site([sub])
        self.assertEqual(["overview-bad-target"] * 7, sorted(c for c, _ in self.errors(r)))
        self.assertIn(("overview-bad-target", "eo|doc-a"), self.errors(r), "a chapter is not an Atlas page: the page would silently vanish from the table")

    def test_request_path_steps_are_checked(self):
        bad = [dict(self.GOOD_STEP, id="a", title=""), dict(self.GOOD_STEP, id="b", gate="yes"), dict(self.GOOD_STEP, id="s1"),
               dict(self.GOOD_STEP, id="c", chapter="doc-a#nope", diagram="gone.html", code=[{"path": "backend/gone.py"}]), {"title": "no id"}]
        r = self.run_site(None, [self.GOOD_STEP] + bad)
        codes = sorted(c for c, _ in self.errors(r))
        self.assertEqual(["overview-bad-entry"] * 4 + ["overview-bad-target"] * 3, codes)

    def test_overview_vitals_copy_needs_a_label_and_a_link_that_exists(self):
        r = self.run_site(vitals={"files": {"label": "Files", "href": "gone.html"}, "routes": {"why": "no label"}, "ok": {"label": "OK", "href": "https://example.com/x"}})
        self.assertEqual([("overview-bad-entry", "routes"), ("overview-bad-target", "files|gone.html")], sorted(self.errors(r)),
                         "an https:// link is not looked up as a file")

    def test_a_data_fragment_without_its_file_is_an_error(self):
        r = self.run_site(index='<div data-fragment="hero"></div><div data-fragment="ghost"></div>', fragments=("hero",))
        self.assertEqual([("overview-bad-target", "ghost")], self.errors(r))

    def test_the_committed_overview_content_is_clean(self):
        report = cs.run_checks(ROOT, allow=cs.load_allow(cs.DEFAULT_ALLOW))
        self.assertEqual([], [str(f) for f in report.findings if f.code.startswith("overview-")])


class AllowList(SiteCase):
    FILES = {"index.html": page(body='<a href="nope.html">x</a><a href="e.html#abc.py">y</a>'), "e.html": page("E - X")}

    def test_exact_and_wildcard_lines_suppress(self):
        r = self.site(self.FILES).check("broken-link|index.html|nope.html   # reason\nbroken-anchor|index.html|e.html#*  # reason\n")
        self.assertEqual([], self.codes(r))
        self.assertEqual(2, len(r.allowed))
        self.assertEqual(0, r.exit_code())

    def test_comments_blank_lines_and_other_files_do_not_suppress(self):
        r = self.site(self.FILES).check("# broken-link|index.html|nope.html\n\nbroken-link|other.html|nope.html\n")
        self.assertEqual(["broken-anchor", "broken-link"], self.codes(r, "ERROR"))

    def test_a_line_that_matches_nothing_is_reported(self):
        r = self.site({"index.html": page()}).check("broken-link|index.html|gone.html  # old\n")
        self.assertEqual(["unused-allow"], self.codes(r, "WARN"))
        self.assertEqual(0, r.exit_code())

    def test_write_allow_prints_lines_that_round_trip(self):
        s = self.site(self.FILES)
        lines = [f"{f.key}  # t" for f in s.check().errors]
        self.assertEqual([], self.codes(s.check("\n".join(lines))))

    def test_hash_inside_a_key_is_not_a_comment(self):
        rules = Site({"a.txt": ""})            # only to get a folder; load_allow reads a path
        self.addCleanup(rules.close)
        p = rules.root / "allow.txt"
        p.write_text("broken-anchor|a.html|b.html#x   # why\n", encoding="utf-8")
        self.assertEqual(["broken-anchor|a.html|b.html#x"], [raw for raw, _ in cs.load_allow(p)])


class ArchModel(SiteCase):
    """P25: the architecture model's files and the pages that name its views and flows."""

    REG = {"flows": [{"id": "request-path", "title": "Request path", "kind": "sequence", "seeds": ["backend/main.py"]}],
           "views": [{"id": "system", "title": "System", "type": "layered", "source": "derived"}]}

    def arch_site(self, **over):
        files = {
            "index.html": page(body='<p>hi</p>'),
            "content/arch-flows.json": json.dumps(self.REG),
            "data/arch/views/system.json": "{}",
            "data/arch/model.json": json.dumps({"views": [{"id": "system"}]}),
            "data/index/paths.json": json.dumps({"paths": ["backend/main.py"]}),
        }
        files.update(over)
        return self.site(files)

    def acodes(self, site):
        return [c for c in self.codes(site.check()) if c.startswith("arch-")]

    def test_clean_and_absent(self):
        self.assertEqual(self.acodes(self.arch_site()), [])
        self.assertEqual(self.acodes(self.site({"index.html": page()})), [])

    def test_missing_shard_and_model_entry(self):
        s = self.arch_site(**{"data/arch/model.json": json.dumps({"views": []})})
        self.assertIn("arch-missing-data", self.acodes(s))
        reg = json.loads(json.dumps(self.REG))
        reg["views"].append({"id": "other", "title": "O", "type": "layered", "source": "derived"})
        s = self.arch_site(**{"content/arch-flows.json": json.dumps(reg)})
        self.assertIn("arch-missing-data", self.acodes(s))

    def test_bad_registry(self):
        reg = {"flows": [{"id": "Bad Id", "kind": "nope"}], "views": []}
        self.assertIn("arch-bad-registry", self.acodes(self.arch_site(**{"content/arch-flows.json": json.dumps(reg)})))

    def test_evidence_path_must_exist(self):
        flow = {"steps": [{"id": "s1", "evidence": [{"path": "backend/gone.py"}]}]}
        self.assertIn("arch-bad-evidence", self.acodes(self.arch_site(**{"data/arch/flows/request-path.json": json.dumps(flow)})))
        flow["steps"][0]["evidence"][0]["path"] = "backend/main.py"
        self.assertEqual(self.acodes(self.arch_site(**{"data/arch/flows/request-path.json": json.dumps(flow)})), [])

    def test_page_references(self):
        ok = page(body='<div data-arch-view="system" data-arch-flow="request-path"></div>')
        self.assertEqual(self.acodes(self.arch_site(**{"index.html": ok})), [])
        bad = page(body='<div data-arch-view="nope"></div><div data-arch-flow="nope"></div>')
        self.assertEqual(self.acodes(self.arch_site(**{"index.html": bad})).count("arch-bad-ref"), 2)


class Cli(SiteCase):
    def test_main_exit_codes(self):
        bad = self.site({"index.html": page(body='<a href="nope.html">x</a>')})
        good = self.site({"index.html": page()})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(1, cs.main(["--root", str(bad.root), "--no-allow"]))
            self.assertEqual(0, cs.main(["--root", str(good.root), "--no-allow"]))
            out.truncate(0), out.seek(0)
            self.assertEqual(0, cs.main(["--root", str(bad.root), "--no-allow", "--write-allow"]))
            self.assertIn("broken-link|index.html|nope.html", out.getvalue())


class ServeMime(unittest.TestCase):
    def test_types_the_site_needs_are_pinned(self):
        for name, want in [("a.js", "text/javascript"), ("a.mjs", "text/javascript"), ("a.json", "application/json"),
                           ("a.woff2", "font/woff2"), ("A.HTML", "text/html"), ("a.css", "text/css"), ("a.md", "text/markdown"),
                           ("a.svg", "image/svg+xml")]:
            self.assertTrue(serve.mime_for(name).startswith(want), name)

    def test_unknown_extension_is_binary(self):
        self.assertEqual("application/octet-stream", serve.mime_for("a.zzzzz"))


class ServeHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._log = serve.Handler.log_message
        serve.Handler.log_message = lambda *a, **k: None          # keep the test output readable
        cls.site = Site({"index.html": page("Home - X"), "a/b.json": '{"ok": true}', "m.mjs": "export const a = 1;",
                         "404.html": "<title>nope</title>custom 404", ".git/config": "secret", "ABOUT.html": page("About - X")})
        cls.server = serve.make_server(cls.site.root, "127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        serve.Handler.log_message = cls._log
        cls.server.shutdown()
        cls.server.server_close()
        cls.site.close()

    def get(self, path):
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5)
            return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_root_serves_index_and_never_caches(self):
        status, headers, body = self.get("/")
        self.assertEqual(200, status)
        self.assertIn(b"Home - X", body)
        self.assertEqual("no-store", headers["Cache-Control"])

    def test_json_and_module_types(self):
        self.assertTrue(self.get("/a/b.json")[1]["Content-Type"].startswith("application/json"))
        self.assertTrue(self.get("/m.mjs")[1]["Content-Type"].startswith("text/javascript"))

    def test_custom_404_and_git_folder_hidden(self):
        status, _, body = self.get("/missing.html")
        self.assertEqual(404, status)
        self.assertIn(b"custom 404", body)
        status, _, body = self.get("/.git/config")
        self.assertEqual(404, status)
        self.assertNotIn(b"secret", body)

    def test_urls_are_not_cleaned(self):
        self.assertEqual(200, self.get("/ABOUT.html")[0])
        self.assertEqual(404, self.get("/ABOUT")[0])


class VercelConfig(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    def header_for(self, source, key):
        for rule in self.cfg["headers"]:
            if rule["source"] == source:
                return {h["key"]: h["value"] for h in rule["headers"]}.get(key)

    def test_urls_are_not_rewritten(self):
        for key in ("cleanUrls", "trailingSlash", "rewrites", "redirects"):
            self.assertNotIn(key, self.cfg, f"{key} would change URLs; links and journey.html#doc-* depend on them")

    def test_noindex_everywhere(self):
        self.assertIn("noindex", self.header_for("/(.*)", "X-Robots-Tag"))

    def test_cache_rules(self):
        self.assertIn("s-maxage=300", self.header_for("/data/(.*)", "Cache-Control"))
        self.assertIn("immutable", self.header_for("/assets/fonts/(.*)", "Cache-Control"))
        for sub in ("css", "js", "vendor"):
            self.assertIn("max-age=3600", self.header_for(f"/assets/{sub}/(.*)", "Cache-Control"))

    def test_no_two_cache_rules_can_match_the_same_file(self):
        sources = [r["source"] for r in self.cfg["headers"] if any(h["key"] == "Cache-Control" for h in r["headers"])]
        prefixes = [s.split("(")[0] for s in sources]
        for i, a in enumerate(prefixes):
            for b in prefixes[i + 1:]:
                self.assertFalse(a.startswith(b) or b.startswith(a), f"{a} overlaps {b}: which Cache-Control wins is unspecified")


class WorkflowFile(unittest.TestCase):
    def test_site_check_workflow_runs_the_gate(self):
        text = (ROOT / ".github" / "workflows" / "site-check.yml").read_text(encoding="utf-8")
        for needle in ("scripts/check_site.py", "scripts/test_check_site.py", "scripts/test_refresh_atlas.py",
                       "scripts/test_refresh_graph.py", "pull_request", "contents: read"):
            self.assertIn(needle, text)
        self.assertNotIn("refresh_atlas.py\n", text.replace("test_refresh_atlas.py", ""))   # the refresh has its own workflow


class TestQualityChecks(SiteCase):
    """P23: HTML budgets, lazy vendors and the accessibility of the markup."""

    def errs(self, files, **kw):
        s = self.site(files)
        return self.codes(s.check(**kw), "ERROR", a11y=True)

    def test_a_clean_page_passes(self):
        self.assertEqual([], self.errs({"index.html": page(body='<label for="q">Q</label><input id="q" type="search"><button>Go</button><img src="a.png" alt="">'), "a.png": b"x"}))

    def test_budget_for_pages_and_chapters(self):
        big = page(body="x" * 210_000)
        self.assertEqual(["page-budget"], self.errs({"api.html": big}))
        s = self.site({"doc-x.html": page(body="x" * 310_000)})
        self.assertEqual([("WARN", "chapter-budget")], [(f.level, f.code) for f in s.check().findings])
        self.assertEqual([], self.errs({"api.html": big}, page_kb=300))

    def test_no_html_file_over_a_megabyte_even_when_generated(self):
        s = self.site({"index.html": page(), "architecture/x.html": page(body="x" * 1_100_000)})
        self.assertEqual(["page-too-big"], self.codes(s.check(), "ERROR", a11y=True))

    def test_big_page_can_be_allowed_with_a_reason(self):
        s = self.site({"api.html": page(body="x" * 210_000)})
        self.assertEqual([], self.codes(s.check("page-budget|api.html|-  # why"), "ERROR", a11y=True))

    def test_vendored_libraries_load_only_on_demand(self):
        head = '<script src="assets/vendor/mermaid/mermaid.min.js"></script>'
        files = {"index.html": page(head=head), "assets/vendor/mermaid/mermaid.min.js": "1"}
        self.assertEqual(["vendor-eager"], self.errs(files))
        js = {"index.html": page(), "assets/js/a.js": 'import hljs from "../vendor/highlight/h.js";\n', "assets/vendor/highlight/h.js": "1"}
        self.assertEqual(["vendor-eager"], self.errs(js))
        lazy = {"index.html": page(), "assets/js/a.js": 'const m = await import("../vendor/highlight/h.js");\n', "assets/vendor/highlight/h.js": "1"}
        self.assertEqual([], self.errs(lazy))

    def test_markup_rules(self):
        bare = "<!doctype html><html><head><title>T - MiniMe Atlas</title></head><body><h1>x</h1></body></html>"
        self.assertEqual(["a11y-lang", "a11y-no-main"], self.errs({"index.html": bare}))
        cases = {
            "a11y-img-alt": '<img src="a.png">',
            "a11y-input-label": '<input id="q" type="search">',
            "a11y-button-name": '<button></button>',
            "a11y-tabindex": '<div tabindex="3">x</div>',
            "a11y-dup-id": '<p id="a">1</p><p id="a">2</p>',
        }
        for code, body in cases.items():
            with self.subTest(code):
                self.assertEqual([code], self.errs({"index.html": page(body=body), "a.png": b"x"}))

    def test_things_that_do_name_a_control(self):
        ok = ('<label>Name <input type="text"></label><label for="b">B</label><input id="b">'
              '<input aria-label="C"><select title="D"></select><button aria-label="E"><svg></svg></button>'
              '<button><img src="a.png" alt="F"></button><button>Text</button><input type="hidden"><input type="file" hidden>'
              '<template><input><button></button><p id="t"></p><p id="t"></p></template>')
        self.assertEqual([], self.errs({"index.html": page(body=ok), "a.png": b"x"}))

    def test_repeated_style_ids_from_the_chapter_builder_are_not_duplicates(self):
        self.assertEqual([], self.errs({"index.html": page(head='<style id="s">a{}</style><style id="s">b{}</style>')}))


class RepoQuality(unittest.TestCase):
    def test_the_committed_site_meets_its_budgets_and_the_allow_list_has_reasons(self):
        report = cs.run_checks(ROOT, allow=cs.load_allow(cs.DEFAULT_ALLOW))
        self.assertEqual([], [str(f) for f in report.errors])
        text = cs.DEFAULT_ALLOW.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith(("page-budget|", "a11y-")):
                self.assertIn("#", line, f"allow line without a reason: {line}")


if __name__ == "__main__":
    unittest.main()
