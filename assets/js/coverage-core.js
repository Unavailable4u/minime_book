/* MiniMe Atlas 2 - Coverage & freshness: the pure logic (P22). No DOM and no imports, so Node tests it
   (scripts/test_status.py) and shell.js can import it for the top-bar chip without loading the page.
   The drawing is in coverage.js. Everything here reads data/index/status.json (written by scripts/build_status.py).

     ageDays(iso, now)            whole days since a YYYY-MM-DD date, or null
     warnDays(cfg)                the amber thresholds: content/config.json "freshness".warnDays, over DEFAULT_WARN
     chipModel(status, cfg, now)  the top-bar chip: { state: "ok" | "stale" | "unknown", text, title, reasons[], items[] }
     folderRows(folders, open)    the folders as an indented list for the heatmap
     auditRollup(entries)         audit marks -> counts per folder ("" is the whole repo)
     heatLevel(ratio)             0..4 for the heatmap cell
     notesBatch(next, prompts)    the command and ready-to-paste Copilot prompt (A or B) for the next batch of notes
     flowBatch(flows, order, prompts)  the same for architecture flows (prompt C for flows not written yet, D for stale ones) */

export const DEFAULT_WARN = { census: 14, graph: 14, notes: 30, docs: 60 };
const MS_DAY = 86400000;

export function ageDays(iso, now = Date.now()) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(typeof iso === "string" ? iso : "");
  if (!m) return null;
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const n = now instanceof Date ? now.getTime() : Number(now);
  if (!Number.isFinite(t) || !Number.isFinite(n)) return null;
  return Math.max(0, Math.floor((n - t) / MS_DAY));
}

/* A usable threshold is a positive number of days; anything else falls back to the default for that source. */
export function warnDays(cfg) {
  const given = cfg && cfg.freshness && cfg.freshness.warnDays;
  const out = { ...DEFAULT_WARN };
  if (typeof given === "number" && given > 0) { for (const k of Object.keys(out)) out[k] = given; return out; }
  if (given && typeof given === "object") for (const k of Object.keys(out)) if (typeof given[k] === "number" && given[k] > 0) out[k] = given[k];
  return out;
}

/* "3727ae3" and "3727ae323c26..." are the same commit. */
export function sameCommit(a, b) {
  const x = String(a || "").toLowerCase(), y = String(b || "").toLowerCase();
  if (!x || !y) return false;
  return x.startsWith(y) || y.startsWith(x);
}

/* integer percent, or null when there is nothing to divide by */
export function pct(n, d) {
  return d > 0 && Number.isFinite(n) ? Math.round((100 * n) / d) : null;
}

export const dayWord = (d) => (d == null ? "?" : d === 0 ? "today" : d === 1 ? "1 day" : `${d} days`);

/* One row per source for the page's freshness strip and the chip's tooltip. tone: ok | stale | none (nothing to judge). */
export function freshnessItems(status, cfg, now = Date.now()) {
  const src = (status && status.sources) || {};
  const warn = warnDays(cfg);
  const census = src.census || {}, graph = src.graph || {}, notes = src.notes || {}, docs = src.docs || {};
  const totals = (status && status.notes && status.notes.totals) || {};
  const item = (id, label, date, limit, extra = {}) => {
    const age = ageDays(date, now);
    const tone = date ? (age != null && age > limit ? "stale" : "ok") : "none";
    return { id, label, date: date || "", age, limit, tone, ...extra };
  };
  const notesPct = pct(totals.noted, totals.files);
  return [
    item("census", "Census", census.date, warn.census, { commit: census.commit || "" }),
    item("graph", "Graph", graph.date, warn.graph, { commit: graph.commit || "" }),
    item("notes", "Notes", notes.date, warn.notes, { commit: notes.commit || "", percent: notesPct }),
    item("docs", "Book", docs.date, warn.docs),
  ];
}

export function chipModel(status, cfg, now = Date.now()) {
  if (!status || !status.sources || !status.sources.census || !status.sources.census.commit) {
    return { state: "unknown", text: "", title: "", reasons: [], items: [] };
  }
  const items = freshnessItems(status, cfg, now);
  const by = Object.fromEntries(items.map((i) => [i.id, i]));
  const reasons = [];
  for (const i of items) {
    if (i.tone === "stale") reasons.push(`${i.label} is ${dayWord(i.age)} old (amber after ${i.limit})`);
  }
  const c = by.census.commit;
  if (by.graph.commit && !sameCommit(by.graph.commit, c)) reasons.push(`The graph is from ${String(by.graph.commit).slice(0, 7)}, the census from ${String(c).slice(0, 7)}`);
  if (by.notes.commit && !sameCommit(by.notes.commit, c)) reasons.push(`The notes were written at ${String(by.notes.commit).slice(0, 7)}, the census is ${String(c).slice(0, 7)}`);
  const parts = [`census ${dayWord(by.census.age)}`];
  if (by.graph.date) parts.push(`graph ${dayWord(by.graph.age)}`);
  if (by.notes.percent != null) parts.push(`notes ${by.notes.percent}%`);
  const state = reasons.length ? "stale" : "ok";
  return {
    state, text: parts.join(" · "), commit: String(c).slice(0, 7), items, reasons,
    title: `Atlas snapshot from MiniMe ${String(c).slice(0, 7)}. ${state === "ok" ? "Everything is in step." : reasons.join(". ") + "."} Click for the coverage page.`,
  };
}

