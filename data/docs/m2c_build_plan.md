# M2C L26 — Build Execution Guide

*Minime to Code · Level 26 (L26). Levels work like release versions: the next release will be L27.*
### From the first patch to release: ordered, parallelizable, patch-sized work packages

*Version 1.2 (2026-11-14; revision of the 1.1 Synchronized Edition) · Companion to `m2c_feature_guide.md` (canonical 16-section feature & product specification), `guides/M2C___Product___Build_Guide.html` (initial design note), `minime_technical_roadmap.md` (Tech-A/B shared ledger sequence), and `MiniMe_Financial_Strategy_Rulebook.md` (shared plan caps). Planned execution window on the Master Timeline: **Jan – Feb 2027** (64 work packages, 12 waves, 157 effort points). Where this guide and the initial HTML product guide disagree, **this guide and `m2c_feature_guide.md` win** (see §1 Overrides O1–O8).*

> **Revision 1.2 (2026-11-14): status snapshot, outside-reference rule and six new work packages.** §0.6 records what the MiniMe code actually contains (Waves 1–8 built, Wave 9 partly built) and where this plan and the code disagree. D13–D18 add the outside-reference rule, the dependency policy, the hook contract, the "always allow" rule, "sandbox is not approval" and where MCP runs; §11.7 records what was learned from the public Claude Code changelog. **New work packages:** **C25** (safe "always allow"), **Q07** (bypass regression corpus), **Q08** (docs and catalog drift check) and **Q09** (crash and resume integrity) in Phase 3; **C28** (streaming headless output, for Menux delegation) in Phase 4; **C27** (managed settings and presets) in Phase 5. Notes were added to C11, C13, C14, C15, C17, L01, L02, L03, C19 and C23. §16 is the restart order. **Counts:** Phases 0–4 are now 69 work packages and about 163 points (the earlier 64 and 157 excluded the six read-only audits; this adds 5 WPs and 6 points); Phase 5 is 7 work packages and about 26 points (was 6 and 24). The four WPs the build added (C24, C26, S14, S15) are done and are not counted.

---

## 0. How to use this guide with your patch workflow

### 0.1 Inputs for every patch you generate

Give the patch-writing model, every time:

1. **This guide**, pointing at one work package (WP) by ID, for example "implement WP S03".
2. **`m2c_guide.md`** (the product spec). Each WP lists the sections it implements.
3. **The repo** at the commit you want to patch against.
4. **Your patch conventions.** Your repo keeps patches as files at the repo root (`W6_2_console_bridge.patch` and so on), and your code uses long explanatory docstrings, "Patch B5"-style notes and fail-open helpers. New patches should follow that style. **[P]** Name them `MK_<id>_<slug>.patch`, for example `MK_B03_remove_python_run.patch`, and keep new ones in a `patches/` folder so the root stops growing.

### 0.2 Rules for one patch

- **One WP = one patch.** Never merge two WPs unless the WP says "may be combined".
- **Touch only the files the WP lists** (plus tests). If it needs another file, stop and say so; do not widen scope.
- **Every patch ships its tests** and the exact commands to run them (§12).
- **The patch must pass `git apply --check`** on the base commit you name, and the model must run the test suites before and after on a copy.
- **Define "done" first.** Each WP has a "Done when" list; the patch description must tick each item.
- **No new dependency** unless the WP lists it.
- **Fail-open vs fail-closed:** metering and telemetry helpers fail open (never break a user request); **security checks fail closed** (policy engine, device auth, path guard).

### 0.3 Prompt template (copy, fill the brackets)

```
You are generating ONE patch for the MiniMe repo at commit [SHA].
Work package: [ID — title] from m2c_build_plan.md.
Read: that WP, §1 (Overrides) and §[cross-cutting section] of m2c_build_plan.md,
and sections [..] of m2c_guide.md.
Constraints: touch only [files]; follow existing code style and docstring conventions;
no new dependencies unless the WP lists them; security checks fail closed.
Process: (1) read the files and list what you found, (2) write the tests first,
(3) implement, (4) run [test commands] before and after, (5) output a single
unified diff named MK_[ID]_[slug].patch that applies with `git apply` on [SHA].
In the description list each "Done when" item with evidence. If something in the WP
is wrong or impossible against the real code, STOP and report instead of improvising.
```

### 0.4 Running patches in parallel (git worktrees)

1. Pick a **base commit** (`main` at the start of a wave).
2. For each WP in the wave: `git worktree add ../wp-B03 -b mk/B03 <base>`; generate and test the patch there.
3. WPs in the same wave **must not share files** (see the conflict map, §3.4). If the model says it needs a file owned by another WP in the wave, move that WP to the next wave.
4. Apply patches to `main` **in the order listed in the wave table**, one at a time, running the test suites after each. If a later patch fails to apply, **regenerate it against the new `main`** (do not hand-edit hunks).
5. Record every applied patch in `PATCHES.md` (ID, date, commit, result). That log is also your resume point if a session is cut off.

### 0.5 Size labels

**S** (about one focused session) · **M** (a few sessions) · **L** (a week-ish of patch rounds) · **XL** (break it up if the model struggles). Sizes are relative effort, not dates.

### 0.6 Build status snapshot (2026-11-14)

Added in revision 1.2. **How this was established:** from the `m2c/`, `backend/codeagent/`, `backend/eo/`, `backend/api/` and `protocol/` trees of the MiniMe repo, the "Patch XNN" headers inside the code, the test folders, `.github/workflows/ci.yml`, and the commit log (latest commit "wave 9 part 2 complete", 2026-11-14). **The tests were not run.** The plan's own resume log (`PATCHES.md`, §0.4) is not in the repository, so correct any row that is wrong and then create that log from this table.

Status words: **Built** = code and tests are present; **Partly** = some of the WP is present; **Not found** = no code found; **Not checked** = could not be told from the files.

| WP | Status | Evidence |
|---|---|---|
| B01, B03, B04, B06, B07, B09 | Built | One commit named for each in the history |
| B00, B02, B05, B08, B10–B12, AUD1–6 | Not checked | Not looked at in this review |
| P00 | Built | `protocol/v1/` (envelope, 11 tool schemas, errors) and its fixtures |
| S01, S02 | Built (not checked in depth) | `backend/eo/usage_ledger.py`, `credits.py`, migration `0012` |
| S03, X01 | Built | `backend/eo/devices.py`, `backend/api/routes/devices.py`, migration `0013`, `DevicesPanel.jsx` |
| S04, S05, S06, S09 | Built | `backend/codeagent/ws.py`, `adapters/openai_compat.py`, `run_manager.py`, `buffer.py`, `broker.py`, migration `0014` |
| S07, S08, S10 | Built | `loop.py` (with S07b, leaving plan mode), `context.py` (mechanical compaction), `metering.py` |
| C01–C04 | Built | `m2c/` package, store, `m2c login`/`logout`, device link (`link/`) |
| C05, C06, C07, C08, C12 | Built | `tools/`, `policy/`, `tools/shell.py`, `checkpoints.py`, `context/` |
| C09 (with C09a, C09b), C10 (with C10b) | Built | `tui/`, `headless.py`, `session_setup.py` |
| I01 | Built | Walking skeleton |
| I02 | Not checked | Phase 3 work has started, so it presumably passed, but no record was found |
| C11 (as C11a and C11b) | Built | `sandbox/` (bubblewrap profile, probe, CONNECT proxy, network bridge) |
| C15 | Built | `secrets/redact.py`, `secrets/env.py` |
| L01 | Partly | `ask_user` and `tasks` built (L01a); `plan_exit` is in the protocol and the loop (S07b) |
| L03 | Partly | Only the mechanical compaction of S08; model-written summaries, compact instructions and the scratchpad are not built |
| Q01 | Partly | `m2c-test` job in `ci.yml`; whether it covers `codeagent` tests and the protocol check was not checked |
| Q06 | Partly | A canary harness exists in `backend/tests/canary/`; whether it covers M2C runs was not checked |
| S11 | Not checked | Redis is used by `buffer.py`, `connections.py` and `emitter.py`; the process split is not visible |
| C13, C14 | Not found | `trust/fingerprint.py` already reserves `.m2c/hooks`, `.m2c/skills`, `.agents/skills`, `.claude/skills` |
| C16, C17, L02, L04, Q02, Q03 | Not found | `backend/evals/promptfoo/` belongs to the web app, not to M2C |
| Phase 4, 5 and 6 WPs | Not found | No `projects/`, ACP, MCP, worktree or packaging code in `m2c/` |
| **Added during the build** | Built | **C24** device tool runner (`runner.py`), **C26** folder-trust prompt and `m2c trust` (`trust/`), **S14** message router and emitter, **S15** switch of the server to the real loop (`wiring.py`). Sub-patches C09a/b, C10b, C11a/b, S07b and L01a are splits of WPs above |

**Where the plan and the code disagree (found while building this table):**

- The client is **not** standard-library only. Its runtime dependencies are `websockets` (only `m2c/link` imports it), and `prompt_toolkit` and `rich` (only `m2c/tui/app.py` imports them); a test fails if another is added. See D14.
- `m2c/README.md` still says the client can only do `doctor`, `login` and `logout`. It also has the chat UI, `-p`, `trust`, checkpoints, the sandbox and the policy engine.
- Permission modes in the code are `plan`, `ask` and `accept-edits`; the feature guide's `ask|edit|auto` was an earlier idea. `auto` waits for L07.
- The tool catalog in the code is the 11 tools of `protocol/v1/tools/` (`read_file`, `list_dir`, `glob`, `grep`, `edit_file`, `write_file`, `delete_path`, `bash`, `plan_exit`, `ask_user`, `tasks`). The feature guide's older table named tools that do not exist.
- The server routes are `/v1/code/*` (as §3.5 says), not `/api/codeagent/*`.
- `minicore/` does not exist yet. M2C is self-contained; Menux's `MT-K01` extracts the shared library from it after M2C reaches M2.
- Menux's feature guide called the delegation interface `m2c run --json`. The real interface is `m2c -p "task" --output-format json`.

---

## 1. Overrides: what changed since the product guide

These come from your latest requirements (local-first trust, one shared account and cap, Linux/WSL2). **They supersede the product guide where they conflict.**

### O1. Data placement (local-first)

*Supersedes product guide §5.2, §11.9 (replay), §13.3 (data model), §15.3.*

| Where | What lives there | Notes |
|---|---|---|
| **User's device (source of truth)** | Project files; session transcripts and event log; approvals; checkpoints; memory; skills; hooks; settings; tool outputs; audit log; device credential | SQLite `~/.m2c/state.db` plus plain files under `~/.m2c/` |
| **Server, persistent, content-free** | Account; device registry (credential hash only); **usage ledger** (user, surface, model, token counts, credits, timestamps, opaque run ID); plan and quota; minimal error counters | **No prompts, code, file paths, or tool outputs.** |
| **Server, ephemeral content** | The in-flight conversation for an **active** run, so the loop can call the model and keep prompt-cache prefixes stable | Encrypted in Redis, TTL (idle 2 h, hard cap 24 h), deleted when the run ends; never written to Postgres or logs |
| **Third parties** | Model providers receive prompt content per request | Use providers and terms with no-training and shortest retention available; list as sub-processors (your rulebook already requires this) |

Consequences:
- The **device log is the truth.** If the server buffer expires or a worker dies, the client re-sends the needed history (`run.resume` with state) and the run continues.
- **No web replay of past M2C runs** by default. The browser can show a **live** run through a non-stored relay. A later opt-in "sync my history to my account" may be added; it is **off** by default.
- **Honest trust claim (use this wording, not "your data never leaves your device"):** *"Your files, history and settings are stored on your device. When you ask M2C to work, the relevant code is sent to our servers and our model providers to generate the answer; we don't keep it after the run ends."* A claim of "never leaves" would be false because the model runs remotely.
- Add a **canary test** in CI that proves no content reaches Postgres or logs (WP Q06).

### O2. One account, one cap, one ledger

*Supersedes product guide §14.4 recommendation of a separate M2C pool.*

- The same **account and plan** covers the web app, M2C, and later Menux. Usage from all surfaces burns **one pool**; the user pays once.
- Enforcement is **server-side** at every model call (pre-flight check, post-call commit). The device cannot be trusted to count.
- **Your repo has no plan or per-user usage tables today** (existing counters are Upstash daily counters keyed by provider key, and `llm_call_log` has no user column). WP S01 builds the shared ledger and also meters the **existing web app**, not only M2C.
- **Unit:** one pool measured in **credits** (cost-weighted), shown to the user as "about N sessions left". Keep it one pool; make it cost-weighted so that agent loops (which re-read cached context every step) do not drain the pool unrealistically. Show usage per surface in the UI for transparency.
- A per-run ceiling still applies on each surface.

