https://minimebook.vercel.app/

## Team to-do (live shared list)

`todo.html` is a shared to-do, workload view and timeline. It also edits the master timeline dates that `roadmap.html` shows, so both pages always agree.

- No login. Anyone with the site link can read and edit, on purpose, so the team can fix each other's work.
- Data lives in a hosted Redis through `api/todo.js` (a Vercel serverless function, no npm packages).
- Changes show up for everyone within a few seconds. Offline edits are kept on the device and sync when back online.
- Safety: deletes go to a trash, the server keeps a snapshot of the whole list for every day for 35 days, and Settings has a download/restore backup.

One-time setup (about 2 minutes):

1. Vercel dashboard, your project, **Storage**, **Create Database**, pick **Upstash for Redis** (Marketplace), connect it to this project (all environments).
2. That adds the `KV_REST_API_URL` and `KV_REST_API_TOKEN` environment variables automatically.
3. Redeploy the project once. Open `todo.html`: the pill at the top should say **Live**. The first visit loads the starter data from `data/todo.json`.

Until the database is connected, the page still works but only on the one device, and says so in the pill.

Master timeline items live in `data/master-timeline.js`. Edit that file to add or rename items.

## Keeping the Atlas in step with the code

The Overview, Files, Functions, History, Map, API, Agents, Infra and Explore pages, plus `data/summary.md`, are generated from `data/census.json` by `scripts/refresh_atlas.py` (Python standard library only). The census itself is made by MiniMe's `scripts/codebase_census.py`.

**Automatic:** push a new `data/census.json` to `main`. `.github/workflows/refresh-atlas.yml` re-renders the pages, commits them, and Vercel deploys that commit. One-time setup: GitHub, Settings, Actions, General, Workflow permissions, **Read and write**.

**To make a new census and refresh everything in one command**, from this repo with a clean MiniMe checkout next to it (the folder must be named `MiniMe`):

```
pip install tree-sitter tree-sitter-javascript pyyaml
python scripts/refresh_atlas.py --census-from ../MiniMe
```

It refuses to replace `data/census.json` if the new one is untrustworthy (no tree-sitter, no PyYAML, or uncommitted files in MiniMe, which the census would count). Then commit and push.

Other commands: `python scripts/refresh_atlas.py` refreshes from the census you already have, `--check` changes nothing and exits 1 if anything is out of date, and `python scripts/test_refresh_atlas.py` runs the tests.

**Search (Ctrl/Cmd+K).** The command palette reads `data/index/*.json`, which `scripts/build_index.py` builds from `content/nav.json`, the chapter headings, the glossary and `data/census.json`. `refresh_atlas.py` rebuilds it with the pages, so the automatic route above keeps it current; run `python scripts/build_index.py` on its own after you edit `nav.json` or a chapter, and `--check` to see whether it is stale. Operators: `>` pages, `#` book headings, `/` files, `@` functions and classes, `:` API routes, `?` help. Keys: `t` theme, `?` shortcut sheet, `g` then `o` / `e` / `b` / `s` to jump. The palette needs `http(s)`, so test it with `python scripts/serve.py`, not by opening the file.

**Chapter reader (P04).** The 15 chapter pages are typeset at run time by `assets/js/reader.js` and `assets/css/reader.css`; `shell.js` loads them only on pages that have a chapter banner or a `.doc article`, and **no `doc-*.html` file is edited**, so the external page builder can keep overwriting them. It gives serif/sans and five text sizes (the **Aa** button), an **On this page** rail built from the headings (`]` toggles it; a bottom sheet below 1200 px), a chapter bar with progress and previous / next, remembered reading position with a "resume" toast, typed callouts (`Purpose:`, `Rule:` ...), scrollable tables with a sticky header and a filter box above 25 rows, copy-link on headings, a copy button on code, and print rules. Its switches are in `content/reader.json`: per-chapter `numbered`, the table filter threshold and the callout patterns. `python scripts/list_headings.py <chapter>` prints heading ids (for placing figures later). Tests: `python scripts/test_reader.py`.

