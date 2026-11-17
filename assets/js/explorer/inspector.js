/* MiniMe Atlas 2 - Explorer inspector (P13): the right-hand column. For a file it shows what it is connected to (imports, imported by,
   graph neighbours, external packages) and its history. Everything here comes from the census and the graph, none of it is AI-written,
   so nothing in this column carries the AI label. Lists show 12 entries and open to all of them. */
import { h, num, day } from "./dom.js";
import { buildRoute } from "./router.js";
import { monthBuckets } from "./model.js";

const SVG = "http://www.w3.org/2000/svg";
const SHOW = 12;

export function sparkline(counts, label) {
  const w = 160;
  const hgt = 34;
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${hgt}`);
  svg.setAttribute("class", "ex-spark");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", label);
  const max = Math.max(1, ...counts);
  const bw = w / counts.length;
  counts.forEach((c, i) => {
    const r = document.createElementNS(SVG, "rect");
    const bh = c ? Math.max(3, (c / max) * (hgt - 2)) : 1;
    r.setAttribute("x", String(i * bw + 1));
    r.setAttribute("y", String(hgt - bh));
    r.setAttribute("width", String(Math.max(1, bw - 2)));
    r.setAttribute("height", String(bh));
    r.setAttribute("class", c ? "ex-spark__bar" : "ex-spark__zero");
    svg.append(r);
  });
  return svg;
}

function pathLink(core, path, extra) {
  const known = core.tree.files.has(path);
  return h("li", null, known ? h("a", { href: buildRoute({ view: "file", path }) }, path) : h("span", { class: "ex-dim" }, path), extra ? h("span", { class: "ex-dim" }, ` ${extra}`) : null);
}

function list(title, items, note) {
  const box = h("section", { class: "ex-insp__sec" });
  box.append(h("h3", null, title, h("span", { class: "ex-dim" }, ` ${num(items.length)}`)));
  if (note) box.append(h("p", { class: "ex-insp__note" }, note));
  if (!items.length) { box.append(h("p", { class: "ex-dim" }, "none")); return box; }
  const ul = h("ul", { class: "ex-insp__list" }, items.slice(0, SHOW));
  box.append(ul);
  if (items.length > SHOW) {
    const btn = h("button", { type: "button", class: "ex-link" }, `Show all ${num(items.length)}`);
    btn.addEventListener("click", () => { ul.replaceChildren(...items); btn.remove(); });
    box.append(btn);
  }
  return box;
}

export function renderInspector(host, core, file, rec) {
  host.replaceChildren();
  host.append(h("h2", { class: "ex-insp__title" }, "Relations"));
  const im = core.imports;
  if (im) {
    host.append(list("Imports", ((im.imports || {})[file.path] || []).map((p) => pathLink(core, p))));
    host.append(list("Imported by", ((im.imported_by || {})[file.path] || []).map((p) => pathLink(core, p))));
    const ext = im.external && im.external[file.path];
    if (ext && ext.length) host.append(h("section", { class: "ex-insp__sec" }, h("h3", null, "External packages", h("span", { class: "ex-dim" }, ` ${ext.length}`)), h("p", { class: "ex-chips" }, ext.map((e) => h("code", null, e)))));
  } else host.append(h("p", { class: "ex-dim" }, "data/code/imports.json is not available."));

  if (core.fileLinks) {
    const near = core.fileLinks.map.get(file.path) || [];
    host.append(list("Graph neighbours", near.map((x) => pathLink(core, x.path, `· ${x.n} link${x.n === 1 ? "" : "s"}`)),
      `Files that share the most links with this one in the knowledge graph (Graphify, commit ${core.fileLinks.commit || "?"}). Inferred, not imports.`));
  } else {
    host.append(h("section", { class: "ex-insp__sec" }, h("h3", null, "Graph neighbours"), h("p", { class: "ex-dim" }, "Not built yet. Run python scripts/refresh_graph.py --minime ../MiniMe to write data/graph/file-links.json.")));
  }

  const g = rec && rec.git;
  const sec = h("section", { class: "ex-insp__sec" }, h("h3", null, "History"));
  if (g && g.commits) {
    const b = monthBuckets(g.dates);
    sec.append(h("p", { class: "ex-insp__hist" }, `${num(g.commits)} commit${g.commits === 1 ? "" : "s"}, ${day(g.first)} to ${day(g.last)}`));
    if (b.counts.length) {
      sec.append(sparkline(b.counts, `Commits per month, ${b.first} to ${b.last}: ${b.counts.join(", ")}`));
      sec.append(h("p", { class: "ex-insp__note" }, `Commits per month, ${b.first} to ${b.last}.`));
    }
    sec.append(h("p", { class: "ex-insp__hist" }, `+${num(g.added)} / −${num(g.deleted)} lines in total`));
  } else sec.append(h("p", { class: "ex-dim" }, "No git history for this file in the census."));
  host.append(sec);
}

export function renderHelp(host) {
  host.replaceChildren(
    h("h2", { class: "ex-insp__title" }, "Keys"),
    h("dl", { class: "ex-keys" },
      ...[["/", "filter the tree"], ["j / k", "move in the tree"], ["l / h", "open / close a folder"], ["Enter", "open the file or folder"], ["o", "open the file on GitHub"], ["Ctrl+K", "search everything"]]
        .flatMap(([k, v]) => [h("dt", null, h("kbd", null, k)), h("dd", null, v)])));
}
