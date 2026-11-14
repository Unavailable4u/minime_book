/* MiniMe Atlas - command palette, theme toggle and shortcut sheet (patch P03).
 *
 * Usage (from shell.js):   import { initPalette } from './palette.js';  initPalette();
 *
 * - Ctrl/Cmd+K opens the palette. Elements with data-action="palette" | "theme" | "shortcuts"
 *   (e.g. the topbar buttons built by shell.js) are wired by event delegation.
 * - Operators (first character of the query):
 *       (none) everything   > pages   # book headings + glossary   / files   @ functions & classes
 *       : API routes        ? operator help
 * - Data comes from data/index/*.json (built by scripts/build_index.py), fetched lazily.
 * - Nothing here touches the DOM at import time, so fuzzy()/match()/parseQuery() are testable in Node.
 */

const ROOT = new URL('../../', import.meta.url); // site root (this file lives in assets/js/)
const GITHUB_BLOB = 'https://github.com/Unavailable4u/MiniMe/blob/main/';
const RECENT_KEY = 'minime_palette_recent';
const THEME_KEY = 'minime_theme';

const OPS = {
  '>': { name: 'Pages', kinds: ['page'], hint: 'Jump to an Atlas page' },
  '#': { name: 'Book headings & glossary', kinds: ['heading', 'term'], hint: 'Type to search book headings and glossary terms' },
  '/': { name: 'Files', kinds: ['file'], hint: 'Type part of a file path' },
  '@': { name: 'Functions & classes', kinds: ['symbol'], hint: 'Type a function or class name' },
  ':': { name: 'API routes', kinds: ['route'], hint: 'Type part of an API route' },
  '?': { name: 'Help', kinds: [], hint: '' },
};

const GROUPS = [
  { kind: 'page', label: 'Pages', limit: 5 },
  { kind: 'heading', label: 'Book', limit: 6 },
  { kind: 'term', label: 'Glossary', limit: 3 },
  { kind: 'file', label: 'Files', limit: 5 },
  { kind: 'symbol', label: 'Functions & classes', limit: 6 },
  { kind: 'route', label: 'API routes', limit: 4 },
];
const BADGE = { page: 'PAGE', heading: 'BOOK', term: 'TERM', file: 'FILE', symbol: 'FUNC', route: 'API' };

/* ------------------------------------------------------------------ matching */
export function parseQuery(raw) {
  const s = String(raw).replace(/^\s+/, '');
  const c = s[0];
  if (c && Object.prototype.hasOwnProperty.call(OPS, c)) return { op: c, q: s.slice(1).trim() };
  return { op: '', q: s.trim() };
}

