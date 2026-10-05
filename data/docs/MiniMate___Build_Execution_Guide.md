# MiniMate — Build Execution Guide

### From "MiniMake is done" to a personal automation system: ordered, parallelizable, patch-sized work packages

*Version 1.0 · 2026-10-02 · companion to `minimate_guide.md` (what to build), `minimake_build_plan.md` (how MiniMake is built, whose patch workflow this guide reuses) and `minimake_guide.md`. Where this guide and `minimate_guide.md` disagree, **this guide wins** (§2).*

---

## 0. How to use this guide

The patch workflow is the one in `minimake_build_plan.md` §0 (one work package = one patch, tests first, git worktrees for parallel patches, apply in wave order, log in `PATCHES.md`, regenerate rather than hand-edit hunks, stop-the-line rules in §13 there). Differences for MiniMate:

- **IDs use the prefix `MT-`** (for example `MT-N02`). Patch files: `MT_N02_scheduler.patch`, kept in `patches/`.
- **Most new code lives in new packages** (`minicore/`, `minimate/`, `backend/mate/`), so conflicts are rare; §4.4 lists the few shared files.
- **I have not seen your finished MiniMake code.** This guide assumes the module layout from `minimake_build_plan.md`. The **first patch (MT-K00) is a read-only inventory** that records the real paths and APIs; every later patch should be told to read that inventory first. If reality differs from this guide, fix the inventory, not the plan.

**Prompt template** (copy; fill the brackets):

```
You are generating ONE patch for the MiniMe repo at commit [SHA].
Work package: [MT-ID — title] from minimate_build_plan.md.
Read first: docs/minimate/minimake_inventory.md (real paths and APIs), that WP, §2
(Overrides) and §[cross-cutting] of minimate_build_plan.md, and sections [..] of
minimate_guide.md.
Constraints: touch only [files]; follow existing code style and docstring conventions;
no new dependency unless the WP lists it; security checks fail closed, metering and
telemetry fail open; MiniMake behavior must not change (run its tests).
Process: read and list findings → write tests first → implement → run [commands]
before and after → output one unified diff MT_[ID]_[slug].patch that applies with
`git apply` on [SHA]. List each "Done when" item with evidence. If the WP is wrong
against the real code, STOP and report.
```

**Size labels:** S (one focused session) · M (a few) · L (about a week of patch rounds) · XL (split it if the model struggles).

---

## 1. Preconditions: what must already exist from MiniMake

MiniMate is a second *profile* on the MiniMake engine. Start only when MiniMake has at least reached **M2 (invite-only beta)**. If any row is missing, build the MiniMake WP first.

| MiniMate needs | MiniMake WP | Used for |
| --- | --- | --- |
| Protocol contract and golden fixtures | P00 | Extending the protocol additively |
| Shared usage ledger with `surface in (web, minimake, minimate, system)`, credits, pool check | S01, S02, S10 | One account, one cap |
| Device pairing, JWT, revocation | S03, C03 | Same login and device |
| Device socket, resume, run manager, ephemeral buffer | S04, S06, C04 | Runs started by the node |
| Provider adapters with tool use | S05 | Brain calls |
| Server loop with a **profile** field, tool broker, context assembler | S07, S08, S09 | Automation runs |
| Server hardening: Redis-backed state, process split, per-user limits | S11 | Many scheduled runs |
| Local store (SQLite), checkpoints | C02, C08 | Local run history and file safety |
| Policy engine (modes, rules, shell parsing, protected paths) | C06 | Basis for tiers |
| Sandbox (bubblewrap), network proxy with allowlist, doctor | C11, C21 | Running anything untrusted |
| Secrets redaction, sanitized environment | C15 | Every outgoing result |
| Hooks, skills loader, instructions and memory loader | C13, C14, C12 | Reused and extended |
| Web tools with taint tracking | C17 | Unattended taint rules |
| Local MCP client with trust levels and tool search | C23 | Connector host |
| Subagents, ask-user and tasks tools, compaction | L01–L03 | Planner and loop quality |
| Review and security-review roles wired in | L05 | Skill draft review |
| Live relay (not stored) from device to browser | X04 | Inbox in the web app |
| Devices page and Usage panel | X01, X02 | Extended for MiniMate |
| Eval harness, red-team suite, no-content canary | Q02, Q03, Q06 | Extended for automations |
| Beta allowlist and plan hooks | S12 | Gate MiniMate |

---

## 2. Overrides: what changed since the MiniMate product guide

Your requirements (data stays on the device, one account and one cap, Linux and WSL2) change several choices in `minimate_guide.md`. **These override it.**

### O1. Topology: the local node is the gateway and the scheduler

The product guide described a server-side gateway, scheduler and cloud sandbox. Under local-first that moves:

| Piece | Where it runs | Why |
| --- | --- | --- |
| Scheduler, triggers, automation specs, run history | **Device (the "node")** | Specs and history are user data |
| Connector tokens and the credential vault | **Device** (OAuth loopback flow; never sent to the server) | Trust |
| Channels (Telegram first) | **Device**, talking outbound with the user's **own bot token** (long polling), so no public endpoint and no server involvement | Works behind NAT; content never needs to reach us |
| Memory, skills, knowledge index, approvals | **Device** | Trust |
| Tool execution (files, shell, browser) | **Device**, sandboxed | Trust |
| The "brain" per run, the Planner, review roles, metering, per-user limits | **Server** (as MiniMake) | The paid, orchestrated part |
| Inbound **webhooks** (public URL needed) | **Server relay** that forwards a signed payload to the device and keeps nothing after delivery (short TTL queue in Redis) | The only inbound content the server touches |
| Browser inbox, automations list, approvals | **Live relay** from the device (nothing stored), the same mechanism as MiniMake's remote view | Trust |
| Cloud sandbox and server-held automations | **Not in v1.** Possible later as an explicit, opt-in "MiniMate Cloud" (see D12) | It requires storing credentials and specs on our servers |

Data placement table (extends MiniMake O1):

