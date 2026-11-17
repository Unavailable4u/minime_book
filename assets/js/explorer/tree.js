/* MiniMe Atlas 2 - Explorer tree (P13). A virtualised, keyboard-driven tree of every file in the census.

   Only the rows in view are in the DOM (ROW_H pixels each, plus a few above and below), so 1,190 files and 100 folders cost nothing
   to scroll. The container is one ARIA tree: focus stays on it and aria-activedescendant names the row the cursor is on.

     j / ArrowDown, k / ArrowUp   move the cursor          Home / End   first / last row
     l / ArrowRight               open a folder, or step into it     h / ArrowLeft   close a folder, or step out to its parent
     Enter / Space                open the file or folder page       o   open the file at GitHub (the census commit)

   Folder rows carry four dots: how many of the files that want an AI note have one (data/index/notes.json). File rows carry a mark
   when a note exists: a circle for fresh, a diamond for stale (shape as well as colour). */
import { h, clear } from "./dom.js";
import { flatten, coverage, noteStatus, ancestors } from "./model.js";

export const ROW_H = 28;
const OVERSCAN = 8;

export function createTree(host, { core, onOpen, onGithub }) {
  const expanded = new Set();
  let filter = "";
  let rows = [];
  let cursor = 0;
  let selected = "";
  let raf = 0;

  host.classList.add("ex-tree");
  host.setAttribute("role", "tree");
  host.setAttribute("aria-label", "Repository files");
  host.tabIndex = 0;
  const spacer = h("div", { class: "ex-tree__space" });
  const win = h("div", { class: "ex-tree__win" });
  spacer.append(win);
  host.append(spacer);

  function rebuild(keepPath) {
    rows = flatten(core.tree.root, expanded, filter);
    spacer.style.height = `${rows.length * ROW_H}px`;
    const at = keepPath ? rows.findIndex((r) => r.node.path === keepPath) : -1;
    if (at >= 0) cursor = at; else cursor = Math.min(cursor, Math.max(0, rows.length - 1));
    paint();
  }

  function rowEl(r, i) {
    const n = r.node;
    const isDir = n.kind === "dir";
    const open = isDir && (filter ? true : expanded.has(n.path));
    const el = h("div", {
      class: `ex-row${i === cursor ? " is-cursor" : ""}${n.path === selected ? " is-selected" : ""}${isDir ? " is-dir" : ""}`,
      id: `ex-ti-${i}`, role: "treeitem", "aria-level": r.depth + 1, "aria-selected": n.path === selected ? "true" : "false",
      "aria-expanded": isDir ? String(open) : null, style: `top:${i * ROW_H}px;height:${ROW_H}px;padding-left:${6 + r.depth * 14}px`, title: n.path,
    });
    el.append(h("span", { class: "ex-row__twist", "aria-hidden": "true" }, isDir ? (open ? "▾" : "▸") : ""));
    el.append(h("span", { class: "ex-row__name" }, n.name + (isDir ? "/" : "")));
    if (isDir) {
      const c = coverage(core.notes, n.path);
      if (c) {
        const dots = h("span", { class: "ex-dots", "aria-label": `${c.noted} of ${c.files} files have a note`, title: `${c.noted} of ${c.files} files have a note` });
        for (let k = 0; k < 4; k++) dots.append(h("i", { class: k < c.dots ? "is-on" : "" }));
        el.append(dots);
      }
    } else {
      const st = noteStatus(core.notes, n.path);
      if (st !== "none") el.append(h("span", { class: `ex-mark ex-mark--${st}`, title: st === "fresh" ? "AI note, up to date" : "AI note, code changed since", "aria-label": st === "fresh" ? "has a fresh note" : "has a stale note" }));
    }
    el.addEventListener("click", (e) => {
      cursor = i;
      if (isDir && e.target.closest(".ex-row__twist")) { toggle(n.path); return; }
      activate(i);
    });
    return el;
  }

  function paint() {
    cancelAnimationFrame(raf);
    const top = host.scrollTop;
    const first = Math.max(0, Math.floor(top / ROW_H) - OVERSCAN);
    const last = Math.min(rows.length, Math.ceil((top + host.clientHeight) / ROW_H) + OVERSCAN);
    clear(win);
    for (let i = first; i < last; i++) win.append(rowEl(rows[i], i));
    if (!rows.length) win.append(h("p", { class: "ex-tree__none" }, "No file matches that filter."));
    const cur = rows[cursor];
    if (cur && cursor >= first && cursor < last) host.setAttribute("aria-activedescendant", `ex-ti-${cursor}`); else host.removeAttribute("aria-activedescendant");
  }
  const schedule = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(paint); };

  function toggle(path, force) {
    const want = force == null ? !expanded.has(path) : force;
    if (want) expanded.add(path); else expanded.delete(path);
    rebuild(path);
  }

  function activate(i) {
    const r = rows[i];
    if (!r) return;
    if (r.node.kind === "dir") { if (!filter) toggle(r.node.path, !expanded.has(r.node.path)); onOpen(r.node); }
    else onOpen(r.node);
  }

  function reveal() {
    const el = rows[cursor];
    if (!el) return;
    const top = cursor * ROW_H;
    if (top < host.scrollTop) host.scrollTop = top;
    else if (top + ROW_H > host.scrollTop + host.clientHeight) host.scrollTop = top + ROW_H - host.clientHeight;
    paint();
  }

  function move(to) {
    cursor = Math.max(0, Math.min(rows.length - 1, to));
    reveal();
  }

  host.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  host.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const r = rows[cursor];
    const k = e.key;
    const handled = () => { e.preventDefault(); e.stopPropagation(); };
    if (k === "ArrowDown" || k === "j") { handled(); move(cursor + 1); }
    else if (k === "ArrowUp" || k === "k") { handled(); move(cursor - 1); }
    else if (k === "Home") { handled(); move(0); }
    else if (k === "End") { handled(); move(rows.length - 1); }
    else if (k === "PageDown") { handled(); move(cursor + Math.floor(host.clientHeight / ROW_H) - 1); }
    else if (k === "PageUp") { handled(); move(cursor - Math.floor(host.clientHeight / ROW_H) + 1); }
    else if ((k === "ArrowRight" || k === "l") && r) {
      handled();
      if (r.node.kind === "dir" && !filter) { if (!expanded.has(r.node.path)) toggle(r.node.path, true); else move(cursor + 1); }
    } else if ((k === "ArrowLeft" || k === "h") && r) {
      handled();
      if (r.node.kind === "dir" && expanded.has(r.node.path) && !filter) toggle(r.node.path, false);
      else { const p = r.node.parent && r.node.parent.path; const at = rows.findIndex((x) => x.node.path === p && p); if (at >= 0) move(at); }
    } else if ((k === "Enter" || k === " ") && r) { handled(); activate(cursor); }
    else if (k === "o" && r && r.node.kind === "file") { handled(); onGithub(r.node); }
  });

  return {
    /* Show `path` as the selected row: open the folders above it, put the cursor on it and scroll it into view. */
    select(path) {
      selected = path || "";
      if (path) {
        const above = path === "" ? [] : ancestors(path);
        const isDir = core.tree.dirs.has(path) && path !== "";
        if (isDir) above.push(path);
        above.forEach((p) => expanded.add(p));
      }
      rows = flatten(core.tree.root, expanded, filter);
      spacer.style.height = `${rows.length * ROW_H}px`;
      const at = rows.findIndex((r) => r.node.path === selected);
      if (at >= 0) { cursor = at; reveal(); } else paint();
    },
    setFilter(q) { filter = q; cursor = 0; host.scrollTop = 0; rebuild(); return rows.filter((r) => r.node.kind === "file").length; },
    get filter() { return filter; },
    /* true when the current filter still shows this path (a folder shows when a file below it matches). */
    filterHas(path) { return flatten(core.tree.root, expanded, filter).some((r) => r.node.path === path); },
    focus() { host.focus(); },
    repaint: schedule,
  };
}
