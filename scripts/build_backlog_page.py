#!/usr/bin/env python3
"""
build_backlog_page.py -- build doc-upgrade-backlog.html (Appendix C, the upgrade backlog) from
data/docs/upgrade_backlog.md, so the reader page and the Markdown source cannot drift apart.

    python scripts/build_backlog_page.py --write     # build the page
    python scripts/build_backlog_page.py --check     # is the committed page what --write would build?

Needs one third-party package, only to build the page (not to check the backlog):

    pip install markdown==3.11.2

Why this exists
    The chapter pages (doc-*.html) of the book come from an external builder that this repository does not contain.
    That builder turns Markdown into HTML with Python-Markdown (extensions: tables, fenced_code, toc) and wraps every
    table in <div class="tw">. This script does the same for Appendix C and takes the page frame (the shared head with
    its CSS, and the shared script at the end) from an existing chapter page, so Appendix C looks like the others and
    follows them when their frame changes. Run against Appendix B's own source it reproduces that page exactly
    (see the note at the end of this docstring), which is how the recipe was checked.

How the checker knows the page is current
    The page ends with a comment holding the SHA-256 of the Markdown (line endings normalised to LF).
    `python scripts/check_backlog.py --check` compares it with the Markdown and needs only the standard library,
    so CI can enforce it without installing anything.

Not done here (the external builder does these for every chapter): the journey.html and tables.html aggregates.

Verification note: with the Appendix B inputs (its .md, its banner texts, its built date and commit) build_page() gives
the committed doc-provider-consolidation.html byte for byte. That was run once, by hand, when this script was written.
"""
import argparse
import datetime
import hashlib
import html
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # scripts/__pycache__ is tracked; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "docs" / "upgrade_backlog.md"
PAGE = ROOT / "doc-upgrade-backlog.html"
TEMPLATE = ROOT / "doc-provider-consolidation.html"       # any chapter page works; its head and tail are shared
SOURCE_REL = "data/docs/upgrade_backlog.md"

PART = "Appendix C · Upgrade backlog"
DESC = ("An incremental register of features to build later. Every feature has a source (a repository, a plan section or "
        "an idea of your own), one line in a generated top table, and a detailed entry: what it is, why, where in the "
        "code, how it would be added and when it counts as done. It grows by batches, and a script keeps its tables and "
        "this page in step with the entries.")
PREV_NEXT = ("doc-provider-consolidation.html", "Appendix B: Provider Consolidation Guide")
WORDS_PER_MINUTE = 220
TOC_MAX = 64
HASH_RE = re.compile(r"<!-- source: (\S+) sha256=([0-9a-f]{64}) -->")
BUILT_RE = re.compile(r'<small class="mm-built">Private\. Built (\d{4}-\d{2}-\d{2}) from commit ([0-9a-f]+)\.</small>')


def source_bytes(path):
    """The Markdown as bytes with CRLF turned into LF, so a Windows checkout hashes like the repository."""
    return Path(path).read_bytes().replace(b"\r\n", b"\n")


def source_sha256(path):
    return hashlib.sha256(source_bytes(path)).hexdigest()


def page_is_current(page, source, source_rel=SOURCE_REL):
    """Stdlib-only freshness test used by check_backlog.py. Returns (ok, message)."""
    page, source = Path(page), Path(source)
    if not page.exists():
        return True, "no page yet"
    m = HASH_RE.search(page.read_text(encoding="utf-8"))
    if not m:
        return False, f"{page.name} has no source hash; rebuild it with: python scripts/build_backlog_page.py --write"
    if m.group(2) != source_sha256(source):
        return False, (f"{page.name} was built from an older {source_rel}; rebuild it with: "
                       "python scripts/build_backlog_page.py --write (needs: pip install markdown==3.11.2)")
    return True, "current"


def _slug_text(tok):
    return html.unescape(tok["name"])


def render_article(md_text):
    """Markdown -> (article html, toc tokens), as the book's builder does it."""
    try:
        import markdown
    except ImportError:
        raise SystemExit("build_backlog_page: the 'markdown' package is needed to build the page. "
                         "Run: pip install markdown==3.11.2")
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"])
    out = md.convert(md_text)
    out = out.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
    return out, md.toc_tokens


def flatten(tokens):
    for t in tokens:
        yield t
        yield from flatten(t.get("children", []))


def toc_html(tokens):
    parts = ['<div class="toc"><b>On this page</b>']
    for t in flatten(tokens):
        if t["level"] not in (2, 3, 4):       # the builder lists h4 too, with the h3 style
            continue
        text = _slug_text(t)
        if len(text) > TOC_MAX:
            text = text[:TOC_MAX - 3] + "..."
        parts.append(f'<a class="t{min(t["level"], 3)}" href="#{t["id"]}">{html.escape(text)}</a>')
    parts.append("</div>")
    return "".join(parts)


