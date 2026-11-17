/* MiniMe Atlas 2 - Explorer data model (P13). One ES module. The functions at the top are pure (Node tests them); the loaders at
   the bottom fetch the sharded JSON under data/ and cache it for the life of the page.

   Inputs (all written by the update scripts, never typed):
     data/code/tree.json           folders -> file rows, 10 numbers per file, and the name of the shard that holds its symbols
     data/code/files/<shard>.json  full per-file records: functions, classes, git dates, module docstring
     data/code/imports.json        imports / imported_by / external, per file
     data/index/notes.json         which files have an AI note, and whether it is fresh
     data/notes/<path>.json        the note itself (loaded only for the file on screen)
     data/graph/file-links.json    strongest graph neighbours per file (optional: exists after refresh_graph.py has run)
   Every one of them may be missing; the page shows what it has. */

export const CODE = "data/code";

/* ------------------------------------------------------------------ the tree */
/* tree.json -> { root, files: Map(path -> file), dirs: Map(path -> dir) }.
   dir  = { kind:"dir",  name, path, dirs:[dir], files:[file], n:{files,lines,code,functions,classes}, parent }
   file = { kind:"file", name, path, lang, lines, code, functions, classes, commits, last, flags, shard, test, binary, parent } */
export function buildTree(raw) {
  const ix = {};
  (raw.file_fields || []).forEach((f, i) => { ix[f] = i; });
  const files = new Map();
  const dirs = new Map();
  const byName = (a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0);
  const mkDir = (d, parent) => {
    const path = parent && parent.path ? `${parent.path}/${d.name}` : d.name;
    const dir = { kind: "dir", name: d.name, path, dirs: [], files: [], n: d.n || { files: 0, lines: 0, code: 0, functions: 0, classes: 0 }, parent };
    dirs.set(path, dir);
    fill(dir, d);
    return dir;
  };
  const fill = (dir, d) => {
    dir.dirs = (d.dirs || []).map((c) => mkDir(c, dir)).sort(byName);
    dir.files = (d.files || []).map((row) => {
      const flags = String(row[ix.flags] || "");
      const f = {
        kind: "file", name: row[ix.name], path: dir.path ? `${dir.path}/${row[ix.name]}` : row[ix.name], lang: row[ix.lang], lines: row[ix.lines], code: row[ix.code],
        functions: row[ix.functions], classes: row[ix.classes], commits: row[ix.commits], last: row[ix.last], flags, shard: row[ix.shard],
        test: flags.includes("t"), binary: flags.includes("b"), parent: dir,
      };
      files.set(f.path, f);
      return f;
    }).sort(byName);
  };
  const root = { kind: "dir", name: "", path: "", dirs: [], files: [], n: { files: 0, lines: 0, code: 0, functions: 0, classes: 0 }, parent: null };
  fill(root, raw.root || {});
  root.n = root.dirs.reduce((a, d) => ({ files: a.files + d.n.files, lines: a.lines + d.n.lines, code: a.code + d.n.code, functions: a.functions + d.n.functions, classes: a.classes + d.n.classes }),
    root.files.reduce((a, f) => ({ files: a.files + 1, lines: a.lines + f.lines, code: a.code + f.code, functions: a.functions + f.functions, classes: a.classes + f.classes }), { files: 0, lines: 0, code: 0, functions: 0, classes: 0 }));
  dirs.set("", root);
  return { root, files, dirs, shards: raw.shards || [], commit: raw.commit || "", generated: raw.generated || "" };
}

export function allFiles(dir) {
  const out = [];
  const walk = (d) => { out.push(...d.files); d.dirs.forEach(walk); };
  walk(dir);
  return out;
}

/* The folders above a path, outermost first: "a/b/c.py" -> ["a", "a/b"]. */
export function ancestors(path) {
  const parts = path.split("/");
  const out = [];
  for (let i = 1; i < parts.length; i++) out.push(parts.slice(0, i).join("/"));
  return out;
}

/* ------------------------------------------------------------------ the tree as a flat list (what the virtual list draws) */
const terms = (q) => String(q || "").toLowerCase().split(/\s+/).filter(Boolean);

/* rows = [{ node, depth }] for the folders in `expanded` (a Set of paths). With a filter, only files whose path holds every word are
   kept, with the folders above them, and those folders are open whatever `expanded` says. */
export function flatten(root, expanded, filter = "") {
  const words = terms(filter);
  const rows = [];
  if (!words.length) {
    const walk = (d, depth) => {
      for (const c of d.dirs) { rows.push({ node: c, depth }); if (expanded.has(c.path)) walk(c, depth + 1); }
      for (const f of d.files) rows.push({ node: f, depth });
    };
    walk(root, 0);
    return rows;
  }
  const hit = (f) => { const p = f.path.toLowerCase(); return words.every((w) => p.includes(w)); };
  const has = new Map();
  const mark = (d) => {
    let any = false;
    for (const c of d.dirs) if (mark(c)) any = true;
    if (d.files.some(hit)) any = true;
    has.set(d.path, any);
    return any;
  };
  mark(root);
  const walk = (d, depth) => {
    for (const c of d.dirs) if (has.get(c.path)) { rows.push({ node: c, depth }); walk(c, depth + 1); }
    for (const f of d.files) if (hit(f)) rows.push({ node: f, depth });
  };
  walk(root, 0);
  return rows;
}

