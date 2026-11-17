/* MiniMe Atlas 2 - Explorer walkthrough blocks (P14d). The AI note of a file has "blocks": 4-10 line ranges, each with a title and a
   few sentences, that walk a newcomer through the file in reading order. This module turns them into margin cards that sit beside
   the real lines on the Source tab, and works out where the reader is, so the page can say which function and which block that is.

   Two halves:
     pure (no DOM, Node can test it)   parseLineRange, alignBlocks, blockAtLine, symbolAtLine, layoutCards, nextBlock
     DOM                               createMargin (the cards and the inline headers for narrow screens), createBand (the tint behind a block)

   Why alignBlocks: a note stores line numbers, and the source can have moved a few lines since (the real notes: 86 % of the anchors
   are exactly where the note says, 10 % are a few lines off, 4 % are not found). Each block also stores the text of its first line
   (`anchor`). A block whose anchor is on its line is "ok". When it is elsewhere within SEARCH lines the block is moved there and is
   "shifted" (shown with a small mark, never silently). When it is nowhere the lines are kept as written and the block is
   "unverified". A block whose lines are past the end of the file is left out and counted in `skipped`.

   All text goes in with textContent (assets/js/explorer/dom.js h()), never as HTML. */
import { h, num } from "./dom.js";

export const SEARCH = 80;          // how far from the stated line an anchor is looked for
const GAP = 8;                      // px between two stacked cards

const norm = (s) => String(s == null ? "" : s).replace(/\s+/g, " ").trim();

/* "628-735" | "628" | "628–735" -> { start, end }; null for anything else or when end < start. */
export function parseLineRange(v) {
  const m = /^\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*$/.exec(String(v == null ? "" : v));
  if (!m) return null;
  const start = Number(m[1]);
  const end = m[2] ? Number(m[2]) : start;
  return start >= 1 && end >= start ? { start, end } : null;
}

/* How well a source line fits an anchor: 3 same text, 2 the line starts with the anchor, 1 the line contains it (anchors of 4+ characters
   only: some notes store just the name, "list_code_files", for the line "def list_code_files(ws_id: ...)"), 0 not at all. */
function fit(line, anchor) {
  if (line === anchor) return 3;
  if (line.startsWith(anchor)) return 2;
  return anchor.length >= 4 && line.includes(anchor) ? 1 : 0;
}

/* Where the anchor is: { line, tier } or null. The stated line wins when it fits at all; otherwise the nearest line within SEARCH that
   starts with the anchor (forward first on a tie), then the nearest that merely contains it. */
export function findAnchor(lines, start, anchor) {
  const a = norm(anchor);
  if (!a) return null;
  const at = (n) => (n >= 1 && n <= lines.length ? fit(norm(lines[n - 1]), a) : 0);
  const here = at(start);
  if (here >= 1) return { line: start, tier: here };
  for (const need of [2, 1]) {
    for (let d = 1; d <= SEARCH; d++) {
      for (const n of [start + d, start - d]) { const t = at(n); if (t >= need) return { line: n, tier: t }; }
    }
  }
  return null;
}

/* blocks: the note's `blocks`; lines: the source split into lines.
   -> { items, skipped }
   items    [{ id, pos, index, title, text, start, end, state: "ok" | "shifted" | "unverified", shift, given }] sorted by start; `pos` is the place in
            this sorted list, `index` the place in the note (ids stay stable when the order changes)
   skipped  [{ index, title, why: "lines" | "outside" }] blocks that could not be placed */
export function alignBlocks(blocks, lines) {
  const total = lines.length;
  const items = [];
  const skipped = [];
  (Array.isArray(blocks) ? blocks : []).forEach((b, index) => {
    if (!b || typeof b !== "object") return;
    const title = norm(b.title);
    const given = parseLineRange(b.lines);
    if (!given) { skipped.push({ index, title, why: "lines" }); return; }
    if (given.start > total) { skipped.push({ index, title, why: "outside" }); return; }
    let start = given.start;
    let end = Math.min(given.end, total);
    let state = "unverified";
    const found = findAnchor(lines, given.start, b.anchor);
    if (found) {
      state = found.line === given.start ? "ok" : "shifted";
      if (found.line !== given.start) {
        start = found.line;
        end = Math.min(total, given.end + (found.line - given.start));
        if (end < start) end = start;
      }
    }
    items.push({ id: `b${index + 1}`, pos: 0, index, title, text: String(b.text == null ? "" : b.text).trim(), start, end, state, shift: start - given.start, given });
  });
  items.sort((a, b) => a.start - b.start || a.index - b.index);
  items.forEach((it, pos) => { it.pos = pos; });
  return { items, skipped };
}

/* The block a line belongs to: of the blocks that contain it, the one that starts last (blocks can nest or overlap); null between blocks. */
export function blockAtLine(items, line) {
  let best = null;
  for (const it of items) if (it.start <= line && line <= it.end && (!best || it.start > best.start || (it.start === best.start && it.end < best.end))) best = it;
  return best;
}

/* The function, method or class that contains a line: the smallest one. rows are symbolRows() rows ({ start, end, kind, qual, ... }). */
export function symbolAtLine(rows, line) {
  let best = null;
  for (const r of rows || []) {
    if (!(r.start <= line && line <= r.end)) continue;
    if (!best || r.end - r.start < best.end - best.start) best = r;
  }
  return best;
}

/* Stacks cards that would overlap: each card goes to its wished height, or below the card before it (plus GAP).
   cards: [{ top, height }] sorted by top; -> the final tops, same order. */
