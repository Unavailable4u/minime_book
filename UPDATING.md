# Updating the whole Atlas (census + graph + notes + source) in one command

The Atlas has six kinds of generated content:

| From | Refreshed by | Pages |
|---|---|---|
| `data/census.json` (MiniMe's `scripts/codebase_census.py`) | `scripts/refresh_atlas.py` | Overview, Files, Functions, History, Map, Explore, `data/code/routes.json` (API), `data/code/agents.json` (Agents) and `data/code/infra.json` (Infra, a shell drawn by `assets/js/infra.js`), `data/summary.md`, the search index (`data/index/*.json`) |
| The Graphify graph (`MiniMe/graphify-out/`) | `scripts/refresh_graph.py` | Graph and its viewer, Overview graph numbers and hubs, Explore connections, the "callers" half of `data/code/routes.json` (API "Frontend callers"), `data/summary.md` graph line |
| AI-written notes (`MiniMe/graphify-out/atlas-notes/`, written by Copilot: what each file and function is for) | `scripts/notes.py ingest` | `data/notes/` and `data/index/notes.json` (coverage and freshness; read by the Explorer and Coverage pages when they land) |
| MiniMe's source code, as committed at the census commit | `scripts/refresh_source.py` | `data/src/<path>.txt` and `data/src/manifest.json` (the Explorer's Source tab shows the real lines next to the explanations; see "Embedded source" below) |
| MiniMe's `protocol/` folder (the M2C wire contract), `m2c/`, and `docs/decisions/`, as committed at the census commit | `scripts/refresh_protocol.py` | `data/code/protocol.json`: the Protocol, M2C client and Decision records pages (see "Protocol, M2C and decision records" below) |
| The architecture model: structure from the census and `data/code/*.json` (script, never stale), flows written by Copilot into `MiniMe/graphify-out/atlas-arch/`, layout in `content/arch-layout.json` | `scripts/arch.py ingest` | `data/arch/` (`derived.json`, `model.json`, `flows/`, `views/`) and `data/index/arch.json` (per-flow status). Step 2c below |
| The SQL in `data/src/` (migrations and the Supabase dump) plus the census's `table_refs` | `scripts/refresh_schema.py` | `data/code/schema.json`: tables, columns, foreign keys, policies, migrations and "who touches this table" (Data model, a shell drawn by `assets/js/data.js`). Run by `update_all.py` after the source step; falls back to the census, and says so, when the SQL is not embedded |

`scripts/update_all.py` runs all seven, then proves nothing is stale and runs the tests. The notes and the architecture flows are the parts a person has to drive: Copilot writes them in batches (Steps 2b and 2c below), and everything else about them is automatic.

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

## Step 2b: AI-written notes (Copilot, run in batches)

The census gives facts (names, lines, signatures, a hash of each function's code). The **notes** add meaning: what a file is for, what each important function does, and what to watch out for. Copilot writes one JSON file per source file into `MiniMe/graphify-out/atlas-notes/` (ignored by MiniMe's git, so it never makes MiniMe "dirty"). `notes.py` decides which files are worth a note, hands Copilot a batch, checks what comes back, and later tells you which notes went **stale** because the code changed. Only the notes whose code changed are ever rewritten.

Do steps 1-3 first, so the census and the graph describe MiniMe's current commit. Then, in a loop:

```powershell
cd path\to\minime_book
python scripts/notes.py status                                   # how much is covered, by tier
python scripts/notes.py todo --tier 1 --limit 15 --minime ../MiniMe
```

