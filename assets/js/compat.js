/* MiniMe Atlas 2 - old-URL redirects (P19). explore.html, code.html and functions.html used to hold ~1.4 MB of baked-in data each.
   They are thin pages now; this module sends the reader to the Explorer and keeps what the old address said.

   What the old pages understood, and where it goes (explorerTarget):
     explore.html#<path>   (encodeURIComponent'ed, as overview, health and the graph viewer write it)  ->  explorer.html#/<path>
                           (the Explorer decides whether it is a file or a folder)
     explore.html#<words>  a search, as the old sidebar palette wrote it                                 ->  explorer.html#/?q=<words>  (file filter)
     #/...                 already an Explorer route                                                     ->  explorer.html#/...
     no hash               code.html, functions.html, explore.html                                       ->  explorer.html#/   (start page)
   Standalone on purpose (no imports): the redirect must not wait for anything. Pure apart from the last block, so Node can test it. */

const START = "explorer.html";
const encPath = (p) => p.split("/").filter(Boolean).map(encodeURIComponent).join("/");
const PATHLIKE = /\//;                                   // a/b
const FILENAME = /^[^\s/]*\.[^\s/]+$/;                 // README.md, .gitignore, backend.Dockerfile: one word with a dot inside it or at the front

export function explorerTarget(page, hash) {
  const raw = String(hash || "").replace(/^#/, "");
  if (raw.startsWith("/")) return /[^/]/.test(raw) ? `${START}#${raw}` : `${START}#/`;     // an Explorer route that arrived on an old page
  let text = raw;
  try { text = decodeURIComponent(raw); } catch { /* a stray % : use the text as it is */ }
  text = text.trim();
  if (!text) return `${START}#/`;
  if (PATHLIKE.test(text) || FILENAME.test(text)) {
    const p = encPath(text.replace(/^(\.\/)+/, ""));
    return p ? `${START}#/${p}` : `${START}#/`;
  }
  return `${START}#/?q=${encodeURIComponent(text)}`;
}

if (typeof document !== "undefined" && document.body && document.body.dataset.compat) {
  const target = explorerTarget(document.body.dataset.compat, location.hash);
  const link = document.getElementById("compat-link");
  if (link) link.setAttribute("href", target);
  location.replace(target);
}
