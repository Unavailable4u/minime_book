/* MiniMe Atlas 2 - drawing helpers shared by the API and Agents pages (P17). Browser only: it builds DOM and fetches JSON, while the pure
   logic (filtering, sorting, KPIs, bar widths, links) lives in codepages.js, which Node tests. Every piece of text goes in with
   textContent (through h()), never as HTML, so a path, a docstring or a note can not inject markup. */
import { h } from "./explorer/dom.js";
import { bookMentions } from "./explorer/backlinks.js";
import { fmtN, filterRows, sortRows, barWidths, noteState, noteFile, pickSymbol } from "./codepages.js";

const BASE = new URL("../../", import.meta.url);
const cache = new Map();

/* One fetch per file per page. A failure is not cached, so the next call tries again. */
export function getJSON(rel) {
  if (!cache.has(rel)) {
    cache.set(rel, fetch(new URL(rel, BASE)).then((r) => { if (!r.ok) throw new Error(`${rel}: ${r.status}`); return r.json(); }).catch((e) => { cache.delete(rel); throw e; }));
  }
  return cache.get(rel);
}

export const empty = (text) => h("p", { class: "cp-empty" }, text);

/* kind: ok | stale | ai | reviewed | here (the shapes are the Atlas's: circle fresh, diamond stale, square AI-written) */
export const badge = (kind, text, title) => h("span", { class: `mm-badge mm-badge--${kind}`, title: title || null }, text);

export function kpiGrid(kpis) {
  return h("div", { class: "cp-kpis" }, kpis.map((k) => h("div", { class: "mm-card mm-kpi" }, h("span", { class: "mm-kpi__value" }, fmtN(k.value)), h("span", { class: "mm-kpi__label" }, k.label))));
}

/* items: [{ name, title, n }]; href(item) is optional and makes the label a link. */
export function barsCard(title, items, { note = "", href = null } = {}) {
  const w = barWidths(items);
  return h("section", { class: "mm-card cp-bars" }, h("h3", { class: "mm-card__title" }, title),
    h("ul", { class: "cp-bars__list" }, items.map((it, i) => {
      const to = href ? href(it) : null;
      return h("li", { class: "cp-bar" }, to ? h("a", { href: to, title: it.title }, it.name) : h("span", { title: it.title }, it.name),
        h("i", { style: `width:${w[i]}%`, "aria-hidden": "true" }), h("em", null, fmtN(it.n)));
    })), note ? h("p", { class: "cp-dim cp-bars__note" }, note) : null);
}

export function freshLine(parts) {
  const stale = parts.some((p) => p.stale);
  return h("p", { class: "cp-fresh", "data-state": stale ? "stale" : "ok" }, parts.map((p, i) => h("span", { class: p.stale ? "cp-fresh__stale" : null }, i ? " · " : "", p.text)));
}

export const section = (title, ...kids) => h("section", { class: "cp-sec" }, h("h3", null, title), kids);

/* links: { explorer, src, github, vscode } (any may be missing). */
export function linkRow(links) {
  const a = (href, text, ext) => (href ? h("a", { class: "mm-btn", href, target: ext ? "_blank" : null, rel: ext ? "noopener" : null }, text) : null);
  return h("div", { class: "cp-links" }, a(links.explorer, "Open in Explorer"), a(links.src, "Source"), a(links.github, "GitHub", true), a(links.vscode, "VS Code"));
}

export function copyButton(text, label = "Copy") {
  const b = h("button", { type: "button", class: "mm-btn" }, label);
  b.addEventListener("click", async () => {
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; } catch { ok = false; }
    b.textContent = ok ? "Copied" : "Copy failed";
    setTimeout(() => { b.textContent = label; }, 1400);
  });
  return b;
}

const list = (items) => h("ul", { class: "cp-list" }, items.map((x) => h("li", null, x)));

/* The AI note for a file, and for one function of it when `qual` is given. Always labelled AI-written, with its freshness. */
export function noteSection({ path, qual = "", title = "What it does" }) {
  const body = h("div", null, h("p", { class: "cp-dim" }, "Loading the note…"));
  const sec = h("section", { class: "cp-sec" }, h("h3", null, title, " ", badge("ai", "AI-written")), body);
  (async () => {
    let index = null;
    try { index = await getJSON("data/index/notes.json"); } catch { index = null; }
    const state = noteState(index, path);
    if (state === "none") { body.replaceChildren(h("p", { class: "cp-dim" }, "No AI note for this file yet. The Explorer still shows its census facts (signature, docstring, calls).")); return; }
    let note = null;
    try { note = await getJSON(noteFile(path)); } catch { note = null; }
    if (!note) { body.replaceChildren(h("p", { class: "cp-dim" }, "The note file could not be loaded.")); return; }
    const sym = qual ? pickSymbol(note, qual) : null;
    const kids = [h("p", { class: "cp-badges" },
      state === "stale" ? badge("stale", "code changed since the note", "The file's source changed after this note was written; it may no longer be true.") : badge("ok", "fresh"),
      sym && sym.confidence ? badge("here", `${sym.confidence} confidence`) : null)];
    if (sym) {
      kids.push(h("p", { class: "cp-lede" }, sym.summary || ""));
      if (sym.details) kids.push(h("p", null, sym.details));
      if ((sym.params || []).length) kids.push(h("p", { class: "cp-label" }, "Parameters"), list(sym.params.map((p) => [h("code", null, p.name), p.desc ? ` – ${p.desc}` : ""])));
      if (sym.returns) kids.push(h("p", null, h("span", { class: "cp-label" }, "Returns "), sym.returns));
      if ((sym.raises || []).length) kids.push(h("p", null, h("span", { class: "cp-label" }, "Raises "), sym.raises.map((r, i) => [i ? ", " : "", h("code", null, r)])));
      if ((sym.side_effects || []).length) kids.push(h("p", { class: "cp-label" }, "Side effects"), list(sym.side_effects));
    } else {
      if (qual) kids.push(h("p", { class: "cp-dim" }, `No note for ${qual}() itself; this is the note for its file.`));
      kids.push(h("p", { class: "cp-lede" }, note.summary || ""));
      if (note.purpose) kids.push(h("p", null, note.purpose));
      if ((note.how_it_works || []).length) kids.push(h("p", { class: "cp-label" }, "How it works"), list(note.how_it_works.slice(0, 8)));
      if ((note.gotchas || []).length) kids.push(h("p", { class: "cp-label" }, "Gotchas"), list(note.gotchas.slice(0, 6)));
    }
    body.replaceChildren(...kids);
  })();
  return sec;
}

