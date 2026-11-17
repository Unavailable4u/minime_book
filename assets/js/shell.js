/* MiniMe Atlas 2 - shell (P02, palette wiring P03). One ES module, no dependencies.
   Builds the sidebar, top bar and breadcrumbs from content/nav.json, and takes over the jobs atlas-ui.js used to do
   (mobile chapter-contents drawer, back-to-top button, wrapping wide SVGs and the roadmap edit table). The command
   palette, theme key, shortcut sheet and "g" jump keys live in palette.js (P03), which this file imports.
   Loaded as <script type="module"> by every converted page (scripts/codemod_shell.py), so it needs http(s):
   run `python scripts/serve.py`, a module cannot load from file://.

   The page frame is prepared before first paint by the inline snippet in <head> (it sets html[data-sidebar] to
   open | collapsed | drawer); this file only keeps that state, it never decides it differently:
   pickSidebar() below is the same rule as the snippet, and scripts/test_codemod_shell.py checks that.

   Keys handled here: [ and Ctrl/Cmd+B (sidebar), ] (fires minime:toc-toggle for P04), Esc (closes drawers and the code-links popover).
   Keys handled by palette.js: Ctrl/Cmd+K, t, ?, g + o/e/b/s.

   Chapter pages (a .bk-banner or a .doc article inside <main>) also load reader.js (P04) on demand, and figures.js (P06) after it:
   see loadReader().

   Events on document:
     minime:sidebar      detail = "open" | "collapsed" | "drawer-open" | "drawer-closed"
     minime:toc-toggle   fired by "]"   (P04 listens and toggles "On this page")
     minime:palette      detail = "open" | "close"   (from palette.js; the mobile drawer closes on "open")
     minime:theme        detail = "dark" | "paper"   (from theme.js)
     minime:links        detail = { root, scheme }   (the code-links popover saved new settings, P12; see links.js) */

import { initPalette, openPalette, toggleTheme } from "./palette.js";

const KEY_SIDEBAR = "minime_sidebar";   // "open" | "collapsed", the reader's choice for desktop widths
const KEY_WINGS = "minime_wings";       // { wingId: true|false }, which sidebar groups are open
const KEY_CACHE = "minime_shell_v1";    // sessionStorage: last nav.json + stats.json, so page 2 paints with no wait
const KEY_SCROLL = "minime_sb_scroll";  // sessionStorage: sidebar scroll position across pages
const BASE = new URL("../../", import.meta.url);

/* The one rule for the sidebar state. Keep identical to the PREPAINT snippet in scripts/codemod_shell.py. */
export function pickSidebar(width, saved, layout) {
  if (width <= 760) return "drawer";
  if (saved === "open" || saved === "collapsed") return saved;
  return layout === "workbench" || width < 1100 ? "collapsed" : "open";
}

/* ------------------------------------------------------------------ small helpers */
const root = typeof document !== "undefined" ? document.documentElement : null;
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode: the choice just is not remembered */ } },
};
const session = {
  get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* ignore */ } },
};
const fmtN = (n) => new Intl.NumberFormat("en-US").format(n);

