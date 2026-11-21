#!/usr/bin/env python3
"""
codemod_shell.py -- move Atlas pages onto the shared shell (patch P02). Standard library only.

Before P02 every page carried its own copy of the sidebar <nav> and loaded atlas-ui.js. Now the sidebar,
top bar, breadcrumbs and palette are built once by assets/js/shell.js from content/nav.json. This script
rewrites the page *frame* to match, and nothing else:

    python scripts/codemod_shell.py                    # convert every page in place
    python scripts/codemod_shell.py --dry-run          # list the pages that would change, change nothing
    python scripts/codemod_shell.py --check            # same, and exit 1 if any page would change
    python scripts/codemod_shell.py --only api.html --only doc-rulebook     # file names or nav ids

It is idempotent: a converted page is left byte-for-byte alone, so running it twice changes nothing.
Run it again with --only <page> after adding a page to content/nav.json.

What it changes in a page (and only here):
    <html>    gets data-layout="reader|workbench|bare" from content/nav.json
    <head>    title becomes "<Page> · MiniMe Atlas"; the Google Fonts link goes (base.css self-hosts Sora);
              theme.js + the pre-paint sidebar snippet + a font preload go in right after the title;
              tokens/base/components/shell.css go in last, so they win over the page's old inline CSS
    <body>    gets data-page="<nav id>"; the page's <nav>...</nav> is removed; its "Built ... from commit ..."
              line is kept as <small class="mm-built"> right after </main> (the refresh scripts match that
              text on the nine generated pages, and the shell shows it in the sidebar footer)
    scripts   atlas-ui.js is replaced by assets/js/shell.js (a module); pages that had no atlas-ui.js
              (the chapters) get the module tag just before </body>

P23 added three clean-up steps, all idempotent, so `--check` also tells you when a regenerated page needs the frame again:
    <body>    a page with no inline CSS of its own gets class="mm", so base.css (Sora, line height, focus ring, reduced motion)
              reaches it. (Before this, those pages were set in the browser's default Times.) A page that still carries
              its own inline CSS keeps its own typography: base.css would re-space its headings and paragraphs.
    <head>    a stale pre-paint snippet is replaced by the current one (the ?legacy=1 switch is gone)
    <style>   rules that only style the old per-page <nav>, the old mobile top bar and the old command box (all built by
              the retired atlas-ui.js) are dropped, and so is the old :root block (shell.css bridges those variables).
              Rules that style page content are never touched; an inline <style> left empty is removed.

What it never touches: anything inside <main>, the pages' own <script> blocks, any live page-content CSS, and the
pages that are not ordinary Atlas pages:
    * entries marked "hidden" in nav.json (styleguide.html is its own standalone showcase; graph-viewer.html is
      generated from scripts/graph_viewer_template.html by refresh_graph.py and is embedded as an iframe)
    * HTML that nav.json does not list (guides/*.html are exported source documents, architecture/*.html is archify output)
Line endings are preserved (CRLF checkouts stay CRLF), like the refresh scripts.

Safety: before a page is written the result is checked (one <main>, no <nav>, one shell tag, <main> byte-identical,
the same number of "Built ... from commit ..." stamps as before). A page that fails is reported and left alone.
"""
import argparse
import html as _html
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # the repo tracks scripts/__pycache__; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent
NAV_REL = "content/nav.json"
SUFFIX = "MiniMe Atlas"

