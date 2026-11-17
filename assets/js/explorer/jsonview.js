/* MiniMe Atlas 2 - Explorer JSON structure view (P14e). A JSON file as a folding tree instead of as a wall of text.

   Pure half (no DOM, Node tests it):
     parseJsonText(text)        { ok, value, relaxed } | { ok:false, error, line, col }   strict first; then once more with comments
                                and trailing commas removed (tsconfig-style files), which is reported as `relaxed`
     describe(value)            "object, 5 keys" / "array, 12 items" / "string" ...
     pathString(parts)          ["a", 0, "b-c"] -> $.a[0]['b-c']
     countNodes(value, cap)     how many values the tree holds (stops counting at cap)
     schemaSummary(value)       for a JSON Schema: title, description, required list and a property table; else null

   DOM half:
     renderJson(text, ctx)      -> { el } or { el, invalid: true }

   The tree is lazy: a folded object or array has not been turned into elements yet, so a 60 KB list of 400 records opens at once and
   only the part the reader unfolds is built. Containers show a hint of their first keys while folded. Long arrays and objects are cut
   into pages of 100 ("Show 100 more"); long strings are cut at 200 characters ("show all"). A key is a button: it copies that
   value's path ($.properties.v). Text only ever goes in as text nodes.

   The generic tree is all a non-schema file gets. The property table for a JSON Schema is a convenience, not the schema viewer of P24
   (which follows $ref across files and draws the message contract); it never fetches anything. */
import { h, copyText, toast, num } from "./dom.js";
import { buildRoute } from "./router.js";

export const MAX_CHARS = 3000000;
const PAGE = 100;
const STR_CUT = 200;
const OPEN_ALL_CAP = 3000;                       // "Expand all" builds every node; refuse above this many

/* ------------------------------------------------------------------ parsing */
/* Comments and trailing commas removed, string contents left alone. Line breaks stay, so positions still match. */
export function stripJsonc(text) {
  let out = "";
  let i = 0;
  const n = text.length;
  while (i < n) {
    const c = text[i];
    if (c === '"') {
      let j = i + 1;
      while (j < n && text[j] !== '"') j += text[j] === "\\" ? 2 : 1;
      out += text.slice(i, j + 1);
      i = j + 1;
    } else if (c === "/" && text[i + 1] === "/") {
      while (i < n && text[i] !== "\n") i++;
    } else if (c === "/" && text[i + 1] === "*") {
      const e = text.indexOf("*/", i + 2);
      const stop = e < 0 ? n : e + 2;
      out += text.slice(i, stop).replace(/[^\n]/g, "");
      i = stop;
    } else { out += c; i++; }
  }
  return out.replace(/,(\s*[}\]])/g, "$1");
}

function where(text, e) {
  const msg = String((e && e.message) || e);
  let pos = null;
  let m = /position (\d+)/.exec(msg);
  if (m) pos = Number(m[1]);
  m = /line (\d+) column (\d+)/.exec(msg);
  if (m) return { line: Number(m[1]), col: Number(m[2]) };
  if (pos == null) return { line: null, col: null };
  const head = text.slice(0, pos).split("\n");
  return { line: head.length, col: head[head.length - 1].length + 1 };
}

export function parseJsonText(text) {
  const src = String(text == null ? "" : text).replace(/^\uFEFF/, "");
  try { return { ok: true, value: JSON.parse(src), relaxed: false }; } catch (e) {
    try { return { ok: true, value: JSON.parse(stripJsonc(src)), relaxed: true }; } catch { /* report the first error: it is the one in the reader's file */ }
    return { ok: false, error: String((e && e.message) || e).replace(/\s*\(line \d+ column \d+\)/, ""), ...where(src, e) };
  }
}

/* ------------------------------------------------------------------ small pure helpers */
export function typeOf(v) { return v === null ? "null" : Array.isArray(v) ? "array" : typeof v; }

export function describe(v) {
  const t = typeOf(v);
  if (t === "object") { const n = Object.keys(v).length; return `object, ${n} key${n === 1 ? "" : "s"}`; }
  if (t === "array") return `array, ${v.length} item${v.length === 1 ? "" : "s"}`;
  return t;
}

const SIMPLE_KEY = /^[A-Za-z_$][\w$]*$/;
export function pathString(parts) {
  return parts.reduce((s, p) => (typeof p === "number" ? `${s}[${p}]` : SIMPLE_KEY.test(p) ? `${s}.${p}` : `${s}['${String(p).replace(/\\/g, "\\\\").replace(/'/g, "\\'")}']`), "$");
}