function el(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;                       // static icon markup from ICONS only
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

const svg = (d) => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${d}</svg>`;
const ICONS = {
  menu: svg('<path d="M4 6h16M4 12h16M4 18h16"/>'),
  panel: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>'),
  search: svg('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>'),
  theme: svg('<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" stroke="none"/>'),
  chevron: svg('<path d="M9 6l6 6-6 6"/>'),
  toc: svg('<path d="M4 6h16M4 12h10M4 18h13"/>'),
  start: svg('<path d="M4 11l8-7 8 7v9H4z"/><path d="M10 20v-6h4v6"/>'),
  system: svg('<rect x="3" y="4" width="7" height="6" rx="1"/><rect x="14" y="14" width="7" height="6" rx="1"/><path d="M10 7h4a3 3 0 0 1 3 3v4"/>'),
  code: svg('<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>'),
  book: svg('<path d="M5 4h10a4 4 0 0 1 4 4v12H9a4 4 0 0 1-4-4z"/><path d="M5 16a4 4 0 0 1 4-4h10"/>'),
  project: svg('<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16M10 10v10"/>'),
  back: svg('<path d="M15 6l-6 6 6 6"/>'),
  link: svg('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'),
};

const isTyping = (t) => !!t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable);
const itemLabel = (it) => (it.chapter == null ? it.title : `${it.part === "appendix" ? "App." : "Ch."} ${it.chapter} · ${it.title}`);

/* ------------------------------------------------------------------ state */
const S = { nav: null, stats: {}, items: [], cur: null, sb: null, top: null, scrim: null, scroller: null };

/* Settles once with { nav, stats } (fresh from the network, else the session cache, else null). reader.js waits on it for prev / next. */
let settleNav = () => {};
const navReady = new Promise((resolve) => { settleNav = resolve; });

function readWings() {
  try { return JSON.parse(store.get(KEY_WINGS) || "{}") || {}; } catch { return {}; }
}
function setWing(id, open) {
  const w = readWings();
  w[id] = open;
  store.set(KEY_WINGS, JSON.stringify(w));
  const head = S.sb && S.sb.querySelector(`.mm-wing[data-wing="${id}"]`);
  if (!head) return;
  head.querySelector(".mm-wing__h").setAttribute("aria-expanded", String(open));
  head.querySelector(".mm-wing__list").hidden = !open;
}

const mode = () => root.dataset.sidebar;
const drawerOpen = () => root.dataset.drawer === "open";

function syncControls() {
  const open = mode() === "drawer" ? drawerOpen() : mode() === "open";
  const menu = document.querySelector(".mm-top__menu");
  if (menu) {
    menu.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-label", open ? "Hide navigation" : "Show navigation");
  }
  const collapse = document.querySelector(".mm-sb__collapse");
  if (collapse) collapse.setAttribute("aria-label", mode() === "collapsed" ? "Expand sidebar" : "Collapse sidebar");
}

function setDrawer(open) {
  if (open) root.dataset.drawer = "open"; else delete root.dataset.drawer;
  syncControls();
  document.dispatchEvent(new CustomEvent("minime:sidebar", { detail: open ? "drawer-open" : "drawer-closed" }));
  if (open && S.sb) { const first = S.sb.querySelector(".mm-sb__jump"); if (first) first.focus({ preventScroll: true }); }
}

export function toggleSidebar() {
  if (mode() === "drawer") { setDrawer(!drawerOpen()); return; }
  const next = mode() === "collapsed" ? "open" : "collapsed";
  root.dataset.sidebar = next;
  store.set(KEY_SIDEBAR, next);
  if (S.sb) S.sb.classList.remove("is-peek");
  syncControls();
  document.dispatchEvent(new CustomEvent("minime:sidebar", { detail: next }));
}

function applySidebar() {
  const next = pickSidebar(window.innerWidth, store.get(KEY_SIDEBAR), root.dataset.layout);
  if (next !== mode()) root.dataset.sidebar = next;
  if (next !== "drawer") delete root.dataset.drawer;
  syncControls();
}

/* closes whatever transient layer is open; returns true if something was closed */
function closeTransient() {
  let closed = false;
  if (document.body.classList.contains("toc-open")) { setToc(false); closed = true; }
  if (drawerOpen()) { setDrawer(false); closed = true; }
  if (S.sb && S.sb.classList.contains("is-peek")) { S.sb.classList.remove("is-peek"); closed = true; }
  if (closeLinksPop(true)) closed = true;
  return closed;
}

function setToc(open) {
  document.body.classList.toggle("toc-open", open);
  const b = document.querySelector(".mm-top__toc");
  if (b) b.setAttribute("aria-expanded", String(open));
}

/* ------------------------------------------------------------------ sidebar */
function buildSidebar() {
  const { nav, stats, cur } = S;
  const wings = readWings();
  const rail = () => mode() === "collapsed";

  const brand = el("a", { class: "mm-sb__brand", href: nav.site.home, "aria-label": nav.site.name },
    el("span", { class: "mm-sb__mark", "aria-hidden": "true" }, "M"),
    el("span", { class: "mm-sb__brand-t" }, "Mini", el("b", {}, "Me"), " Atlas"));
  const collapse = el("button", { class: "mm-ib mm-sb__collapse", type: "button", title: "Collapse sidebar ( [ )", onclick: toggleSidebar, html: ICONS.panel });
  const jump = el("button", { class: "mm-sb__jump", type: "button", title: "Search the Atlas (Ctrl+K)", onclick: () => openPalette() },
    el("span", { class: "mm-sb__jump-i", html: ICONS.search }),
    el("span", { class: "mm-sb__jump-t" }, "Quick jump"),
    el("kbd", {}, "Ctrl K"));

  const scroller = el("div", { class: "mm-sb__scroll", role: "navigation", "aria-label": "Atlas pages" });
  for (const w of nav.wings) {
    const active = !!cur && cur.wing === w.id;
    const open = active || (wings[w.id] ?? w.open !== false);
    const listId = `mm-wing-${w.id}`;
    const list = el("ul", { class: "mm-wing__list", id: listId, hidden: !open });
    let lastPart = null;
    for (const it of w.items) {
      if (it.part && it.part !== lastPart) list.append(el("li", { class: "mm-part", role: "presentation" }, nav.parts[it.part] || it.part));
      lastPart = it.part || null;
      const on = !!cur && cur.id === it.id;
      const count = it.count_from && Number.isFinite(stats[it.count_from]) ? fmtN(stats[it.count_from]) : null;
      list.append(el("li", {},
        el("a", { class: "mm-it" + (on ? " is-active" : ""), href: it.url, "aria-current": on ? "page" : null, title: it.blurb },
          it.chapter != null ? el("span", { class: "mm-it__n" }, it.chapter) : null,
          el("span", { class: "mm-it__t" }, it.title),
          count ? el("span", { class: "mm-it__c" }, count) : null)));
    }
    const head = el("button", { class: "mm-wing__h", type: "button", "aria-expanded": String(open), "aria-controls": listId, title: w.title },
      el("span", { class: "mm-wing__i", html: ICONS[w.icon] || ICONS.panel }),
      el("span", { class: "mm-wing__t" }, w.title),
      el("span", { class: "mm-wing__chev", html: ICONS.chevron }));
    head.addEventListener("click", () => {
      if (rail() && !S.sb.classList.contains("is-peek")) { S.sb.classList.add("is-peek"); setWing(w.id, true); return; }   // touch: first tap peeks
      setWing(w.id, head.getAttribute("aria-expanded") !== "true");
    });
    scroller.append(el("section", { class: "mm-wing" + (active ? " is-active" : ""), "data-wing": w.id }, head, list));
  }

  const built = document.querySelector("body > .mm-built");
  const foot = el("div", { class: "mm-sb__foot" },
    built ? el("span", { class: "mm-sb__built" }, built.textContent.trim()) : null,
    el("span", { class: "mm-sb__priv" }, "Private. Not indexed."));

  const sb = el("aside", { class: "mm-sb", id: "mm-sb", "aria-label": nav.site.name },
    el("div", { class: "mm-sb__head" }, brand, collapse), jump, scroller, foot);
  S.scroller = scroller;
  return sb;
}

/* ------------------------------------------------------------------ top bar */
function buildTop() {
  const { nav, stats, cur } = S;
  const bare = root.dataset.layout === "bare";
  const crumbs = el("ol", { class: "mm-crumbs__l" });
  const crumb = (child) => crumbs.append(el("li", {}, child));
  if (bare) {
    crumb(el("a", { href: nav.site.home }, el("span", { html: ICONS.back }), "Back to Atlas"));
  } else if (cur) {
    const wing = nav.wings.find((w) => w.id === cur.wing);
    if (wing && wing.items.length > 1) crumb(el("a", { href: wing.items[0].url }, wing.title));
    if (cur.part) crumb(el("span", {}, nav.parts[cur.part] || cur.part));
    crumb(el("span", { "aria-current": "page" }, itemLabel(cur)));
  } else {
    crumb(el("span", { "aria-current": "page" }, document.title.split(" · ")[0]));
  }

  const hasToc = !!document.querySelector("main .toc");
  const chip = stats.commit
    ? el("span", { class: "mm-chip", title: `Atlas snapshot: census built ${stats.generated || "?"} from MiniMe commit ${stats.commit}` },
        "MiniMe ", el("code", {}, String(stats.commit).slice(0, 7)))
    : null;
  const theme = el("button", { class: "mm-ib mm-top__theme", type: "button", title: "Switch theme (Dark / Paper)", html: ICONS.theme,
    onclick: () => toggleTheme() });

  return el("header", { class: "mm-top" },
    el("button", { class: "mm-ib mm-top__menu", type: "button", "aria-controls": "mm-sb", "aria-expanded": "false", title: "Toggle sidebar ( [ )", html: ICONS.menu, onclick: toggleSidebar }),
    el("div", { class: "mm-crumbs", role: "navigation", "aria-label": "Breadcrumb" }, crumbs),
    el("span", { class: "mm-top__sp" }),
    hasToc ? el("button", { class: "mm-top__toc", type: "button", "aria-expanded": "false", onclick: () => setToc(!document.body.classList.contains("toc-open")) },
      el("span", { html: ICONS.toc }), el("span", { class: "mm-top__toc-t" }, "Contents")) : null,
    chip,
    el("button", { class: "mm-top__k", type: "button", title: "Search the Atlas (Ctrl+K)", onclick: () => openPalette() },
      el("span", { html: ICONS.search }), el("span", { class: "mm-top__k-t" }, "Search"), el("kbd", {}, "Ctrl K")),
    el("button", { class: "mm-ib mm-top__links", type: "button", "aria-haspopup": "dialog", "aria-expanded": "false", "aria-label": "Code link settings",
      title: "Code link settings: where your MiniMe folder is, and which editor to open", html: ICONS.link, onclick: () => openLinksPop() }),
    theme);
}

/* ------------------------------------------------------------------ code-link settings (P12)
   The small dialog behind the link icon in the top bar. It stores two things in this browser only (links.js, KEY_LINKS):
   the folder your MiniMe working copy lives in, and which editor the "VS Code" buttons open. links.js is fetched the first
   time the dialog opens, so pages that never use it do not pay for it. Everything else about links lives in links.js. */
let linksMod = null;
let linksBusy = false;
const loadLinks = () => (linksMod || (linksMod = import("./links.js")));

function closeLinksPop(refocus = false) {
  const pop = document.getElementById("mm-links-pop");
  if (!pop) return false;
  pop.remove();
  const b = document.querySelector(".mm-top__links");
  if (b) { b.setAttribute("aria-expanded", "false"); if (refocus) b.focus({ preventScroll: true }); }
  return true;
}

async function openLinksPop() {
  if (closeLinksPop()) return;                                    // the icon toggles
  if (linksBusy) return;
  const btn = document.querySelector(".mm-top__links");
  if (!btn) return;
  linksBusy = true;
  let L, opts;
  try {
    L = await loadLinks();
    opts = await L.loadLinkOptions();                             // never rejects: a missing manifest only means fewer buttons
  } catch (err) {
    console.warn("[atlas links]", err);
    linksBusy = false;
    return;
  }
  linksBusy = false;
  if (document.getElementById("mm-links-pop")) return;
  btn.setAttribute("aria-expanded", "true");

  const saved = L.readSettings();
  const input = el("input", { class: "mm-pop__in", id: "mm-links-root", type: "text", value: saved.root, spellcheck: "false", autocomplete: "off",
    autocapitalize: "off", placeholder: "E:\\python workplace\\code\\MiniMe", "aria-describedby": "mm-links-prev" });
  const select = el("select", { class: "mm-pop__in", id: "mm-links-scheme" },
    el("option", { value: "" }, `Site default (${opts.siteScheme === "vscode-insiders" ? "VS Code Insiders" : "VS Code"})`),
    ...L.SCHEMES.map((s) => el("option", { value: s }, s === "vscode" ? "VS Code" : "VS Code Insiders")));
  select.value = saved.scheme;
  const prev = el("p", { class: "mm-pop__prev", id: "mm-links-prev", "aria-live": "polite" });
  const status = el("p", { class: "mm-pop__status", role: "status" });

  const effectiveScheme = () => select.value || opts.siteScheme;
  const refreshPreview = () => {
    const v = input.value.trim();
    prev.replaceChildren();
    if (!v) { prev.append("No folder set, so the VS Code buttons are hidden."); return; }
    const url = L.vscodeUrl(v, "README.md", 1, effectiveScheme());
    if (!url) { prev.append("That is not an absolute folder path (for example E:\\code\\MiniMe or /home/me/MiniMe)."); prev.classList.add("is-bad"); return; }
    prev.classList.remove("is-bad");
    prev.append("README.md opens as ", el("code", {}, url));
  };
  input.addEventListener("input", () => { status.textContent = ""; refreshPreview(); });
  select.addEventListener("change", () => { status.textContent = ""; refreshPreview(); });

  const tidy = (v) => v.trim().replace(/^["']+|["']+$/g, "").trim();          // "Copy as path" adds quotes; links.js copes, but do not show them back
  const save = (e) => {
    e.preventDefault();
    const v = tidy(input.value);
    if (v && !L.normalizeRoot(v)) { prev.classList.add("is-bad"); input.focus(); return; }
    input.value = v;
    const ok = L.saveSettings({ root: v, scheme: select.value });
    status.textContent = ok ? "Saved in this browser." : "Could not save (private mode?). The setting lasts until you close the tab.";
    document.dispatchEvent(new CustomEvent("minime:links", { detail: { root: v, scheme: select.value } }));
  };
  const clear = () => {
    input.value = "";
    select.value = "";
    L.saveSettings({});
    refreshPreview();
    status.textContent = "Cleared.";
    document.dispatchEvent(new CustomEvent("minime:links", { detail: { root: "", scheme: "" } }));
  };

  const commit = opts.commit ? opts.commit.slice(0, 7) : "";
  const note = commit
    ? el("p", { class: "mm-pop__note" }, "GitHub links and the embedded source are for MiniMe commit ", el("code", {}, commit),
        ", the snapshot this Atlas describes. VS Code opens your working copy, so its line numbers can differ if your checkout has moved on.")
    : el("p", { class: "mm-pop__note" }, "No embedded source yet: run ", el("code", {}, "python scripts/refresh_source.py"), " (or update_all.py) to add the in-site source and GitHub links.");

  const pop = el("form", { class: "mm-pop", id: "mm-links-pop", role: "dialog", "aria-label": "Code link settings", onsubmit: save },
    el("h2", { class: "mm-pop__h" }, "Code links"),
    el("p", { class: "mm-pop__lead" }, "Where the Source, GitHub and VS Code buttons should go. Kept in this browser only."),
    el("label", { class: "mm-pop__l", for: "mm-links-root" }, "Your MiniMe folder"),
    input, prev,
    el("label", { class: "mm-pop__l", for: "mm-links-scheme" }, "Editor"),
    select, note,
    el("div", { class: "mm-pop__row" },
      el("button", { class: "mm-pop__b mm-pop__b--go", type: "submit" }, "Save"),
      el("button", { class: "mm-pop__b", type: "button", onclick: clear }, "Clear"),
      el("button", { class: "mm-pop__b", type: "button", onclick: () => closeLinksPop(true) }, "Close"),
      status));
  document.body.append(pop);
  refreshPreview();
  input.focus({ preventScroll: true });
}

/* ------------------------------------------------------------------ what atlas-ui.js used to do */
function legacyFixups() {
  // roadmap.html: the edit table needs its scroll wrapper
  const edit = document.getElementById("edit");
  if (edit && edit.parentElement && !edit.parentElement.classList.contains("tw")) {
    const tw = el("div", { class: "tw" });
    edit.before(tw);
    tw.append(edit);
  }
  // wide SVGs scroll sideways on a phone instead of squeezing
  document.querySelectorAll("main svg").forEach((s) => {
    const w = parseFloat((s.getAttribute("viewBox") || "").split(/[\s,]+/)[2] || "0");
    const p = s.parentElement;
    if (w >= 650 && p && !p.classList.contains("svg-scroll") && !p.classList.contains("svg-wrap")) {
      const wrap = el("div", { class: "svg-scroll" });
      s.before(wrap);
      wrap.append(s);
    }
  });
  // chapter pages: header row for the contents drawer (shown by the page's own mobile CSS)
  const toc = document.querySelector("main .toc");
  if (toc && !toc.querySelector(".toc-mhdr")) {
    const hdr = el("div", { class: "toc-mhdr" }, el("b", {}, "Chapter Contents"),
      el("button", { class: "toc-mclose", type: "button", onclick: () => setToc(false) }, "\u2715 Close"));
    toc.prepend(hdr);
    toc.addEventListener("click", (e) => { if (e.target.closest("a")) setToc(false); });
  }
  // back to top
  if (!document.querySelector(".mm-btt")) {
    const btt = el("button", { class: "mm-btt", type: "button", title: "Back to top", "aria-label": "Back to top", html: svg('<path d="M12 19V6M6 11l6-6 6 6"/>'),
      onclick: () => window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }) });
    document.body.append(btt);
    window.addEventListener("scroll", () => btt.classList.toggle("is-on", window.scrollY > 450), { passive: true });
  }
}

/* Tables whose header sticks to the page (no scroll box of their own) must stop below the top bar. */
function markStickyTables() {
  const scrolls = (n) => { const s = getComputedStyle(n); return /(auto|scroll|hidden)/.test(s.overflowX + s.overflowY); };
  document.querySelectorAll("main table").forEach((t) => {
    for (let n = t.parentElement; n && n.tagName !== "MAIN" && n !== document.body; n = n.parentElement) if (scrolls(n)) return;
    t.classList.add("mm-vsticky");
  });
}

/* ------------------------------------------------------------------ mount */
function mount(data) {
  S.nav = data.nav;
  S.stats = data.stats || {};
  S.items = [];
  for (const w of S.nav.wings) for (const it of w.items) S.items.push({ ...it, wing: w.id, wingTitle: w.title });
  const file = location.pathname.split("/").pop() || S.nav.site.home;
  S.cur = S.items.find((i) => i.id === document.body.dataset.page) || S.items.find((i) => i.url === file) || null;

  const keep = S.scroller ? S.scroller.scrollTop : Number(session.get(KEY_SCROLL) || 0);
  document.querySelectorAll(".mm-sb, .mm-top, .mm-scrim, .mm-skipnav").forEach((n) => n.remove());
  closeLinksPop();

  const main = document.querySelector("main");
  if (main && !main.id) main.id = "mm-main";
  S.top = buildTop();
  S.scrim = el("div", { class: "mm-scrim", onclick: closeTransient });
  const parts = [el("a", { class: "mm-skipnav", href: "#mm-main" }, "Skip to content")];
  if (root.dataset.layout !== "bare") { S.sb = buildSidebar(); parts.push(S.sb); } else S.sb = null;
  document.body.prepend(...parts, S.top, S.scrim);

  if (S.scroller) {
    S.scroller.scrollTop = keep;
    const on = S.scroller.querySelector(".mm-it.is-active");
    if (on) { const r = on.getBoundingClientRect(), b = S.scroller.getBoundingClientRect(); if (r.top < b.top || r.bottom > b.bottom) on.scrollIntoView({ block: "nearest" }); }
  }
  syncControls();
  root.dataset.shell = "1";
}

function mountFallback() {
  const nav = { site: { name: "MiniMe Atlas", home: "index.html" }, parts: {}, wings: [] };
  mount({ nav, stats: {} });
  if (S.scroller) S.scroller.append(el("p", { class: "mm-sb__err" },
    "The navigation could not be loaded. If you opened this file directly, start the local server: python scripts/serve.py"));
}

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}

async function load() {
  let cached = null;
  try { cached = JSON.parse(session.get(KEY_CACHE)); } catch { cached = null; }
  if (cached && cached.nav) mount(cached);
  try {
    const [nav, stats] = await Promise.all([getJSON("content/nav.json"), getJSON("data/index/stats.json").catch(() => ({}))]);
    const fresh = { nav, stats };
    if (!cached || JSON.stringify(cached) !== JSON.stringify(fresh)) {
      session.set(KEY_CACHE, JSON.stringify(fresh));
      mount(fresh);
    }
    settleNav(fresh);
  } catch (err) {
    if (!(cached && cached.nav)) mountFallback();
    console.warn("[atlas shell]", err);
    settleNav(cached && cached.nav ? cached : null);
  }
}

/* P04: chapter pages get the reader layer. It is a separate module, fetched only where it is used; if it fails to load
   the chapter simply stays as it was. */
function loadReader() {
  if (root.dataset.layout === "bare" || !document.querySelector("main .bk-banner, main .doc article")) return;
  const opts = { navReady };
  // The figure layer (P06) needs the reader's heading ids, so it starts after the reader has finished. A failing reader
  // is only logged: the chapter is still readable, and the figures are inserted after whatever headings it has.
  import("./reader.js")
    .then((m) => m.initReader(opts))
    .catch((err) => console.warn("[atlas reader]", err))
    .then(() => import("./figures.js"))
    .then((m) => m.initFigures({ navReady }))
    .catch((err) => console.warn("[atlas figures]", err));
}

function boot() {
  const run = () => {
    initPalette();                                                  // before load(): Ctrl+K works even if nav.json fails
    legacyFixups();
    load();
    loadReader();
    const idle = window.requestIdleCallback || ((f) => setTimeout(f, 200));
    idle(markStickyTables);

    window.matchMedia("(max-width: 760px)").addEventListener("change", applySidebar);
    window.matchMedia("(max-width: 1099px)").addEventListener("change", applySidebar);
    window.addEventListener("pagehide", () => { if (S.scroller) session.set(KEY_SCROLL, String(S.scroller.scrollTop)); });

    document.addEventListener("click", (e) => {
      if (S.sb && S.sb.classList.contains("is-peek") && !e.target.closest(".mm-sb")) S.sb.classList.remove("is-peek");
      if (mode() === "drawer" && drawerOpen() && e.target.closest(".mm-sb a")) setDrawer(false);
      if (!e.target.closest(".mm-pop, .mm-top__links")) closeLinksPop();
    });
    // the palette closes the mobile drawer when it opens, so the two never stack
    document.addEventListener("minime:palette", (e) => { if (e.detail === "open" && drawerOpen()) setDrawer(false); });
    document.addEventListener("keydown", (e) => {
      if (e.defaultPrevented || e.isComposing || typeof e.key !== "string") return;   // autofill fires keydown without a key
      const mod = (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey;
      const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      if (mod && k === "b") { e.preventDefault(); toggleSidebar(); return; }
      if (e.key === "Escape") { closeTransient(); return; }
      if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target)) return;
      if (e.key === "[") { e.preventDefault(); toggleSidebar(); }
      else if (e.key === "]") document.dispatchEvent(new CustomEvent("minime:toc-toggle"));
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run, { once: true });
  else run();
}

// The pre-paint snippet sets data-sidebar on converted pages. Without it (?legacy=1, or a page that was
// not converted) the shell stays out of the way. In node (tests) there is no document at all.
if (root && root.dataset.sidebar) boot();