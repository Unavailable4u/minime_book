/* MiniMe Atlas 2 - Explorer main pane (P13): the start page, a folder page and a file page. Each render function fills `host`
   and returns nothing; the data it needs is loaded by main.js. A page that has no AI note still shows everything the census knows
   about the file; it just says plainly that the note is missing and offers the prompt that writes one. */
import { h, num, day, copyText, toast } from "./dom.js";
import { buildRoute } from "./router.js";
import { coverage, noteStatus, notePrompt, allFiles } from "./model.js";
import { createSymbols } from "./symbols.js";
import { renderSource } from "./source.js";
import { renderSymbolPanel } from "./symbol.js";
import { docViewFor, renderDocView, DOC_LABEL } from "./docview.js";
import { codeLinks } from "../links.js";
import { bookMentions, renderBackrefs } from "./backlinks.js";
import { progressEl, AUDIT_HASH } from "./auditui.js";

/* ------------------------------------------------------------------ pieces */
function crumbs(path, isFile) {
  const parts = path ? path.split("/") : [];
  const nav = h("nav", { class: "ex-crumbs", "aria-label": "Location" }, h("a", { href: buildRoute({ view: "home" }) }, "repo"));
  parts.forEach((p, i) => {
    const sub = parts.slice(0, i + 1).join("/");
    nav.append(h("span", { "aria-hidden": "true" }, "/"));
    nav.append(i === parts.length - 1 ? h("span", { "aria-current": "page" }, p) : h("a", { href: buildRoute({ view: "dir", path: sub }) }, p));
  });
  return nav;
}

function tabs(items, active, onPick) {
  const bar = h("div", { class: "ex-tabs", role: "tablist" });
  items.forEach(([id, label]) => bar.append(h("button", {
    type: "button", role: "tab", id: `ex-tab-${id}`, "aria-selected": String(id === active), "aria-controls": "ex-panel", tabindex: id === active ? "0" : "-1",
    onclick: () => onPick(id),
    onkeydown: (e) => {
      const i = items.findIndex((x) => x[0] === id);
      const to = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : -1;
      if (to >= 0 && to < items.length) { e.preventDefault(); onPick(items[to][0]); setTimeout(() => document.getElementById(`ex-tab-${items[to][0]}`)?.focus(), 0); }
    },
  }, label)));
  return bar;
}

const kv = (rows) => h("dl", { class: "ex-kv" }, rows.filter((r) => r[1] != null && r[1] !== "").flatMap(([k, v]) => [h("dt", null, k), h("dd", null, v)]));

function noteMark(status) {
  return status === "none" ? null : h("span", { class: `ex-mark ex-mark--${status}`, title: status === "fresh" ? "AI note, up to date" : "AI note, code changed since", "aria-label": status === "fresh" ? "has a fresh note" : "has a stale note" });
}

function coverDots(c) {
  if (!c) return null;
  const d = h("span", { class: "ex-dots", title: `${c.noted} of ${c.files} files that want a note have one`, "aria-label": `${c.noted} of ${c.files} files have a note` });
  for (let k = 0; k < 4; k++) d.append(h("i", { class: k < c.dots ? "is-on" : "" }));
  return d;
}

function codeButtons(file, linkOpts, start, end) {
  const l = codeLinks({ path: file.path, start, end }, linkOpts || {});
  const out = h("p", { class: "ex-go" });
  if (l.src) out.append(h("a", { class: "mm-btn", href: l.src, target: "_blank", rel: "noopener" }, "Raw source"));
  if (l.github) out.append(h("a", { class: "mm-btn", href: l.github, target: "_blank", rel: "noopener" }, "GitHub"));
  if (l.vscode) out.append(h("a", { class: "mm-btn", href: l.vscode }, "VS Code"));
  out.append(h("button", { type: "button", class: "mm-btn", onclick: async () => toast((await copyText(file.path)) ? "Path copied" : "Could not copy") }, "Copy path"));
  return out;
}

