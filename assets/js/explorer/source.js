/* MiniMe Atlas 2 - Explorer Source tab (P14a). The real code of a file, from the copy that scripts/refresh_source.py made under data/src/.

   renderSource(panel, ctx) fills the tab panel. What it shows:
     - the file with line numbers, the selected lines marked, and the selection kept in the address (#/f/<path>@120-141?tab=source)
     - how to change the selection: click a line number, Shift+click for a range, "Go to line", Esc clears it
     - Raw source / GitHub / VS Code buttons for the selected lines (assets/js/links.js builds them)
     - a warning when the line numbers can not be trusted (copy and census from different commits, note written for another version)
   When the file has no embedded copy (not in the manifest, embedSource off, or the fetch fails) the tab says so and still gives the
   GitHub / VS Code buttons plus what the census knows about the file or symbol, so it is never an empty tab.

   Lines are drawn 1,000 at a time ("Show more lines"); the biggest embedded file has about 5,500. Text goes in with textContent only.
   Syntax colours (P14b): the plain text is shown at once; assets/js/explorer/highlight.js then loads the vendored highlight.js
   in the background and the lines are re-drawn as coloured segments (still text nodes, never HTML). A "Syntax colours" checkbox
   turns them off (remembered). If the engine is missing or the file is not code, nothing changes and no checkbox appears.
   Walkthrough (P14d): when the file's AI note has "blocks", each one is a card in a column beside the lines it explains (assets/js/explorer/
   blocks.js aligns them to the real lines and re-anchors the ones that moved). Under 760 px the cards become headers inside the code.
   A bar above the code says which function (or class) and which block the reader is in, and follows the scroll. "Walkthrough notes"
   turns the cards off (remembered). n / p in the code jump to the next / previous block. The symbol panel is P14c. */
import { h, num, copyText, toast } from "./dom.js";
import { buildRoute } from "./router.js";
import { getText, splitLines, clampRange, parseGoto, sourceNotices, noteDrifted, noteStatus, signature, symbolRows } from "./model.js";
import { codeLinks } from "../links.js";
import { highlightLines } from "./highlight.js";
import { alignBlocks, blockAtLine, symbolAtLine, nextBlock, createMargin, createBand } from "./blocks.js";

const CHUNK = 1000;
const KEY_WRAP = "minime_ex_wrap";
const KEY_HL = "minime_ex_hl";
const KEY_NOTES = "minime_ex_notes";
const NARROW = 760;               // px of viewer width under which the cards move from the margin into the code

const readWrap = () => { try { return localStorage.getItem(KEY_WRAP) === "1"; } catch { return false; } };
const saveWrap = (on) => { try { localStorage.setItem(KEY_WRAP, on ? "1" : "0"); } catch { /* private mode: not remembered */ } };
const readHl = () => { try { return localStorage.getItem(KEY_HL) !== "0"; } catch { return true; } };   // on unless the reader turned it off
const saveHl = (on) => { try { localStorage.setItem(KEY_HL, on ? "1" : "0"); } catch { /* private mode: not remembered */ } };
const readNotes = () => { try { return localStorage.getItem(KEY_NOTES) !== "0"; } catch { return true; } };   // on unless the reader turned it off
const saveNotes = (on) => { try { localStorage.setItem(KEY_NOTES, on ? "1" : "0"); } catch { /* private mode: not remembered */ } };

/* ------------------------------------------------------------------ buttons */
function linkButtons(file, linkOpts, range) {
  const wrap = h("p", { class: "ex-go ex-src__go" });
  const a = (label, extra) => { const el = h("a", { class: "mm-btn", rel: "noopener", ...extra }, label); wrap.append(el); return el; };
  const raw = a("Raw source", { target: "_blank" });
  const gh = a("GitHub", { target: "_blank" });
  const vs = a("VS Code");
  const update = (r) => {
    const l = codeLinks({ path: file.path, start: r ? r.start : null, end: r ? r.end : null }, linkOpts || {});
    for (const [el, href] of [[raw, l.src], [gh, l.github], [vs, l.vscode]]) { if (href) el.setAttribute("href", href); else el.removeAttribute("href"); el.hidden = !href; }
  };
  update(range);
  return { el: wrap, update, any: () => !raw.hidden || !gh.hidden || !vs.hidden };
}

