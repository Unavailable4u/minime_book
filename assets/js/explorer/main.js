/* MiniMe Atlas 2 - Explorer page (P13). Boots explorer.html: loads the small index files, builds the tree, and shows whatever the hash
   route names. Three views share the page: the start page (#/), a folder (#/d/<folder>) and a file (#/f/<path>[::qual][@lines]).

   The data is sharded, so a file page loads exactly two small files: its shard (symbols, git dates) and its note, if it has one.
   The Source tab (P14a) loads the embedded copy of the file, data/src/<path>.txt, only when it is opened. The symbol panel (P14c: signature, parameters, calls and called-by, from the file's record, its note
   and callers/<shard>.json) is loaded when the address names a symbol; the walkthrough margin cards arrive with the next P14 patches; assets/js/links.js builds the raw / GitHub / VS Code links. */
import { h } from "./dom.js";
import { parseRoute, buildRoute } from "./router.js";
import { loadCore, loadRecord, loadRecords, loadNote, loadCallers, symbolRows, allFiles, noteStatus } from "./model.js";
import { createTree } from "./tree.js";
import { renderHome, renderDir, renderFile } from "./fileview.js";
import { renderInspector, renderHelp } from "./inspector.js";
import { loadLinkOptions, codeLinks } from "../links.js";

const KEY_W = "minime_ex_tw";
const $ = (id) => document.getElementById(id);
const DIR_SHARDS = 12;          // shards read for the Symbols tab of a folder; deeper folders have fewer
const DIR_NOTES = 60;           // note files read for it

let core;
let linkOpts = {};
let tree;
let seq = 0;
let lastKey = "";

const go = (r) => { const hash = buildRoute(r); if (location.hash === hash) route(); else location.hash = hash; };

function fail(host, msg) {
  host.replaceChildren(h("h1", null, "Explorer"), h("p", { class: "ex-err" }, msg), h("p", null, h("a", { href: "#/" }, "Back to the start page")));
}

function title(t) { document.title = `${t ? `${t} · ` : ""}Explorer · MiniMe Atlas`; }

function closeSheet() { $("ex").classList.remove("is-sheet"); $("ex-tree-btn").setAttribute("aria-expanded", "false"); }

async function route() {
  const my = ++seq;
  const main = $("ex-main");
  const insp = $("ex-insp");
  let r = parseRoute(location.hash);
  if (r.view === "auto") r = { ...r, view: core.tree.files.has(r.path) ? "file" : core.tree.dirs.has(r.path) ? "dir" : "missing" };
  if (r.view === "file" && !core.tree.files.has(r.path)) r = { ...r, view: core.tree.dirs.has(r.path) ? "dir" : "missing" };
  if (r.view === "dir" && !core.tree.dirs.has(r.path)) r = { ...r, view: "missing" };
  const wasSheet = $("ex").classList.contains("is-sheet");
  closeSheet();
  const key = `${r.view}|${r.path}`;
  const newPage = key !== lastKey;
  lastKey = key;
  if (tree.filter && r.path && !tree.filterHas(r.path)) { $("ex-q").value = ""; tree.setFilter(""); $("ex-count").textContent = ""; }
  tree.select(r.view === "missing" ? "" : r.path);

  if (r.view === "home") {
    title("");
    renderHome(main, core, { openFolder: (p) => go({ view: "dir", path: p }) });
    renderHelp(insp);
  } else if (r.view === "missing") {
    title("Not found");
    fail(main, `${r.path} is not in the census. It may be new, renamed or removed.`);
    renderHelp(insp);
  } else if (r.view === "dir") {
    const dir = core.tree.dirs.get(r.path);
    title(`${dir.name}/`);
    renderDir(main, core, dir, {
      tab: r.tab, linkOpts, setTab: (t) => go({ ...r, tab: t }), openFile: (s) => go({ view: "file", path: s.path, qual: s.qual, start: s.start, end: s.end }),
      loadSymbols: async () => {
        const files = allFiles(dir).filter((f) => !f.binary && (f.functions || f.classes));
        const { recs, more } = await loadRecords(core, files, DIR_SHARDS);
        const withNote = recs.filter((x) => noteStatus(core.notes, x.path) !== "none");
        const used = withNote.slice(0, DIR_NOTES);
        const notes = new Map((await Promise.all(used.map(async (x) => [x.path, await loadNote(x.path)]))));
        return { rows: recs.flatMap((x) => symbolRows(x, notes.get(x.path))), more, noteCap: withNote.length > DIR_NOTES ? DIR_NOTES : 0 };
      },
    });
    renderHelp(insp);
  } else {
    const file = core.tree.files.get(r.path);
    title(file.name);
    main.replaceChildren(h("p", { class: "ex-dim" }, `Loading ${file.name}…`));
    let rec = null;
    let note = null;
    let callers = null;
    try { [rec, note, callers] = await Promise.all([loadRecord(core, file), noteStatus(core.notes, file.path) === "none" ? null : loadNote(file.path), r.qual ? loadCallers(core, file).catch(() => null) : null]); }
    catch (e) { if (my === seq) { fail(main, `Could not load the data of ${file.path}: ${e.message}`); } return; }
    if (my !== seq) return;                                     // the reader has already moved on
    const rows = rec ? symbolRows(rec, note) : [];
    renderFile(main, core, file, rec, note, {
      rows, tab: r.tab, qual: r.qual, start: r.start, end: r.end, linkOpts, callers,
      // Picking lines on the Source tab rewrites the address in place: no new history entry, no page rebuild.
      onRange: (sel) => { try { history.replaceState(null, "", buildRoute({ view: "file", path: file.path, start: sel ? sel.start : null, end: sel ? sel.end : null, tab: "source" })); } catch { /* the address just stays as it was */ } },
      setTab: (t) => go({ ...r, qual: "", start: null, end: null, tab: t }),
      openFile: (s) => go({ view: "file", path: s.path, qual: s.qual, start: s.start, end: s.end, tab: "symbols" }),
    });
    renderInspector(insp, core, file, rec);
  }
  if (newPage) window.scrollTo(0, 0);
  // Keep the keyboard in the tree while the reader is browsing it (j/k then Enter, Enter, ...); otherwise move to the page.
  if (wasSheet || !$("ex-side").contains(document.activeElement)) main.focus({ preventScroll: true });
}

