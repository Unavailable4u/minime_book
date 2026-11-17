/* MiniMe Atlas 2 - Explorer DOM helper (P13). h("div", { class: "x", onclick }, "text", child, ...) builds an element.
   Text is always added with createTextNode, never as HTML, so a file name or a docstring can not inject markup. */

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, String(v));
  }
  add(el, kids);
  return el;
}

function add(el, kids) {
  for (const k of kids) {
    if (k == null || k === false) continue;
    if (Array.isArray(k)) add(el, k);
    else el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}

export const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };

export const num = (n) => (Number.isFinite(n) ? n.toLocaleString("en-US") : "?");

/* "2026-10-21" -> "21 Oct 2026" */
export function day(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  if (!m) return iso || "?";
  const mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(m[2]) - 1];
  return `${Number(m[3])} ${mon} ${m[1]}`;
}

export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* fall through to the textarea route */ }
  try {
    const t = h("textarea", { "aria-hidden": "true", style: "position:fixed;left:-999px;top:0" });
    t.value = text;
    document.body.append(t);
    t.select();
    const ok = document.execCommand("copy");
    t.remove();
    return ok;
  } catch { return false; }
}

let toastTimer = 0;
export function toast(msg) {
  let t = document.getElementById("ex-toast");
  if (!t) { t = h("div", { id: "ex-toast", class: "ex-toast", role: "status", "aria-live": "polite" }); document.body.append(t); }
  t.textContent = msg;
  t.classList.add("is-on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("is-on"), 2200);
}