/* ------------------------------------------------------------------ the viewer */
/* ctx.range = { start, end } or null; ctx.onRange(range|null) is told when the reader changes the selection.
   ctx.noteBlocks = the note's `blocks` (or nothing), ctx.rows = symbolRows() of the file, ctx.stale = the note is for another version of the code. */
export function createSource({ file, text, range, qual, linkOpts, notices = [], onRange, noteBlocks = null, rows = [], stale = false }) {
  const lines = splitLines(text);
  const total = lines.length;
  const { items, skipped } = alignBlocks(noteBlocks, lines);
  let sel = range ? clampRange(range.start, range.end, total) : null;
  let anchor = sel ? sel.start : null;
  let drawn = 0;
  const els = [];                                  // els[n] = the element of line n; kept here because the view is built before it is in the page

  const root = h("div", { class: "ex-src" });
  notices.forEach((n) => root.append(h("p", { class: "ex-callout ex-callout--warn" }, n.text)));
  if (skipped.length) root.append(h("p", { class: "ex-callout" }, `${skipped.length} walkthrough note${skipped.length === 1 ? "" : "s"} could not be placed (${skipped.map((k) => `${k.title || "untitled"}: ${k.why === "outside" ? "its lines are past the end of this file" : "its line range is not valid"}`).join("; ")}). They are still in the Explain tab.`));

  const info = h("p", { class: "ex-src__info", "aria-live": "polite" });
  const gotoInput = h("input", { type: "text", class: "ex-q ex-src__goto", placeholder: "Go to line", "aria-label": "Go to line or line range", inputmode: "numeric", autocomplete: "off", size: "10" });
  const wrapBox = h("input", { type: "checkbox" });
  const hlBox = h("input", { type: "checkbox" });
  const hlLabel = h("label", { class: "ex-check", hidden: true }, hlBox, " Syntax colours");   // shown once colours exist for this file
  const notesBox = h("input", { type: "checkbox" });
  const notesLabel = h("label", { class: "ex-check", hidden: !items.length }, notesBox, " Walkthrough notes");
  const copyBtn = h("button", { type: "button", class: "mm-btn" }, "Copy");
  const linkBtn = h("button", { type: "button", class: "mm-btn" }, "Copy link");
  const buttons = linkButtons(file, linkOpts, sel);
  const form = h("form", { class: "ex-src__tools", role: "search", onsubmit: (e) => {
    e.preventDefault();
    const r = parseGoto(gotoInput.value, total);
    if (!r) { toast(`Enter a line from 1 to ${num(total)}, or a range like 120-141`); return; }
    choose(r, true);
  } }, gotoInput, h("label", { class: "ex-check" }, wrapBox, " Wrap lines"), hlLabel, notesLabel, copyBtn, linkBtn);

  const code = h("div", { class: "ex-code", role: "region", "aria-label": `Source of ${file.name}`, tabindex: "0" });
  const more = h("button", { type: "button", class: "mm-btn ex-src__more", hidden: true });
  const now = h("p", { class: "ex-src__now", hidden: true, "aria-label": "Where you are in the file" });   // the explain bar: function + block under the reader
  const body = h("div", { class: "ex-src__body" }, code);
  root.classList.toggle("has-notes", items.length > 0);
  root.append(form, info, buttons.el, now, body, more);

  let tokens = null;                               // per-line coloured segments from highlight.js, once they have arrived
  const textKids = (n) => (tokens ? tokens[n - 1].map((seg) => (seg.c ? h("span", { class: seg.c }, seg.t) : seg.t)) : [lines[n - 1]]);

  const lineEl = (n) => h("div", { class: "ex-line", id: `ex-L${n}` },
    h("a", { class: "ex-line__n", href: buildRoute({ view: "file", path: file.path, start: n, tab: "source" }), "aria-label": `Line ${n}`, dataset: { n } }, String(n)),
    h("span", { class: "ex-line__t" }, textKids(n)));

  /* Walkthrough cards (P14d). Built only when the note has blocks that could be placed; everything below is a no-op without them. */
  const margin = items.length ? createMargin({ items, stale, code, lineEl: (n) => els[n], drawnTo: () => drawn, onPick: (it) => pickBlock(it) }) : null;
  const band = createBand(code, (n) => els[n]);
  if (margin) body.append(margin.el);
  let cursor = null;                               // block the reader jumped to (n / p / a card); cleared by scrolling away from where the jump landed
  let cursorTop = 0;                               // scrollTop right after that jump (the browser may have clamped it)
  let raf = 0;

  function draw(upTo) {
    const to = Math.min(total, Math.max(upTo, drawn));
    if (to <= drawn) return;
    const frag = document.createDocumentFragment();
    for (let n = drawn + 1; n <= to; n++) {
      if (margin) for (const hd of margin.headsAt(n)) frag.append(hd);
      els[n] = lineEl(n);
      frag.append(els[n]);
    }
    code.append(frag);
    drawn = to;
    more.hidden = drawn >= total;
    more.textContent = `Show ${num(Math.min(CHUNK, total - drawn))} more lines (${num(total - drawn)} not shown)`;
    schedule();
  }

  let marked = [];
  function paint() {
    marked.forEach((el) => el.classList.remove("is-sel"));
    marked = [];
    if (sel) {
      for (let n = sel.start; n <= Math.min(sel.end, drawn); n++) {
        els[n].classList.add("is-sel");
        marked.push(els[n]);
      }
    }
    const what = [`${num(total)} line${total === 1 ? "" : "s"}`];
    if (sel) what.push(sel.end > sel.start ? `lines ${num(sel.start)}–${num(sel.end)} selected` : `line ${num(sel.start)} selected`);
    if (qual && sel) what.push(qual);
    if (items.length) what.push(`${items.length} walkthrough note${items.length === 1 ? "" : "s"}`);
    info.textContent = what.join(" · ");
    copyBtn.textContent = sel ? (sel.end > sel.start ? "Copy lines" : "Copy line") : "Copy file";
    buttons.update(sel);
  }

  function choose(r, scroll) {
    sel = r;
    anchor = r ? r.start : null;
    if (r) draw(r.end + 200);
    paint();
    if (r && scroll && els[r.start]) els[r.start].scrollIntoView({ block: "center" });
    if (onRange) onRange(sel);
  }

  /* ---- walkthrough: where the reader is, and moving between blocks ---- */
  /* The line at the top of the code box: the first line whose bottom edge is below a point 1 px under the top of the box. */
  function readingLine() {
    if (!drawn || code.scrollTop <= 0) return 1;
    const probe = code.scrollTop + 1;
    let lo = 1;
    let hi = drawn;
    while (lo < hi) { const mid = (lo + hi) >> 1; const e = els[mid]; if (e.offsetTop + e.offsetHeight > probe) hi = mid; else lo = mid + 1; }
    return lo;
  }
  const lastNow = { key: null };
  function updateNow() {
    raf = 0;
    const line = cursor != null && items[cursor] ? items[cursor].start : readingLine();
    const it = cursor != null && items[cursor] ? items[cursor] : blockAtLine(items, line);
    const row = symbolAtLine(rows, line);
    if (margin) margin.setActive(it);
    if (it) band.show(it.start, Math.min(it.end, drawn)); else band.hide();
    const key = `${row ? row.qual : ""}|${it ? it.id : ""}`;
    if (key === lastNow.key) return;
    lastNow.key = key;
    now.hidden = !rows.length && !items.length;
    now.replaceChildren(h("span", null,
      row ? [h("span", { class: "ex-pill" }, row.kind), " ", h("code", { class: "ex-src__q" }, row.qual), h("span", { class: "ex-dim" }, ` lines ${num(row.start)}–${num(row.end)}`),
        row.desc ? [" · ", row.desc, " ", h("span", { class: row.from === "note" ? "mm-badge mm-badge--ai" : "ex-from" }, row.from === "note" ? "AI note" : "docstring")] : null,
        " ", h("a", { class: "ex-link", href: buildRoute({ view: "file", path: file.path, qual: row.qual, tab: "symbols" }) }, "Open symbol")]
        : h("span", { class: "ex-dim" }, line <= 1 && !it ? "Top of the file, outside any function or class" : "Outside any function or class"),
      it ? h("span", { class: "ex-src__blk" }, " · walkthrough: ", h("b", null, it.title || "untitled")) : null));
  }
  function schedule() {
    if (margin) margin.relayout();
    if (raf) return;
    raf = typeof requestAnimationFrame === "function" ? requestAnimationFrame(updateNow) : (updateNow(), 0);
  }
  const hasNow = rows.length > 0 || items.length > 0;
  code.addEventListener("scroll", () => {
    if (margin) margin.scroll(code.scrollTop);
    if (cursor != null && Math.abs(code.scrollTop - cursorTop) > 2) cursor = null;   // moved by hand: back to following the scroll position
    if (hasNow && !raf) raf = typeof requestAnimationFrame === "function" ? requestAnimationFrame(updateNow) : (updateNow(), 0);
  }, { passive: true });

  /* Put the first line of a block at the top of the code box (the box scrolls, not the page). */
  function jumpTo(it) {
    draw(it.start + 50);
    const el = els[it.start];
    if (!el) return;
    code.scrollTop = Math.max(0, el.offsetTop - 2);
    cursorTop = code.scrollTop;
    cursor = it.pos;
    updateNow();
  }
  function pickBlock(it) { choose({ start: it.start, end: it.end }, false); jumpTo(it); }
  code.addEventListener("keydown", (e) => {
    if (!items.length || e.ctrlKey || e.metaKey || e.altKey || (e.key !== "n" && e.key !== "p")) return;
    e.preventDefault();
    const dir = e.key === "n" ? 1 : -1;
    const it = cursor != null ? items[cursor + dir] : nextBlock(items, readingLine(), dir);
    if (it) jumpTo(it); else toast(dir > 0 ? "That was the last walkthrough note" : "That is the first walkthrough note");
  });

  /* A click on a line number: select that line; Shift+click extends from the line clicked before; clicking the only selected line clears. */
  code.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a.ex-line__n");
    if (!a || !code.contains(a)) return;
    e.preventDefault();
    const n = Number(a.dataset.n);
    if (e.shiftKey && anchor != null) choose(clampRange(Math.min(anchor, n), Math.max(anchor, n), total), false);
    else if (sel && sel.start === n && sel.end === n) choose(null, false);
    else { choose(clampRange(n, n, total), false); anchor = n; }
  });
  code.addEventListener("keydown", (e) => { if (e.key === "Escape" && sel) { e.preventDefault(); choose(null, false); } });
  more.addEventListener("click", () => { draw(drawn + CHUNK); paint(); });

  const setWrap = (on) => { code.classList.toggle("is-wrap", on); schedule(); };
  const setNotes = (on) => { root.classList.toggle("is-notes-off", !on); schedule(); };
  notesBox.checked = readNotes();
  setNotes(notesBox.checked);
  notesBox.addEventListener("change", () => { setNotes(notesBox.checked); saveNotes(notesBox.checked); });
  if (typeof ResizeObserver === "function") {
    new ResizeObserver((entries) => {
      const w = entries[0] && entries[0].contentRect ? entries[0].contentRect.width : root.clientWidth;
      if (w > 0) root.classList.toggle("is-narrow", w < NARROW);
      schedule();
    }).observe(root);
  }
  const setHl = (on) => { code.classList.toggle("is-hl", !!tokens && on); };
  hlBox.checked = readHl();
  hlBox.addEventListener("change", () => { setHl(hlBox.checked); saveHl(hlBox.checked); });
  wrapBox.checked = readWrap();
  setWrap(wrapBox.checked);
  wrapBox.addEventListener("change", () => { setWrap(wrapBox.checked); saveWrap(wrapBox.checked); });

  copyBtn.addEventListener("click", async () => {
    const part = sel ? lines.slice(sel.start - 1, sel.end) : lines;
    toast((await copyText(part.join("\n"))) ? `Copied ${num(part.length)} line${part.length === 1 ? "" : "s"}` : "Could not copy");
  });
  linkBtn.addEventListener("click", async () => {
    const hash = buildRoute({ view: "file", path: file.path, start: sel ? sel.start : null, end: sel ? sel.end : null, tab: "source" });
    toast((await copyText(`${location.href.split("#")[0]}${hash}`)) ? "Link copied" : "Could not copy");
  });

  draw(Math.max(CHUNK, sel ? sel.end + 200 : 0));
  paint();
  /* Colours arrive after the plain text: swap the content of the lines already drawn (the text itself never changes). */
  function setTokens(result) {
    if (!result || result.lines.length !== total) return;
    tokens = result.lines;
    for (let n = 1; n <= drawn; n++) els[n].lastChild.replaceChildren(...textKids(n));
    code.dataset.lang = result.lang;
    hlLabel.hidden = false;
    hlLabel.title = `Coloured as ${result.lang} (highlight.js)`;
    setHl(hlBox.checked);
  }

  schedule();
  return { el: root, lines, setTokens, blocks: items, jumpToBlock: (pos) => { if (items[pos]) pickBlock(items[pos]); }, reveal() { if (sel && els[sel.start]) els[sel.start].scrollIntoView({ block: "center" }); }, selection: () => sel };
}

