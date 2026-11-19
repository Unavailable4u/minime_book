/* MiniMe Atlas 2 - shared helpers for the API and Agents pages (P17). One ES module, no DOM, no network: Node tests every function here
   (scripts/test_codepages.py). api.js and agents.js do the drawing.

   Inputs (written by the update scripts, never typed):
     data/code/routes.json   every route: method, path, handler, file, line, deps, response_model, router, callers[]
                             (refresh_atlas.py writes the routes from the census; refresh_graph.py writes the callers)
     data/code/agents.json   agent modules, roles, provider key slots (refresh_atlas.py)
     data/index/notes.json, data/notes/<file>.json   the AI notes (P11), loaded for the handler or module on screen
     data/index/mentions.json   the chapter sections that name a file or a function (P15)
   Nothing here invents a link: a caller, a role or a note is shown only when the data has it. */

import { buildRoute } from "./explorer/router.js";

export const fmtN = (n) => (Number.isFinite(n) ? n.toLocaleString("en-US") : "\u2013");

/* ------------------------------------------------------------------ filtering and sorting */
export const tokens = (q) => String(q || "").toLowerCase().split(/\s+/).filter(Boolean);

/* Every word of the query must appear somewhere in text(row). */
export function filterRows(rows, q, text) {
  const t = tokens(q);
  if (!t.length) return rows.slice();
  return rows.filter((r) => { const s = text(r).toLowerCase(); return t.every((w) => s.includes(w)); });
}

/* Stable sort by get(row); numbers numerically, text case-insensitively, empty values last either way. */
export function sortRows(rows, get, asc = true) {
  const empty = (v) => v == null || v === "";
  const cmp = (a, b) => {
    const x = get(a), y = get(b);
    if (empty(x) && empty(y)) return 0;
    if (empty(x)) return 1;
    if (empty(y)) return -1;
    if (typeof x === "number" && typeof y === "number") return asc ? x - y : y - x;
    const r = String(x).toLowerCase().localeCompare(String(y).toLowerCase());
    return asc ? r : -r;
  };
  return rows.map((r, i) => [r, i]).sort((a, b) => cmp(a[0], b[0]) || a[1] - b[1]).map((p) => p[0]);
}

/* ------------------------------------------------------------------ routes */
export const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];
export const shortFile = (p) => (p.startsWith("backend/api/") ? p.slice("backend/api/".length) : p);
export const stem = (p) => String(p).split("/").pop().replace(/\.[^.]+$/, "");
export const baseName = (p) => String(p).split("/").pop();

/* A row the table and the detail panel share. */
export function routeRows(doc) {
  return ((doc && doc.routes) || []).map((r) => ({
    ...r,
    short: shortFile(r.file),
    depsText: r.deps && r.deps.length ? r.deps.join(", ") : "none",
    called: (r.callers || []).length,
  }));
}

export function routeKpis(routes) {
  const n = (m) => routes.filter((r) => r.method === m).length;
  return [
    { label: "routes", value: routes.length },
    { label: "GET", value: n("GET") },
    { label: "POST", value: n("POST") },
    { label: "PUT / PATCH", value: n("PUT") + n("PATCH") },
    { label: "DELETE", value: n("DELETE") },
    { label: "with declared auth/deps", value: routes.filter((r) => r.deps && r.deps.length).length },
    { label: "called by the frontend", value: routes.filter((r) => (r.callers || []).length).length },
  ];
}

/* The route files by number of routes: [{ name, title, n }], biggest first. */
export function routesPerFile(routes, limit = 13) {
  const m = new Map();
  for (const r of routes) m.set(r.file, (m.get(r.file) || 0) + 1);
  return [...m].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, limit).map(([file, n]) => ({ name: stem(file), title: file, n }));
}

/* The frontend files that call the most routes: [{ name, title, n }]. */
export function callerFiles(routes, limit = 10) {
  const m = new Map();
  for (const r of routes) for (const c of r.callers || []) m.set(c.file, (m.get(c.file) || 0) + 1);
  return [...m].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, limit).map(([file, n]) => ({ name: baseName(file), title: file, n }));
}

/* How a frontend caller was found. Every link is inferred, and the page says so; this says how. */
export const VIA = {
  shape: "same path shape (HTTP method ignored)",
  method: "best path match, and the code names this HTTP method",
  score: "best path match (the code names no method)",
};
export const viaText = (via) => (via || []).map((v) => VIA[v] || v).join("; ");

/* The strongest evidence a caller has, for sorting and for the badge: method > score > shape. */
export function viaRank(via) {
  const v = via || [];
  return v.includes("method") ? 0 : v.includes("score") ? 1 : v.includes("shape") ? 2 : 3;
}