| Where | What |
| --- | --- |
| **Device (truth)** | Automation specs, run events, approvals, memory files, skills, knowledge index, connector tokens (vault), channel tokens, settings, audit log |
| **Server, persistent, content-free** | Account, devices, usage ledger (`surface='minimate'`: numbers and opaque IDs), webhook registry (webhook ID, device, secret hash) |
| **Server, ephemeral content** | In-flight run buffer (as MiniMake), webhook payload queue (TTL, deleted on delivery) |
| **Third parties** | Model providers (prompt content per request); **Telegram** (messages to the user's bot pass through Telegram); any connector's own service |

### O2. One account, one cap (same as MiniMake)

MiniMate runs burn the **same pool** (`surface='minimate'`). Extra rules for unattended work:

- If the pool is exhausted, scheduled runs are **skipped and the owner is notified once**, never retried in a loop.
- **Per-automation and daily budgets are enforced on the device** (using usage events from the server) because they are the user's own limits; the **pool and per-user rate and concurrency limits are enforced on the server** because they protect you.
- Heartbeats and polls call the model only when a local pre-check says something changed (§MT-A05).

### O3. Platforms, and the WSL2 reality

- **Native Linux:** full feature set.
- **WSL2:** a scheduler is only useful while the WSL instance is running, and **WSL2 stops the instance shortly after the last terminal closes**. Community reports show settings such as `vmIdleTimeout=-1` and `instanceIdleTimeout=-1` help on some versions but not all, and the reliable workaround is a persistent process started at Windows login (for example a scheduled task running `wsl.exe` with a long sleep). I did not test this; confirm against current WSL docs.
  - So MiniMate on WSL2 ships with a **guided keep-alive setup**, and `minimate doctor` warns clearly when it is missing. Missed runs are handled by a spec-level policy (§MT-A04).
  - Be honest in the docs: **automations run only while the WSL instance is up.** For true always-on use, recommend a small Linux machine (a mini-PC or Raspberry Pi) running the node.
- **Desktop control on WSL2 only reaches Linux GUI apps inside WSLg, not Windows applications.** Do not promise Windows automation.
- Windows folders (`/mnt/c/...`) can be granted **read-only by default**, with a warning about speed and permission quirks.
- macOS and native Windows: not supported.

### O4. Packages

- New shared library **`minicore/`** extracted from MiniMake (MT-K01): store, link, auth, policy, sandbox, secrets, hooks, skills loader, instructions and memory loader, tool base classes.
- **`minimake/`** and **`minimate/`** both depend on `minicore`. Two commands, two PyPI names, one installer.
- Server: the loop stays in `backend/codeagent/` (profile-aware); MiniMate-specific server code goes in **`backend/mate/`**.

### O5. Gmail and Google reality (affects the connector plan)

- Reading Gmail is a **restricted** Google scope. Multiple sources agree it requires Google app verification **plus an annual third-party CASA security assessment**; third-party estimates put the assessment at a few hundred to a few thousand dollars a year. Calendar scopes are "sensitive" (verification, no CASA); some Drive scopes are restricted. One source classifies `gmail.readonly` more leniently, so check Google's own scope list before relying on any of this.
- Google also requires restricted-scope apps to meet its **Limited Use** requirements in the privacy policy. Sending a user's mail content to model providers may conflict with those terms. **Ask a lawyer before building the official Google OAuth connectors** (MT-H12).
- **So v1 uses:** IMAP with an app password for email; CalDAV or ICS feeds for calendar; plain files; Telegram; a **bring-your-own OAuth client** option for power users (they create their own Google Cloud project; no verification needed for personal use in testing mode, with its limits). The official Google connector is a Phase 6 business decision.

### O6. Tiers and unattended policy

The T0–T5 tiers and the unattended ceiling (T2) from `minimate_guide.md` §6.7 and §11.2 stand. Mapping to MiniMake's tool risk levels:

| MiniMake risk (per tool) | MiniMate tier (per capability or automation ceiling) |
| --- | --- |
| R0 read-only | T0 observe |
| (derived content) | T1 derive: drafts, summaries in the workspace |
| R1 write inside the workspace | T1–T2 |
| – | T2 notify the owner |
| R3 network or outside project | T3 act externally (reversible) |
| R2 shell, R1 outside grants | T4 change system or data |
| R4 irreversible | T5 |

Rule: **a tool's effective tier is the higher of its MiniMake risk level and the tier its connector declares.**

### O7. The profile

Runs carry `profile: "automation"`, with their own system prompt, tool catalog, default budgets, and `run_kind` (`interactive | scheduled | triggered | heartbeat | delegated`).

### O8. Trust copy for MiniMate (more sensitive than MiniMake)

> **Where your data lives.** Your automations, memory, skills and connector credentials are stored on your device. When an automation runs, the content it needs (for example today's calendar entries and email subjects) is sent to our servers and our model providers to produce the result; we don't keep it after the run ends. If you connect Telegram, messages to your bot pass through Telegram. We keep only usage numbers so your plan's limit applies across the web app, MiniMake and MiniMate. Messages from people you haven't paired are treated as data, never as instructions. You can pause everything with one button.

---

## 3. Decisions to lock before the first patch

| # | Decision | Default | Notes |
| --- | --- | --- | --- |
| D1 | Scheduler | **Own small scheduler on `croniter` with a SQLite job table**, run inside the node | Simple, testable, no heavy dependency |
| D2 | Node run modes | **systemd user service** where available; **foreground `minimate run`** otherwise (WSL without systemd) | `doctor` picks and explains |
| D3 | Vault encryption key | **OS keyring if available, else a passphrase-derived key (prompted at node start), else a `0600` key file flagged "less secure" in `doctor`** | WSL2 usually has no keyring |
| D4 | First channel | **Telegram with the user's own bot** (long polling) | No server involvement |
| D5 | Email | **IMAP + app password**, read and draft only | Google OAuth is D11 |
| D6 | Calendar | **CalDAV / ICS URL** first |  |
| D7 | Spec format | **YAML validated by a JSON Schema** | Same parser on server (Planner) and node |
| D8 | Browser automation | **Playwright (headless Chromium), optional extra install** | Large download; off by default |
| D9 | Embeddings for memory search | **None in v1 (SQLite FTS5 only)** | Embeddings would send content to a provider |
| D10 | Webhook relay TTL | **Delivery within 10 minutes or dropped; max 64 KB** | Content-free persistence |
| D11 | Google OAuth connectors | **Defer; decide after legal advice and budget for CASA** | See O5 |
| D12 | Cloud-hosted automations ("MiniMate Cloud") | **Not in v1; revisit after the beta** | Needs a separate trust model and disclosure |
| D13 | Package and command names | **`minimate`, `minicore`** | Check availability on PyPI and your domain |
| D14 | How MiniMate hands a task to MiniMake | **Local IPC to the installed `minimake` CLI** (headless mode) | Keeps code tasks under MiniMake's sandbox and policy |

---

## 4. The map

### 4.1 Phases and milestones

| Phase | Goal | Ends with | Milestone |
| --- | --- | --- | --- |
| **0** | Foundations | Real inventory of MiniMake; shared core extracted; protocol and profile extended; spec and tier definitions | – |
| **1** | First automation | Cron-scheduled automation on the node → server brain → Telegram message to the owner; metered under `surface='minimate'` | **MT-I01** |
| **2** | Safe unattended | Tiers, unattended policy, approvals, reader/actor split, taint, panic button, inbox, email/calendar/files read | **MT-I02** |
| **3** | Memory, skills, triggers | Memory files and search, poisoning defenses, skills with manifests, skill drafts for review, file/webhook/poll triggers, heartbeat gating | **MT-I03** |
| **4** | Beta | Web inbox and planner chat, delegation to MiniMake, doctor with WSL keep-alive, cost estimates, docs | **MT-I04 (invite-only beta)** |
| **5** | Desktop and voice | Browser profile, AT-SPI, ydotool, headless desktop container, voice, extra connectors | **MT-I05** |
| **6** | Ecosystem and release | Marketplace with scanning and signing, team features, Google connectors (if approved), external audit, packaging | **GA** |

### 4.2 Tracks

| Track | Scope |
| --- | --- |
| **K** | Kernel: inventory, shared core, profile support, protocol additions, UI relay |
| **N** | Node: service, scheduler, run orchestrator, vault, notifier, triggers, doctor |
| **A** | Automations: spec, planner, dry run, lifecycle, budgets, graduation |
| **T** | Trust: tiers, unattended policy, approvals, reader/actor, sealed tools, taint, panic, anomaly |
| **H** | Connectors and the connector host |
| **G** | Gateway and channels |
| **M** | Memory, skills, learning loop |
| **W** | Web app surfaces |
| **D** | Desktop and voice |
| **E** | Server-side economics and abuse controls |
| **Q** | Quality |
| **R** | Release |
| **I** | Integration milestones |

### 4.3 Dependency graph (arrows mean "apply first")

```
PHASE 0   K00 ──► K01 ──► (everything on the node)
          K00 ──► K02 (profile support, server)      K00 ──► K03 (protocol 1.1)
          A01 (spec schema)   T01 (tier model)       (A01, T01 independent)

PHASE 1   K01 ──► N01 ──► N02 ──► N04 ──┐
          K01 ──► N05 (vault)           │
          K01 ──► G01 ──► H01 ──► H03   ├──► I01 (first automation)
          K02+A01 ──► A02 (planner)     │
          A01 ──► A03 (dry run)         │
          N04 ──► A04 (lifecycle)  ─────┘

PHASE 2   T01 ──► T02 ──► T03 ──► G04 ──► W-inbox (K04 first)
          T02 ──► T04, T05, T06     T07, T08
          H02 (connector host) ──► H04, H05, H06
          A05 (budgets, heartbeat gating)    A06 (graduation)
          Q01, Q02, Q04 ──► I02 (safe unattended)

PHASE 3   M01 ──► M02, M03, M06, M07        M04 ──► M05
          N03 ──► H07,  H08 (relay)          G03 (digests)    E01   Q03 ──► I03

PHASE 4   K04 ──► W01..W07      A07 (delegate to MiniMake)     N07 (doctor + keep-alive)
          E02   Q05   R02 (docs)  ──► I04

PHASE 5   D01 ──► D04      D02, D03 ──► D05      D06      H09–H11, H13

PHASE 6   M08 (marketplace) , T09 (team policy), H12 (Google, if approved),
          audit, R01 (packaging), R03, R04 ──► GA
```

### 4.4 Conflict map (files more than one WP touches)

| File(s) | WPs, in order |
| --- | --- |
| `minicore/**` (after MT-K01) | K01 owns the move. Later WPs **add** modules or **extend through registries**, never rewrite existing ones. Any change to `minicore` must pass **both** products' tests |
| `protocol/v1/*` | K03 only (additive); later additions are new files |
| `backend/codeagent/loop.py`, `tools_schema.py` | K02 only: it adds the profile hook and the tool-catalog registry. Everything else registers tools from `backend/mate/tools/*.json` |
| `backend/api/server.py` | K02 adds one `include_router` for `/v1/mate`; later routers are added inside `backend/mate/` |
| `frontend` navigation and the Mate page shell | W01 creates the page and the nav entry; W02–W07 are components inside it |
| `minimate/src/minimate/node/service.py` | N01 → N02 → N04 → N03 → N07 (each extends the node's event loop) |
| `backend/migrations/` | Numbers are **reserved** (§4.5) |

### 4.5 Reserved numbers

| Item | Number |
| --- | --- |
| Migration: webhook relay registry | **0017** (H08) |
| Migration: push-notification subscriptions (optional) | **0018** (W-late) |
| Migration: marketplace catalog | **0019** (M08) |
| Protocol | additive revision **1.1** (K03) |
| Server routes | `/v1/mate/*` (planner, relay, webhooks) |

### 4.6 Waves

| Wave | Patches (parallel) | Needs |
| --- | --- | --- |
| **1** | K00, A01, T01 | MiniMake M2 |
| **2** | K01, K02, K03 | K00 |
| **3** | N01, N05, G01, A02, A03 | K01; K01; K01; K02+A01; A01 |
| **4** | N02, H01, N06 | N01; G01; N01 |
| **5** | N04, H03 | N02+N05; H01+G01 |
| **6** | A04, I01 | N04 |
| **7** | T02, H02 | T01+K01; K01+H01 |
| **8** | T03, T05, T06, T07, H04, H05, H06, A05 | T02; T02; T02; T02; H02; H02; H02; N04+A01 |
| **9** | T04, T08, G02, G04, K04, A06 | T05+N04; T03; G01; T03; K03; A04 |
| **10** | W01, Q01, Q02, Q04 | K04+T03; I01; I01; I01 |
| **11** | I02 | Phase 2 |
| **12** | M01, M04, N03, H07, H08, G03, E01 | K01; K01; N02; N03; K03; G01; N04 |
| **13** | M02, M03, M05, M06, M07, Q03 | M01; M01; M04; M01; M01; I02 |
| **14** | I03 | Phase 3 |
| **15** | W02–W07, A07, N07, E02, Q05, R02 | W01; I01 |
| **16** | I04 (beta) | Phase 4 |
| **17+** | Phase 5 and 6 items | per WP |

---

## 5. Phase 0 — Foundations

### MT-K00 · Inventory of the finished MiniMake · S · Wave 1 (read-only)

*Output (one new file, no code):* `docs/minimate/minimake_inventory.md`. *What:* The patch-writing model reads the repo and records: the real module paths for every item in §1 (store, link, auth, policy engine, sandbox, secrets, hooks, skills, instructions/memory loader, tool classes, MCP client, TUI), their public function and class signatures, the server's profile handling, the tool catalog format, the protocol version and message list, the migration numbers used so far, and the commands to run each test suite. Also record anything from §1 that is **missing**. *Done when:* every §1 row is marked present, partly present or missing with a path; the test commands are verified to run green on the current commit. *Why first:* this guide cannot know MiniMake's final layout, and every later patch depends on the facts in this file.

### MT-A01 · Automation spec: schema, parser, validator · M · Wave 1

*Implements:* product guide §6.2. *Files (new):* `protocol/spec/automation.schema.json`, `minicore/src/minicore/automation/{spec.py,validate.py}` (or `minimate/` until K01 lands), tests, `docs/minimate/automation-spec.md`. *What:* The YAML spec from product guide §6.2: `id`, `description`, `trigger` (cron, interval, heartbeat, file, webhook, poll, message, manual), `agent` (`profile`, `model_class`, `instructions`, `pipeline` for reader/actor), `capabilities` (connector tools, channel tools, folders with `r`/`rw`), `policy` (`tier_max`, `unattended`, `approvals`, `egress`), `budget` (`per_run_credits`, `per_day_credits`, `per_month_credits`), `quiet_hours`, `missed_run`, `notify_on_failure`. JSON Schema plus a validator that adds semantic checks: capabilities must exist in the capability registry (T01), `tier_max` must cover every listed capability's tier, an unattended spec may not list any capability above T2, an unattended spec with untrusted-content tools must declare the reader/actor pipeline, `egress` is a closed list, budgets are positive. *Done when:* valid and invalid fixtures; every semantic rule has a failing test; the same module is importable by the server (Planner) and the node.

### MT-T01 · Tier model and capability registry · M · Wave 1

*Implements:* product guide §11.2; §2 O6. *Files (new):* `minicore/src/minicore/tiers/{tiers.py,registry.py}`, `docs/minimate/tiers.md`, tests. *What:* The T0–T5 enumeration with ordering; a **capability registry** (`capability_id → {tier, read_or_write, egress_domains, description, confirm_phrase?}`); the effective-tier function from O6; a loader for connector manifests (H01). Pure data and functions, no I/O. *Done when:* tests for ordering, effective tier, unknown capability (treated as T5 and denied), and registry loading.

### MT-K01 · Extract `minicore` from MiniMake · L · Wave 2

*Files:* new `minicore/` package; `minimake/` modules moved and replaced by thin re-exports; `pyproject.toml` files; CI. *What:* **Behavior-preserving move.** Using the inventory (K00), move the shared modules (store, link, auth, policy, sandbox, secrets, hooks, skills loader, instructions/memory loader, tool base classes, checkpoints) into `minicore/src/minicore/`. Keep `minimake.*` import paths working with re-exports for one release. No logic changes. *Done when:* **every MiniMake test passes unchanged** (only import lines may differ); `minicore` has its own test suite carrying the moved tests; a new empty `minimate/` package imports `minicore` in CI. *Rule for all later WPs:* additions to `minicore` must keep both products green.

### MT-K02 · Server profile support · M · Wave 2

*Files:* `backend/codeagent/{loop.py,tools_schema.py,prompts.py}` (profile hooks only), new `backend/mate/{__init__.py,router.py,profile.py}`, one `include_router` in `backend/api/server.py`, tests. *What:* `run.start.profile = "automation"` selects: the system prompt (`backend/mate/prompts/automation.md`), the **tool catalog** assembled from `backend/mate/tools/*.json` (initially `connector_call`, `notify_owner`, `read_file`, `list_dir`, `glob`, `grep`, `memory_search`, `memory_write`, `skill`, `tasks`, `ask_user`), default budgets by `run_kind`, and the model class from the spec. Code runs unaffected; add a test that a `profile="code"` run is byte-identical to before. *Done when:* both profiles run through the same loop in tests; unknown profiles are rejected; the MiniMake loop tests pass unchanged.

### MT-K03 · Protocol additions (revision 1.1) · S · Wave 2

*Files:* `protocol/v1/` additive files, fixtures, contract tests. *What:* Additive only: `run.start` fields `run_kind`, `spec_id`, `pipeline_stage`; webhook relay messages `relay.webhook` (server→device: `webhook_id`, `payload`, `received_at`, `sig`) and `relay.ack`; UI relay messages `ui.query` (server→device: `{id, name, args}`) and `ui.reply`; approval events `approval.requested`, `approval.decided`; error codes `automation_paused`, `relay_expired`. New golden fixtures: scheduled run, run skipped for quota, webhook delivery, UI query and reply. *Done when:* all MiniMake fixtures still validate; new fixtures validate; the byte-equality check between `protocol/` and the packaged copies still passes.

---

## 6. Phase 1 — First automation (the walking skeleton)

**Goal:** the thinnest end-to-end automation: the user installs the node, pairs a Telegram bot, describes an automation, and a scheduled run produces a message on Telegram, charged to the shared pool. No email, no memory, no unattended-risk features yet, so the only output is **a message to the owner** (T2).

### MT-N01 · Node skeleton and service · M · Wave 3

*Files:* `minimate/pyproject.toml`, `minimate/src/minimate/{cli.py,node/service.py,node/paths.py,node/config.py}`, `minimate/tests/`. *What:* Commands `minimate init`, `minimate run` (foreground), `minimate status`, `minimate stop`; `minimate service install|uninstall` writing a **systemd user unit** when systemd exists (D2). State under `~/.minimate/` (`0700`): `state.db` (reuses `minicore` store), `automations/`, `memory/`, `skills/`, `logs/`. Single-instance lock; graceful shutdown; sign-in reuses `minicore` auth (same device credential flow, labelled as MiniMate). *Done when:* start and stop are clean; two nodes cannot run at once; `minimate status` shows login state and next scheduled runs; works without systemd via foreground mode.

### MT-N05 · Vault · M · Wave 3

*Implements:* §3 D3; product guide §11.5. *Files:* `minimate/src/minimate/vault/{store.py,keys.py}`, tests. *What:* An encrypted store (`vault.db`, authenticated encryption) for connector and channel secrets. Key sources in order: OS keyring, passphrase-derived (Argon2 or scrypt, prompted at node start and cached only in memory), `0600` key file (flagged "less secure" by `doctor`). Secrets are only ever read by connector code inside the node process; they never go into model context, logs, tool results or the sandbox. `minimate vault add|list|remove` (values are never printed). *Done when:* tests prove ciphertext at rest, wrong key fails closed, secret redaction catches vault values in outgoing text, and a deliberately logged secret is blocked by the redaction filter.

### MT-G01 · Channel abstraction and pairing · M · Wave 3

*Files:* `minimate/src/minimate/channels/{base.py,pairing.py,router.py}`, tests. *What:* A `Channel` interface (`start`, `stop`, `send(owner_text, buttons?)`, `on_message`, `on_callback`) and an **owner pairing** flow: the node shows a one-time code; the owner sends it to the bot; the channel records the owner's account ID. Anyone else is a "stranger" (G02 handles them). Everything the router receives is labelled `trust: owner | stranger`. *Done when:* pairing succeeds once and codes cannot be reused; strangers never reach the run starter.

### MT-A02 · Planner endpoint and client · L · Wave 3

*Files:* `backend/mate/planner.py`, route `POST /v1/mate/plan`, prompt `backend/mate/prompts/planner.md`, `minimate/src/minimate/planner_client.py`, tests. *What:* Stateless server endpoint. Input: the user's plain-language request plus the node's **capability list** (names, tiers, descriptions only, no secrets). Output: a draft spec (A01 format), a plain-language summary, the tier it needs, an estimated credit range, and open questions. The server **validates the draft with the A01 validator before returning** and retries once with the error if invalid. Nothing is stored. Uses the Brain role or the strong class; metered as `minimate` usage. *Done when:* ten scripted requests produce valid specs or specific questions; the validator rejects a deliberately over-privileged draft; no content is persisted (the Q06 canary extended in MT-Q04 covers this).

### MT-A03 · Dry-run engine · M · Wave 3

*Files:* `minicore/src/minicore/automation/dryrun.py` (or `minimate/`), tests. *What:* Run a spec with **all writes simulated**: connector write tools and `notify_owner` return a canned success and record "would do X"; reads use real data (or fixtures in tests). Produces a human-readable report of what would have happened and what it would have cost. *Done when:* a dry run never calls a real write; the report matches the recorded intents.

### MT-N02 · Scheduler · M · Wave 4

*Files:* `minimate/src/minimate/node/scheduler.py`, tests. *What:* Cron, interval and manual triggers on `croniter` with time zones and DST handled; a job table in `state.db`; **missed-run policy** per spec (`run_now`, `skip`, `run_if_recent:<minutes>`) computed at node start and after sleep; jitter to avoid every user hitting the server at :00; dedupe by trigger-event ID. *Done when:* tests with a fake clock cover DST changes, a node that was off, rapid restarts and duplicate events.

### MT-H01 · Connector SDK and manifest · M · Wave 4

*Files:* `minimate/src/minimate/connectors/{base.py,manifest.py,stances.py}`, `docs/minimate/connector-sdk.md`, tests. *What:* A connector declares: name, auth method, tools with JSON Schemas, **per-tool tier**, read/write class, egress domains, rate limits and test fixtures. Per-tool **stances** (`allow | ask | block`) from settings. A uniform `call(tool, args)` entry that validates arguments, applies the stance and tier, injects credentials from the vault, calls out only to the declared domains (through `minicore`'s network proxy), enforces a size cap on the parsed result, and returns it labelled with a trust level. *Done when:* a toy connector passes the whole path; an undeclared domain, an oversize result and a blocked stance each fail in tests.

### MT-N06 · Notifier (minimum) · S · Wave 4

*Files:* `minimate/src/minimate/notify.py`, tests. *What:* Desktop notifications through `notify-send` or D-Bus when available, falling back to the channel; used for failures, approvals waiting and panic. Never includes message bodies when the user has set `channel_detail: minimal`.

### MT-N04 · Run orchestrator · L · Wave 5

*Files:* `minimate/src/minimate/node/runner.py`, tests. *What:* The node-side executor of an automation run: build `run.start` (`profile=automation`, `run_kind`, spec instructions, memory index if any), connect through `minicore`'s link, receive `tool_proposed`, route each call to the right local executor (connector host, file tools, `notify_owner`), apply the policy engine with the **unattended** flag (T02 later; until then only T0–T2 tools are available), send `tool_result`, honor budgets and cancel, write every event to the local store. Handles quota exhaustion (`quota_exhausted` → skip and notify once), disconnects and resume. *Done when:* a scripted fake server drives a full run; cancel kills in-flight tools; budgets stop a run; events land in `state.db`.

### MT-H03 · Telegram channel and connector · M · Wave 5

*Files:* `minimate/src/minimate/channels/telegram.py`, `connectors/telegram/manifest.yaml`, tests with a fake Bot API. *What:* Long polling with the user's bot token from the vault; owner-only sends (`send_to_owner`, with Markdown escaping and length splitting); inline keyboards for approvals (decisions arrive as callback queries with an opaque approval ID and a nonce, accepted only from the paired owner); rate limiting and backoff on API errors. *Done when:* pairing and send work against the fake API; callbacks from non-owners are ignored; the token never appears in logs.

### MT-A04 · Run lifecycle · M · Wave 6

*Files:* `minimate/src/minimate/node/lifecycle.py`, tests. *What:* States `queued → running → completed | failed | skipped | paused | awaiting_approval`; one active run per automation by default (queue or drop per spec); retries with backoff for transient failures; one failure notification per failure episode, not per attempt; a per-automation timeline in the store. *Done when:* tests for concurrency, retry limits, notification de-duplication and restart recovery.

### MT-I01 · First automation (acceptance) · M · Wave 6

*Joins:* K01, K02, K03, N01, N02, N04, N05, N06, G01, H01, H03, A01, A02, A03, A04. *What:* End to end on a real machine with a dev model: `minimate init`, pair Telegram, say "send me a short good-morning message with today's date at 07:30", review the spec and dry run, approve, and watch the scheduled run arrive. Check the shared pool. *Done when:*

- [ ] The Telegram message arrives at the scheduled time; the run is in the local store.
- [ ] A ledger row exists with `surface='minimate'` and the web Usage panel shows it.
- [ ] No automation content exists in Postgres, logs or Redis after the run (Q06 canary).
- [ ] The node restarts mid-day and still runs the next scheduled automation.
- [ ] A skipped run (node off at 07:30) follows the missed-run policy.

---

## 7. Phase 2 — Safe unattended automations

**Goal:** let automations run while nobody is watching, safely. This phase adds everything that makes unattended runs trustworthy **before** any write connector (beyond messaging the owner) is allowed: tiers enforced by code, queued approvals, split agents for untrusted content, taint, a panic button, an inbox, and the first read connectors (email, calendar, files).

> **Gate:** do not enable any tier above T2 for unattended runs until MT-T02 through MT-T08 and the red-team suite (MT-Q02) pass.

### MT-H02 · Connector host (local MCP, stances, trust) · L · Wave 7

*Files:* `minimate/src/minimate/connectors/host.py`, `mcp_bridge.py`, tests. Reuses MiniMake's local MCP client (C23). *What:* Runs connectors as in-process Python plugins or as **local MCP servers** (stdio) under the sandbox, with tool descriptions from non-first-party servers marked untrusted and shown to the user at install; deferred tool schemas (tool search); per-server trust levels; credentials injected from the vault by the host, never passed through the model. *Done when:* a local MCP server's tools appear with correct tiers; an unlisted tool is invisible; a poisoned tool description cannot change a stance (tests with fixtures).

### MT-T02 · Unattended policy layer · L · Wave 7

*Implements:* product guide §6.7, §11.2–11.4. *Files:* `minicore/src/minicore/policy/unattended.py` (extends the C06 decision function), tests. *What:* A decision wrapper used only when `run_kind != interactive`:

1. Only capabilities listed in the spec are visible.
2. Effective tier above the spec's `tier_max` → **deny**.
3. Tier ≤ T2 → allow if the capability is listed.
4. **T3 → queue an approval** (never auto-allow, never ask interactively).
5. **T4 and T5 → deny** in unattended runs.
6. Any "ask" from the base policy becomes "queue or deny", never a blocking prompt.
7. **Fails closed** on any error. *Done when:* a table-driven test over every tier and run kind; a removed capability can never be reached by a model that names it directly; no path turns an unattended "ask" into "allow".

### MT-T03 · Approvals store and decision flow · M · Wave 8

*Files:* `minimate/src/minimate/approvals/{store.py,flow.py}`, tests. *What:* Approvals live in `state.db`: `id`, `run_id`, automation, capability, **exact content** (draft text, command, diff), tier, `expires_at` (default 24 h), `status`. Flow: a T3 call creates an approval and pauses *that call only* (the run may continue other work or finish with the action pending). Decisions: approve once, approve and remember this exact action, edit then approve, deny, deny and pause the automation. On approve the node **re-checks the policy** immediately before executing. Expiry means skipped and logged. Decision sources: local CLI, desktop notification actions, channels (G04), web inbox through the UI relay (K04) with the same nonce checks. *Done when:* tests for expiry, double decisions, replay of an old approval ID, edits changing the content hash (an edited approval needs a fresh decision), and approval after policy change (denied).

### MT-T05 · Sealed tool endpoints · M · Wave 8

*Files:* `minimate/src/minimate/sealed/{notify_owner.py,draft_reply.py}`, tests. *What:* Fixed-schema tools with hard-coded targets: `notify_owner(text)` (recipient is always the paired owner), `save_report(name, markdown)` (writes only inside the workspace folder), `draft_reply(thread_ref, text)` (creates a **draft** in the user's own mailbox; cannot send). No tool at tier ≤ T2 accepts a free-form recipient, URL or path. *Done when:* fuzz tests try to smuggle a recipient, URL or path through each argument and fail.

### MT-T06 · Taint for unattended runs · M · Wave 8

*Implements:* product guide §11.3(5); reuses MiniMake's taint state (C17). *Files:* `minicore/src/minicore/policy/taint_unattended.py`, tests. *What:* A run becomes tainted when any tool result carries `trust: external` (inbound mail bodies, fetched pages, shared documents, a stranger's message). Once tainted: every egress-capable or external-write tool becomes **deny** (not ask), the tainted flag and cause are recorded in the run timeline, and the final summary tells the owner. A reader/actor pipeline (T04) is the supported way to use untrusted content *and* act. *Done when:* the poisoned-mail fixture cannot cause any outbound action; the flag appears in the timeline.

### MT-T07 · Panic button and kill switch · S · Wave 8

*Files:* `minimate/src/minimate/panic.py`, CLI `minimate panic`, tests. *What:* One action: stop all runs, mark every automation disabled, drop the vault key from memory (the vault locks until re-unlocked), optionally revoke the device token. Reachable from the CLI, a desktop notification action, a Telegram command from the owner, and (K04) the web button. Everything it did is logged. *Done when:* after panic no run starts, no connector call can decrypt a secret, and resume requires an explicit unlock.

### MT-H04 · Email connector (IMAP: read and draft) · L · Wave 8

*Files:* `minimate/src/minimate/connectors/imap/*`, manifest, tests with a fake IMAP server. *What:* App-password IMAP (D5). Tools: `search` and `read` (T0, results marked **untrusted** and tainting), `list_folders`, `create_draft` (T2, in the user's own Drafts folder; the connector has **no send tool**). Read results are size-capped and stripped of active content; attachments are not fetched in v1. *Done when:* the injection fixtures (hidden instructions in headers, HTML and plain bodies) are delivered to the model only as labelled data; no code path can send mail.

### MT-H05 · Calendar connector (CalDAV and ICS) · M · Wave 8

Read events (T0), free-busy summary, no write in v1. Event titles and descriptions are untrusted text. *Done when:* works against a local CalDAV test server and a static ICS file.

### MT-H06 · Local files connector · M · Wave 8

Folder grants with `r` or `rw` modes stored in settings; reuses MiniMake's path guard and the two-form denylist; `/mnt/c` grants default to `r` with a warning. Tools: list, read, search, write (T1, inside `rw` grants only, with checkpoints from C08). *Done when:* traversal, symlink and denylist tests pass.

### MT-A05 · Budgets and heartbeat gating · M · Wave 8

*Files:* `minimate/src/minimate/node/budgets.py`, `heartbeat.py`, tests. *What:* Per-run, per-day and per-month credit budgets from the spec, tracked locally from the server's `usage` events; at 80% warn, at 100% pause the automation and notify. **Heartbeat:** a cheap local pre-check script list (new priority mail? calendar change? disk over 90%?) runs first; the model is called only if a check reports a change or the checklist has content; quiet hours and a daily beat cap apply. Default interval 60 minutes. *Done when:* tests prove that an unchanged world costs zero model calls, that budgets pause correctly, and that a node restart does not reset the day's spend (it is rebuilt from the local store).

### MT-T04 · Reader/actor split runtime · L · Wave 9

*Implements:* product guide §11.3(1)–(3). *Files:* `minimate/src/minimate/node/pipeline.py`, server prompts `backend/mate/prompts/{reader,actor}.md`, tests. *What:* For specs that declare `pipeline: [reader, actor]`, the node runs **two separate runs**. The **reader** run has only untrusted-content read tools and **no egress or write tools**; it must return JSON that matches a schema in the spec, size-capped and sanitized (strip URLs and markup unless the schema allows them). The **actor** run receives only that structured result plus the owner's instructions, and only sealed T2 tools. Fixtures show the limit: structured fields can still carry an injection, so the actor never gets a free-form send or path tool. *Done when:* the injection corpus run through the pipeline produces no unapproved outbound action; a reader attempting to call a write tool is denied.

### MT-T08 · Anomaly detection · M · Wave 9

Local heuristics: repeated denies, a tool the automation has never used, cost above three times its median, run time above three times its median, an unexpected stranger message burst. Action: pause the automation and notify once. *Done when:* replayed anomalous timelines trigger and normal ones do not.

### MT-G02 · Stranger handling and rate limits · S · Wave 9

Strangers' messages are stored as **data** (optionally summarized for the owner on request), never routed to a run starter; per-sender rate limits; a block list. *Done when:* a stranger message cannot start a run, change settings or approve anything.

### MT-G04 · Approval buttons over channels · S · Wave 9

Telegram inline buttons for T03 decisions with `channel_detail: minimal` (a ping that says an approval is waiting, details viewed locally or in the web inbox) or `full` (the exact content in the chat). The trust copy states that full details pass through Telegram. *Done when:* callbacks validate owner, nonce and expiry.

### MT-K04 · UI relay (device queries from the browser) · M · Wave 9

*Files:* `backend/mate/relay_ui.py`, route `POST /v1/mate/relay/query`, node handler `minimate/src/minimate/node/ui_handler.py`, tests. *What:* The browser asks the **server**, the server forwards a `ui.query` to the owner's connected device, the device answers with `ui.reply`, and the server passes it through **without storing it**. A fixed whitelist of query names (`automations.list`, `automation.get`, `runs.recent`, `approvals.pending`, `approval.decide`, `memory.list`, `skills.list`, `usage.local`, `panic`). Device offline returns a clear "device offline" result. Rate limits; owner session only. Extends MiniMake's live relay (X04). *Done when:* nothing from replies appears in Postgres, Redis (after delivery) or logs (Q06); an unlisted query name is refused; a different user cannot query someone else's device.

### MT-A06 · Versions and graduation · M · Wave 9

*Files:* `minimate/src/minimate/node/graduation.py`, tests. *What:* Spec versions (every change creates a new version; rollback). New automations start **attended** (outputs go to the owner for review) for N clean runs (default 5); then the node proposes **graduation to unattended** showing the exact policy. Any change to capabilities, tier or egress resets the trial. *Done when:* tests for the state machine and for capability changes resetting graduation.

### MT-W01 · Mate page and inbox (web) · L · Wave 10

*Files:* a new Mate page and navigation entry; components for **Needs you**, **Running now**, **Recent**; tests. *What:* Reads through the UI relay (K04). Approval cards show what, exact content, which automation, tier, and what happens if nothing is done; buttons per T03. Clear states for "device offline" and "no device paired". *Done when:* an approval raised on the device can be decided from the browser; offline behavior is understandable; node tests, lint and build pass.

### MT-Q01 · Automation eval harness · L · Wave 10

Fixture-driven runs (fake mailbox, calendar and files) of the sample automations in a sandbox, with graders and cost capture; records success, steps, credits, heartbeat skip rate. Extends `backend/evals/` and MiniMake's harness (Q02).

### MT-Q02 · Red-team suite v2 · L · Wave 10

Fixtures for injection through mail (headers, HTML, hidden text, calendar invites), filenames and document metadata, MCP descriptions, stranger messages, memory poisoning (added in Phase 3), skill exfiltration with canary secrets, vault extraction attempts, sandbox escapes, and heartbeat abuse. **A release is blocked if any "no unapproved egress, no external write, no secret read" test fails.**

### MT-Q04 · Canary test, extended · M · Wave 10

Extend MiniMake's no-content-at-rest test (Q06) to MiniMate: planner requests, run buffers, webhook relay, UI relay, ledger, logs and error reports must never contain canary content after the operation completes.

### MT-I02 · Safe unattended (acceptance) · M · Wave 11

- [ ] Morning brief (calendar plus mail subjects through the reader/actor pipeline) runs unattended for a week and messages only the owner.
- [ ] A poisoned email cannot cause any outbound action (red-team green).
- [ ] An attempted T3 action creates an approval that can be decided on Telegram and in the web inbox; expiry works.
- [ ] Panic button stops everything and locks the vault.
- [ ] Budgets pause an over-budget automation; the shared pool and per-surface usage agree.
- [ ] Canary test green.

---

## 8. Phase 3 — Memory, skills and triggers

### MT-M01 · Memory files and search · M · Wave 12

*Implements:* product guide §7. *Files:* `minimate/src/minimate/memory/{files.py,index.py,tools.py}`, tests. *What:* Plain Markdown under `~/.minimate/memory/`: `MEMORY.md` (durable facts), `USER.md` (preferences), `daily/YYYY-MM-DD.md` (append-only). A **SQLite FTS5 index** (D9) over all of it. Tools `memory_search`, `memory_read`, `memory_write` for the automation profile. Every automatic write is shown to the owner with an undo. Secrets and sensitive categories are not auto-saved (redaction first). *Done when:* search ranks correctly on a fixture set; edits made by the user in an editor are reindexed; undo restores the previous text.

### MT-M03 · Memory poisoning defenses · M · Wave 13

Each memory line carries **provenance**: `owner` (typed by or confirmed by the owner) or `source:<kind>:<id>` (derived from external content). Only `owner` lines may be written as **instructions** ("always forward…", "never ask me about…"); external-source lines are facts only, tagged with their source. Instruction-like text from a non-owner source requires confirmation. The consolidation job never promotes untrusted lines to `MEMORY.md`. *Done when:* poisoned email, web and calendar fixtures never create an instruction line.

### MT-M02 · Consolidation job · M · Wave 13

A built-in system automation (cheap class, budget-capped, runs nightly when the node is up): merge duplicates, resolve contradictions (newest wins unless flagged), roll old daily notes into weekly summaries, propose skill drafts from repeated procedures (MT-M05). Shown in the inbox like any other automation.

### MT-M04 · Skills v2 with permission manifests · L · Wave 12

*Files:* `minicore/src/minicore/skills/manifest.py` and `minimate/src/minimate/skills/enforce.py`, tests. *What:* Build on the `SKILL.md` loader (C14). Parse the optional `permissions` block (folders, connectors, network, `tier_max`) and **enforce it at runtime**: a skill's scripts run only in the sandbox with exactly those mounts and egress domains; a skill that tries to exceed its manifest is stopped and logged. Skills without a manifest default to the strictest settings (no network, no connectors, read-only workspace). *Done when:* a skill with an undeclared network call fails in the sandbox test; manifest and automation policy intersect, never union.

### MT-M05 · Skill drafts and the review queue · L · Wave 13

*What:* After a successful multi-step run, a cheap-class job may **propose** a skill draft into `~/.minimate/skills/_proposed/`. The review queue runs the server's **reviewer and security-reviewer roles** on it (content is transient), attaches findings and a diff against any existing skill, and shows it in the inbox. **Nothing activates without owner approval.** Approved skills get a version, a recorded dry-run test that must still pass, and a rollback button; usage stats (success, cost) per skill. *Done when:* a proposed skill that contains a network exfiltration is flagged and cannot be activated without an explicit override.

### MT-M06 · Knowledge folders index · M · Wave 13

User-chosen folders indexed with FTS5, with source paths kept for citations. Retrieval only on match. Re-indexing on file events. *Done when:* index respects the denylist and folder grants.

### MT-M07 · Export and import · S · Wave 13

Zip export of memory, skills and automations (no secrets); importers for common Markdown memory layouts used by other agent tools (check formats first).

### MT-N03 · Event triggers · M · Wave 12

*Files:* `minimate/src/minimate/node/triggers/{files.py,system.py}`, tests. *What:* File events (inotify via a maintained library or a polling fallback) with debounce, only inside granted folders; system events through D-Bus signals where available (disk space, network change, USB). Each event gets a dedupe ID and goes through the same lifecycle as a scheduled run.

### MT-H07 · Poll and RSS connector · S · Wave 12

Diff-based polling of feeds and pages; wakes the model only on change; page text is untrusted and tainting.

### MT-H08 · Webhook relay · L · Wave 12

*Implements:* §2 O1 (the only inbound content the server touches). *Files:* `backend/migrations/0017_mate_webhook_relay.sql`, `backend/mate/webhooks.py`, routes, `minimate/src/minimate/node/webhooks.py`, tests. *What:* The user creates a webhook on the device; the server stores only `webhook_id`, owner, device, a **hash** of the signing secret and limits. `POST /v1/mate/hook/{id}` verifies the signature, enforces size (D10) and rate limits, puts the payload into a **short-TTL Redis queue**, and forwards `relay.webhook` to the device if connected; the device acks and the server deletes the payload. Undelivered payloads are dropped at the TTL (the sender gets a documented status). Replay protection with timestamps and nonces. *Done when:* payloads never touch Postgres or logs; expired payloads vanish; a wrong signature or replay is rejected; the Q04 canary extension covers it.

### MT-G03 · Digest mode and formatting · S · Wave 12

Group routine outputs into one daily message; failures and approvals always go through immediately; per-channel formatting.

### MT-E01 · Server-side abuse and limits · M · Wave 12

Per-user concurrent automation runs, runs per hour and day, planner request limits, relay and webhook rate limits, and graceful `rate_limited` errors. Uses MiniMake's S11 Redis state. *Done when:* limits hold under a load test with a flood of scheduled runs.

### MT-Q03 · Soak tests · M · Wave 13

A 30-day compressed soak (fake clock) of ten automations on test accounts: duplicate runs, missed runs, cost creep, memory growth, approval pile-up, node restarts.

### MT-I03 · Memory and skills (acceptance) · M · Wave 14

- [ ] Memory persists across days, is editable by hand, and every automatic write has an undo.
- [ ] A heartbeat with nothing to do makes zero model calls for a day.
- [ ] A webhook triggers a run with no content stored server-side.
- [ ] A skill draft is proposed, reviewed, activated and rolled back.
- [ ] Poisoning fixtures never create instruction memory.

---

## 9. Phase 4 — Beta

### MT-A07 · Delegate to MiniMake · M · Wave 15

*Implements:* §3 D14. *What:* A capability `code_task(repo, prompt, mode)` (T3) that runs the installed `minimake -p` in **plan** mode by default through local IPC, so code work stays under MiniMake's sandbox and policy. Results come back as a summary the owner can open in MiniMake. Pushing or committing always needs an approval. Both products' ledger rows are tagged with their own surface. *Done when:* a CI-failure automation opens a plan-mode session and reports back; MiniMake not installed gives a clear error.

### MT-W02–W07 · Web surfaces · M each · Wave 15

- **W02** Automations list and detail (spec, versions, timeline, cost this month, pause, dry run).
- **W03** Approvals page (bulk view, filters, expiry countdown).
- **W04** Planner chat: describe an automation, see the draft spec and plain-language summary, the tier it needs and the credit estimate, dry run, approve.
- **W05** Usage by surface (extends X02: web, MiniMake, MiniMate, per-automation spend from the device).
- **W06** Memory and skills browser (read and edit through the relay; review queue).
- **W07** Devices page extension: show the node's status, last heartbeat, and the WSL keep-alive warning. All read from the device through the UI relay and show clear offline states.

### MT-N07 · Node `doctor` and WSL keep-alive · M · Wave 15

*What:* `minimate doctor` reports: Linux or WSL2, systemd availability, service status, vault key source (and the "less secure" warning), keyring, sandbox probe, network proxy, clock skew, channel status, last successful scheduled run, and on **WSL2 whether a keep-alive is configured**. `minimate wsl-keepalive` prints the exact steps and the Windows-side commands for the user to run (it does not touch Windows settings itself): a scheduled task at login that starts a long-lived `wsl.exe` process, plus the `.wslconfig` idle settings, with the caveat that these did not work on every version in community reports. *Done when:* tests mock each check; output is readable and actionable.

### MT-E02 · Cost estimates · S · Wave 15

The planner and the web UI show an estimated credit range per run and per month for a spec, computed from the spec's trigger frequency, model class and recent medians (falling back to defaults). Shown as a range, labelled "estimate".

### MT-Q05 · Cost telemetry · S · Wave 15

Content-free metrics: credits per run and per automation, heartbeat skip rate, approval time, failures, planner retries. Feeds your pricing decisions.

### MT-R02 · Docs and trust pages · M · Wave 15

Install and quick start; **what runs where** (device vs server) with the §2 O8 copy; what passes through Telegram and model providers; WSL2 limits and keep-alive; the app-password note for email; security model (tiers, unattended rule); panic button; uninstall and data deletion.

### MT-I04 · Beta acceptance · M · Wave 16

- [ ] 20–50 invited users on mixed Linux and WSL2 setups.
- [ ] Unit economics measured against your plans; heartbeat costs inside the model.
- [ ] No critical findings from a security review of the relay, webhook and approval paths.
- [ ] Red-team, soak and canary suites green on the beta build.
- [ ] Support runbook: revoke device, panic from the web, read a content-free diagnostics bundle.

---

## 10. Phase 5 — Desktop, voice and more connectors

All of this is **attended-first** and Linux-native. On WSL2 only Linux GUI apps are reachable.

| WP | Title | Notes |
| --- | --- | --- |
| **D01** | Dedicated browser profile (Playwright, optional install) | Separate profile, never the user's daily one; sandboxed; domains through the proxy allowlist; page text is untrusted and tainting. |
| **D02** | AT-SPI reader | Accessibility tree first: role plus name targeting; `doctor` reports whether accessibility is enabled and warns if a screen reader must be stopped. |
| **D03** | Screenshots and input | Screencast portal for screenshots (may prompt each time); `ydotool` on Wayland, `xdotool` on X11; per-compositor support matrix in `doctor`. |
| **D04** | Headless virtual desktop in a container | For unattended GUI tasks: Xvfb or headless Wayland in a Podman container; disposable; no access to the real session. |
| **D05** | Attended desktop control | Runs on the real desktop only while the user is present; every action is shown; kill switch; never unattended. |
| **D06** | Voice | Push-to-talk and voice notes through channels first; transcripts are treated as normal owner messages only from the paired device or channel. |
| **H09** | GitHub connector (token) | Read issues, PRs and CI; PR creation is T3 with approval. |
| **H10** | Slack and Discord | Owner-paired; stranger rules apply; group chats are untrusted. |
| **H11** | Home Assistant | Local network only; actions above T2 need approval. |
| **H13** | OAuth loopback client library | Loopback redirect with PKCE for connectors that need it; test it from a Windows browser into WSL2 (localhost forwarding is usually on, but verify). |

Exit (**MT-I05**): reliability numbers per compositor published in `doctor`; no unattended control of the real session; browser automation passes the red-team suite.

---

## 11. Phase 6 — Ecosystem and release

| WP | Title | Notes |
| --- | --- | --- |
| **M08** | Marketplace with scanning and signing | Migration `0019`; permission manifests required; static scan, sandboxed trial with canary secrets, publisher verification, signing, yanking; **community content off by default**. |
| **T09** | Team policy | Managed settings, shared automations, audit export. |
| **H12** | Google connectors (if approved) | Only after legal review of Google's Limited Use terms and a budget for verification and the annual CASA assessment (O5). |
| **—** | Cloud-hosted automations (decision D12) | Separate trust model, explicit opt-in, disclosure that specs and credentials live on your servers. |
| **—** | External security audit | Scope: vault, relay and webhook paths, unattended policy, approvals, sandbox, skills enforcement. The gate for GA. |
| **R01** | Packaging | `minimate` and `minicore` on PyPI; the installer offers MiniMake, MiniMate or both; `minimate update`; signed releases. |
| **R03** | Legal and privacy | Sub-processors including Telegram's role, retention (webhook TTL, run buffer), terms for acting on the user's behalf. |
| **R04** | Support tooling | Content-free diagnostics, device revoke, credit adjustments, status page. |

GA checklist: audit findings closed; red-team, soak and canary suites green on the release build; fresh-install tests on Ubuntu, Debian, Fedora and WSL2 Ubuntu (with and without keep-alive); shared-cap behavior verified across web, MiniMake and MiniMate; trust copy matches the system's behavior.

---

## 12. Which WPs unlock which automations

| Sample automation (product guide Appendix B) | Needs |
| --- | --- |
| Morning brief | H03, H05, H04 (read), T04, A05 |
| Inbox triage with drafts | H04, T04, T05, T06 |
| Download organizer | H06, N03, T02 |
| Receipt-to-spreadsheet | H06, M04 (for a spreadsheet skill) |
| Log and uptime watcher | H07 or local checks, A05, G03 |
| Backup verifier | H06, N02 |
| CI-failure responder | H08 or H09, A07 |
| Research digest | C17 (web tools), T04, G03 |
| Meeting prep | H05, H04, M01 |
| Reply to a customer | H04, T03, G04 (every send is T3 with approval) |
| Weekly dependency update | A07, H09, T03 |
| Install a tool for me | Attended only (T4) |

---

## 13. Tests and commands

| Area | Command | Notes |
| --- | --- | --- |
| Backend | `cd backend && pytest tests/unit tests/integration -v` | Includes `backend/mate` tests |
| Core | `cd minicore && pytest` | Must stay green for both products |
| MiniMake | `cd minimake && pytest` | Unchanged by MiniMate work |
| MiniMate | `cd minimate && pytest` | Sandbox tests skip loudly if `bwrap` is missing |
| Protocol | `python protocol/validate.py` | Includes the 1.1 fixtures |
| Frontend | `cd frontend && npm test && npx next lint && npx next build` |  |
| Evals | `python -m evals.minimate.run --suite automations` | Costs real credits |
| Red team | `pytest minimate/tests/redteam -v` | Blocks release |
| Canary | `pytest backend/tests/integration/test_no_content_at_rest.py` | Extended by MT-Q04 |
| Soak | `pytest minimate/tests/soak -v` | Fake clock; slow |

---

## 14. Risks of the build itself

| Risk | Mitigation |
| --- | --- |
| This plan's assumptions about MiniMake are wrong | MT-K00 inventory first; fix the inventory, not the patches |
| Extracting `minicore` breaks MiniMake | K01 is move-only; MiniMake's tests are the safety net; keep re-export shims |
| Unattended features arrive before the safety layer | The Phase 2 gate; T02–T08 and Q02 block anything above T2 |
| WSL2 users see "my automation didn't run" | `doctor` and docs say plainly that WSL must be running; guided keep-alive; recommend an always-on Linux box |
| Gmail integration costs more than expected | IMAP first; legal and budget decision before H12 |
| Telegram leaks detail the user thought stayed local | `channel_detail: minimal` default; trust copy names Telegram |
| Notification fatigue | Digests, graduation flow, anomaly pauses |
| Heartbeat costs | Local pre-checks, zero-call skips, quiet hours, 60-minute default, budgets |
| Marketplace or skill supply-chain incident | No marketplace before Phase 6; manifests enforced; canary trials |
| Scope explosion ("agentic OS") | Phase gates; desktop and voice only after the beta |
| Solo-founder capacity | Waves are a ceiling; Phase 0 to I01 is the proof; Phase 2 is the minimum before anyone else runs it |

**Stop the line:** any red-team or canary failure; a patch that weakens a policy, tier or vault check; a MiniMake test turning red; a migration number used twice; two applied patches disagreeing about the protocol.

---

## 15. Work-package index

| ID | Title | Phase | Wave | Depends on | Size |
| --- | --- | --- | --- | --- | --- |
| K00 | Inventory of MiniMake (read-only) | 0 | 1 | MiniMake M2 | S |
| A01 | Automation spec and validator | 0 | 1 | – | M |
| T01 | Tier model and capability registry | 0 | 1 | – | M |
| K01 | Extract `minicore` | 0 | 2 | K00 | L |
| K02 | Server profile support | 0 | 2 | K00 | M |
| K03 | Protocol 1.1 | 0 | 2 | K00 | S |
| N01 | Node skeleton and service | 1 | 3 | K01 | M |
| N05 | Vault | 1 | 3 | K01 | M |
| G01 | Channel abstraction and pairing | 1 | 3 | K01 | M |
| A02 | Planner endpoint and client | 1 | 3 | K02, A01 | L |
| A03 | Dry-run engine | 1 | 3 | A01 | M |
| N02 | Scheduler | 1 | 4 | N01 | M |
| H01 | Connector SDK and manifest | 1 | 4 | G01 | M |
| N06 | Notifier | 1 | 4 | N01 | S |
| N04 | Run orchestrator | 1 | 5 | N02, N05 | L |
| H03 | Telegram channel and connector | 1 | 5 | H01, G01 | M |
| A04 | Run lifecycle | 1 | 6 | N04 | M |
| I01 | First automation | 1 | 6 | Phase 1 | M |
| T02 | Unattended policy layer | 2 | 7 | T01, K01 | L |
| H02 | Connector host (local MCP) | 2 | 7 | K01, H01 | L |
| T03 | Approvals store and flow | 2 | 8 | T02 | M |
| T05 | Sealed tool endpoints | 2 | 8 | T02 | M |
| T06 | Taint for unattended runs | 2 | 8 | T02 | M |
| T07 | Panic button | 2 | 8 | T02 | S |
| H04 | Email (IMAP) | 2 | 8 | H02 | L |
| H05 | Calendar (CalDAV, ICS) | 2 | 8 | H02 | M |
| H06 | Local files connector | 2 | 8 | H02 | M |
| A05 | Budgets and heartbeat gating | 2 | 8 | N04, A01 | M |
| T04 | Reader/actor runtime | 2 | 9 | T05, N04 | L |
| T08 | Anomaly detection | 2 | 9 | T03 | M |
| G02 | Stranger handling | 2 | 9 | G01 | S |
| G04 | Approval buttons over channels | 2 | 9 | T03 | S |
| K04 | UI relay | 2 | 9 | K03 | M |
| A06 | Versions and graduation | 2 | 9 | A04 | M |
| W01 | Mate page and inbox | 2 | 10 | K04, T03 | L |
| Q01 | Automation eval harness | 2 | 10 | I01 | L |
| Q02 | Red-team suite v2 | 2 | 10 | I01 | L |
| Q04 | Canary extension | 2 | 10 | I01 | M |
| I02 | Safe unattended | 2 | 11 | Phase 2 | M |
| M01 | Memory files and search | 3 | 12 | K01 | M |
| M04 | Skills v2 with manifests | 3 | 12 | K01 | L |
| N03 | Event triggers | 3 | 12 | N02 | M |
| H07 | Poll and RSS | 3 | 12 | N03 | S |
| H08 | Webhook relay | 3 | 12 | K03 | L |
| G03 | Digest mode | 3 | 12 | G01 | S |
| E01 | Server abuse limits | 3 | 12 | N04 | M |
| M02 | Consolidation job | 3 | 13 | M01 | M |
| M03 | Memory poisoning defenses | 3 | 13 | M01 | M |
| M05 | Skill drafts and review queue | 3 | 13 | M04 | L |
| M06 | Knowledge folders index | 3 | 13 | M01 | M |
| M07 | Export and import | 3 | 13 | M01 | S |
| Q03 | Soak tests | 3 | 13 | I02 | M |
| I03 | Memory and skills | 3 | 14 | Phase 3 | M |
| A07 | Delegate to MiniMake | 4 | 15 | I01 | M |
| W02–W07 | Web surfaces | 4 | 15 | W01 | M each |
| N07 | Doctor and WSL keep-alive | 4 | 15 | I01 | M |
| E02 | Cost estimates | 4 | 15 | A02 | S |
| Q05 | Cost telemetry | 4 | 15 | I01 | S |
| R02 | Docs and trust pages | 4 | 15 | I01 | M |
| I04 | Beta acceptance | 4 | 16 | Phase 4 | M |
| D01–D06, H09–H11, H13 | Phase 5 items | 5 | 17+ | per WP | M–L |
| M08, T09, H12, R01, R03, R04, audit | Phase 6 items | 6 | 17+ | per WP | M–XL |

---

## 16. Your first week on MiniMate

1. **Confirm MiniMake has reached M2** and every §1 row is present. If not, finish those MiniMake WPs first.
2. **Lock decisions D1–D10 and D13** (D11 and D12 can wait).
3. **Wave 1 in parallel:** K00 (read-only), A01, T01.
4. **Wave 2 in parallel:** K01 (the careful one: run MiniMake's whole test suite before and after), K02, K03.
5. **Then Phase 1.** When "send me a good-morning message at 07:30" works end to end on your own machine, charged to your own pool, with nothing stored on your servers, the design is proven and Phase 2 (safety) is the next thing, not more features.

*End of the MiniMate build guide.*