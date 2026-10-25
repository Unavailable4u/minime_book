#!/usr/bin/env python3
"""
refresh_graph.py -- refresh every Graphify-derived part of the MiniMe Atlas from a
freshly generated graphify-out/ folder.

refresh_atlas.py renders the pages that come from data/census.json and deliberately
carries the Graphify-derived parts over unchanged. This script is the other half: it
re-computes those parts from MiniMe's graphify-out/graph.json (the graph you regenerate
with Copilot), so after running both scripts nothing on the site is left from an old graph.

    python scripts/refresh_graph.py --minime ../MiniMe           # refresh from ../MiniMe/graphify-out
    python scripts/refresh_graph.py --minime ../MiniMe --check   # change nothing; exit 1 if out of date

Only the Python standard library is used.

What it refreshes, and where each number comes from:

    graph-viewer.html   the "Constellation" viewer shown on graph.html, generated from scripts/graph_viewer_template.html
                        plus the file-level graph (files, functions and routes from explore.html, and every
                        file-to-file link counted from graph.json, not just the top 14 per file)
    graph.html          node/link/community counts, the folder-to-folder matrix, "Strongest cross-folder
                        links", the "Communities, named" table (largest 40), and the Built stamp
    index.html          "graph nodes" and "graph links" KPIs, "Graph hubs (most connections)"
    explore.html        the per-file "Links out / Links in" edges (top 14 each way, weight = number of
                        graph links between the two files)
    api.html            the per-route "Frontend callers" column, the "called by the frontend" KPI and
                        "Frontend files that call the API most". These are NOT in graph.json: they are
                        found by scanning MiniMe/frontend for "/api/..." strings and matching them to
                        the route paths by shape (inferred, not proven, and the HTTP method is ignored,
                        the same caveat the page already states).
    data/summary.md     the "Graph:" line

Safety: the graph must have been built at the same commit as data/census.json (and at the
current MiniMe HEAD), otherwise the pages would mix two different versions of the code. Pass
--allow-stale-graph to override that on purpose.
"""
import argparse
import collections
import datetime as dt
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # the repo tracks scripts/__pycache__; do not make it show as modified

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("refresh_atlas", ROOT / "scripts" / "refresh_atlas.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)

fmt, esc, base = ra.fmt, ra.esc, ra.base
HUBS, PAIRS, MATRIX_N, COMMUNITIES, EG_TOP = 10, 12, 14, 40, 14
MATRIX_MIN = 1                        # smallest link count shown in the matrix (smaller shows as a dot)
SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "coverage", "__pycache__"}
FRONTEND_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs")
TEST_RE = re.compile(r"(^|/)(tests?|__tests__)/|\.(test|spec)\.[jt]sx?$|(^|/)test_[^/]*$")


# ---------------------------------------------------------------------------- graph
class Graph:
    """graphify-out/graph.json in the shape the Atlas needs."""

    def __init__(self, path, repo_prefix=""):
        path = Path(path)
        d = json.loads(path.read_text(encoding="utf-8"))
        self.path = path
        self.commit = d.get("built_at_commit") or ""
        self.date = dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
        self._prefix = repo_prefix.replace("\\", "/").rstrip("/") + "/" if repo_prefix else ""
        self.nodes = d["nodes"]
        self.N = {n["id"]: n for n in self.nodes}
        for n in self.nodes:
            n["source_file"] = self.norm(n.get("source_file"))
        raw = d.get("links") if d.get("links") is not None else d.get("edges") or []
        self.links = [(l["source"], l["target"]) for l in raw if l.get("source") in self.N and l.get("target") in self.N]
        self.degree = collections.Counter()
        for a, b in self.links:
            self.degree[a] += 1
            self.degree[b] += 1
        self.file_of = {n["id"]: n["source_file"] for n in self.nodes}

    def norm(self, p):
        if isinstance(p, list):
            p = p[0] if p else ""
        p = (p or "").replace("\\", "/")
        if self._prefix and p.startswith(self._prefix):
            p = p[len(self._prefix):]
        return re.sub(r"^\./", "", p)

    @property
    def communities(self):
        return len({n["community"] for n in self.nodes if n.get("community") is not None})


def is_test(path):
    return bool(TEST_RE.search(path))


def folder(path):
    """backend/eo, frontend/app/components, daemon/preview_proxy.py ... ('' for a top-level file)."""
    s = path.split("/")
    if len(s) < 2:
        return ""
    if s[0] == "frontend" and s[1] == "app" and len(s) >= 4:
        return "/".join(s[:3])
    return "/".join(s[:2])


