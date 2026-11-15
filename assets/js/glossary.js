/* MiniMe Atlas 2 - glossary page (P05). One ES module, no dependencies. Loaded by glossary.html.

   Draws content/glossary.json: every term once, with its short and long definition and "see" links.
   The anchor of a term is slug(term), the same recipe as scripts/build_index.py and scripts/check_site.py, so a palette
   result (Ctrl+K, then #) and a reader tooltip both land on the right entry.

   A "see" target is a chapter id (optionally #heading-id), a repo file, or file::symbol. scripts/check_site.py checks that every one exists.
   Pure helpers are exported so scripts/test_library.py can run them in Node with no browser. */

const GITHUB_BLOB = "https://github.com/Unavailable4u/MiniMe/blob/";
const BASE = typeof document !== "undefined" ? new URL("../../", import.meta.url) : null;

/* ================================================================== pure helpers (no DOM) */

export function slug(text) {
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "root";
}

const norm = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "");

/* Accepts {"terms": [...]} or a bare list; drops entries without a name or a short definition. */
export function normalizeTerms(raw) {
  const list = Array.isArray(raw) ? raw : raw && Array.isArray(raw.terms) ? raw.terms : [];
  const seen = new Set(), out = [];
  for (const t of list) {
    if (!t || typeof t.term !== "string" || !t.term.trim() || typeof t.short !== "string" || !t.short.trim()) continue;
    const id = slug(t.term);
    if (seen.has(id)) continue;
    seen.add(id);
    out.push({
      id, term: t.term.trim(), aliases: Array.isArray(t.aliases) ? t.aliases.filter((a) => typeof a === "string") : [],
      category: t.category || "Other", short: t.short.trim(), long: typeof t.long === "string" ? t.long.trim() : "",
      see: Array.isArray(t.see) ? t.see.filter((s) => typeof s === "string") : [], match: ["ci", "cs", "off"].includes(t.match) ? t.match : "ci",
      review: !!t.needs_review,
    });
  }
  return out.sort((a, b) => a.term.toLowerCase().localeCompare(b.term.toLowerCase()));
}

/* Category chips with counts, in the order the categories first appear alphabetically. */
export function categoryCounts(terms) {
  const m = new Map();
  for (const t of terms) m.set(t.category, (m.get(t.category) || 0) + 1);
  return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([name, count]) => ({ name, count }));
}

/* Every word of the query must appear in the term, its aliases, its category or its definitions. */
export function filterTerms(terms, q, category) {
  const words = norm(q).split(/[^a-z0-9]+/).filter(Boolean);
  return terms.filter((t) => {
    if (category && category !== "all" && t.category !== category) return false;
    if (!words.length) return true;
    const hay = norm([t.term, ...t.aliases, t.category, t.short, t.long].join(" "));
    return words.every((w) => hay.includes(w));
  });
}

/* Where a "see" target goes. `pages` maps a page id to {url, title}; `titles` maps "page.html#id" to the heading's text. */
export function seeLink(target, pages, titles, commit) {
  if (target.includes("::") || target.includes("/")) {
    const [path, qual] = target.split("::");
    const enc = path.split("/").map(encodeURIComponent).join("/");
    return { code: true, url: `${GITHUB_BLOB}${commit || "main"}/${enc}`, text: qual ? `${path} \u00b7 ${qual}` : path, external: true };
  }
  const [id, heading] = target.split("#");
  const p = pages[id];
  if (!p) return null;
  const url = heading ? `${p.url}#${heading}` : p.url;
  const head = heading && titles ? titles[url] : "";
  return { code: false, url, text: head ? `${p.label || p.title}: ${head}` : p.label || p.title, external: false };
}

/* ================================================================== DOM layer */
function h(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}

const S = { terms: [], nodes: new Map(), q: "", cat: "all" };

