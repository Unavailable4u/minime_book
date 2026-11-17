/* MiniMe Atlas 2 - code links (P12, plan section 6.4). One ES module, no dependencies, no DOM at import time (tests run it in node).

   One place that turns "this file / these lines" into the four ways of getting to the code:

     codeLinks({ path, start, end, commit }, opts) -> { explorer, github?, vscode?, src? }

     explorer  the Explorer page for the file, with the line range in the hash:  explorer.html#/<path>@<start>-<end>
               explorerHash() builds that hash and parseExplorerHash() reads it back, so the Explorer router (P13) and the
               source pane (P14) use the same format as every link made here.
     github    https://github.com/<repo>/blob/<full commit>/<path>#L<start>-L<end>   (needs a 40-character commit)
     vscode    vscode://file/<local MiniMe folder>/<path>:<line>                       (needs the folder, saved in the settings)
     src       data/src/<path>.txt, the copy of the file made by scripts/refresh_source.py (only when the manifest lists it)

   A link whose ingredients are missing is left out, never made up. The UI shows a button for every key that is present.

   Settings (the local MiniMe folder and the editor) live in localStorage under KEY_LINKS and are edited in the popover that
   shell.js builds from the link icon in the top bar. Nothing here touches the network except loadLinkOptions(). */

export const KEY_LINKS = "minime_links_v1";
export const SCHEMES = ["vscode", "vscode-insiders"];
export const DEFAULTS = { repo: "Unavailable4u/MiniMe", scheme: "vscode" };

const HEX40 = /^[0-9a-f]{40}$/;

/* ------------------------------------------------------------------ paths and lines */
const encodePath = (p) => p.split("/").map(encodeURIComponent).join("/");

/* "a\\b/./c.py" -> "a/b/c.py". Returns null for an empty path, an absolute path or one that climbs out with "..". */
export function cleanPath(raw) {
  if (typeof raw !== "string") return null;
  const parts = raw.trim().replace(/\\/g, "/").split("/").filter((s) => s !== "" && s !== ".");
  if (!parts.length || parts.includes("..") || /^[A-Za-z]:$/.test(parts[0]) || /^\s*[\\/]/.test(raw)) return null;
  return parts.join("/");
}

const toLine = (n) => (Number.isInteger(n) && n >= 1 ? n : null);

function lineRange(start, end) {
  const s = toLine(start);
  if (!s) return null;
  const e = toLine(end);
  return { start: s, end: e && e > s ? e : s };
}

/* ------------------------------------------------------------------ the Explorer hash */
export function explorerHash(path, start, end) {
  const p = cleanPath(path);
  if (!p) return null;
  const r = lineRange(start, end);
  return `#/${encodePath(p)}${r ? `@${r.start}${r.end > r.start ? `-${r.end}` : ""}` : ""}`;
}

/* "#/backend/api/deps.py@120-141" -> { path, start: 120, end: 141 }; null when it is not a file hash. */
export function parseExplorerHash(hash) {
  const m = /^#?\/(.+?)(?:@(\d+)(?:-(\d+))?)?$/.exec(String(hash || ""));
  if (!m) return null;
  let path;
  try { path = decodeURIComponent(m[1]); } catch { return null; }
  path = cleanPath(path);
  if (!path) return null;
  const r = m[2] ? lineRange(Number(m[2]), m[3] ? Number(m[3]) : null) : null;
  return { path, start: r ? r.start : null, end: r ? r.end : null };
}

/* ------------------------------------------------------------------ the local MiniMe folder */
/* What the person typed -> the form VS Code links need, or null when it is not an absolute folder path.
     E:\python workplace\code\MiniMe   ->  E:/python%20workplace/code/MiniMe
     "/home/me/MiniMe/"                ->  /home/me/MiniMe
   Quotes (from "Copy as path"), backslashes, doubled and trailing slashes are tidied; a path that is already
   %-encoded is not encoded twice. UNC paths (\\server\share) are not supported by vscode://file and give null. */