/* The Explorer link for a file, a symbol or a line range. */
export const explorerHref = (path, { qual = "", start = null, end = null } = {}) =>
  `explorer.html${buildRoute({ view: "file", path, qual, start, end })}`;

/* The hash api.html uses for a selected route: "#GET /api/chats", percent-encoded. */
export const routeHash = (r) => `#${encodeURIComponent(r.key)}`;
export function routeFromHash(routes, hash) {
  let key = "";
  try { key = decodeURIComponent(String(hash || "").replace(/^#/, "")); } catch { return null; }
  return routes.find((r) => r.key === key) || null;
}

/* The prefix chain, root first: how the path was put together. Only what the census knows. */
export function prefixChain(r) {
  const out = [];
  if (r.include_prefix != null && r.router) out.push({ label: `include_router(${r.router})`, prefix: r.include_prefix });
  if (r.prefix) out.push({ label: "APIRouter(prefix=...)", prefix: r.prefix });
  out.push({ label: "decorator path", prefix: r.path });
  return out;
}

/* A symbol of a note by qualified name, or null. Handlers are top-level functions, so qual is the handler name. */
export function pickSymbol(note, qual) {
  if (!note || !Array.isArray(note.symbols)) return null;
  return note.symbols.find((s) => s.qual === qual) || null;
}

/* "fresh" | "stale" | "none" for a file, from data/index/notes.json (the same rule the Explorer uses). */
export function noteState(notes, path) {
  const e = notes && notes.files && notes.files[path];
  if (!e) return "none";
  return e.status === "stale" || (e.bad && e.bad.length) ? "stale" : "fresh";
}

export const noteFile = (path) => `data/notes/${path.replace(/\//g, "__")}.json`;

/* The caveat under every callers list. Said once, in one place, so the two pages cannot drift. */
export const CALLERS_CAVEAT = "Inferred by scanning the frontend for \"/api/...\" strings, not proven. Test files are not scanned, and a call built from a variable that is not a visible string is missed.";

/* How old the caller scan is, for the freshness line: { text, stale }. */
export function scanInfo(doc) {
  const s = doc && doc.callers_scan;
  if (!s) return { text: "Frontend callers: not scanned yet (run refresh_graph.py).", stale: true };
  const same = s.commit && doc.commit && (String(doc.commit).startsWith(String(s.commit).slice(0, 7)) || String(s.commit).startsWith(String(doc.commit)));
  return {
    text: `Frontend callers scanned at ${s.commit ? String(s.commit).slice(0, 7) : "an unknown commit"}: ${fmtN(s.frontend_files)} frontend files, ${fmtN(s.pairs)} links.`,
    stale: !same,
  };
}

/* ------------------------------------------------------------------ agents */
export function agentKpis(doc) {
  const modules = (doc && doc.modules) || [], roles = (doc && doc.roles) || [], providers = (doc && doc.providers) || [];
  return [
    { label: "agent modules", value: modules.length },
    { label: "roles", value: roles.length },
    { label: "provider key slots", value: providers.reduce((n, p) => n + p.slots.length, 0) },
    { label: "providers", value: providers.length },
    { label: "agent code lines", value: modules.reduce((n, m) => n + m.code, 0) },
    { label: "agents with no test file", value: modules.filter((m) => !m.tests.length).length },
  ];
}

export function moduleRows(doc) {
  const roleOf = new Map(((doc && doc.roles) || []).filter((r) => r.module).map((r) => [r.module, r]));
  return ((doc && doc.modules) || []).map((m) => ({ ...m, role: roleOf.get(m.name) || null, testCount: m.tests.length }));
}

export const roleCounts = (doc) => ((doc && doc.roles) || []).filter((r) => r.slots.length).map((r) => ({ name: r.key, title: r.key, n: r.slots.length }));
export const providerCounts = (doc) => ((doc && doc.providers) || []).map((p) => ({ name: p.name, title: p.name, n: p.slots.length })).sort((a, b) => b.n - a.n || (a.name < b.name ? -1 : 1));

/* Roles that no key slot serves: the pills the old page marked "no key slot". */
export const unservedRoles = (doc) => ((doc && doc.roles) || []).filter((r) => !r.slots.length).map((r) => r.key);

/* Bar widths for a list of { n }: the biggest is 55 % of the row, as the old pages drew them. */
export function barWidths(items, scale = 55) {
  const mx = Math.max(1, ...items.map((i) => i.n));
  return items.map((i) => Math.max(1.1, Math.round((i.n / mx) * scale * 10) / 10));
}