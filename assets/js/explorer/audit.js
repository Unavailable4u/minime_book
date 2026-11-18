/* MiniMe Atlas 2 - Explorer audit mode, data layer (P16). No DOM and no imports: Node tests it (scripts/explorer_tests/audit.mjs).
   The pieces that draw (buttons, tree marks, the Audit page, the r / c / n keys) are in auditui.js.

   A mark is one reviewer's verdict on one symbol (function, method or class):
     { path, qual, state: "todo" | "reviewed" | "concern", note (one line, <= 200), hash, commit, start, end, at }
   `hash` is the census hash of the symbol when it was marked, `commit` the census commit, `start`/`end` its lines then. Marking a
   symbol Reviewed therefore records exactly which version of the code was read. When the census hash of that symbol later differs,
   the check is not green any more: the status becomes "rereview" (needs re-review). The mark itself is kept, so nothing is lost and
   pressing r again, after reading the new code, renews it. A concern stays a concern when the code changes (it is flagged as changed).

   Derived status of a symbol, from its mark and what the census says about it now (`current`):
     none | todo | reviewed | rereview | concern | gone (the census was checked and the symbol is not there any more)
   `current` is undefined when the symbol has not been looked at in this page view (a reviewed mark is then "unverified": counted as
   reviewed, but not compared with the code yet), a hash string, or null when its file was loaded and the symbol is missing.

   Where marks live:
     local   (default) localStorage "minime_audit_v1": { v: 1, marks: [mark, ...] }. If the browser refuses to store, they live in memory
             for this tab and `persistent` is false, so the page can say so.
     shared  the live-sync store of the To-do page (sync.js -> api/todo.js) as records of kind "audit". The id of a record is
             auditId(path, qual): api/todo.js only accepts ids of [A-Za-z0-9_.-] up to 64 characters, so "path::qual" itself can not be
             the id; the path and the name travel inside the record, and a record whose id does not match them is ignored. The newest
             updatedAt wins, as for every other kind. Switching is explicit and remembered ("minime_audit_mode"); local marks are never
             deleted or uploaded behind the reader's back (uploadLocal() is a button). */

export const KEY_AUDIT = "minime_audit_v1";
export const KEY_MODE = "minime_audit_mode";
export const STATES = ["todo", "reviewed", "concern"];
export const KEY_STATE = { r: "reviewed", c: "concern", n: "todo" };
export const LIMITS = { note: 200, path: 400, qual: 300, hash: 64, marks: 25000, file: 5000000 };
export const GLYPH = { todo: "○", reviewed: "✓", rereview: "↻", concern: "!", gone: "∅" };
export const LABEL = { none: "not marked", todo: "to do", reviewed: "reviewed", rereview: "needs re-review", concern: "concern", gone: "symbol no longer in the census" };

const EPOCH = "1970-01-01T00:00:00.000Z";
const ms = (s) => { const t = Date.parse(s); return Number.isFinite(t) ? t : 0; };
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

export const markKey = (path, qual) => `${path}::${qual}`;

/* One line, no control characters, at most LIMITS.note characters. */
export function cleanNote(s) {
  return String(s == null ? "" : s).replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, LIMITS.note);
}

/* cyrb53: a small, fast 53-bit string hash. Synchronous on purpose (SubtleCrypto is async), and plenty for 20,000 symbols. */
function cyrb53(str) {
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507); h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507); h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return 4294967296 * (2097151 & h2) + (h1 >>> 0);
}

/* The id of a shared record: "a" + 14 hex digits, which matches api/todo.js ID_RE (/^[A-Za-z0-9_.-]{1,64}$/). */
export const auditId = (path, qual) => `a${cyrb53(markKey(path, qual)).toString(16).padStart(14, "0")}`;

/* Anything that claims to be a mark (an import, a shared record) -> a clean mark, or null. Never throws. */
export function normalizeMark(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const path = typeof raw.path === "string" ? raw.path.trim() : "";
  const qual = typeof raw.qual === "string" ? raw.qual.trim() : "";
  if (!path || !qual || path.length > LIMITS.path || qual.length > LIMITS.qual) return null;
  if (path.includes("::") || qual.includes("::") || /[\u0000-\u001f]/.test(path + qual)) return null;
  if (!STATES.includes(raw.state)) return null;
  const hash = typeof raw.hash === "string" && /^[\w.:+=-]{1,64}$/.test(raw.hash) ? raw.hash : "";
  const commit = typeof raw.commit === "string" && /^[0-9a-f]{7,40}$/i.test(raw.commit) ? raw.commit.toLowerCase() : "";
  const line = (v) => (Number.isInteger(v) && v > 0 && v < 10000000 ? v : 0);
  const t = typeof raw.at === "string" ? ms(raw.at) : 0;
  return { path, qual, state: raw.state, note: cleanNote(raw.note), hash, commit, start: line(raw.start), end: line(raw.end), at: t ? new Date(t).toISOString() : EPOCH };
}

