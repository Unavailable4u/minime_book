/* A box that scrolls must be reachable by keyboard (WCAG 2.1.1), but a box that does not overflow must not be a tab
   stop: ninety tables in one chapter would be ninety stops. reachable() watches the box and gives it tabindex, a role
   and a name only while it really scrolls. Used by reader.js (chapter tables) and protocol.js (field tables). (P23) */

export function overflows(box) {
  return box.scrollWidth > box.clientWidth + 1 || box.scrollHeight > box.clientHeight + 1;
}

export function reachable(box, label) {
  const sync = () => {
    if (overflows(box)) {
      box.tabIndex = 0;
      box.setAttribute("role", "region");
      box.setAttribute("aria-label", label);
    } else {
      box.removeAttribute("tabindex");
      box.removeAttribute("role");
      box.removeAttribute("aria-label");
    }
  };
  if (typeof ResizeObserver === "function") {
    const ro = new ResizeObserver(sync);
    ro.observe(box);
    if (box.firstElementChild) ro.observe(box.firstElementChild);      // the table inside grows when it is filtered or rendered later
  } else sync();
  return sync;
}

/* the heading a table sits under, so "Table 3: Pricing tiers" names it and no two labels are equal */
export function labelFor(node, n, kind = "Table") {
  for (let el = node; el; el = el.parentElement) {
    for (let p = el.previousElementSibling; p; p = p.previousElementSibling) {
      if (/^H[1-6]$/.test(p.tagName) && p.textContent.trim()) return `${kind} ${n}: ${p.textContent.trim().slice(0, 60)}`;
    }
    if (el.tagName === "MAIN" || el.tagName === "ARTICLE") break;
  }
  return `${kind} ${n}`;
}