### O3. Platforms

Linux and **WSL2** only for v1. Native Windows: not supported. WSL1: not supported. macOS: deferred (the Seatbelt backend moves to a later phase). Projects must live in the Linux filesystem (for example `~/code/...`), not under `/mnt/c` (slow, permission quirks; `doctor` warns and the sandbox may refuse).

### O4. Client implementation and packaging

- **Python client**, a new top-level package `m2c/` (reuses your daemon's `path_guard`, tool and connection code). Not Rust or TypeScript for v1.
- Distribution: published package installed with `uv tool install m2c` (or `pipx`), plus an `install.sh` that installs `uv`, checks `ripgrep`, `git` and `bubblewrap`, and runs `m2c doctor`. A bundled binary can come later.
- The existing `daemon/` stays untouched until M2C has parity; its preview proxy migrates in Phase 5.

### O5. Backend package name

The product guide proposed `backend/m2c/`. **Use `backend/codeagent/` instead** to avoid an import-name clash with the top-level `m2c/` client package when both are in one dev environment.

### O6. Browser slimming (decided)

Browser keeps: editor, explorer, AI proposals and review, history, Problems, Console (preview), HTML/React preview, Dev server URL preview, ZIP download, planning tabs. Browser **removes**: the Run option for files in the preview panel, the Terminal panel, and Local folder mode. **Pyodide stays** only for chat artifacts. Backend `local_workspace` routes and `daemon/` stay until Phase 5.

### O7. Account required, no offline mode

The brain is server-side, so M2C needs a signed-in account and a connection. Say so in the install docs.

### O8. Profile field

Every run carries `profile: "code"`. Menux will add other profiles on the same engine; do not hard-code "coding" assumptions into the run manager.

---

## 2. Decisions to lock before the first patch

Recommended defaults are in bold. Change them before generating patches, not after.

| # | Decision | Default | If you choose otherwise |
|---|---|---|---|
| D1 | Client language | **Python ≥ 3.11** | Rewriting later is costly; decide now |
| D2 | TUI library | **`prompt_toolkit` + `rich`** (scrollback-friendly, simple streaming) | `textual` is heavier; keep the UI behind an interface so it can be swapped |
| D3 | First model adapter | **OpenAI-compatible chat completions with tools**, pointed at whichever dev provider passes a 20-call tool-calling smoke test (Groq, Mistral and similar are OpenAI-compatible) | Anthropic adapter second, Gemini third |
| D4 | Where the server runs at first | **Mounted in the existing FastAPI app** (`/v1/code/*`); separate process in WP S11 | Separate service from day one costs more setup |
| D5 | Credit definition | **1 credit = a fixed USD amount (config constant), cached reads at provider price** | Pick the constant when you set plans; ledger stores both credits and USD |
| D6 | Ephemeral buffer TTL | **idle 2 h, hard cap 24 h** | Shorter is safer, longer helps resume |
| D7 | Package and command name | **`m2c`** | Check availability on PyPI and your domain first (not checked) |
| D8 | Download host | Your domain (`install.sh`) + PyPI | Needed before WP C22 |
| D9 | macOS | **Deferred** | Adds a Seatbelt backend later |
| D10 | Linux distros supported | **Ubuntu 22.04+/24.04, Debian 12, Fedora current; Arch best effort; WSL2 Ubuntu is the primary Windows path** | Document tested versions in `doctor` |
| D11 | Open-sourcing the client | **Decide before beta** (trust benefit vs. exposing policy code) | Affects license headers from the start |
| D12 | MiniLocker (`draft` repo) reuse | **A source of parts, not a base.** Copy a module in with a provenance header and its tests; no runtime dependency on the repo; never import its Docker sandbox, egress proxy, API or UI (§11.6) | Vendoring or a shared package couples release cadence and drags Docker, FastAPI and S3 dependencies into the client. Check the hackathon's terms before the first copy |
| D13 | Outside reference policy | **Learn from public documentation, public changelogs, observable behavior and permissively licensed code whose licence has been read. Never use leaked, unlicensed or source-unavailable code, including copies re-uploaded under another licence, and never write a close rewrite from it.** If such code is seen by accident, stop, do not copy from it, and tell the owner | Protects the product's right to ship; see §11.7 |
| D14 | Client runtime dependencies | **Standard library plus three recorded exceptions:** `websockets` (only `m2c/link`), `prompt_toolkit` and `rich` (only `m2c/tui/app.py`, imported lazily). A test fails if another appears; adding one needs a decision here | The code already works this way; the README said otherwise |
| D15 | Hook contract | **Command hooks; the event as JSON on stdin; exit 0 means "no objection" (the normal policy still decides), exit 2 blocks with a message to the model, other codes warn. A hook can tighten (ask, deny) and never loosen: a hook's "allow" does not override deny rules, protected paths, the taint floor, the sandbox or the folder-trust rule.** Project hooks run only in a trusted folder; the model cannot edit hook or settings paths | Same direction as Menux MX8 |
| D16 | "Always allow" | **A saved rule is offered only if the same call, checked again against the new rule set, would be allowed; it is never broader than what the person approved; deny and ask rules also apply to an approval that arrives after a reconnect or restart.** Headless runs use explicit rules only | `C25`; avoids rules that quietly stop working or quietly allow more |
| D17 | Sandbox is not approval | **A command that runs in the sandbox still follows the normal permission flow. Skipping the prompt for sandboxed shell commands is an opt-in setting, off by default, and refused when the sandbox probe fails** | Matches C11 ("refuse auto-allow when the sandbox cannot be built") |
| D18 | Where MCP runs | **On the device only (C23).** `backend/eo/mcp_client.py` is a protocol reference for the connect, discover and call code, not a runtime dependency: the server never calls third-party MCP servers for an M2C run. MCP tool descriptions and results are untrusted data and taint the session | Data stays local (O1) |

---

## 3. The map

### 3.1 Phases and milestones

| Phase | Goal | Ends with | Product milestone |
|---|---|---|---|
| **0** | Build-tab fixes and browser slimming | Clean, tested browser editor; CI green | – |
| **1** | Contract and walking skeleton | `m2c login` → connect → send "hello" → streamed model reply → ledger row, shown in the web app | – |
| **2** | Core agent | Edit real files with approvals, checkpoints, rewind, TUI, headless | **M0 internal** |
| **3** | Safety and workflows | Sandbox, hooks, skills, secrets, taint, subagents, compaction, eval harness, red-team suite | **M1 safe daily driver** |
| **4** | Platform integration and beta | Handoff, remote view, review commands, plan chains, invite system | **M2 invite-only beta** |
| **5** | Editors, scale, hardening | ACP, worktrees, classifier, LSP, MCP, process split, external audit | **M3** |
| **6** | Release | Packaging, docs, legal, support | **GA** |

### 3.2 Tracks (letters in WP IDs)

| Track | Scope | Mostly touches |
|---|---|---|
| **B** | Build-tab fixes, browser slimming | `frontend/`, `backend/eo/`, `backend/api/` (existing code) |
| **AUD** | Read-only audits of unaudited browser areas | docs only |
| **P** | Protocol and contract | `protocol/` (new) |
| **S** | Server: ledger, devices, socket, adapter, runs, loop | `backend/codeagent/` (new), `backend/eo/` (few hooks), `backend/migrations/` |
| **C** | Client application | `m2c/` (new) |
| **L** | Loop and agent features (spans server and client) | both |
| **X** | Web app features for M2C (devices, usage, banner, remote view) | `frontend/` |
| **Q** | Quality: CI, evals, red team, canary tests | `backend/evals/`, `m2c/tests/`, `.github/` |
| **I** | Integration patches (join points) | small, across tracks |

### 3.3 Dependency graph (arrows mean "must be applied first")

```
PHASE 0   B01 B02 B03 B04 B06 B07 B09 AUD1-6   (all independent)
          B04→B05      B02→B08,B11,B12      B06+B09→B10

PHASE 1   P00 ──┬──► S04 ──► S06 ─────────┐
                ├──► S05 ─────────────────┤
                └──► C04(needs S04 contract)               
          S01 ──► S02                       ├──► I01 (hello run)
          S03 ──► S04, X01, C03 ────────────┤
          C01 ──► C02, C03, C04 ────────────┘

PHASE 2   S05+S06 ──► S07 ──► S10
          S04+S06 ──► S09(tool broker) ──► S07
          S07 ──► S08
          C02 ──► C08 (checkpoints)        C06 ──► C07 (shell)
          C05, C06, C07, C08, C12 ──► C09 (TUI) ──► I02 (first real task, M0)
          C04 ──► C10 (headless)

PHASE 3   C07 ──► C11 (sandbox) ──► C16, C17(taint)
          C06 ──► C13 (hooks) , C14 (skills), C15 (secrets)
          S07 ──► L01, L02, L03, L04      S06 ──► S11
          Q01, Q02, Q03, Q06 (any time after M0)  ──► I03 (M1)
          (rev 1.2)  C06+C09 ──► C25      C06+C11+C25 ──► Q07 ──► Q03      Q08 (independent)      C02+C08+C09 ──► Q09

PHASE 4   C02 ──► C20 ──► X03      S06 ──► X04      S01 ──► X02
          L02 ──► L05 (review)      S07 ──► L06 (chains)     C11 ──► C21 (doctor full)
          Q04, S12 (invites/billing hooks) ──► I04 (M2)
          (rev 1.2)  C10+L01 ──► C28 (streaming output for delegation)

PHASE 5   C18 (ACP), C19 (worktrees), L07 (classifier), L08 (LSP/repo map),
          C23 (local MCP), S13 (migrate preview proxy), C27 (managed settings), external audit

PHASE 6   C22 (packaging), X05 (docs), X06 (legal) ──► GA
```

### 3.4 Conflict map: files that more than one WP touches

Patches that touch the same file **cannot be in the same wave**; apply in the order shown.

| File(s) | WPs in order |
|---|---|
| `frontend/app/components/tabs/BuildTab.jsx` | B04 → B05 |
| `frontend/app/lib/workbench/fileProviders.js` | B06 → B10 |
| `frontend/app/components/workbench/EditorWorkbench.jsx` | B09 → B10 |
| `frontend/app/components/workbench/PreviewPane.jsx` | B03 → B10 (B10 only trims daemon-source wiring) |
| `frontend/package.json`, `package-lock.json` | B02 → B11 → B12 (anything that changes npm dependencies joins this queue) |
| `frontend/public/workers/pyodideWorker.js`, `app/hooks/usePyodideWorker.js` | B02 → B08 → B12 |
| `backend/utils/llm_client.py` | **S01 only** (S05 must not edit it; it builds a new module) |
| `backend/api/task_runner.py` | S01 only |
| `backend/api/server.py` | B07 (CORS line) and S04 (one `include_router` line). Different hunks; low risk. If `git apply` fails, regenerate the later one |
| `backend/migrations/` | Numbers are **reserved** (§3.5) so parallel patches never collide |
| `protocol/v1/*` | P00 creates it; later edits are versioned additions only |
| `m2c/src/m2c/policy/{decide,rules}.py` | C06 → L01a (built) → C25 → C13 (adds the hook call point) → L07 → C27. One writer at a time |
| `m2c/src/m2c/headless.py`, `cli.py` | C10b (built) → C26 (built) → C28 |
| `m2c/README.md` | Any WP that adds a command, flag or dependency updates it in the same patch; Q08 checks it |

### 3.5 Reserved numbers

| Item | Number |
|---|---|
| Migration: plans and usage ledger | **0012** (S01) |
| Migration: devices | **0013** (S03) |
| Migration: M2C run metadata (content-free) | **0014** (S06) |
| Migration: project checkouts | **0015** (X03) |
| Migration: beta allowlist / feature flags | **0016** (S12) |
| Protocol version | **1** (`protocol/v1`) |
| Server routes | `/v1/code/*` (device and run API), `/api/devices`, `/api/usage` |

### 3.6 Execution waves (what to generate in parallel)

Within a wave, patches are independent. Apply in the order listed.

| Wave | Patches (parallel) | Needs |
|---|---|---|
| **1** | B01, B02, B03, B04, B06, B07, B09, P00, S01, S03, C01, AUD1–AUD6 | Nothing |
| **2** | B05, B08, B10\*, B11, S02, S04, S05, C02, C03, X01 | B04; B02; B06+B09; B02; S01; P00+S03; P00; C01; C01+S03; S03 |
| **3** | S06, C04, B12, X02 | S04; C01+P00+S04; B02+B08+B11; S01 |
| **4** | I01 (walking skeleton) | S01, S04, S05, S06, C03, C04, X01 |
| **5** | S09, C05, C06, C12, C10 | S04+S06+P00; C01+P00; C01; C01; C04 |
| **6** | S07, C07, C08 | S05+S06+S09; C06; C02+C05 |
| **7** | S08, S10, C09 | S07; S01+S07; C05–C08, C12 |
| **8** | I02 (M0) | All of Phase 2 |
| **9** | C11, C13, C14, C15, L01, L02, L03, L04, S11, Q01, Q02, Q03, Q06 **plus, in revision 1.2, C25, Q07, Q08, Q09.** Built so far: C11, C15, L01a. Order for the rest: §16 | C07; C06; C06; C06; S07+C09; S07; S07; S07+C13; S06; M0; M0; M0; S06; C25 needs C06+C09; Q07 needs C06+C11+C25; Q08 nothing; Q09 needs C02+C08+C09 |
| **10** | C16, C17, I03 (M1) | C11; C11+C06; Phase 3 |
| **11** | C20, X03, X04, L05, L06, C21, S12, Q04, C28 | C02; C20; S06+S07; L02; S07; C11; S06; C11; C10+L01 |
| **12** | I04 (M2 beta) | Phase 4 |
| **13+** | C18, C19, L07, L08, C23, C27, S13, apply_patch tool; then C22, X05, X06 | per WP |

\* B10 needs B06 and B09 applied first; place it at the end of wave 2.

---

## 4. Phase 0 — Build-tab fixes and browser slimming

### 4.1 Status of the earlier audit items at your current `main`

I re-checked your repo (commit `094f0e7`) by reading the code. I did **not** run the app or the database, so "fixed" means the code does what the audit asked, not that it has been tested in production.

| Audit item | Status on `main` |
|---|---|
| #1 Move/rename 500 (UPDATE revoked on versions table) | **Fixed in code**: `move_path` now copies history rows with INSERT ... SELECT and deletes the old ones, leaving a tombstone. B01 adds tests that prove it against a real database. |
| #2 "Failed to fetch" instead of 500 | **Fixed**: `api/middleware.py` (UnhandledErrorMiddleware inside CORS). |
| #3 Pyodide fails to load | **Open on `main`**: my patch `item3_pyodide_selfhost.patch` is not committed there (WP B02). |
| #4 Delete then recreate collides in history | **Fixed in code**: next-version SQL plus version shifting on move. Covered by B01 tests. |
| #5, #6 Run executes wrong file; plots missing in preview | **Moot** once the Python Run is removed from the preview panel (B03). |
| #7 Promote discards unsaved edits | **Open** (B04). |
| #8, #9 Python worker robustness and traceback styling | **Open**, now only for chat artifacts (B08). |
| #10 Board data race on project switch | **Open** (B05). |
| #11 Unreadable validation errors | **Open** (B06). |
| #12 Tests can't catch grant/constraint bugs; no `npm test` | **Open** (B01 backend, B11 frontend). |
| #13 Pyodide pin | **Open**, after B02 (B12). |
| #14 File paths ending in `/history` or `/restore` | **Documented** in `api/routes/code.py` (routes are ordered deliberately); no patch needed. |
| #15 CORS origins default only `localhost:3000` | **Open** (B07). |

### 4.2 Work packages

**B00 · Baseline (no patch)** · S
Run `pytest tests/unit tests/integration` in `backend/`, the frontend node tests, `next lint` and `next build` on `main`, and write the results into `PATCHES.md`. If anything fails on the untouched base, fix or record it before starting Wave 1, so later patches are not blamed for old failures.

**B01 · Real-database tests for the code-file store** · M · Wave 1
*Files (new only):* `backend/tests/integration/test_code_files_real_db.py`, `backend/tests/static/test_sql_grants.py`, small additions to `backend/tests/conftest.py`.
*What:* Existing tests use a fake cursor, so grants and constraints are never exercised. Add (1) an integration test that connects as the `minime_app` role against a throwaway Postgres (env `TEST_DATABASE_URL`, skipped if unset) and runs: save, move file, move folder, delete then recreate at the same path, move onto a previously deleted path, restore; and (2) a static test that parses every SQL statement in `eo/workspace_code_files.py` and fails if it uses `UPDATE` on a table the migrations only grant `SELECT, INSERT, DELETE` on.
*Done when:* both tests pass on `main`; temporarily reintroducing the old `UPDATE file_path` makes them fail; README note explains how to run them.

**B02 · Pyodide self-hosting for chat artifacts** · M · Wave 1
*Patch exists:* `item3_pyodide_selfhost.patch` (apply to `main` and commit it; regenerate it if it no longer applies).
*What it does:* self-hosted core under `/pyodide/` with the CDN as a fallback; failed loads are not cached; packages load on demand; package download failures surface as explicit errors; vendor script on `postinstall`; middleware skips `/pyodide/` and `/workers/`; adds the worker test.
*Done when:* `npm ci` creates `public/pyodide/`; all node tests pass; a plain Python chat artifact runs with the CDN blocked.

**B03 · Remove the Python Run from the preview panel** · S · Wave 1
*Files:* `frontend/app/components/workbench/PreviewPane.jsx` (+ its test).
*What:* Remove `PythonPreview` and its call site (about line 664 and line 923). A `.py` file selected in the preview panel shows a neutral empty state ("Python files aren't run in the browser"). Do not touch `ArtifactRenderer.jsx` or the worker.
*Done when:* no import of the worker remains in `PreviewPane.jsx`; selecting a `.py` file shows the empty state; HTML and React previews are unchanged; lint and build pass.

**B04 · Guard "Promote" against unsaved edits** · S · Wave 1
*Files:* `frontend/app/components/tabs/BuildTab.jsx`.
*What:* `handlePromote` (about line 1436, called around line 1540) bypasses `guardUnsaved()`. Wrap the call so a dirty editor asks for confirmation, matching the other navigation actions.
*Done when:* with an unsaved edit, Promote shows the same confirmation as switching projects; with a clean editor it behaves as before; test covers both.

**B05 · Fix the board data race on project switch** · S · Wave 2 (after B04)
*Files:* `BuildTab.jsx`.
*What:* `refresh()` (about line 1405) calls `setData` outside the cancellation guard, so a slow response from the previous project can overwrite the current one. Tie the response to the project it was requested for and drop stale ones.
*Done when:* a test with two overlapping fetches shows only the latest project's data.

**B06 · Readable validation errors** · S · Wave 1
*Files:* `frontend/app/lib/workbench/fileProviders.js` (`parseErrorDetail`, about line 94) + test.
*What:* FastAPI 422 responses return `detail` as an array of objects; today that renders "[object Object]". Format arrays (field and message), objects, and strings into one readable line.
*Done when:* unit tests for string, array, object and missing-detail cases.

**B07 · Dev-friendly CORS origins** · S · Wave 1
*Files:* `backend/api/server.py` (about line 268), `backend/.env.example` (or the existing env docs), a unit test.
*What:* Default allowed origins include `http://127.0.0.1:3000` as well as `http://localhost:3000`; add an optional `ALLOWED_ORIGIN_REGEX` setting for LAN testing, documented as dev-only. Never allow `*` with credentials.
*Done when:* tests cover the defaults and the regex; production env docs say how to set explicit origins.

**B08 · Chat-artifact Python runner hardening** · M · Wave 2 (after B02)
*Files:* `app/hooks/usePyodideWorker.js`, `public/workers/pyodideWorker.js`, `app/components/ArtifactRenderer.jsx`, tests.
*What:* a visible **Stop** control; a run timeout (default 30 s) that terminates and recreates the worker; a clear message for `input()` (not supported); tracebacks sent to the error stream so they get the error styling.
*Done when:* `while True: pass` can be stopped and the next run works; a traceback shows in the error style; tests cover timeout and restart.

**B09 · Remove the browser Terminal panel** · S · Wave 1
*Files:* `frontend/app/components/workbench/BottomPanel.jsx`, `frontend/app/components/TerminalPanel.jsx` (delete), `EditorWorkbench.jsx` wiring, tests.
*What:* Remove the Terminal tab and component. Keep Problems, Console and History. Leave the backend command routes in place (M2C replaces them later).
*Done when:* no reference to `TerminalPanel` remains; the other bottom tabs behave as before; lint and build pass.

**B10 · Remove Local folder mode from the browser editor** · M · Wave 2 (after B06, B09)
*Files:* `fileProviders.js` (`createLocalFileProvider`), `EditorWorkbench.jsx` (the source toggle and local-only branches around lines 331, 500, 1005, 1690, 1729, 1757), the explorer's source switch, `HistoryPanel.jsx`, `PreviewPane.jsx` (only if it references local-source state), tests.
*What:* The editor works on cloud project files only. **Keep** `useDaemonStatus` and the Dev-server URL preview proxy path (M2C replaces them in Phase 5). Leave backend `local_workspace` routes untouched.
*Done when:* no local-provider code path remains in the editor; Dev-server URL preview still works with a running daemon; all node tests, lint and build pass.

**B11 · Frontend test runner and CI** · S · Wave 2 (after B02)
*Files:* `frontend/package.json`, a small `frontend/scripts/run-node-tests.mjs`, `.github/workflows/ci.yml`.
*What:* Add `npm test` that runs every `*.test.mjs`; add the frontend tests, `next lint` and `next build` to CI beside the existing `pytest tests/unit tests/integration` job.
*Done when:* `npm test` passes locally and in CI; a deliberately broken test fails CI.

**B12 · Pyodide version bump (optional)** · S · Wave 3
*Files:* `package.json`, `package-lock.json`, worker constant.
*What:* Move `PYODIDE_VERSION` and the dependency together to the current patch release (npm shows newer 314.x versions than 314.0.2) and re-run the worker test. Skip if B02 is stable and you do not need it.

**AUD1–AUD6 · Audits of the remaining Build areas** · S each · Wave 1, parallel
Read-only reviews that produce a findings document, no code: Tasks board, Instructions, Wireframes, the proposals and review flow, History panel, chat dock. Each finding becomes a numbered B-WP (B13 onward) only if you decide it is worth a patch.

### 4.3 Phase 0 exit checklist

- [ ] CI green (backend pytest, frontend `npm test`, lint, build).
- [ ] Move, rename and delete-then-recreate work in the browser against the real database.
- [ ] No Run, Terminal or Local folder in the browser editor; Dev-server URL preview still works.
- [ ] Python in chat artifacts runs and can be stopped; works with `cdn.jsdelivr.net` blocked.
- [ ] `PATCHES.md` lists every applied patch.

---

## 5. Phase 1 — Contract and walking skeleton

**Goal:** the thinnest path that proves the whole architecture: a user logs in from the terminal, the device connects, a message goes to the server, a model reply streams back, usage is charged to the shared account, and the web app shows the device and the usage. No tools yet.

### P00 · Protocol and tool-schema contract · S · Wave 1 · *blocks S04, S05, S09, C04, C05*

*Implements:* product guide §5.5, §13.1–13.2, Appendix F; this guide §O1.
*Files (new):* `protocol/README.md`, `protocol/v1/*.json` (JSON Schemas), `protocol/v1/tools/*.json`, `protocol/fixtures/*.jsonl`, `protocol/validate.py`, `backend/tests/unit/test_protocol_contract.py`, a CI step.

*What:*
1. **Envelope:** `{ "v": 1, "t": "<type>", "id": "<uuid>", "run_id": "<opaque>", "seq": <int, server events only>, "ts": "<iso>", "payload": {…} }`.
2. **Message types:**
   - Client → server: `hello`, `run.start`, `user_message`, `tool_result`, `tool_stream`, `approval`, `cancel`, `run.resume`, `ping`.
   - Server → client: `welcome`, `run_event`, `tool_proposed`, `budget_warning`, `error`, `pong`.
3. **`run_event` subtypes:** `text_delta`, `text_done`, `tool_started`, `tool_finished`, `state_changed`, `usage`, `notice`.
4. **Error codes** (stable strings): `unauthorized`, `device_revoked`, `quota_exhausted`, `run_not_found`, `protocol_unsupported`, `rate_limited`, `provider_unavailable`, `tool_timeout`, `invalid_message`, `internal`.
5. **`run.start` payload:** `profile` ("code"), `mode`, `cwd_label` (a label, not a path), `instructions` (text assembled by the client), `rules`, `memory_index`, `tool_catalog_version`, `history` (optional, for resume from the device log), `model_pref`.
6. **Tool schemas v0** (`read_file`, `list_dir`, `glob`, `grep`, `edit_file`, `write_file`, `delete_path`, `bash`, `plan_exit`) with `risk` levels R0–R4, per product guide §7.2–7.3.
7. **Golden transcripts** in `protocol/fixtures/` (a plain chat, a run with one edit and one approval, a disconnect and resume, a quota error). Both client and server tests replay these, which is what lets the two sides be built in parallel.
8. **Versioning rule:** additive changes only within `v1`; breaking changes create `v2`; the server declares its minimum supported version in `welcome`.

*Done when:* every fixture validates; invalid examples fail; a test proves the schemas in `protocol/v1` are the only source (the client package carries a synced copy and CI checks byte equality).

### S01 · Shared usage ledger and plan limits · L · Wave 1

*Implements:* §O2; product guide §14.4.
*Files:* `backend/migrations/0012_user_plans_and_usage_ledger.sql`; new `backend/eo/usage_ledger.py`, `backend/eo/plans.py`, `backend/eo/usage_context.py`, `backend/config/plans.json`, `backend/api/routes/usage.py`; **small hooks** in `backend/utils/llm_client.py` (beside `_record_call_log`) and `backend/api/task_runner.py`; tests. *This WP is the only one allowed to edit `llm_client.py` and `task_runner.py`.*

*What:*
1. Tables: `user_plans(user_id, plan_key, credit_pool, period_start, period_end, status)` and `usage_ledger(id, user_id, surface, session_id, run_id, provider, model, input_tokens, cached_input_tokens, output_tokens, credits, cost_usd, created_at)` with `surface in ('web','m2c','menux','system')`. Ledger rows hold **numbers and IDs only**, never content.
2. `usage_context`: a `contextvars` holder for `(user_id, surface, session_id)`. `task_runner` sets it where `owner_id` is available; any other LLM entry point that has an owner sets it too. **First do an inventory** of every caller of `generate_text` / `stream_completion` and list in the patch description which ones carry an owner and which are attributed to `system`.
3. The hook in `llm_client` writes one ledger row per real call, **fail-open** (a ledger error never fails the user's call), next to the existing `_record_call_log()`.
4. `usage_ledger.check(user_id, estimate)` (pre-flight) and `commit(...)`; when the pool is exhausted it returns a structured `quota_exhausted` result (the web app and M2C each decide how to present it). Free and unconfigured accounts follow `plans.json` defaults.
5. `GET /api/usage`: pool, used, remaining, reset date, by-surface breakdown.
6. RLS: users can read only their own rows; writes come from the app role.

*Done when:* a web chat task creates ledger rows with the right user and `surface='web'`; the pool decreases; `/api/usage` matches the sum of rows; a forced ledger failure does not break a chat; tests cover the call-site inventory.

### S02 · Credit weighting · S · Wave 2 (after S01)

*Files:* `backend/config/credits.json`, `backend/eo/credits.py`, extension of the price table in `llm_client.py` **only through `credits.py`** (to keep S01 the sole owner of `llm_client.py`; if price entries must change there, add them in S01 or regenerate), tests.
*What:* `credits_for(provider, model, input, cached_input, output)` using the price table plus a cached-read price per model; the constant for 1 credit comes from config (D5). Include a test that an agent-style call pattern (large cached input, small output) produces the expected cost-weighted credits, not raw token counts.
*Done when:* unit tests with at least four models; unknown models fall back to a conservative default and log once.

### S03 · Device pairing and credentials · L · Wave 1

*Implements:* product guide §8.9; this guide §O1.
*Files:* `backend/migrations/0013_m2c_devices.sql`; new `backend/eo/devices.py`, `backend/api/routes/devices.py`, tests.
*What (device-code flow):*
- `POST /v1/code/devices/pair/start` {device_name, os, client_version} → {device_code (secret), user_code (short, human-friendly), verification_url, interval, expires_in}.
- `POST /v1/code/devices/pair/poll` {device_code} → `pending | approved{device_credential, device_id} | denied | expired`. The credential (256-bit random) is returned **once**; the server stores only its SHA-256.
- `POST /api/devices/approve` {user_code} (signed-in user) binds the device to that user; `GET /api/devices` lists; `POST /api/devices/{id}/revoke`.
- `POST /v1/code/devices/token` {device_credential} → short-lived JWT (about 15 min) with `sub=user_id`, `device_id`; checked against `revoked_at`.
- Rate limits on start and on user-code attempts; user codes expire (about 10 min) and lock after repeated wrong attempts.
*Done when:* full flow works against the test client; a revoked device can no longer get a token; credentials never appear in logs; a replayed `device_code` after approval fails.

### S04 · Device socket endpoint and handshake · M · Wave 2

*Files:* new `backend/codeagent/__init__.py`, `ws.py`, `connections.py`; one `include_router` line in `backend/api/server.py`; tests.
*What:* `WS /v1/code/device`. Handshake: client sends `hello{protocol, jwt, client_version, caps}`; server verifies the JWT and revocation, replies `welcome{minimum_protocol, limits, jwt_ttl}` or `error`. Registry of connected devices per user; ping/pong; token refresh over the socket before expiry; validation of every message against `protocol/v1`; clean close codes. Reuse the structure of `eo/local_workspace.py` where it fits, but **do not** reuse its shared-token auth.
*Done when:* tests replay the protocol fixtures against a fake device; an invalid JWT or revoked device is refused; messages that fail schema validation get `invalid_message` and do not crash the socket.

### S05 · Model adapter with native tool use · XL · Wave 2

*Files (new only):* `backend/codeagent/model_adapter.py`, `backend/codeagent/adapters/openai_compat.py`, `backend/tests/unit/test_codeagent_adapter.py`, `backend/tests/manual/smoke_tool_calling.py`.
*What:* A provider-neutral streaming interface that yields `text_delta`, `tool_call{id, name, arguments}`, and `usage{input, cached_input, output}` events, with errors mapped onto your existing `utils/llm_errors.py`. First adapter: OpenAI-compatible chat completions with `tools`. Reuse the key selection and cooldown helpers from `llm_client.py` by **importing them read-only**; do not edit that file. Add the manual smoke script (20 tool-calling calls against the chosen dev provider; report malformed-call rate).
*Reuse (MiniLocker, §11.6):* port `minilocker/llm/toolcalls.py` (tolerant parsing of malformed tool-call arguments and of calls written as plain text) with its tests into `backend/codeagent/adapters/`, and build the smoke script on `minilocker/llm/bakeoff.py`. MiniLocker's client does not stream, so the streaming layer is new work. The parser must pass this WP's malformed-argument tests as written.
*Done when:* unit tests with a fake streaming server cover text-only, one tool call, parallel tool calls, malformed JSON arguments, and provider errors; the smoke script produces a report you can read to pick the dev model.

### S06 · Run manager, ephemeral buffer, run metadata · L · Wave 3

*Implements:* §O1; product guide §6.2.
*Files:* `backend/migrations/0014_m2c_runs.sql`; new `backend/codeagent/runs.py`, `buffer.py`, tests.
*What:* Create a run (`profile`, `mode`), run state machine (`created → running ⇄ awaiting_approval → completed`, plus `paused_budget`, `paused_disconnected`, `paused_error`, `cancelled`, `failed`, `expired`), content-free metadata row, and the **ephemeral buffer**: the conversation for an active run in Redis (via the existing bus), **encrypted** (AES-GCM, key derived from a server secret and the run ID), TTL per D6, deleted on completion. Cancel uses `eo/run_guard`'s flag. `run.resume` rebuilds the buffer from the device's `history` if it expired.
*Done when:* state transitions are tested; buffer content is unreadable without the key; after completion nothing remains in Redis; **no content column exists** in the metadata table.

### C01 · Client skeleton and minimal `doctor` · M · Wave 1

*Implements:* §O3, §O4; product guide §12.4, Appendix E.
*Files (new):* `m2c/pyproject.toml`, `m2c/src/m2c/{__init__,cli,config,paths,logging_setup}.py`, `m2c/src/m2c/doctor.py`, `m2c/tests/`, CI step for `m2c/tests`.
*What:* Entry point `m2c` with `--version`, `login`, `logout`, `doctor` (stubs for the first two). Creates `~/.m2c/` with `0700` permissions. `doctor` checks: Linux or WSL2 (reject WSL1 and native Windows with a clear message), Python version, `rg`, `git`, `bwrap` present, project path not under `/mnt/c`, writable config dir. Logging never records message content.
*Done when:* installs in a clean venv; `m2c doctor` prints a readable report and a non-zero exit when a hard requirement is missing; unit tests mock each check.

### C02 · Local store · M · Wave 2

*Implements:* §O1; product guide §9.3, §11.2.
*Files:* `m2c/src/m2c/store/{db.py,migrations.py,sessions.py,events.py}`, tests.
*What:* SQLite at `~/.m2c/state.db` with tables `sessions(id, project_path, created_at, mode, model_pref)`, `events(session_id, seq, ts, type, json)` (append-only), `approvals(...)`, `checkpoints(session_id, step, path, blob_hash, ts)`, plus a schema version table and forward-only migrations. Export to JSONL. File mode `0600`.
*Reuse (MiniLocker, §11.6):* optional. `minilocker/ledger/chain.py` is a model for hash-chaining `events` (`prev_hash` and `hash` per row) and for reading back a log whose final line was torn by an interrupted write. The chain detects edits; it is not signed or anchored, so describe it that way.
*Done when:* create, append, read-back and export work; an interrupted write leaves a valid database; migrations are tested from version 0.

### C03 · Login (device-code client) · M · Wave 2

*Files:* `m2c/src/m2c/auth/{login.py,credentials.py}`, tests with a mock server.
*What:* `m2c login` calls `pair/start`, prints the code and URL (do **not** depend on a browser opening, which often fails in WSL2), polls, then stores the credential. Storage: OS keyring when available, else a `0600` file under `~/.m2c/`. `logout` deletes it and calls revoke. Token fetching and refresh helper for the link.
*Done when:* tests cover pending, approved, denied, expired and network errors; the credential never appears in logs or tracebacks.

### C04 · Device link client · M · Wave 3

*Implements:* product guide §13.2; reuses ideas from `daemon/connection.py`.
*Files:* `m2c/src/m2c/link/{client.py,reconnect.py}`, tests.
*What:* WebSocket client (`websockets`), handshake per P00, reconnect with backoff and jitter, `run.resume` using the last seen `seq`, request/response correlation by `id`, graceful shutdown. Event callbacks into the store (C02).
*Done when:* tests replay the golden fixtures against a fake server; killing the connection mid-stream resumes without duplicate or missing events.

### X01 · Devices page in the web app · M · Wave 2

*Files:* a Settings section (new component under `frontend/app/components/` and a route or tab entry), tests.
*What:* Enter the code from the terminal to approve a device; list devices (name, OS, last seen); revoke. Show a short explanation of what M2C can and cannot do on that device and the trust statement from §O1.
*Done when:* the full pairing loop works with S03; revoked devices disappear from the active list; node tests and build pass.

### X02 · Usage panel · S · Wave 3

*Files:* a small component using `GET /api/usage`.
*What:* Shows pool, used, remaining, reset date, and a by-surface breakdown (web, M2C). Uses your four-numbers wording (what you used, what is left, when it resets, what a run costs roughly).

### I01 · Walking skeleton ("hello run") · M · Wave 4

*Joins:* S01, S04, S05, S06, C03, C04, X01.
*Files:* `backend/codeagent/hello.py` (a minimal text-only loop), `m2c/src/m2c/repl.py` (a minimal prompt loop), end-to-end test.
*What:* `m2c` after login opens a prompt; a typed message becomes `run.start` + `user_message`; the server calls the adapter; text streams back; a ledger row is written with `surface='m2c'` and the right user; the web Usage panel changes.
*Done when:*
- [ ] Login approved in the web app; device appears there.
- [ ] A message gets a streamed reply.
- [ ] A ledger row exists (numbers only) and the pool decreased.
- [ ] Disconnect and reconnect mid-reply resumes the stream.
- [ ] Revoking the device in the web app closes the session within about a minute.

---

## 6. Phase 2 — Core agent (milestone M0, internal)

**Goal:** a real tool-using coding agent you can use on the MiniMe repo itself, with local approvals, checkpoints and a usable terminal UI. No sandbox yet, so **internal use only, with the default mode set to ask**.

### S09 · Server tool broker · M · Wave 5

*Files:* `backend/codeagent/broker.py`, tests.
*What:* Sends `tool_proposed` to the device with a timeout, waits for `tool_result`, enforces `call_id` idempotency, handles disconnect (marks the call failed with a clear reason and pauses the run), truncates oversize results with a marker, and labels result trust. Never decides approvals.
*Done when:* tests cover timeout, duplicate results, disconnect during a call, and oversize output.

### C05 · Local tool executors v0 · L · Wave 5

*Implements:* product guide §7; §8.5.
*Files:* `m2c/src/m2c/tools/{files.py,search.py,paths.py}`, tests. Port and extend `daemon/path_guard.py` and the relevant parts of `daemon/tools.py`.
*What:* `read_file` (line ranges; records "seen" state), `list_dir`, `glob`, `grep` (ripgrep wrapper, capped output), `edit_file` (exact string, fail if not unique), `write_file` (atomic: temp file, validate, rename; requires prior read for existing files), `delete_path`. Path guard pins everything under the session root and resolves symlinks. **Two-form denylist:** a hard-coded list the model and project files cannot change (private keys, `.env*`, credential stores) plus a user list in settings.
*Done when:* tests include path traversal, symlink escape, read-before-write, non-unique edit, denylist, and a simulated interrupted write.

### C06 · Policy engine v0 · L · Wave 5

*Implements:* product guide §8.2–8.3.
*Files:* `m2c/src/m2c/policy/{modes.py,rules.py,decide.py,shellparse.py}`, tests.
*What:* Modes `plan`, `ask`, `accept-edits`. Rules `allow`, `ask`, `deny` with exact strings first and simple patterns; evaluation order deny → ask → allow; settings layering (managed > user > project) with project settings requiring the trust prompt. **Compound commands** are split (`&&`, `||`, `;`, pipes, subshells, redirections) and each part is checked; unknown syntax means "ask". Protected paths (`.git/`, `.m2c/`, shell rc files) are read-only for edits. The decision function is pure and returns `allow | ask | deny` with a reason. **Fails closed.**
*Reuse (MiniLocker, §11.6):* test corpus only. Mine `minilocker/policy/engine.py` and its tests for bypass cases, but do not port the engine: it scores commands with regexes and treats unparseable syntax as low risk, the opposite of this WP's "unknown syntax means ask" and fail-closed rule.
*Done when:* a large table-driven test, including bypass attempts (`ls && curl …`, `$(…)`, backticks, env-var tricks), passes; no code path allows without an explicit rule or mode.

### C12 · Instructions, rules and memory loader · M · Wave 5

*Files:* `m2c/src/m2c/context/{instructions.py,rules.py,memory.py}`, tests.
*What:* Load `M2C.md`, then `AGENTS.md` and `CLAUDE.md` if present, hierarchically (global, repo, subdirectory) with `@path` imports (size and depth limits); path-scoped rules; auto-memory index (first ~200 lines or 25 KB). Produces the `instructions`, `rules` and `memory_index` fields for `run.start`. Memory writes are shown to the user and never include secrets.
*Done when:* tests for precedence, imports, oversize files and missing files.

### C10 · Headless mode · S · Wave 5

*Files:* `m2c/src/m2c/headless.py`, tests.
*What:* `m2c -p "task"` with `--output-format text|json`, `--mode`, non-interactive policy (only explicit allow rules; anything that would ask fails the run with a clear error).
*Done when:* exit codes distinguish success, policy denial, quota, and failure; tests with the fake server.

### S07 · Agent loop executor v0 · XL · Wave 6

*Implements:* product guide §6.1–6.3, 6.8–6.10.
*Files:* `backend/codeagent/loop.py`, `prompts.py`, tests.
*What:* The loop from product guide §6.1: assemble context, call the adapter with visible tools (plan mode restricts to read-only plus `plan_exit`), stream events, send tool calls through the broker (S09), append results, repeat. Stops: model finishes, step limit, dollar ceiling, cancel, three identical failing calls, three consecutive failures (reusing `run_guard`'s breaker and `tool_budget`). Provider errors fall through the chain and emit a `notice` when quality class changes. Never silently downgrade.
*Done when:* tests with a scripted fake model cover multi-step runs, parallel tool calls, malformed calls, cancel, step limit, and disconnect-pause-resume.

### C07 · Shell tool v0 · M · Wave 6

*Files:* `m2c/src/m2c/tools/shell.py`, tests.
*What:* Run a command under the policy engine: timeout, streamed output, process-group kill on cancel, sanitized environment (strip `*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*`, cloud credentials), working directory pinned to the session root, output cap. **No sandbox yet** (C11): default mode `ask`, and print a visible warning that commands run with the user's full privileges.
*Done when:* tests cover timeout, kill, env stripping, and truncation.

### C08 · Checkpoints and rewind · M · Wave 6

*Files:* `m2c/src/m2c/checkpoints.py`, tests.
*What:* Before each edit, snapshot affected files (content-addressed blobs under `~/.m2c/checkpoints/<session>/`), index in the store (C02). `rewind(step)` restores files and optionally truncates the conversation. Skips symlinks. UI states plainly that remote effects are not covered.
*Done when:* edit, edit, rewind restores exact bytes; interrupted snapshot leaves no half state.

### S08 · Context assembler v0 · M · Wave 7

*Files:* `backend/codeagent/context.py`, tests.
*What:* Order for cache stability (system prompt, tool schemas, instructions, rules, memory index, history, tool results); truncate large tool results; clear old tool outputs first when the window fills, then summarize (compaction v0); stop auto-compaction after repeated thrash; keep the system prompt short and capability-focused (product guide §6.4).

### S10 · Metering inside the loop · M · Wave 7

*Files:* `backend/codeagent/metering.py`, tests.
*What:* Before each model call, `usage_ledger.check`; after, `commit` with real usage (including cached tokens) and credits from S02; per-run credit ceiling; `budget_warning` at 80%; pause with `paused_budget` and a "grant more" path through the existing `run_guard.grant_more`. Quota failures return `quota_exhausted`, never a silent downgrade.
*Done when:* tests prove charges are exact for a multi-step run; a run pauses at the ceiling and resumes after a grant.

### C09 · Terminal UI v0 · L · Wave 7

*Implements:* product guide §12.1–12.3 (using D2).
*Files:* `m2c/src/m2c/tui/{app.py,render.py,approval.py,diff.py,status.py}`, tests for the pure render and approval logic.
*What:* Streaming chat, tool cards with collapsed diffs, an approval prompt (`y` once, `a` allow this exact command for the session, `n`, `e` edit, `d` deny), a status line (mode, model class, tainted flag, context percentage, running credits), `Esc` interrupt (queue messages while a tool runs), `Esc Esc` rewind, `Shift+Tab` mode cycle, `@` file mention. Everything behind a small `UI` interface so the library can be swapped.
*Done when:* an interactive session works end to end against the fake server and the real server; tests cover approval keys, rendering of large diffs, and interrupt handling.

### I02 · First real task (M0) · M · Wave 8

*Joins:* all Phase 2 WPs.
*What:* Use M2C on the MiniMe repo to make a small real change (for example a docstring fix and a test). Capture the run as a golden transcript.
*Done when:*
- [ ] Read, grep, edit, run tests, with approvals at the right moments.
- [ ] Checkpoint and rewind restore exact bytes.
- [ ] The ledger shows the run's credits and the web Usage panel agrees.
- [ ] Headless mode runs the same task with explicit rules.
- [ ] A short written list of what annoyed you, which becomes the backlog.

---

## 7. Phase 3 — Safety and workflows (milestone M1, safe daily driver)

**Goal:** an agent you would let run on your own machine every day. Shell commands run in a sandbox, secrets are protected, untrusted content tightens approvals, and quality and security are measured.

### C11 · Sandbox (bubblewrap) and network proxy · XL · Wave 9

*Status (2026-11-14): built as two patches, C11a (profile, probe, shell integration) and C11b (the CONNECT proxy and network bridge). New in revision 1.2: D17 (sandbox is not approval) and the Q07 sandbox cases (config folders and the shared git directory are protected).*

*Implements:* product guide §8.4; §O3.
*Files:* `m2c/src/m2c/sandbox/{bwrap.py,profile.py,netproxy.py,probe.py}`, tests (skipped when `bwrap` or user namespaces are unavailable, with a loud "SKIPPED" report).
*What:*
- Run `bash` through bubblewrap: project directory writable; `.git/`, `.m2c/` and shell rc files read-only inside it; system toolchain paths read-only; home secrets (`~/.ssh`, `~/.aws`, browser profiles) not mounted; private `/tmp`; new PID namespace.
- Network **off by default** inside the sandbox; a local **HTTP CONNECT proxy** with a domain allowlist is the only way out, prompting on a new domain.
- `probe.py` tests at startup that the sandbox really works (can it write outside the project? read `~/.ssh`? reach a blocked host?) and `doctor` reports it. If the sandbox cannot be built (WSL2 without user namespaces, container without privileges), **say so and refuse `auto-allow`**; never pretend.
- Landlock + seccomp as an alternative backend is optional and can wait.
*Reuse (MiniLocker, §11.6):* tests only. Re-aim the Attack Lab's escape and exfiltration attacks (`read_secrets`, `exfil_unknown_domain`, `host_escape_probes`, `malicious_repo_hook`) at the bubblewrap backend. The Docker sandbox itself is not reused.
*Done when:* escape tests fail as intended (write `.git`, read `~/.ssh`, reach a blocked domain, `cd ..` then write); commands that need a new domain trigger the prompt; works on Ubuntu native and WSL2 Ubuntu.

### C13 · Hooks · M · Wave 9

*Implements:* product guide §8.8, Appendix C.
*Files:* `m2c/src/m2c/hooks/*`, tests.
*What:* Events `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `SubagentStart/Stop`, `PreCompact`, `Stop`, `SessionEnd`. Command handlers first. **Contract (D15):** the event arrives as JSON on stdin; exit 0 means "no objection" and the normal policy still decides, exit 2 blocks and sends the message to the model, other codes warn; a hook can tighten (ask, deny) and never loosen, so a hook's "allow" does not override deny rules, protected paths, the taint floor, the sandbox or the folder-trust rule. A `PermissionRequest` hook can answer only ask or deny. Hooks get a timeout and a trimmed environment, and their output is redacted like any tool result. Project hooks require the folder-trust prompt (`trust/fingerprint.py` already covers `.m2c/hooks`). Hooks cannot be edited by the model (the settings paths are protected, and Q07 tests that the sandbox refuses writes there).
*Done when:* a `PreToolUse` hook blocks a command; a `Stop` hook forces a continuation; a hook timeout does not hang the session.

### C14 · Skills · M · Wave 9

*Files:* `m2c/src/m2c/skills/*`, tests.
*What:* Load `SKILL.md` folders from `~/.m2c/skills`, `<repo>/.m2c/skills`, and (after a trust prompt) `<repo>/.agents/skills` and `.claude/skills`. Only name and description go into context; the `skill` tool loads the body. Support `disable-model-invocation`. Ship built-ins: `init`, `verify`, `review`, `create-skill`.
*Revision 1.2:* a skill that declares tools or hooks does not run unattended (headless, or called by Menux) until the owner has an explicit allow rule for `skill(name)`; a skill can never grant itself more than policy allows; skills copied from `.agents/skills` and `.claude/skills` follow the same trust prompt. `backend/eo/skill_library.py` is the web agents' server-side skill store, a different design, so it is not reused here (skills are local files, O1).

### C15 · Secrets, redaction and environment · M · Wave 9

*Status (2026-11-14): built.*

*Implements:* product guide §8.5.
*Files:* `m2c/src/m2c/secrets/{redact.py,env.py}`, tests.
*What:* A redaction filter applied to **every** tool result before it leaves the machine (cloud keys, tokens, private-key blocks, JWTs, high-entropy strings near words like "key" or "secret"), with a test corpus and a false-positive budget. Stronger environment sanitization with named per-project exceptions.
*Done when:* canary secrets planted in files and env never appear in outgoing messages (asserted against the fake server).

### L01 · `ask_user`, `tasks`, `plan_exit` · M · Wave 9
*Status (2026-11-14): partly built. L01a (`ask_user` and `tasks`, client and server) and S07b (leaving plan mode) are in; check that every *Done when* item below has a test, then close it.*
Server tools and client rendering for a blocking structured question, a small task list with statuses and dependencies, and plan approval. *Done when:* a run can pause on a question and continue; plan mode ends only through `plan_exit`.

### L02 · Subagents · L · Wave 9
`explore` and `plan` first (read-only tools, cheap model class, separate context, return a summary only, no further spawning, share the run's budget). `review` and `security-review` come in L05. *Done when:* a subagent's exploration does not enter the main context, and its tool calls are fully logged locally.
*Revision 1.2:* a subagent keeps its own model class and budget and is not moved by a parent's mode or plan-chain change; a subagent answer cut off at the token limit is asked again more briefly instead of returning only its tail; background subagents wait for C16.

### L03 · Compaction v1, auto-memory, scratchpad · M · Wave 9
Summarization with user-controlled "compact instructions"; stop-on-thrash; memory writes shown and undoable; a run-scoped scratchpad file for long tasks. *Done when:* a 60-step run stays within a set context percentage and the final answer still reflects early decisions.
*Status:* S08 already does mechanical compaction on the server; this WP adds model-written summaries, compact instructions and the scratchpad. *Revision 1.2:* compaction must never drop the most recent turns after an unclean exit (Q09), a provider "context too long" error triggers compaction instead of failing every later turn, and the instructions loaded by C12 survive compaction.

### L04 · Verification loop and Stop hooks · M · Wave 9
`lint`, `test`, `build` commands from settings; run after edits; the `Stop` hook can block finishing until tests pass; at most N fix attempts, then report what could not be fixed. *Done when:* a failing test sends the model back to fix it, and a stuck loop ends with an honest report.

### S11 · Server hardening and process split · L · Wave 9

*Files:* `backend/codeagent/` modules, `backend.Dockerfile` or a second service entry in `docker-compose.yml`, a new ASGI entry (for example `backend/codeagent/app.py`), tests.
*What:* Move pending-approval and connection-routing state from process memory to Redis so multiple workers work; a dedicated gateway for WebSockets; per-user concurrent-run and rate limits; health checks; graceful drain on deploy. Run M2C traffic as its own process so long sessions do not compete with chat (your current setup runs one uvicorn process with a small agent task pool).
*Done when:* two server processes serve one run correctly (events routed, approvals found); killing one mid-run resumes on the other.

### C16 · Background shell · M · Wave 10
Long-running commands with ids, output polling, kill; dev servers and watchers. Same sandbox and policy.

### C17 · Web tools and taint tracking · L · Wave 10
*Implements:* product guide §8.6.
`web_fetch` runs **locally** through the sandbox proxy (so the user's IP and data stay local); `web_search` goes through the server (the search key stays server-side; queries are content that leaves the device, so say so in the trust copy; the server side can reuse the existing `backend/utils/web_search.py`, Tavily then Exa, behind a `/v1/code/` tool route). Any untrusted result sets the session `tainted`. While tainted: network-capable tools, `git push` and other outbound actions **always ask**, even in `accept-edits`; writes outside the project are denied. The UI shows the flag and the reason.
*Reuse (MiniLocker, §11.6):* port `minilocker/policy/injection.py` (`sanitize`, `scan`, and the nonce `fence` for untrusted text) and the taint-floor idea from `policy/engine.py`. The scan is only a signal; the session `tainted` flag and the always-ask rule above remain the control.
*Done when:* a poisoned fetched page cannot cause an unapproved outbound action in the red-team suite.

### Q01 · CI for the new packages · S · Wave 9
Run `m2c/tests`, `backend` tests (including `codeagent`), and the protocol checks on every push.

### Q02 · Eval harness · L · Wave 9
*Files:* `backend/evals/m2c/` (your repo already has `backend/evals/`).
*What:* A runner that drives `m2c -p` against a fresh copy of a task repo, then runs a verifier script. Start with 20–30 golden tasks (a web app, a firmware-style repo, a Python service). Records success, steps, tokens, credits, cache-hit rate. Used for every model and prompt change.
*Reuse (MiniLocker, §11.6):* model the runner on `minilocker/scenarios/runner.py` and the `fix_repo` scenario (`scenarios/repo_fix.py`): a verifier the model never sees, repeated runs per task, and a 95% interval (`wilson()`) reported beside the pass count. MiniLocker drives its own agent loop; this runner drives `m2c -p`.

### Q03 · Red-team suite · L · Wave 9
Fixtures for indirect injection (README, issue text, fetched page, MCP-style tool description), secret-read attempts, sandbox escapes, denylist bypass, and hook tampering. *Revision 1.2:* start from the Q07 bypass corpus and add end-to-end scenarios on top of it. **A release is blocked if any "no unapproved egress, no secret read, no write outside the project" test fails.**
*Reuse (MiniLocker, §11.6):* seed the fixtures from the Attack Lab catalog (`minilocker/attacks/catalog.py`: `hostile_page_injection`, `deny_then_bypass`, `read_secrets`, `exfil_unknown_domain`, `malicious_repo_hook` and others), rewritten for the bubblewrap backend and the CONNECT proxy.

### Q06 · "No content at rest" canary test · M · Wave 9
Run a scripted session with canary strings in prompts, file contents and tool outputs. Afterwards scan Postgres rows, application logs, Redis keys after run end, and error-reporting payloads for the canaries. Any hit fails CI. This is the test that backs your trust statement.

### C25 · Safe "always allow" and rule hygiene · S · Wave 9 · *new in revision 1.2*

*Implements:* D16. *Files:* `m2c/src/m2c/policy/rules.py`, `m2c/src/m2c/tui/approval.py`, tests.
*What:* The `a` key in the approval prompt saves the exact call (tool and normalized arguments), never a broader pattern. A saved rule is offered only when the same call, evaluated again against the new rule set, would be allowed (so a compound command with one denied or asking part is never "always allowed"). Relative deny and ask patterns such as `read_file(.env*)` are anchored to the project root, not to the current directory, so they still hold after a `cd` inside a shell command and for added directories. A late approval (after a reconnect or a restart) is checked against the current deny and ask rules before it is used. `/why` shows which rule or mode decided the last call (the decision function already returns the reason).
*Done when:* tests cover the compound-command case, a deny pattern surviving a `cd`, a late approval for a call that is now denied being refused, and `/why` naming the deciding rule; the policy invariants test stays green.

### Q07 · Policy and sandbox bypass regression corpus · M · Wave 9 · *new in revision 1.2*

*Files:* `m2c/tests/redteam/bypass_corpus/` (table-driven), CI wiring.
*What:* One table of boundary-bypass patterns with the decision M2C must give each. This class of bug is well known from the public changelogs of comparable agents, so the rows are written from those patterns and from M2C's own findings, never from anyone's source code (D13). Groups:
- **Compound commands:** `a && b`, `a; b`, pipes, `$(...)`, backticks, process substitution, here-documents, `bash -c '...'`, `env X=1 cmd`, `xargs`, `find -exec`, `timeout cmd`, `sudo`. An allow rule for one program must not allow a program it wraps.
- **A rule naming one program running another:** aliases, `PATH` shadowing, a symlinked or relative binary (`./git`).
- **Deny rules:** relative paths, `cd`, added directories, symlinks, letter case, a deny rule that applies after a restart.
- **Settings and trust:** a committed project settings or hooks file must never be treated as the person's own; the folder-trust fingerprint covers every file that can change policy.
- **Sandbox:** writes to `.m2c/` settings, hooks, skills and agents are refused in the project and in added directories; a linked worktree's shared git directory and a `.git` file that points elsewhere are protected; helper processes the sandbox starts (the network bridge and proxy) get an environment with no tokens or keys.
- **Terminal safety:** control characters in file names, paths, tool output and `-p` text output are neutralised before they reach a terminal.
Each future policy or sandbox bug adds a row as part of its fix.
*Done when:* every row has an expected decision and runs in CI; Q03 reuses the corpus as its first fixtures.

### Q08 · Docs and catalog drift check · S · Wave 9 · *new in revision 1.2*

*Files:* `m2c/tests/docs/`, optionally a small script in the book repo.
*What:* A test that fails when the documentation and the code disagree: the tool names in `protocol/v1/tools/*.json` against `policy/modes.py` (a partial check already exists) and against the tool table in the feature guide; the commands and flags printed by `m2c --help` against the README's command table; the runtime dependencies in `pyproject.toml` against the README and D14. Optional second half in the book repo: every WP ID in the index is unique, every dependency exists, every non-added WP appears in exactly one wave, and the headline counts match the index.
*Done when:* the README is regenerated or corrected first, the check is green, and changing a tool schema without updating the docs turns it red.

### Q09 · Crash, resume and truncation integrity tests · S · Wave 9 · *new in revision 1.2*

*Files:* `m2c/tests/runner/`, `m2c/tests/store/`, fake server fixtures.
*What:* Kill the client at each step of a run (after a tool result is written, before an event is flushed, during a checkpoint, during an atomic write) and check that: the local log holds every completed turn or a clear marker, never silently missing recent turns; `history` rebuilt for `run.resume` (C09a) is correct; a checkpoint is never half written; a command issued after the working directory was deleted fails with a message and does not run somewhere else; a repeated `tool_result` or approval after a reconnect is idempotent by `call_id`; a provider "context too long" error triggers compaction instead of failing every turn.
*Done when:* the fault-injection suite passes in CI against the fake server.

### I03 · M1 acceptance · M · Wave 10
- [ ] Sandbox probes pass on Ubuntu and WSL2 Ubuntu; `doctor` is honest when they cannot.
- [ ] Red-team and canary suites pass.
- [ ] 20 golden tasks at the success rate you set from your baseline.
- [ ] You use M2C for your own work for two weeks; failures are logged as backlog items.
- [ ] The Q07 bypass corpus and the Q09 crash and resume suite pass, and the Q08 docs check is green (revision 1.2).
- [ ] `PATCHES.md` matches the code and the README lists the commands that exist.

---

## 8. Phase 4 — Platform integration and beta (milestone M2, invite-only)

### C20 · Pull and push client · M · Wave 11
*Files:* `m2c/src/m2c/projects/{pull.py,push.py}`, tests.
*What:* `m2c pull <project>` writes a cloud project into a local folder (skipping `node_modules`, `.git`, build output) and records the base version per file; `m2c push` sends only changed files with their base versions. **Explicit, user-triggered, with a confirmation that shows what will be uploaded** (this is the one place project content goes to your servers on purpose).

### X03 · Handoff on the server and the "checked out" banner · L · Wave 11
*Files:* `backend/migrations/0015_project_checkouts.sql`; routes under `/v1/code/projects/{id}/pull|push|release`; frontend: banner and read-only state in the editor; tests.
*What:* Pull marks the project "checked out" by a device; the browser shows a banner and makes code files read-only with a "release checkout" button; push writes each changed file as a normal new version in history and **rejects** when the cloud version moved past the base version (user chooses to pull again or overwrite). Only code files sync; instructions, tasks and wireframes stay in the cloud.
*Done when:* two conflicting edits are detected; release works; history shows pushed versions.

### X04 · Live remote view and remote approvals · L · Wave 11
*What:* The web app shows a running M2C run **live** through a non-stored relay (nothing is kept after the stream), and can approve or cancel; remote approvals still pass the device's local hard rules. No history replay in the browser (see §O1).

### L05 · `/review` and `/security-review` · M · Wave 11
Wire the `review` and `security-review` subagents to your existing reviewer and security-reviewer roles. Output: findings with file and line that the user can send back as tasks. Content sent for review is treated like any other model call (transient).

### L06 · Plan chains and escalation · M · Wave 11
Per-plan model chains in config, an "escalate" action (strong model for planning or repeated failure), cheap class for summaries, titles and classifier; never silent downgrade; every class change is shown. Use the Q02 harness to choose chains by cost per solved task.

### C21 · Full `doctor` · S · Wave 11
Adds sandbox probes, proxy check, clock skew, keyring availability, version and update status, and a content-free diagnostics bundle the user can read before sharing.

### S12 · Beta allowlist and billing hooks · M · Wave 11
*Files:* `backend/migrations/0016_beta_allowlist.sql`, small routes, tests.
*What:* Invite-only gate for M2C; assignment of `plan_key` from your billing events (the billing integration itself is outside this guide); admin script to grant, revoke and top up credits.

### Q04 · Device-link security review · M · Wave 11
Penetration-style tests on pairing, token handling, revocation timing, and socket abuse (budgeted in your rulebook's pen-test line).

### C28 · Streaming headless output for delegation · S · Wave 11 · *new in revision 1.2*

*Files:* `m2c/src/m2c/headless.py`, `m2c/src/m2c/cli.py`, tests.
*What:* `m2c -p "task" --output-format stream-json` writes one JSON event per line on stdout (the same event types as the protocol's `run_event`, with secrets already redacted), and ends with one result line that carries the exit status and the usage totals. The existing exit-code table and signal behavior (SIGINT or SIGTERM cancels the run first) are unchanged, and `text` and `json` stay as they are. This is the interface Menux uses for delegation (Menux `MT-A07`); the earlier name `m2c run --json` does not exist.
*Done when:* a test reads the stream line by line from a fake server run, a cancelled run ends with the documented code, and Menux's delegation test can start a plan-mode run, read its events and stop it.

### I04 · M2 beta acceptance · M · Wave 12
- [ ] 20–50 invited users; per-run and per-user cost within your pricing model.
- [ ] Shared cap works across web and M2C (a user burns one pool).
- [ ] Handoff and remote view work without storing content.
- [ ] No critical findings from Q04; canary and red-team suites still green.
- [ ] Support runbook exists (revoke device, reset credits, read diagnostics).
- [ ] Menux's delegation test (`MT-A07`) runs against `m2c -p --output-format stream-json` (C28).

---

## 9. Phase 5 — Editors, scale and hardening (milestone M3)

| WP | Title | Notes |
|---|---|---|
| **C18** | ACP server (`m2c acp`) | JSON-RPC over stdio so Zed, JetBrains and similar editors can launch M2C; route commands through the editor terminal when offered. |
| **C19** | Worktrees and parallel sessions | `--worktree name`; per-plan concurrency limit; "compare runs" is optional and opt-in because it multiplies cost. *Revision 1.2:* the sandbox must treat a linked worktree's shared git directory and hook paths as protected (a Q07 row); cleanup must not delete a worktree that holds uncommitted work. |
| **L07** | Auto-mode classifier | Ships only after an eval of a few hundred labeled tool calls, including injections; local deny rules and the sandbox always win; the classifier can move "ask" to "allow", never override a deny. |
| **L08** | LSP diagnostics and repo map | Diagnostics after edits; tree-sitter outline as optional orientation; add a semantic index only if your eval shows gains. |
| **C23** | Local MCP client | MCP servers run **on the device** (data stays local, D18); trust levels per server (blocked, read-only, ask); tool search to defer schemas; build against the 2026-07-28 spec. *Revision 1.2:* tool names and descriptions from a server are untrusted data and taint the session; a rule for an MCP tool matches its exact name and a name that differs only by letter case is refused; a server's output is redacted like any tool result; servers start inside the sandbox unless the owner marks one as trusted. Reference code for the protocol handling: `backend/eo/mcp_client.py` (it runs on the server and cannot be reused as is). |
| **C27** | Managed settings and policy presets | *New in revision 1.2.* Fill the empty `managed` layer of `load_layers` (a root-owned file such as `/etc/m2c/managed-settings.toml`): precedence managed over user over project; keys for rules-only-from-managed, hooks-only-from-managed, a fixed domain allowlist, "sandbox required" and a highest mode; a lower layer can never loosen a managed setting; `doctor` shows which settings are managed and from where. Ship three documented presets, `strict`, `standard` and `lax`. Size M. Needs C06 and C26. For teams and companies, so it waits for M2. |
| **—** | `apply_patch` tool | Multi-hunk edits. |
| **S13** | Migrate the preview proxy from `daemon/` into `m2c/` | Then retire `daemon/`, the backend `local_workspace` routes and `useDaemonStatus`. |
| **—** | External security audit | Scope: device link, policy engine, sandbox, secrets, MCP. Budgeted in your rulebook; make it the gate for GA. |

Exit: editors work via ACP; classifier meets its false-allow limit; audit findings fixed.

---

## 10. Phase 6 — Release (GA)

| WP | Title | Notes |
|---|---|---|
| **C22** | Packaging and release | Publish to PyPI; `install.sh` (installs `uv`, checks `rg`, `git`, `bwrap`, runs `doctor`); `m2c update`; stable and beta channels; signed releases; changelog. |
| **X05** | Docs and trust pages | Install guide for Linux and WSL2, data-location page (use the §O1 wording), what leaves your device and when, security model, uninstall and data deletion, FAQ. |
| **X06** | Legal and privacy | Sub-processor list, retention statement (run buffer TTL, ledger fields), terms for command execution on user machines. |
| **—** | Support tooling | Content-free diagnostics, device revoke, credit adjustments, status page. |
| **—** | Monitoring | Content-free metrics only: auth failures, run counts, cost per run, error rates. |

GA checklist: audit findings closed; canary and red-team suites green on the release build; install tested on fresh Ubuntu, Debian, Fedora and WSL2 Ubuntu; shared-cap behavior verified end to end; trust copy matches what the system does.

---

## 11. Cross-cutting specs

### 11.1 WSL2 and Linux requirements (for `doctor` and the docs)

- **Detect WSL2** from the kernel release string containing "microsoft" and "WSL2"; reject WSL1.
- **Keep projects in the Linux filesystem.** `/mnt/c/...` is slow, has different permission semantics, and defeats the sandbox's assumptions; `doctor` warns and the sandbox refuses to auto-allow.
- **Packages:** `git`, `ripgrep`, `bubblewrap`; unprivileged user namespaces must work (`doctor` tries to run `bwrap` for real instead of trusting a flag).
- **No GUI assumptions:** device login prints a URL and code; do not rely on `xdg-open`.
- **Keyring:** Secret Service is usually absent in WSL2; the `0600` credentials file is the normal path there.
- **systemd is not required.**
- **Time:** large clock skew breaks JWTs; `doctor` checks it.

### 11.2 Install and update

`curl -fsSL https://<your-domain>/install.sh | sh` → ensure `uv` → `uv tool install m2c` → `m2c doctor`. The script must be readable, print what it will do, and avoid `sudo` (it tells the user which package-manager command to run themselves for `ripgrep` and `bubblewrap`). Updates: `m2c update` and a gentle "new version available" notice. Support `pipx` for people who prefer it.

### 11.3 Trust copy (use consistently in the app, the docs and the web Devices page)

> **Where your data lives.** Your project files, session history, memory and settings are stored on your device. When you ask M2C to work, the relevant code and conversation are sent to our servers and to our model providers so the model can answer; we don't keep that content after the run ends. We keep only usage numbers (which model, how many tokens, when) so we can apply your plan's limit across the web app and M2C. You can revoke any device at any time.

### 11.4 What the server may and may not log

May log: user ID, device ID, opaque run ID, model, token counts, credits, status codes, durations, error codes. **May not log:** prompts, file contents, file paths, command lines, tool outputs, or exception messages that contain them (use your existing `error_sanitizer.py`). Q06 enforces it.

### 11.5 Shared cap behavior (so the web app and M2C feel consistent)

- One pool; both surfaces call the same `check` and `commit`.
- At 80% both show a warning; at 100% both pause with the same message and the same reset date.
- Per-run ceiling is separate from the pool; "grant more" raises the run ceiling only, never the pool.

### 11.6 Reuse from MiniLocker (the `draft` repo)

MiniLocker is your hackathon project: a Docker-based agent sandbox with a policy engine, an injection scanner, a hash-chained ledger and an attack suite. It was reviewed at commit `54520a2`. It is a **source of parts, not a base** (D12). M2C runs on the user's own machine inside `bubblewrap` (§O3, C11); MiniLocker runs the agent inside a Docker container on a server, so its sandbox, egress proxy, control-plane API, artifact store and UI do not carry over.

Rules for any reuse:

1. **Copy, do not depend.** Port the module and its tests into the package that owns the WP, add a header comment naming the source file and commit (`Adapted from MiniLocker 54520a2, minilocker/<path>`), and make no runtime import from the draft repo.
2. **The WP's own *Done when* is the gate.** Ported code that passes MiniLocker's tests but not this WP's tests is not done.
3. **Check the hackathon's rules on reuse** before the first copy (D12).
4. **One module per patch** (§0.2), so a bad import is easy to revert.

| MiniLocker module | Used in | What to take | Why it is not a drop-in |
|---|---|---|---|
| `llm/toolcalls.py`, `llm/bakeoff.py` | S05 | Tolerant tool-call parsing; the bake-off as the basis of the 20-call smoke script | Its client does not stream; the streaming adapter is new work |
| `policy/injection.py` | C17 | Invisible-character stripping, injection scan, nonce-fenced wrapper for untrusted text, the taint-floor idea | The scan is a signal, not the control; tune it against the Q03 fixtures |
| `ledger/chain.py` | C02 (optional) | Hash-chained event log; tolerates a torn final line | Not signed or anchored: it detects edits and does not prevent a full rewrite, so the trust pages (X05) must say so |
| `policy/engine.py` | C06 (tests only) | Rules and cases as bypass tests for the C06 table | Regex scoring, unparseable syntax scored low, no `$(...)` or backtick parsing; C06 must fail closed |
| `attacks/` catalog | Q03, C11 tests | The 13 attacks as red-team fixtures | Written for Docker paths and its egress proxy; rewrite for bubblewrap and the CONNECT proxy |
| `scenarios/` runner | Q02 | Hidden-test verifier, repeated runs, 95% interval | It drives MiniLocker's own loop; Q02 drives `m2c -p` |
| `sandbox/browser_worker.py`, `attacks/browser_attacks.py` | Menux D01 | URL-scheme refusal, page text returned as data, hostile-page attacks as tests | Runs inside a Docker container; Menux uses a dedicated Playwright profile and the proxy allowlist |

**Not reused:** the Docker sandbox and its container lifecycle, the egress proxy, the control-plane API, the artifact store and the frontend. If server-side code execution is ever added (this plan has none), revisit.

Size labels in §14 are unchanged. Reuse is a head start, not a reason to shrink an estimate before a port has actually passed its WP's tests.

### 11.7 Prior art, outside references and what M2C takes from them (revision 1.2)

**The rule (D13).** M2C may learn from public documentation, public changelogs, observable behavior, and code under a licence that has been read and recorded. It may not use leaked, unlicensed or source-unavailable code, including a copy that someone re-uploaded under an MIT or other licence (the uploader cannot license what they do not own), and it may not be written as a close rewrite of such code. A repository that republishes another company's proprietary source is not a reference, however it is labeled. If such material is seen by accident, stop, copy nothing from it, and tell the owner. The product is meant to be shipped and sold, so the right to ship matters more than any feature.

**What was compared (2026-11-14).** The official public Claude Code repository (the changelog, example settings, one example hook, and a few small plugins; it contains no application source) against the M2C code. The comparison is limited to what that changelog and those examples say exists; Claude Code itself was not run. Two repositories that republish its proprietary source were deliberately not used.

| Area | M2C today | Public Claude Code | What M2C takes |
|---|---|---|---|
| Core tools, plan mode, checkpoints and rewind, folder trust | Built | Present | Nothing; M2C's fail-closed checks and tests are already strong |
| Permission rules | `tool(pattern)` allow and deny, deny wins | Same shape, plus a long history of rule-matching fixes | **C25** (D16) and **Q07**: turn that history into M2C tests |
| Sandbox | `bubblewrap` plus a proxy | Present; sandboxed commands follow the normal permission flow by default, auto-allow is opt-in | **D17** |
| Hooks | Not built (C13) | A major area | **D15**: the contract, tighten-only |
| Skills, slash commands, plugins | Not built (C14, later C22) | Present | C14 notes on unattended use; plugins stay out of scope |
| MCP | Not built (C23, Phase 5) | A major area | **D18**: local only; the backend client is a protocol reference |
| Subagents, background agents | Not built (L02, C16) | Present | L02 notes (own model and budget, truncated output) |
| Compaction | Mechanical only (S08) | Present | L03 notes (never drop recent turns after a crash; react to context-too-long) |
| Worktrees | Not built (C19) | Present | C19 notes (sandbox must protect the shared git directory) |
| Web search and fetch | Not built (C17); a Tavily and Exa helper exists on the server | Present | C17 note: reuse the server helper |
| Organization settings | `managed` layer is empty (C06) | MDM examples; strict and HIPAA presets | **C27** |
| Headless and service use | `-p` with exit codes | `-p`, an SDK, service exit codes | **C28** |
| IDE, LSP, notebooks, scheduled tasks | Not planned yet (ACP is C18; LSP is L08) | Present | Backlog (feature guide §18) |

**Existing reuse inside the repository.** The backend already has an MCP client (`backend/eo/mcp_client.py`, JSON-RPC over stdio and HTTP), a server-side skill library (`backend/eo/skill_library.py`) and a web-search helper (`backend/utils/web_search.py`, Tavily then Exa). They were built for the web agents, not for M2C: the first two run on the server, where M2C needs the work done on the device. Use them as reference for protocol handling and fixtures, then write the client-side versions inside the owning WP. The same rule as MiniLocker (§11.6) applies: copy by patch, name the source in a header, and let the WP's own *Done when* decide.

---

## 12. Tests and commands

| Area | Command | Notes |
|---|---|---|
| Backend | `cd backend && pytest tests/unit tests/integration -v` | Matches your CI; real-DB tests need `TEST_DATABASE_URL` |
| Backend static | `cd backend && pytest tests/static -v` | SQL-versus-grants test (B01) |
| Frontend | `cd frontend && npm test && npx next lint && npx next build` | `npm test` arrives with B11 |
| Client | `cd m2c && pytest` | Sandbox tests skip loudly if `bwrap` is missing |
| Protocol | `python protocol/validate.py` | Also in CI |
| Evals | `python -m evals.m2c.run --suite golden` | After Q02; costs real money, run on demand |
| Red team | `pytest m2c/tests/redteam -v` | After Q03; blocks release |
| Canary | `pytest backend/tests/integration/test_no_content_at_rest.py` | After Q06; blocks release |
| Bypass corpus | `pytest m2c/tests/redteam/bypass_corpus -v` | After Q07; blocks release (revision 1.2) |
| Docs drift | `pytest m2c/tests/docs -v` | After Q08 (revision 1.2) |
| Crash and resume | `pytest m2c/tests/runner m2c/tests/store -v` | Includes the Q09 fault-injection cases (revision 1.2) |

---

## 13. Risks of the build itself, and stop-the-line rules

**Stop the line (do not generate more patches until fixed):** the base test suite is red; the docs drift check (Q08) is red; a policy or sandbox bug is fixed without a new row in the Q07 corpus; a patch weakens a security check; the canary or red-team test fails; a migration number is used twice; two applied patches disagree about the protocol.

| Risk | Mitigation |
|---|---|
| Parallel patches conflict | Conflict map (§3.4); regenerate rather than hand-edit hunks |
| Client and server drift | One protocol directory, golden fixtures, byte-equality CI check |
| Model-generated patches drift in style | Prompt template (§0.3), small WPs, tests first |
| Scope creep | Phase gates; Phase 5 and 6 items stay off the board until M2 |
| The sandbox does not work on some setups | `doctor` probes and honest refusal; document tested environments |
| Solo-founder capacity | Waves are the ceiling, not the target; Phase 0 and Phase 1 are the minimum viable proof |
| Cost surprises during testing | Per-run ceilings from S10 from day one; dev keys until M2 |
| Trust claim becomes untrue | Q06 canary test and the §11.4 logging rule |
| Imported code carries the wrong assumption | Reuse is by copy (D12); the WP's own *Done when* tests and the C06 fail-closed rule decide, not the source project's tests |
| Code from an unlicensed or leaked source reaches the product | D13: use public docs, changelogs and observed behavior only; reviewers ask "where did this come from?" for any large new module; provenance header on anything copied (D12) |
| Docs and code drift apart (the README, the tool table and the plan already did) | Q08 in CI; update the README in the same patch that adds a command; keep `PATCHES.md` |
| A hook, skill or MCP server widens what the agent may do | D15 (tighten only), D17, D18; Q07 and Q03 cases; project extensions only after the folder-trust prompt |

---

## 14. Work-package index

| ID | Title | Phase | Wave | Depends on | Size |
|---|---|---|---|---|---|
| B00 | Baseline check | 0 | – | – | S |
| B01 | Real-DB tests for code files | 0 | 1 | – | M |
| B02 | Pyodide self-hosting (patch exists) | 0 | 1 | – | M |
| B03 | Remove Python Run from preview | 0 | 1 | – | S |
| B04 | Guard Promote | 0 | 1 | – | S |
| B05 | Board race fix | 0 | 2 | B04 | S |
| B06 | Readable validation errors | 0 | 1 | – | S |
| B07 | Dev CORS origins | 0 | 1 | – | S |
| B08 | Chat-artifact runner hardening | 0 | 2 | B02 | M |
| B09 | Remove Terminal panel | 0 | 1 | – | S |
| B10 | Remove Local folder mode | 0 | 2 | B06, B09 | M |
| B11 | Frontend tests and CI | 0 | 2 | B02 | S |
| B12 | Pyodide bump (optional) | 0 | 3 | B02, B08, B11 | S |
| AUD1–6 | Audits of remaining Build areas | 0 | 1 | – | S each |
| P00 | Protocol and tool-schema contract | 1 | 1 | – | S |
| S01 | Shared usage ledger and plans | 1 | 1 | – | L |
| S02 | Credit weighting | 1 | 2 | S01 | S |
| S03 | Device pairing and credentials | 1 | 1 | – | L |
| S04 | Device socket and handshake | 1 | 2 | P00, S03 | M |
| S05 | Model adapter with tool use | 1 | 2 | P00 | XL |
| S06 | Run manager and ephemeral buffer | 1 | 3 | S04 | L |
| C01 | Client skeleton and doctor-lite | 1 | 1 | – | M |
| C02 | Local store | 1 | 2 | C01 | M |
| C03 | Login client | 1 | 2 | C01, S03 | M |
| C04 | Device link client | 1 | 3 | C01, P00, S04 | M |
| X01 | Devices page | 1 | 2 | S03 | M |
| X02 | Usage panel | 1 | 3 | S01 | S |
| I01 | Walking skeleton | 1 | 4 | S01, S04, S05, S06, C03, C04, X01 | M |
| S09 | Server tool broker | 2 | 5 | S04, S06, P00 | M |
| C05 | Local tools v0 | 2 | 5 | C01, P00 | L |
| C06 | Policy engine v0 | 2 | 5 | C01 | L |
| C12 | Instructions, rules, memory | 2 | 5 | C01 | M |
| C10 | Headless mode | 2 | 5 | C04 | S |
| S07 | Agent loop v0 | 2 | 6 | S05, S06, S09 | XL |
| C07 | Shell tool v0 | 2 | 6 | C06 | M |
| C08 | Checkpoints and rewind | 2 | 6 | C02, C05 | M |
| S08 | Context assembler v0 | 2 | 7 | S07 | M |
| S10 | Metering in the loop | 2 | 7 | S01, S02, S07 | M |
| C09 | Terminal UI v0 | 2 | 7 | C04–C08, C12 | L |
| I02 | First real task (M0) | 2 | 8 | Phase 2 | M |
| C11 | Sandbox and network proxy | 3 | 9 | C07 | XL |
| C13 | Hooks | 3 | 9 | C06 | M |
| C14 | Skills | 3 | 9 | C06 | M |
| C15 | Secrets and redaction | 3 | 9 | C06 | M |
| L01 | ask_user, tasks, plan_exit | 3 | 9 | S07, C09 | M |
| L02 | Subagents | 3 | 9 | S07 | L |
| L03 | Compaction v1, memory, scratchpad | 3 | 9 | S07 | M |
| L04 | Verification loop, Stop hooks | 3 | 9 | S07, C13 | M |
| S11 | Server hardening, process split | 3 | 9 | S06 | L |
| Q01 | CI for new packages | 3 | 9 | M0 | S |
| Q02 | Eval harness | 3 | 9 | M0 | L |
| Q03 | Red-team suite | 3 | 9 | M0 | L |
| Q06 | No-content canary test | 3 | 9 | S06 | M |
| C25 | Safe "always allow" and rule hygiene | 3 | 9 | C06, C09 | S |
| Q07 | Policy and sandbox bypass regression corpus | 3 | 9 | C06, C11, C25 | M |
| Q08 | Docs and catalog drift check | 3 | 9 | – | S |
| Q09 | Crash, resume and truncation integrity tests | 3 | 9 | C02, C08, C09 | S |
| C16 | Background shell | 3 | 10 | C11 | M |
| C17 | Web tools and taint | 3 | 10 | C06, C11 | L |
| I03 | M1 acceptance | 3 | 10 | Phase 3 | M |
| C20 | Pull and push client | 4 | 11 | C02 | M |
| X03 | Handoff server and banner | 4 | 11 | C20 | L |
| X04 | Live remote view | 4 | 11 | S06, S07 | L |
| L05 | Review and security-review | 4 | 11 | L02 | M |
| L06 | Plan chains and escalation | 4 | 11 | S07, Q02 | M |
| C21 | Full doctor | 4 | 11 | C11 | S |
| S12 | Beta allowlist and billing hooks | 4 | 11 | S01 | M |
| Q04 | Device-link security review | 4 | 11 | C11 | M |
| C28 | Streaming headless output for delegation | 4 | 11 | C10, L01 | S |
| I04 | M2 beta acceptance | 4 | 12 | Phase 4 | M |
| C18, C19, L07, L08, C23, S13 | Phase 5 items | 5 | 13+ | per WP | L each |
| C27 | Managed settings and policy presets | 5 | 13+ | C06, C26 | M |
| C22, X05, X06 | Release items | 6 | 13+ | Phase 5 | M each |

**Added during the build (done; not in the counts above).** C24 device tool runner · C26 folder-trust prompt and `m2c trust` · S14 message router and emitter · S15 switch of the server to the real loop. Sub-patches C09a/b, C10b, C11a/b, S07b and L01a are splits of WPs already in the index.

---

## 15. Your first week (a concrete start)

1. **Day 1:** run B00 (baseline). Lock decisions D1–D7. Commit `item3_pyodide_selfhost.patch` (B02) if it is not on `main`.
2. **Generate Wave 1 in parallel**, each in its own worktree: B01, B03, B04, B06, B07, B09, P00, S01, S03, C01, plus AUD1–AUD6 as read-only tasks. Apply in this order: B07, B06, B03, B04, B09, B01, P00, C01, S03, S01 (S01 last because it touches the most shared code).
3. **Then Wave 2:** B05, B08, B10, B11, S02, S04, S05, C02, C03, X01.
4. **Aim for I01 (the walking skeleton).** When "hello" streams back from your own server to your own terminal and the web app shows the usage, the architecture is proven and the rest is incremental.

## 16. Your first week back (2026-11, revision 1.2)

The original §15 stays as the record of how the build started. This is how to restart from where the code is now (§0.6).

1. **Day 1: confirm the ground.** Run `cd m2c && pytest`, the codeagent tests, `python protocol/validate.py` and CI. Correct any wrong row in §0.6, then save it as `PATCHES.md` (§0.4) so the next session starts from a log and not from a guess.
2. **Day 1: fix the README.** It still says the client can only do `doctor`, `login` and `logout`. List the commands and flags that exist, the three runtime dependencies (D14) and the exit codes. Q08 keeps it right afterwards.
3. **Wave 9, next patches, in this order:**
   - **C25** (safe always-allow, `/why`): small, and everything else that touches rules builds on it.
   - **Q08** (docs and catalog drift check): small and independent, so it can go in at the same time.
   - **C13** (hooks, D15), then **Q07** (bypass corpus), which should include the hook cases.
4. **Then:** C14 (skills), L03 (finish compaction), L04 (verification loop and Stop hooks, which needs C13), L02 (subagents), then Q03 (seeded from Q07), Q06 (check the canary covers M2C), Q02 (golden tasks), Q09 (crash and resume), S11 and C16, C17 (web tools, taint), and last I03.
5. **Hold the gate.** Do not start Phase 4 before I03 passes: the two-week dogfood from I02 and the red-team and canary suites green. C28 (streaming output) is the first Phase 4 patch because Menux's delegation (`MT-A07`) needs it.
6. **Stop-the-line additions (revision 1.2):** the docs-drift check is red, or a policy or sandbox bug is fixed without a new row in the Q07 corpus.

*End of the build guide.*