function isBoundary(t, i) {
  return i === 0 || /[\s/_\-.:#>@(]/.test(t[i - 1]);
}

/** Score one lower-cased query token against a text. null = no match. Substring beats subsequence. */
export function fuzzy(q, text, lt = text.toLowerCase()) {
  if (!q) return { score: 0, idx: [] };
  const at = lt.indexOf(q);
  if (at >= 0) {
    let score = 1000 - at * 2 - (lt.length - q.length) * 0.5;
    if (at === 0) score += 300;
    else if (isBoundary(lt, at)) score += 150;
    const idx = [];
    for (let k = 0; k < q.length; k++) idx.push(at + k);
    return { score, idx };
  }
  let pos = 0;
  let last = -2;
  let score = 200;
  const idx = [];
  for (let k = 0; k < q.length; k++) {
    const f = lt.indexOf(q[k], pos);
    if (f < 0) return null;
    if (f === last + 1) score += 15;
    else score -= Math.min(f - pos, 8);
    if (isBoundary(lt, f)) score += 10;
    idx.push(f);
    last = f;
    pos = f + 1;
  }
  return { score: Math.min(600, Math.max(1, score - lt.length * 0.2)), idx };
}

/** Every whitespace-separated token must match; score is the average. */
export function match(tokens, text, lt = text.toLowerCase()) {
  let total = 0;
  const all = [];
  for (const t of tokens) {
    const m = fuzzy(t, text, lt);
    if (!m) return null;
    total += m.score;
    all.push(...m.idx);
  }
  return { score: tokens.length ? total / tokens.length : 0, idx: [...new Set(all)].sort((a, b) => a - b) };
}

function matchItem(tokens, it) {
  const m = match(tokens, it.title, it.lt);
  if (m) return m;
  if (it.extra) {
    const m2 = match(tokens, it.extra, it.lextra);
    if (m2) return { score: m2.score * 0.3, idx: [] };
  }
  return null;
}

/* --------------------------------------------------------------------- state */
const S = {
  inited: false,
  open: false,
  els: {},
  opts: [],
  sel: 0,
  prevFocus: null,
  pools: { page: [], heading: [], term: [], file: [], symbol: [], route: [] },
  coreP: null,
  coreReady: false,
  error: '',
  symState: 'idle',
  explorer: null,
  sheetOpen: false,
};

const lower = (it) => {
  it.lt = it.title.toLowerCase();
  it.lextra = (it.extra || '').toLowerCase();
  return it;
};

async function fetchJSON(rel) {
  const r = await fetch(new URL(rel, ROOT));
  if (!r.ok) throw new Error(`${rel}: HTTP ${r.status}`);
  return r.json();
}

function loadCore() {
  if (!S.coreP) {
    S.coreP = Promise.all([
      fetchJSON('data/index/search.json'),
      fetchJSON('data/index/paths.json').catch(() => null),
      fetchJSON('data/index/routes.json').catch(() => null),
    ])
      .then(([search, paths, routes]) => {
        S.pools.page = (search.pages || []).map((p) =>
          lower({ kind: 'page', title: p.title, sub: p.wing || '', url: p.url, extra: [(p.keywords || []).join(' '), p.blurb || ''].join(' ').trim() }));
        S.pools.heading = (search.headings || []).map((h) =>
          lower({ kind: 'heading', title: h.title, sub: h.chapterTitle || '', url: h.url }));
        S.pools.term = (search.terms || []).map((t) =>
          lower({ kind: 'term', title: t.term, sub: 'Glossary', url: t.url, extra: [(t.aliases || []).join(' '), t.short || ''].join(' ').trim() }));
        S.pools.file = ((paths && paths.paths) || []).map((p) => lower({ kind: 'file', title: p, sub: '', path: p }));
        S.pools.route = ((routes && routes.routes) || []).map((r) =>
          lower({
            kind: 'route', title: `${r.method} ${r.route}`.trim(), sub: `${r.handler} · ${r.file}:${r.line}`,
            path: r.file, qual: r.handler, line: r.line, extra: r.handler,
          }));
        S.coreReady = true;
      })
      .catch((e) => {
        S.error = `Search index not available (${e.message}). Run: python scripts/build_index.py`;
        S.coreP = null; // allow a retry next time the palette opens
      });
  }
  return S.coreP;
}

function loadSymbols() {
  if (S.symState !== 'idle') return;
  S.symState = 'loading';
  fetchJSON('data/index/symbols.json')
    .then((man) => Promise.all((man.shards || []).map((s) => fetchJSON(`data/index/${s.file}`))))
    .then((shards) => {
      const out = [];
      for (const sh of shards) {
        for (const [name, qual, path, line, kind] of sh.rows || []) {
          out.push(lower({
            kind: 'symbol', title: qual || name, name, qual, path, line,
            badge: kind === 'cls' ? 'CLASS' : 'FUNC', sub: `${path}:${line}`, extra: path,
          }));
        }
      }
      S.pools.symbol = out;
      S.symState = 'ready';
    })
    .catch(() => { S.symState = 'error'; })
    .finally(() => { if (S.open) render(); });
}

function probeExplorer() {
  if (S.explorer !== null) return;
  S.explorer = false; // until proven (explorer.html arrives with patch P13)
  fetch(new URL('explorer.html', ROOT), { method: 'HEAD' })
    .then((r) => { S.explorer = r.ok; if (S.open) render(); })
    .catch(() => {});
}

/* ------------------------------------------------------------------- targets */
function target(it) {
  if (it.url) return { href: new URL(it.url, ROOT).href, external: false };
  if (it.kind === 'file') {
    return S.explorer
      ? { href: new URL(`explorer.html#/f/${encodeURI(it.path)}`, ROOT).href, external: false }
      : { href: GITHUB_BLOB + encodeURI(it.path), external: true };
  }
  const line = it.line || 1;
  if (S.explorer) {
    const sym = it.qual ? `::${it.qual}` : '';
    return { href: new URL(`explorer.html#/f/${encodeURI(it.path)}${sym}@${line}`, ROOT).href, external: false };
  }
  return { href: `${GITHUB_BLOB}${encodeURI(it.path)}#L${line}`, external: true };
}

function loadRecent() {
  try {
    const v = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    return Array.isArray(v) ? v.filter((x) => x && x.kind && x.title).slice(0, 8) : [];
  } catch { return []; }
}

const recentKey = (x) => `${x.kind}|${x.url || x.path}|${x.title}`;

function remember(it) {
  const slim = { kind: it.kind, title: it.title, sub: it.sub || '', url: it.url, path: it.path, line: it.line, qual: it.qual, badge: it.badge };
  const list = [slim, ...loadRecent().filter((x) => recentKey(x) !== recentKey(slim))].slice(0, 8);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch { /* private mode */ }
}

function go(it, newTab) {
  remember(it);
  close();
  const t = target(it);
  if (t.external || newTab) window.open(t.href, '_blank', 'noopener');
  else window.location.assign(t.href);
}

/* ------------------------------------------------------------------- results */
function searchPool(pool, tokens, limit) {
  const hits = [];
  for (const it of pool) {
    const m = matchItem(tokens, it);
    if (m) hits.push({ item: it, score: m.score, idx: m.idx });
  }
  hits.sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title));
  return hits.slice(0, limit);
}

