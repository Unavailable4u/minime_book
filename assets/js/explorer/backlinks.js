/* MiniMe Atlas 2 - "Discussed in the book" (P15). The reverse of the links codelink.js makes: for a file or a symbol, the chapter sections whose
   <code> text resolves to it. The data is data/index/mentions.json, written by scripts/build_index.py:
     { chapters: [{ url, title }], mentions: { "path" | "path::qual": [{ c: chapter index, id: heading id, h: heading, s: snippet, n: count }] } }
   bookMentions() is pure (Node tests it); renderBackrefs() builds the section. All text goes in with textContent. */
import { h } from "./dom.js";

const SHOW = 8;

/* The mentions of a file (and of every symbol in it), or of one symbol when `qual` is given.
   -> [{ url (with #heading), chapter, heading, snippet, n, sym }] in chapter order. */
export function bookMentions(doc, path, qual = "") {
  if (!doc || !doc.mentions || !Array.isArray(doc.chapters) || !path) return [];
  const out = [];
  const take = (key, sym) => {
    for (const m of doc.mentions[key] || []) {
      const ch = doc.chapters[m.c];
      if (!ch) continue;
      out.push({ url: m.id ? `${ch.url}#${m.id}` : ch.url, chapter: ch.title || ch.url, heading: m.h || "", snippet: m.s || "", n: m.n || 1, sym, c: m.c, id: m.id || "" });
    }
  };
  if (qual) take(`${path}::${qual}`, qual);
  else {
    take(path, "");
    const prefix = `${path}::`;
    for (const key of Object.keys(doc.mentions)) if (key.startsWith(prefix)) take(key, key.slice(prefix.length));
  }
  return out.sort((a, b) => a.c - b.c || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0) || (a.sym < b.sym ? -1 : a.sym > b.sym ? 1 : 0));
}

export function renderBackrefs(list) {
  if (!list.length) return null;
  const draw = (m) => h("li", null,
    h("a", { href: m.url }, m.chapter, m.heading ? ` › ${m.heading}` : ""),
    m.sym ? h("code", { class: "ex-book__sym" }, m.sym) : null,
    m.n > 1 ? h("span", { class: "ex-dim" }, ` ×${m.n}`) : null,
    m.snippet ? h("span", { class: "ex-book__snip ex-dim" }, m.snippet) : null);
  const ul = h("ul", { class: "ex-book__list" });
  const btn = h("button", { type: "button", class: "ex-link", hidden: list.length <= SHOW });
  const paint = (all) => {
    ul.replaceChildren(...(all ? list : list.slice(0, SHOW)).map(draw));
    btn.hidden = all || list.length <= SHOW;
    btn.textContent = `Show all ${list.length} mentions`;
  };
  btn.addEventListener("click", () => paint(true));
  paint(false);
  return h("section", { class: "ex-sec ex-book", "aria-label": "Discussed in the book" }, h("h3", null, `Discussed in the book (${list.length})`), ul, btn);
}