/* "Discussed in the book": the chapter sections whose <code> text names this file (or this function of it). */
export function bookSection({ path, qual = "" }) {
  const body = h("div", null, h("p", { class: "cp-dim" }, "Looking for mentions…"));
  const sec = h("section", { class: "cp-sec" }, h("h3", null, "Discussed in the book"), body);
  (async () => {
    let doc = null;
    try { doc = await getJSON("data/index/mentions.json"); } catch { doc = null; }
    const ms = bookMentions(doc, path, qual);
    if (!ms.length) { body.replaceChildren(h("p", { class: "cp-dim" }, "No chapter section names it in a <code> span.")); return; }
    const row = (m) => h("li", null, h("a", { href: m.url }, m.chapter, m.heading ? ` › ${m.heading}` : ""), m.sym ? [" ", h("code", null, m.sym)] : null);
    const ul = h("ul", { class: "cp-list" }, ms.slice(0, 8).map(row));
    const kids = [ul];
    if (ms.length > 8) {
      const more = h("button", { type: "button", class: "cp-linkbtn" }, `Show all ${ms.length} mentions`);
      more.addEventListener("click", () => { ul.replaceChildren(...ms.map(row)); more.remove(); });
      kids.push(more);
    }
    body.replaceChildren(...kids);
  })();
  return sec;
}

/* A filterable, sortable table. cols: [{ id, label, get(row), num?, mono?, render?(row) }]. onPick(row) runs on click, Enter and Space. */
export function makeTable({ cols, rows, key, filterText, onPick, placeholder = "Filter…", pageSize = 300 }) {
  const st = { q: "", col: null, asc: true, limit: pageSize, sel: "" };
  const input = h("input", { type: "search", class: "mm-input cp-filter", placeholder, "aria-label": placeholder });
  const count = h("span", { class: "cp-dim", "aria-live": "polite" });
  const thead = h("thead");
  const tbody = h("tbody");
  const more = h("button", { type: "button", class: "mm-btn" }, "Show more");
  const wrap = h("div", { class: "mm-tablewrap cp-tablewrap" }, h("table", { class: "mm-table is-compact" }, thead, tbody));
  const el = h("div", { class: "cp-table" }, h("div", { class: "mm-toolbar" }, input, count), wrap, more);

  const current = () => {
    const found = filterRows(rows, st.q, filterText);
    const c = cols.find((x) => x.id === st.col);
    return c ? sortRows(found, c.get, st.asc) : found;
  };
  const head = () => {
    thead.replaceChildren(h("tr", null, cols.map((c) => {
      const th = h("th", { scope: "col", class: c.num ? "is-num" : null, "aria-sort": st.col === c.id ? (st.asc ? "ascending" : "descending") : null });
      const b = h("button", { type: "button" }, c.label);
      b.addEventListener("click", () => { st.asc = st.col === c.id ? !st.asc : !c.num; st.col = c.id; head(); draw(); });
      th.append(b);
      return th;
    })));
  };
  const mark = () => {
    for (const tr of tbody.children) tr.setAttribute("aria-selected", String(tr.dataset.key === st.sel));
    const on = tbody.querySelector('[aria-selected="true"]');
    if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
  };
  const draw = () => {
    const all = current();
    const shown = all.slice(0, st.limit);
    tbody.replaceChildren(...shown.map((r) => {
      const tr = h("tr", { tabindex: "0", "data-key": key(r), "aria-selected": String(key(r) === st.sel) },
        cols.map((c) => { const v = c.get(r); return h("td", { class: [c.num ? "is-num" : "", c.mono ? "is-mono" : ""].join(" ").trim() || null }, c.render ? c.render(r) : typeof v === "number" ? fmtN(v) : v == null ? "" : String(v)); }));
      tr.addEventListener("click", (e) => { if (!e.target.closest("a")) onPick(r); });
      tr.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && e.target === tr) { e.preventDefault(); onPick(r); } });
      return tr;
    }));
    more.hidden = all.length <= st.limit;
    count.textContent = `${fmtN(all.length)} of ${fmtN(rows.length)} rows`;
  };
  input.addEventListener("input", () => { st.q = input.value; st.limit = pageSize; draw(); });
  more.addEventListener("click", () => { st.limit += 500; draw(); });
  head();
  draw();
  return { el, input, select(k) { st.sel = k || ""; mark(); } };
}