function compute(op, q) {
  const plain = (items) => items.map((item) => ({ item, idx: [] }));
  if (op === '?') {
    const items = Object.entries(OPS).filter(([k]) => k !== '?').map(([k, v]) => ({ kind: 'op', action: 'op', op: k, title: `${k}  ${v.name}`, sub: v.hint }));
    return { groups: [{ label: 'Operators', items: plain(items) }], note: '' };
  }
  if (!q) {
    if (!op) {
      const groups = [];
      const rec = loadRecent();
      if (rec.length) groups.push({ label: 'Recent', items: plain(rec) });
      groups.push({ label: 'Pages', items: plain(S.pools.page.slice(0, 8)) });
      return { groups, note: '' };
    }
    if (op === '>') return { groups: [{ label: 'Pages', items: plain(S.pools.page) }], note: '' };
    return { groups: [], note: OPS[op].hint };
  }
  const tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
  const kinds = op ? OPS[op].kinds : GROUPS.map((g) => g.kind);
  const groups = [];
  for (const g of GROUPS) {
    if (!kinds.includes(g.kind)) continue;
    const hits = searchPool(S.pools[g.kind], tokens, op ? 60 : g.limit);
    if (hits.length) groups.push({ label: g.label, items: hits });
  }
  let note = '';
  const symbolsWanted = kinds.includes('symbol');
  if (symbolsWanted && S.symState === 'loading') note = 'Loading function index…';
  else if (symbolsWanted && S.symState === 'error') note = 'Function index unavailable.';
  if (!groups.length && !note) note = 'No matches';
  return { groups, note };
}

