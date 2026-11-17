/* MiniMe Atlas 2 - Explorer Markdown (P14e). A Markdown file shown as a document instead of as code.

   Two halves:
     parseMarkdown(text)            -> { blocks, headings }   pure: no DOM, no network, so Node can test it
     renderMarkdown(text, ctx)      -> { el, headings }       builds DOM nodes with h(); text only ever goes in as text nodes

   Safety is by construction, not by filtering: there is no HTML pass-through (a tag in the file is shown as the text it is,
   except <br>, which is a line break, and <!-- comments -->, which are dropped), every link goes through resolveHref(), which only lets
   http, https and mailto out and turns everything else (javascript:, data:, file:, ...) into plain text, and remote images are never
   loaded: an image is shown as a labelled link. So a README can not run code or make this page call another site by itself.

   What is supported (what the 16 Markdown files of MiniMe use, plus the usual neighbours): ATX and setext headings, paragraphs, bold,
   italic, strike-through, inline code, fenced and indented code, block quotes, nested bullet / numbered / task lists, GFM tables with
   alignment, horizontal rules, inline / reference / auto links, front matter (shown folded). Not supported, and left as readable text:
   raw HTML blocks, footnotes, definition lists, math.

   Links that leave the page are made safe, links inside the repository are made useful:  [x](../docs/a.md)  opens that file in the
   Explorer,  [x](src/app.py#L10-L20)  opens the Source tab at those lines,  [x](#heading)  scrolls inside the document without
   touching the address (the address is the Explorer's route). Each heading has a small "source" link to its line in the Source tab. */
import { h, copyText, toast } from "./dom.js";
import { buildRoute } from "./router.js";
import { cleanPath } from "../links.js";
import { highlightWith, langFromFence } from "./highlight.js";

export const MAX_CHARS = 600000;       // bigger files are left to the Source tab