export function countNodes(v, cap = Infinity) {
  let n = 0;
  const stack = [v];
  while (stack.length && n <= cap) {
    const x = stack.pop();
    n++;
    if (Array.isArray(x)) stack.push(...x);
    else if (x && typeof x === "object") stack.push(...Object.values(x));
  }
  return n;
}

const childrenOf = (v) => (Array.isArray(v) ? v.map((x, i) => [i, x]) : Object.entries(v));
const isContainer = (v) => v !== null && typeof v === "object";

/* One property's type as a short phrase: "string", "string | null", "array of Thing", "-> common.json#/$defs/id", "enum (3)", "oneOf (2)". */
function typeLabel(s) {
  if (s === true) return "any";
  if (s === false) return "never";
  if (!s || typeof s !== "object") return "?";
  if (typeof s.$ref === "string") return `-> ${s.$ref}`;
  if (Array.isArray(s.enum)) return `enum (${s.enum.length})`;
  if (s.const !== undefined) return `const ${JSON.stringify(s.const)}`;
  for (const k of ["oneOf", "anyOf", "allOf"]) if (Array.isArray(s[k])) return `${k} (${s[k].length})`;
  const t = Array.isArray(s.type) ? s.type.join(" | ") : s.type;
  if (t === "array" || (Array.isArray(s.type) && s.type.includes("array"))) return s.items && typeof s.items === "object" && !Array.isArray(s.items) ? `array of ${typeLabel(s.items)}` : "array";
  return t || (s.properties ? "object" : "?");
}

export function schemaSummary(v) {
  if (!v || typeof v !== "object" || Array.isArray(v)) return null;
  const props = v.properties && typeof v.properties === "object" && !Array.isArray(v.properties) ? v.properties : null;
  const isSchema = typeof v.$schema === "string" && /json-schema\.org/.test(v.$schema);
  if (!props && !isSchema) return null;
  const required = Array.isArray(v.required) ? v.required.filter((x) => typeof x === "string") : [];
  return {
    title: typeof v.title === "string" ? v.title : "", description: typeof v.description === "string" ? v.description : "",
    id: typeof v.$id === "string" ? v.$id : "", dialect: typeof v.$schema === "string" ? v.$schema : "", required,
    props: props ? Object.entries(props).map(([name, s]) => ({ name, type: typeLabel(s), required: required.includes(name), desc: s && typeof s === "object" && typeof s.description === "string" ? s.description : "" })) : [],
    defs: v.$defs && typeof v.$defs === "object" ? Object.keys(v.$defs) : [],
  };
}

/* ------------------------------------------------------------------ DOM */
function valueEl(v) {
  const t = typeOf(v);
  if (t === "string") {
    const el = h("span", { class: "ex-j__v ex-j__v--string" });
    const q = JSON.stringify(v);
    if (q.length <= STR_CUT) { el.textContent = q; return el; }
    const more = h("button", { type: "button", class: "ex-j__more" }, `show all ${num(v.length)} characters`);
    el.append(`${q.slice(0, STR_CUT)}…`, " ", more);
    more.addEventListener("click", () => el.replaceChildren(q));
    return el;
  }
  return h("span", { class: `ex-j__v ex-j__v--${t}` }, String(v));
}