/* ------------------------------------------------------------------ start page */
export function renderHome(host, core, { openFolder, audit = null }) {
  const t = core.tree;
  const n = t.root.n;
  host.replaceChildren(
    h("h1", null, "Explorer"),
    h("p", { class: "ex-lede" }, "Every file of MiniMe, from the folder down to the function. Pick a folder on the left, or press ", h("kbd", null, "Ctrl+K"), " and type a file or function name."),
    h("p", { class: "ex-totals" },
      h("span", null, h("b", null, num(n.files)), " files"), h("span", null, h("b", null, num(n.functions)), " functions"), h("span", null, h("b", null, num(n.classes)), " classes"),
      h("span", null, h("b", null, num(n.lines)), " lines"),
      core.notes && core.notes.totals ? h("span", null, h("b", null, num(core.notes.totals.noted)), ` of ${num(core.notes.totals.files)} files have an AI note`) : null),
    h("p", { class: "ex-src" }, `Census of ${t.generated || "?"}, commit ${(t.commit || "").slice(0, 7) || "?"}.`));
  if (audit) {                                                  // P16: how much of the code has been read
    const a = audit.totals(n.functions + n.classes);
    host.append(h("p", { class: "ex-auditline" }, h("b", null, "Audit: "),
      a.marked ? `${num(a.reviewed)} of ${num(a.total)} symbols reviewed${a.rereview ? `, ${num(a.rereview)} need re-review` : ""}${a.concern ? `, ${num(a.concern)} concern${a.concern === 1 ? "" : "s"}` : ""}${a.todo ? `, ${num(a.todo)} to do` : ""}. ` : "nothing marked yet. ",
      h("a", { href: AUDIT_HASH }, "Open the audit page")));
  }
  const grid = h("div", { class: "ex-folders" });
  for (const d of t.root.dirs) {
    grid.append(h("a", { class: "ex-folder", href: buildRoute({ view: "dir", path: d.path }), onclick: (e) => { e.preventDefault(); openFolder(d.path); } },
      h("span", { class: "ex-folder__name" }, `${d.name}/`), coverDots(coverage(core.notes, d.path)),
      h("span", { class: "ex-folder__n" }, `${num(d.n.files)} files · ${num(d.n.lines)} lines · ${num(d.n.functions)} functions`)));
  }
  host.append(h("h2", null, "Folders"), grid);
  const files = allFiles(t.root).filter((f) => !f.binary && !f.test);
  const top = (key, k) => files.slice().sort((a, b) => b[key] - a[key] || (a.path < b.path ? -1 : 1)).slice(0, k);
  const mk = (title, rows, fmt) => h("section", { class: "ex-top" }, h("h2", null, title), h("ol", null, rows.map((f) => h("li", null, h("a", { href: buildRoute({ view: "file", path: f.path }) }, f.path), h("span", { class: "ex-dim" }, ` ${fmt(f)}`)))));
  host.append(h("div", { class: "ex-tops" }, mk("Largest files", top("lines", 10), (f) => `${num(f.lines)} lines`), mk("Most changed", top("commits", 10), (f) => `${num(f.commits)} commits`)));
}

/* ------------------------------------------------------------------ folder page */
const COLS = [["name", "Name"], ["lines", "Lines"], ["functions", "Functions"], ["classes", "Classes"], ["commits", "Commits"], ["last", "Last change"]];

