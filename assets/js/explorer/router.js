/* MiniMe Atlas 2 - Explorer hash routes (P13). Pure: no DOM, no network, so Node can test it.

   Canonical forms (what the Explorer writes, and what the command palette already writes):
     #/f/<path>[::<qual>][@<start>[-<end>]][?tab=symbols|source|view]     a file, optionally one symbol and a line range
     #/d/<folder>[?tab=symbols]                                a folder
     #/                                                        the start page
   The form assets/js/links.js writes, #/<path>@<start>-<end>, is read too. It does not say whether the path is a file or a
   folder, so it comes back as view "auto" and the page decides from the file index. */
import { cleanPath } from "../links.js";

export const TABS = ["view", "explain", "source", "symbols"];

const encPath = (p) => p.split("/").map(encodeURIComponent).join("/");

export function parseRoute(hash) {
  let h = String(hash || "").replace(/^#/, "");
  let tab = "";
  const q = h.indexOf("?");
  if (q >= 0) {
    const m = /(?:^|&)tab=([a-z]+)/.exec(h.slice(q + 1));
    if (m && TABS.includes(m[1])) tab = m[1];
    h = h.slice(0, q);
  }
  h = h.replace(/^\/+/, "");
  if (!h) return { view: "home", path: "", qual: "", start: null, end: null, tab };
  let view = "auto";
  if (h.startsWith("f/")) { view = "file"; h = h.slice(2); }
  else if (h.startsWith("d/")) { view = "dir"; h = h.slice(2); }
  let start = null;
  let end = null;
  const at = /@(\d+)(?:-(\d+))?$/.exec(h);
  if (at) {
    h = h.slice(0, at.index);
    start = Number(at[1]);
    end = at[2] ? Number(at[2]) : null;
    if (start < 1) start = null;
    if (start && end != null && end < start) end = start;
  }
  let qual = "";
  const cc = h.indexOf("::");
  if (cc >= 0) { qual = h.slice(cc + 2); h = h.slice(0, cc); }
  let path;
  try { path = cleanPath(decodeURIComponent(h)); if (qual) qual = decodeURIComponent(qual); } catch { return { view: "home", path: "", qual: "", start: null, end: null, tab }; }
  if (!path) return { view: "home", path: "", qual: "", start: null, end: null, tab };
  return { view, path, qual, start, end: start ? end : null, tab };
}

/* #/?q=<text> (P19): the old Explore / Files / Functions pages send a search here. It prefills the file filter; the route itself is still the start page. */
export function hashQuery(hash) {
  const h = String(hash || "");
  const i = h.indexOf("?");
  if (i < 0) return "";
  const m = /(?:^|&)q=([^&]*)/.exec(h.slice(i + 1));
  if (!m) return "";
  try { return decodeURIComponent(m[1].replace(/\+/g, " ")).trim(); } catch { return ""; }
}

export function buildRoute({ view = "file", path = "", qual = "", start = null, end = null, tab = "" } = {}) {
  const p = cleanPath(path);
  if (view === "home" || !p) return "#/";
  let out = `#/${view === "dir" ? "d" : "f"}/${encPath(p)}`;
  if (view !== "dir" && qual) out += `::${encodeURIComponent(qual)}`;
  if (view !== "dir" && start) out += `@${start}${end && end > start ? `-${end}` : ""}`;
  if (tab && TABS.includes(tab)) out += `?tab=${tab}`;
  return out;
}
