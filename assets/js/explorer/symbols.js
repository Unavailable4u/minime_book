/* MiniMe Atlas 2 - Explorer symbols table (P13). Every function, method and class of a file or a folder, sortable and filterable.

   Each row: kind, signature, one line of description with its source named (AI note / docstring / "no description yet"), a freshness
   mark, size and complexity, and the three ways to the code: this page, GitHub, VS Code. 200 rows are drawn at a time; "Show more" adds
   200, so a folder with 10,000 test functions stays light. Sorting and filtering work on the whole list, not on what is drawn. */
import { h, clear, num } from "./dom.js";
import { SORTS, filterSymbols } from "./model.js";
import { buildRoute } from "./router.js";
import { codeLinks } from "../links.js";

const PAGE = 200;
const KINDS = [["all", "All kinds"], ["function", "Functions"], ["method", "Methods"], ["class", "Classes"], ["component", "Components"], ["hook", "Hooks"]];
const FROM = { note: ["AI note", "mm-badge mm-badge--ai"], doc: ["docstring", "ex-from"], none: ["", "ex-from"] };

export function createSymbols({ rows, showPath, linkOpts, selected, onOpen }) {
  const S = { q: "", kind: "all", sort: showPath ? "name" : "line", noteOnly: false, hideTests: false, shown: PAGE, rows };
  const root = h("div", { class: "ex-sym" });
  const count = h("p", { class: "ex-sym__count", "aria-live": "polite" });
  const list = h("ol", { class: "ex-sym__list" });
  const more = h("button", { type: "button", class: "mm-btn ex-sym__more", hidden: true }, "Show more");

  const q = h("input", { type: "search", class: "ex-q", placeholder: showPath ? "Filter symbols by name, file or description" : "Filter symbols", "aria-label": "Filter symbols", autocomplete: "off" });
  const kind = h("select", { class: "ex-sel", "aria-label": "Kind" }, KINDS.map(([v, l]) => h("option", { value: v }, l)));
  const sort = h("select", { class: "ex-sel", "aria-label": "Sort by" }, Object.entries(SORTS).map(([v, o]) => h("option", { value: v }, `Sort: ${o.label}`)));
  sort.value = S.sort;
  const noteOnly = h("input", { type: "checkbox" });
  const hideTests = h("input", { type: "checkbox" });
  const tools = h("div", { class: "ex-sym__tools", role: "search" }, q, kind, sort,
    h("label", { class: "ex-check" }, noteOnly, " Has AI note"), h("label", { class: "ex-check" }, hideTests, " Hide tests"));
  root.append(tools, count, list, more);

  function link(r) {
    return codeLinks({ path: r.path, start: r.start, end: r.end }, linkOpts || {});
  }

  function rowEl(r) {
    const l = link(r);
    const [fromLabel, fromCls] = FROM[r.from];
    const sel = selected && r.qual === selected;
    const li = h("li", { class: `ex-sym__row${sel ? " is-selected" : ""}`, id: `sym-${r.path}::${r.qual}`, dataset: { qual: r.qual } });
    li.append(h("div", { class: "ex-sym__head" },
      h("span", { class: `ex-kind ex-kind--${r.kind}`, title: r.kind }, r.kind === "class" ? "C" : r.kind === "method" ? "m" : r.kind === "component" ? "◇" : r.kind === "hook" ? "↪" : "f"),
      h("a", { class: "ex-sym__sig", href: buildRoute({ view: "file", path: r.path, qual: r.qual, start: r.start, end: r.end, tab: "symbols" }), onclick: (e) => { if (onOpen) { e.preventDefault(); onOpen(r); } } }, r.sig),
      r.fresh === "fresh" ? h("span", { class: "ex-mark ex-mark--fresh", title: "AI note matches the current code", "aria-label": "note is fresh" })
        : r.fresh === "stale" ? h("span", { class: "ex-mark ex-mark--stale", title: "Code changed since the note was written", "aria-label": "note is stale" })
        : r.fresh === "unverified" ? h("span", { class: "ex-mark ex-mark--unverified", title: "Note has no code hash yet, so freshness is unknown", "aria-label": "note freshness unknown" }) : null));
    li.append(r.desc
      ? h("p", { class: "ex-sym__desc" }, r.desc, " ", fromLabel ? h("span", { class: fromCls }, fromLabel) : null)
      : h("p", { class: "ex-sym__desc ex-sym__desc--none" }, "no description yet"));
    const meta = h("p", { class: "ex-sym__meta" });
    if (showPath) meta.append(h("a", { href: buildRoute({ view: "file", path: r.path }) }, r.path), " · ");
    meta.append(`lines ${r.start}–${r.end} · ${num(r.loc)} loc`, r.cc != null ? ` · cc ${r.cc}` : "", r.visibility === "private" ? " · private" : "");
    li.append(meta);
    const go = h("p", { class: "ex-sym__go" });
    go.append(h("a", { class: "ex-sym__view", href: buildRoute({ view: "file", path: r.path, qual: r.qual, start: r.start, end: r.end, tab: "source" }) }, "View source"));
    if (l.src) go.append(h("a", { href: l.src, target: "_blank", rel: "noopener" }, "Raw source"));
    if (l.github) go.append(h("a", { href: l.github, target: "_blank", rel: "noopener" }, "GitHub"));
    if (l.vscode) go.append(h("a", { href: l.vscode }, "VS Code"));
    if (go.childNodes.length) li.append(go);
    return li;
  }

  function paint() {
    let out = filterSymbols(S.rows, S);
    out = out.slice().sort(SORTS[S.sort].cmp);
    clear(list);
    const slice = out.slice(0, S.shown);
    const sel = selected ? slice.find((r) => r.qual === selected) : null;
    slice.forEach((r) => list.append(rowEl(r)));
    count.textContent = out.length === S.rows.length ? `${num(out.length)} symbols` : `${num(out.length)} of ${num(S.rows.length)} symbols`;
    more.hidden = out.length <= S.shown;
    more.textContent = `Show ${num(Math.min(PAGE, out.length - S.shown))} more`;
    if (!out.length) list.append(h("li", { class: "ex-sym__empty" }, S.rows.length ? "No symbol matches that filter." : "This file defines no functions or classes."));
    return sel;
  }

  let timer = 0;
  q.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { S.q = q.value.trim(); S.shown = PAGE; paint(); }, 120); });
  kind.addEventListener("change", () => { S.kind = kind.value; S.shown = PAGE; paint(); });
  sort.addEventListener("change", () => { S.sort = sort.value; S.shown = PAGE; paint(); });
  noteOnly.addEventListener("change", () => { S.noteOnly = noteOnly.checked; S.shown = PAGE; paint(); });
  hideTests.addEventListener("change", () => { S.hideTests = hideTests.checked; S.shown = PAGE; paint(); });
  more.addEventListener("click", () => { S.shown += PAGE; paint(); });

  paint();
  return {
    el: root,
    setRows(rs) { S.rows = rs; paint(); },
    focusFilter() { q.focus(); },
    /* Bring the row of `qual` into view (and past the page limit when it is further down). */
    reveal(qual, scroll = true) {
      selected = qual;
      let out = filterSymbols(S.rows, S).slice().sort(SORTS[S.sort].cmp);
      const at = out.findIndex((r) => r.qual === qual);
      if (at >= S.shown) S.shown = Math.ceil((at + 1) / PAGE) * PAGE;
      paint();
      const el = [...list.children].find((li) => li.dataset && li.dataset.qual === qual);
      if (el) { if (scroll) el.scrollIntoView({ block: "center" }); el.classList.add("is-selected"); }
    },
  };
}