/* ------------------------------------------------------------------ when there is no source to show */
function symbolOf(rec, qual) {
  if (!rec || !qual) return null;
  const f = (rec.functions || []).find((s) => s.qual === qual);
  if (f) return { ...f, kind: f.kind || "function" };
  const c = (rec.classes || []).find((s) => s.qual === qual);
  return c ? { ...c, kind: "class" } : null;
}

function fallback(panel, { reason, file, rec, qual, start, end, linkOpts }) {
  panel.replaceChildren(h("p", { class: "ex-callout" }, reason));
  const btns = linkButtons(file, linkOpts, clampRange(start, end, Number.MAX_SAFE_INTEGER));
  if (btns.any()) panel.append(btns.el);
  else panel.append(h("p", { class: "ex-dim" }, "No link can be made yet: the commit is unknown and no local MiniMe folder is set (link icon in the top bar)."));
  const sym = symbolOf(rec, qual);
  if (sym) {
    panel.append(h("h3", { class: "ex-src__h" }, `${sym.qual}${sym.start ? ` · lines ${sym.start}–${sym.end}` : ""}`), h("pre", { class: "ex-pre" }, signature(sym)));
    if (sym.doc1) panel.append(h("p", null, sym.doc1, " ", h("span", { class: "ex-from" }, "docstring")));
  } else if (rec && rec.module_doc) {
    panel.append(h("h3", { class: "ex-src__h" }, "Module docstring"), h("pre", { class: "ex-pre" }, rec.module_doc));
  }
}