/* ----------------------------------------------------------------------- DOM */
const CSS = `
.mmp-backdrop[hidden]{display:none}
.mmp-backdrop{position:fixed;inset:0;z-index:1000;display:flex;align-items:flex-start;justify-content:center;
  padding:max(8vh,env(safe-area-inset-top)) 12px 12px;background:rgba(5,5,8,.62)}
html.mmp-open{overflow:hidden}
.mmp{width:min(680px,100%);max-height:min(76vh,720px);display:flex;flex-direction:column;overflow:hidden;
  background:var(--panel,#121216);color:var(--ink,#f2f1ed);border:1px solid var(--line,#26262e);border-radius:12px;
  box-shadow:0 24px 80px rgba(0,0,0,.5);font:14px/1.4 var(--font-ui,'Sora',system-ui,sans-serif)}
.mmp-input{width:100%;box-sizing:border-box;padding:14px 16px;border:0;border-bottom:1px solid var(--line,#26262e);
  background:transparent;color:inherit;font:inherit;font-size:16px;outline:none}
.mmp-input::placeholder{color:var(--ink-dim,#a8a6a0)}
.mmp-list{overflow-y:auto;padding:6px;overscroll-behavior:contain}
.mmp-group{padding:10px 10px 4px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-dim,#a8a6a0)}
.mmp-note{padding:14px 12px;color:var(--ink-dim,#a8a6a0)}
.mmp-opt{display:flex;align-items:baseline;gap:10px;padding:8px 10px;border-radius:8px;color:inherit;text-decoration:none;cursor:pointer}
.mmp-opt[aria-selected="true"]{background:var(--panel-2,#17171d);outline:1px solid var(--brand,#ff2052);outline-offset:-1px}
.mmp-badge{flex:none;min-width:44px;text-align:center;padding:1px 6px;border:1px solid var(--line,#26262e);border-radius:5px;
  font:600 10px/1.6 var(--font-mono,'JetBrains Mono',ui-monospace,monospace);color:var(--ink-dim,#a8a6a0)}
.mmp-title{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mmp-title mark{background:none;color:var(--brand,#ff2052);font-weight:700}
.mmp-title.mono{font-family:var(--font-mono,'JetBrains Mono',ui-monospace,monospace);font-size:13px}
.mmp-sub{flex:0 1 38%;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--ink-dim,#a8a6a0)}
.mmp-foot{display:flex;flex-wrap:wrap;gap:4px 14px;padding:8px 14px;border-top:1px solid var(--line,#26262e);font-size:11px;color:var(--ink-dim,#a8a6a0)}
.mms-box{padding:0;max-width:560px}
.mms-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line,#26262e)}
.mms-head h2{margin:0;font-size:15px}
.mms-body{overflow-y:auto;padding:8px 16px 16px}
.mms-body h3{margin:14px 0 6px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-dim,#a8a6a0)}
.mms-row{display:flex;justify-content:space-between;gap:16px;padding:5px 0;border-bottom:1px solid var(--line,#26262e)}
.mms-row kbd{font:600 12px var(--font-mono,'JetBrains Mono',ui-monospace,monospace);padding:1px 6px;border:1px solid var(--line,#26262e);border-radius:5px;background:var(--panel-2,#17171d)}
.mms-close{border:1px solid var(--line,#26262e);background:var(--panel-2,#17171d);color:inherit;border-radius:6px;padding:4px 10px;font:inherit;cursor:pointer}
.mm-toast{position:fixed;left:50%;bottom:max(20px,env(safe-area-inset-bottom));transform:translateX(-50%);z-index:1100;
  padding:8px 14px;border-radius:8px;background:var(--panel-2,#17171d);color:var(--ink,#f2f1ed);border:1px solid var(--line,#26262e);font-size:13px}
.mm-toast[hidden]{display:none}
@media (prefers-reduced-motion:no-preference){.mmp{animation:mmp-in .12s ease-out}@keyframes mmp-in{from{opacity:0;transform:translateY(-6px)}}}
@media (max-width:560px){.mmp-sub{display:none}}
`;

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function highlight(node, text, idx) {
  if (!idx || !idx.length) { node.textContent = text; return; }
  const on = new Set(idx);
  let i = 0;
  while (i < text.length) {
    let j = i;
    const hit = on.has(i);
    while (j < text.length && on.has(j) === hit) j++;
    if (hit) node.appendChild(el('mark', '', text.slice(i, j)));
    else node.appendChild(document.createTextNode(text.slice(i, j)));
    i = j;
  }
}

function ensureBuilt() {
  if (S.els.backdrop) return;
  const style = el('style');
  style.id = 'mm-palette-css';
  style.textContent = CSS;
  document.head.appendChild(style);

  const backdrop = el('div', 'mmp-backdrop');
  backdrop.hidden = true;
  const box = el('div', 'mmp');
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Command palette');

  const input = el('input', 'mmp-input');
  input.type = 'text';
  input.placeholder = 'Search pages, headings, files, functions, routes…   ( ? for help )';
  input.autocomplete = 'off';
  input.spellcheck = false;
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-expanded', 'true');
  input.setAttribute('aria-controls', 'mmp-list');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-label', 'Search the Atlas');

  const list = el('div', 'mmp-list');
  list.id = 'mmp-list';
  list.setAttribute('role', 'listbox');
  const foot = el('div', 'mmp-foot');
  for (const t of ['↑↓ / Tab move', '↵ open', 'Ctrl/⌘ ↵ new tab', 'Esc close', '? operators']) foot.appendChild(el('span', '', t));

  box.append(input, list, foot);
  backdrop.appendChild(box);
  document.body.appendChild(backdrop);

  backdrop.addEventListener('mousedown', (e) => { if (e.target === backdrop) close(); });
  input.addEventListener('input', () => { S.sel = 0; render(); });
  backdrop.addEventListener('keydown', onPaletteKey);
  list.addEventListener('mousemove', (e) => {
    const o = e.target.closest('.mmp-opt');
    if (o && Number(o.dataset.i) !== S.sel) setSel(Number(o.dataset.i), false);
  });
  list.addEventListener('click', (e) => {
    const o = e.target.closest('.mmp-opt');
    if (!o) return;
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) { close(); return; } // let the browser open a new tab
    e.preventDefault();
    activate(Number(o.dataset.i), false);
  });

  const toast = el('div', 'mm-toast');
  toast.hidden = true;
  toast.setAttribute('role', 'status');
  document.body.appendChild(toast);

  Object.assign(S.els, { backdrop, input, list, toast });
}