def folder_stats(g):
    """(directed cross-folder link counts, non-test node counts per folder), tests excluded."""
    pairs, nodes = collections.Counter(), collections.Counter()
    for n in g.nodes:
        p = n["source_file"]
        if p and folder(p) and not is_test(p):
            nodes[folder(p)] += 1
    for a, b in g.links:
        pa, pb = g.file_of[a], g.file_of[b]
        fa, fb = folder(pa) if pa else "", folder(pb) if pb else ""
        if fa and fb and fa != fb and not is_test(pa) and not is_test(pb):
            pairs[(fa, fb)] += 1
    return pairs, nodes


# ---------------------------------------------------------------------------- index
def hubs_card(g):
    rows = sorted(((v, g.N[i]) for i, v in g.degree.items() if g.N[i]["source_file"]), key=lambda r: (-r[0], r[1]["label"]))[:HUBS]
    items = [(f"{n['label']}  {base(n['source_file'])}",) * 2 + (v,) for v, n in rows]
    return ra.bars_card("Graph hubs (most connections)", items)


def refresh_index(html, g):
    for label, value in (("graph nodes", len(g.nodes)), ("graph links", len(g.links))):
        pat = re.compile(r'(<div class="k">)[^<]*(</div><div class="l">' + re.escape(label) + r"</div>)")
        html, n = pat.subn(lambda m: m.group(1) + fmt(value) + m.group(2), html)
        if n != 1:
            raise ValueError(f"index KPI card {label!r}: expected 1 match, got {n}")
    return ra.replace_card(html, "Graph hubs", hubs_card(g))


# ---------------------------------------------------------------------- graph page
def matrix_table(pairs, nodes):
    volume = collections.Counter()                      # cross-folder links in + out: which folders matter most
    for (a, b), v in pairs.items():
        volume[a] += v
        volume[b] += v
    busiest = {f for f, _ in sorted(volume.items(), key=lambda kv: (-kv[1], kv[0]))[:MATRIX_N]}
    cols = sorted(busiest, key=lambda f: (-nodes.get(f, 0), f))      # shown biggest folder first
    mx = max((v for (a, b), v in pairs.items() if a in cols and b in cols), default=1)
    head = "".join(f'<th style="height:112px;vertical-align:bottom;padding:4px 2px;text-align:center"><div style="writing-mode:vertical-rl;'
                   f'transform:rotate(180deg);white-space:nowrap;font-size:11.5px;margin:0 auto">{esc(c)}</div></th>' for c in cols)
    out = ['<table style="table-layout:fixed;width:100%"><colgroup><col style="width:190px">' + "<col>" * len(cols) + "</colgroup>",
           f"<tr><th>from \\ to</th>{head}</tr>"]
    for r in cols:
        cells = []
        for c in cols:
            v = pairs.get((r, c), 0)
            if v < MATRIX_MIN:
                cells.append('<td style="text-align:center;color:#3a3a46;padding:6px 2px">·</td>')
                continue
            a = 0.15 + 0.85 * math.log1p(v) / math.log1p(mx)
            cells.append(f'<td class="n" style="text-align:center;padding:6px 2px;font-size:12px;background:rgba(255,32,82,{a:.2f})" '
                         f'title="{esc(r)} -&gt; {esc(c)}: {fmt(v)} links">{fmt(v)}</td>')
        out.append(f"<tr><td><b>{esc(r)}</b></td>{''.join(cells)}</tr>")
    return "".join(out) + "</table>"


def strongest_bars(pairs):
    top = pairs.most_common(PAIRS)
    mx = top[0][1] if top else 1
    return "".join(ra.bar(f"{a} → {b}", f"{a} → {b}", v, mx) for (a, b), v in top)