export function renderDir(host, core, dir, { tab, setTab, loadSymbols, linkOpts, openFile, audit = null }) {
  const c = coverage(core.notes, dir.path);
  host.replaceChildren(
    crumbs(dir.path, false),
    h("h1", null, `${dir.name}/`),
    h("p", { class: "ex-totals" }, h("span", null, h("b", null, num(dir.n.files)), " files"), h("span", null, h("b", null, num(dir.n.lines)), " lines"),
      h("span", null, h("b", null, num(dir.n.functions)), " functions"), h("span", null, h("b", null, num(dir.n.classes)), " classes"),
      c ? h("span", null, coverDots(c), ` ${c.noted} of ${c.files} files have an AI note`) : null,
      audit && audit.dirProgress(dir.path, dir.n.functions + dir.n.classes) ? h("span", null, progressEl(audit.dirProgress(dir.path, dir.n.functions + dir.n.classes)), " symbols reviewed") : null));
  const active = tab === "symbols" ? "symbols" : "explain";
  host.append(tabs([["explain", "Folders and files"], ["symbols", "Symbols"]], active, setTab));
  const panel = h("div", { class: "ex-panel", id: "ex-panel", role: "tabpanel", "aria-labelledby": `ex-tab-${active}` });
  host.append(panel);
  if (active === "symbols") {
    panel.append(h("p", { class: "ex-dim" }, "Loading the symbols of this folder…"));
    loadSymbols().then(({ rows, more, noteCap }) => {
      panel.replaceChildren();
      if (more > 0) panel.append(h("p", { class: "ex-callout" }, `This folder has ${more} more data shard${more === 1 ? "" : "s"} than the page loads at once. Open a subfolder to see every symbol in it.`));
      if (noteCap) panel.append(h("p", { class: "ex-dim" }, `AI summaries are shown for the first ${noteCap} files that have a note; the rest show their docstring.`));
      panel.append(createSymbols({ rows, showPath: true, linkOpts, onOpen: (r) => openFile(r), audit }).el);
    }).catch((e) => { panel.replaceChildren(h("p", { class: "ex-err" }, `Could not load the symbols: ${e.message}`)); });
    return;
  }
  const state = { key: "kind", dir: 1 };
  const table = h("table", { class: "mm-table is-compact ex-table" });
  const body = h("tbody");
  const head = h("tr");
  COLS.forEach(([k, label]) => head.append(h("th", { class: k === "name" || k === "last" ? "" : "is-num", scope: "col" }, h("button", { type: "button", onclick: () => { state.dir = state.key === k ? -state.dir : k === "name" ? 1 : -1; state.key = k; paint(); } }, label))));
  head.append(h("th", { scope: "col" }, "Note"));
  table.append(h("thead", null, head), body);
  function paint() {
    const kids = [...dir.dirs, ...dir.files];
    const val = (n) => (state.key === "name" ? n.name : state.key === "last" ? n.last || "" : (n.kind === "dir" ? n.n[state.key] : n[state.key]) ?? 0);
    kids.sort((a, b) => {
      if (state.key === "kind") return (a.kind === b.kind ? 0 : a.kind === "dir" ? -1 : 1) || (a.name < b.name ? -1 : 1);
      const x = val(a), y = val(b);
      return (x < y ? -1 : x > y ? 1 : 0) * state.dir || (a.name < b.name ? -1 : 1);
    });
    [...head.children].forEach((th, i) => { const k = COLS[i] && COLS[i][0]; if (k && k === state.key) th.setAttribute("aria-sort", state.dir > 0 ? "ascending" : "descending"); else th.removeAttribute("aria-sort"); });
    body.replaceChildren(...kids.map((n) => {
      const isDir = n.kind === "dir";
      const m = isDir ? n.n : n;
      return h("tr", null,
        h("td", null, h("a", { href: buildRoute({ view: isDir ? "dir" : "file", path: n.path }) }, isDir ? `${n.name}/` : n.name)),
        h("td", { class: "is-num" }, num(m.lines)), h("td", { class: "is-num" }, num(m.functions)), h("td", { class: "is-num" }, num(m.classes)),
        h("td", { class: "is-num" }, isDir ? "" : num(m.commits)), h("td", null, isDir ? "" : day(m.last)),
        h("td", null, isDir ? coverDots(coverage(core.notes, n.path)) : noteMark(noteStatus(core.notes, n.path))));
    }));
  }
  paint();
  panel.append(h("div", { class: "mm-tablewrap ex-tablewrap" }, table));
}

/* ------------------------------------------------------------------ file page */
const list = (items) => (items && items.length ? h("ul", { class: "ex-list" }, items.map((x) => h("li", null, String(x)))) : null);