function render() {
  const { list, input } = S.els;
  list.textContent = '';
  S.opts = [];
  const { op, q } = parseQuery(input.value);

  let result;
  if (S.error) result = { groups: [], note: S.error };
  else if (!S.coreReady) result = { groups: [], note: 'Loading index…' };
  else result = compute(op, q);

  for (const g of result.groups) {
    list.appendChild(el('div', 'mmp-group', g.label)).setAttribute('role', 'presentation');
    for (const { item, idx } of g.items) {
      const i = S.opts.length;
      const t = item.action ? null : target(item);
      const row = t ? el('a', 'mmp-opt') : el('div', 'mmp-opt');
      if (t) {
        row.href = t.href;
        if (t.external) { row.target = '_blank'; row.rel = 'noopener'; }
      }
      row.id = `mmp-o-${i}`;
      row.dataset.i = String(i);
      row.setAttribute('role', 'option');
      row.tabIndex = -1;
      row.appendChild(el('span', 'mmp-badge', item.badge || BADGE[item.kind] || item.kind.toUpperCase()));
      const title = el('span', `mmp-title${item.kind === 'file' || item.kind === 'symbol' || item.kind === 'route' ? ' mono' : ''}`);
      highlight(title, item.title, idx);
      row.appendChild(title);
      if (item.sub) row.appendChild(el('span', 'mmp-sub', item.sub));
      list.appendChild(row);
      S.opts.push({ item, row });
    }
  }
  if (result.note) list.appendChild(el('div', 'mmp-note', result.note));
  S.sel = Math.min(S.sel, Math.max(0, S.opts.length - 1));
  setSel(S.sel, true);
}

function setSel(i, scroll) {
  S.sel = i;
  S.opts.forEach((o, k) => o.row.setAttribute('aria-selected', k === i ? 'true' : 'false'));
  const cur = S.opts[i];
  if (cur) {
    S.els.input.setAttribute('aria-activedescendant', cur.row.id);
    if (scroll) cur.row.scrollIntoView({ block: 'nearest' });
  } else {
    S.els.input.removeAttribute('aria-activedescendant');
  }
}

function move(delta) {
  if (!S.opts.length) return;
  setSel((S.sel + delta + S.opts.length) % S.opts.length, true);
}

function activate(i, newTab) {
  const o = S.opts[i];
  if (!o) return;
  if (o.item.action === 'op') {
    S.els.input.value = o.item.op;
    S.sel = 0;
    render();
    S.els.input.focus();
    return;
  }
  go(o.item, newTab);
}

function onPaletteKey(e) {
  if (e.isComposing) return;
  switch (e.key) {
    case 'ArrowDown': e.preventDefault(); move(1); break;
    case 'ArrowUp': e.preventDefault(); move(-1); break;
    case 'PageDown': e.preventDefault(); move(8); break;
    case 'PageUp': e.preventDefault(); move(-8); break;
    case 'Tab': e.preventDefault(); move(e.shiftKey ? -1 : 1); break; // also keeps focus inside the dialog
    case 'Enter': e.preventDefault(); activate(S.sel, e.ctrlKey || e.metaKey); break;
    case 'Escape': e.preventDefault(); e.stopPropagation(); close(); break;
    default:
  }
}

/* ----------------------------------------------------------- open / close API */
export function openPalette(prefill = '') {
  ensureBuilt();
  if (S.sheetOpen) closeSheet();
  if (S.open) return;
  S.open = true;
  S.prevFocus = document.activeElement;
  S.els.backdrop.hidden = false;
  document.documentElement.classList.add('mmp-open');
  S.els.input.value = prefill;
  S.sel = 0;
  render();
  S.els.input.focus();
  probeExplorer();
  loadCore().then(() => { if (S.open) render(); loadSymbols(); });
}

export function closePalette() { close(); }

function close() {
  if (!S.open) return;
  S.open = false;
  S.els.backdrop.hidden = true;
  document.documentElement.classList.remove('mmp-open');
  const p = S.prevFocus;
  if (p && typeof p.focus === 'function') { try { p.focus(); } catch { /* element gone */ } }
}