function buildTerm(t, pages, titles, commit) {
  const see = t.see.map((s) => seeLink(s, pages, titles, commit)).filter(Boolean).map((l) =>
    h("li", {}, h("a", l.external ? { href: l.url, target: "_blank", rel: "noopener" } : { href: l.url }, l.code ? h("code", {}, l.text) : l.text)));
  const node = h("article", { class: "gl-term", id: t.id },
    h("h2", { class: "gl-term__h" }, h("a", { href: `#${t.id}`, title: "Link to this term" }, t.term), h("span", { class: "gl-badge" }, t.category),
      t.review ? h("span", { class: "gl-badge gl-badge--review", title: "Drafted from the sources; waiting for your review" }, "needs review") : null),
    t.aliases.length ? h("p", { class: "gl-term__also" }, "Also written: ", t.aliases.join(", ")) : null,
    h("p", { class: "gl-term__short" }, t.short),
    t.long ? h("p", { class: "gl-term__long" }, t.long) : null,
    see.length ? h("ul", { class: "gl-term__see" }, h("li", {}, "See"), see) : null);
  S.nodes.set(t.id, node);
  return node;
}

function apply() {
  const keep = new Set(filterTerms(S.terms, S.q, S.cat).map((t) => t.id));
  for (const [id, node] of S.nodes) node.hidden = !keep.has(id);
  document.getElementById("gl-count").textContent = keep.size === S.terms.length ? `${S.terms.length} terms` : `${keep.size} of ${S.terms.length} terms`;
  document.getElementById("gl-none").hidden = keep.size > 0;
  document.querySelectorAll("#gl-chips .lib-chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cat === S.cat)));
}

function goToHash() {
  const id = decodeURIComponent(location.hash.slice(1));
  S.nodes.forEach((n) => n.classList.remove("is-target"));
  const node = id && S.nodes.get(id);
  if (!node) return;
  if (node.hidden) { S.q = ""; S.cat = "all"; document.getElementById("gl-q").value = ""; apply(); }   // a link must never land on a hidden term
  node.classList.add("is-target");
  node.scrollIntoView({ block: "start" });
}

async function boot() {
  const list = document.getElementById("gl-list");
  let raw, nav, search = { headings: [] }, stats = {};
  try {
    [raw, nav] = await Promise.all([getJSON("content/glossary.json"), getJSON("content/nav.json")]);
  } catch (e) {
    list.replaceChildren(h("p", { class: "lib__empty lib__err" }, "The glossary could not be loaded. If you opened this file directly, start the local server: python scripts/serve.py"));
    console.warn("[atlas glossary]", e);
    return;
  }
  await Promise.all([getJSON("data/index/search.json").then((d) => (search = d)).catch(() => null), getJSON("data/index/stats.json").then((d) => (stats = d)).catch(() => null)]);
  const pages = {};
  for (const w of nav.wings) for (const it of w.items) pages[it.id] = { url: it.url, title: it.title, label: it.chapter != null ? `${it.part === "appendix" ? "App." : "Ch."} ${it.chapter}` : it.title };
  const titles = {};
  for (const x of search.headings || []) titles[x.url] = x.title;

  S.terms = normalizeTerms(raw);
  list.replaceChildren(...S.terms.map((t) => buildTerm(t, pages, titles, stats.commit)));
  const mk = (id, text) => h("button", { class: "lib-chip", type: "button", "data-cat": id, "aria-pressed": String(id === S.cat), onclick: () => { S.cat = id; apply(); } }, text);
  document.getElementById("gl-chips").replaceChildren(mk("all", "All"), ...categoryCounts(S.terms).map((c) => mk(c.name, `${c.name} (${c.count})`)));
  const q = document.getElementById("gl-q");
  let timer = 0;
  q.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { S.q = q.value.trim(); apply(); }, 100); });
  q.addEventListener("keydown", (e) => { if (e.key === "Escape" && q.value) { q.value = ""; S.q = ""; apply(); } });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return;
    const t = e.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return;
    e.preventDefault();
    q.focus();
  });
  window.addEventListener("hashchange", goToHash);
  apply();
  goToHash();                                                            // the list is drawn by script, so the browser's own jump to #term found nothing
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
}
