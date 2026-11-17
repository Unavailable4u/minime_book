/* MiniMe Atlas 2 - Explorer syntax colours (P14b). Turns the text of a source file into per-line coloured segments.

   Three parts:
     langFor(path, firstLine)      which highlight.js grammar a file needs (or null: shown plain)          pure
     parseHighlighted(html)        highlight.js output (HTML) -> [[{ t, c }, ...], ...], one array per line  pure
     highlightLines(lines, path)   loads the vendored engine + that one grammar on demand and runs it       async

   Why parse the HTML back into segments instead of using it: source.js builds every line with textContent / createTextNode
   only (a file name, a docstring or a source line can never inject markup), and the viewer draws one line per row, but a
   docstring or a template string spans many lines. highlight.js is run once over the whole file; its output is cut at the
   newlines, and a token that crosses a line break is simply carried onto the next line with the same class.

   The engine is vendored (assets/vendor/highlight/, pinned by scripts/vendor_highlight.py) and loaded with import(), core
   first, then only the grammar needed (about 24 KB for Python). Colour is an enhancement: when the files are missing, the
   file is too big, or anything throws, highlightLines() answers null and the Source tab keeps its plain text.
   The class names (hljs-keyword, hljs-string, ...) are coloured by assets/css/explorer.css from the Atlas tokens. */

let VENDOR = new URL("../../vendor/highlight/", import.meta.url);

/* Files over this many characters are left plain: the engine is synchronous and a 600 KB file would freeze the page. */
export const MAX_CHARS = 600000;

/* File extension (lower case, without the dot) -> grammar. Anything not listed is plain text. */
const BY_EXT = {
  py: "python", pyi: "python",
  js: "javascript", jsx: "javascript", mjs: "javascript", cjs: "javascript",
  ts: "typescript", tsx: "typescript", mts: "typescript", cts: "typescript",
  json: "json", jsonc: "json",
  sql: "sql",
  yaml: "yaml", yml: "yaml",
  sh: "bash", bash: "bash", zsh: "bash",
  ps1: "powershell", psm1: "powershell",
  css: "css",
  svg: "xml", xml: "xml", html: "xml", htm: "xml",
  ini: "ini", toml: "ini", cfg: "ini",
  md: "markdown", markdown: "markdown",
};

/* Grammars that embed another one: JSX and Markdown contain XML/HTML, so the engine needs it registered first. */
const NEEDS = { javascript: ["xml"], typescript: ["xml"], markdown: ["xml"] };

/* Shebang interpreter -> grammar, for scripts without an extension (".githooks/pre-commit"). */
const BY_SHEBANG = [[/\b(?:ba|z|da|k)?sh\b/, "bash"], [/\bpython[0-9.]*\b/, "python"], [/\b(?:node|deno|bun)\b/, "javascript"]];

export function langFor(path, firstLine = "") {
  const name = String(path || "").split("/").pop();
  const lower = name.toLowerCase();
  if (lower === "dockerfile" || lower.endsWith(".dockerfile") || lower.startsWith("dockerfile.")) return "dockerfile";
  if (lower.startsWith(".env")) return "ini";                      // .env.example
  const dot = lower.lastIndexOf(".");
  if (dot > 0 && BY_EXT[lower.slice(dot + 1)]) return BY_EXT[lower.slice(dot + 1)];
  const m = /^#!\s*(\S.*)$/.exec(String(firstLine || ""));
  if (m) for (const [re, lang] of BY_SHEBANG) if (re.test(m[1])) return lang;
  return null;
}

