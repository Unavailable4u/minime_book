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

**Not refreshed, because the census cannot supply it.** From the Graphify graph: the graph nodes, graph links and guides cards, "Graph hubs", the API "frontend callers" column (carried over per route, blank for routes added since) and the Explore connection edges (carried over per file). From other inputs: Tests, Health, Data model, Tables, Graph, Roadmap, Finance, Decisions and the document pages. Each of those keeps its own "Built ... from commit ..." label, so every page says how old it is.

## Product names

| Product | Short name | Full name | Tagline | CLI / paths |
|---|---|---|---|---|
| Terminal & editor coding agent | M2C | M2C L26 | Minime to Code | `m2c login`, `m2c run`, `~/.m2c/`, `M2C.md` |
| Personal automation agent | Menux | Menux | Minime agentic automation | `menux status`, `menux run`, `~/.menux/` |

L in M2C L26 means Level. Treat a level like a release version: the next release is M2C L27, then L28, and so on.