export function normalizeRoot(raw) {
  if (typeof raw !== "string") return null;
  let s = raw.trim().replace(/^["']+|["']+$/g, "").trim();
  if (!s || /^(\\\\|\/\/)/.test(s)) return null;
  if (/%[0-9a-f]{2}/i.test(s)) { try { s = decodeURIComponent(s); } catch { /* keep it as typed */ } }
  s = s.replace(/\\/g, "/").replace(/\/{2,}/g, "/").replace(/\/+$/, "");
  const win = /^([A-Za-z]):(\/.+)$/.exec(s);
  if (win) return `${win[1]}:/${encodePath(win[2].slice(1))}`;
  if (/^\/.+/.test(s)) return `/${encodePath(s.slice(1))}`;
  return null;
}

export function vscodeUrl(root, path, line, scheme = DEFAULTS.scheme) {
  const r = normalizeRoot(root);
  const p = cleanPath(path);
  if (!r || !p) return null;
  const sch = SCHEMES.includes(scheme) ? scheme : DEFAULTS.scheme;
  const base = r.startsWith("/") ? `${sch}://file${r}` : `${sch}://file/${r}`;
  const l = toLine(line);
  return `${base}/${encodePath(p)}${l ? `:${l}` : ""}`;
}

/* ------------------------------------------------------------------ the links */
export const srcUrl = (path) => { const p = cleanPath(path); return p ? `data/src/${encodePath(p)}.txt` : null; };

export function githubUrl(repo, commit, path, start, end) {
  const p = cleanPath(path);
  if (!p || !/^[\w.-]+\/[\w.-]+$/.test(repo || "") || !HEX40.test(commit || "")) return null;
  const r = lineRange(start, end);
  return `https://github.com/${repo}/blob/${commit}/${encodePath(p)}${r ? `#L${r.start}${r.end > r.start ? `-L${r.end}` : ""}` : ""}`;
}

/* target: { path, start?, end?, commit? }.  opts: { repo, commit, root, scheme, srcFiles }
   srcFiles is the "files" object of data/src/manifest.json (path -> blob id); without it no "src" link is made. */
export function codeLinks(target, opts = {}) {
  const path = cleanPath(target && target.path);
  if (!path) return {};
  const { start, end } = target;
  const out = { explorer: `explorer.html${explorerHash(path, start, end)}` };
  const gh = githubUrl(opts.repo || DEFAULTS.repo, (target.commit || opts.commit || "").toLowerCase(), path, start, end);
  if (gh) out.github = gh;
  const vs = vscodeUrl(opts.root, path, start, opts.scheme);
  if (vs) out.vscode = vs;
  if (opts.srcFiles && Object.prototype.hasOwnProperty.call(opts.srcFiles, path)) out.src = srcUrl(path);
  return out;
}

/* ------------------------------------------------------------------ settings (localStorage) */
function defaultStorage() {
  try { return typeof localStorage !== "undefined" ? localStorage : null; } catch { return null; }
}

export function readSettings(storage = defaultStorage()) {
  let saved = {};
  try { saved = JSON.parse((storage && storage.getItem(KEY_LINKS)) || "{}") || {}; } catch { saved = {}; }
  return {
    root: typeof saved.root === "string" ? saved.root : "",
    scheme: SCHEMES.includes(saved.scheme) ? saved.scheme : "",       // "" = use the site default from content/config.json
  };
}

export function saveSettings({ root = "", scheme = "" } = {}, storage = defaultStorage()) {
  const clean = { root: String(root).trim(), scheme: SCHEMES.includes(scheme) ? scheme : "" };
  try {
    if (!storage) return false;
    if (!clean.root && !clean.scheme) storage.removeItem(KEY_LINKS); else storage.setItem(KEY_LINKS, JSON.stringify(clean));
    return true;
  } catch { return false; }                                            // private mode: the choice just is not remembered
}

/* ------------------------------------------------------------------ loading (browser only) */
const BASE = typeof import.meta !== "undefined" && import.meta.url ? new URL("../../", import.meta.url) : null;
let cache = null;

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}

/* The options codeLinks() needs: site config + source manifest (fetched once per page) + this reader's settings.
   Never rejects: a missing config or manifest only means fewer buttons. */
export async function loadLinkOptions(storage) {
  if (!cache) {
    cache = Promise.all([getJSON("content/config.json").catch(() => ({})), getJSON("data/src/manifest.json").catch(() => null)])
      .then(([config, manifest]) => ({ config: config || {}, manifest }));
  }
  const { config, manifest } = await cache;
  return linkOptions(config, manifest, readSettings(storage));
}

/* Pure part of loadLinkOptions(), so it can be tested without a network. */
export function linkOptions(config = {}, manifest = null, settings = { root: "", scheme: "" }) {
  const embed = config.embedSource !== false && manifest && typeof manifest.files === "object";
  const siteScheme = SCHEMES.includes(config.editor && config.editor.scheme) ? config.editor.scheme : DEFAULTS.scheme;
  return {
    repo: (config.github && config.github.repo) || DEFAULTS.repo,
    commit: manifest && HEX40.test(manifest.commit || "") ? manifest.commit : "",
    root: settings.root,
    scheme: settings.scheme || siteScheme,
    siteScheme,                                                       // the editor when the reader has not chosen one (the settings popover names it)
    srcFiles: embed ? manifest.files : null,
  };
}