function initResize() {
  const ex = $("ex");
  const bar = $("ex-resize");
  const clamp = (v) => Math.max(220, Math.min(520, v));
  const set = (v, save) => {
    v = clamp(v);
    ex.style.setProperty("--ex-tw", `${v}px`);
    bar.setAttribute("aria-valuenow", String(v));
    if (save) { try { localStorage.setItem(KEY_W, String(v)); } catch { /* private mode: the width is just not remembered */ } }
  };
  let saved = 300;
  try { saved = Number(localStorage.getItem(KEY_W)) || 300; } catch { /* default width */ }
  set(saved, false);
  bar.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    bar.setPointerCapture(e.pointerId);
    const left = ex.getBoundingClientRect().left;
    const move = (ev) => set(ev.clientX - left, false);
    const up = () => { bar.removeEventListener("pointermove", move); bar.removeEventListener("pointerup", up); set(Number(bar.getAttribute("aria-valuenow")), true); tree.repaint(); };
    bar.addEventListener("pointermove", move);
    bar.addEventListener("pointerup", up);
  });
  bar.addEventListener("keydown", (e) => {
    const d = e.key === "ArrowLeft" ? -16 : e.key === "ArrowRight" ? 16 : 0;
    if (!d) return;
    e.preventDefault();
    set(Number(bar.getAttribute("aria-valuenow")) + d, true);
    tree.repaint();
  });
}

async function boot() {
  const main = $("ex-main");
  try { core = await loadCore(); } catch (e) { fail(main, `The code index could not be loaded (${e.message}). Run python scripts/serve.py and open http://localhost:8000/explorer.html; opening the file directly does not work.`); return; }
  try { linkOpts = await loadLinkOptions(); } catch { linkOpts = {}; }
  tree = createTree($("ex-tree"), {
    core,
    onOpen: (n) => go(n.kind === "dir" ? { view: "dir", path: n.path } : { view: "file", path: n.path }),
    onGithub: (f) => { const l = codeLinks({ path: f.path }, linkOpts); if (l.github) window.open(l.github, "_blank", "noopener"); },
  });
  const q = $("ex-q");
  let timer = 0;
  q.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { const n = tree.setFilter(q.value.trim()); $("ex-count").textContent = q.value.trim() ? `${n.toLocaleString("en-US")} files` : ""; }, 100); });
  q.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { q.value = ""; tree.setFilter(""); $("ex-count").textContent = ""; tree.focus(); }
    else if (e.key === "ArrowDown" || e.key === "Enter") { e.preventDefault(); tree.focus(); }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return;
    const t = e.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return;
    e.preventDefault();
    closeSheet();
    $("ex").classList.add("is-sheet");
    q.focus();
  });
  $("ex-tree-btn").addEventListener("click", () => {
    const open = $("ex").classList.toggle("is-sheet");
    $("ex-tree-btn").setAttribute("aria-expanded", String(open));
    if (open) tree.focus();
  });
  $("ex-sheet-close").addEventListener("click", closeSheet);
  initResize();
  window.addEventListener("hashchange", route);
  route();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
else boot();