function section(title, content) {
  return content ? h("section", { class: "ex-sec" }, h("h3", null, title), content) : null;
}

function explain(file, rec, note) {
  const out = h("div", { class: "ex-explain" });
  const put = (...secs) => secs.forEach((x) => { if (x) out.append(x); });     // Node.append(null) would write the text "null"
  if (note) {
    put(
      section("Purpose", note.purpose ? h("p", null, note.purpose) : null),
      section("How it works", note.how_it_works && note.how_it_works.length ? h("ol", { class: "ex-list" }, note.how_it_works.map((x) => h("li", null, x))) : null),
      section("Inputs", list(note.inputs)), section("Outputs", list(note.outputs)), section("Side effects", list(note.side_effects)),
      section("Things to watch", list(note.gotchas)),
      section("Not clear from the code", list(note.unknowns)),
      section("Concepts", note.concepts && note.concepts.length ? h("p", { class: "ex-chips" }, note.concepts.map((c) => h("code", null, c))) : null));
    const blocks = (note.blocks || []).map((b) => {
      const m = /^(\d+)(?:-(\d+))?$/.exec(String(b.lines || ""));
      const href = m ? buildRoute({ view: "file", path: file.path, start: Number(m[1]), end: m[2] ? Number(m[2]) : null, tab: "source" }) : null;
      return h("li", null, href ? h("a", { href }, `lines ${b.lines}`) : `lines ${b.lines}`, " ", h("b", null, b.title || ""), b.text ? h("span", { class: "ex-dim" }, ` ${b.text}`) : null);
    });
    put(section("Walkthrough", blocks.length ? h("div", null,
      h("p", { class: "ex-dim" }, "Each block is a stretch of the file, in reading order. ", h("a", { class: "mm-btn", href: buildRoute({ view: "file", path: file.path, tab: "source" }) }, "Read it beside the code")),
      h("ol", { class: "ex-blocks" }, blocks)) : null));
  }
  const exports = rec && rec.exports && rec.exports.length ? h("p", { class: "ex-chips" }, rec.exports.slice(0, 40).map((e) => h("code", null, e))) : null;
  put(section("Exports", exports));
  const doc = rec && rec.module_doc;
  put(section("Module docstring", doc ? h("details", { open: !note }, h("summary", null, doc.split("\n")[0].slice(0, 120) || "show"), h("pre", { class: "ex-pre" }, doc)) : null));
  if (!out.childNodes.length) out.append(h("p", { class: "ex-dim" }, "Nothing besides the numbers above is known about this file yet."));
  return out;
}