_spec = importlib.util.spec_from_file_location("refresh_atlas", ROOT / "scripts" / "refresh_atlas.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)        # only for read_lf / to_native, so CRLF handling is identical to the refresh scripts

THEME_TAG = '<script src="assets/js/theme.js"></script>'
# Runs before first paint: picks the sidebar state so the page never flashes the wrong width.
# Same rule as assets/js/shell.js pickSidebar(): a saved choice wins; otherwise collapsed on workbench pages
# and below 1100px; always a drawer at 760px and below.
# (scripts/test_codemod_shell.py runs this exact text in node and compares it with shell.js.)
PREPAINT = ('<script data-mm="prepaint">(function(d,w){var r=d.documentElement,s=null,v=w.innerWidth;'
            'try{s=localStorage.getItem("minime_sidebar")}catch(e){}'
            'r.dataset.sidebar=v<=760?"drawer":s==="open"||s==="collapsed"?s:'
            'r.dataset.layout==="workbench"||v<1100?"collapsed":"open"})(document,window)</script>')
PRELOAD = ('<link rel="preload" href="assets/fonts/sora-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>')
CSS_TAGS = [f'<link rel="stylesheet" href="assets/css/{n}.css">' for n in ("tokens", "base", "components", "shell")]
SHELL_TAG = '<script type="module" src="assets/js/shell.js"></script>'
OLD_UI_TAG = '<script src="atlas-ui.js"></script>'      # only so a page that still has it can be converted; the file itself is gone (P23)
PREPAINT_RE = re.compile(r'<script data-mm="prepaint">.*?</script>', re.S)
STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>\n?", re.S)
# selectors that only ever styled elements atlas-ui.js built: the page's own <nav>, the mobile top bar (.m-*), the nav helpers
# (.nav-*) and the command box (.cmd-*). A rule is dropped only when EVERY selector in its list matches.
DEAD_SELECTOR = re.compile(r"^nav(?![\w-])|^\.nv$|\.m-[a-z]|^\.nav-[a-z]|^\.cmd-[a-z]|^body\.nav-open(?![\w-])")
BRIDGED_VARS = {"--bg", "--p", "--p2", "--ln", "--tx", "--dim", "--r", "--v", "--a", "--g", "--m"}
GOOGLE_FONTS = re.compile(r'\n?<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">')
BUILT = re.compile(r"Built \d{4}-\d{2}-\d{2} from commit [0-9a-f]+\.")
LAYOUTS = ("reader", "workbench", "bare")


class CodemodError(Exception):
    pass


# ------------------------------------------------------------------ nav.json
def load_nav(root):
    nav = json.loads(Path(root, NAV_REL).read_bytes().decode("utf-8-sig"))
    items = {}
    for wing in nav["wings"]:
        for it in wing["items"]:
            items[it["url"]] = dict(it, wing=wing["id"], hidden=False)
    for it in nav.get("hidden", []):
        items[it["url"]] = dict(it, wing=None, hidden=True)
    return nav, items


# ------------------------------------------------------------------ html helpers
def _set_attr(tag_html, name, value):
    """Return the opening tag with attribute `name` set to `value` (replaced if present, else appended)."""
    pat = re.compile(r'\s' + name + r'="[^"]*"')
    new = f' {name}="{value}"'
    if pat.search(tag_html):
        return pat.sub(lambda m: new, tag_html, count=1)
    return tag_html[:-1] + new + ">"


def _balanced_nav(html):
    """(start, end) of the first <nav>...</nav>, balancing nested <nav>; None if there is no <nav>."""
    m0 = re.search(r"<nav\b[^>]*>", html)
    if not m0:
        return None
    depth = 0
    for m in re.finditer(r"<nav\b[^>]*>|</nav>", html[m0.start():]):
        depth += 1 if m.group(0).startswith("<nav") else -1
        if depth == 0:
            return m0.start(), m0.start() + m.end()
    raise CodemodError("unbalanced <nav>")


# ------------------------------------------------------------------ dead inline CSS (P23)
def _split_rules(css):
    """Split CSS into top-level chunks [(leading_whitespace, prelude, body_or_None, tail)], honouring strings, comments
    and nested braces. A chunk is `prelude{body}`; a statement such as @import has body None."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = i
        while j < n and css[j].isspace():
            j += 1
        lead = css[i:j]
        if j >= n:
            out.append((lead, "", None))
            break
        k, depth, quote = j, 0, None
        body_start = None
        while k < n:
            c = css[k]
            if quote:
                if c == "\\":
                    k += 1
                elif c == quote:
                    quote = None
            elif css.startswith("/*", k):
                e = css.find("*/", k + 2)
                k = n if e < 0 else e + 1
            elif c in "\"'":
                quote = c
            elif c == "{":
                if depth == 0:
                    body_start = k
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            elif c == ";" and depth == 0:
                break
            k += 1
        if body_start is None:
            out.append((lead, css[j:k + 1], None))
        else:
            out.append((lead, css[j:body_start], css[body_start + 1:k]))
        i = k + 1
    return out


def _dead_rule(prelude, body):
    sels = [re.sub(r"\s+", " ", x.strip()) for x in prelude.split(",")]
    if sels and all(DEAD_SELECTOR.search(x) for x in sels):
        return True
    if [x for x in sels if x != ":root"] == [] and body is not None:      # the old :root colour block, bridged by shell.css
        names = {d.split(":")[0].strip() for d in body.split(";") if ":" in d}
        return bool(names) and names <= BRIDGED_VARS
    return False


def prune_css(css):
    """Drop the dead rules (inside @media / @supports too). Everything else is returned byte for byte."""
    kept = []
    for lead, prelude, body in _split_rules(css):
        if body is None:
            kept.append(lead + prelude)
            continue
        if prelude.lstrip().startswith("@"):
            if re.match(r"@(media|supports)\b", prelude.lstrip()):
                inner = prune_css(body)
                if not inner.strip():
                    continue
                kept.append(f"{lead}{prelude}{{{inner}}}")
            else:
                kept.append(f"{lead}{prelude}{{{body}}}")
            continue
        if _dead_rule(prelude, body):
            continue
        kept.append(f"{lead}{prelude}{{{body}}}")
    return "".join(kept)


def prune_styles(html):
    """Run prune_css over every inline <style>; remove a <style> that ends up empty."""
    def one(m):
        new = prune_css(m.group(1))
        if not new.strip():
            return ""
        return m.group(0) if new == m.group(1) else m.group(0).replace(m.group(1), new, 1)
    return STYLE_RE.sub(one, html)


def _add_class(tag_html, name):
    m = re.search(r'\sclass="([^"]*)"', tag_html)
    if not m:
        return tag_html[:-1] + f' class="{name}">'
    if name in m.group(1).split():
        return tag_html
    return tag_html[:m.start(1)] + (m.group(1) + " " + name).strip() + tag_html[m.end(1):]


def _main_block(html):
    a = html.find("<main")
    b = html.find("</main>")
    if a < 0 or b < 0 or html.count("<main") != 1:
        raise CodemodError("expected exactly one <main>...</main>")
    return html[a:b + len("</main>")]


def convert(html, item):
    """Return the page rewritten onto the shell. Idempotent. Raises CodemodError if the page is not shaped as expected."""
    if item["layout"] not in LAYOUTS:
        raise CodemodError(f"bad layout {item['layout']!r} in nav.json")
    out = html

    # <html data-layout>
    m = re.search(r"<html\b[^>]*>", out)
    if not m:
        raise CodemodError("no <html> tag")
    out = out[:m.start()] + _set_attr(m.group(0), "data-layout", item["layout"]) + out[m.end():]

    # <title> and the Google Fonts link
    title = f"{_html.escape(item['title'], quote=False)} · {SUFFIX}"
    out, n = re.subn(r"<title>.*?</title>", lambda _m: f"<title>{title}</title>", out, count=1, flags=re.S)
    if n != 1:
        raise CodemodError("no <title>")
    out = GOOGLE_FONTS.sub("", out)

    # head: theme + pre-paint + preload right after the title, shell CSS right before </head>
    if "assets/js/theme.js" not in out:
        out = out.replace("</title>", "</title>\n" + "\n".join((THEME_TAG, PREPAINT, PRELOAD)) + "\n", 1)
    out = PREPAINT_RE.sub(lambda _m: PREPAINT, out, count=1)      # a page converted before P23 still has the ?legacy=1 version
    missing = [t for t in CSS_TAGS if t not in out]
    if missing:
        if "</head>" not in out:
            raise CodemodError("no </head>")
        out = out.replace("</head>", "\n" + "\n".join(missing) + "\n</head>", 1)

    # <body data-page>
    m = re.search(r"<body\b[^>]*>", out)
    if not m:
        raise CodemodError("no <body>")
    out = out[:m.start()] + _set_attr(m.group(0), "data-page", item["id"]) + out[m.end():]

    # the page's own <nav>: drop it, keep its footer line as <small class="mm-built"> after </main>
    span = _balanced_nav(out)
    if span:
        nav_html = out[span[0]:span[1]]
        smalls = re.findall(r"<small\b[^>]*>(.*?)</small>", nav_html, re.S)
        out = out[:span[0]] + out[span[1]:]
        if smalls and 'class="mm-built"' not in out:
            if "</main>" not in out:
                raise CodemodError("no </main>")
            out = out.replace("</main>", f'</main><small class="mm-built">{smalls[-1]}</small>', 1)

    out = prune_styles(out)
    if not STYLE_RE.search(out):        # no inline CSS left: the page relies on the shared styles, so it must opt in to base.css
        m = re.search(r"<body\b[^>]*>", out)
        out = out[:m.start()] + _add_class(m.group(0), "mm") + out[m.end():]

    # scripts
    if OLD_UI_TAG in out:
        out = out.replace(OLD_UI_TAG, SHELL_TAG)
    if SHELL_TAG not in out:
        if "</body>" not in out:
            raise CodemodError("no </body>")
        out = out.replace("</body>", SHELL_TAG + "</body>", 1)
    return out


def verify(before, after):
    """Hard guarantees about a converted page. Raises CodemodError on any violation."""
    if _main_block(before) != _main_block(after):
        raise CodemodError("<main> would change")
    if re.search(r"<nav\b", after):
        raise CodemodError("a <nav> is left")
    if after.count(SHELL_TAG) != 1 or "atlas-ui.js" in after:
        raise CodemodError("shell script tag missing or duplicated")
    if len(BUILT.findall(before)) != len(BUILT.findall(after)):
        raise CodemodError('the number of "Built ... from commit ..." stamps would change')
    if not STYLE_RE.search(after) and not re.search(r'<body\b[^>]*\sclass="[^"]*\bmm\b', after):
        raise CodemodError('a page with no inline CSS needs class="mm" on <body>')
    if "legacy=1" in after:
        raise CodemodError("the ?legacy=1 switch is still in the pre-paint snippet")
    if after.count('class="mm-built"') > 1:
        raise CodemodError("more than one mm-built line")


# ------------------------------------------------------------------ driver
def plan(root, only=None):
    """-> (changes {path: new_text_native}, skipped [(name, why)], errors [(name, why)])"""
    root = Path(root)
    nav, items = load_nav(root)
    by_id = {it["id"]: it for it in items.values()}
    wanted = None
    if only:
        wanted = set()
        for o in only:
            if o.endswith(".html"):
                key = o
            else:
                key = by_id[o]["url"] if o in by_id else None
            if key not in items:
                raise SystemExit(f"--only {o}: not a page listed in {NAV_REL} (use a file name such as api.html, or a nav id)")
            wanted.add(key)
    changes, skipped, errors = {}, [], []
    for path in sorted(root.glob("*.html")):
        name = path.name
        if wanted is not None and name not in wanted:
            continue
        it = items.get(name)
        if it is None:
            skipped.append((name, f"not listed in {NAV_REL}"))
            continue
        if it["hidden"]:
            skipped.append((name, "hidden in nav.json (standalone or generated page)"))
            continue
        old, crlf = ra.read_lf(path)
        try:
            new = convert(old, it)
            verify(old, new)
        except CodemodError as e:
            errors.append((name, str(e)))
            continue
        if new != old:
            changes[path] = ra.to_native(new, crlf)
    return changes, skipped, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    ap.add_argument("--dry-run", action="store_true", help="list the pages that would change; change nothing")
    ap.add_argument("--check", action="store_true", help="like --dry-run, and exit 1 if any page would change")
    ap.add_argument("--only", action="append", metavar="PAGE", help="only this page (file name or nav id); repeatable")
    args = ap.parse_args(argv)
    root = Path(args.root)
    changes, skipped, errors = plan(root, args.only)
    for name, why in errors:
        print(f"ERROR   {name}: {why}")
    if args.dry_run or args.check:
        for p in sorted(changes):
            print("would convert:", p.name)
        if not changes and not errors:
            print("every page is already on the shell")
        else:
            print(f"{len(changes)} page(s) would change" + (f", {len(errors)} error(s)" if errors else ""))
        return 1 if (args.check and (changes or errors)) or errors else 0
    for p, text in changes.items():
        p.write_bytes(text.encode("utf-8"))
        print("converted:", p.name)
    if not changes and not errors:
        print("already on the shell; nothing to do")
    for name, why in skipped:
        if args.only is None:
            print(f"skipped: {name} ({why})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())