`todo` writes two files into `MiniMe/graphify-out/atlas-notes/`: `_SCHEMA.md` (the exact format and rules) and `_todo.json` (the next batch: files, and for each the symbols that need a note, with their line numbers, hash, signature and the file's blob id). A batch stops at 15 files or 80 symbols, whichever comes first (`--limit`, `--max-symbols`), most-connected files first. Keep batches small: given about 200 symbols at once, Copilot writes a script that fills a template instead of writing each entry, and `validate` flags that as placeholder text. `--tier 2` or `--tier 3` includes the deeper tiers after the earlier ones are done.

Open MiniMe in VS Code, switch Copilot to **Agent** mode and paste prompt **A** (new notes) or **B** (refresh stale ones). `todo` tells you which: its list shows `new`, `changed` or `fix` per file. When Copilot is done:

```powershell
python scripts/notes.py ingest --minime ../MiniMe
python scripts/notes.py status
```

`ingest` checks every note (a malformed one is reported and stops it; add `--skip-invalid` to take the rest), copies the good ones into `data/notes/`, fills in the symbol hashes, and writes `data/index/notes.json`. Run `todo` again for the next batch. When you have done enough for today, run `python scripts/update_all.py` (it ingests too), and publish.

Do not commit in MiniMe between `todo` and `ingest`: the notes record the commit they were written against, and a different commit makes them stale at once (`todo` warns when MiniMe has moved on from the census).

## Step 2c: Architecture flows (Copilot, run per flow)

The architecture model has three parts. The **structure** (which folders exist, who imports whom, which routes and agents there are) is derived by `scripts/arch.py` from the census and `data/code/*.json`: no AI, never stale. The **flows** (the ordered steps of the request path, the task pipeline, the run and workspace lifecycles, the daemon approval path, memory, the M2C protocol) are written by Copilot, one JSON file per flow, into `MiniMe/graphify-out/atlas-arch/`. Every step cites the code it is about (`{path, qual, lines}`); `arch.py` fills in the hashes and later says which steps went **stale** (the cited code changed) or **broken** (it is gone). The **layout** is `content/arch-layout.json` (databases and outside services, pinned positions). Which flows and views exist is `content/arch-flows.json`.

Do steps 1-3 first (and Step 2b if you want notes). Then, in a loop:

```powershell
cd path\to\minime_book
python scripts/arch.py status                       # per flow: missing / fresh / stale / broken / unverified
python scripts/arch.py todo --minime ../MiniMe      # writes _SCHEMA.md and _todo.json into MiniMe/graphify-out/atlas-arch/
```

Open MiniMe in VS Code, switch Copilot to **Agent** mode and paste prompt **C** (flows not written yet) or **D** (refresh the stale steps). `_todo.json` says which. When Copilot is done:

```powershell
python scripts/arch.py validate --minime ../MiniMe      # optional: check without writing
python scripts/arch.py ingest --minime ../MiniMe
python scripts/arch.py status
```

**Seeing it.** `arch-view.html` (System, "System views") draws every view of the model from `data/arch/views/*.json`: `?view=<id>`, plus `&flow=<flow id>` on the unified view, `&level=0|1|2`, `&embed=1&theme=paper|dark`. A flow that is not written yet shows the derived part and says so. `?edit=1` lets you drag boxes on the structure views and **Copy JSON** for `content/arch-layout.json` (only `pins` change). In a chapter, a figure `{"type": "arch", "view": "<id>"}` (optional `"flow"`, `"focus"`) draws the same view inline. The code is `assets/js/arch/` (`render.js`) on `assets/js/svgview.js`; `scripts/test_arch_render.py` tests it, and `scripts/arch_render_fixtures.py` makes miniature flows to look at before the real ones exist.

**The System page.** `architecture.html` shows every view with its flow's steps, freshness and the code each step cites. Nothing there is retyped: after the update loop (`arch.py todo`, prompt D, `update_all.py`) the page shows the new status by itself. The only hand-written text is `content/system/views.json` (a sentence or two per view, the legend, the book sections to read, and the order of the sections); a new view in `content/arch-flows.json` appears on the page without prose until you add some. When a flow lists `doc_conflicts`, the page shows them under its diagram: correct the chapter, not the diagram. `scripts/test_system.py` checks that every chapter section and page named in `views.json` exists.

`ingest` rejects a flow that has an error (add `--skip-invalid` to take the rest): a schema or actor id that is wrong, a step without evidence, a bad `next`, a step id that was renumbered or reused, a secret, or a **symbol that does not exist** in a flow written at the current commit. Warnings (over-long text, a stage the code registers that has no step, a citation of removed code) are printed and do not stop it. Do not commit in MiniMe between `todo` and `ingest`: a flow records the commit it was written at.

**Prompt C: write flows**

```
Write "architecture flows" for the Atlas. Do NOT modify any source file, do not commit.

1. Read graphify-out/atlas-arch/_SCHEMA.md and graphify-out/atlas-arch/_todo.json. Process at most 2 flows from it, in order.
2. For each flow: read the seed files listed in its todo entry, then follow the calls (census.json "calls" and the code itself)
   to trace the REAL execution path. Write graphify-out/atlas-arch/<flow-id>.json (schema version 1).
3. Set "commit" to `git rev-parse HEAD`. Use ONLY actor ids listed in the todo entry's "actors".
4. Every step (or transition) needs >= 1 evidence entry {path, qual, lines}: a real function or class that does what the step says.
   If you cannot point to code for a step, do NOT write it; put it in "unknowns" instead. Leave evidence "hash" as null.
5. Order steps by actual execution order in the code, not by what documents say. If data/docs or a chapter disagrees with the code,
   follow the code and add an entry to "doc_conflicts" naming the chapter section.
6. Mark approval gates (user, daemon, policy, tiers) with kind "gate" and a "gate" object; DB/Redis/file writes are kind "store";
   LLM-provider and network calls are kind "external". Use stable step ids s01, s02, ... in execution order.
7. Text fields are plain English, <= 240 chars. Never include secrets, tokens, or values from .env files.
8. When done, run `python -c "import json,glob;[json.load(open(f)) for f in glob.glob('graphify-out/atlas-arch/*.json')]"`
   and print: flows written, steps written, steps skipped (no evidence) and why.
Do not ask me questions unless something blocks you.
```

**Prompt D: after a code change, refresh only what is stale**

```
Run `git status` and `git log -1 --oneline`; stop if there are uncommitted changes.
Re-read graphify-out/atlas-arch/_todo.json (flows not written, or steps whose evidence changed or disappeared).
Update ONLY the steps/transitions listed there. Keep every other step, its id and its order exactly as they are.
New steps take the next free id (never renumber, never reuse). Remove a step only if the code path no longer exists
(and fix the "next" links of its neighbours). Re-check evidence for each touched step against the current code.
Same rules as prompt C. Update "commit" to the current HEAD. Do not touch source files; do not commit.
```

A few facts are read straight from MiniMe's source with `ast` and never guessed (`scripts/arch_extract.py`: the agent registry, the role-to-module map, the router tiers). They are listed under `extractors` in `content/arch-flows.json`; when one cannot be read, the flow is written entirely by Copilot and the status says so. `arch.py build --check` (what CI runs, no MiniMe needed) proves `data/arch/` matches what the committed inputs produce. If you pin node positions in the System page's edit mode, paste the JSON into `pins` of `content/arch-layout.json`.

**Prompt A: write a batch of new notes**

```
Write "atlas notes" for the next batch of files. Do NOT modify any source file, do not commit or push.

1. Run `git status` and `git log -1 --oneline`. If there are uncommitted changes to tracked files, stop and tell me.
2. Read graphify-out/atlas-notes/_SCHEMA.md (the exact format and rules) and graphify-out/atlas-notes/_todo.json (the batch). Process every entry of "files", in order, and no other file.
3. For each entry: read the WHOLE source file, then write graphify-out/atlas-notes/<note_file> (schema version 1).
4. Copy "path", "tier", "blob" and "commit" from the entry exactly as given. Never compute or guess them. Set "written" to today's date (YYYY-MM-DD).
5. Write one "symbols" entry for EVERY symbol listed in the entry. Use its "qual", "start", "end" and "hash" exactly as given, and add: "summary" (<= 140 characters, what it is FOR), "params" (name + one-line meaning), "returns", "raises", "side_effects" (I/O, database writes, network, LLM calls, file system, subprocess), "confidence" (high, medium or low) and "evidence" (the line ranges you relied on). Do not add symbols that are not listed.
6. If the entry has "write_blocks": true, also write "blocks": 4-10 contiguous line ranges that walk a newcomer through the file in reading order, each with "lines" (like "58-82"), "anchor" (the exact first line of the block, without leading spaces), "title" and 1-3 sentences of "text".
7. Be truthful. Describe only what the code does. If a reason, a caller or a behaviour is not visible in the code, put it in "unknowns" instead of guessing, and use confidence "low" when unsure.
8. Never include secrets, tokens, passwords or values from .env files.
9. Write every entry yourself, from the code you read. Do NOT generate the notes with a script or a template, and do not reuse the same wording across entries. If you cannot say something useful about a parameter or a return value, leave that field out instead of writing a placeholder such as "value used by the symbol".
10. When done, run: python -c "import json,glob;[json.load(open(f,encoding='utf-8')) for f in glob.glob('graphify-out/atlas-notes/*.json')];print('all valid JSON')"
   then print: files written, symbols written, files skipped and why.
Do not ask me questions unless something blocks you.
```

**Prompt B: after a code change, refresh only what is stale**

```
Refresh the stale "atlas notes". Do NOT modify any source file, do not commit or push.

1. Run `git status` and `git log -1 --oneline`. If there are uncommitted changes to tracked files, stop and tell me.
2. Read graphify-out/atlas-notes/_SCHEMA.md and graphify-out/atlas-notes/_todo.json. For each entry of "files", open the existing note graphify-out/atlas-notes/<note_file> and update it in place.
3. Copy "tier", "blob" and "commit" from the entry. Set "written" to today's date.
4. Touch only what the entry lists. For each item in the entry's "symbols": re-read that code, rewrite its entry (summary, params, returns, raises, side_effects, confidence, evidence), and set "qual", "start", "end" and "hash" from the entry; add the entry if it is new. Delete the entries named in "removed". Leave every other symbol exactly as it is.
5. Re-read the note's "summary", "purpose", "how_it_works", "gotchas" and "unknowns" against the changed code, and correct only what is now wrong.
6. If the entry has "write_blocks": true, check every block: its "lines" must still cover the code that starts at its "anchor" line. Fix the line ranges and text, add a block for new code, delete a block whose code is gone.
7. Follow the rules in _SCHEMA.md: be truthful (put what you cannot see in the code into "unknowns"), never include secrets, plain English.
8. Write every changed entry yourself, from the code you read. Do NOT generate it with a script or a template, and never write placeholder text.
9. When done, run: python -c "import json,glob;[json.load(open(f,encoding='utf-8')) for f in glob.glob('graphify-out/atlas-notes/*.json')];print('all valid JSON')"
   then print: files updated, symbols rewritten, symbols removed.
Do not ask me questions unless something blocks you.
```

**How the notes stay honest and cheap**

* **Tiers** (`content/notes-tiers.json`, editable; `python scripts/notes.py tiers` shows the effect, `tiers <path>` explains one file): T1 = full note with a walkthrough of the file (the most-connected files in the graph, route files, the orchestrator core, the code agent, the daemon, the M2C core); T2 = file note plus the larger or public functions; T3 = file note plus public functions (frontend, migrations, scripts); T4 = tests and fixtures, a one-line summary only; T0 = no note (binary files, Markdown, `protocol/v1/*.json`, which the Protocol page will render directly). A function with none of the traits listed for its tier gets no note: the site shows its census facts instead.
* **Freshness** is judged from git objects, never from the working tree (so Windows line endings cannot cause false alarms). A note records the blob id of its file; a different blob means **stale**. Each symbol records the hash of its code: a different hash means that function changed, a missing symbol is **broken**. `ingest` fills hashes from the census, and moves the line numbers of unchanged symbols to where they now are, so a note is not stale just because code above it grew.
* **Errors block, warnings do not.** Blocking: malformed JSON, wrong types, text that looks like a secret, or a symbol that does not exist although the note was written at the census commit (a hallucination). Warnings: unknown keys, over-long text, a symbol that vanished from newer code, a note for a deleted file (`ingest --prune-orphans` removes those).
* Notes are **AI-written** and the site will say so. Copilot is told to put anything it cannot see in the code into `unknowns`, and to cite the lines it relied on; spot-check the first few batches.
* `ingest` never deletes notes by itself. On a machine without MiniMe's `atlas-notes` folder it just rebuilds `data/index/notes.json` from `data/notes/`. A note in MiniMe that is older than the committed copy is skipped.

## What `update_all.py` checks and does

1. MiniMe has no uncommitted or untracked files, and `graphify-out/graph.json` was built at MiniMe's current commit. If not, it stops and tells you which step to redo. This stops the site from mixing two versions of the code.
2. `refresh_atlas.py --census-from <MiniMe>`: new census, then every census-driven page and the search index.
3. `refresh_graph.py --minime <MiniMe>`: every Graphify-driven part.
4. `notes.py ingest --minime <MiniMe>`: validates the notes Copilot wrote, copies them into `data/notes/`, rewrites `data/index/notes.json`. A malformed note stops it; stale or missing notes only show in the coverage numbers.
5. `refresh_source.py --minime <MiniMe>`: copies MiniMe's source into `data/src/` (see "Embedded source"). A file that fails the secret scan is not copied and is printed as `REFUSED`; that never stops the run. Skipped with `--no-embed-source`, or when `content/config.json` has `"embedSource": false`.
6. `refresh_protocol.py --minime <MiniMe>`: rebuilds `data/code/protocol.json` from `protocol/`, `m2c/` and `docs/decisions/` at the census commit (see "Protocol, M2C and decision records"). It stops with a message if MiniMe has no `protocol/v1` at that commit.
7. `refresh_schema.py`, then `arch.py ingest --minime <MiniMe>`: derives the architecture structure and ingests the flows Copilot wrote (Step 2c). A flow with an error stops it; stale or missing flows only show in `arch.py status`. (It runs after the schema step because the derived structure reads `data/code/schema.json`.)
8. Both scripts with `--check` (the first also proves the search index is current), `notes.py ingest --check`, `notes.py validate`, `arch.py ingest --check`, `arch.py validate`, `refresh_source.py --check` and `refresh_protocol.py --check`, then the unit tests, including the index builder, the palette, the chapter reader, the notes pipeline, the architecture model, the source copier and the protocol pages.
9. With `--push`: `git add -A`, commit, `git pull --rebase`, `git push`.

The GitHub Action (`refresh-atlas.yml`) still runs when `data/census.json` is pushed. After this routine it finds nothing to change, so it commits nothing.

## Protocol, M2C and decision records (P24)

Three pages are drawn from one file, `data/code/protocol.json`, written by **`python scripts/refresh_protocol.py --minime ../MiniMe`** (`update_all.py` runs it for you):

* **Protocol** (`protocol.html`): every message type of MiniMe's `protocol/v1` (direction, data class, the envelope's `run_id` / `seq` rules, each field with its type, limits, enum values and default), the seven `run_event` subtypes, the eleven tools with their risk level (`R0` to `R4`, drawn in the amber gate colour, plus `risk_max` where a call can be riskier), the shared enums, and the golden transcripts. Every message has one real example taken from a transcript. A chip says whether the client's copy of the schemas (`m2c/src/m2c/protocol/v1`) is byte for byte the server's.
* **M2C client** (`m2c.html`): the package map of `m2c/src/m2c` (file counts, the first paragraph of each package's own docstring, and an AI note summary only where one exists), the commands table and the status line from `m2c/README.md`. The few hand-written sentences (what the page is for, which chapters belong to it) are in `content/system/m2c.json`.
* **Decision records** (`adrs.html`): the files in `docs/decisions/`: number, title and status (accepted, superseded or see the record). "Read the record" opens the Markdown in the Explorer. A record is not linked to a Golden Rule yet: that waits for stable rule ids on the Decisions page (plan P21).

How it stays true:

* Everything is read **from git at the census commit** (`git ls-tree`, `git cat-file`), never from the working tree, so uncommitted edits and Windows line endings change nothing. The file's `generated` date is the commit's own date, so `--check` compares byte for byte.
* **A field the schema marks `x-m2c-secret` is replaced by a placeholder in the example**, whatever the fixture holds. The fixtures contain credential-shaped placeholders; none of them reaches the site (`test_refresh_protocol.py` checks the published file for it). Long strings in examples are cut at 160 characters and long lists at three items.
* `refresh_protocol.py --check` rebuilds in memory and compares with the file. Without a MiniMe checkout it only proves the file is well formed and at the census commit (that is what CI runs).
* If MiniMe's schema gains a message type, field or tool, the pages change on the next `update_all.py` with no edit here. If the envelope names a type that has no schema file, the script stops and says which.
* Tests: `python scripts/test_refresh_protocol.py` (a throw-away git repository stands in for MiniMe; the JavaScript helpers run under Node). By hand, in a browser: open `protocol.html#m/hello`, `#t/delete_path` and `#e/usage`, press Esc, and look at both themes at 360 px.

## Embedded source and code links (P12)

The Explorer shows an explanation next to the real code, and every symbol has three ways to reach it: **Source** (the in-site viewer, the main path), **GitHub** (a permalink at the census commit, so the lines match what was audited) and **VS Code** (your working copy, opened with a `vscode://` link).

* **`python scripts/refresh_source.py --minime ../MiniMe`** copies every tracked text file of MiniMe at the **census commit** into `data/src/<path>.txt`, and writes `data/src/manifest.json` (path to git blob id, the commit, what was skipped and why). It reads from **git objects** (`git ls-tree`, `git cat-file`), never from the working tree, so Windows line endings and uncommitted edits cannot leak in, and each copy's blob id equals the one in a note. Only changed files are rewritten; files that left the commit are deleted. `--check` changes nothing and exits 1 if `data/src` is out of date; without a MiniMe checkout, `--check` only proves `data/src` matches its own manifest and the census commit (that is what CI runs). `update_all.py` runs it for you.
* **Not copied:** anything in `data/src-denylist.txt` (lockfiles, `*.jsonl` fixtures, MiniMe's committed runtime data under `backend/data/`, `.coverage`, minified files), files over 300 KB, binary or non-UTF-8 files, symlinks, submodules, a real `.env` (not `.env.example`), `*.pem`, `*.key`, `*.p12`, `*.pfx`, and any file that fails the secret scan. The manifest lists each skipped file with its reason, so the Explorer can say why a file has no source. Edit the deny list freely: changing it makes the next run judge every file again.
* **Secret scan:** uses `gitleaks` with MiniMe's own `.gitleaks.toml` when `gitleaks` is on your `PATH`, otherwise a built-in regex check (private-key blocks, AWS, GitHub, Slack and `sk-` keys, JWTs, long `api_key = "..."` assignments). It judges **content**, never file names. A hit in a normal folder **refuses** the file (printed as `REFUSED (not copied): path: rule (line N)`; the secret itself is never printed or stored). A hit under `tests/` or `fixtures/` is only a warning and the file is still copied (`m2c/tests/secret_handling/` holds deliberately fake secrets). A refusal means a secret may be committed in MiniMe: look at that file in MiniMe, not here. `--strict` makes the exit code 1 when anything was refused.
* **`data/src` is committed** (about 19 MB, about 1,150 files, loaded one at a time so no page gets heavier) and `.gitattributes` marks it `-text`, so git never converts its line endings. Vercel serves it as `text/plain`.
* **Turning it off:** `"embedSource": false` in `content/config.json` hides the Source button, and `update_all.py --no-embed-source` skips the copy. The GitHub repo and the default editor are in the same file.
* **VS Code links** need to know where MiniMe lives on *your* machine. Click the link icon in the top bar, type the folder (`E:\python workplace\code\MiniMe`; quotes from "Copy as path" are fine) and choose VS Code or Insiders. It is saved in this browser only. The popover shows the exact URL it will open. Those links open your working copy, so their line numbers can differ from the audited commit if your checkout has moved on; GitHub and Source always match the audited commit.
* The logic for all of this is one module, `assets/js/links.js` (`codeLinks({path, start, end, commit}, opts)`); the Explorer and the chapter code links import it. Tests: `python scripts/test_refresh_source.py` and `python scripts/test_links.py`.

## How the graph-driven numbers are worked out

* **Counts**: nodes, links and communities in `graph.json`.
* **Overview numbers (`data/index/vitals.json`)**: `index.html` is a shell that `assets/js/overview.js` fills from this file, so no script edits the page itself. `refresh_atlas.py` writes the `census` half (KPIs, languages, commits per month, directory-table counts) and `refresh_graph.py` writes the `graph` half (nodes, links, communities, hubs). Each keeps the other's half as it is. The page shows both halves with the commit and day they were measured at, and turns amber when they disagree. The hand-written parts are in `content/overview/`, the directory table in `content/subsystems.json` and the request walk-through in `content/system/request-path.json`; `check_site.py` checks every link and code reference in them.

* **Topology diagram (`content/topology.json`)**: the System-at-a-glance diagram on the Overview (`assets/js/topology.js`, `assets/css/topology.css`). The *layout* is curated by hand in `content/topology.json`: groups, 20 boxes with the real repo folders each stands for, the M2C client that opens into 9 parts, and 13 lines. The *numbers* are never typed: box size is code lines (`data/index/vitals.json` `census.topology`, written by `refresh_atlas.py`) and line width is graph links between folders (`data/graph/folders.json`, written by `refresh_graph.py`). A dashed line is a relationship declared in the layout (HTTP, a WebSocket, the approval gate) because the graph has no links across it; `check_site.py` warns when a solid line has no links (`topology-edge-quiet`) or a box has no numbers (`topology-stale`) and errors on a box outside its group, a folder no census file lives in, or a chapter or diagram that does not exist. `data/graph/folders.json` is seeded from the Graph page's folder table until the first `update_all.py` run replaces it with the full graph; the page says so while it is a seed.
  To move a box: open the page with `?edit=1`, drag the boxes, press **Copy JSON** and paste it over `content/topology.json` (only `x` and `y` change). To add a box: add a node (and its group, folders, text), run `python scripts/refresh_atlas.py`, then `python scripts/check_site.py`. A line that would cross another box needs a `"bend"` (and `"label_t"` moves its label along the line); `scripts/test_topology.py` fails when a line runs through a box.
  By hand, in a browser (the tests cannot): hover, click, Tab, the arrow keys and Escape; Follow one request; Show the M2C parts; zoom; the bottom sheet at 360 px; and both themes.
* **Graph hubs**: the 10 nodes with the most links that belong to a source file (library nodes such as `json` or `os` have no file and are skipped).
* **Folder matrix and "Strongest cross-folder links"**: links counted from the folder of the source node to the folder of the target node, tests excluded. A folder is `backend/eo`, `frontend/app/components` and so on. The 14 busiest folders get a row and a column.
* **Communities, named**: the 40 largest, each named after its dominant folder and most common files (Graphify's own labels are not useful).
* **Graph viewer (`graph-viewer.html`)**: no longer a copy of Graphify's `graph.html`. It is generated from `scripts/graph_viewer_template.html` (edit that file to change the look). The files, functions and routes are the ones on the Explore page; the links are every file-to-file link in `graph.json`, weighted by how many graph links join the two files, so unlike Explore they are not cut to the top 14. Folders are `backend/eo`, `frontend/app`, `daemon` and so on, with loose top-level files under `root`. Graphify's own `graph.html` is no longer read.
* **Explore "Links out / in"**: for each file, the 14 files it is most linked to, weighted by the number of graph links between them.
* **API "Frontend callers"** (`data/code/routes.json`, drawn by `api.html`): not in the graph. The script scans `MiniMe/frontend` for `/api/...` strings (including ones built from a `const base = ...` and `${...}` expressions) and matches them to route paths by shape: that decides *which* file calls *which* route. Each link also carries `via`, how well it is backed, found by a second reading of the same file (a port of MiniMe's `scripts/graphify_api_links.py`): `method` = best path match and the code names this route's HTTP method; `score` = best path match, no method named; `shape` = only the path shape matched (the HTTP method is ignored, a weaker guess). Everything is inferred, not proven, and the page says so. Calls built from fully dynamic strings are missed, so a route can show 0 although the frontend calls it. `refresh_atlas.py` writes the census half of that file (handlers, deps, response model, router) and keeps the callers; `refresh_graph.py` writes the callers and keeps the census half.
* **Why two scanners were merged, not one deleted (P17):** on MiniMe `3727ae3`, the book's scan found 215 file-to-route links (143 routes, 41 frontend files). `graphify_api_links.py` found 179 (142 routes, 31 files, but it also reads test files). The book's set is the larger one, so it stays the source of the links and the old counts stay identical. The 12 links only MiniMe's script found are mixed: some are comments or prose that mention a path, and some are real calls whose URL ends in a variable such as `${qs}` that the book's scan misses. They are not added, so the page shows what it showed before; if you want them, make `api_literals` drop a trailing `${qs}` and re-run the golden test (`python scripts/test_codepages.py`).

## Chapter code links and "Discussed in the book" (P15)

Identifiers in the chapters link to the code, and the code links back. Nothing in the chapters is edited: `scripts/build_index.py` reads every `<code>` span of every `doc-*.html` and decides what it names.

* **In a chapter,** a `<code>` span that names a file, a folder, a function or a class gets a dotted underline. Hover or focus shows a card (what it is, signature, the AI note's summary, freshness, **Open in Explorer / Source / GitHub / VS Code**); click goes to the Explorer. A name that exists in several places (`GrowthTab`, `.env.example`) is a dashed underline that opens a chooser. Only `<code>` is linked: never plain prose, never a `<pre>` block, never text already inside a link.
* **In the Explorer,** a file or symbol page lists the chapter sections that mention it under **Discussed in the book**.
* **The rules,** first match wins: an alias from `content/link-aliases.json`; an exact path (optionally `:12`, `:12-20`, `#L12-L20`) or folder; a unique path ending (`tui/app.py`); `path::qualified.name`; a unique class or function name, or `Class.method`. If several share a name, the ones outside test files win when exactly one remains, otherwise the one in a file the same section already named, otherwise the reader chooses. Names shorter than four characters, dunder names and common words (`state`, `config`, `agent` ...) are never linked.
* **Output** (all under `data/index/`, rebuilt by `build_index.py`, which `refresh_atlas.py` and `update_all.py` already run): `linkables.json` (what the browser may link), `mentions.json` (the backlinks) and `link-report.json` (per chapter: how many spans, how many linked, ambiguous, unresolved, and the most common unresolved texts). `build_index.py` prints the overall percentage; most of the unresolved text is not code at all (file names of other repositories, environment variables, shell commands).
* **Fixing a miss:** look at `unresolved` in `link-report.json`. When a phrase should point at code, add it to `content/link-aliases.json`: `{"aliases": {"the stage router": "backend/eo/router.py"}}` (keys are case-insensitive; a target may be a file, `path::name`, `path::name@10-40` or `folder/`). A target that is not in the census is reported as a warning and not linked, so a renamed file never leaves a dead link.
* **Code:** the build half is `scripts/chapter_links.py`; the browser half is `assets/js/codelink.js` (loaded by `shell.js` on chapter pages, after the reader and the figures) with `assets/css/codelink.css`; the backlinks panel is `assets/js/explorer/backlinks.js`. Tests: `python scripts/test_chapter_links.py` (rules, build wiring, and every link and mention in the committed index against the census) and `python scripts/test_explorer.py` (`codelink.mjs`: targets, the card, a chapter page in jsdom).

## Audit marks (P16)

Audit marks are the reader's own data, not generated data: nothing in `update_all.py` writes them, and a refresh never deletes them.

* **After a refresh,** a mark of a *reviewed* symbol whose census `hash` changed shows "needs re-review" the next time its file is opened (or all at once with **Check against the census** on `explorer.html#/audit`). A mark whose symbol or file has left the census is listed as "no longer in the census"; clear it or keep it.
* **Where they are:** `localStorage` key `minime_audit_v1` in each browser (move them with Export / Import on the audit page), or, if someone switches **Share marks with the team** on, in the To-do store (`api/todo.js`, record kind `audit`, one record per symbol, id = hash of `path::qual`). Records stay in the shared store like every other kind (deletes are tombstones, and the daily snapshots include them). Every poll of the To-do pages downloads the whole store, so a very large number of shared marks makes those pages heavier; export and clear if that ever matters.
* **Tests:** `python scripts/test_todo_api.py` proves the API accepts `audit` and nothing else new; `python scripts/test_explorer.py` covers the rules and the pages.

## The search index

`data/index/` feeds the command palette (Ctrl/Cmd+K). `scripts/build_index.py` writes it from `content/nav.json` (pages), the `h2`/`h3` headings of every chapter, the glossary and `data/census.json` (files, routes, functions). It is deterministic: same inputs, same bytes. `refresh_atlas.py` rebuilds it with the pages, so `update_all.py` and the GitHub Action keep it current. It also writes `data/index/book.json`, the library page's data (chapter descriptions, word, section and table counts and last-built date, read from each chapter's banner). Three things change it without the census changing: editing `content/nav.json`, editing a chapter (a new chapter build changes its counts) and editing `content/glossary.json` (the palette's `#` search lists its terms). After any of them, run:

```
python scripts/build_index.py          # rewrite what changed
python scripts/build_index.py --check  # change nothing; exit 1 if the index is stale
```

## Still manual

Tests, Health, Data model, Tables, Roadmap, Finance, Decisions and the document pages do not come from the census or the graph, so they keep their own "Built ... from commit ..." labels.

## Troubleshooting

| Message | What to do |
|---|---|
| `MiniMe has uncommitted or untracked files` | Commit or stash them in MiniMe (a leftover patch file counts). `graphify-out/` is ignored by MiniMe's git, so it is fine. |
| `The graph was built at X but MiniMe is at Y` | You committed after generating the graph. Run the Copilot prompt again. |
| `graph.json not found` | Run the Copilot prompt; the graph is not committed. |
| `Not replacing data/census.json, the new census is not trustworthy` | Follow the `pip install` line it prints. |
| `search index is stale` / `missing: data/index/...` | Run `python scripts/build_index.py` (you edited `nav.json`, a chapter or the glossary). |
| `glossary-bad-see` / `path-bad-target` from `check_site.py` | A glossary term or reading-path step points at a chapter, heading id, file or symbol that is gone (a chapter was rebuilt, or MiniMe moved a file). `python scripts/list_headings.py <chapter>` lists the current heading ids; fix the target in `content/glossary.json` or `content/reading-paths.json`. |
| `note file(s) are malformed, nothing was ingested` | `ingest` printed which file and why. Fix or delete that file in `MiniMe/graphify-out/atlas-notes/` (or run Prompt A/B again for it), or use `--skip-invalid`. |
| `error: ... symbol X: not in the census` | Copilot invented a function name (or used a `qual` that was not in `_todo.json`). Fix the note or have Copilot redo that file. |
| `MiniMe is at X but the census is from Y` (from `notes.py todo`) | MiniMe moved on after the census. Run `python scripts/update_all.py` first, so lines, hashes and blob ids match what Copilot will read. |
| `arch: ... cites X, which is not in the census` / a flow is rejected | Copilot cited a function that does not exist at the flow's commit. `arch.py validate --minime ../MiniMe` names the step; fix it by hand or run Prompt C/D again for that flow. |
| `git push` rejected | Branch protection or a new remote commit. Run `git pull --rebase`, then `git push`. |
| `REFUSED (not copied): path: ...` from `refresh_source.py` | The secret scan found something that looks like a credential in a MiniMe file outside `tests/`, so that file is not in `data/src`. Check it in MiniMe; if it is a false positive, add an allow-list rule to MiniMe's `.gitleaks.toml` (the scan reads it when `gitleaks` is installed) or fix the pattern. |
| `protocol: data/code/protocol.json is out of date` | Run `python scripts/refresh_protocol.py --minime ../MiniMe` (or `update_all.py`). In CI this means `data/code/protocol.json` was not committed together with the census it belongs to. |
| `source: data/src is out of date` | Run `python scripts/refresh_source.py --minime ../MiniMe` (or `update_all.py`). In CI this means `data/src` was not committed together with the census it belongs to. |
| `MiniMe has no commit abc1234 (the census commit)` | Your MiniMe checkout does not contain the commit the census was built from. `git fetch` in MiniMe, or refresh the census from this checkout. |
| The VS Code button is missing | Set your MiniMe folder with the link icon in the top bar. |

Single steps: `python scripts/build_index.py --check`, `python scripts/refresh_atlas.py --check`, `python scripts/refresh_graph.py --minime ../MiniMe --check` `python scripts/notes.py ingest --minime ../MiniMe --check` and `python scripts/arch.py ingest --minime ../MiniMe --check` change nothing and exit 1 if something is out of date.