/* ------------------------------------------------------------------ notes */
export const noteFileName = (path) => `${path.replace(/\//g, "__")}.json`;

/* 0..4 filled dots for a folder, from data/index/notes.json "folders". null when the folder has no file that wants a note. */
export function coverage(notes, dirPath) {
  const f = notes && notes.folders && notes.folders[dirPath];
  if (!f || !f.files) return null;
  const ratio = f.noted / f.files;
  let dots = Math.round(ratio * 4);
  if (f.noted > 0 && dots === 0) dots = 1;
  if (f.noted < f.files && dots === 4) dots = 3;
  return { dots, noted: f.noted, files: f.files, stale: f.stale || 0 };
}

/* "fresh" | "stale" | "none" for a file, from the notes index. */
export function noteStatus(notes, path) {
  const e = notes && notes.files && notes.files[path];
  if (!e) return "none";
  return e.status === "stale" || (e.bad && e.bad.length) ? "stale" : "fresh";
}

/* ------------------------------------------------------------------ symbols */
export function signature(sym) {
  if (sym.kind === "class") return `class ${sym.name}${sym.bases && sym.bases.length ? `(${sym.bases.join(", ")})` : ""}`;
  const ps = (sym.params || []).map((p) => `${p.name}${p.annotation ? `: ${p.annotation}` : ""}${p.default != null ? ` = ${p.default}` : ""}`);
  return `${sym.async ? "async " : ""}${sym.name}(${ps.join(", ")})${sym.returns ? ` -> ${sym.returns}` : ""}`;
}

/* One row per function, method and class of a file record, with the one-line description chosen like this:
     the AI note's summary  ->  the docstring's first line (doc1)  ->  nothing ("no description yet").
   `fresh` compares the hash the note was written against with the census hash of the symbol now:
     "fresh" same hash, "stale" different hash, "unverified" the note has no hash yet, "none" no note for this symbol. */
export function symbolRows(rec, note) {
  const sums = new Map(((note && note.symbols) || []).map((s) => [s.qual, s]));
  const row = (s, kind) => {
    const n = sums.get(s.qual) || null;
    let fresh = "none";
    if (n) fresh = n.hash ? (n.hash === s.hash ? "fresh" : "stale") : "unverified";
    const summary = n && n.summary ? n.summary : "";
    const desc = summary || s.doc1 || "";
    return {
      path: rec.path, qual: s.qual, name: s.name, kind, start: s.start, end: s.end, loc: s.loc || 0, cc: s.cc == null ? null : s.cc,
      sig: signature({ ...s, kind }), desc, from: summary ? "note" : s.doc1 ? "doc" : "none", fresh, note: n,
      visibility: s.visibility || "", test: !!s.test || !!rec.test, decorators: s.decorators || [], hash: s.hash || "",
    };
  };
  return [...(rec.functions || []).map((f) => row(f, f.kind || "function")), ...(rec.classes || []).map((c) => row(c, "class"))];
}

export const SORTS = {
  line: { label: "Line", cmp: (a, b) => a.start - b.start || a.qual.localeCompare(b.qual) },
  name: { label: "Name", cmp: (a, b) => a.name.localeCompare(b.name) || a.start - b.start },
  size: { label: "Size", cmp: (a, b) => b.loc - a.loc || a.start - b.start },
  cc: { label: "Complexity", cmp: (a, b) => (b.cc ?? -1) - (a.cc ?? -1) || b.loc - a.loc },
  note: { label: "Has note", cmp: (a, b) => (b.from === "note") - (a.from === "note") || (b.from === "doc") - (a.from === "doc") || a.start - b.start },
};

/* filter = { q, kind: "all" | "function" | "method" | "class" | "component" | "hook", noteOnly, hideTests } */
export function filterSymbols(rows, { q = "", kind = "all", noteOnly = false, hideTests = false } = {}) {
  const words = terms(q);
  return rows.filter((r) => {
    if (kind !== "all" && r.kind !== kind) return false;
    if (noteOnly && r.from !== "note") return false;
    if (hideTests && r.test) return false;
    if (!words.length) return true;
    const hay = `${r.qual} ${r.path} ${r.desc}`.toLowerCase();
    return words.every((w) => hay.includes(w));
  });
}

/* ------------------------------------------------------------------ churn */
const monthIndex = (iso) => { const m = /^(\d{4})-(\d{2})/.exec(iso || ""); return m ? Number(m[1]) * 12 + Number(m[2]) - 1 : null; };

