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
                        plus the file-level graph (files and functions from data/code/files/*.json, routes from
                        data/code/routes.json, and every file-to-file link counted from graph.json, not just the top 14
                        per file). Since P19 it no longer reads explore.html: that page is a redirect to the Explorer now
    graph.html          node/link/community counts, the folder-to-folder matrix, "Strongest cross-folder
                        links", the "Communities, named" table (largest 40), and the Built stamp
    data/index/vitals.json   the "graph" half: nodes, links, communities, the commit and day of the graph, and the
                        ten hubs (most connections). index.html draws it (assets/js/overview.js, P07); the "census"
                        half of the same file belongs to refresh_atlas.py and is carried over untouched
    data/code/routes.json   (P17) the "callers" half: which frontend files call each route, and how well each link is backed
                        (via: method / score / shape). These are NOT in graph.json: they are found by scanning
                        MiniMe/frontend for "/api/..." strings and matching them to the route paths by shape (inferred, not
                        proven), then checking the code for the HTTP method (a port of MiniMe's graphify_api_links.py).
                        The census half (handlers, deps, ...) belongs to refresh_atlas.py and is kept as it is.
                        api.html draws it (assets/js/api.js).
    data/summary.md     the "Graph:" line
    data/graph/folders.json  (P08) cross-folder link counts and node counts at the finer folder level the live topology
                        diagram on index.html uses (frontend/app/<x>, m2c/src/m2c/<part>, protocol/v1 ...). The diagram
                        reads it for edge widths; which folders form which box is in content/topology.json
    data/graph/file-links.json  (P13) the strongest file-to-file graph links of every file, for the Explorer's "Graph neighbours"
                        panel. Paths are stored once and the links refer to them by position, so the file stays small.

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
HUBS, PAIRS, MATRIX_N, COMMUNITIES = 10, 12, 14, 40
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


def topo_folder(path):
    """The folder a file belongs to in the topology diagram (P08), one level finer than folder() where the diagram needs it:
    m2c/src/m2c/<part> ('m2c/src/m2c' for the files directly in the package), frontend/app/<x>, protocol/v1, daemon, backend/<x>.
    '' for a file at the top level of the repository."""
    dirs = path.split("/")[:-1]
    if not dirs:
        return ""
    if dirs[:3] == ["m2c", "src", "m2c"]:
        return "/".join(dirs[:4])
    if dirs[:2] == ["frontend", "app"] and len(dirs) >= 3:
        return "/".join(dirs[:3])
    return "/".join(dirs[:2])


def folder_stats(g, key=folder):
    """(directed cross-folder link counts, non-test node counts per folder), tests excluded. `key` maps a path to its folder."""
    pairs, nodes = collections.Counter(), collections.Counter()
    for n in g.nodes:
        p = n["source_file"]
        if p and key(p) and not is_test(p):
            nodes[key(p)] += 1
    for a, b in g.links:
        pa, pb = g.file_of[a], g.file_of[b]
        fa, fb = key(pa) if pa else "", key(pb) if pb else ""
        if fa and fb and fa != fb and not is_test(pa) and not is_test(pb):
            pairs[(fa, fb)] += 1
    return pairs, nodes


# --------------------------------------------------------------------------- vitals
def graph_hubs(g):
    """The HUBS files-or-functions with the most graph connections, concept nodes (no source file) left out."""
    rows = sorted(((v, g.N[i]) for i, v in g.degree.items() if g.N[i]["source_file"]), key=lambda r: (-r[0], r[1]["label"]))[:HUBS]
    return [{"label": n["label"], "path": n["source_file"], "links": v} for v, n in rows]


def graph_vitals(g):
    """The "graph" half of data/index/vitals.json. The commit is the short form, like the census's."""
    return {"commit": g.commit[:7], "date": g.date, "nodes": len(g.nodes), "links": len(g.links), "communities": g.communities, "hubs": graph_hubs(g)}


# ------------------------------------------------------------------- folders.json
FOLDERS_REL = "data/graph/folders.json"


def folders_json(g):
    """data/graph/folders.json (P08): the folder-level numbers the topology diagram draws its edges from. Deterministic: the
    commit and day are the graph's own. One folder pair per line so a rebuilt graph gives a readable diff."""
    pairs, nodes = folder_stats(g, topo_folder)
    head = {"version": 1, "source": "graphify", "commit": g.commit[:7], "date": g.date, "nodes": dict(sorted(nodes.items()))}
    rows = sorted(([a, b, v] for (a, b), v in pairs.items()), key=lambda r: (-r[2], r[0], r[1]))
    top = json.dumps(head, indent=2, ensure_ascii=False)
    body = ",\n".join("    " + json.dumps(r, ensure_ascii=False) for r in rows)
    return top[:-2] + ',\n  "pairs": [' + ("\n" + body + "\n  " if rows else "") + "]\n}\n"


# ----------------------------------------------------------------- file-links.json
FILELINKS_REL = "data/graph/file-links.json"
FILELINKS_TOP = 12                    # neighbours kept per file (the Explorer shows a short list, strongest first)


def file_links_json(g):
    """data/graph/file-links.json (P13): for each file the FILELINKS_TOP files it shares the most graph links with, in either
    direction (links inside one file and links to concept nodes are not file pairs). `paths` lists every file that has a
    neighbour, sorted; line i of `links` belongs to paths[i] and holds [[index into paths, link count], ...], strongest first
    (ties by path). Test files are kept: a test file's page shows what it is connected to like any other. Deterministic."""
    counts = collections.Counter()
    for a, b in g.links:
        pa, pb = g.file_of[a], g.file_of[b]
        if pa and pb and pa != pb:
            counts[tuple(sorted((pa, pb)))] += 1
    near = collections.defaultdict(list)
    for (a, b), v in counts.items():
        near[a].append((b, v))
        near[b].append((a, v))
    paths = sorted(near)
    pos = {p: i for i, p in enumerate(paths)}
    rows = []
    for p in paths:
        top = sorted(near[p], key=lambda r: (-r[1], r[0]))[:FILELINKS_TOP]
        rows.append(json.dumps([[pos[q], v] for q, v in top], separators=(",", ":")))
    head = {"version": 1, "source": "graphify", "commit": g.commit[:7], "date": g.date, "top": FILELINKS_TOP}
    top = json.dumps(head, indent=2, ensure_ascii=False)[:-2]
    plist = ",\n".join("    " + json.dumps(p, ensure_ascii=False) for p in paths)
    llist = ",\n".join("    " + r for r in rows)
    return (top + ',\n  "paths": [' + ("\n" + plist + "\n  " if paths else "") + '],\n  "links": [' + ("\n" + llist + "\n  " if rows else "") + "]\n}\n")


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


def _between(html, a, b, new):
    """`html` with everything from the marker `a` up to (not including) the marker `b` replaced by `new`. Only graph.html uses it."""
    i = html.find(a)
    j = html.find(b, i)
    if i < 0 or j < 0:
        raise KeyError(f"section {a!r}..{b!r} not found")
    tail = "\n" if html[j - 1:j] == "\n" else ""
    return html[:i] + new + tail + html[j:]


def refresh_graph_page(html, g):
    pairs, nodes = folder_stats(g)
    html = ra.sub_once(html, r'(<p class="sub">)[\d,]+ nodes and [\d,]+ links from Graphify(, summarized by folder first, then explorable\.</p>)',
                       lambda m: f"{m.group(1)}{fmt(len(g.nodes))} nodes and {fmt(len(g.links))} links from Graphify{m.group(2)}")
    i = html.find('<table style="table-layout:fixed')
    if i < 0:
        raise KeyError("folder matrix table not found")
    j = html.find("</table>", i) + len("</table>")
    html = html[:i] + matrix_table(pairs, nodes) + html[j:]
    html = _between(html, '<h3 style="margin-top:0">Strongest cross-folder links</h3>', "</div><h2>Communities, named",
                       '<h3 style="margin-top:0">Strongest cross-folder links</h3>' + strongest_bars(pairs))
    html = _between(html, '<p class="sub">Graphify\'s own labels', "<h2>Interactive viewer</h2>", community_table(g))
    html = refresh_viewer_blurb(html)
    return ra.sub_once(html, r"Built \d{4}-\d{2}-\d{2} from commit [0-9a-f]+\.", f"Built {g.date} from commit {g.commit[:7]}.")


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


CODE_FILES_DIR = "data/code/files"       # the sharded census records build_code.py writes (P10)
ROUTES_REL = ra.ROUTES_REL


def code_files(root):
    """Every non-binary file record of the census, sorted by path, read from data/code/files/*.json.

    These are the same files, in the same order, that the old explore.html listed (refresh_atlas.nonbinary), so a file keeps its index in
    the viewer's edge list."""
    d = Path(root) / CODE_FILES_DIR
    recs = []
    for p in sorted(d.glob("*.json")):
        doc = json.loads(ra.read_lf(p)[0])
        recs.extend(doc.get("files") or [])
    if not recs:
        raise SystemExit(f"{d} has no file records. Run python scripts/refresh_atlas.py first (it writes the sharded code data).")
    return sorted(recs, key=lambda f: f["path"])


def code_routes(root):
    """The routes of data/code/routes.json (written by refresh_atlas.py, in census order)."""
    return (ra.read_json(root, ROUTES_REL) or {}).get("routes") or []


def viewer_rows(files):
    """(rows, fns): one row per file [path, 2-letter language, code lines, functions, commits, last change, is test, first line of the module docstring]
    and one per function [name, file index, start line, lines, kind]. The layout the viewer template was built for."""
    rows, fns = [], []
    for i, f in enumerate(files):
        git = f.get("git") or {}
        fl = ra.G(f, "functions")
        rows.append([f["path"], f["lang"][:2], f["code"], len(fl), git.get("commits", 0), git.get("last") or "", 1 if f.get("test") else 0,
                     (f.get("module_doc") or "").strip().split("\n")[0][:90]])
        fns.extend([fn["name"], i, fn["start"], fn["loc"], fn["kind"]] for fn in fl)
    return rows, fns


def viewer_data(g, files, routes):
    """Everything the viewer shows, as one JSON-able dict.

    Files, functions and routes come from data/code (which refresh_atlas.py builds from the census), so the viewer always lists the same
    files as the rest of the Atlas. The links are counted from graph.json: one per graph link between two different files, weighted by
    how many links join them.
    """
    rows, fns = viewer_rows(files)
    idx = {r[0]: i for i, r in enumerate(rows)}
    routes = [[r["method"], r["path"], idx[r["file"]], r["handler"]] for r in routes if r["file"] in idx]     # a route whose file the census does not list has nowhere to be drawn
    count = collections.Counter(viewer_group(r[0]) for r in rows)
    groups = sorted(count, key=lambda x: (-count[x], x))
    gi = {x: i for i, x in enumerate(groups)}
    out_files = []
    for path, lang, code, nfn, commits, last, test, doc in rows:
        doc = re.sub(r"\s+", " ", doc or "").strip()
        if len(doc) > VIEWER_DESC_MAX:
            doc = doc[:VIEWER_DESC_MAX - 3].rstrip() + "..."
        out_files.append([path, lang, code, nfn, commits, last, 1 if test else 0, gi[viewer_group(path)], doc])
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
        "files": out_files,
        "edges": edges,
        "fns": [[f[0], f[1], f[2]] for f in fns],
        "top": top,
        "routes": routes,
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


# The second opinion, ported from MiniMe's scripts/graphify_api_links.py (which writes graph.linked.json). It reads the frontend line by
# line, follows `const base = `.../api/x`` aliases, notices the HTTP method (`method: "POST"` within 16 lines, or an apiPost( helper)
# and scores a call against every route by path segments. P17 reconciled the two (UPDATING.md): this file's pair set is the larger one
# (143 routes and 41 frontend files against 142 and 31 on the census commit it was compared at), so it stays the source of *which* file
# calls *which* route. The port is used only to say how well each pair is backed: `via`.
PATH_RE = re.compile(r"/api/[A-Za-z0-9_./${}:~()\-]+")
BASE_RE = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*`([^`]*?/api/[^`]*)`")
BASE_USE_RE = re.compile(r"\$\{(\w+)\}([^'\"`),]*)")
METHOD_RE = re.compile(r"\bmethod\s*:\s*[\"'](GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)[\"']", re.I)
HELPER_RE = re.compile(r"\bapi(Get|Post|Put|Patch|Delete|Options|Head)\s*\(", re.I)
VIA_ORDER = ("method", "score", "shape")


def norm_call_path(path):
    path = re.sub(r"\$\{(?:qs|query|searchParams)\}", "", path)
    path = path.split("?", 1)[0].split("#", 1)[0].strip()
    path = re.sub(r"[).,;]+$", "", path)
    path = path.replace("\\", "/")
    path = re.sub(r"\$\{[^}/]+\}|\{[^}/]+\}", "{param}", path)
    path = re.sub(r"/+", "/", path)
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") or "/"


def path_match_score(call_path, route_path):
    """(score, dynamic segments matched) of a normalised call path against a route path, or None when the shapes cannot match."""
    left, right = norm_call_path(call_path), norm_call_path(route_path)
    lp, rp = left.strip("/").split("/"), right.strip("/").split("/")
    if left == "/" or right == "/" or len(lp) != len(rp):
        return (0, 0) if left == right else None
    score = dyn = 0
    for a, b in zip(lp, rp):
        if a == b:
            score += 2
        elif a == "{param}" and b == "{param}":
            score += 1
            dyn += 1
        elif a == "{param}" or b == "{param}":
            continue
        else:
            return None
    return score, dyn


def best_routes(path, method, routes):
    """The routes that match a call best by path score; when the code names an HTTP method, only those with that method."""
    scored = [(path_match_score(path, r[1]), r) for r in routes]
    scored = [(s, r) for s, r in scored if s is not None]
    if not scored:
        return []
    top = max(s for s, _ in scored)
    best = [r for s, r in scored if s == top]
    return [r for r in best if r[0] == method] if method else best


def named_calls(src):
    """[(normalised path, upper-case HTTP method or None)] for every "/api/..." call written in a frontend source, line by line."""
    lines = src.splitlines()
    bases = {}
    for n, line in enumerate(lines, 1):
        m = BASE_RE.search(line)
        if m:
            bases.setdefault(m.group(1), []).append((n, m.group(2)[m.group(2).find("/api"):]))
    out = []
    for n, line in enumerate(lines, 1):
        s = line.lstrip()
        if s.startswith("//") or s.startswith("*"):
            continue
        paths = [] if BASE_RE.search(line) else [m.group(0) for m in PATH_RE.finditer(line)]
        for name, defs in bases.items():
            for use in BASE_USE_RE.finditer(line):
                if use.group(1) == name:
                    before = [d for d in defs if d[0] <= n]
                    if before:
                        paths.append(before[-1][1] + use.group(2))
        if not paths:
            continue
        ctx = []
        for cl in lines[n - 1:n + 16]:
            ctx.append(cl)
            if "});" in cl:
                break
        mm, hm = METHOD_RE.search("\n".join(ctx)), HELPER_RE.search(line)
        method = hm.group(1).upper() if hm else mm.group(1).upper() if mm else None
        for pv in dict.fromkeys(paths):
            out.append((norm_call_path(pv), method))
    return out


def scan_api_calls(frontend, routes):
    """({(method, path): {file relative to frontend/: [via, ...]}}, number of frontend files scanned).

    Which file calls which route is decided as before: a "/api/..." string in the file matches the route's path shape (the HTTP method
    is ignored, and an exact path beats a /{param} route of the same shape). `via` says how well that link is backed, strongest first:
      method  the best path match, and the code names this route's HTTP method
      score   the best path match, and the code names no method
      shape   only the path shape matched (the link is a weaker guess)
    Test files and build folders are not scanned. Every link is inferred, not proven."""
    rx = {r: route_regex(r[1]) for r in routes}
    plain = {r for r in routes if "{" not in r[1]}
    out = {r: {} for r in routes}
    scanned = 0
    for fp in sorted(Path(frontend).rglob("*")):
        rel = fp.relative_to(frontend).as_posix()
        if not fp.is_file() or fp.suffix not in FRONTEND_EXT or SKIP_DIRS & set(fp.relative_to(frontend).parts) or is_test(rel):
            continue
        scanned += 1
        src = fp.read_text(encoding="utf-8", errors="ignore")
        hits = set()
        for lit in api_literals(src):
            hit = [r for r in routes if rx[r].match(lit)]
            if "_p_" not in lit and any(r in plain for r in hit):
                hit = [r for r in hit if r in plain]      # an exact path beats a /{param} route of the same shape
            hits.update(hit)
        if not hits:
            continue
        backed = collections.defaultdict(set)
        for path, method in named_calls(src):
            for r in best_routes(path, method, routes):
                backed[r].add("method" if method else "score")
        for r in hits:
            out[r][rel] = [v for v in VIA_ORDER if v in backed.get(r, ())] or ["shape"]
    return out, scanned


def scan_callers(frontend, routes):
    """({(method, path): n frontend files}, {file: n routes it calls}). The counts the old api.html showed."""
    calls, _ = scan_api_calls(frontend, routes)
    per_file = collections.Counter(f for files in calls.values() for f in files)
    return {r: len(calls[r]) for r in routes}, dict(per_file)


def api_callers(frontend, commit, routes):
    """(callers, scan) for data/code/routes.json: callers is {"METHOD /path": [{"file": "frontend/...", "via": [...]}]}."""
    calls, scanned = scan_api_calls(frontend, [(r["method"], r["path"]) for r in routes])
    callers = {f"{m} {p}": [{"file": f"frontend/{f}", "via": via} for f, via in sorted(files.items())] for (m, p), files in calls.items() if files}
    return callers, {"commit": commit, "frontend_files": scanned, "pairs": sum(len(v) for v in callers.values())}


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

    page("graph.html", refresh_graph_page, g)
    frontend = Path(minime) / "frontend"
    census = ra.read_json(root, "data/census.json")
    routes = None                                                   # the routes the viewer draws: the ones this run writes to routes.json, else the ones on disk
    if frontend.is_dir() and census.get("routes"):                  # P17: the "callers" half of data/code/routes.json; the census half is rebuilt as refresh_atlas.py does
        rp = root / ra.ROUTES_REL
        doc = ra.build_routes(census, ra.read_json(root, ra.ROUTES_REL))
        routes = doc["routes"]
        callers, scan = api_callers(frontend, git_head(minime) or g.commit, doc["routes"])
        new = ra.json_text(ra.with_callers(doc, callers, scan))
        old, crlf = ra.read_lf(rp) if rp.exists() else (None, False)
        if new != old:
            changes[rp] = ra.to_native(new, crlf).encode("utf-8")
    sp = root / "data" / "summary.md"
    if sp.exists():
        old, crlf = ra.read_lf(sp)
        new = update_summary(old, g)
        if new != old:
            changes[sp] = ra.to_native(new, crlf).encode("utf-8")
    vp = root / ra.VITALS_REL                                      # P07: the Overview's graph numbers; the census half is kept as it is
    new = ra.vitals_text(ra.read_vitals(root), graph=graph_vitals(g))
    old, crlf = ra.read_lf(vp) if vp.exists() else (None, False)
    if new != old:
        changes[vp] = ra.to_native(new, crlf).encode("utf-8")
    fp = root / FOLDERS_REL                                        # P08: edge widths for the topology diagram
    new = folders_json(g)
    old, crlf = ra.read_lf(fp) if fp.exists() else (None, False)
    if new != old:
        changes[fp] = ra.to_native(new, crlf).encode("utf-8")
    lp = root / FILELINKS_REL                                      # P13: the Explorer's graph neighbours
    new = file_links_json(g)
    old, crlf = ra.read_lf(lp) if lp.exists() else (None, False)
    if new != old:
        changes[lp] = ra.to_native(new, crlf).encode("utf-8")
    target = root / "graph-viewer.html"
    data = viewer_html(viewer_data(g, code_files(root), code_routes(root) if routes is None else routes)).encode("utf-8")
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
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        print("updated:", p.relative_to(root))
    if not changes:
        print("already up to date")
    print(f"graph: {fmt(len(g.nodes))} nodes, {fmt(len(g.links))} links, {fmt(g.communities)} communities, commit {g.commit[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
