/* MiniMe Atlas - command palette, theme toggle, shortcut sheet and "g" jump keys (patch P03).
 *
 * shell.js imports this and calls initPalette(); nothing else needs to. Styles live in assets/css/shell.css
 * (section 5), so the palette follows the Dark / Paper themes like everything else.
 *
 * - Ctrl/Cmd+K opens the palette. Elements with data-action="palette" | "theme" | "shortcuts"
 *   are wired by event delegation.
 * - Operators (first character of the query):
 *       (none) everything   > pages   # book headings + glossary   / files   @ functions & classes
 *       : API routes        ? operator help
 * - Single keys (not while typing, not with Ctrl/Alt):  t = theme,  ? = shortcut sheet,
 *   g then o / e / b / s = go to Overview / Explorer / Book / System.
 * - Data comes from data/index/*.json (built by scripts/build_index.py), fetched lazily on first open.
 *   The function index is sharded; shards are added to the results as they arrive, test code last and ranked lower.
 * - Nothing here touches the DOM at import time, so parseQuery() / fuzzy() / match() / symbolItems() run in Node
 *   (scripts/test_palette.py does exactly that).
 */

const ROOT = new URL('../../', import.meta.url); // site root (this file lives in assets/js/)
const GITHUB_BLOB = 'https://github.com/Unavailable4u/MiniMe/blob/';
const RECENT_KEY = 'minime_palette_recent';

// test code is findable but should not bury the real thing: same name, lower rank
const TEST_PATH = /(^|\/)(tests?|__tests__)\/|(^|\/)(test_[^/]*|conftest\.py|[^/]*\.test\.[jt]sx?)$/;
const TEST_RANK = -250;

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

// "g" then a key. Explorer is resolved at run time: explorer.html (P13) once it is in the nav, explore.html until then.
const GO = {
  o: { label: 'Overview', url: 'index.html' },
  e: { label: 'Explorer', url: null },
  b: { label: 'Book', url: 'docs.html' },
  s: { label: 'System', url: 'architecture.html' },
};
const CHORD_MS = 1500;

/* ------------------------------------------------------------------ matching */
export function parseQuery(raw) {
  const s = String(raw).replace(/^\s+/, '');
  const c = s[0];
  // Windows paths: backend\api\deps.py finds backend/api/deps.py
  if (c && Object.prototype.hasOwnProperty.call(OPS, c)) return { op: c, q: s.slice(1).trim().replace(/\\/g, '/') };
  return { op: '', q: s.trim().replace(/\\/g, '/') };
}