def community_table(g):
    members = collections.defaultdict(list)
    for n in g.nodes:
        if n.get("community") is not None:
            members[n["community"]].append(n)
    ranked = sorted(members.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    rows = []
    for cid, ns in ranked[:COMMUNITIES]:
        files = collections.Counter(n["source_file"] for n in ns if n["source_file"])
        folders = collections.Counter(folder(f) for f in files.elements() if folder(f))
        top_files = [base(f) for f, _ in files.most_common(5)]
        where = folders.most_common(1)[0][0].split("/", 1)[-1] if folders else "no source file"
        name = f"{where} · {', '.join(top_files[:2])}" if top_files else where
        rows.append(f'<tr><td>{cid}</td><td><b>{esc(name)}</b></td><td class="n">{fmt(len(ns))}</td><td>{esc(", ".join(top_files))}</td></tr>')
    sub = (f"Graphify's own labels were not useful, so each group is named after its dominant folder and most common files. "
           f"Largest {min(COMMUNITIES, len(ranked))} of {fmt(len(ranked))}.")
    return (f'<p class="sub">{sub}</p><div class="tw"><table><tr><th style="width:50px">#</th><th style="width:34%">Name</th>'
            f'<th style="width:80px">Nodes</th><th>Most common files</th></tr>{"".join(rows)}</table></div>')


def refresh_viewer_blurb(html):
    return ra.sub_once(html, r'(<h2>Interactive viewer</h2><p class="sub">)[^<]*(<a href="graph-viewer\.html" target="_blank">)',
                       lambda m: f"{m.group(1)}Folders and files as a constellation. Search a file or function, click a folder to zoom in, click a file to see what it links to and from. {m.group(2)}")


def refresh_graph_page(html, g):
    pairs, nodes = folder_stats(g)
    html = ra.sub_once(html, r'(<p class="sub">)[\d,]+ nodes and [\d,]+ links from Graphify(, summarized by folder first, then explorable\.</p>)',
                       lambda m: f"{m.group(1)}{fmt(len(g.nodes))} nodes and {fmt(len(g.links))} links from Graphify{m.group(2)}")
    i = html.find('<table style="table-layout:fixed')
    if i < 0:
        raise KeyError("folder matrix table not found")
    j = html.find("</table>", i) + len("</table>")
    html = html[:i] + matrix_table(pairs, nodes) + html[j:]
    html = ra._between(html, '<h3 style="margin-top:0">Strongest cross-folder links</h3>', "</div><h2>Communities, named",
                       '<h3 style="margin-top:0">Strongest cross-folder links</h3>' + strongest_bars(pairs))
    html = ra._between(html, '<p class="sub">Graphify\'s own labels', "<h2>Interactive viewer</h2>", community_table(g))
    html = refresh_viewer_blurb(html)
    return ra.sub_once(html, r"Built \d{4}-\d{2}-\d{2} from commit [0-9a-f]+\.", f"Built {g.date} from commit {g.commit[:7]}.")


# ------------------------------------------------------------------------- explore
def refresh_explore(html, g):
    paths = [r[0] for r in ra.read_literal(html, "const F=")]
    idx = {p: i for i, p in enumerate(paths)}
    weight = collections.Counter()
    for a, b in g.links:
        pa, pb = g.file_of[a], g.file_of[b]
        if pa in idx and pb in idx and pa != pb:
            weight[(idx[pa], idx[pb])] += 1
    out, inn = collections.defaultdict(list), collections.defaultdict(list)
    for (a, b), w in weight.items():
        out[a].append([b, w])
        inn[b].append([a, w])
    top = lambda lst: sorted(lst, key=lambda x: (-x[1], x[0]))[:EG_TOP]
    EG = {str(k): {"o": top(out.get(k, [])), "i": top(inn.get(k, []))} for k in sorted(set(out) | set(inn))}
    return ra.replace_literal(html, ",EG=", json.dumps(EG, separators=(",", ":")))


# ------------------------------------------------------------------------- viewer
VIEWER_TEMPLATE = ROOT / "scripts" / "graph_viewer_template.html"
VIEWER_TOP_FUNCTIONS = 6                # largest functions listed in a file's details panel
VIEWER_DESC_MAX = 110                   # characters of a file's docstring kept in the viewer


def viewer_group(path):
    """Folder a file is drawn in: 'backend/eo', 'frontend/app', 'daemon', or 'root' for loose top-level files."""
    p = path.split("/")
    if len(p) == 1 or p[0].startswith("."):
        return "root"
    return p[0] if len(p) == 2 else p[0] + "/" + p[1]


def viewer_data(g, explore_html):
    """Everything the viewer shows, as one JSON-able dict.

    Files, functions and routes come from explore.html (which refresh_atlas.py builds from the census), so the
    viewer always lists the same files as the rest of the Atlas. The links are counted from graph.json: one per
    graph link between two different files, weighted by how many links join them.
    """
    rows = ra.read_literal(explore_html, "const F=")
    fns = ra.read_literal(explore_html, ",FN=")
    routes = ra.read_literal(explore_html, ",RT=")
    count = collections.Counter(viewer_group(r[0]) for r in rows)
    groups = sorted(count, key=lambda x: (-count[x], x))
    gi = {x: i for i, x in enumerate(groups)}
    files = []
    for path, lang, code, nfn, commits, last, test, doc in rows:
        doc = re.sub(r"\s+", " ", doc or "").strip()
        if len(doc) > VIEWER_DESC_MAX:
            doc = doc[:VIEWER_DESC_MAX - 3].rstrip() + "..."
        files.append([path, lang, code, nfn, commits, last, 1 if test else 0, gi[viewer_group(path)], doc])
    idx = {r[0]: i for i, r in enumerate(rows)}
    weight = collections.Counter()
    for a, b in g.links:
        pa, pb = g.file_of[a], g.file_of[b]
        if pa in idx and pb in idx and pa != pb:
            weight[(idx[pa], idx[pb])] += 1
    edges = sorted([a, b, w] for (a, b), w in weight.items())
    by_file = collections.defaultdict(list)
    for f in fns:                                         # [name, file index, line, lines, kind]
        by_file[f[1]].append(f)
    top = {str(i): [[f[0], f[2], f[3], f[4]] for f in sorted(l, key=lambda f: -f[3])[:VIEWER_TOP_FUNCTIONS]] for i, l in sorted(by_file.items())}
    return {
        "meta": {"date": g.date, "commit": g.commit[:7]},
        "groups": groups,
        "files": files,
        "edges": edges,
        "fns": [[f[0], f[1], f[2]] for f in fns],
        "top": top,
        "routes": [[r[0], r[1], r[2], r[3]] for r in routes],
    }


def viewer_html(data, template=VIEWER_TEMPLATE):
    html = Path(template).read_text(encoding="utf-8")
    if html.count("__DATA__") != 1:
        raise ValueError(f"{template} must contain exactly one __DATA__ placeholder")
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    blob = blob.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")   # keep it safe inside <script>
    return html.replace("__DATA__", blob)


# ----------------------------------------------------------------------------- api
API_LIT = re.compile(r"/api/(?:\$\{[^}]*\}|[^\"'`\s${}])*")


def route_regex(path):
    parts = []
    for s in [s for s in path.strip("/").split("/") if s]:
        if s.startswith("{") and s.endswith("}"):
            parts.append(".+" if s.endswith(":path}") else "[^/]+")
        else:
            parts.append(re.escape(s))
    return re.compile("^/" + "/".join(parts) + "/?$")


ALIAS_DECL = re.compile(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:`([^`\n]*)`|\"([^\"\n]*)\"|'([^'\n]*)')")


def expand_aliases(src):
    """`const base = `${apiUrl}/api/workspaces/${id}/code`` then `${base}/files` -> the full '/api/...' text."""
    for _ in range(2):
        aliases = {}
        for m in ALIAS_DECL.finditer(src):
            value = next(v for v in m.groups()[1:] if v is not None)
            if "/api/" in value and "${" + m.group(1) + "}" not in value:
                aliases[m.group(1)] = value
        if not aliases:
            break
        for name, value in aliases.items():
            src = src.replace("${" + name + "}", value)
    return src


def api_literals(src):
    """Every '/api/...' string in a source file, template expressions turned into one placeholder segment."""
    out = set()
    src = expand_aliases(src)
    for m in API_LIT.finditer(src):
        s = re.sub(r"\$\{[^}]*\}", "_p_", m.group(0)).split("?")[0].rstrip(",;:.")
        out.add(s)
    return out


def scan_callers(frontend, routes):
    """({(method, path): n frontend files}, {file: n routes it calls}). Matched by path shape, not method."""
    rx = {r: route_regex(r[1]) for r in routes}
    plain = {r for r in routes if "{" not in r[1]}
    calls, per_file = collections.defaultdict(set), collections.defaultdict(set)
    for fp in sorted(Path(frontend).rglob("*")):
        rel = fp.relative_to(frontend).as_posix()
        if not fp.is_file() or fp.suffix not in FRONTEND_EXT or SKIP_DIRS & set(fp.relative_to(frontend).parts) or is_test(rel):
            continue
        for lit in api_literals(fp.read_text(encoding="utf-8", errors="ignore")):
            hit = [r for r in routes if rx[r].match(lit)]
            if "_p_" not in lit and any(r in plain for r in hit):
                hit = [r for r in hit if r in plain]      # an exact path beats a /{param} route of the same shape
            for r in hit:
                calls[r].add(rel)
                per_file[rel].add(r)
    return {r: len(calls[r]) for r in routes}, {f: len(v) for f, v in per_file.items()}


def refresh_api(html, frontend):
    rows = ra.read_literal(html, "ROWS=")
    counts, per_file = scan_callers(frontend, [(r[0], r[1]) for r in rows])
    for r in rows:
        r[7] = counts[(r[0], r[1])]
    html = ra.replace_literal(html, "ROWS=", json.dumps(rows))
    called = sum(1 for r in rows if r[7] > 0)
    html = ra.sub_once(html, r'(<div class="k">)[\d,]+(</div><div class="l">called by the frontend</div>)',
                       lambda m: f"{m.group(1)}{fmt(called)}{m.group(2)}")
    top = sorted(per_file.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    return ra.replace_card(html, "Frontend files that call the API most", ra.bars_card("Frontend files that call the API most", [(base(f), base(f), n) for f, n in top]))


# --------------------------------------------------------------------------- driver
def update_summary(text, g, census_commit=None):
    nl = "\r\n" if "\r\n" in text else "\n"
    s = text.replace("\r\n", "\n")
    line = f"- Graph: {fmt(len(g.nodes))} nodes, {fmt(len(g.links))} links, {fmt(g.communities)} communities (Graphify run of {g.date}, commit `{g.commit[:7]}`)."
    return ra.sub_once(s, r"(?m)^- Graph: .*$", line).replace("\n", nl)


def refresh_all(root, g, minime):
    """Return {path: new_bytes} for every file whose content would change."""
    root = Path(root)
    changes = {}

    def page(name, fn, *args):
        path = root / name
        old, crlf = ra.read_lf(path)
        new = fn(old, *args)
        if new != old:
            changes[path] = ra.to_native(new, crlf).encode("utf-8")

    page("index.html", refresh_index, g)
    page("graph.html", refresh_graph_page, g)
    page("explore.html", refresh_explore, g)
    explore = root / "explore.html"
    explore_html = changes[explore].decode("utf-8") if explore in changes else ra.read_lf(explore)[0]
    frontend = Path(minime) / "frontend"
    if frontend.is_dir():
        page("api.html", refresh_api, frontend)
    sp = root / "data" / "summary.md"
    if sp.exists():
        old, crlf = ra.read_lf(sp)
        new = update_summary(old, g)
        if new != old:
            changes[sp] = ra.to_native(new, crlf).encode("utf-8")
    target = root / "graph-viewer.html"
    data = viewer_html(viewer_data(g, explore_html)).encode("utf-8")
    if not target.exists() or target.read_bytes() != data:
        changes[target] = data
    return changes


def git_head(repo):
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def freshness_problems(g, census, minime):
    """Reasons this graph must not be mixed into pages built from this census."""
    out = []
    head = git_head(minime)
    if not g.commit:
        out.append("graph.json has no built_at_commit, so its version cannot be checked.")
    if g.commit and head and g.commit != head:
        out.append(f"the graph was built at {g.commit[:7]} but MiniMe is now at {head[:7]}. Commit your work, then regenerate the graph with Copilot.")
    ch = (census or {}).get("git", {}).get("head", "")
    if g.commit and ch and not (g.commit.startswith(ch) or ch.startswith(g.commit)):
        out.append(f"the graph was built at {g.commit[:7]} but data/census.json is from {ch[:7]}. Run refresh_atlas.py --census-from first (update_all.py does both).")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    ap.add_argument("--minime", default=str(ROOT.parent / "MiniMe"), help="the MiniMe checkout (default: ../MiniMe)")
    ap.add_argument("--graph", help="path to graph.json (default: <minime>/graphify-out/graph.json)")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything is out of date")
    ap.add_argument("--allow-stale-graph", action="store_true", help="use the graph even if it was built at a different commit")
    args = ap.parse_args(argv)
    root, minime = Path(args.root), Path(args.minime)
    gpath = Path(args.graph) if args.graph else minime / "graphify-out" / "graph.json"
    if not gpath.exists():
        sys.exit(f"{gpath} not found. Regenerate the graph with Copilot first (see README: 'Updating everything').")
    g = Graph(gpath, repo_prefix=str(minime.resolve()))
    cpath = root / "data" / "census.json"
    census = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else None
    problems = freshness_problems(g, census, minime)
    if problems and not args.allow_stale_graph:
        sys.exit("Not refreshing from this graph:\n  - " + "\n  - ".join(problems) + "\n(pass --allow-stale-graph to use it anyway)")
    changes = refresh_all(root, g, minime)
    if args.check:
        for p in sorted(changes):
            print("out of date:", p.relative_to(root))
        print("graph-derived parts are in sync with the graph" if not changes else f"{len(changes)} file(s) out of date; run: python scripts/refresh_graph.py")
        return 1 if changes else 0
    for p, data in changes.items():
        p.write_bytes(data)
        print("updated:", p.relative_to(root))
    if not changes:
        print("already up to date")
    print(f"graph: {fmt(len(g.nodes))} nodes, {fmt(len(g.links))} links, {fmt(g.communities)} communities, commit {g.commit[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