**Library and glossary (P05).** `docs.html` is the book's table of contents, drawn in the browser by `assets/js/library.js` from `data/index/book.json`: one card per chapter with read time, sections, tables, last-built date, a progress ring and a Continue button (both read what the chapter reader remembered), five part filters, a search over chapter titles and section headings, and the reading paths. `book.json` is written by `scripts/build_index.py` from each chapter's own banner (`.bk-desc`, `.bk-meta`, the "Built ... from commit ..." line), so the counts cannot drift; the two interactive design specs have no counts and say so. `glossary.html` shows `content/glossary.json` (term, aliases, category, short, long, `see`, optional `match` and `needs_review`). In a chapter the first use of each term per section gets a dotted underline and a tooltip (hover, focus or tap; `Esc` closes); a term with `"match": "off"` (ordinary words like *wave*) appears on the glossary page only, `"cs"` matches the exact case, and `"glossary": false` in `content/reader.json` turns tooltips off for a chapter or everywhere. A `see` is a chapter id (`doc-rulebook`, or `doc-rulebook#1-the-15-golden-rules`), a repo file, or `file::symbol`; `content/reading-paths.json` uses the same targets, and `check_site.py` fails if any of them is missing. Add a term by editing `content/glossary.json`, then `python scripts/build_index.py` so the palette finds it. Tests: `python scripts/test_library.py`.

**Figures (P06).** Diagrams are put into the chapters at run time by `assets/js/figures.js` (loaded by `shell.js` after the reader), so no `doc-*.html` file is edited. Each chapter has an optional manifest `content/figures/<chapter id>.json`: `{id, after, place, type, src | code, caption, alt, wide, size}`, where `after` is a heading id (`python scripts/list_headings.py <chapter>`), `type` is `archify` (an `architecture/*.html` page in an iframe; `size` is the pixel size of its SVG), `svg` (a file in `content/figures/svg/` or inline `code`, drawn with the theme tokens) or `mermaid` (needs `python scripts/vendor_mermaid.py` once). Figures are numbered per chapter (Figure 4.2), follow the Dark / Paper theme, and have an Expand viewer (wheel / pinch zoom, drag, `+ - 0 1`, `Esc`). `alt` is required and `check_site.py` validates every manifest and SVG. Tests: `python scripts/test_figures.py`.

**Overview (P07).** `index.html` is a shell: `assets/js/overview.js` and `assets/css/overview.css` draw it from `data/index/vitals.json` (the census half is written by `refresh_atlas.py`, the graph half by `refresh_graph.py`), `content/subsystems.json` (directory table), `content/system/request-path.json` ("Anatomy of a request", shared with the System page) and the hand-written `content/overview/*.html`. `scripts/test_overview.py` tests the helpers in Node.

**Topology (P08).** The "System at a glance" diagram on the Overview: `assets/js/topology.js` and `assets/css/topology.css` draw it from `content/topology.json` (the hand-curated layout), `data/index/vitals.json` `census.topology` (box size = code lines, from `refresh_atlas.py`) and `data/graph/folders.json` (line width = graph links, from `refresh_graph.py`). Hover or focus a box for its details, click it for links, follow one request through it, or open the M2C client into its 9 parts. `?edit=1` lets you drag boxes and copy the new layout as JSON. `scripts/test_topology.py` tests the helpers in Node and the layout against the census; the rules are in `check_site.py`.

**Not refreshed, because the census cannot supply it.** From the Graphify graph (now the `graph` half of `data/index/vitals.json`): the graph nodes and links, "Graph hubs", the API "frontend callers" column (carried over per route, blank for routes added since) and the Explore connection edges (carried over per file). From other inputs: Tests, Health, Data model, Tables, Graph, Roadmap, Finance, Decisions and the document pages. Each of those keeps its own "Built ... from commit ..." label, so every page says how old it is.

## Product names

| Product | Short name | Full name | Tagline | CLI / paths |
|---|---|---|---|---|
| Terminal & editor coding agent | M2C | M2C L26 | Minime to Code | `m2c login`, `m2c run`, `~/.m2c/`, `M2C.md` |
| Personal automation agent | Menux | Menux | Minime agentic automation | `menux status`, `menux run`, `~/.menux/` |

L in M2C L26 means Level. Treat a level like a release version: the next release is M2C L27, then L28, and so on.
