/* MiniMe Atlas 2 - pure helpers for the Infra and Data model pages (P18). One ES module, no DOM, no network: Node tests every
   function here (scripts/test_dataviews.py). infra.js and data.js do the drawing.

   Inputs (written by the update scripts, never typed):
     data/code/infra.json    services, Dockerfiles, CI jobs, dependency manifests, environment variables   (scripts/refresh_atlas.py)
     data/code/schema.json   tables, columns, foreign keys, policies, migrations, who mentions a table      (scripts/refresh_schema.py)
   Nothing here invents a link or a relationship: a foreign key is drawn only when the SQL declares it, and "who touches a
   table" is a text match from the census (a file that names the table), which the page says. */

import { explorerHref, fmtN } from "./codepages.js";

export { explorerHref, fmtN };

/* ------------------------------------------------------------------ infra */
export const isTestPath = (p) => /(^|\/)(tests?|__tests__|fixtures)\//.test(p) || /(^|\/)(test_[^/]*|[^/]*_test\.py|conftest\.py)$/.test(p);

export function infraKpis(doc) {
  const d = doc || {};
  const deps = (d.dependencies || []).reduce((n, m) => n + m.groups.reduce((k, g) => k + g.items.length, 0), 0);
  const env = d.env || [];
  return [
    { label: "compose services", value: (d.services || []).length },
    { label: "Dockerfiles", value: (d.dockerfiles || []).length },
    { label: "CI jobs", value: (d.ci || []).reduce((n, w) => n + w.jobs.length, 0) },
    { label: "dependencies listed", value: deps },
    { label: "environment variables read", value: env.length },
    { label: "documented in an .env.example", value: env.filter((e) => e.documented_in.length).length },
    { label: "read only by tests", value: env.filter((e) => e.files.length && e.test_files.length === e.files.length).length },
  ];
}

/* The old page cut "backend/" off the first file; the rows keep the whole path and offer `short` for display. */
export const shortPath = (p) => (String(p).startsWith("backend/") ? String(p).slice("backend/".length) : String(p));

export function envRows(doc) {
  return ((doc && doc.env) || []).map((e) => {
    const code = e.files.filter((f) => !e.test_files.includes(f));
    return {
      ...e,
      key: e.name,
      uses: e.files.length,
      codeFiles: code,
      testOnly: e.files.length > 0 && code.length === 0,
      first: e.files[0] || "",
      short: shortPath(e.files[0] || ""),
      documented: e.documented_in.length > 0,
      docText: e.documented_in.length ? e.documented_in.join(", ") : "no",
      comment: e.comment || "",
    };
  });
}

/* Variable families by prefix: LAYA_, SUPABASE_, NEXT_PUBLIC_ ... [{ name, title, n }], biggest first. A family needs 3 or more members. */
export function envFamilies(doc, limit = 10) {
  const m = new Map();
  for (const e of (doc && doc.env) || []) {
    const parts = e.name.split("_");
    const prefix = parts[0] === "NEXT" && parts[1] === "PUBLIC" ? "NEXT_PUBLIC" : parts[0];
    if (parts.length > 1) m.set(prefix, (m.get(prefix) || 0) + 1);
  }
  return [...m].filter(([, n]) => n >= 3).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, limit).map(([p, n]) => ({ name: `${p}_`, title: `${p}_* variables`, n }));
}

/* "node:20-slim" three times -> [{ image: "node:20-slim", n: 3 }], in first-seen order. */
export function stageSummary(stages) {
  const out = [];
  for (const s of stages || []) {
    const hit = out.find((x) => x.image === s);
    if (hit) hit.n += 1; else out.push({ image: s, n: 1 });
  }
  return out;
}

export const depCount = (m) => m.groups.reduce((n, g) => n + g.items.length, 0);

/* A manifest title: "backend/requirements.txt" -> "backend", "frontend/package.json" -> "frontend". */
export function manifestLabel(m) {
  const dir = m.file.includes("/") ? m.file.slice(0, m.file.lastIndexOf("/")) : "(root)";
  return m.name && m.kind === "package.json" ? `${dir} (${m.name})` : dir;
}

/* ------------------------------------------------------------------ schema */
export const PUBLIC = "public";
export const bare = (key) => String(key).split(".").slice(1).join(".");
export const schemaOf = (key) => String(key).split(".")[0];
export const migNumber = (file) => { const m = /\/(\d+)_/.exec(file || ""); return m ? m[1] : ""; };

