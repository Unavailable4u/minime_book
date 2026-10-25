# Updating the whole Atlas (census + graph) in one command

The Atlas has two kinds of generated content:

| From | Refreshed by | Pages |
|---|---|---|
| `data/census.json` (MiniMe's `scripts/codebase_census.py`) | `scripts/refresh_atlas.py` | Overview, Files, Functions, History, Map, API, Agents, Infra, Explore, `data/summary.md` |
| The Graphify graph (`MiniMe/graphify-out/`) | `scripts/refresh_graph.py` | Graph and its viewer, Overview graph numbers and hubs, Explore connections, API "Frontend callers", `data/summary.md` graph line |

`scripts/update_all.py` runs both, then proves nothing is stale and runs the tests.

## The routine

**1. In MiniMe: commit your work.** The census and the graph both describe a commit, and the census refuses a repo with uncommitted files.

**2. In MiniMe: regenerate the graph with Copilot** (Agent mode). Paste:

```
Rebuild the graphify knowledge graph for this repository so it matches the CURRENT state of the codebase.

1. Read graphify-out/command.txt and reuse the exact method that produced the existing graph.
2. Run `git status` and `git log -1 --oneline`. Tell me the branch and commit. If there are uncommitted changes, stop and tell me.
3. Run the incremental update (`graphify update .` or the /graphify --update equivalent) on the repo root. Skip graphify-out/, .git/, node_modules/, virtual environments, build output and anything that looks like a secret. If the result looks stale or inconsistent (deleted files still present), delete graphify-out/cache and graphify-out/manifest.json and do a full rebuild.
4. Regenerate graphify-out/graph.json, graph.html and GRAPH_REPORT.md.
5. Verify: `built_at_commit` inside graph.json equals `git rev-parse HEAD`; files deleted since the last graph are gone; report node, edge and community counts (before and after if you can).
6. Update graphify-out/command.txt with the exact commands you ran.

Rules: do not modify source code, do not commit or push, do not ask me questions unless something blocks you.
```

**3. In minime_book:**

```powershell
cd path\to\minime_book
pip install tree-sitter tree-sitter-javascript pyyaml     # once
python scripts/update_all.py --push
```

`--push` commits and pushes when everything passed, and Vercel deploys it. Leave `--push` off to look at the result first (`git diff --stat`, open the pages) and publish yourself.

MiniMe is expected next to this repo in a folder named `MiniMe`. Otherwise add `--minime "E:\python workplace\code\MiniMe"`.

## What `update_all.py` checks and does

1. MiniMe has no uncommitted or untracked files, and `graphify-out/graph.json` was built at MiniMe's current commit. If not, it stops and tells you which step to redo. This stops the site from mixing two versions of the code.
2. `refresh_atlas.py --census-from <MiniMe>`: new census, then every census-driven page.
3. `refresh_graph.py --minime <MiniMe>`: every Graphify-driven part.
4. Both scripts with `--check`, then the unit tests of both.
5. With `--push`: `git add -A`, commit, `git pull --rebase`, `git push`.

The GitHub Action (`refresh-atlas.yml`) still runs when `data/census.json` is pushed. After this routine it finds nothing to change, so it commits nothing.

## How the graph-driven numbers are worked out

* **Counts**: nodes, links and communities in `graph.json`.
* **Graph hubs**: the 10 nodes with the most links that belong to a source file (library nodes such as `json` or `os` have no file and are skipped).
* **Folder matrix and "Strongest cross-folder links"**: links counted from the folder of the source node to the folder of the target node, tests excluded. A folder is `backend/eo`, `frontend/app/components` and so on. The 14 busiest folders get a row and a column.
* **Communities, named**: the 40 largest, each named after its dominant folder and most common files (Graphify's own labels are not useful).
* **Graph viewer (`graph-viewer.html`)**: no longer a copy of Graphify's `graph.html`. It is generated from `scripts/graph_viewer_template.html` (edit that file to change the look). The files, functions and routes are the ones on the Explore page; the links are every file-to-file link in `graph.json`, weighted by how many graph links join the two files, so unlike Explore they are not cut to the top 14. Folders are `backend/eo`, `frontend/app`, `daemon` and so on, with loose top-level files under `root`. Graphify's own `graph.html` is no longer read.
* **Explore "Links out / in"**: for each file, the 14 files it is most linked to, weighted by the number of graph links between them.
* **API "Frontend callers"**: not in the graph. The script scans `MiniMe/frontend` for `/api/...` strings (including ones built from a `const base = ...` and `${...}` expressions) and matches them to route paths by shape. It is inferred, not proven, and ignores the HTTP method, as the page already says. Calls built from fully dynamic strings are missed, so a route can show 0 although the frontend calls it.

## Still manual

Tests, Health, Data model, Tables, Roadmap, Finance, Decisions and the document pages do not come from the census or the graph, so they keep their own "Built ... from commit ..." labels.

## Troubleshooting

| Message | What to do |
|---|---|
| `MiniMe has uncommitted or untracked files` | Commit or stash them in MiniMe (a leftover patch file counts). `graphify-out/` is ignored by MiniMe's git, so it is fine. |
| `The graph was built at X but MiniMe is at Y` | You committed after generating the graph. Run the Copilot prompt again. |
| `graph.json not found` | Run the Copilot prompt; the graph is not committed. |
| `Not replacing data/census.json, the new census is not trustworthy` | Follow the `pip install` line it prints. |
| `git push` rejected | Branch protection or a new remote commit. Run `git pull --rebase`, then `git push`. |

Single steps: `python scripts/refresh_atlas.py --check` and `python scripts/refresh_graph.py --minime ../MiniMe --check` change nothing and exit 1 if a page is out of date.