/* ---------------------------------------------------------------------- theme */
export function toggleTheme() {
  const cur = document.documentElement.dataset.theme === 'paper' ? 'paper' : 'dark';
  const next = cur === 'paper' ? 'dark' : 'paper';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem(THEME_KEY, next); } catch { /* private mode */ }
  window.dispatchEvent(new CustomEvent('minime:themechange', { detail: { theme: next } }));
  ensureBuilt();
  const t = S.els.toast;
  t.textContent = `Theme: ${next === 'paper' ? 'Paper' : 'Dark'}`;
  t.hidden = false;
  clearTimeout(toggleTheme._t);
  toggleTheme._t = setTimeout(() => { t.hidden = true; }, 1400);
}

/* ------------------------------------------------------------ shortcut sheet */
const SHEET = [
  ['General', [
    ['Ctrl/⌘ + K', 'Open the command palette'],
    ['[  or  Ctrl/⌘ + B', 'Collapse / expand the sidebar'],
    ['t', 'Switch theme (Dark / Paper)'],
    ['?', 'Show this sheet'],
    ['Esc', 'Close palette or sheet'],
  ]],
  ['Inside the palette', [
    ['↑ ↓  ·  Tab', 'Move through results'],
    ['Enter  ·  Ctrl/⌘ + Enter', 'Open  ·  open in a new tab'],
  ]],
  ['Palette operators', Object.entries(OPS).map(([k, v]) => [k, k === '?' ? 'Operator help' : v.name])],
];

function buildSheet() {
  if (S.els.sheet) return;
  const backdrop = el('div', 'mmp-backdrop');
  backdrop.hidden = true;
  const box = el('div', 'mmp mms-box');
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-labelledby', 'mms-title');
  const head = el('div', 'mms-head');
  const h = el('h2', '', 'Keyboard shortcuts');
  h.id = 'mms-title';
  const closeBtn = el('button', 'mms-close', 'Close');
  closeBtn.type = 'button';
  head.append(h, closeBtn);
  const body = el('div', 'mms-body');
  for (const [title, rows] of SHEET) {
    body.appendChild(el('h3', '', title));
    for (const [k, d] of rows) {
      const r = el('div', 'mms-row');
      r.appendChild(el('span', '', d));
      r.appendChild(el('kbd', '', k));
      body.appendChild(r);
    }
  }
  box.append(head, body);
  backdrop.appendChild(box);
  document.body.appendChild(backdrop);
  closeBtn.addEventListener('click', closeSheet);
  backdrop.addEventListener('mousedown', (e) => { if (e.target === backdrop) closeSheet(); });
  backdrop.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeSheet(); }
    else if (e.key === 'Tab') { e.preventDefault(); closeBtn.focus(); } // single focusable control
  });
  S.els.sheet = backdrop;
  S.els.sheetClose = closeBtn;
}

export function openSheet() {
  ensureBuilt();
  buildSheet();
  if (S.sheetOpen) return;
  close();
  S.sheetOpen = true;
  S.prevFocus = document.activeElement;
  S.els.sheet.hidden = false;
  document.documentElement.classList.add('mmp-open');
  S.els.sheetClose.focus();
}

function closeSheet() {
  if (!S.sheetOpen) return;
  S.sheetOpen = false;
  S.els.sheet.hidden = true;
  document.documentElement.classList.remove('mmp-open');
  const p = S.prevFocus;
  if (p && typeof p.focus === 'function') { try { p.focus(); } catch { /* element gone */ } }
}

/* --------------------------------------------------------------------- global */
function isTyping(el_) {
  return !!el_ && (el_.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el_.tagName));
}

function onGlobalKey(e) {
  if (e.defaultPrevented || e.isComposing) return;
  const mod = e.ctrlKey || e.metaKey;
  if (mod && !e.altKey && !e.shiftKey && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    if (S.open) close(); else openPalette();
    return;
  }
  if (mod || e.altKey || S.open || S.sheetOpen || isTyping(e.target)) return;
  if (e.key === 't') { e.preventDefault(); toggleTheme(); }
  else if (e.key === '?') { e.preventDefault(); openSheet(); }
}

function onGlobalClick(e) {
  const a = e.target.closest && e.target.closest('[data-action]');
  if (!a) return;
  const act = a.getAttribute('data-action');
  if (act === 'palette') { e.preventDefault(); openPalette(); }
  else if (act === 'theme') { e.preventDefault(); toggleTheme(); }
  else if (act === 'shortcuts') { e.preventDefault(); openSheet(); }
}

export function initPalette() {
  if (S.inited) return;
  S.inited = true;
  window.addEventListener('keydown', onGlobalKey, true);
  document.addEventListener('click', onGlobalClick);
}