export function schemaKpis(doc) {
  const d = doc || {};
  const pub = (d.tables || []).filter((t) => t.schema === PUBLIC);
  const rels = (d.relations || []).filter((r) => schemaOf(r.from) === PUBLIC);
  return [
    { label: "tables in public", value: pub.length },
    { label: "columns", value: pub.reduce((n, t) => n + t.columns.length, 0) },
    { label: "foreign keys", value: rels.length },
    { label: "migrations", value: (d.migrations || []).length },
    { label: "row-level security forced", value: pub.filter((t) => t.rls === "forced").length },
    { label: "policies", value: pub.reduce((n, t) => n + (t.policies || []).length, 0) },
    { label: "tables no code file names", value: pub.filter((t) => t.refs && !t.refs.code.length).length },
    { label: "tables the dump is missing", value: ((d.drift && d.drift.in_migrations_not_in_dump) || []).length },
  ];
}

export function tableRows(doc) {
  return ((doc && doc.tables) || []).map((t) => ({
    ...t,
    id: t.key,
    columnCount: t.columns.length,
    fkCount: (t.fks || []).length,
    policyCount: (t.policies || []).length,
    indexCount: (t.indexes || []).length,
    rlsText: t.rls || "none",
    codeRefs: t.refs ? t.refs.code.length : null,
    testRefs: t.refs ? t.refs.tests.length : null,
    mig: migNumber(t.created_in),
    createdText: t.created_in ? (migNumber(t.created_in) ? `migration ${migNumber(t.created_in)}` : t.created_in.replace(/^scripts\//, "")) : "",
    drifted: !!t.drift,
  }));
}

export const schemaCounts = (doc) => ((doc && doc.schemas) || []).map((s) => ({ name: s.name, tables: s.tables, file: s.file }));

/* The hash data.html uses for a selected table: "#public.workspaces". */
export const tableHash = (t) => `#${encodeURIComponent(t.key)}`;
export function tableFromHash(rows, hash) {
  let key = "";
  try { key = decodeURIComponent(String(hash || "").replace(/^#/, "")); } catch { return null; }
  if (!key) return null;
  return rows.find((r) => r.key === key) || rows.find((r) => r.schema === PUBLIC && r.name === key) || null;
}

/* What a table references and what references it: [{ cols, table, tableCols, onDelete }] and [{ from, cols, tableCols, onDelete }]. */
export function relationsOf(doc, key) {
  const rels = (doc && doc.relations) || [];
  return {
    references: rels.filter((r) => r.from === key).map((r) => ({ cols: r.cols, table: r.to, tableCols: r.to_cols, onDelete: r.on_delete || "", origin: r.origin })),
    referencedBy: rels.filter((r) => r.to === key).map((r) => ({ table: r.from, cols: r.cols, tableCols: r.to_cols, onDelete: r.on_delete || "", origin: r.origin })),
  };
}

/* Short flags for a column, in a fixed order: PK, FK, NOT NULL, UNIQUE. */
export function columnFlags(c) {
  const out = [];
  if (c.pk) out.push("PK");
  if (c.fk) out.push("FK");
  if (c.notnull && !c.pk) out.push("NOT NULL");
  if (c.unique) out.push("UNIQUE");
  return out;
}

/* The three lists "who touches this table" shows. A table of another schema has no list (its name is not unique across schemas). */
export function refGroups(t) {
  if (!t || !t.refs) return null;
  return [
    { id: "code", label: "Code", files: t.refs.code },
    { id: "tests", label: "Tests", files: t.refs.tests },
    { id: "sql", label: "SQL files", files: t.refs.sql },
  ];
}

export const REFS_CAVEAT = "A text match: these files contain the table's name. That is not proof they query it (a common name such as \"workspaces\" also appears in prose and in other tables' names), and a query built from a variable is missed.";

/* One sentence per kind of difference between the migrations and the dump, or "" when the table has none. */
export function driftText(t) {
  const d = t && t.drift;
  if (!d) return "";
  const parts = [];
  if (d.only_migrations) parts.push(`the migrations add ${d.only_migrations.join(", ")}, which the dump does not have`);
  if (d.only_dump) parts.push(`the dump has ${d.only_dump.join(", ")}, which no migration creates`);
  if (d.type_differs) parts.push(`${d.type_differs.join(", ")} ${d.type_differs.length > 1 ? "have" : "has"} a different type in the two`);
  return parts.join("; ");
}

export function migrationRows(doc) {
  return ((doc && doc.migrations) || []).map((m) => ({
    ...m,
    key: m.id || m.file,
    createsText: m.creates.map(bare).join(", "),
    changed: m.touches.map(bare),
    addedColumns: m.adds_columns.map((a) => `${bare(a.table)}.${a.column}`),
  }));
}

/* ------------------------------------------------------------------ ER diagram layout */
export const ER = { boxW: 208, head: 26, row: 17, pad: 6, gapX: 96, gapY: 22, maxCols: 4, margin: 16, ghost: "auth.users" };

/* The columns a box shows: keys first (primary and foreign), then others up to maxCols; the rest becomes "+N more". */
export function boxColumns(t, max = ER.maxCols) {
  const keys = t.columns.filter((c) => c.pk || c.fk);
  const rest = t.columns.filter((c) => !c.pk && !c.fk);
  const shown = keys.concat(rest).slice(0, max);
  return { shown, more: Math.max(0, t.columns.length - shown.length) };
}

const boxH = (n, more) => ER.head + ER.pad + (n + (more ? 1 : 0)) * ER.row + ER.pad;

/* Deterministic layered layout of the tables of one schema. A table sits to the right of the tables it references. Tables
   without any foreign key (to or from) go in a band below. A foreign key to a table of another schema (auth.users) is drawn
   to one shared "ghost" box on the left. Returns { width, height, nodes, edges, ghost, isolated }. */
export function erLayout(doc, schema = PUBLIC) {
  const tables = ((doc && doc.tables) || []).filter((t) => t.schema === schema).slice().sort((a, b) => (a.key < b.key ? -1 : 1));
  const keys = new Set(tables.map((t) => t.key));
  const rels = ((doc && doc.relations) || []).filter((r) => keys.has(r.from));
  const inner = rels.filter((r) => keys.has(r.to) && r.to !== r.from);
  const outer = rels.filter((r) => !keys.has(r.to));
  const linked = new Set();
  for (const r of rels) { linked.add(r.from); if (keys.has(r.to)) linked.add(r.to); }
  const connected = tables.filter((t) => linked.has(t.key));
  const isolated = tables.filter((t) => !linked.has(t.key));

  /* layer = longest chain of references below the table (roots are layer 0); a cycle stops after |tables| passes */
  const layer = new Map(connected.map((t) => [t.key, 0]));
  for (let pass = 0; pass <= connected.length; pass++) {
    let moved = false;
    for (const r of inner) {
      const want = layer.get(r.to) + 1;
      if (layer.get(r.from) < want && want <= connected.length) { layer.set(r.from, want); moved = true; }
    }
    if (!moved) break;
  }
  const hasGhost = outer.length > 0;
  const shift = hasGhost ? 1 : 0;
  const layers = [];
  for (const t of connected) {
    const L = layer.get(t.key) + shift;
    (layers[L] = layers[L] || []).push(t);
  }
  for (let i = 0; i < layers.length; i++) if (!layers[i]) layers[i] = [];

  const colW = ER.boxW + ER.gapX;
  const nodes = new Map();
  const place = (t, L, y) => {
    const { shown, more } = boxColumns(t);
    const h = boxH(shown.length, more);
    const n = { key: t.key, name: t.name, x: ER.margin + L * colW, y, w: ER.boxW, h, layer: L, shown, more, total: t.columns.length };
    nodes.set(t.key, n);
    return h;
  };

  /* order inside a layer: by the average vertical position of the tables it references (two sweeps), ties by name */
  const parentsOf = (key) => inner.filter((r) => r.from === key).map((r) => r.to);
  const order = layers.map((arr) => arr.slice().sort((a, b) => (a.key < b.key ? -1 : 1)));
  for (let sweep = 0; sweep < 2; sweep++) {
    const pos = new Map();
    order.forEach((arr, L) => { let y = 0; for (const t of arr) { const { shown, more } = boxColumns(t); pos.set(t.key, y); y += boxH(shown.length, more) + ER.gapY; } void L; });
    for (let L = 1; L < order.length; L++) {
      const bary = (t) => { const ps = parentsOf(t.key).filter((k) => pos.has(k)); return ps.length ? ps.reduce((s, k) => s + pos.get(k), 0) / ps.length : Infinity; };
      order[L] = order[L].slice().sort((a, b) => { const x = bary(a), y = bary(b); return x === y ? (a.key < b.key ? -1 : 1) : x - y; });
      let y = 0;
      for (const t of order[L]) { const { shown, more } = boxColumns(t); pos.set(t.key, y); y += boxH(shown.length, more) + ER.gapY; }
    }
  }

  let bottom = ER.margin;
  order.forEach((arr, L) => {
    let y = ER.margin;
    for (const t of arr) y += place(t, L, y) + ER.gapY;
    bottom = Math.max(bottom, y);
  });

  let ghost = null;
  if (hasGhost) {
    const targets = [...new Set(outer.map((r) => r.to))].sort();
    const gh = ER.head + ER.pad + ER.row + ER.pad;
    ghost = { keys: targets, x: ER.margin, y: ER.margin, w: ER.boxW, h: gh + (targets.length - 1) * ER.row, label: targets.length === 1 ? targets[0] : "other schemas", rows: targets };
  }

  /* the band of tables with no foreign key, laid out in rows */
  const cols = Math.max(1, Math.floor(((layers.length || 1) * colW - ER.gapX) / colW) || 1);
  const perRow = Math.max(3, cols);
  let bandY = bottom + (isolated.length ? 34 : 0);
  let rowTop = bandY, rowH = 0;
  isolated.forEach((t, i) => {
    const c = i % perRow;
    if (c === 0 && i > 0) { rowTop += rowH + ER.gapY; rowH = 0; }
    const { shown, more } = boxColumns(t, 4);
    const h = boxH(shown.length, more);
    nodes.set(t.key, { key: t.key, name: t.name, x: ER.margin + c * colW, y: rowTop, w: ER.boxW, h, layer: -1, shown, more, total: t.columns.length });
    rowH = Math.max(rowH, h);
  });
  const bandLabelY = isolated.length ? bottom + 16 : null;
  const height = isolated.length ? rowTop + rowH + ER.margin : bottom + ER.margin;
  const width = ER.margin * 2 + Math.max(layers.length, isolated.length ? Math.min(perRow, isolated.length) : 0, 1) * colW - ER.gapX;

  /* edges: from the child's left edge to the parent's right edge; several keys between the same pair fan out a little */
  const edges = [];
  const seen = new Map();
  const mid = (n) => n.y + n.h / 2;
  for (const r of rels) {
    const a = nodes.get(r.from);
    if (!a) continue;
    const pair = `${r.from}>${r.to}`;
    const k = seen.get(pair) || 0;
    seen.set(pair, k + 1);
    const off = k * 6;
    let b = nodes.get(r.to), x2, y2;
    if (b) {
      x2 = b.x + b.w; y2 = mid(b) + off;
    } else if (ghost) {
      x2 = ghost.x + ghost.w; y2 = ghost.y + ER.head + ER.pad + ER.row * (ghost.keys.indexOf(r.to) + 0.5);
    } else continue;
    const x1 = a.x, y1 = mid(a) + off;
    const dx = Math.max(24, (x1 - x2) / 2);
    edges.push({ from: r.from, to: r.to, cols: r.cols, toCols: r.to_cols, onDelete: r.on_delete || "", d: `M${x1},${y1} C${x1 - dx},${y1} ${x2 + dx},${y2} ${x2},${y2}`, x1, y1, x2, y2 });
  }
  return { width, height, nodes: [...nodes.values()], edges, ghost, isolated: isolated.map((t) => t.key), bandLabelY, layers: layers.length };
}

/* Whether any two boxes overlap (the layout must never do that). */
export function overlaps(nodes) {
  const hit = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) hit.push([a.key, b.key]);
    }
  }
  return hit;
}

/* The keys joined to `key` by an edge, either way; the diagram dims the rest when a table is selected. */
export function neighbours(edges, key) {
  const s = new Set([key]);
  for (const e of edges) { if (e.from === key) s.add(e.to); if (e.to === key) s.add(e.from); }
  return s;
}

/* ------------------------------------------------------------------ the book's tables page (tables.html) */

/* Every word of the query must appear in the text (case-insensitive); an empty query matches everything. */
export function matchWords(text, q) {
  const words = String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const hay = String(text || "").toLowerCase();
  return words.every((w) => hay.includes(w));
}

/* The number in a table cell ("$1,200", "45%", "3.5x"), or null when the cell is text. */
export function cellNumber(s) {
  const m = /^\s*[$\u20ac\u00a3]?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(?:%|x|k|m|b)?\s*$/i.exec(String(s || ""));
  return m ? Number(m[1].replace(/,/g, "")) : null;
}

/* Compare two cells: numbers numerically, text case-insensitively, empty cells last either way. Returns -1, 0, 1 for ascending. */
export function compareCells(a, b, asc = true) {
  const x = String(a || "").trim(), y = String(b || "").trim();
  if (!x && !y) return 0;
  if (!x) return 1;
  if (!y) return -1;
  const nx = cellNumber(x), ny = cellNumber(y);
  const r = nx != null && ny != null ? Math.sign(nx - ny) : x.toLowerCase().localeCompare(y.toLowerCase());
  return asc ? r : -r;
}

/* Per-category counts from the table cards actually on the page: [{ id, n }] with "all" first. Typed-in counts drift; these can not. */
export function categoryCounts(cats) {
  const m = new Map();
  for (const c of cats) m.set(c, (m.get(c) || 0) + 1);
  return [{ id: "all", n: cats.length }, ...[...m].map(([id, n]) => ({ id, n }))];
}
