/* MiniMe Atlas 2 - graph-slice figures (P20). One ES module, no dependencies, no build step.

   A graph-slice figure shows the neighbourhood of one file or one folder in the code graph: the thing in the middle, and the files
   (or, for a folder, the folders) it shares the most graph links with, strongest first, fanned out to its left and right. The line
   to each neighbour is as thick as the number of links. Every neighbour opens in the Explorer.

   Data: data/graph/file-links.json (written by scripts/refresh_graph.py, P13). It keeps the 12 strongest neighbours of every file,
   so a folder's numbers add up the links that survive that cut: they are a floor, not a total, and the figure says so.

   Manifest entry (content/figures/<chapter>.json, see figures.js):
     { "id": "agents-graph", "after": "<heading id>", "type": "graph-slice", "focus": "backend/agents", "limit": 10,
       "caption": "...", "alt": "..." }
     focus   repo-relative path of a file or a folder, as it appears in data/index/paths.json
     limit   neighbours drawn, 3 to 24 (default 12)

   Everything here that does not touch the page (the model, the layout, the SVG text) is exported and has no DOM dependency, so
   scripts/test_graphslice.py runs it in Node. The SVG paints with the Atlas tokens (var(--ink), var(--graph), ...), so it follows
   the Dark / Paper theme without being redrawn. Colour is never the only carrier: a file is a circle, a folder a square, and every
   neighbour carries its link count as text. */

export const SLICE_MIN = 3;
export const SLICE_MAX = 24;
export const SLICE_DEFAULT = 12;
export const LINKS_PATH = "data/graph/file-links.json";
export const SLICE_FOCUS = /^[A-Za-z0-9._@+-]+(?:\/[A-Za-z0-9._@+-]+)*\/?$/;

const W = 920;                 // viewBox width
const MID = W / 2;
const ROW = 40;                // vertical room of one neighbour (two lines of text)
const DOT_X = 250;             // distance of a neighbour's marker from the centre line
const NAME_MAX = 28;           // characters of a name drawn before it is cut

/* ================================================================== pure helpers */