/* ------------------------------------------------------------------ HTML -> segments */
const ENTITIES = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#x27;": "'", "&#39;": "'" };
const decode = (s) => s.replace(/&(?:amp|lt|gt|quot|#x27|#39);/g, (e) => ENTITIES[e]);

/* highlight.js output only ever contains <span class="..."> ... </span> around text whose & < > " ' are escaped.
   Returns one array of { t: text, c: class } per line ("" for text outside any span). A span still open at a newline is
   re-opened on the next line by the class stack; an empty line is an empty array. */
export function parseHighlighted(html) {
  const lines = [[]];
  const stack = [];
  const re = /<span class="([^"]*)">|<\/span>|([^<]+)/g;
  let m;
  while ((m = re.exec(String(html || ""))) !== null) {
    if (m[1] !== undefined) { stack.push(m[1]); continue; }
    if (m[2] === undefined) { stack.pop(); continue; }
    const cls = stack.length ? stack[stack.length - 1] : "";
    const parts = decode(m[2]).split("\n");
    parts.forEach((part, i) => {
      if (i > 0) lines.push([]);
      if (part) lines[lines.length - 1].push({ t: part, c: cls });
    });
  }
  return lines;
}

/* ------------------------------------------------------------------ the engine, loaded on demand */
let corePromise = null;
const grammarPromises = new Map();

/* For tests: point the loader at another folder (or a missing one) and forget what was loaded. */
export function setVendorBase(url) {
  VENDOR = new URL(url, import.meta.url);
  corePromise = null;
  grammarPromises.clear();
}

const load = (rel) => import(new URL(rel, VENDOR).href).then((m) => m.default);

function engine() {
  if (!corePromise) corePromise = load("core.min.js");
  return corePromise;
}

function grammar(hljs, lang) {
  if (!grammarPromises.has(lang)) {
    grammarPromises.set(lang, (async () => {
      for (const dep of NEEDS[lang] || []) await grammar(hljs, dep);
      if (!hljs.getLanguage(lang)) hljs.registerLanguage(lang, await load(`languages/${lang}.min.js`));
    })());
  }
  return grammarPromises.get(lang);
}

/* A fenced code block's info string ("python", "js title=x", "jsonc") -> grammar, or null. Only grammars that are vendored count. */
const FENCE_ALIAS = { py: "python", python3: "python", js: "javascript", jsx: "javascript", node: "javascript", ts: "typescript", tsx: "typescript", jsonc: "json",
  yml: "yaml", sh: "bash", shell: "bash", zsh: "bash", console: "bash", ps1: "powershell", html: "xml", svg: "xml", toml: "ini", md: "markdown", postgres: "sql", postgresql: "sql", psql: "sql" };
const KNOWN = new Set(["python", "javascript", "typescript", "json", "sql", "yaml", "bash", "powershell", "css", "xml", "ini", "markdown", "dockerfile"]);
export function langFromFence(info) {
  const w = String(info || "").trim().split(/[\s{]/)[0].toLowerCase();
  const l = FENCE_ALIAS[w] || w;
  return KNOWN.has(l) ? l : null;
}

/* Colours for text in a known grammar. Same contract as highlightLines (one entry per line, same text) but the grammar is given. */
export async function highlightWith(lines, lang) {
  try {
    if (!lang || !KNOWN.has(lang)) return null;
    const text = lines.join("\n");
    if (text.length > MAX_CHARS) return null;
    const hljs = await engine();
    await grammar(hljs, lang);
    const out = parseHighlighted(hljs.highlight(text, { language: lang, ignoreIllegals: true }).value);
    if (out.length !== lines.length) return null;                  // the viewer's rows and the colours must line up one to one
    for (let i = 0; i < out.length; i++) if (out[i].map((s) => s.t).join("") !== lines[i]) return null;
    return { lang, lines: out };
  } catch {
    return null;
  }
}

/* lines: the file as the viewer shows it (array of strings). Returns { lang, lines: [[{t,c}]] } with exactly one entry per
   line and the same text as the input, or null when there is nothing to colour (plain file, too big, vendor missing, error). */
export async function highlightLines(lines, path) {
  const lang = langFor(path, lines[0]);
  return lang ? highlightWith(lines, lang) : null;
}