/* ctx = { path, onLine(line) -> href of the Source tab at that line (for the parse error) } */
export function renderJson(text, ctx = {}) {
  const root = h("div", { class: "ex-j" });
  if (String(text).length > MAX_CHARS) {
    root.append(h("p", { class: "ex-callout ex-callout--warn" }, `This file is ${num(String(text).length)} characters, too big to unfold here. Use the Source tab.`));
    return { el: root, invalid: true };
  }
  const parsed = parseJsonText(text);
  if (!parsed.ok) {
    const at = parsed.line ? ` at line ${parsed.line}${parsed.col ? `, column ${parsed.col}` : ""}` : "";
    root.append(h("p", { class: "ex-callout ex-callout--warn" }, `This file is not valid JSON: ${parsed.error}${at}. `,
      parsed.line && ctx.path ? h("a", { href: buildRoute({ view: "file", path: ctx.path, start: parsed.line, tab: "source" }) }, "Show that line in the Source tab") : null));
    return { el: root, invalid: true };
  }
  const value = parsed.value;
  if (parsed.relaxed) root.append(h("p", { class: "ex-callout" }, "Comments or trailing commas in this file were ignored to build the tree. Strict JSON parsers would reject it."));

  const sum = schemaSummary(value);
  if (sum) {
    const box = h("section", { class: "ex-j__schema" }, h("h3", null, sum.title || "JSON Schema"));
    if (sum.description) box.append(h("p", null, sum.description));
    box.append(h("p", { class: "ex-dim" }, [sum.id ? h("code", null, sum.id) : null, sum.dialect ? ` · ${sum.dialect.replace(/^https?:\/\//, "")}` : null,
      sum.required.length ? ` · required: ${sum.required.join(", ")}` : null, sum.defs.length ? ` · ${sum.defs.length} definitions: ${sum.defs.slice(0, 8).join(", ")}${sum.defs.length > 8 ? ", …" : ""}` : null]));
    if (sum.props.length) {
      const body = h("tbody", null, sum.props.map((p) => h("tr", null, h("td", null, h("code", null, p.name)), h("td", null, p.type), h("td", null, p.required ? "required" : ""), h("td", null, p.desc))));
      box.append(h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact" }, h("thead", null, h("tr", null, ["Property", "Type", "", "Description"].map((x) => h("th", { scope: "col" }, x)))), body)));
    }
    root.append(box);
  }

  /* ---- the tree */
  const total = countNodes(value, OPEN_ALL_CAP);
  const bar = h("div", { class: "ex-j__bar" });
  const expand = h("button", { type: "button", class: "mm-btn" }, "Expand all");
  const collapse = h("button", { type: "button", class: "mm-btn" }, "Collapse all");
  bar.append(expand, collapse, h("span", { class: "ex-dim" }, describe(value)));
  expand.disabled = total > OPEN_ALL_CAP;
  if (expand.disabled) expand.title = `Too many values to open at once (more than ${num(OPEN_ALL_CAP)}). Unfold the parts you want.`;
  const tree = h("ul", { class: "ex-j__tree", "aria-label": "JSON structure" });
  root.append(bar, tree);

  const toggles = [];                                                        // every container's { open(), close() }, for Expand / Collapse all

  function row(key, v, parts) {
    const label = key === null ? null : h("button", { type: "button", class: "ex-j__k", title: `Copy path ${pathString(parts)}` }, typeof key === "number" ? String(key) : JSON.stringify(key));
    if (label) label.addEventListener("click", async () => toast((await copyText(pathString(parts))) ? `Copied ${pathString(parts)}` : "Could not copy"));
    if (!isContainer(v)) return h("li", null, label, label ? h("span", { class: "ex-j__colon" }, ": ") : null, valueEl(v));
    const kids = childrenOf(v);
    const empty = kids.length === 0;
    const isArr = Array.isArray(v);
    const tg = h("button", { type: "button", class: "ex-j__tg", "aria-expanded": "false", "aria-label": "Unfold" }, "▸");
    const hint = h("span", { class: "ex-j__hint ex-dim" });
    const list = h("ul", { hidden: true });
    let built = 0;
    const more = h("button", { type: "button", class: "mm-btn ex-j__page" });
    const build = (upTo) => {
      const to = Math.min(kids.length, upTo);
      const frag = document.createDocumentFragment();
      for (; built < to; built++) frag.append(row(kids[built][0], kids[built][1], [...parts, kids[built][0]]));
      list.insertBefore(frag, more.parentNode === list ? more : null);
      if (built < kids.length) { more.textContent = `Show ${Math.min(PAGE, kids.length - built)} more (${num(kids.length - built)} not shown)`; if (more.parentNode !== list) list.append(more); } else more.remove();
    };
    more.addEventListener("click", () => build(built + PAGE));
    const setHint = (open) => {
      const n = kids.length;
      hint.textContent = open ? ` ${isArr ? "[" : "{"}${n}${isArr ? "]" : "}"}`
        : empty ? (isArr ? " []" : " {}")
          : isArr ? ` [${n}]` : ` {${kids.slice(0, 4).map(([k]) => k).join(", ")}${n > 4 ? ", …" : ""}}`;
    };
    const set = (open) => {
      if (empty) return;
      if (open && !built) build(PAGE);
      list.hidden = !open;
      tg.setAttribute("aria-expanded", String(open));
      tg.textContent = open ? "▾" : "▸";
      tg.setAttribute("aria-label", open ? "Fold" : "Unfold");
      setHint(open);
    };
    setHint(false);
    if (empty) tg.disabled = true;
    tg.addEventListener("click", () => set(list.hidden));
    toggles.push({ open: () => set(true), close: () => set(false), depth: parts.length });
    const li = h("li", null, tg, label, label ? h("span", { class: "ex-j__colon" }, ": ") : null, hint, list);
    li.__set = set;
    return li;
  }

  const top = row(null, value, []);
  tree.append(top);
  if (top.__set) top.__set(true);                                            // the root is open; everything below it starts folded
  expand.addEventListener("click", () => { for (let k = 0; k < toggles.length; k++) toggles[k].open(); });     // toggles grows while it runs: opening builds more rows
  collapse.addEventListener("click", () => { toggles.forEach((t) => t.close()); if (top.__set) top.__set(true); });
  return { el: root };
}