def banner_html(part, desc, words, sections, tables, minutes, prev_next, download_href):
    nxt_href, nxt_text = prev_next
    return (
        '<div class="bk-banner">\n'
        '  <div class="bk-top">\n'
        '    <div>\n'
        f'      <span class="bk-part">{part}</span>\n'
        '      <span class="bk-ch">Not one of the 14 chapters</span>\n'
        '      <span class="bk-new">NEW</span>\n'
        '    </div>\n'
        '    <div class="bk-actions">\n'
        '      <a href="docs.html" class="bk-pill-link">📚 All 14 Chapters</a>\n'
        f'      <a href="{download_href}" download class="bk-pill-link">⬇ Download .md</a>\n'
        '    </div>\n'
        '  </div>\n'
        f'  <p class="bk-desc">{desc}</p>\n'
        '  <div class="bk-meta">\n'
        f'    <span><b>{words:,}</b> words (~{minutes} min read)</span><span>·</span>'
        f'<span><b>{sections}</b> sections</span><span>·</span><span><b>{tables}</b> tables</span>\n'
        '  </div>\n'
        f'  <div class="bk-prevnext"><a href="docs.html" class="bk-nav-btn">← Back to the book</a>'
        f'<a href="{nxt_href}" class="bk-nav-btn bk-next">{nxt_text} →</a></div>\n'
        '</div>'
    )


def build_page(md_text, template_html, *, part=PART, desc=DESC, prev_next=PREV_NEXT, appendix_label="Appendix C",
               download_href=SOURCE_REL, page_id="doc-upgrade-backlog", built=None, commit=None, source_hash=None):
    """The full page as a string. `built` and `commit` are the two values of the footer; `source_hash` is optional
    (the committed Appendix C page carries it; reproducing another chapter's page leaves it out)."""
    md_text = md_text.replace("\r\n", "\n")
    article, tokens = render_article(md_text)
    title_m = re.match(r"# (.+)", md_text)
    if not title_m:
        raise SystemExit("build_backlog_page: the Markdown must start with a '# Title' line")
    title = html.escape(title_m.group(1).strip(), quote=False)
    words = len(md_text.split())
    sections = len(re.findall(r"<h[234][ >]", article))
    tables = article.count("<table>")
    minutes = max(1, round(words / WORDS_PER_MINUTE))

    head_end = template_html.index("</head>")
    head = re.sub(r"<title>.*?</title>", f"<title>{title} · MiniMe Atlas</title>", template_html[:head_end], count=1, flags=re.S)
    tail_start = template_html.index('<script id="bk-chapter-script">')
    tail = template_html[tail_start:]
    if source_hash:
        tail = tail.replace("</body></html>", f"<!-- source: {SOURCE_REL} sha256={source_hash} -->\n</body></html>", 1)

    body = (
        f'</head><body data-page="{page_id}"><main><h1>{title}</h1>'
        f'<p class="sub">{appendix_label}. {words:,} words. <a href="{download_href}" download>Download .md</a></p>'
        + banner_html(part, desc, words, sections, tables, minutes, prev_next, download_href)
        + f'<div class="doc"><article>{article}</article>{toc_html(tokens)}</div></main>'
        f'<small class="mm-built">Private. Built {built} from commit {commit}.</small>'
    )
    return head + body + tail


def git_head(root=ROOT):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, timeout=20)
        h = r.stdout.strip()
        return h if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{4,40}", h) else None
    except (OSError, subprocess.SubprocessError):
        return None


def build_for_repo(built=None, commit=None):
    template = TEMPLATE.read_text(encoding="utf-8")
    return build_page(source_bytes(SOURCE).decode("utf-8"), template, built=built, commit=commit,
                      source_hash=source_sha256(SOURCE))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build doc-upgrade-backlog.html from data/docs/upgrade_backlog.md.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="build the page")
    mode.add_argument("--check", action="store_true", help="exit 1 when the committed page is not what --write would build")
    ap.add_argument("--built", help="footer date, YYYY-MM-DD (default: today; with --check: the date in the page)")
    ap.add_argument("--commit", help="footer commit (default: git HEAD; with --check: the commit in the page)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.check:
        if not PAGE.exists():
            print(f"build_backlog_page: {PAGE.name} does not exist; run with --write")
            return 1
        old = PAGE.read_bytes().decode("utf-8")
        m = BUILT_RE.search(old)
        if not m:
            print("build_backlog_page: the page has no 'Built ... from commit ...' footer")
            return 1
        new = build_for_repo(m.group(1), m.group(2))
        if new != old:
            print(f"build_backlog_page: {PAGE.name} is not what the current source builds; run: python scripts/build_backlog_page.py --write")
            return 1
        print(f"build_backlog_page: {PAGE.name} is current")
        return 0

    built = args.built or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(built)
    except ValueError:
        print(f"build_backlog_page: '{built}' is not a date (YYYY-MM-DD)")
        return 1
    commit = args.commit or git_head() or "0000000"
    if not re.fullmatch(r"[0-9a-f]{4,40}", commit):
        print(f"build_backlog_page: '{commit}' is not a commit id")
        return 1
    page = build_for_repo(built, commit)
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"build_backlog_page: wrote {PAGE.name} ({len(page.encode('utf-8')) // 1024} KB), built {built} from commit {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
