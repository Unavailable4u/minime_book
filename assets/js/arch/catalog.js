/* MiniMe Atlas 2 - architecture: catalog view (P26). The API surface: route groups as cards, routes as rows.

   Fully derived: data/arch/derived.json catalogues.routes comes from the census (routers, their prefixes, the handlers); nothing to write
   and nothing to go stale. The page for one route's callers and notes is api.html; here a click gives the handler's place in the code. */

import { CARD, catalogLayout } from "./layout.js";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

/* [{id, title, prefix, node, file, router, count, rows: [route arrays]}]; `filter` keeps the routes whose method, path or handler contain it,
   and the groups that still have one. */
export function groupsOf(catalogue, filter = "") {
  const q = String(filter || "").trim().toLowerCase();
  const out = [];
  for (const g of catalogue || []) {
    const rows = (g.routes || []).filter((r) => !q || r.slice(0, 3).some((x) => String(x).toLowerCase().includes(q)));
    if (!rows.length) continue;
    out.push({ id: g.file + "::" + (g.router || ""), title: g.router || g.file.split("/").pop(), prefix: g.prefix || "", node: g.node, file: g.file, router: g.router, count: (g.routes || []).length, rows, raw: g });
  }
  return out;
}

export const totalRoutes = (catalogue) => (catalogue || []).reduce((n, g) => n + (g.routes || []).length, 0);

export const clip = (text, max) => (String(text).length > max ? String(text).slice(0, max - 1) + "…" : String(text));

export function draw(ctx, groups, width = 1240) {
  const { svg } = ctx;
  const L = catalogLayout(groups.map((g) => ({ id: g.id, rows: g.rows.length })), width);
  const [W, H] = [L.size[0], Math.max(L.size[1], 120)];
  const s = ctx.root(W, H);
  const centers = [];
  groups.forEach((g, i) => {
    const c = L.cards[i];
    const card = svg("g", { class: "ar-card", transform: `translate(${c.x},${c.y})` });
    card.append(svg("rect", { class: "ar-card__r", width: c.w, height: c.h, rx: 12 }),
      svg("text", { class: "ar-card__t", x: 14, y: 22 }, clip(g.title, 32)),
      svg("text", { class: "ar-card__n", x: c.w - 14, y: 22, "text-anchor": "end" }, `${g.rows.length}${g.rows.length !== g.count ? ` of ${g.count}` : ""} ${g.rows.length === 1 && g.rows.length === g.count ? "route" : "routes"}`),
      svg("text", { class: "ar-card__s", x: 14, y: 38 }, clip(`${g.prefix ? g.prefix + " · " : ""}${g.file}`, 54)));
    g.rows.forEach((r, k) => {
      const y = CARD.head + k * CARD.row;
      const m = String(r[0]).toUpperCase(), row = svg("g", { class: "ar-route", transform: `translate(0,${y})` });
      row.append(svg("rect", { class: "ar-route__bg", x: 6, y: -1, width: c.w - 12, height: CARD.row - 1, rx: 4 }),
        svg("text", { class: `ar-route__m ar-m--${m.toLowerCase()}`, x: 14, y: 11 }, m.slice(0, 6)),
        svg("text", { class: "ar-route__p", x: 62, y: 11 }, clip(r[1], 46)),
        svg("title", {}, `${m} ${r[1]} → ${r[2]}${r[3] ? ` (${g.file}:${r[3]})` : ""}`));
      ctx.mk(`r:${g.id}:${k}`, row, { type: "route", group: g.raw, route: r }, `${m} ${r[1]}, handler ${r[2]}`);
      card.append(row);
      centers.push({ id: `r:${g.id}:${k}`, x: c.x + 100, y: c.y + y });
    });
    s.append(card);
  });
  const nodes = groups.map((g) => ({ id: g.id, label: `${g.title} (${g.rows.length})` }));
  return { el: s, size: [W, H], centers, mermaid: { type: "catalog", nodes, edges: [] } };
}