/* ------------------------------------------------------------------ the folder heatmap */
/* folders: status.json "folders". open: Set of folder paths that are expanded. -> rows in tree order, each with depth, name, parent,
   hasKids and the numbers. A folder is visible when all its ancestors are open. */
export function folderRows(folders, open = new Set()) {
  const paths = Object.keys(folders || {}).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const kids = new Set(paths.map((p) => p.split("/").slice(0, -1).join("/")).filter(Boolean));
  const rows = [];
  for (const path of paths) {
    const parts = path.split("/");
    let visible = true;
    for (let i = 1; i < parts.length; i++) if (!open.has(parts.slice(0, i).join("/"))) { visible = false; break; }
    if (!visible) continue;
    const f = folders[path];
    rows.push({ path, name: parts[parts.length - 1], depth: parts.length - 1, parent: parts.slice(0, -1).join("/"), hasKids: kids.has(path),
      files: f.files || 0, symbols: f.symbols || 0, elig: f.elig || 0, noted: f.noted || 0, fresh: f.fresh || 0, stale: f.stale || 0,
      notesRatio: f.elig ? f.noted / f.elig : null });
  }
  return rows;
}

/* ratio 0..1 -> 0 (nothing) .. 4 (everything); a little is never drawn as nothing and "almost" never as all. null -> -1 (not applicable) */
export function heatLevel(ratio) {
  if (ratio == null || !Number.isFinite(ratio)) return -1;
  if (ratio <= 0) return 0;
  if (ratio >= 1) return 4;
  return Math.min(3, Math.max(1, Math.round(ratio * 4)));
}

/* audit.entries() -> { "<dir>": { reviewed, rereview, concern, todo, marked } }. "" is the whole repo. A mark whose symbol is gone is not counted
   as a review. A review the census could not be compared with yet ("unverified") counts as reviewed, and `unchecked` says how many. */
export function auditRollup(entries) {
  const out = {};
  const bump = (dir, e) => {
    const c = out[dir] || (out[dir] = { reviewed: 0, rereview: 0, concern: 0, todo: 0, gone: 0, unchecked: 0, marked: 0 });
    c.marked++;
    if (e.status === "gone") c.gone++;
    else if (c[e.status] != null) c[e.status]++;
    if (e.unverified && e.status === "reviewed") c.unchecked++;
  };
  for (const e of entries || []) {
    const path = e && e.mark && e.mark.path;
    if (!path) continue;
    const parts = path.split("/").slice(0, -1);
    bump("", e);
    for (let k = 1; k <= parts.length; k++) bump(parts.slice(0, k).join("/"), e);
  }
  return out;
}

/* ------------------------------------------------------------------ prompts */
/* What to run, and what to paste, to write the next batch of notes. `next` is status.json "next".
   Returns { tier, limit, command, prompt, files[], kind: "A" | "B", note } or null when nothing needs a note. */
export function notesBatch(next, prompts, { limit = 20, minime = "../MiniMe" } = {}) {
  const files = (next && next.files) || [];
  if (!files.length) return null;
  const tier = Math.min(...files.map((f) => f.tier));
  const batch = files.filter((f) => f.tier <= tier).slice(0, limit);
  const changed = batch.filter((f) => f.reason === "changed").length;
  const kind = changed > batch.length / 2 ? "B" : "A";
  const command = `python scripts/notes.py todo --tier ${tier} --limit ${limit} --minime ${minime}`;
  const list = batch.map((f, i) => `${String(i + 1).padStart(2, " ")}. T${f.tier} ${f.reason.padEnd(7)} ${f.path}  (${f.symbols} symbols)`).join("\n");
  const head = [
    `# Batch preview for the next notes (Atlas coverage page). Run this in minime_book first:`,
    `#   ${command}`,
    `# It writes graphify-out/atlas-notes/_todo.json, which is the authoritative batch. The files below are what it should pick;`,
    `# if _todo.json differs, follow _todo.json.`,
    list, "",
  ].join("\n");
  return { tier, limit, command, kind, files: batch, prompt: head + "\n" + (prompts && prompts[kind] ? prompts[kind] : ""), count: batch.length };
}

/* Flows that need Copilot: not written yet (prompt C, two at a time, as the prompt says) and flows with stale, broken or unverified steps (prompt D).
   flows: status.json "flows"; order: status.json "flow_order". Returns { missing[], refresh[], prompt (the C or D text, or ""), kind, command } or null. */
export function flowBatch(flows, order, prompts) {
  const ids = (order && order.length ? order : Object.keys(flows || {})).filter((id) => flows && flows[id]);
  const missing = ids.filter((id) => flows[id].status === "missing");
  const refresh = ids.filter((id) => ["stale", "broken", "unverified"].includes(flows[id].status) || (flows[id].incomplete || []).length);
  if (!missing.length && !refresh.length) return null;
  const kind = refresh.length ? "D" : "C";
  const todo = kind === "D" ? refresh : missing.slice(0, 2);
  const head = [
    `# Flows for this batch (Atlas coverage page): ${todo.join(", ")}`,
    `# Run first, in minime_book:  python scripts/arch.py todo --minime ../MiniMe`,
    `# It writes graphify-out/atlas-arch/_todo.json, the authoritative list.`, "",
  ].join("\n");
  return { kind, missing, refresh, flows: todo, command: "python scripts/arch.py todo --minime ../MiniMe", prompt: head + "\n" + ((prompts && prompts[kind]) || "") };
}

export const fmtN = (n) => (Number.isFinite(n) ? n.toLocaleString("en-US") : "?");