/* ------------------------------------------------------------------ small pure helpers */
const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", "#39": "'", nbsp: "\u00a0" };
export const decodeEntities = (s) => String(s).replace(/&(amp|lt|gt|quot|apos|#39|nbsp);/g, (_, n) => ENTITIES[n]);

/* GitHub's heading ids: lower case, punctuation dropped, spaces to hyphens. Empty text gives "section". */
export function slugify(text) {
  const s = String(text || "").toLowerCase().trim().replace(/[^\p{L}\p{N}\s_-]/gu, "").replace(/\s/g, "-");
  return s || "section";
}

export function plainText(inline) {
  return (inline || []).map((n) => (n.t === "text" || n.t === "code" ? n.v : n.t === "br" ? " " : n.t === "image" ? n.alt : plainText(n.c))).join("");
}

const normLabel = (s) => String(s).trim().replace(/\s+/g, " ").toLowerCase();

/* ------------------------------------------------------------------ links */
/* href as written in a file -> what to do with it. ctx = { path, hasFile(p), hasDir(p) }. Never throws, never returns a URL that runs code.
     { kind: "anchor", id }                        #heading in this document
     { kind: "external", url }                     http, https, mailto
     { kind: "file", path, start?, end? }          a file of the repository (the Explorer shows it)
     { kind: "dir", path }                         a folder of the repository
     { kind: "missing", path }                     looks like a repository path, but the census has no such file
     { kind: "blocked" }                           any other scheme; shown as text */
export function resolveHref(raw, ctx = {}) {
  const href = String(raw == null ? "" : raw).trim();
  if (!href) return { kind: "blocked" };
  const probe = href.replace(/[\u0000-\u0020\u007f-\u009f]/g, "");           // browsers ignore tabs and newlines inside a scheme
  if (probe.startsWith("#")) { let id = probe.slice(1); try { id = decodeURIComponent(id); } catch { /* keep as written */ } return { kind: "anchor", id: id.toLowerCase() }; }
  const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(probe);
  if (scheme) return /^(https?|mailto)$/i.test(scheme[1]) ? { kind: "external", url: href } : { kind: "blocked" };
  if (probe.startsWith("//")) return { kind: "external", url: `https:${href}` };
  let rel = href.replace(/\\/g, "/");
  let frag = "";
  const hash = rel.indexOf("#");
  if (hash >= 0) { frag = rel.slice(hash + 1); rel = rel.slice(0, hash); }
  const q = rel.indexOf("?");
  if (q >= 0) rel = rel.slice(0, q);
  try { rel = decodeURIComponent(rel); } catch { /* keep as written */ }
  if (!rel) return { kind: "blocked" };
  const base = String(ctx.path || "").split("/").slice(0, -1);
  const parts = rel.startsWith("/") ? [] : base.slice();
  for (const seg of rel.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") { if (!parts.length) return { kind: "blocked" }; parts.pop(); } else parts.push(seg);       // climbing out of the repository is not a link
  }
  const path = cleanPath(parts.join("/"));
  if (!path) return { kind: "blocked" };
  const dir = path.replace(/\/+$/, "");
  if (ctx.hasFile && ctx.hasFile(path)) {
    const m = /^L(\d+)(?:-L?(\d+))?$/i.exec(frag);                           // GitHub's  #L10-L20
    return m ? { kind: "file", path, start: Number(m[1]), end: m[2] ? Number(m[2]) : null } : { kind: "file", path };
  }
  if (ctx.hasDir && ctx.hasDir(dir)) return { kind: "dir", path: dir };
  return { kind: "missing", path };
}

/* ------------------------------------------------------------------ inline */
const PUNCT = /[!-/:-@[-`{-~]/;
const isWord = (c) => !!c && /[\p{L}\p{N}]/u.test(c);
const isSpace = (c) => !c || /\s/.test(c);

/* The index of the "]" that closes the "[" at i, skipping escapes and code spans; -1 when there is none. */
function closeBracket(s, i) {
  let depth = 0;
  for (let j = i; j < s.length; j++) {
    const c = s[j];
    if (c === "\\") { j++; continue; }
    if (c === "`") { const run = /^`+/.exec(s.slice(j))[0]; const end = s.indexOf(run, j + run.length); j = end < 0 ? j + run.length - 1 : end + run.length - 1; continue; }
    if (c === "[") depth++;
    else if (c === "]" && --depth === 0) return j;
  }
  return -1;
}

/* "(dest "title")" starting at i (which holds "("). Returns { href, title, end } with end just past ")", or null. */
function parseDest(s, i) {
  let j = i + 1;
  while (/\s/.test(s[j] || "")) j++;
  let href = "";
  if (s[j] === "<") {
    const e = s.indexOf(">", j);
    if (e < 0 || /\n/.test(s.slice(j, e))) return null;
    href = s.slice(j + 1, e);
    j = e + 1;
  } else {
    let depth = 0;
    const st = j;
    for (; j < s.length; j++) {
      const c = s[j];
      if (c === "\\" && j + 1 < s.length) { j++; continue; }
      if (/\s/.test(c)) break;
      if (c === "(") depth++;
      else if (c === ")") { if (depth === 0) break; depth--; }
    }
    href = s.slice(st, j).replace(/\\([!-/:-@[-`{-~])/g, "$1");
  }
  while (/\s/.test(s[j] || "")) j++;
  let title = "";
  const open = s[j];
  if (open === '"' || open === "'" || open === "(") {
    const close = open === "(" ? ")" : open;
    let k = j + 1;
    while (k < s.length && s[k] !== close) k += s[k] === "\\" ? 2 : 1;
    if (k >= s.length) return null;
    title = s.slice(j + 1, k);
    j = k + 1;
    while (/\s/.test(s[j] || "")) j++;
  }
  return s[j] === ")" ? { href, title, end: j + 1 } : null;
}

/* How many times the character c repeats from index i. */
function sameRun(s, i, c) { let n = 0; while (s[i + n] === c) n++; return n; }

/* The index where the emphasis opened before `from` closes: a run of c that is as long as the opener (exactly one for a single
   * or _, so a nested ** is skipped), has no space before it and, for _, no letter after it. Code spans and escapes are skipped. -1 if none. */
function findCloser(s, from, c, len) {
  let j = from;
  while (j < s.length) {
    const d = s[j];
    if (d === "\\") { j += 2; continue; }
    if (d === "`") { const r = /^`+/.exec(s.slice(j))[0]; const e = s.indexOf(r, j + r.length); j = e < 0 ? j + r.length : e + r.length; continue; }
    if (d !== c) { j++; continue; }
    const run = sameRun(s, j, c);
    const fits = len === 1 ? run === 1 : run >= len;
    if (fits && j > from && !isSpace(s[j - 1]) && (c !== "_" || !isWord(s[j + run]))) return j;
    j += run;
  }
  return -1;
}

export function parseInline(src, env = { defs: new Map() }, noLink = false) {
  const s = String(src);
  const out = [];
  let buf = "";
  const flush = () => { if (buf) { out.push({ t: "text", v: decodeEntities(buf) }); buf = ""; } };
  const push = (n) => { flush(); out.push(n); };
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (c === "\\") {
      if (s[i + 1] === "\n") { push({ t: "br" }); i += 2; continue; }
      if (i + 1 < s.length && PUNCT.test(s[i + 1])) { buf += s[i + 1]; i += 2; continue; }
      buf += c; i++; continue;
    }
    if (c === "`") {
      const run = /^`+/.exec(s.slice(i))[0];
      const end = s.indexOf(run, i + run.length);
      let close = end;
      while (close >= 0 && s[close + run.length] === "`") close = s.indexOf(run, close + run.length + 1);       // the closing run must be exactly as long
      if (close < 0) { buf += run; i += run.length; continue; }
      let v = s.slice(i + run.length, close).replace(/\n/g, " ");
      if (v.length > 2 && v.startsWith(" ") && v.endsWith(" ") && v.trim()) v = v.slice(1, -1);
      push({ t: "code", v });
      i = close + run.length;
      continue;
    }
    if ((c === "[" || (c === "!" && s[i + 1] === "[")) && !(noLink && c === "[")) {
      const img = c === "!";
      const open = img ? i + 1 : i;
      const close = closeBracket(s, open);
      if (close > 0) {
        const label = s.slice(open + 1, close);
        let dest = null;
        let end = close + 1;
        if (s[end] === "(") { const d = parseDest(s, end); if (d) { dest = d; end = d.end; } }
        else {
          const ref = /^\[([^\]]*)\]/.exec(s.slice(end));                   // [text][ref], [text][], or the shortcut [ref]
          const key = ref ? normLabel(ref[1] || label) : normLabel(label);
          if (env.defs.has(key) && (ref || !img)) { dest = env.defs.get(key); end = ref ? end + ref[0].length : end; }
        }
        if (dest) {
          if (img) push({ t: "image", src: dest.href, alt: plainText(parseInline(label, env, true)), title: dest.title });
          else push({ t: "link", href: dest.href, title: dest.title, c: parseInline(label, env, true) });
          i = end;
          continue;
        }
      }
      buf += c; i++; continue;
    }
    if (c === "<") {
      const auto = /^<((?:https?:\/\/|mailto:)[^\s<>]+)>/i.exec(s.slice(i));
      if (auto && !noLink) { push({ t: "link", href: auto[1], title: "", c: [{ t: "text", v: auto[1] }] }); i += auto[0].length; continue; }
      const br = /^<br\s*\/?>/i.exec(s.slice(i));
      if (br) { push({ t: "br" }); i += br[0].length; continue; }
      const cm = /^<!--[\s\S]*?-->/.exec(s.slice(i));
      if (cm) { i += cm[0].length; continue; }
      buf += c; i++; continue;
    }
    if (c === "*" || c === "_" || c === "~") {
      const run = sameRun(s, i, c);
      const before = s[i - 1];
      const after = s[i + run];
      const tries = c === "~" ? (run >= 2 ? [2] : []) : run >= 3 ? [3, 2, 1] : [run];     // *** falls back to ** and then *, when no closing run is found
      const opens = tries.length > 0 && !isSpace(after) && (c !== "_" || !isWord(before));
      let done = false;
      if (opens) {
        for (const len of tries) {
          const j = findCloser(s, i + len, c, len);
          if (j < 0) continue;
          const inner = parseInline(s.slice(i + len, j), env, noLink);
          push(c === "~" ? { t: "del", c: inner } : len === 1 ? { t: "em", c: inner } : len === 2 ? { t: "strong", c: inner } : { t: "strong", c: [{ t: "em", c: inner }] });
          i = j + len;
          done = true;
          break;
        }
      }
      if (!done) { buf += s.slice(i, i + run); i += run; }
      continue;
    }
    if (c === "h" && !noLink && !isWord(s[i - 1]) && /^https?:\/\//i.test(s.slice(i, i + 8))) {
      let u = /^[^\s<]+/.exec(s.slice(i))[0];
      while (/[.,:;!?'"*_~]$/.test(u) || (u.endsWith(")") && (u.match(/\)/g) || []).length > (u.match(/\(/g) || []).length)) u = u.slice(0, -1);
      if (u.length > 8) { push({ t: "link", href: u, title: "", c: [{ t: "text", v: u }] }); i += u.length; continue; }
    }
    if (c === "\n") {
      if (/ {2,}$/.test(buf)) { buf = buf.replace(/ +$/, ""); push({ t: "br" }); } else buf = buf.replace(/ +$/, "") + " ";
      i++;
      continue;
    }
    buf += c;
    i++;
  }
  flush();
  return out;
}

/* ------------------------------------------------------------------ blocks */
const RE_FENCE = /^( {0,3})(`{3,}|~{3,})(.*)$/;
const RE_HEAD = /^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$/;
const RE_HR = /^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/;
const RE_QUOTE = /^ {0,3}>/;
const RE_ITEM = /^( {0,3})([-*+]|\d{1,9}[.)])( +|$)(.*)$/;
const RE_DELIM = /^ {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;
const RE_SETEXT = /^ {0,3}(=+|-+)[ \t]*$/;
const blank = (l) => /^\s*$/.test(l);
const indentOf = (l) => /^ */.exec(l.replace(/\t/g, "    "))[0].length;

function splitRow(line) {
  let t = line.trim();
  if (t.startsWith("|")) t = t.slice(1);
  if (t.endsWith("|") && !t.endsWith("\\|")) t = t.slice(0, -1);
  const cells = [];
  let cur = "";
  for (let i = 0; i < t.length; i++) {
    if (t[i] === "\\" && t[i + 1] === "|") { cur += "|"; i++; } else if (t[i] === "|") { cells.push(cur.trim()); cur = ""; } else cur += t[i];
  }
  cells.push(cur.trim());
  return cells;
}

const startsBlock = (l, canOrder) => {
  if (RE_FENCE.test(l) && !(l.trim().startsWith("`") && l.replace(/^\s*`+/, "").includes("`"))) return true;
  if (RE_HEAD.test(l) || RE_HR.test(l) || RE_QUOTE.test(l)) return true;
  const m = RE_ITEM.exec(l);
  return !!m && m[4] !== "" && (/^[-*+]$/.test(m[2]) || (canOrder && /^1[.)]$/.test(m[2])));      // an empty item, or 2. / 3., does not interrupt a paragraph
};

function parseBlocks(lines, base, env) {
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const ln = lines[i];
    if (blank(ln)) { i++; continue; }
    const at = base + i + 1;

    let m = RE_FENCE.exec(ln);
    if (m && !(m[2][0] === "`" && m[3].includes("`"))) {
      const [, ind, fence, info] = m;
      const body = [];
      let j = i + 1;
      const closer = new RegExp(`^ {0,3}${fence[0] === "`" ? "`" : "~"}{${fence.length},}[ \\t]*$`);
      while (j < lines.length && !closer.test(lines[j])) { body.push(lines[j].replace(new RegExp(`^ {0,${ind.length}}`), "")); j++; }
      out.push({ t: "code", lang: info.trim(), v: body.join("\n"), line: at });
      i = j + 1;
      continue;
    }
    if (/^\s*<!--/.test(ln)) { let j = i; while (j < lines.length && !lines[j].includes("-->")) j++; i = j + 1; continue; }
    m = RE_HEAD.exec(ln);
    if (m) { out.push({ t: "heading", level: m[1].length, c: parseInline(m[2] || "", env), line: at }); i++; continue; }
    if (RE_HR.test(ln)) { out.push({ t: "hr", line: at }); i++; continue; }
    if (RE_QUOTE.test(ln)) {
      const inner = [];
      let j = i;
      while (j < lines.length && !blank(lines[j]) && (RE_QUOTE.test(lines[j]) || (inner.length && !startsBlock(lines[j], false)))) { inner.push(lines[j].replace(/^ {0,3}> ?/, "")); j++; }
      out.push({ t: "quote", c: parseBlocks(inner, base + i, env), line: at });
      i = j;
      continue;
    }
    m = RE_ITEM.exec(ln);
    if (m && !RE_HR.test(ln)) {
      const ordered = /\d/.test(m[2]);
      const list = { t: "list", ordered, start: ordered ? parseInt(m[2], 10) : 1, items: [], line: at };
      let j = i;
      while (j < lines.length) {
        const im = RE_ITEM.exec(lines[j]);
        if (!im || RE_HR.test(lines[j]) || /\d/.test(im[2]) !== ordered || (j > i && indentOf(lines[j]) >= 4)) break;
        const spaces = im[3].length > 4 || im[4] === "" ? 1 : im[3].length;
        const w = im[1].length + im[2].length + spaces;                    // columns taken by the marker; the item's other lines are indented at least this much
        const itemLines = [im[4]];
        const first = j;
        j++;
        while (j < lines.length) {
          const l = lines[j];
          if (blank(l)) {
            let k = j;
            while (k < lines.length && blank(lines[k])) k++;
            if (k < lines.length && indentOf(lines[k]) >= w) { for (; j < k; j++) itemLines.push(""); continue; }
            break;
          }
          if (indentOf(l) >= w) { itemLines.push(l.replace(/\t/g, "    ").slice(w)); j++; continue; }
          if (!itemLines[itemLines.length - 1].trim() || startsBlock(l, true) || RE_ITEM.test(l)) break;      // a lazy continuation line must continue a paragraph
          itemLines.push(l.trim());
          j++;
        }
        let task = null;
        const tm = /^\[([ xX])\][ \t]+/.exec(itemLines[0]);
        if (tm) { task = tm[1] !== " "; itemLines[0] = itemLines[0].slice(tm[0].length); }
        list.items.push({ task, c: parseBlocks(itemLines, base + first, env) });
        let k = j;                                                         // another item of this list, after any blank lines?
        while (k < lines.length && blank(lines[k])) k++;
        if (k >= lines.length || !RE_ITEM.test(lines[k])) break;
        j = k;
      }
      out.push(list);
      i = j;
      continue;
    }
    if (ln.includes("|") && i + 1 < lines.length && RE_DELIM.test(lines[i + 1]) && lines[i + 1].includes("-")) {
      const head = splitRow(ln);
      const delim = splitRow(lines[i + 1]);
      if (head.length === delim.length) {
        const align = delim.map((d) => (/^:-+:$/.test(d) ? "center" : /^-+:$/.test(d) ? "right" : /^:-+$/.test(d) ? "left" : ""));
        const rows = [];
        let j = i + 2;
        while (j < lines.length && !blank(lines[j]) && lines[j].includes("|")) {
          const cells = splitRow(lines[j]);
          while (cells.length < head.length) cells.push("");
          rows.push(cells.slice(0, head.length).map((x) => parseInline(x, env)));
          j++;
        }
        out.push({ t: "table", align, head: head.map((x) => parseInline(x, env)), rows, line: at });
        i = j;
        continue;
      }
    }
    if (indentOf(ln) >= 4) {
      const body = [];
      let j = i;
      while (j < lines.length && (blank(lines[j]) || indentOf(lines[j]) >= 4)) { body.push(lines[j].replace(/\t/g, "    ").slice(4)); j++; }
      while (body.length && blank(body[body.length - 1])) body.pop();
      out.push({ t: "code", lang: "", v: body.join("\n"), line: at });
      i = j;
      continue;
    }
    const para = [ln.replace(/^\s+/, "")];
    let j = i + 1;
    let level = 0;
    while (j < lines.length && !blank(lines[j])) {
      const sm = RE_SETEXT.exec(lines[j]);
      if (sm) { level = sm[1][0] === "=" ? 1 : 2; j++; break; }
      if (startsBlock(lines[j], true) || /^\s*<!--/.test(lines[j]) || (lines[j].includes("|") && j + 1 < lines.length && RE_DELIM.test(lines[j + 1]) && lines[j + 1].includes("-") && splitRow(lines[j]).length === splitRow(lines[j + 1]).length)) break;
      para.push(lines[j].replace(/^\s+/, ""));
      j++;
    }
    const inline = parseInline(para.join("\n"), env);
    out.push(level ? { t: "heading", level, c: inline, line: at } : { t: "para", c: inline, line: at });
    i = j;
  }
  return out;
}

/* Link reference definitions ("[label]: url "title"") are taken out of the text before parsing and kept in env.defs. */
function takeDefinitions(lines, env) {
  let inFence = null;
  return lines.map((l) => {
    const f = RE_FENCE.exec(l);
    if (f && (!inFence || f[2][0] === inFence)) { inFence = inFence ? null : f[2][0]; return l; }
    if (inFence) return l;
    const m = /^ {0,3}\[([^\]]+)\]:[ \t]*<?([^\s>]+)>?(?:[ \t]+["'(](.*?)["')])?[ \t]*$/.exec(l);
    if (!m) return l;
    const key = normLabel(m[1]);
    if (!env.defs.has(key)) env.defs.set(key, { href: m[2], title: m[3] || "" });
    return "";
  });
}

function collectHeadings(blocks, acc, seen) {
  for (const b of blocks) {
    if (b.t === "heading") {
      const base = slugify(plainText(b.c));
      const n = seen.get(base) || 0;
      seen.set(base, n + 1);
      b.id = n ? `${base}-${n}` : base;
      acc.push({ level: b.level, text: plainText(b.c), id: b.id, line: b.line });
    } else if (b.t === "quote") collectHeadings(b.c, acc, seen);
    else if (b.t === "list") b.items.forEach((it) => collectHeadings(it.c, acc, seen));
  }
  return acc;
}

export function parseMarkdown(text) {
  const env = { defs: new Map() };
  let lines = String(text == null ? "" : text).replace(/\r\n?/g, "\n").split("\n");
  let front = null;
  if (lines[0] === "---") {                                                // YAML front matter
    const end = lines.indexOf("---", 1);
    if (end > 0) { front = lines.slice(1, end).join("\n"); lines = [...lines.slice(0, end + 1).map(() => ""), ...lines.slice(end + 1)]; }
  }
  lines = takeDefinitions(lines, env);
  const blocks = parseBlocks(lines, 0, env);
  const headings = collectHeadings(blocks, [], new Map());
  return { blocks, headings, front };
}

/* ------------------------------------------------------------------ DOM */
const SOURCE = (path, line) => buildRoute({ view: "file", path, start: line, tab: "source" });

/* ctx = { path, hasFile(p), hasDir(p), self (the address of this page, for in-page links), highlight (default true) } */
export function renderMarkdown(text, ctx = {}) {
  const doc = parseMarkdown(text);
  const path = ctx.path || "";
  const pending = [];                                                       // code blocks waiting for their colours

  const link = (n, kids) => {
    const r = resolveHref(n.href, ctx);
    const title = n.title || null;
    if (r.kind === "anchor") return h("a", { href: ctx.self || "#", dataset: { anchor: r.id }, title }, kids);
    if (r.kind === "external") return h("a", { href: r.url, target: "_blank", rel: "noopener noreferrer", class: "ex-md__ext", title }, kids);
    if (r.kind === "file") return h("a", { href: buildRoute({ view: "file", path: r.path, start: r.start, end: r.end, tab: r.start ? "source" : "" }), title: title || r.path }, kids);
    if (r.kind === "dir") return h("a", { href: buildRoute({ view: "dir", path: r.path }), title: title || `${r.path}/` }, kids);
    if (r.kind === "missing") return h("span", { class: "ex-md__dead", title: `${r.path} is not in the census` }, kids);
    return h("span", null, kids);                                           // blocked: the words stay, the link does not
  };

  const inline = (nodes) => nodes.map((n) => {
    switch (n.t) {
      case "text": return n.v;
      case "code": return h("code", null, n.v);
      case "em": return h("em", null, inline(n.c));
      case "strong": return h("strong", null, inline(n.c));
      case "del": return h("del", null, inline(n.c));
      case "br": return h("br");
      case "link": return link(n, inline(n.c));
      case "image": {
        const r = resolveHref(n.src, ctx);
        const label = n.alt || String(n.src).split("/").pop() || "image";
        const tag = h("span", { class: "ex-md__img", title: "Images are not loaded here" }, `image: ${label}`);
        if (r.kind === "external") return h("a", { href: r.url, target: "_blank", rel: "noopener noreferrer", class: "ex-md__ext" }, tag);
        if (r.kind === "file") return h("a", { href: buildRoute({ view: "file", path: r.path }) }, tag);
        return tag;
      }
      default: return null;
    }
  });

  const codeBlock = (b) => {
    const lines = b.v.split("\n");
    const lang = langFromFence(b.lang);
    const code = h("code", null, b.v);
    const copy = h("button", { type: "button", class: "mm-btn ex-md__copy", "aria-label": "Copy this code" }, "Copy");
    copy.addEventListener("click", async () => toast((await copyText(b.v)) ? "Copied" : "Could not copy"));
    const label = (b.lang || "").trim().split(/\s/)[0];
    const wrap = h("div", { class: "ex-md__codewrap" }, h("div", { class: "ex-md__codebar" }, h("span", { class: "ex-dim" }, label || "text"), copy), h("pre", { class: `ex-md__code ex-hl is-hl`, tabindex: "0" }, code));
    if (lang && ctx.highlight !== false) pending.push({ code, lines, lang });
    return wrap;
  };

  const block = (b) => {
    switch (b.t) {
      case "heading": {
        const tag = `h${Math.min(6, b.level + 1)}`;                          // the page's own title is the h1
        return h(tag, { class: `ex-md__h ex-md__h${b.level}`, id: `mdh-${b.id}`, tabindex: "-1" }, inline(b.c), " ",
          h("a", { class: "ex-md__src", href: SOURCE(path, b.line), title: `Line ${b.line} in the Source tab`, "aria-label": `Show line ${b.line} in the Source tab` }, `L${b.line}`));
      }
      case "para": return h("p", null, inline(b.c));
      case "code": return codeBlock(b);
      case "hr": return h("hr");
      case "quote": return h("blockquote", null, b.c.map(block));
      case "list": {
        const list = h(b.ordered ? "ol" : "ul", { start: b.ordered && b.start !== 1 ? b.start : null, class: b.items.some((it) => it.task !== null) ? "ex-md__tasks" : null });
        for (const it of b.items) {
          const li = h("li", { class: it.task === null ? null : "ex-md__task" });
          if (it.task !== null) li.append(h("input", { type: "checkbox", disabled: true, checked: it.task, "aria-label": it.task ? "done" : "not done" }), " ");
          li.append(...it.c.map(block));
          list.append(li);
        }
        return list;
      }
      case "table": {
        const th = (cells) => h("tr", null, cells.map((c, k) => h("th", { scope: "col", dataset: { align: b.align[k] || "" } }, inline(c))));
        const tr = (cells) => h("tr", null, cells.map((c, k) => h("td", { dataset: { align: b.align[k] || "" } }, inline(c))));
        return h("div", { class: "mm-tablewrap ex-md__tablewrap" }, h("table", { class: "mm-table is-compact" }, h("thead", null, th(b.head)), h("tbody", null, b.rows.map(tr))));
      }
      default: return null;
    }
  };

  const root = h("article", { class: "ex-md" });
  if (doc.front != null) root.append(h("details", { class: "ex-md__front" }, h("summary", null, "Front matter"), h("pre", { class: "ex-pre" }, doc.front)));
  const toc = doc.headings.filter((x) => x.level <= 3);
  if (toc.length >= 4) {
    const min = Math.min(...toc.map((x) => x.level));
    root.append(h("details", { class: "ex-md__toc", open: true }, h("summary", null, `Contents (${toc.length})`),
      h("ul", null, toc.map((x) => h("li", { class: `ex-md__lv${x.level - min}` }, h("a", { href: ctx.self || "#", dataset: { anchor: x.id } }, x.text))))));
  }
  for (const b of doc.blocks) { const el = block(b); if (el) root.append(el); }
  if (!doc.blocks.length) root.append(h("p", { class: "ex-dim" }, "This file is empty."));

  root.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[data-anchor]");
    if (!a || !root.contains(a)) return;
    e.preventDefault();
    const target = root.querySelector(`[id="mdh-${a.dataset.anchor.replace(/"/g, "")}"]`);
    if (target) { target.scrollIntoView({ block: "start" }); target.focus?.({ preventScroll: true }); }
  });

  /* Colours arrive after the plain text, exactly like the Source tab: text nodes and spans, never HTML. */
  Promise.all(pending.map(async ({ code, lines, lang }) => {
    const res = await highlightWith(lines, lang);
    if (!res) return;
    const kids = [];
    res.lines.forEach((segs, i) => { if (i) kids.push("\n"); segs.forEach((s) => kids.push(s.c ? h("span", { class: s.c }, s.t) : s.t)); });
    code.replaceChildren(...kids);
  })).catch(() => { /* colours are an extra */ });

  return { el: root, headings: doc.headings, blocks: doc.blocks };
}