/* Commit dates -> commits per month, for the last `span` months up to the latest date (fewer when the history is shorter, at least 2). */
export function monthBuckets(dates, span = 18) {
  const ms = (dates || []).map(monthIndex).filter((m) => m != null);
  if (!ms.length) return { counts: [], first: "", last: "" };
  const end = Math.max(...ms);
  const begin = Math.max(Math.min(...ms), end - span + 1);
  const n = Math.max(2, end - begin + 1);
  const start = end - n + 1;
  const counts = Array(n).fill(0);
  for (const m of ms) if (m >= start) counts[m - start] += 1;
  const lab = (m) => `${Math.floor(m / 12)}-${String((m % 12) + 1).padStart(2, "0")}`;
  return { counts, first: lab(start), last: lab(end) };
}

/* ------------------------------------------------------------------ the prompt for a file with no note yet */
export function notePrompt(path) {
  const out = `graphify-out/atlas-notes/${path.replace(/\//g, "__")}.json`;
  return [
    `Write an "atlas note" for ${path}. Do NOT modify any source file, do not commit.`,
    "",
    "1. Read graphify-out/atlas-notes/_SCHEMA.md (schema version 1). If it is missing, stop and tell me to run",
    "   `python scripts/notes.py todo --minime ../MiniMe` in the minime_book repository first.",
    `2. Read the whole file ${path}, then write ${out} following that schema.`,
    '3. Set "blob" to the output of `git hash-object ' + path + '` and "commit" to `git rev-parse HEAD`.',
    '4. Be truthful: describe only what the code does. If a reason or behaviour is not visible in the code, put it in "unknowns"',
    '   instead of guessing, and use confidence "low" when unsure.',
    '5. For every function and class of substance write "summary" (<= 140 chars, what it is FOR), "params", "returns", "raises",',
    '   "side_effects" and "evidence" line ranges; write "start"/"end", and copy "hash" from _todo.json when the file is listed there, else null.',
    "6. Never include secrets, tokens, or values from .env files.",
    `7. Validate the JSON by loading it with python, then print the file and symbol counts.`,
  ].join("\n");
}

/* ------------------------------------------------------------------ loading (browser only) */
const BASE = typeof import.meta !== "undefined" && import.meta.url ? new URL("../../../", import.meta.url) : null;
const cache = new Map();

export function getJSON(rel) {
  if (!cache.has(rel)) {
    cache.set(rel, fetch(new URL(rel, BASE)).then((r) => { if (!r.ok) throw new Error(`${rel}: ${r.status}`); return r.json(); }));
    cache.get(rel).catch(() => cache.delete(rel));        // a failed fetch is tried again next time
  }
  return cache.get(rel);
}

const optional = (rel) => getJSON(rel).catch(() => null);

/* The small files every view needs. tree.json is required (the page says so when it is missing); the others are optional. */
export async function loadCore() {
  const [rawTree, imports, notes, fileLinks] = await Promise.all([
    getJSON(`${CODE}/tree.json`), optional(`${CODE}/imports.json`), optional("data/index/notes.json"), optional("data/graph/file-links.json"),
  ]);
  return { tree: buildTree(rawTree), imports, notes, fileLinks: indexFileLinks(fileLinks) };
}

/* file-links.json stores paths once and refers to them by position: turn it into path -> [{ path, n }]. */
export function indexFileLinks(doc) {
  if (!doc || !Array.isArray(doc.paths) || !Array.isArray(doc.links)) return null;
  const out = new Map();
  doc.paths.forEach((p, i) => out.set(p, (doc.links[i] || []).map(([j, n]) => ({ path: doc.paths[j], n })).filter((x) => x.path)));
  return { map: out, commit: doc.commit || "", date: doc.date || "" };
}

/* The full record of one file (functions, classes, git dates, module docstring), from its shard. null when it has none. */
export async function loadRecord(core, file) {
  const name = core.tree.shards[file.shard];
  if (name == null) return null;
  const shard = await getJSON(`${CODE}/files/${name}.json`);
  return (shard.files || []).find((r) => r.path === file.path) || null;
}

export const loadNote = (path) => optional(`data/notes/${noteFileName(path)}`);

/* All records of the files below a folder, one shard fetch per shard (at most `cap` shards; `more` says some were left out). */
export async function loadRecords(core, files, cap = 40) {
  const want = new Set(files.map((f) => f.path));
  const shards = [...new Set(files.map((f) => f.shard))].filter((s) => core.tree.shards[s] != null);
  const use = shards.slice(0, cap);
  const parts = await Promise.all(use.map((s) => getJSON(`${CODE}/files/${core.tree.shards[s]}.json`).catch(() => ({ files: [] }))));
  const recs = parts.flatMap((p) => p.files || []).filter((r) => want.has(r.path));
  return { recs, more: shards.length - use.length };
}