export function cleanFocus(value) {
  if (typeof value !== "string") return "";
  return value.trim().replace(/^\.\//, "").replace(/\/+$/, "");
}

/* null when `focus` is fine, else a short reason. check_site.py has the same rule in Python. */
export function focusProblem(value) {
  if (typeof value !== "string" || value.trim() === "") return 'needs "focus": a file or folder path from data/index/paths.json';
  if (!SLICE_FOCUS.test(value.trim())) return '"focus" must be a repo-relative path of letters, digits and . _ @ + - separated by /';
  if (value.trim().split("/").some((s) => s === "." || s === "..")) return '"focus" must not contain . or .. segments';
  return null;
}

export function limitProblem(value) {
  if (value == null) return null;
  if (!Number.isInteger(value) || value < SLICE_MIN || value > SLICE_MAX) return `"limit" must be a whole number from ${SLICE_MIN} to ${SLICE_MAX}`;
  return null;
}

const byLinks = (a, b) => b.links - a.links || (a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
const baseName = (p) => p.slice(p.lastIndexOf("/") + 1);
const dirName = (p) => { const i = p.lastIndexOf("/"); return i < 0 ? "" : p.slice(0, i); };

/* The folder a neighbour is drawn as: the first `depth` segments of its path, but never a folder that contains the focus (that
   neighbour is then drawn as the file it is) and never the file's own name. A file in the repo root stays a file. */
function neighbourKey(path, focus, depth) {
  const segs = path.split("/");
  if (segs.length === 1) return { path, kind: "file" };
  const folder = segs.slice(0, Math.min(segs.length - 1, depth)).join("/");
  if (focus === folder || focus.startsWith(folder + "/")) return { path, kind: "file" };
  return { path: folder, kind: "folder" };
}

/* The neighbourhood of `focus` in a file-links.json document { paths: [...], links: [[[index, count], ...], ...] }.
   A file gives { kind: "file", centre, nodes: [{path, kind: "file", links, files: 1}], more }; a folder gives the folders (and loose
   files) its files are most linked to. Returns null when the document has nothing for this focus (an unknown path, or a file with no
   graph links). `more` is how many neighbours were left out by `limit`. */
export function sliceModel(doc, focus, limit = SLICE_DEFAULT) {
  const f = cleanFocus(focus);
  const n = Number.isInteger(limit) ? Math.min(SLICE_MAX, Math.max(SLICE_MIN, limit)) : SLICE_DEFAULT;
  if (!f || !doc || !Array.isArray(doc.paths) || !Array.isArray(doc.links)) return null;
  const paths = doc.paths;
  const at = paths.indexOf(f);
  if (at >= 0) {
    const all = (doc.links[at] || []).filter((r) => Array.isArray(r) && paths[r[0]] != null)
      .map(([j, w]) => ({ path: paths[j], kind: "file", links: w, files: 1 })).sort(byLinks);
    if (!all.length) return null;
    return { kind: "file", focus: f, centre: { path: f, kind: "file", label: baseName(f), sub: dirName(f), files: 1 },
             nodes: all.slice(0, n), more: Math.max(0, all.length - n), partial: true };
  }
  const prefix = f + "/";
  const inside = [];
  paths.forEach((p, i) => { if (p.startsWith(prefix)) inside.push(i); });
  if (!inside.length) return null;
  const inSet = new Set(inside);
  const depth = Math.max(2, f.split("/").length);
  const groups = new Map();
  for (const i of inside) {
    for (const r of doc.links[i] || []) {
      if (!Array.isArray(r) || inSet.has(r[0]) || paths[r[0]] == null) continue;
      const key = neighbourKey(paths[r[0]], f, depth);
      const g = groups.get(key.path) || { path: key.path, kind: key.kind, links: 0, seen: new Set() };
      g.links += r[1];
      g.seen.add(r[0]);
      groups.set(key.path, g);
    }
  }
  const all = [...groups.values()].map((g) => ({ path: g.path, kind: g.kind, links: g.links, files: g.seen.size })).sort(byLinks);
  if (!all.length) return null;
  return { kind: "folder", focus: f, centre: { path: f, kind: "folder", label: baseName(f) + "/", sub: dirName(f), files: inside.length },
           nodes: all.slice(0, n), more: Math.max(0, all.length - n), partial: true };
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);
const encPath = (p) => p.split("/").map(encodeURIComponent).join("/");

/* The Explorer's hash routes (assets/js/explorer/router.js). */
export function explorerHref(kind, path) {
  return `explorer.html#/${kind === "folder" ? "d" : "f"}/${encPath(path)}`;
}
/* The graph viewer opened on the same file or folder (graph-viewer.html reads ?focus=). */
export function viewerHref(path) {
  return `graph-viewer.html?focus=${encodeURIComponent(path)}`;
}

/* Where each neighbour goes: strongest first, alternately right and left, each side top to bottom. Pure geometry. */
export function sliceLayout(model) {
  const right = [], left = [];
  model.nodes.forEach((nd, i) => (i % 2 === 0 ? right : left).push(nd));
  const rows = Math.max(right.length, left.length, 1);
  const H = Math.max(260, rows * ROW + 96);
  const cy = H / 2;
  const place = (list, side) => {
    const top = cy - ((list.length - 1) * ROW) / 2;
    return list.map((nd, k) => ({ node: nd, side, x: MID + side * DOT_X, y: top + k * ROW }));
  };
  const centreW = Math.max(150, Math.min(280, 8 * Math.max(model.centre.label.length, model.centre.sub.length * 0.8) + 40));
  return { W, H, cx: MID, cy, centreW, centreH: 46, items: [...place(right, 1), ...place(left, -1)] };
}

/* The figure as SVG text. Every string that comes from data is escaped; hrefs are built from encoded path segments. */
export function sliceSvg(model) {
  const L = sliceLayout(model);
  const max = Math.max(1, ...model.nodes.map((n) => n.links));
  const out = [];
  out.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${L.W} ${L.H}" font-family="var(--font-ui)" font-size="12">`);
  const edges = [], marks = [];
  for (const it of L.items) {
    const nd = it.node;
    const x0 = L.cx + it.side * (L.centreW / 2), x1 = it.x - it.side * 8;
    const dx = Math.abs(x1 - x0) * 0.55;
    const width = (1 + (4 * nd.links) / max).toFixed(2);
    edges.push(`<path d="M${x0.toFixed(1)} ${L.cy} C${(x0 + it.side * dx).toFixed(1)} ${L.cy} ${(x1 - it.side * dx).toFixed(1)} ${it.y.toFixed(1)} ${x1.toFixed(1)} ${it.y.toFixed(1)}" fill="none" stroke="var(--graph)" stroke-opacity="0.7" stroke-width="${width}" stroke-linecap="round"/>`);
    const anchor = it.side > 0 ? "start" : "end";
    const tx = it.x + it.side * 16;
    const detail = nd.kind === "folder" ? `${nd.links} links · ${nd.files} file${nd.files === 1 ? "" : "s"}` : `${nd.links} link${nd.links === 1 ? "" : "s"}`;
    const dir = nd.kind === "file" && dirName(nd.path) ? `  ${cut(dirName(nd.path), 22)}` : "";
    const shape = nd.kind === "folder"
      ? `<rect x="${(it.x - 6).toFixed(1)}" y="${(it.y - 6).toFixed(1)}" width="12" height="12" rx="2" fill="var(--panel)" stroke="var(--graph)" stroke-width="2"/>`
      : `<circle cx="${it.x.toFixed(1)}" cy="${it.y.toFixed(1)}" r="6" fill="var(--graph)"/>`;
    const name = nd.kind === "folder" ? baseName(nd.path) + "/" : baseName(nd.path);
    const parent = nd.kind === "folder" && dirName(nd.path) ? `${cut(dirName(nd.path), 22)}/ ` : "";
    marks.push(
      `<a tabindex="-1" href="${esc(explorerHref(nd.kind, nd.path))}"><title>${esc(nd.path)}: ${esc(detail)}</title>${shape}` +
      `<text x="${tx.toFixed(1)}" y="${(it.y - 3).toFixed(1)}" text-anchor="${anchor}" fill="var(--ink)" font-weight="600">${esc(cut(name, NAME_MAX))}</text>` +
      `<text x="${tx.toFixed(1)}" y="${(it.y + 11).toFixed(1)}" text-anchor="${anchor}" fill="var(--ink-dim)" font-size="10.5">${esc(parent + detail + dir)}</text></a>`);
  }
  out.push(...edges);
  const c = model.centre;
  const cx0 = L.cx - L.centreW / 2, cy0 = L.cy - L.centreH / 2;
  out.push(`<a tabindex="-1" href="${esc(explorerHref(c.kind, c.path))}"><title>${esc(c.path)}</title>` +
    `<rect x="${cx0.toFixed(1)}" y="${cy0.toFixed(1)}" width="${L.centreW}" height="${L.centreH}" rx="10" fill="var(--brand)"/>` +
    `<text x="${L.cx}" y="${(L.cy - 3).toFixed(1)}" text-anchor="middle" fill="var(--on-brand)" font-weight="700" font-size="13">${esc(cut(c.label, 30))}</text>` +
    `<text x="${L.cx}" y="${(L.cy + 12).toFixed(1)}" text-anchor="middle" fill="var(--on-brand)" font-size="10.5">${esc(c.kind === "folder" ? `${c.files} files with graph links` : cut(c.sub || "repository root", 36))}</text></a>`);
  out.push(...marks);
  if (model.more > 0) {
    out.push(`<text x="${MID}" y="${L.H - 10}" text-anchor="middle" fill="var(--ink-dim)" font-size="10.5">+ ${model.more} more neighbour${model.more === 1 ? "" : "s"} not drawn</text>`);
  }
  out.push("</svg>");
  return out.join("");
}

/* A plain-text note under the figure: what the lines mean, and what the numbers are not. */
export function sliceNote(model) {
  const what = model.kind === "folder" ? "Each box is a folder (or a loose file) that the files in this folder link to; the number is how many graph links join them." : "Each circle is a file this file shares graph links with; the number is how many links join them.";
  return `${what} Only each file's 12 strongest links are kept, so the numbers are a floor.`;
}

/* ================================================================== browser side */

let cache = null;
/* data/graph/file-links.json, fetched once per page. `base` is the site root URL (figures.js passes its own). */
export function loadLinks(base) {
  if (!cache) {
    cache = fetch(new URL(LINKS_PATH, base)).then((r) => {
      if (!r.ok) throw new Error(`${LINKS_PATH}: HTTP ${r.status}`);
      return r.json();
    }).catch((err) => { cache = null; throw err; });
  }
  return cache;
}

/* Everything figures.js needs to put a graph-slice on the page: { model, svg, note }. Throws a readable error when it cannot. */
export async function loadSlice(fig, base) {
  const doc = await loadLinks(base);
  const model = sliceModel(doc, fig.focus, fig.limit || SLICE_DEFAULT);
  if (!model) throw new Error(`the graph has no links recorded for "${fig.focus}" (a path that is not in ${LINKS_PATH}, or a file nothing links to)`);
  return { model, svg: sliceSvg(model), note: sliceNote(model) };
}