export function layoutCards(cards, gap = GAP) {
  const out = [];
  let floor = -Infinity;
  for (const c of cards) {
    const top = Math.max(c.top, floor);
    out.push(top);
    floor = top + (c.height || 0) + gap;
  }
  return out;
}

/* n / p on the code: the first block that starts after `line`, or the last one that starts before it (dir +1 / -1). null at the ends. */
export function nextBlock(items, line, dir) {
  if (dir > 0) return items.find((it) => it.start > line) || null;
  for (let i = items.length - 1; i >= 0; i--) if (items[i].start < line) return items[i];
  return null;
}

/* ------------------------------------------------------------------ DOM */
const STATE = {
  shifted: (it) => ["moved", `This block is now at lines ${it.start}-${it.end}; the note said ${it.given.start}-${it.given.end}. Found by the text of its first line.`],
  unverified: () => ["not checked", "The first line of this block was not found near the lines the note gives, so its position could not be confirmed."],
};

function card(it, total, stale, cls) {
  const chips = [];
  if (STATE[it.state]) { const [label, title] = STATE[it.state](it); chips.push(h("span", { class: `ex-card__chip ex-card__chip--${it.state}`, title }, label)); }
  if (stale) chips.push(h("span", { class: "ex-card__chip ex-card__chip--stale", title: "The code changed after this note was written." }, "code changed"));
  return h("article", { class: `${cls}${stale ? " is-stale" : ""}`, dataset: { block: it.id }, "aria-label": `Walkthrough note ${it.pos + 1} of ${total}: ${it.title || "untitled"}` },
    h("header", { class: "ex-card__head" }, h("span", { class: "ex-card__n" }, `${it.pos + 1}/${total}`), h("h4", { class: "ex-card__t" }, it.title || "Untitled")),
    it.text ? h("p", { class: "ex-card__x" }, it.text) : null,
    h("p", { class: "ex-card__f" }, h("button", { type: "button", class: "ex-link", dataset: { pick: it.id } }, it.end > it.start ? `lines ${num(it.start)}–${num(it.end)}` : `line ${num(it.start)}`), chips));
}

/* The cards beside the code, plus one inline header per block for narrow screens (the page hides whichever does not apply).
   ctx: { items, stale, code, lineEl(n) -> element | undefined, drawnTo() -> last drawn line, onPick(item) }
   -> { el, headsAt(n), relayout(), scroll(top), setActive(item|null) } */
export function createMargin({ items, stale, code, lineEl, drawnTo, onPick }) {
  const el = h("div", { class: "ex-margin", role: "complementary", "aria-label": "Walkthrough notes" });
  const inner = h("div", { class: "ex-margin__in" });
  el.append(inner);
  const cards = new Map();
  const heads = new Map();
  const total = items.length;
  for (const it of items) {
    const c = card(it, total, stale, "ex-card");
    cards.set(it.id, c);
    inner.append(c);
    const head = card(it, total, stale, "ex-bhead");
    if (!heads.has(it.start)) heads.set(it.start, []);
    heads.get(it.start).push(head);
  }
  const pick = (e) => { const b = e.target.closest && e.target.closest("button[data-pick]"); if (b) { const it = items.find((x) => x.id === b.dataset.pick); if (it) onPick(it); } };
  el.addEventListener("click", pick);
  code.addEventListener("click", pick);                 // the inline headers live inside the code box

  function relayout() {
    const drawn = drawnTo();
    const shown = items.filter((it) => it.start <= drawn);
    for (const it of items) cards.get(it.id).hidden = it.start > drawn;
    const rows = shown.map((it) => { const ln = lineEl(it.start); return { it, c: cards.get(it.id), top: ln ? ln.offsetTop : 0 }; });
    rows.forEach((r) => { r.height = r.c.offsetHeight; });
    layoutCards(rows).forEach((top, i) => { rows[i].c.style.top = `${Math.round(top)}px`; });
  }
  const scroll = (top) => { inner.style.transform = `translateY(${-Math.round(top)}px)`; };
  /* The wheel over the cards scrolls the code, like the wheel over the code does; at either end it is left to the page. */
  el.addEventListener("wheel", (e) => {
    const max = code.scrollHeight - code.clientHeight;
    if ((e.deltaY < 0 && code.scrollTop > 0) || (e.deltaY > 0 && code.scrollTop < max - 1)) { e.preventDefault(); code.scrollTop += e.deltaY; }
  }, { passive: false });
  function setActive(it) {
    for (const [id, c] of cards) { const on = !!it && id === it.id; c.classList.toggle("is-active", on); if (on) c.setAttribute("aria-current", "true"); else c.removeAttribute("aria-current"); }
    for (const list of heads.values()) for (const hd of list) hd.classList.toggle("is-active", !!it && hd.dataset.block === it.id);
  }
  return { el, headsAt: (n) => heads.get(n) || [], relayout, scroll, setActive };
}

/* A tint behind the lines of one block, drawn inside the code box. */
export function createBand(code, lineEl) {
  const el = h("div", { class: "ex-band", hidden: true, "aria-hidden": "true" });
  code.append(el);
  return {
    show(start, end) {
      const a = lineEl(start);
      const b = lineEl(end) || a;
      if (!a) { el.hidden = true; return; }
      el.style.top = `${a.offsetTop}px`;
      el.style.height = `${Math.max(0, b.offsetTop + b.offsetHeight - a.offsetTop)}px`;
      el.hidden = false;
    },
    hide() { el.hidden = true; },
  };
}