/* mark: a normalized mark or null.  current: see the top of this file. */
export function auditStatus(mark, current) {
  if (!mark) return { status: "none", state: "none", changed: false, gone: false, unverified: false };
  const gone = current === null;
  const known = typeof current === "string" && current !== "" && !!mark.hash;
  const changed = !!(known && current !== mark.hash);
  let status = mark.state;
  if (gone) status = "gone";
  else if (mark.state === "reviewed" && changed) status = "rereview";
  return { status, state: mark.state, changed, gone, unverified: mark.state === "reviewed" && !gone && !known };
}

/* The audit filter of the Symbols list: which statuses each choice keeps. */
export const AUDIT_FILTERS = [["all", "Any audit state"], ["open", "Not reviewed yet"], ["reviewed", "Reviewed"], ["rereview", "Needs re-review"], ["concern", "Concerns"], ["todo", "To do"]];
export function auditFilterMatch(kind, status) {
  if (kind === "open") return status === "none" || status === "todo" || status === "rereview";
  return kind === "all" || !kind ? true : status === kind;
}

/* The next symbol of a file (by line, wrapping round) that still needs a look: no mark, to do, or a review that has gone stale.
   rows: [{ qual, start, ... }]; statusOf(row) -> { status }. null when there is none. */
export function nextToReview(rows, qual, statusOf) {
  const list = rows.slice().sort((a, b) => a.start - b.start || cmp(a.qual, b.qual));
  const at = list.findIndex((r) => r.qual === qual);
  const from = at < 0 ? 0 : at + 1;
  for (let k = 0; k < list.length; k++) {
    const r = list[(from + k) % list.length];
    if (r.qual === qual) continue;
    const s = statusOf(r).status;
    if (s === "none" || s === "todo" || s === "rereview") return r;
  }
  return null;
}

/* The concerns as Markdown, ready to paste into an issue. entries: [{ mark, changed }]; link(mark) -> URL or "". */
export function concernsMarkdown(entries, { commit = "", date = "", link = () => "" } = {}) {
  const code = (s) => `\`${String(s).replace(/`/g, "'")}\``;
  const out = ["## Audit concerns", "", `${[commit ? `MiniMe census commit ${commit.slice(0, 7)}` : "", date, `${entries.length} concern${entries.length === 1 ? "" : "s"}`].filter(Boolean).join(" · ")}`, ""];
  for (const e of entries) {
    const m = e.mark;
    const lines = m.start ? ` (lines ${m.start}${m.end > m.start ? `–${m.end}` : ""})` : "";
    out.push(`- [ ] ${code(markKey(m.path, m.qual))}${lines}${m.note ? `: ${m.note}` : ""}${e.changed ? " _(the code has changed since this was flagged)_" : ""}`);
    const url = link(m);
    if (url) out.push(`  - ${url}`);
  }
  if (!entries.length) out.push("_No concerns flagged._");
  return `${out.join("\n")}\n`;
}

/* ------------------------------------------------------------------ the store */
const emptyCounts = () => ({ todo: 0, reviewed: 0, rereview: 0, concern: 0, gone: 0, unchecked: 0, marked: 0 });

