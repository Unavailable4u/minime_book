/* MiniMe Atlas 2 - the book's Tables page (P18). tables.html keeps its table cards (they are copied from the book guides); this
   module replaces the inline script it had. It adds, on top of what the page did before:
     - a filter box that matches every word, in any order, across a card (dataviews.matchWords),
     - category buttons whose counts are counted from the cards on the page, so they can not drift from them,
     - a "N of M tables" line, and a message when nothing matches,
     - sortable column headers on every table (numbers by value, text by letter, empty cells last), using compareCells.
   The cards' own markup is not rewritten: a table is only re-ordered, never re-built. The pure logic is in dataviews.js (Node tests it). */
import { matchWords, compareCells, categoryCounts, fmtN } from "./dataviews.js";

const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function tag(main) {
  /* each <h2> names a guide and, in a <span class="l">, its category; the cards after it belong to that category */
  $$("h2", main).filter((h) => h.parentElement === main).forEach((h) => {
    const sp = h.querySelector("span.l");
    const cat = sp ? sp.textContent.trim() : "MiniMe core";
    h.dataset.catHdr = cat;
    for (let n = h.nextElementSibling; n && n.tagName === "DETAILS"; n = n.nextElementSibling) n.dataset.cat = cat;
  });
}

function sortable(details) {
  for (const table of $$("table", details)) {
    const head = table.rows[0];
    if (!head || !head.querySelector("th")) continue;
    const body = () => Array.from(table.rows).slice(1);
    const state = { col: -1, asc: true };
    Array.from(head.cells).forEach((th, i) => {
      const label = th.textContent;
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.title = `Sort by ${label}`;
      th.replaceChildren(b);
      th.scope = "col";
      b.addEventListener("click", () => {
        state.asc = state.col === i ? !state.asc : true;
        state.col = i;
        Array.from(head.cells).forEach((c, j) => { if (j === i) c.setAttribute("aria-sort", state.asc ? "ascending" : "descending"); else c.removeAttribute("aria-sort"); });
        const rows = body().map((tr, k) => ({ tr, k, text: tr.cells[i] ? tr.cells[i].textContent : "" }));
        rows.sort((a, c) => compareCells(a.text, c.text, state.asc) || a.k - c.k);   /* stable: equal cells keep the page's own order */
        const parent = head.parentNode;
        rows.forEach((r) => parent.append(r.tr));
      });
    });
  }
}

function init() {
  const main = document.querySelector("main");
  const input = document.getElementById("sq");
  const bar = document.getElementById("tb-cat-bar");
  if (!main || !input || !bar) return;
  tag(main);
  const cards = $$("details.tb", main);
  const text = new Map(cards.map((d) => [d, d.textContent.toLowerCase()]));
  const names = new Map($$("button.tb-fbtn", bar).map((b) => [b.dataset.c, b.textContent.replace(/\s*\(\d+\)\s*$/, "")]));
  const counts = categoryCounts(cards.map((d) => d.dataset.cat || "MiniMe core"));
  const expand = document.getElementById("tb-exp");

  const status = document.createElement("p");
  status.className = "tb-count";
  status.setAttribute("aria-live", "polite");
  const none = document.createElement("p");
  none.className = "tb-empty";
  none.hidden = true;
  none.textContent = "No table matches. Try fewer words, or pick All tables.";
  bar.after(status, none);

  let cat = "all", open = false;
  const buttons = counts.map((c) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tb-fbtn" + (c.id === "all" ? " on" : "");
    b.dataset.c = c.id;
    b.textContent = `${c.id === "all" ? "All tables" : names.get(c.id) || c.id} (${fmtN(c.n)})`;
    b.addEventListener("click", () => { cat = c.id; buttons.forEach((x) => x.classList.toggle("on", x === b)); apply(); });
    return b;
  });
  bar.replaceChildren(...buttons, ...(expand ? [expand] : []));
  const total = document.getElementById("tb-total");
  if (total) total.textContent = fmtN(cards.length);

  function apply() {
    const q = input.value;
    let shown = 0;
    $$("h2[data-cat-hdr]", main).forEach((h) => {
      let any = false;
      for (let n = h.nextElementSibling; n && n.tagName === "DETAILS"; n = n.nextElementSibling) {
        const ok = (cat === "all" || n.dataset.cat === cat) && matchWords(text.get(n), q);
        n.hidden = !ok;
        if (ok) { any = true; shown += 1; if (q.trim()) n.open = true; }
      }
      h.hidden = !any;
    });
    status.textContent = `${fmtN(shown)} of ${fmtN(cards.length)} tables shown`;
    none.hidden = shown > 0;
  }
  input.addEventListener("input", apply);
  if (expand) expand.addEventListener("click", () => { open = !open; cards.forEach((d) => { if (!d.hidden) d.open = open; }); });
  cards.forEach(sortable);
  apply();
}

init();