export function renderFile(host, core, file, rec, note, { rows, tab, qual, setTab, linkOpts, openFile, start, end, onRange, callers = null, book = null, audit = null, commit = "" }) {
  const status = noteStatus(core.notes, file.path);
  const entry = core.notes && core.notes.files && core.notes.files[file.path];
  const badges = h("p", { class: "ex-badges" }, h("span", { class: "ex-pill" }, file.lang || "file"), file.test ? h("span", { class: "ex-pill" }, "test") : null,
    entry ? h("span", { class: "ex-pill" }, `T${entry.tier}`) : null,
    note ? h("span", { class: "mm-badge mm-badge--ai" }, "AI-written") : null,
    status === "fresh" ? h("span", { class: "mm-badge mm-badge--ok" }, "note fresh") : status === "stale" ? h("span", { class: "mm-badge mm-badge--stale" }, "code changed since note") : h("span", { class: "mm-badge" }, "no note yet"));
  host.replaceChildren(crumbs(file.path, true), h("h1", { class: "ex-file" }, file.name), badges);

  const summary = h("div", { class: "ex-summary" });
  if (note && note.summary) {
    summary.append(h("p", { class: "ex-summary__text" }, note.summary), h("p", { class: "ex-summary__by" }, `AI-written ${note.written ? day(note.written) : ""}${note.commit ? `, against commit ${note.commit.slice(0, 7)}` : ""}. Written by Copilot from reading the code; check it against the source.`));
    if (status === "stale") summary.append(h("p", { class: "ex-callout ex-callout--warn" }, "The code of this file has changed since the note was written. Read the note as a hint, not as a fact."));
  } else {
    const first = rec && rec.module_doc ? rec.module_doc.split(/\n\s*\n/)[0].replace(/\s+/g, " ").trim() : "";
    summary.append(h("p", { class: "ex-summary__text ex-summary__text--none" }, "No AI note for this file yet."));
    if (first) summary.append(h("p", { class: "ex-summary__doc" }, first.length > 300 ? `${first.slice(0, 300)}…` : first, " ", h("span", { class: "ex-from" }, "module docstring")));
    if (!file.binary) summary.append(h("p", null, h("button", { type: "button", class: "mm-btn", onclick: async () => toast((await copyText(notePrompt(file.path))) ? "Prompt copied. Paste it into Copilot, in the MiniMe repository." : "Could not copy") }, "Copy the Copilot prompt for this file")));
  }
  host.append(summary);

  const m = rec || {};
  host.append(kv([
    ["Lines", `${num(file.lines)} (${num(file.code)} code${m.comment != null ? `, ${num(m.comment)} comment` : ""}${m.blank != null ? `, ${num(m.blank)} blank` : ""})`],
    ["Functions", file.functions ? num(file.functions) : ""], ["Classes", file.classes ? num(file.classes) : ""],
    ["Commits", file.commits ? `${num(file.commits)}, last ${day(file.last)}` : ""], ["Size", m.size != null ? `${num(m.size)} bytes` : ""],
  ]), codeButtons(file, linkOpts, start, end));
  const backrefs = renderBackrefs(bookMentions(book, file.path, qual));      // P15: the chapter sections that mention this file / symbol
  if (backrefs) host.append(backrefs);

  const syms = rows || [];
  const kind = docViewFor(file, linkOpts);                                   // Markdown, JSON, SQL with an embedded copy: one more tab, first (P14e)
  const items = [...(kind ? [["view", DOC_LABEL[kind]]] : []), ["explain", "Explain"], ...(file.binary ? [] : [["source", "Source"]]), ["symbols", `Symbols (${num(syms.length)})`]];
  // An explicit tab wins; otherwise a symbol opens the Symbols tab and a bare line range opens the Source tab.
  const active = items.some((x) => x[0] === tab) ? tab : qual ? "symbols" : start ? "source" : kind ? "view" : "explain";
  host.append(tabs(items, active, setTab));
  const panel = h("div", { class: "ex-panel", id: "ex-panel", role: "tabpanel", "aria-labelledby": `ex-tab-${active}` });
  host.append(panel);
  if (active === "view") renderDocView(panel, { core, file, kind, linkOpts });
  else if (active === "explain") panel.append(explain(file, rec, note));
  else if (active === "source") renderSource(panel, { core, file, rec, note, qual, start, end, linkOpts, onRange });
  else {
    // A named symbol gets its panel (signature, parameters, calls, called by) above the list; the list keeps it highlighted.
    const row = qual ? syms.find((r) => r.qual === qual) : null;
    const sym = row && rec ? [...(rec.functions || []), ...(rec.classes || [])].find((s) => s.qual === qual) : null;
    if (qual && !sym) panel.append(h("p", { class: "ex-callout ex-callout--warn" }, `This file has no function or class named ${qual} in the census. It may have been renamed or removed since.`));
    if (sym) {
      const isTest = (p) => { const f = core.tree.files.get(p); return !!(f && f.test); };
      panel.append(renderSymbolPanel({ file, files: core.tree.files, linkOpts, openSymbol: (path, q) => openFile({ path, qual: q }), audit, rows: syms, commit }, { sym: row.kind === "class" ? { ...sym, kind: "class" } : sym, row, callers, isTest, rec }));
    }
    const t = createSymbols({ rows: syms, showPath: false, linkOpts, selected: qual, onOpen: (r) => openFile(r), audit });
    panel.append(t.el);
    if (qual) t.reveal(qual, !sym);
  }
}