/* storage: a Storage (localStorage) or null.  now: () -> ISO string (tests pass a fake clock). */
export function createAudit({ storage = null, now = () => new Date().toISOString() } = {}) {
  const hooks = new Set();
  let local = new Map();                 // key -> mark: the browser's own marks
  let shared = new Map();                // key -> mark: what the live-sync store holds (only used in shared mode)
  let sync = null;                       // the Sync object of sync.js while in shared mode
  let wired = false;
  let persistent = !!storage;
  const current = new Map();             // key -> hash | "" | null, filled by observe(); never saved
  let idx = null;                        // path -> [mark]
  let agg = null;                        // "f:<path>" | "d:<dir>" -> counts

  const read = (k) => { try { return storage ? storage.getItem(k) : null; } catch { return null; } };
  const write = (k, v) => { try { if (!storage) return false; storage.setItem(k, v); return true; } catch { return false; } };

  function loadLocal() {
    const out = new Map();
    let doc = null;
    try { doc = JSON.parse(read(KEY_AUDIT) || "null"); } catch { doc = null; }
    for (const raw of doc && Array.isArray(doc.marks) ? doc.marks : []) { const m = normalizeMark(raw); if (m) out.set(markKey(m.path, m.qual), m); }
    return out;
  }
  function saveLocal() {
    persistent = write(KEY_AUDIT, JSON.stringify({ v: 1, marks: [...local.values()].sort((a, b) => cmp(a.path, b.path) || cmp(a.qual, b.qual)) }));
    return persistent;
  }
  function loadShared() {
    const out = new Map();
    for (const rec of sync.list("audit")) {
      if (!rec || rec.deleted) continue;
      const m = normalizeMark({ ...rec, at: rec.updatedAt || rec.at });
      if (m && rec.id === auditId(m.path, m.qual)) out.set(markKey(m.path, m.qual), m);
    }
    return out;
  }

  const active = () => (sync ? shared : local);
  const changed = () => { idx = null; agg = null; for (const fn of [...hooks]) { try { fn(); } catch (e) { console.error(e); } } };

  function put(m, quiet) {
    const key = markKey(m.path, m.qual);
    if (sync) {
      const rec = sync.put("audit", { id: auditId(m.path, m.qual), ...m });
      shared.set(key, { ...m, at: rec && rec.updatedAt ? rec.updatedAt : m.at });
    } else { local.set(key, m); if (!quiet) saveLocal(); }
    if (!quiet) changed();
  }
  function drop(key) {
    const m = active().get(key);
    if (!m) return false;
    if (sync) { sync.put("audit", { id: auditId(m.path, m.qual), path: m.path, qual: m.qual, deleted: true }); shared.delete(key); } else { local.delete(key); saveLocal(); }
    changed();
    return true;
  }

  const get = (path, qual) => active().get(markKey(path, qual)) || null;
  const statusOf = (path, qual, hash) => auditStatus(active().get(markKey(path, qual)), hash !== undefined ? hash : current.get(markKey(path, qual)));

  function set(path, qual, state, info = {}) {
    if (!STATES.includes(state)) throw new RangeError(`unknown audit state: ${state}`);
    const key = markKey(path, qual);
    const old = active().get(key);
    if (!old && active().size >= LIMITS.marks) return null;
    const seen = current.get(key);
    const m = normalizeMark({
      path, qual, state, at: now(),
      note: info.note != null ? info.note : old ? old.note : "",
      hash: info.hash != null ? info.hash : typeof seen === "string" && seen ? seen : old ? old.hash : "",
      commit: info.commit != null ? info.commit : old ? old.commit : "",
      start: info.start != null ? info.start : old ? old.start : 0,
      end: info.end != null ? info.end : old ? old.end : 0,
    });
    if (!m) return null;
    put(m);
    return m;
  }

  /* What a key press does: the key of the state the symbol is in clears the mark, any other key sets that state. The one exception is
     r on a review that has gone stale, which renews it (new hash) instead of clearing it. -> "set" | "cleared" | "renewed" | "none" */
  function toggle(path, qual, state, info = {}) {
    const key = markKey(path, qual);
    const old = active().get(key);
    const st = auditStatus(old, info.hash !== undefined ? info.hash : current.get(key));
    if (old && old.state === state && !(state === "reviewed" && st.status === "rereview")) { drop(key); return "cleared"; }
    if (!set(path, qual, state, info)) return "none";
    return old && state === "reviewed" && st.status === "rereview" ? "renewed" : "set";
  }

  function setNote(path, qual, text) {
    const old = get(path, qual);
    const note = cleanNote(text);
    if (!old || old.note === note) return old;
    const m = { ...old, note, at: now() };            // the hash stays: editing a comment is not re-reading the code
    put(m);
    return m;
  }

  const clear = (path, qual) => drop(markKey(path, qual));

  function index() {
    if (!idx) { idx = new Map(); for (const m of active().values()) { if (!idx.has(m.path)) idx.set(m.path, []); idx.get(m.path).push(m); } }
    return idx;
  }

  /* Tell the store what the census says about a file now: syms = [{ qual, hash }] for every symbol of that file. Marks of the file
     whose symbol is not in the list become "gone". Fires the hooks only when some status moved. */
  function observe(path, syms) {
    const before = (index().get(path) || []).map((m) => statusOf(m.path, m.qual).status).join();
    const seen = new Set();
    for (const s of syms) { current.set(markKey(path, s.qual), s.hash || ""); seen.add(s.qual); }
    const marked = index().get(path) || [];
    for (const m of marked) if (!seen.has(m.qual)) current.set(markKey(path, m.qual), null);
    agg = null;
    if (marked.length && before !== marked.map((m) => statusOf(m.path, m.qual).status).join()) changed();
  }
  const observeRecord = (rec) => { if (rec && rec.path) observe(rec.path, [...(rec.functions || []), ...(rec.classes || [])].filter((s) => s && s.qual)); };

  function aggregate() {
    if (agg) return agg;
    agg = new Map();
    const bump = (k, st) => {
      if (!agg.has(k)) agg.set(k, emptyCounts());
      const c = agg.get(k);
      c.marked++;
      if (st.status === "gone") c.gone++; else c[st.status]++;
      if (st.unverified) c.unchecked++;
    };
    for (const m of active().values()) {
      const st = statusOf(m.path, m.qual);
      bump(`f:${m.path}`, st);
      const parts = m.path.split("/");
      bump("d:", st);
      for (let i = 1; i < parts.length; i++) bump(`d:${parts.slice(0, i).join("/")}`, st);
    }
    return agg;
  }
  const progress = (key, total) => { const c = aggregate().get(key); return c ? { ...c, total: total || 0 } : null; };

  function entries() {
    return [...active().values()].map((m) => ({ mark: m, ...statusOf(m.path, m.qual) }))
      .sort((a, b) => cmp(a.mark.path, b.mark.path) || a.mark.start - b.mark.start || cmp(a.mark.qual, b.mark.qual));
  }

  /* ---------------------------------------------- export / import */
  const exportDoc = ({ commit = "" } = {}) => ({ v: 1, app: "minime-atlas-audit", exported: now(), census: commit, marks: entries().map((e) => e.mark) });

  /* text: the JSON of an export (or a bare array of marks). Marks are merged, the newer `at` wins, nothing is deleted.
     -> { ok, error?, added, updated, same, older, invalid } */
  function importDoc(input) {
    const rep = { ok: false, added: 0, updated: 0, same: 0, older: 0, invalid: 0 };
    let doc = input;
    if (typeof input === "string") {
      if (input.length > LIMITS.file) return { ...rep, error: "That file is too large to be an audit export." };
      try { doc = JSON.parse(input); } catch { return { ...rep, error: "That is not valid JSON." }; }
    }
    const list = Array.isArray(doc) ? doc : doc && typeof doc === "object" && Array.isArray(doc.marks) ? doc.marks : null;
    if (!list) return { ...rep, error: "No \"marks\" list in that file." };
    if (doc && !Array.isArray(doc) && doc.v != null && doc.v !== 1) return { ...rep, error: `Unknown export version ${String(doc.v).slice(0, 10)}.` };
    if (list.length > LIMITS.marks) return { ...rep, error: `More than ${LIMITS.marks} marks.` };
    for (const raw of list) {
      const m = normalizeMark(raw);
      if (!m) { rep.invalid++; continue; }
      const old = active().get(markKey(m.path, m.qual));
      if (!old) { if (active().size >= LIMITS.marks) { rep.invalid++; continue; } rep.added++; put(m, true); }
      else if (ms(m.at) > ms(old.at)) { rep.updated++; put(m, true); }
      else if (JSON.stringify(m) === JSON.stringify(old)) rep.same++;
      else rep.older++;
    }
    if (!sync && (rep.added || rep.updated)) saveLocal();
    if (rep.added || rep.updated) changed();
    return { ...rep, ok: true };
  }

  /* ---------------------------------------------- shared mode */
  function useShared(Sync) {
    sync = Sync;
    write(KEY_MODE, "shared");
    shared = loadShared();
    if (!wired) {
      wired = true;
      Sync.on("change", () => { if (sync) { shared = loadShared(); changed(); } });
      Sync.on("status", () => { if (sync) changed(); });
    }
    if (typeof Sync.start === "function") Sync.start();
    changed();
  }
  function useLocal() { sync = null; write(KEY_MODE, "local"); changed(); }

  /* Local marks the shared store does not have, or has an older version of -> uploaded. Returns how many. */
  function uploadLocal() {
    if (!sync) return 0;
    let n = 0;
    for (const [key, m] of local) {
      const there = shared.get(key);
      if (there && ms(there.at) >= ms(m.at)) continue;
      put(m, true);
      n++;
    }
    if (n) changed();
    return n;
  }

  local = loadLocal();

  return {
    get, statusOf, set, toggle, setNote, clear, entries, observe, observeRecord, exportDoc, importDoc,
    fileProgress: (path, total) => progress(`f:${path}`, total),
    dirProgress: (path, total) => progress(`d:${path}`, total),
    totals: (total) => progress("d:", total) || { ...emptyCounts(), total: total || 0 },
    marksOf: (path) => (index().get(path) || []).slice(),
    size: () => active().size,
    localSize: () => local.size,
    on(fn) { hooks.add(fn); return () => hooks.delete(fn); },
    reload() { local = loadLocal(); if (sync) shared = loadShared(); changed(); },
    useShared, useLocal, uploadLocal,
    wantsShared: () => read(KEY_MODE) === "shared",
    get mode() { return sync ? "shared" : "local"; },
    get persistent() { return persistent; },
    get syncStatus() { return sync ? sync.status || "" : ""; },
  };
}