function isBoundary(t, i) {
  return i === 0 || /[\s/_\-.:#>@(]/.test(t[i - 1]);
}

/** How far apart (in characters) the letters of a subsequence match may sit: tight for short queries. */
export function maxSpan(n) {
  return n <= 4 ? n * 2 + 2 : n * 2 + 4;
}

/** Score one lower-cased query token against a text. null = no match. Substring beats subsequence.
 *  subsequence=false accepts substrings only (used for long secondary text, where "t-a-r-g-e-t" appears by chance). */
export function fuzzy(q, text, lt = text.toLowerCase(), subsequence = true) {
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
  if (!subsequence) return null;
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
  // letters scattered across a long text are a coincidence, not a match: "api" must not find "Technical Implementation"
  if (idx[idx.length - 1] - idx[0] + 1 > maxSpan(q.length)) return null;
  return { score: Math.min(600, Math.max(1, score - lt.length * 0.2)), idx };
}

/** Every whitespace-separated token must match; score is the average. */
export function match(tokens, text, lt = text.toLowerCase(), subsequence = true) {
  let total = 0;
  const all = [];
  for (const t of tokens) {
    const m = fuzzy(t, text, lt, subsequence);
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
    const m2 = match(tokens, it.extra, it.lextra, false); // keywords, blurbs, paths: whole words only, no letter-skipping
    if (m2) return { score: m2.score * 0.3, idx: [] };
  }
  return null;
}

const lower = (it) => {
  it.lt = it.title.toLowerCase();
  it.lextra = (it.extra || '').toLowerCase();
  return it;
};

/** One symbols-<shard>.json -> palette items. Rows are [qual, index into files, line, kind]. */
export function symbolItems(shard) {
  const files = (shard && shard.files) || [];
  const out = [];
  for (const row of (shard && shard.rows) || []) {
    const [qual, fi, line, kind] = row;
    const path = files[fi];
    if (!qual || !path) continue;
    out.push(lower({
      kind: 'symbol', title: qual, qual, path, line,
      badge: kind === 'cls' ? 'CLASS' : 'FUNC', sub: `${path}:${line}`, extra: path,
      rank: TEST_PATH.test(path) ? TEST_RANK : 0,
    }));
  }
  return out;
}

/** Test shards last, so the code people actually read is searchable first. */
export function shardOrder(shards) {
  const isTest = (s) => /(^|__)tests?(__|$)/.test(s.id);
  return [...shards].sort((a, b) => Number(isTest(a)) - Number(isTest(b)));
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
  stats: {},
  symState: 'idle', // idle | loading | ready | error
  symDone: 0,
  symTotal: 0,
  explorer: false, // explorer.html is in the nav (P13)
  explore: false, // explore.html is in the nav (until P19)
  sheetOpen: false,
  chordUntil: 0,
  raf: 0,
};

async function fetchJSON(rel) {
  const r = await fetch(new URL(rel, ROOT));
  if (!r.ok) throw new Error(`${rel}: HTTP ${r.status}`);
  return r.json();
}

function loadCore() {
  if (!S.coreP) {
    S.error = '';
    S.coreP = Promise.all([
      fetchJSON('data/index/search.json'),
      fetchJSON('data/index/paths.json').catch(() => null),
      fetchJSON('data/index/routes.json').catch(() => null),
      fetchJSON('data/index/stats.json').catch(() => null),
    ])
      .then(([search, paths, routes, stats]) => {
        S.stats = stats || {};
        const pages = search.pages || [];
        S.explorer = pages.some((p) => p.url === 'explorer.html');
        S.explore = pages.some((p) => p.url === 'explore.html');
        S.pools.page = pages.map((p) =>
          lower({
            kind: 'page', title: p.label || p.title, sub: p.part || p.wing || '', url: p.url,
            extra: [p.wing, (p.keywords || []).join(' '), p.blurb].filter(Boolean).join(' '),
          }));
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

function renderSoon() {
  if (S.raf) return;
  S.raf = requestAnimationFrame(() => {
    S.raf = 0;
    if (!S.open) return;
    const { op, q } = parseQuery(S.els.input.value);
    const kinds = op ? OPS[op].kinds : GROUPS.map((g) => g.kind);
    if (q && kinds.includes('symbol')) render(); // a new shard can change the symbol results (and the "loading" note)
  });
}

function loadSymbols() {
  if (S.symState !== 'idle') return;
  S.symState = 'loading';
  fetchJSON('data/index/symbols.json')
    .then((man) => {
      const shards = shardOrder(man.shards || []);
      S.symTotal = shards.length;
      if (!shards.length) { S.symState = 'ready'; return null; }
      let failed = 0;
      const finish = () => {
        S.symDone += 1;
        if (S.symDone === S.symTotal) S.symState = failed === S.symTotal ? 'error' : 'ready';
        renderSoon();
      };
      for (const s of shards) {
        fetchJSON(`data/index/${s.file}`)
          .then((sh) => { for (const it of symbolItems(sh)) S.pools.symbol.push(it); })
          .catch(() => { failed += 1; })
          .finally(finish);
      }
      return null;
    })
    .catch(() => { S.symState = 'error'; })
    .finally(() => { if (S.open) render(); });
}

/* ------------------------------------------------------------------- targets */
const encPath = (p) => p.split('/').map(encodeURIComponent).join('/');

function target(it) {
  if (it.url) return { href: new URL(it.url, ROOT).href, external: false };
  const line = it.line || 1;
  if (it.kind === 'file') {
    if (S.explorer) return { href: new URL(`explorer.html#/f/${encPath(it.path)}`, ROOT).href, external: false };
    if (S.explore) return { href: new URL(`explore.html#${encodeURIComponent(it.path)}`, ROOT).href, external: false };
    return { href: `${GITHUB_BLOB}${S.stats.commit || 'main'}/${encPath(it.path)}`, external: true };
  }
  if (S.explorer) {
    const sym = it.qual ? `::${it.qual}` : '';
    return { href: new URL(`explorer.html#/f/${encPath(it.path)}${sym}@${line}`, ROOT).href, external: false };
  }
  // the census commit, so the line number matches the code the Atlas describes (a branch name would drift)
  return { href: `${GITHUB_BLOB}${S.stats.commit || 'main'}/${encPath(it.path)}#L${line}`, external: true };
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
    if (m) hits.push({ item: it, score: m.score + (it.rank || 0), idx: m.idx });
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
  if (symbolsWanted && S.symState === 'loading') note = `Loading function index… (${S.symDone}/${S.symTotal || '?'})`;
  else if (symbolsWanted && S.symState === 'error') note = 'Function index unavailable.';
  if (!groups.length && !note) note = 'No matches';
  return { groups, note };
}

/* ----------------------------------------------------------------------- DOM */
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
  input.setAttribute('autocapitalize', 'off');
  input.setAttribute('enterkeyhint', 'go');
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-expanded', 'true');
  input.setAttribute('aria-controls', 'mmp-list');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-label', 'Search the Atlas');

  const list = el('div', 'mmp-list');
  list.id = 'mmp-list';
  list.setAttribute('role', 'listbox');
  const status = el('div', 'mmp-sr');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  const foot = el('div', 'mmp-foot');
  for (const t of ['↑↓ / Tab move', '↵ open', 'Ctrl/⌘ ↵ new tab', 'Esc close', '? operators']) foot.appendChild(el('span', '', t));

  box.append(input, list, status, foot);
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

  Object.assign(S.els, { backdrop, input, list, status });
}

function render() {
  const { list, input, status } = S.els;
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
      const mono = item.kind === 'file' || item.kind === 'symbol' || item.kind === 'route';
      const title = el('span', `mmp-title${mono ? ' mono' : ''}`);
      highlight(title, item.title, idx);
      row.appendChild(title);
      if (item.sub) row.appendChild(el('span', 'mmp-sub', item.sub));
      list.appendChild(row);
      S.opts.push({ item, row });
    }
  }
  if (result.note) list.appendChild(el('div', 'mmp-note', result.note));
  status.textContent = S.opts.length ? `${S.opts.length} result${S.opts.length === 1 ? '' : 's'}` : (result.note || '');
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
function announce(state) {
  document.dispatchEvent(new CustomEvent('minime:palette', { detail: state })); // shell.js closes the mobile drawer on "open"
}

export function openPalette(prefill = '') {
  if (typeof prefill !== 'string') prefill = ''; // an event handler may pass the click event
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
  announce('open');
  loadCore().then(() => { if (S.open) render(); loadSymbols(); });
}

export function closePalette() { close(); }

export function isPaletteOpen() { return S.open || S.sheetOpen; }

function close() {
  if (!S.open) return;
  S.open = false;
  S.els.backdrop.hidden = true;
  document.documentElement.classList.remove('mmp-open');
  const p = S.prevFocus;
  if (p && typeof p.focus === 'function') { try { p.focus(); } catch { /* element gone */ } }
  announce('close');
}

/* --------------------------------------------------------------------- toast */
function toast(text, ms = 1400) {
  if (!S.els.toasts) {
    const box = el('div', 'mm-toasts'); // the design-system toast container (components.css)
    box.setAttribute('role', 'status');
    document.body.appendChild(box);
    S.els.toasts = box;
  }
  const t = el('div', 'mm-toast', text);
  S.els.toasts.replaceChildren(t); // one at a time: the newest replaces the last
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { if (t.parentNode) t.remove(); }, ms);
}

/* ---------------------------------------------------------------------- theme */
export function toggleTheme() {
  const T = window.minimeTheme; // assets/js/theme.js owns the theme: one writer, one "minime:theme" event
  if (T && typeof T.cycle === 'function') T.cycle();
  else {
    const next = document.documentElement.dataset.theme === 'paper' ? 'dark' : 'paper';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('minime_theme', next); } catch { /* private mode */ }
    document.dispatchEvent(new CustomEvent('minime:theme', { detail: next }));
  }
  toast(`Theme: ${document.documentElement.dataset.theme === 'paper' ? 'Paper' : 'Dark'}`);
}

/* ------------------------------------------------------------ shortcut sheet */
// Only keys that do something today. Add "]" (On this page) with P04, "/" (focus the filter box) and the Explorer keys
// (j/k, Enter, o) with P13, in the same patch that implements them.
const SHEET = [
  ['General', [
    ['Ctrl/⌘ + K', 'Open the command palette'],
    ['[  or  Ctrl/⌘ + B', 'Collapse / expand the sidebar'],
    ['t', 'Switch theme (Dark / Paper)'],
    ['?', 'Show this sheet'],
    ['Esc', 'Close palette or sheet'],
  ]],
  ['Go to  (press g, then)', Object.entries(GO).map(([k, v]) => [`g ${k}`, v.label])],
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

async function goKey(k) {
  const g = GO[k];
  let url = g.url;
  if (!url) {
    await loadCore();
    url = S.explorer ? 'explorer.html' : S.explore ? 'explore.html' : null;
  }
  if (url) window.location.assign(new URL(url, ROOT).href);
  else toast('The Explorer is not available yet');
}

function onGlobalKey(e) {
  // autofill and some IMEs fire keydown without a key; they are never ours
  if (e.defaultPrevented || e.isComposing || typeof e.key !== 'string') return;
  // a page that sets html[data-layout="bare"] owns its keyboard (full-screen tools); the top-bar button still works
  if (document.documentElement.dataset.layout === 'bare') return;
  const mod = e.ctrlKey || e.metaKey;
  if (mod && !e.altKey && !e.shiftKey && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    if (S.open) close(); else openPalette();
    return;
  }
  if (mod || e.altKey || S.open || S.sheetOpen || isTyping(e.target)) return;

  if (S.chordUntil) {
    const live = Date.now() < S.chordUntil;
    S.chordUntil = 0;
    if (live && Object.prototype.hasOwnProperty.call(GO, e.key)) { e.preventDefault(); goKey(e.key); return; }
  }
  if (e.key === 't') { e.preventDefault(); toggleTheme(); }
  else if (e.key === '?') { e.preventDefault(); openSheet(); }
  else if (e.key === 'g') {
    S.chordUntil = Date.now() + CHORD_MS;
    toast('Go to:  o Overview · e Explorer · b Book · s System', CHORD_MS);
  }
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