/* ------------------------------------------------------------------ the tab */
/* ctx: { core, file, rec, note, qual, start, end, linkOpts, onRange } */
export function renderSource(panel, ctx) {
  const { core, file, rec, note, qual, start, end, linkOpts = {}, onRange } = ctx;
  const where = { file, rec, qual, start, end, linkOpts };
  if (file.binary) { fallback(panel, { ...where, reason: "This is a binary file, so there is no source text to show." }); return; }
  const src = codeLinks({ path: file.path }, linkOpts).src;
  if (!src) {
    fallback(panel, { ...where, reason: linkOpts.srcFiles ? "This file is not in the embedded source copy (it may be too large, listed in data/src-denylist.txt, or refused by the secret scan)." : "This Atlas was built without an embedded copy of the source (data/src/manifest.json is missing or embedSource is off)." });
    return;
  }
  panel.replaceChildren(h("p", { class: "ex-dim" }, `Loading the source of ${file.name}…`));
  getText(src).then((text) => {
    const notices = sourceNotices({ path: file.path, note, srcFiles: linkOpts.srcFiles, copyCommit: linkOpts.commit, censusCommit: core && core.tree && core.tree.commit });
    const stale = noteStatus(core && core.notes, file.path) === "stale" || noteDrifted({ path: file.path, note, srcFiles: linkOpts.srcFiles });
    const view = createSource({ file, text, range: start ? { start, end } : null, qual, linkOpts, notices, onRange, noteBlocks: note && note.blocks, rows: rec ? symbolRows(rec, note) : [], stale });
    panel.replaceChildren(view.el);
    view.reveal();
    highlightLines(view.lines, file.path).then((result) => view.setTokens(result));   // colours are an extra: a null answer leaves the plain text
  }).catch((e) => fallback(panel, { ...where, reason: `The source could not be loaded (${e.message}).` }));
}
