# Menux — Build Execution Guide

*Minime agentic automation*

### From "M2C is done" to a personal automation system: ordered, parallelizable, patch-sized work packages

*Version 1.1 · 2026-10-26 · companion to `menux_guide.md` (what to build), `m2c_build_plan.md` (how M2C is built, whose patch workflow this guide reuses) and `m2c_guide.md`. Where this guide and `menux_guide.md` disagree, **this guide wins** (§2).*

> **Revision 1.1 (2026-10-26): the Companion Expansion.** Phase 5 is rewritten and split into **5A (native control), 5B (eyes and hands) and 5C (companion)** (§10); new tracks `X`, `V` and `S` (§4.2); new decisions D15–D25 (§3); extensions CX1–CX7 and the Companion trust copy (§2); new reserved numbers (§4.5); new waves 17–27 (§4.6); new tests, risks and index rows. **Phases 0–4 are unchanged: 59 work packages, 16 waves, 133 points.** Phase 5 adds 45 work packages and about 133 points and starts only after `MT-I04`. The user-facing description is in `menux_feature_guide.md` §17–§27.

---

## 0. How to use this guide

The patch workflow is the one in `m2c_build_plan.md` §0 (one work package = one patch, tests first, git worktrees for parallel patches, apply in wave order, log in `PATCHES.md`, regenerate rather than hand-edit hunks, stop-the-line rules in §13 there). Differences for Menux:

- **IDs use the prefix `MT-`** (for example `MT-N02`). Patch files: `MT_N02_scheduler.patch`, kept in `patches/`.
- **Most new code lives in new packages** (`minicore/`, `menux/`, `backend/mate/`), so conflicts are rare; §4.4 lists the few shared files.
- **Companion work packages (Phase 5)** reuse the existing track letters where they fit (`D`, `M`, `T`, `Q`, `R`, `K`, `N`, `E`, `W`, `I`) and add three: `X` (control), `V` (virtual desktop and the control panel) and `S` (screen memory and vision). Size labels map to points roughly as S=1, M=2, L=4, XL=8; this is an approximation of how the 133 points of Phases 0–4 were counted.
- **Third-party components are candidates, not dependencies,** until `R05` has recorded a licence decision (CX7). A WP that needs one must say so and wait for `R05`.
- **I have not seen your finished M2C code.** This guide assumes the module layout from `m2c_build_plan.md`. The **first patch (MT-K00) is a read-only inventory** that records the real paths and APIs; every later patch should be told to read that inventory first. If reality differs from this guide, fix the inventory, not the plan.

**Prompt template** (copy; fill the brackets):

```
You are generating ONE patch for the MiniMe repo at commit [SHA].
Work package: [MT-ID — title] from menux_build_plan.md.
Read first: docs/menux/m2c_inventory.md (real paths and APIs), that WP, §2
(Overrides) and §[cross-cutting] of menux_build_plan.md, and sections [..] of
menux_guide.md.
Constraints: touch only [files]; follow existing code style and docstring conventions;
no new dependency unless the WP lists it; security checks fail closed, metering and
telemetry fail open; M2C behavior must not change (run its tests).
Process: read and list findings → write tests first → implement → run [commands]
before and after → output one unified diff MT_[ID]_[slug].patch that applies with
`git apply` on [SHA]. List each "Done when" item with evidence. If the WP is wrong
against the real code, STOP and report.
```

**Size labels:** S (one focused session) · M (a few) · L (about a week of patch rounds) · XL (split it if the model struggles).

---

## 1. Preconditions: what must already exist from M2C

Menux is a second *profile* on the M2C engine. Start only when M2C has at least reached **M2 (invite-only beta)**. If any row is missing, build the M2C WP first.

| Menux needs | M2C WP | Used for |
| --- | --- | --- |
| Protocol contract and golden fixtures | P00 | Extending the protocol additively |
| Shared usage ledger with `surface in (web, m2c, menux, system)`, credits, pool check | S01, S02, S10 | One account, one cap |
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
| Devices page and Usage panel | X01, X02 | Extended for Menux |
| Eval harness, red-team suite, no-content canary | Q02, Q03, Q06 | Extended for automations |
| Beta allowlist and plan hooks | S12 | Gate Menux |

---

## 2. Overrides: what changed since the Menux product guide

Your requirements (data stays on the device, one account and one cap, Linux and WSL2) change several choices in `menux_guide.md`. **These override it.**

### O1. Topology: the local node is the gateway and the scheduler

The product guide described a server-side gateway, scheduler and cloud sandbox. Under local-first that moves:

| Piece | Where it runs | Why |
| --- | --- | --- |
| Scheduler, triggers, automation specs, run history | **Device (the "node")** | Specs and history are user data |
| Connector tokens and the credential vault | **Device** (OAuth loopback flow; never sent to the server) | Trust |
| Channels (Telegram first) | **Device**, talking outbound with the user's **own bot token** (long polling), so no public endpoint and no server involvement | Works behind NAT; content never needs to reach us |
| Memory, skills, knowledge index, approvals | **Device** | Trust |
| Tool execution (files, shell, browser) | **Device**, sandboxed | Trust |
| The "brain" per run, the Planner, review roles, metering, per-user limits | **Server** (as M2C) | The paid, orchestrated part |
| Inbound **webhooks** (public URL needed) | **Server relay** that forwards a signed payload to the device and keeps nothing after delivery (short TTL queue in Redis) | The only inbound content the server touches |
| Browser inbox, automations list, approvals | **Live relay** from the device (nothing stored), the same mechanism as M2C's remote view | Trust |
| Cloud sandbox and server-held automations | **Not in v1.** Possible later as an explicit, opt-in "Menux Cloud" (see D12) | It requires storing credentials and specs on our servers |

Data placement table (extends M2C O1):

| Where | What |
| --- | --- |
| **Device (truth)** | Automation specs, run events, approvals, memory files, skills, knowledge index, connector tokens (vault), channel tokens, settings, audit log |
| **Server, persistent, content-free** | Account, devices, usage ledger (`surface='menux'`: numbers and opaque IDs), webhook registry (webhook ID, device, secret hash) |
| **Server, ephemeral content** | In-flight run buffer (as M2C), webhook payload queue (TTL, deleted on delivery) |
| **Third parties** | Model providers (prompt content per request); **Telegram** (messages to the user's bot pass through Telegram); any connector's own service |

### O2. One account, one cap (same as M2C)

Menux runs burn the **same pool** (`surface='menux'`). Extra rules for unattended work:

- If the pool is exhausted, scheduled runs are **skipped and the owner is notified once**, never retried in a loop.
- **Per-automation and daily budgets are enforced on the device** (using usage events from the server) because they are the user's own limits; the **pool and per-user rate and concurrency limits are enforced on the server** because they protect you.
- Heartbeats and polls call the model only when a local pre-check says something changed (§MT-A05).

### O3. Platforms, and the WSL2 reality

- **Native Linux:** full feature set.
- **WSL2:** a scheduler is only useful while the WSL instance is running, and **WSL2 stops the instance shortly after the last terminal closes**. Community reports show settings such as `vmIdleTimeout=-1` and `instanceIdleTimeout=-1` help on some versions but not all, and the reliable workaround is a persistent process started at Windows login (for example a scheduled task running `wsl.exe` with a long sleep). I did not test this; confirm against current WSL docs.
  - So Menux on WSL2 ships with a **guided keep-alive setup**, and `menux doctor` warns clearly when it is missing. Missed runs are handled by a spec-level policy (§MT-A04).
  - Be honest in the docs: **automations run only while the WSL instance is up.** For true always-on use, recommend a small Linux machine (a mini-PC or Raspberry Pi) running the node.
- **Desktop control on WSL2 only reaches Linux GUI apps inside WSLg, not Windows applications.** Do not promise Windows automation. The Companion Expansion keeps this limit at launch. A Windows-side helper is designed in `D07` (Phase 5C) and built in `D08` (Phase 6) only if its review passes (CX2).
- Windows folders (`/mnt/c/...`) can be granted **read-only by default**, with a warning about speed and permission quirks.
- macOS and native Windows: not supported.

### O4. Packages

- New shared library **`minicore/`** extracted from M2C (MT-K01): store, link, auth, policy, sandbox, secrets, hooks, skills loader, instructions and memory loader, tool base classes.
- **`m2c/`** and **`menux/`** both depend on `minicore`. Two commands, two PyPI names, one installer.
- Server: the loop stays in `backend/codeagent/` (profile-aware); Menux-specific server code goes in **`backend/mate/`**.

### O5. Gmail and Google reality (affects the connector plan)

- Reading Gmail is a **restricted** Google scope. Multiple sources agree it requires Google app verification **plus an annual third-party CASA security assessment**; third-party estimates put the assessment at a few hundred to a few thousand dollars a year. Calendar scopes are "sensitive" (verification, no CASA); some Drive scopes are restricted. One source classifies `gmail.readonly` more leniently, so check Google's own scope list before relying on any of this.
- Google also requires restricted-scope apps to meet its **Limited Use** requirements in the privacy policy. Sending a user's mail content to model providers may conflict with those terms. **Ask a lawyer before building the official Google OAuth connectors** (MT-H12).
- **So v1 uses:** IMAP with an app password for email; CalDAV or ICS feeds for calendar; plain files; Telegram; a **bring-your-own OAuth client** option for power users (they create their own Google Cloud project; no verification needed for personal use in testing mode, with its limits). The official Google connector is a Phase 6 business decision.

### O6. Tiers and unattended policy

The T0–T5 tiers and the unattended ceiling (T2) from `menux_guide.md` §6.7 and §11.2 stand. Mapping to M2C's tool risk levels:

| M2C risk (per tool) | Menux tier (per capability or automation ceiling) |
| --- | --- |
| R0 read-only | T0 observe |
| (derived content) | T1 derive: drafts, summaries in the workspace |
| R1 write inside the workspace | T1–T2 |
| – | T2 notify the owner |
| R3 network or outside project | T3 act externally (reversible) |
| R2 shell, R1 outside grants | T4 change system or data |
| R4 irreversible | T5 |

Rule: **a tool's effective tier is the higher of its M2C risk level and the tier its connector declares.**

### O7. The profile

Runs carry `profile: "automation"`, with their own system prompt, tool catalog, default budgets, and `run_kind` (`interactive | scheduled | triggered | heartbeat | delegated`).

### O8. Trust copy for Menux (more sensitive than M2C)

> **Where your data lives.** Your automations, memory, skills and connector credentials are stored on your device. When an automation runs, the content it needs (for example today's calendar entries and email subjects) is sent to our servers and our model providers to produce the result; we don't keep it after the run ends. If you connect Telegram, messages to your bot pass through Telegram. We keep only usage numbers so your plan's limit applies across the web app, M2C and Menux. Messages from people you haven't paired are treated as data, never as instructions. You can pause everything with one button.

### Companion extensions (CX1–CX7)

Added in revision 1.1. They govern Phase 5 and sit beside O1–O8; they never relax O1–O8, the T0–T5 tiers or the shared pool.

| # | Extension | Rule | Where it is built |
| --- | --- | --- | --- |
| **CX1** | Reach levels and the control ladder | Reach 0–4. For every task use the most reliable method that can do the job: commands, application scripting, accessibility tree, keyboard shortcuts, vision and pointer, with a registered specialist tool first for the operations it covers. Every method inherits tiers, approvals, panic and audit. Guide mode is the end of the line, never a silent failure | X01–X05, X06, X07, X08 |
| **CX2** | Linux first, WSL2 second | Native Linux gets everything. WSL2 gets everything that runs inside Linux. Controlling Windows applications needs a Windows-side helper: design spike `D07` (5C), build `D08` (Phase 6), only if reviewed. No promise before that | D07, D08, N08 |
| **CX3** | The user always wins | Pointer work defaults to the virtual desktop (Background). On the real screen Menux takes turns and yields on any user input. The user can watch, take over and hand back | D04, V01–V03 |
| **CX4** | Screen memory: local, off by default, visible | Event-driven, text first, raw images deleted after extraction, sensitive apps excluded, encrypted with a vault-derived key, never stored on the server, indicator always visible, one-key pause | S01–S04, Q08 |
| **CX5** | Two perception paths | Everything that sees has a CPU-only path (accessibility and CPU OCR, cloud grounding only with consent) and a GPU path (local models). `doctor` recommends one; the user can override | N08, S05, E03 |
| **CX6** | Skills shared as sanitized, signed templates | Real automations and data never leave the device. Templates are stripped, parameterized, scanned, trialled with canary secrets, signed, installed disabled | M12 (curated), M08 (marketplace) |
| **CX7** | Reuse or build, after a licence check | No candidate is imported before `R05` records a decision; every candidate sits behind a Menux interface with an own-build fallback | R05 |

**Tier follows effect and context (T10).** The capability registry may assign a tier by context. `input.contained` (pointer and keyboard input inside a disposable virtual desktop with no accounts, no real files and allowlisted egress only) is T1; the same input on a logged-in profile or the real desktop is T3–T4. Unknown context takes the higher tier. **Grants** (scoped, time-limited, revocable) substitute for per-step approval of T3–T4 inside their scope and never cover the **always-confirm list**: payments; passwords, keys and vault export; deleting files outside staging or granted scratch; sending to a new third party or destination; changing the dial, grants, policy or logging; installing software, tools or skills; any unrecognized capability or context. This rule must be validated by the GUI red-team suite (Q07) before Phase 5B is released.

### Trust copy for the Companion (addendum to O8)

> **What Menux sees.** Screen awareness and screen memory are off until you turn them on, and an indicator is visible whenever they run. Menux reads text from your screen on your device and keeps it, encrypted, on your device. Password managers, banking pages and private windows are excluded by default. When a task needs a model to look at a screenshot, only that image, or a text description of it, is sent, only with your permission, and we don't keep it after the run ends. Menux works on its own virtual desktop by default and steps aside the moment you use your mouse or keyboard. Some actions, such as payments, deleting files, using passwords and sending to someone new, always need your confirmation. You can pause, search, export or delete everything Menux remembers at any time.

---

## 3. Decisions to lock before the first patch

| # | Decision | Default | Notes |
| --- | --- | --- | --- |
| D1 | Scheduler | **Own small scheduler on `croniter` with a SQLite job table**, run inside the node | Simple, testable, no heavy dependency |
| D2 | Node run modes | **systemd user service** where available; **foreground `menux run`** otherwise (WSL without systemd) | `doctor` picks and explains |
| D3 | Vault encryption key | **OS keyring if available, else a passphrase-derived key (prompted at node start), else a `0600` key file flagged "less secure" in `doctor`** | WSL2 usually has no keyring |
| D4 | First channel | **Telegram with the user's own bot** (long polling) | No server involvement |
| D5 | Email | **IMAP + app password**, read and draft only | Google OAuth is D11 |
| D6 | Calendar | **CalDAV / ICS URL** first |  |
| D7 | Spec format | **YAML validated by a JSON Schema** | Same parser on server (Planner) and node |
| D8 | Browser automation | **Playwright (headless Chromium), optional extra install** | Large download; off by default |
| D9 | Embeddings for memory search | **None in v1 (SQLite FTS5 only)** | Embeddings would send content to a provider |
| D10 | Webhook relay TTL | **Delivery within 10 minutes or dropped; max 64 KB** | Content-free persistence |
| D11 | Google OAuth connectors | **Defer; decide after legal advice and budget for CASA** | See O5 |
| D12 | Cloud-hosted automations ("Menux Cloud") | **Not in v1; revisit after the beta** | Needs a separate trust model and disclosure |
| D13 | Package and command names | **`menux`, `minicore`** | Check availability on PyPI and your domain |
| D14 | How Menux hands a task to M2C | **Local IPC to the installed `m2c` CLI** (headless mode) | Keeps code tasks under M2C's sandbox and policy |
| D15 | Companion scope and order | **Phase 5A, 5B, 5C after `MT-I04`; Phases 0–4 stay at 59 WPs / 133 pts** | Each sub-phase is releasable on its own |
| D16 | Control ladder and selector | **Specialist tool first for its operations, then rungs 1–5 in order (commands, application scripting, accessibility, shortcuts, vision and pointer); Guide mode last** | Reliability first; never a silent failure |
| D17 | Where pointer work happens | **Background on a virtual desktop by default; Shared mode yields to the user on any input; live view with take-over** | The user always wins (CX3) |
| D18 | Screen memory defaults | **Off; event-driven; text first; raw images deleted after extraction; text kept 30 days and thumbnails 24 hours (proposed, to confirm in testing)** | Local only; FTS5 only (D9) |
| D19 | Perception paths | **Both: CPU-only path (cloud grounding with consent) and GPU path (local models); `doctor` recommends, the user overrides** | CPU-only users are first-class |
| D20 | Reuse or build | **Candidates are reviewed by the owner against their licence text; use if the licence permits, otherwise build our own** | `R05`; candidates in feature guide §27 |
| D21 | Skill sharing | **Curated first-party library and opt-in submit-for-review in 5C (`M12`); open marketplace in Phase 6 (`M08`), off by default** | Templates only (CX6) |
| D22 | Distribution | **Menux session image (package or script first, VM or image later); no full distribution before GA** | Revisit after GA |
| D23 | Windows | **WSL2 at launch with honest limits; helper design spike in 5C (`D07`), build in Phase 6 (`D08`) only if reviewed** | CX2 |
| D24 | Games | **Opt-in game profile; strategy, turn-based and slow live tasks; no anti-cheat circumvention; notice shown** | Real-time action titles are out of scope |
| D25 | Context-based tiering | **Tier follows effect and context; contained input in a disposable session is T1; grants are scoped and time-limited; always-confirm list is a hard floor** | `T10`; validated by `Q07` |

D15–D25 are Companion decisions. They can wait until the beta is under way, but must be locked before the first Phase 5 patch.

---

## 4. The map

### 4.1 Phases and milestones

| Phase | Goal | Ends with | Milestone |
| --- | --- | --- | --- |
| **0** | Foundations | Real inventory of M2C; shared core extracted; protocol and profile extended; spec and tier definitions | – |
| **1** | First automation | Cron-scheduled automation on the node → server brain → Telegram message to the owner; metered under `surface='menux'` | **MT-I01** |
| **2** | Safe unattended | Tiers, unattended policy, approvals, reader/actor split, taint, panic button, inbox, email/calendar/files read | **MT-I02** |
| **3** | Memory, skills, triggers | Memory files and search, poisoning defenses, skills with manifests, skill drafts for review, file/webhook/poll triggers, heartbeat gating | **MT-I03** |
| **4** | Beta | Web inbox and planner chat, delegation to M2C, doctor with WSL keep-alive, cost estimates, docs | **MT-I04 (invite-only beta)** |
| **5A** | Native control (Reach 1–2) | Licence record, hardware probe, protocol 1.2, context-based tiering and grants, shell and file tool, application registry and ladder selector, LibreOffice and app adapters, AT-SPI, shortcut and input maps, browser profile, reliability benchmark | **MT-I05a** |
| **5B** | Eyes and hands (Reach 3) | Screenshots and input, virtual desktop with live view and take-over, shared mode, tray dial, screen memory, dual-path grounding, pointer layer with verification, guide mode, Menux Map, GUI red-team and privacy suites | **MT-I05b** |
| **5C** | Companion (Reach 4) | Specialist tool kit and self-built tools, experience memory, learning by demonstration, self-repair, skill templates and curated library, game loop, session image, Windows-helper design | **MT-I05c** |
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
| **D** | Desktop: browser profile, accessibility, screenshots and input, virtual desktop container, voice, Windows helper |
| **X** | Control: shell tool, application registry and ladder selector, application adapters, input maps, pointer layer, guide mode, specialist tools, games |
| **V** | Virtual desktop sessions, live view, shared mode, the tray control panel |
| **S** | Screen memory and vision: capture, extraction, store, search, grounding |
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

PHASE 4   K04 ──► W01..W07      A07 (delegate to M2C)     N07 (doctor + keep-alive)
          E02   Q05   R02 (docs)  ──► I04

PHASE 5A  R05, N08, K05, T10 (first, in parallel)
          T10 ──► X01      T10+H02 ──► X02 ──► X03, X04, X05 (X05 also needs D02)
          R05+T04+T06 ──► D01 (browser profile)     N08+R05 ──► D02 (AT-SPI)
          X03+X04+D02 ──► Q06 ──► I05a

PHASE 5B  N08+R05 ──► D03        N08 ──► D04        D03+D04+T10 ──► V01 ──► V02, V03 ──► V05
          N08+D03+K05+R05 ──► S05 ──► X06 (also X02, D03, T10)      T10+T07 ──► V04
          D02+D03+N05 ──► S01 ──► S02 ──► S03 ──► S04, W09, Q08      S02+X02 ──► X07
          T04+S05 ──► T11            X06+T11+V01 ──► Q07            E01+K05 ──► E03
          K04+A06+M04+X02 ──► W08                                     all of 5B ──► I05b

PHASE 5C  X02+R05 ──► X08 ──► X09 (also M05, T10)       M01+X02 ──► M09 ──► M11 (also A06, X06)
          S03+M05+X06 ──► M10          X05+X06 ──► X10
          M04+M05+Q02+T11+R05 ──► M12      N08+V01+D03 ──► N09      N07+N08 ──► D07
          R02+S03+V04 ──► R06          all of 5C ──► I05c

INDEPENDENT   D06 (voice), H09–H11, H13

PHASE 6   M08 (marketplace, builds on M12), D08 (Windows helper, after D07 passes review),
          T09 (team policy), H12 (Google, if approved), audit, R01 (packaging), R03, R04 ──► GA
```

### 4.4 Conflict map (files more than one WP touches)

| File(s) | WPs, in order |
| --- | --- |
| `minicore/**` (after MT-K01) | K01 owns the move. Later WPs **add** modules or **extend through registries**, never rewrite existing ones. Any change to `minicore` must pass **both** products' tests |
| `protocol/v1/*` | K03 only (additive); later additions are new files |
| `backend/codeagent/loop.py`, `tools_schema.py` | K02 only: it adds the profile hook and the tool-catalog registry. Everything else registers tools from `backend/mate/tools/*.json` |
| `backend/api/server.py` | K02 adds one `include_router` for `/v1/mate`; later routers are added inside `backend/mate/` |
| `frontend` navigation and the Mate page shell | W01 creates the page and the nav entry; W02–W07 are components inside it |
| `menux/src/menux/node/service.py` | N01 → N02 → N04 → N03 → N07 (each extends the node's event loop) |
| `backend/migrations/` | Numbers are **reserved** (§4.5) |
| `minicore/src/minicore/tiers/registry.py` | T01 owns it; T10 adds context-based tiering and the always-confirm list; later WPs only register capabilities |
| `menux/src/menux/control/**` (application profiles, selector) | X02 owns the registry and selector; X03–X05, X08 and X09 add profiles and tools |
| `menux/src/menux/desktop/**` (capture, input, sessions) | D02 → D03 → D04 → V01; S01 and S05 add modules; V02–V04 are separate modules |
| `protocol/v1/*` | K03 (1.1) and K05 (1.2) are additive new files |
| `backend/mate/` | E03 adds `vision`; M12 adds `skills`; neither edits existing routes |

### 4.5 Reserved numbers

| Item | Number |
| --- | --- |
| Migration: webhook relay registry | **0017** (H08) |
| Migration: push-notification subscriptions (optional) | **0018** (W-late) |
| Migration: marketplace catalog | **0019** (M08) |
| Migration: skill templates (curated library) | **0020** (M12) |
| Migration: vision usage, only if `usage_ledger` cannot carry it | **0021** (E03) |
| Protocol | additive revision **1.1** (K03), additive revision **1.2** (K05) |
| Server routes | `/v1/mate/*` (planner, relay, webhooks), `/v1/mate/vision/*` (E03), `/v1/mate/skills/*` (M12) |

### 4.6 Waves

| Wave | Patches (parallel) | Needs |
| --- | --- | --- |
| **1** | K00, A01, T01 | M2C M2 |
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
| **17** | R05, N08, K05, T10 | Phase 4 (I04) and the earlier waves named in §10 |
| **18** | X01, X02, D01, D02 | per WP (§10 lists each dependency) |
| **19** | X03, X04, X05, D03, D04 | per WP (§10 lists each dependency) |
| **20** | Q06, S05, V01, S01, E03 | per WP (§10 lists each dependency) |
| **21** | I05a, S02, V02, V03, X06, T11, V04 | per WP (§10 lists each dependency) |
| **22** | V05, S03, X07, Q07 | per WP (§10 lists each dependency) |
| **23** | S04, W08, W09, Q08 | per WP (§10 lists each dependency) |
| **24** | I05b | per WP (§10 lists each dependency) |
| **25** | X08, M09, N09, D07 | per WP (§10 lists each dependency) |
| **26** | X09, X10, M10, M11, M12, R06 | per WP (§10 lists each dependency) |
| **27** | I05c | per WP (§10 lists each dependency) |
| **28+** | D08, M08, T09, H12, R01, R03, R04, audit (Phase 6) | I05c; D07 for D08; M12 for M08 |

Phase 5 waves overlap on purpose: a 5B work package may start as soon as its own dependencies exist. The acceptance milestones `I05a`, `I05b` and `I05c` gate the **release** of each sub-phase, not the work. `D06` (voice) and `H09–H11`, `H13` are independent and unscheduled.

---

## 5. Phase 0 — Foundations

### MT-K00 · Inventory of the finished M2C · S · Wave 1 (read-only)

*Output (one new file, no code):* `docs/menux/m2c_inventory.md`. *What:* The patch-writing model reads the repo and records: the real module paths for every item in §1 (store, link, auth, policy engine, sandbox, secrets, hooks, skills, instructions/memory loader, tool classes, MCP client, TUI), their public function and class signatures, the server's profile handling, the tool catalog format, the protocol version and message list, the migration numbers used so far, and the commands to run each test suite. Also record anything from §1 that is **missing**. *Done when:* every §1 row is marked present, partly present or missing with a path; the test commands are verified to run green on the current commit. *Why first:* this guide cannot know M2C's final layout, and every later patch depends on the facts in this file.

### MT-A01 · Automation spec: schema, parser, validator · M · Wave 1

*Implements:* product guide §6.2. *Files (new):* `protocol/spec/automation.schema.json`, `minicore/src/minicore/automation/{spec.py,validate.py}` (or `menux/` until K01 lands), tests, `docs/menux/automation-spec.md`. *What:* The YAML spec from product guide §6.2: `id`, `description`, `trigger` (cron, interval, heartbeat, file, webhook, poll, message, manual), `agent` (`profile`, `model_class`, `instructions`, `pipeline` for reader/actor), `capabilities` (connector tools, channel tools, folders with `r`/`rw`), `policy` (`tier_max`, `unattended`, `approvals`, `egress`), `budget` (`per_run_credits`, `per_day_credits`, `per_month_credits`), `quiet_hours`, `missed_run`, `notify_on_failure`. JSON Schema plus a validator that adds semantic checks: capabilities must exist in the capability registry (T01), `tier_max` must cover every listed capability's tier, an unattended spec may not list any capability above T2, an unattended spec with untrusted-content tools must declare the reader/actor pipeline, `egress` is a closed list, budgets are positive. *Done when:* valid and invalid fixtures; every semantic rule has a failing test; the same module is importable by the server (Planner) and the node.

### MT-T01 · Tier model and capability registry · M · Wave 1

*Implements:* product guide §11.2; §2 O6. *Files (new):* `minicore/src/minicore/tiers/{tiers.py,registry.py}`, `docs/menux/tiers.md`, tests. *What:* The T0–T5 enumeration with ordering; a **capability registry** (`capability_id → {tier, read_or_write, egress_domains, description, confirm_phrase?}`); the effective-tier function from O6; a loader for connector manifests (H01). Pure data and functions, no I/O. *Done when:* tests for ordering, effective tier, unknown capability (treated as T5 and denied), and registry loading.

### MT-K01 · Extract `minicore` from M2C · L · Wave 2

*Files:* new `minicore/` package; `m2c/` modules moved and replaced by thin re-exports; `pyproject.toml` files; CI. *What:* **Behavior-preserving move.** Using the inventory (K00), move the shared modules (store, link, auth, policy, sandbox, secrets, hooks, skills loader, instructions/memory loader, tool base classes, checkpoints) into `minicore/src/minicore/`. Keep `m2c.*` import paths working with re-exports for one release. No logic changes. *Done when:* **every M2C test passes unchanged** (only import lines may differ); `minicore` has its own test suite carrying the moved tests; a new empty `menux/` package imports `minicore` in CI. *Rule for all later WPs:* additions to `minicore` must keep both products green.

### MT-K02 · Server profile support · M · Wave 2

*Files:* `backend/codeagent/{loop.py,tools_schema.py,prompts.py}` (profile hooks only), new `backend/mate/{__init__.py,router.py,profile.py}`, one `include_router` in `backend/api/server.py`, tests. *What:* `run.start.profile = "automation"` selects: the system prompt (`backend/mate/prompts/automation.md`), the **tool catalog** assembled from `backend/mate/tools/*.json` (initially `connector_call`, `notify_owner`, `read_file`, `list_dir`, `glob`, `grep`, `memory_search`, `memory_write`, `skill`, `tasks`, `ask_user`), default budgets by `run_kind`, and the model class from the spec. Code runs unaffected; add a test that a `profile="code"` run is byte-identical to before. *Done when:* both profiles run through the same loop in tests; unknown profiles are rejected; the M2C loop tests pass unchanged.

### MT-K03 · Protocol additions (revision 1.1) · S · Wave 2

*Files:* `protocol/v1/` additive files, fixtures, contract tests. *What:* Additive only: `run.start` fields `run_kind`, `spec_id`, `pipeline_stage`; webhook relay messages `relay.webhook` (server→device: `webhook_id`, `payload`, `received_at`, `sig`) and `relay.ack`; UI relay messages `ui.query` (server→device: `{id, name, args}`) and `ui.reply`; approval events `approval.requested`, `approval.decided`; error codes `automation_paused`, `relay_expired`. New golden fixtures: scheduled run, run skipped for quota, webhook delivery, UI query and reply. *Done when:* all M2C fixtures still validate; new fixtures validate; the byte-equality check between `protocol/` and the packaged copies still passes.

---

## 6. Phase 1 — First automation (the walking skeleton)

**Goal:** the thinnest end-to-end automation: the user installs the node, pairs a Telegram bot, describes an automation, and a scheduled run produces a message on Telegram, charged to the shared pool. No email, no memory, no unattended-risk features yet, so the only output is **a message to the owner** (T2).

### MT-N01 · Node skeleton and service · M · Wave 3

*Files:* `menux/pyproject.toml`, `menux/src/menux/{cli.py,node/service.py,node/paths.py,node/config.py}`, `menux/tests/`. *What:* Commands `menux init`, `menux run` (foreground), `menux status`, `menux stop`; `menux service install|uninstall` writing a **systemd user unit** when systemd exists (D2). State under `~/.menux/` (`0700`): `state.db` (reuses `minicore` store), `automations/`, `memory/`, `skills/`, `logs/`. Single-instance lock; graceful shutdown; sign-in reuses `minicore` auth (same device credential flow, labelled as Menux). *Done when:* start and stop are clean; two nodes cannot run at once; `menux status` shows login state and next scheduled runs; works without systemd via foreground mode.

### MT-N05 · Vault · M · Wave 3

*Implements:* §3 D3; product guide §11.5. *Files:* `menux/src/menux/vault/{store.py,keys.py}`, tests. *What:* An encrypted store (`vault.db`, authenticated encryption) for connector and channel secrets. Key sources in order: OS keyring, passphrase-derived (Argon2 or scrypt, prompted at node start and cached only in memory), `0600` key file (flagged "less secure" by `doctor`). Secrets are only ever read by connector code inside the node process; they never go into model context, logs, tool results or the sandbox. `menux vault add|list|remove` (values are never printed). *Done when:* tests prove ciphertext at rest, wrong key fails closed, secret redaction catches vault values in outgoing text, and a deliberately logged secret is blocked by the redaction filter.

### MT-G01 · Channel abstraction and pairing · M · Wave 3

*Files:* `menux/src/menux/channels/{base.py,pairing.py,router.py}`, tests. *What:* A `Channel` interface (`start`, `stop`, `send(owner_text, buttons?)`, `on_message`, `on_callback`) and an **owner pairing** flow: the node shows a one-time code; the owner sends it to the bot; the channel records the owner's account ID. Anyone else is a "stranger" (G02 handles them). Everything the router receives is labelled `trust: owner | stranger`. *Done when:* pairing succeeds once and codes cannot be reused; strangers never reach the run starter.

### MT-A02 · Planner endpoint and client · L · Wave 3

*Files:* `backend/mate/planner.py`, route `POST /v1/mate/plan`, prompt `backend/mate/prompts/planner.md`, `menux/src/menux/planner_client.py`, tests. *What:* Stateless server endpoint. Input: the user's plain-language request plus the node's **capability list** (names, tiers, descriptions only, no secrets). Output: a draft spec (A01 format), a plain-language summary, the tier it needs, an estimated credit range, and open questions. The server **validates the draft with the A01 validator before returning** and retries once with the error if invalid. Nothing is stored. Uses the Brain role or the strong class; metered as `menux` usage. *Done when:* ten scripted requests produce valid specs or specific questions; the validator rejects a deliberately over-privileged draft; no content is persisted (the Q06 canary extended in MT-Q04 covers this).

### MT-A03 · Dry-run engine · M · Wave 3

*Files:* `minicore/src/minicore/automation/dryrun.py` (or `menux/`), tests. *What:* Run a spec with **all writes simulated**: connector write tools and `notify_owner` return a canned success and record "would do X"; reads use real data (or fixtures in tests). Produces a human-readable report of what would have happened and what it would have cost. *Done when:* a dry run never calls a real write; the report matches the recorded intents.

### MT-N02 · Scheduler · M · Wave 4

*Files:* `menux/src/menux/node/scheduler.py`, tests. *What:* Cron, interval and manual triggers on `croniter` with time zones and DST handled; a job table in `state.db`; **missed-run policy** per spec (`run_now`, `skip`, `run_if_recent:<minutes>`) computed at node start and after sleep; jitter to avoid every user hitting the server at :00; dedupe by trigger-event ID. *Done when:* tests with a fake clock cover DST changes, a node that was off, rapid restarts and duplicate events.

### MT-H01 · Connector SDK and manifest · M · Wave 4

*Files:* `menux/src/menux/connectors/{base.py,manifest.py,stances.py}`, `docs/menux/connector-sdk.md`, tests. *What:* A connector declares: name, auth method, tools with JSON Schemas, **per-tool tier**, read/write class, egress domains, rate limits and test fixtures. Per-tool **stances** (`allow | ask | block`) from settings. A uniform `call(tool, args)` entry that validates arguments, applies the stance and tier, injects credentials from the vault, calls out only to the declared domains (through `minicore`'s network proxy), enforces a size cap on the parsed result, and returns it labelled with a trust level. *Done when:* a toy connector passes the whole path; an undeclared domain, an oversize result and a blocked stance each fail in tests.

### MT-N06 · Notifier (minimum) · S · Wave 4

*Files:* `menux/src/menux/notify.py`, tests. *What:* Desktop notifications through `notify-send` or D-Bus when available, falling back to the channel; used for failures, approvals waiting and panic. Never includes message bodies when the user has set `channel_detail: minimal`.

### MT-N04 · Run orchestrator · L · Wave 5

*Files:* `menux/src/menux/node/runner.py`, tests. *What:* The node-side executor of an automation run: build `run.start` (`profile=automation`, `run_kind`, spec instructions, memory index if any), connect through `minicore`'s link, receive `tool_proposed`, route each call to the right local executor (connector host, file tools, `notify_owner`), apply the policy engine with the **unattended** flag (T02 later; until then only T0–T2 tools are available), send `tool_result`, honor budgets and cancel, write every event to the local store. Handles quota exhaustion (`quota_exhausted` → skip and notify once), disconnects and resume. *Done when:* a scripted fake server drives a full run; cancel kills in-flight tools; budgets stop a run; events land in `state.db`.

### MT-H03 · Telegram channel and connector · M · Wave 5

*Files:* `menux/src/menux/channels/telegram.py`, `connectors/telegram/manifest.yaml`, tests with a fake Bot API. *What:* Long polling with the user's bot token from the vault; owner-only sends (`send_to_owner`, with Markdown escaping and length splitting); inline keyboards for approvals (decisions arrive as callback queries with an opaque approval ID and a nonce, accepted only from the paired owner); rate limiting and backoff on API errors. *Done when:* pairing and send work against the fake API; callbacks from non-owners are ignored; the token never appears in logs.

### MT-A04 · Run lifecycle · M · Wave 6

*Files:* `menux/src/menux/node/lifecycle.py`, tests. *What:* States `queued → running → completed | failed | skipped | paused | awaiting_approval`; one active run per automation by default (queue or drop per spec); retries with backoff for transient failures; one failure notification per failure episode, not per attempt; a per-automation timeline in the store. *Done when:* tests for concurrency, retry limits, notification de-duplication and restart recovery.

### MT-I01 · First automation (acceptance) · M · Wave 6

*Joins:* K01, K02, K03, N01, N02, N04, N05, N06, G01, H01, H03, A01, A02, A03, A04. *What:* End to end on a real machine with a dev model: `menux init`, pair Telegram, say "send me a short good-morning message with today's date at 07:30", review the spec and dry run, approve, and watch the scheduled run arrive. Check the shared pool. *Done when:*

- [ ] The Telegram message arrives at the scheduled time; the run is in the local store.
- [ ] A ledger row exists with `surface='menux'` and the web Usage panel shows it.
- [ ] No automation content exists in Postgres, logs or Redis after the run (Q06 canary).
- [ ] The node restarts mid-day and still runs the next scheduled automation.
- [ ] A skipped run (node off at 07:30) follows the missed-run policy.

---

## 7. Phase 2 — Safe unattended automations

**Goal:** let automations run while nobody is watching, safely. This phase adds everything that makes unattended runs trustworthy **before** any write connector (beyond messaging the owner) is allowed: tiers enforced by code, queued approvals, split agents for untrusted content, taint, a panic button, an inbox, and the first read connectors (email, calendar, files).

> **Gate:** do not enable any tier above T2 for unattended runs until MT-T02 through MT-T08 and the red-team suite (MT-Q02) pass.

### MT-H02 · Connector host (local MCP, stances, trust) · L · Wave 7

*Files:* `menux/src/menux/connectors/host.py`, `mcp_bridge.py`, tests. Reuses M2C's local MCP client (C23). *What:* Runs connectors as in-process Python plugins or as **local MCP servers** (stdio) under the sandbox, with tool descriptions from non-first-party servers marked untrusted and shown to the user at install; deferred tool schemas (tool search); per-server trust levels; credentials injected from the vault by the host, never passed through the model. *Done when:* a local MCP server's tools appear with correct tiers; an unlisted tool is invisible; a poisoned tool description cannot change a stance (tests with fixtures).

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

*Files:* `menux/src/menux/approvals/{store.py,flow.py}`, tests. *What:* Approvals live in `state.db`: `id`, `run_id`, automation, capability, **exact content** (draft text, command, diff), tier, `expires_at` (default 24 h), `status`. Flow: a T3 call creates an approval and pauses *that call only* (the run may continue other work or finish with the action pending). Decisions: approve once, approve and remember this exact action, edit then approve, deny, deny and pause the automation. On approve the node **re-checks the policy** immediately before executing. Expiry means skipped and logged. Decision sources: local CLI, desktop notification actions, channels (G04), web inbox through the UI relay (K04) with the same nonce checks. *Done when:* tests for expiry, double decisions, replay of an old approval ID, edits changing the content hash (an edited approval needs a fresh decision), and approval after policy change (denied).

### MT-T05 · Sealed tool endpoints · M · Wave 8

*Files:* `menux/src/menux/sealed/{notify_owner.py,draft_reply.py}`, tests. *What:* Fixed-schema tools with hard-coded targets: `notify_owner(text)` (recipient is always the paired owner), `save_report(name, markdown)` (writes only inside the workspace folder), `draft_reply(thread_ref, text)` (creates a **draft** in the user's own mailbox; cannot send). No tool at tier ≤ T2 accepts a free-form recipient, URL or path. *Done when:* fuzz tests try to smuggle a recipient, URL or path through each argument and fail.

### MT-T06 · Taint for unattended runs · M · Wave 8

*Implements:* product guide §11.3(5); reuses M2C's taint state (C17). *Files:* `minicore/src/minicore/policy/taint_unattended.py`, tests. *What:* A run becomes tainted when any tool result carries `trust: external` (inbound mail bodies, fetched pages, shared documents, a stranger's message). Once tainted: every egress-capable or external-write tool becomes **deny** (not ask), the tainted flag and cause are recorded in the run timeline, and the final summary tells the owner. A reader/actor pipeline (T04) is the supported way to use untrusted content *and* act. *Done when:* the poisoned-mail fixture cannot cause any outbound action; the flag appears in the timeline.

### MT-T07 · Panic button and kill switch · S · Wave 8

*Files:* `menux/src/menux/panic.py`, CLI `menux panic`, tests. *What:* One action: stop all runs, mark every automation disabled, drop the vault key from memory (the vault locks until re-unlocked), optionally revoke the device token. Reachable from the CLI, a desktop notification action, a Telegram command from the owner, and (K04) the web button. Everything it did is logged. *Done when:* after panic no run starts, no connector call can decrypt a secret, and resume requires an explicit unlock.

### MT-H04 · Email connector (IMAP: read and draft) · L · Wave 8

*Files:* `menux/src/menux/connectors/imap/*`, manifest, tests with a fake IMAP server. *What:* App-password IMAP (D5). Tools: `search` and `read` (T0, results marked **untrusted** and tainting), `list_folders`, `create_draft` (T2, in the user's own Drafts folder; the connector has **no send tool**). Read results are size-capped and stripped of active content; attachments are not fetched in v1. *Done when:* the injection fixtures (hidden instructions in headers, HTML and plain bodies) are delivered to the model only as labelled data; no code path can send mail.

### MT-H05 · Calendar connector (CalDAV and ICS) · M · Wave 8

Read events (T0), free-busy summary, no write in v1. Event titles and descriptions are untrusted text. *Done when:* works against a local CalDAV test server and a static ICS file.

### MT-H06 · Local files connector · M · Wave 8

Folder grants with `r` or `rw` modes stored in settings; reuses M2C's path guard and the two-form denylist; `/mnt/c` grants default to `r` with a warning. Tools: list, read, search, write (T1, inside `rw` grants only, with checkpoints from C08). *Done when:* traversal, symlink and denylist tests pass.

### MT-A05 · Budgets and heartbeat gating · M · Wave 8

*Files:* `menux/src/menux/node/budgets.py`, `heartbeat.py`, tests. *What:* Per-run, per-day and per-month credit budgets from the spec, tracked locally from the server's `usage` events; at 80% warn, at 100% pause the automation and notify. **Heartbeat:** a cheap local pre-check script list (new priority mail? calendar change? disk over 90%?) runs first; the model is called only if a check reports a change or the checklist has content; quiet hours and a daily beat cap apply. Default interval 60 minutes. *Done when:* tests prove that an unchanged world costs zero model calls, that budgets pause correctly, and that a node restart does not reset the day's spend (it is rebuilt from the local store).

### MT-T04 · Reader/actor split runtime · L · Wave 9

*Implements:* product guide §11.3(1)–(3). *Files:* `menux/src/menux/node/pipeline.py`, server prompts `backend/mate/prompts/{reader,actor}.md`, tests. *What:* For specs that declare `pipeline: [reader, actor]`, the node runs **two separate runs**. The **reader** run has only untrusted-content read tools and **no egress or write tools**; it must return JSON that matches a schema in the spec, size-capped and sanitized (strip URLs and markup unless the schema allows them). The **actor** run receives only that structured result plus the owner's instructions, and only sealed T2 tools. Fixtures show the limit: structured fields can still carry an injection, so the actor never gets a free-form send or path tool. *Done when:* the injection corpus run through the pipeline produces no unapproved outbound action; a reader attempting to call a write tool is denied.

### MT-T08 · Anomaly detection · M · Wave 9

Local heuristics: repeated denies, a tool the automation has never used, cost above three times its median, run time above three times its median, an unexpected stranger message burst. Action: pause the automation and notify once. *Done when:* replayed anomalous timelines trigger and normal ones do not.

### MT-G02 · Stranger handling and rate limits · S · Wave 9

Strangers' messages are stored as **data** (optionally summarized for the owner on request), never routed to a run starter; per-sender rate limits; a block list. *Done when:* a stranger message cannot start a run, change settings or approve anything.

### MT-G04 · Approval buttons over channels · S · Wave 9

Telegram inline buttons for T03 decisions with `channel_detail: minimal` (a ping that says an approval is waiting, details viewed locally or in the web inbox) or `full` (the exact content in the chat). The trust copy states that full details pass through Telegram. *Done when:* callbacks validate owner, nonce and expiry.

### MT-K04 · UI relay (device queries from the browser) · M · Wave 9

*Files:* `backend/mate/relay_ui.py`, route `POST /v1/mate/relay/query`, node handler `menux/src/menux/node/ui_handler.py`, tests. *What:* The browser asks the **server**, the server forwards a `ui.query` to the owner's connected device, the device answers with `ui.reply`, and the server passes it through **without storing it**. A fixed whitelist of query names (`automations.list`, `automation.get`, `runs.recent`, `approvals.pending`, `approval.decide`, `memory.list`, `skills.list`, `usage.local`, `panic`). Device offline returns a clear "device offline" result. Rate limits; owner session only. Extends M2C's live relay (X04). *Done when:* nothing from replies appears in Postgres, Redis (after delivery) or logs (Q06); an unlisted query name is refused; a different user cannot query someone else's device.

### MT-A06 · Versions and graduation · M · Wave 9

*Files:* `menux/src/menux/node/graduation.py`, tests. *What:* Spec versions (every change creates a new version; rollback). New automations start **attended** (outputs go to the owner for review) for N clean runs (default 5); then the node proposes **graduation to unattended** showing the exact policy. Any change to capabilities, tier or egress resets the trial. *Done when:* tests for the state machine and for capability changes resetting graduation.

### MT-W01 · Mate page and inbox (web) · L · Wave 10

*Files:* a new Mate page and navigation entry; components for **Needs you**, **Running now**, **Recent**; tests. *What:* Reads through the UI relay (K04). Approval cards show what, exact content, which automation, tier, and what happens if nothing is done; buttons per T03. Clear states for "device offline" and "no device paired". *Done when:* an approval raised on the device can be decided from the browser; offline behavior is understandable; node tests, lint and build pass.

### MT-Q01 · Automation eval harness · L · Wave 10

Fixture-driven runs (fake mailbox, calendar and files) of the sample automations in a sandbox, with graders and cost capture; records success, steps, credits, heartbeat skip rate. Extends `backend/evals/` and M2C's harness (Q02).

### MT-Q02 · Red-team suite v2 · L · Wave 10

Fixtures for injection through mail (headers, HTML, hidden text, calendar invites), filenames and document metadata, MCP descriptions, stranger messages, memory poisoning (added in Phase 3), skill exfiltration with canary secrets, vault extraction attempts, sandbox escapes, and heartbeat abuse. **A release is blocked if any "no unapproved egress, no external write, no secret read" test fails.**

### MT-Q04 · Canary test, extended · M · Wave 10

Extend M2C's no-content-at-rest test (Q06) to Menux: planner requests, run buffers, webhook relay, UI relay, ledger, logs and error reports must never contain canary content after the operation completes.

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

*Implements:* product guide §7. *Files:* `menux/src/menux/memory/{files.py,index.py,tools.py}`, tests. *What:* Plain Markdown under `~/.menux/memory/`: `MEMORY.md` (durable facts), `USER.md` (preferences), `daily/YYYY-MM-DD.md` (append-only). A **SQLite FTS5 index** (D9) over all of it. Tools `memory_search`, `memory_read`, `memory_write` for the automation profile. Every automatic write is shown to the owner with an undo. Secrets and sensitive categories are not auto-saved (redaction first). *Done when:* search ranks correctly on a fixture set; edits made by the user in an editor are reindexed; undo restores the previous text.

### MT-M03 · Memory poisoning defenses · M · Wave 13

Each memory line carries **provenance**: `owner` (typed by or confirmed by the owner) or `source:<kind>:<id>` (derived from external content). Only `owner` lines may be written as **instructions** ("always forward…", "never ask me about…"); external-source lines are facts only, tagged with their source. Instruction-like text from a non-owner source requires confirmation. The consolidation job never promotes untrusted lines to `MEMORY.md`. *Done when:* poisoned email, web and calendar fixtures never create an instruction line.

### MT-M02 · Consolidation job · M · Wave 13

A built-in system automation (cheap class, budget-capped, runs nightly when the node is up): merge duplicates, resolve contradictions (newest wins unless flagged), roll old daily notes into weekly summaries, propose skill drafts from repeated procedures (MT-M05). Shown in the inbox like any other automation.

### MT-M04 · Skills v2 with permission manifests · L · Wave 12

*Files:* `minicore/src/minicore/skills/manifest.py` and `menux/src/menux/skills/enforce.py`, tests. *What:* Build on the `SKILL.md` loader (C14). Parse the optional `permissions` block (folders, connectors, network, `tier_max`) and **enforce it at runtime**: a skill's scripts run only in the sandbox with exactly those mounts and egress domains; a skill that tries to exceed its manifest is stopped and logged. Skills without a manifest default to the strictest settings (no network, no connectors, read-only workspace). *Done when:* a skill with an undeclared network call fails in the sandbox test; manifest and automation policy intersect, never union.

### MT-M05 · Skill drafts and the review queue · L · Wave 13

*What:* After a successful multi-step run, a cheap-class job may **propose** a skill draft into `~/.menux/skills/_proposed/`. The review queue runs the server's **reviewer and security-reviewer roles** on it (content is transient), attaches findings and a diff against any existing skill, and shows it in the inbox. **Nothing activates without owner approval.** Approved skills get a version, a recorded dry-run test that must still pass, and a rollback button; usage stats (success, cost) per skill. *Done when:* a proposed skill that contains a network exfiltration is flagged and cannot be activated without an explicit override.

### MT-M06 · Knowledge folders index · M · Wave 13

User-chosen folders indexed with FTS5, with source paths kept for citations. Retrieval only on match. Re-indexing on file events. *Done when:* index respects the denylist and folder grants.

### MT-M07 · Export and import · S · Wave 13

Zip export of memory, skills and automations (no secrets); importers for common Markdown memory layouts used by other agent tools (check formats first).

### MT-N03 · Event triggers · M · Wave 12

*Files:* `menux/src/menux/node/triggers/{files.py,system.py}`, tests. *What:* File events (inotify via a maintained library or a polling fallback) with debounce, only inside granted folders; system events through D-Bus signals where available (disk space, network change, USB). Each event gets a dedupe ID and goes through the same lifecycle as a scheduled run.

### MT-H07 · Poll and RSS connector · S · Wave 12

Diff-based polling of feeds and pages; wakes the model only on change; page text is untrusted and tainting.

### MT-H08 · Webhook relay · L · Wave 12

*Implements:* §2 O1 (the only inbound content the server touches). *Files:* `backend/migrations/0017_mate_webhook_relay.sql`, `backend/mate/webhooks.py`, routes, `menux/src/menux/node/webhooks.py`, tests. *What:* The user creates a webhook on the device; the server stores only `webhook_id`, owner, device, a **hash** of the signing secret and limits. `POST /v1/mate/hook/{id}` verifies the signature, enforces size (D10) and rate limits, puts the payload into a **short-TTL Redis queue**, and forwards `relay.webhook` to the device if connected; the device acks and the server deletes the payload. Undelivered payloads are dropped at the TTL (the sender gets a documented status). Replay protection with timestamps and nonces. *Done when:* payloads never touch Postgres or logs; expired payloads vanish; a wrong signature or replay is rejected; the Q04 canary extension covers it.

### MT-G03 · Digest mode and formatting · S · Wave 12

Group routine outputs into one daily message; failures and approvals always go through immediately; per-channel formatting.

### MT-E01 · Server-side abuse and limits · M · Wave 12

Per-user concurrent automation runs, runs per hour and day, planner request limits, relay and webhook rate limits, and graceful `rate_limited` errors. Uses M2C's S11 Redis state. *Done when:* limits hold under a load test with a flood of scheduled runs.

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

### MT-A07 · Delegate to M2C · M · Wave 15

*Implements:* §3 D14. *What:* A capability `code_task(repo, prompt, mode)` (T3) that runs the installed `m2c -p` in **plan** mode by default through local IPC, so code work stays under M2C's sandbox and policy. Results come back as a summary the owner can open in M2C. Pushing or committing always needs an approval. Both products' ledger rows are tagged with their own surface. *Done when:* a CI-failure automation opens a plan-mode session and reports back; M2C not installed gives a clear error.

### MT-W02–W07 · Web surfaces · M each · Wave 15

- **W02** Automations list and detail (spec, versions, timeline, cost this month, pause, dry run).
- **W03** Approvals page (bulk view, filters, expiry countdown).
- **W04** Planner chat: describe an automation, see the draft spec and plain-language summary, the tier it needs and the credit estimate, dry run, approve.
- **W05** Usage by surface (extends X02: web, M2C, Menux, per-automation spend from the device).
- **W06** Memory and skills browser (read and edit through the relay; review queue).
- **W07** Devices page extension: show the node's status, last heartbeat, and the WSL keep-alive warning. All read from the device through the UI relay and show clear offline states.

### MT-N07 · Node `doctor` and WSL keep-alive · M · Wave 15

*What:* `menux doctor` reports: Linux or WSL2, systemd availability, service status, vault key source (and the "less secure" warning), keyring, sandbox probe, network proxy, clock skew, channel status, last successful scheduled run, and on **WSL2 whether a keep-alive is configured**. `menux wsl-keepalive` prints the exact steps and the Windows-side commands for the user to run (it does not touch Windows settings itself): a scheduled task at login that starts a long-lived `wsl.exe` process, plus the `.wslconfig` idle settings, with the caveat that these did not work on every version in community reports. *Done when:* tests mock each check; output is readable and actionable.

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

## 10. Phase 5 — The Companion Expansion

Phase 5 starts only after the beta milestone **MT-I04**. It grows Menux from Reach 0 (observe and notify) to Reach 4 (specialist tools and learning) and is split into three releases, each with its own acceptance milestone, so the plan can stop after any of them. The user-facing description is `menux_feature_guide.md` §17–§27; the rules are CX1–CX7 (§2) and decisions D15–D25 (§3).

Everything here is **Linux-native**. On WSL2 only Linux GUI apps are reachable until the Windows-side helper exists (CX2). Third-party components named below are **candidates**: no WP imports one until `R05` has recorded a licence decision (CX7). Sizes map roughly to points as S=1, M=2, L=4, XL=8.

| Release | Reach | Work packages | Points | Waves | Milestone |
| --- | --- | --- | --- | --- | --- |
| 5A Native control | 1–2 | 13 | 32 | 17–21 | MT-I05a |
| 5B Eyes and hands | 3 | 21 | 67 | 19–24 | MT-I05b |
| 5C Companion | 4 | 11 | 34 | 25–27 | MT-I05c |
| **Phase 5 total** | | **45** | **133** | | |

For scale: Phases 0–4 are 59 WPs and 133 points. Phase 5 is about the same again.

### 10.1 Phase 5A — Native control (Reach 1–2)

Commands, files, application scripting, accessibility and the safety layer that everything later depends on. No screenshots and no pointer yet.

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **R05** | Reuse-or-build licence review | S | 17 | – | Feature guide §27 (CX7). Read the licence of every candidate in the §27 table, classify it, and record a decision (dependency, separate process, study only, or build our own) in `docs/menux/third_party.md`; add `NOTICE` entries, pin versions, and write the own-build fallback plan for each. **Blocks** D01, D02, D03, S01, S02, S05, X03, X04, X08 and M12 from importing any candidate. *Done when:* every candidate has a recorded decision and CI fails if a dependency is missing from the record. |
| **N08** | Hardware and display probe for `doctor` | M | 17 | N07 | Extends N07. Reports CPU features, RAM, GPU and VRAM, display server (Wayland or X11), compositor, screencast and RemoteDesktop portals, `/dev/uinput` access, AT-SPI state and container runtime, then recommends the perception path (CPU-only or GPU) and explains every warning with a fix. *Done when:* fixtures for GNOME, KDE, Hyprland, i3, X11, no-GPU and GPU machines. |
| **K05** | Protocol 1.2 (vision and session messages) | S | 17 | K03 | Additive revision: image and element-list message parts with a `consent` field and size limits, `perception_path` in run metadata, event types for screen actions, and `mode` (`background`, `shared`, `takeover`). New files only. *Done when:* golden fixtures; M2C and Menux tests stay green. |
| **T10** | Context-based tiering, grants and the always-confirm list | L | 17 | T02, T03, T07 | Feature guide §6.6 and §22. A capability's tier may depend on context (for example `input.contained` is T1 inside a disposable virtual desktop with no accounts and T3–T4 on a profile with logged-in accounts or real files); scoped, time-limited, revocable **grants** replace step-by-step approval for T3–T4 inside their scope; the **always-confirm list** is a hard floor that grants and the dial cannot lower; unknown context is treated as the higher tier. *Done when:* tests for every row of the floor, grant expiry and revocation, panic revoking grants, and "a user cannot lower a tier by editing YAML" still holding. |
| **X01** | Shell and file tool in the sandbox (Reach 1) | M | 18 | K01, T10 | Runs commands through the `minicore` sandbox (`bubblewrap`); classifies each command by effect (read-only T0–T1, writes inside granted folders T2–T3, system changes T4, destructive T5); allow and deny lists, output caps, timeouts, dry run, and no network unless the automation's egress list allows it. Reuses M2C's shell tool through `minicore`. *Done when:* red-team cases for command injection, path escapes and destructive commands pass. |
| **X02** | Application control registry and ladder selector (Reach 2) | L | 18 | T01, H02, T10 | Per-application control profiles (id, window match, rungs available, tools, shortcut map, per-operation tier, quirks, measured reliability) and the selector from feature guide §18.3: highest reliable rung first, precondition and postcondition checks, one retry, step down, outcome recorded, Guide mode at the end of the line. New package `menux/src/menux/control/`. *Done when:* selector tests with fake apps for every rung, including "all rungs fail" ending in a message to the owner, never a silent failure. |
| **D01** | Dedicated browser profile (Playwright, optional install) | M | 18 | R05, T04, T06 | Unchanged from the earlier plan: separate profile, never the user's daily one; sandboxed; domains through the proxy allowlist; page text is untrusted and tainting. **Reuse (MiniLocker, `m2c_build_plan.md` §11.6):** URL-scheme refusal, page text returned as data with scan and fence, and `attacks/browser_attacks.py` as tests; the Docker and proxy parts are not reused, and approve-before-submit is new work. Registered in X02 as the application-native rung for web pages. |
| **D02** | AT-SPI reader (accessibility rung) | M | 18 | N08, R05 | Accessibility tree first: role plus name targeting; element references that expire; `doctor` reports whether accessibility is enabled and warns if a screen reader must be stopped. **Reuse candidate:** the `computer-use-linux` Rust MCP server (AT-SPI, window targeting for GNOME, KDE, Hyprland, i3 and COSMIC) if R05 clears its licence; otherwise build our own behind the same `ControlBackend` interface. |
| **X03** | LibreOffice control | L | 19 | X02 | Documents, spreadsheets and presentations through LibreOffice's headless UNO interface and macros: read, edit, convert, export to PDF, with no GUI and no pointer. *Done when:* a sample automation edits a spreadsheet while the user works in another window. |
| **X04** | Scriptable application adapters | L | 19 | X02 | FreeCAD, Blender and OpenSCAD through their Python or command-line interfaces; Inkscape and GIMP batch modes as optional adapters. Each adapter is a control profile plus a tested tool. Menux may draft further adapters itself later (X09). |
| **X05** | Shortcut maps and input maps | M | 19 | X02, D02 | Per-application shortcut tables and user-defined key maps (for example movement keys for a game); validation of maps; conflicts with the user's own shortcuts reported by `doctor`. |
| **Q06** | Control reliability benchmark | M | 20 | X03, X04, D02 | A fixed task set per application, per rung and per compositor, run on the reference machines; results published in `doctor` and in the docs. A rung below its published threshold is marked "ask first" by default. |
| **I05a** | Native control (acceptance) | M | 21 | R05, N08, K05, T10, X01, X02, X03, X04, X05, D01, D02, Q06 | See §10.5. |

### 10.2 Phase 5B — Eyes and hands (Reach 3)

The virtual desktop, live view and take-over, screen memory, vision grounding and the pointer layer, behind the dial and the GUI red-team suite. `D05` (attended control of the real desktop) is replaced by `V03` (Shared mode).

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **D03** | Screenshots and input | L | 19 | N08, R05 | Screencast portal for screenshots (may prompt each time); on Wayland the RemoteDesktop portal where available with `ydotool`/`uinput` as the fallback, `xdotool` on X11; per-compositor support matrix in `doctor`. **Reuse candidates:** `computer-use-linux` (portal and `ydotool` handling) and `ydotool` itself, both subject to R05 (`ydotool` is believed to be copyleft: verify, and if it does not fit, write to `uinput` directly or use the portal). |
| **D04** | Headless virtual desktop in a container | L | 19 | N08 | Xvfb or a headless Wayland compositor in a Podman container; disposable; no access to the real session; separate browser profile and files; egress through the allowlist. The substrate for V01. |
| **S05** | Vision grounding adapter, dual path | L | 20 | N08, D03, K05, R05 | Feature guide §21. One interface, `ground(screenshot, target) → element`, with a **CPU path** (accessibility first, CPU OCR, cloud grounding on a downscaled and cropped image, per-task consent) and a **GPU path** (local grounding model). Chosen by the `doctor` probe and overridable. Candidates: OmniParser, UI-TARS, GTA1, Holo, Moondream (licences and weights through R05). *Done when:* the same task suite passes on both paths on the reference machines. |
| **V01** | Virtual desktop session manager | L | 20 | D03, D04, T10 | Create, list, snapshot and destroy Menux sessions on D04; launch applications; separate profiles; resource limits; logged-in accounts only through explicit per-site grants (T10); `menux session` commands. *Done when:* two sessions run side by side without touching the user's own session. |
| **S01** | Screen capture engine | L | 20 | D02, D03, N05 | Event-driven capture (window focus, navigation, click, scroll or typing pause), de-duplication, throttling, idle and battery pause, exclusions (password managers, banking and payment pages, private windows, password fields), a visible indicator, a one-key pause. Local only. **Off by default.** Screenpipe is a design reference; its licence is reported inconsistently, so no code is copied before R05 decides. |
| **E03** | Server: vision metering and limits | M | 20 | E01, K05 | `/v1/mate/vision/*`; metering of cloud vision calls under `surface='menux'` through the shared `usage_ledger` (reserve migration `0021` only if the ledger cannot carry the new kind); per-user image-size and rate limits; no image stored after the run (extends the Q04 canary). |
| **S02** | Text extraction pipeline | L | 21 | S01, R05 | Accessibility text first, CPU OCR fallback (a Tesseract-class engine, licence through R05), optional local vision; secrets and card-number redaction before anything is stored; thumbnails kept at most 24 hours unless pinned; raw images deleted after extraction. |
| **V02** | Live view and take-over | L | 21 | V01 | An authenticated viewer bound to localhost for a Background session: watch, take over (the user's input goes to the virtual desktop) and hand back; every handover is logged. Remote viewing through the relay is not part of this WP. |
| **V03** | Shared mode and input arbitration (replaces D05) | L | 21 | V01, D03 | User-activity detector; Menux yields on any user input; a visible ghost cursor; resume after idle; automatic move to Background on conflict with a notification; every action visible; kill switch; never unattended on the real session. |
| **X06** | Pointer and keyboard action layer with verification | L | 21 | X02, D03, S05, T10 | Actions bound to element references from S05 or D02; stale-reference protection (a failed extraction clears cached elements); precondition and postcondition checks; checkpoints between steps; bounded multi-step plans where every step is verified. *Done when:* a fake-app suite and a real-app suite pass, and failure falls back to Guide mode. |
| **T11** | Reader/actor for pixels and the task-scope guard | L | 21 | T04, S05 | Feature guide §26. A tool-less Reader pass turns screenshots and screen text into a typed result (elements, roles, names, visible text as quoted data); the Actor sees only that. The run keeps its original task, and any off-task action (new domain, new application, terminal, download-and-run, permission dialog, credential field) escalates to approval. |
| **V04** | The tray control panel (the dial) | L | 21 | T10, T07 | Tray or hidden icon with quick toggles (screen awareness, screen memory, browser capture, mode, pause, panic), per-app allow/ask/block, global ceiling, active grants and hotkeys; a `menux dial` CLI where no tray exists; settings stored locally and surviving restart. |
| **V05** | Multi-pointer X11 spike (research) | S | 22 | V03 | Time-boxed. Can two independent pointers and focus points coexist on the user's screen? Output is a findings note only; the product does not depend on it. |
| **S03** | Screen memory store and search | M | 22 | S02, M01, N05 | `~/.menux/screen/` SQLite with FTS5 (no embeddings, decision D9), encrypted with a key derived from the vault key; provenance fields (time, app, window title, URL, source, trust label); retention defaults (proposed: text 30 days, thumbnails 24 hours); disk cap; "forget last N minutes", "forget app", "forget everything"; export. |
| **X07** | Guide mode | M | 22 | S02, X02 | When Menux may not or cannot act, it looks (if screen awareness is allowed) and tells the user the next step in words or as an on-screen hint. It sends no input and needs only T0–T1. |
| **Q07** | GUI red-team suite | L | 22 | X06, T11, V01 | **Blocks release.** Hostile web pages, fake dialogs and permission prompts, on-screen instructions, clipboard attacks, look-alike windows and drag-and-drop traps; pointer actions must stop when the target cannot be verified. |
| **S04** | Screen-memory tool for runs | M | 23 | S03, T04 | "What was that article I read on Tuesday?" queries S03; results pass through the Reader (T04), carry provenance and an untrusted label, and become durable memory only through M03 review. |
| **W08** | The Menux Map page | L | 23 | K04, A06, M04, X02 | Web page through the UI relay (K04): applications, connectors, channels, skills, automations and grants with their links, tier, last run and health; click through to open and edit the local spec or skill (edits go to the device, not the server); highlights grants wider than recent use. |
| **W09** | Screen-memory timeline and settings | M | 23 | S03, K04 | A scrollable timeline and search over S03, the indicator state, exclusions, retention settings and forget controls. Live relay only. |
| **Q08** | Screen-memory privacy and canary tests | M | 23 | S03, Q04 | Nothing from screen memory at rest on the server; exclusions hold; deletion is real (including indexes and backups); encryption at rest verified; a run cannot hide the indicator. |
| **I05b** | Eyes and hands (acceptance) | M | 24 | D03, D04, S05, V01, S01, E03, S02, V02, V03, X06, T11, V04, V05, S03, X07, Q07, S04, W08, W09, Q08 | See §10.5. |

### 10.3 Phase 5C — Companion (Reach 4)

Specialist tools, learning, sharing and games. `D07` is a design spike only.

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **X08** | Specialist tool kit | L | 25 | X02, R05 | A template and test harness for building a purpose-made tool for an application that has no scripting interface or an unreliable one (tool manifest, tier per operation, fixtures, sandboxed tests, versioning). First targets are chosen by user demand; CAD is the leading candidate. *Done when:* one tool for a listed application passes its fixtures. |
| **M09** | Experience memory | M | 25 | M01, X02 | Records which rung and steps worked for which application and task, with outcome and cost; consulted by the selector; local, viewable and deletable; labelled untrusted until confirmed by repeated success. |
| **N09** | Menux session image (optional) | L | 25 | N08, V01, D03 | An installable session (package or script first, later a VM or bootable image) with the display session, portals, `uinput` permission, accessibility and virtual-desktop tooling preconfigured. A full distribution is out of scope until after GA (D22). |
| **D07** | Windows-side helper: design spike | M | 25 | N07, N08 | Architecture and threat model for a small native Windows process in the user's session that exposes screenshots, input and Windows UI Automation to the WSL2 node over an authenticated local channel. Output: a design note and a review. **No product promise.** |
| **X09** | Self-built tools and adapters | L | 26 | X08, M05, T10 | Menux drafts an adapter script or tool for an application, tests it in the sandbox, and proposes it as a reviewed skill install (T4). Never self-activating. |
| **X10** | Game loop runner and input maps | L | 26 | X05, X06 | Opt-in game profile; a fast local loop (frame sampling, small decisions) with the large model as strategist; engine tools (for example a chess engine) run as separate processes after R05; runs on the virtual desktop; shows the anti-cheat notice; no circumvention. |
| **M10** | Learn by demonstration | L | 26 | S03, M05, X06 | Record mode captures the user doing a task (accessibility events and screen memory); Menux drafts a parameterized skill, dry-runs it, and queues it for review (M05). |
| **M11** | GUI skill self-repair | M | 26 | M09, A06, X06 | When a postcondition fails after a UI change, try another rung, propose a patched skill version, review it, and keep versions with rollback (A06). |
| **M12** | Skill templates and the curated library | L | 26 | M04, M05, Q02, T11, R05 | Sanitizer (strip paths, names, emails, tokens, IDs, URLs), parameterization, permission manifest, static scan, canary-secret sandbox trial, publisher identity and signature. The server stores only the template (migration `0020`), never the user's runs or data. Installing a template on another device shows the manifest, tier, egress and applications and stays disabled until the owner enables it. First-party curated library plus opt-in "submit for review"; the open marketplace is M08 (Phase 6). |
| **R06** | Companion docs and trust pages | M | 26 | R02, S03, V04 | The screen-memory trust copy, the perception-path explanation, the dial and grants guide, the WSL2 and Windows honesty page, and the licences page. |
| **I05c** | Companion (acceptance) | M | 27 | X08, M09, N09, D07, X09, X10, M10, M11, M12, R06 | See §10.5. |

### 10.4 Independent Phase 5 items

Not part of 5A–5C; schedule them when wanted, after `MT-I04`.

| WP | Title | Notes |
| --- | --- | --- |
| **D06** | Voice | Push-to-talk and voice notes through channels first; transcripts are treated as normal owner messages only from the paired device or channel. |
| **H09** | GitHub connector (token) | Read issues, PRs and CI; PR creation is T3 with approval. |
| **H10** | Slack and Discord | Owner-paired; stranger rules apply; group chats are untrusted. |
| **H11** | Home Assistant | Local network only; actions above T2 need approval. |
| **H13** | OAuth loopback client library | Loopback redirect with PKCE for connectors that need it; test it from a Windows browser into WSL2 (localhost forwarding is usually on, but verify). |

### 10.5 Exits

**MT-I05a · Native control (acceptance)**

- [ ] An automation runs a sandboxed shell command and a LibreOffice edit end to end, with tiers and approvals unchanged.
- [ ] The ladder selector uses the highest supported rung, steps down on failure, and ends in a message to the owner, never a silent failure.
- [ ] `menux doctor` reports hardware, display server, compositor, portals, `uinput` access, accessibility state and the recommended perception path, and explains each warning.
- [ ] The reliability benchmark (`Q06`) is published per application, rung and compositor.
- [ ] Browser automation passes the red-team suite.
- [ ] Every third-party component in use has a recorded licence decision and an own-build fallback (`R05`).
- [ ] No unattended control of the real session.

**MT-I05b · Eyes and hands (acceptance)**

- [ ] The user can watch, take over and hand back a Background session; in Shared mode Menux yields on user input within the agreed target.
- [ ] Screen memory is off by default, the indicator is visible, exclusions hold, "forget" really deletes, and encryption at rest is verified (`Q08`).
- [ ] The CPU-only and GPU paths pass the same task suite on the reference machines; the CPU path never sends an image without consent.
- [ ] The GUI red-team suite (`Q07`) is green and the canary shows no screen content at rest on the server.
- [ ] Panic suspends the virtual desktop, stops input and revokes all grants, and survives a restart.
- [ ] The Menux Map shows every application, connector, automation and grant, and edits round-trip to the local specifications.
- [ ] The always-confirm list holds in every mode, with and without grants.

**MT-I05c · Companion (acceptance)**

- [ ] A skill learned by demonstration is replayed, repaired after a UI change, and rolled back.
- [ ] A skill template installs on a second device only after review, stays disabled until enabled, and contains no personal string from the seeded canary.
- [ ] The game loop completes a chess game and a user-defined input-map task on the virtual desktop, shows the anti-cheat notice, and does not bypass anything.
- [ ] The specialist tool kit produces at least one working tool for a listed application.
- [ ] The Windows-helper design and threat model (`D07`) have been reviewed and a go or no-go recorded.
- [ ] The trust pages match the system's behavior (`R06`).

---

## 11. Phase 6 — Ecosystem and release

| WP | Title | Notes |
| --- | --- | --- |
| **M08** | Marketplace with scanning and signing | Migration `0019`; permission manifests required; static scan, sandboxed trial with canary secrets, publisher verification, signing, yanking; **community content off by default**. Builds on the template pipeline and curated library from `M12` (Phase 5C). |
| **D08** | Windows-side helper: build | Only if the `D07` design and threat model pass review. A native Windows process in the user's session; authenticated local channel to the WSL2 node; same tiers, grants and audit log; its own security review before release. |
| **T09** | Team policy | Managed settings, shared automations, audit export. |
| **H12** | Google connectors (if approved) | Only after legal review of Google's Limited Use terms and a budget for verification and the annual CASA assessment (O5). |
| **—** | Cloud-hosted automations (decision D12) | Separate trust model, explicit opt-in, disclosure that specs and credentials live on your servers. |
| **—** | External security audit | Scope: vault, relay and webhook paths, unattended policy, approvals, sandbox, skills enforcement. The gate for GA. |
| **R01** | Packaging | `menux` and `minicore` on PyPI; the installer offers M2C, Menux or both; `menux update`; signed releases. |
| **R03** | Legal and privacy | Sub-processors including Telegram's role, retention (webhook TTL, run buffer), terms for acting on the user's behalf. |
| **R04** | Support tooling | Content-free diagnostics, device revoke, credit adjustments, status page. |

GA checklist: audit findings closed; red-team, soak and canary suites green on the release build; fresh-install tests on Ubuntu, Debian, Fedora and WSL2 Ubuntu (with and without keep-alive); shared-cap behavior verified across web, M2C and Menux; trust copy matches the system's behavior.

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
| Tidy my spreadsheet in LibreOffice while I work | X01, X02, X03 (no pointer, no conflict with the user) |
| What was that article I read on Tuesday? | S01, S02, S03, S04, T04 |
| Build me a part in FreeCAD or OpenSCAD | X02, X04 (specialist tool via X08 for harder CAD) |
| Fill in this web form, and ask me before submitting | D01, X02, T10 (approve-before-submit is T4) |
| Do this task in an app I can't script | D02, D03, S05, X06, V01 (Background), T11 |
| Learn this by watching me do it once | S03, M05, M10, then M11 for repairs |
| Play a chess game with me | X05, X06, X10 |
| Show me what Menux is connected to, and let me edit it | W08, K04, A06 |
| Tell me the next step in an app Menux can't control | S02, X07 (Guide mode) |

---

## 13. Tests and commands

| Area | Command | Notes |
| --- | --- | --- |
| Backend | `cd backend && pytest tests/unit tests/integration -v` | Includes `backend/mate` tests |
| Core | `cd minicore && pytest` | Must stay green for both products |
| M2C | `cd m2c && pytest` | Unchanged by Menux work |
| Menux | `cd menux && pytest` | Sandbox tests skip loudly if `bwrap` is missing |
| Protocol | `python protocol/validate.py` | Includes the 1.1 fixtures |
| Frontend | `cd frontend && npm test && npx next lint && npx next build` |  |
| Evals | `python -m evals.menux.run --suite automations` | Costs real credits |
| Red team | `pytest menux/tests/redteam -v` | Blocks release |
| Canary | `pytest backend/tests/integration/test_no_content_at_rest.py` | Extended by MT-Q04 |
| Soak | `pytest menux/tests/soak -v` | Fake clock; slow |
| GUI red team | `pytest menux/tests/redteam_gui -v` | Q07; blocks Phase 5B release |
| Screen-memory privacy | `pytest menux/tests/screen_privacy -v` and the extended canary | Q08, Q04; blocks Phase 5B release |
| Control reliability | `python -m evals.menux.run --suite control` | Q06; costs real credits on the CPU path; results go to `doctor` |
| Licence record | `python scripts/check_third_party.py` | R05; fails if a dependency is missing from `docs/menux/third_party.md` |

---

## 14. Risks of the build itself

| Risk | Mitigation |
| --- | --- |
| This plan's assumptions about M2C are wrong | MT-K00 inventory first; fix the inventory, not the patches |
| Extracting `minicore` breaks M2C | K01 is move-only; M2C's tests are the safety net; keep re-export shims |
| Unattended features arrive before the safety layer | The Phase 2 gate; T02–T08 and Q02 block anything above T2 |
| WSL2 users see "my automation didn't run" | `doctor` and docs say plainly that WSL must be running; guided keep-alive; recommend an always-on Linux box |
| Gmail integration costs more than expected | IMAP first; legal and budget decision before H12 |
| Telegram leaks detail the user thought stayed local | `channel_detail: minimal` default; trust copy names Telegram |
| Notification fatigue | Digests, graduation flow, anomaly pauses |
| Heartbeat costs | Local pre-checks, zero-call skips, quiet hours, 60-minute default, budgets |
| Marketplace or skill supply-chain incident | No marketplace before Phase 6; manifests enforced; canary trials |
| Scope explosion ("agentic OS") | Phase gates; Phase 5 starts only after the beta; 5A, 5B and 5C are separately releasable; Phases 0–4 stay at 59 WPs / 133 pts |
| The Companion is about as large as all of v1 | Say so in planning (Phase 5 is about the size of Phases 0–4); do not schedule it inside the March–June 2027 window; stop after any sub-phase if needed |
| Pointer and vision control is less reliable than users expect | The ladder prefers reliable rungs; verification around every action; Guide mode; published benchmark (Q06); weak rungs default to "ask first"; the docs say plainly what is slow or fragile |
| Screen memory becomes a privacy incident | Off by default; visible indicator; text first; raw images deleted; exclusions; encryption with a vault-derived key; nothing on the server; Q08; trust copy and legal review (R03) updated before 5B ships |
| Prompt injection through pixels or on-screen text | Reader for pixels and the task-scope guard (T11); Q07; scoped, time-limited grants; always-confirm floor |
| Tier-by-context is wrong somewhere and contained input is not really contained | Default to the higher tier when context is unclear; Q07 tests escapes from the virtual desktop; the session has no accounts and allowlisted egress |
| Wayland and compositor variability | `doctor` matrix; portals first, `uinput` fallback; X11 fallback; session image (N09); Q06 numbers per compositor |
| A licence surprise (copyleft, AGPL weights, source-available) | `R05` first; interfaces around every candidate; own-build fallback written in advance |
| Shared skills become a supply-chain attack | Templates only; sanitizer; manifests; scan; canary trial; signing; installed disabled; community content off by default |
| CPU-only users get a poor experience, or GPU users get a different product | One interface with two implementations; the same task suite must pass on both; CPU path text-first with consent for images |
| Users set "Full control" and get hurt | The always-confirm floor; time-limited grants; panic; every action logged and reviewable |
| Solo-founder capacity | Waves are a ceiling; Phase 0 to I01 is the proof; Phase 2 is the minimum before anyone else runs it |

**Stop the line:** any red-team or canary failure; a patch that weakens a policy, tier or vault check; an M2C test turning red; a migration number used twice; two applied patches disagreeing about the protocol.

---

## 15. Work-package index

| ID | Title | Phase | Wave | Depends on | Size |
| --- | --- | --- | --- | --- | --- |
| K00 | Inventory of M2C (read-only) | 0 | 1 | M2C M2 | S |
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
| A07 | Delegate to M2C | 4 | 15 | I01 | M |
| W02–W07 | Web surfaces | 4 | 15 | W01 | M each |
| N07 | Doctor and WSL keep-alive | 4 | 15 | I01 | M |
| E02 | Cost estimates | 4 | 15 | A02 | S |
| Q05 | Cost telemetry | 4 | 15 | I01 | S |
| R02 | Docs and trust pages | 4 | 15 | I01 | M |
| I04 | Beta acceptance | 4 | 16 | Phase 4 | M |
| R05 | Reuse-or-build licence review | 5A | 17 | – | S |
| N08 | Hardware and display probe for `doctor` | 5A | 17 | N07 | M |
| K05 | Protocol 1.2 (vision and session messages) | 5A | 17 | K03 | S |
| T10 | Context-based tiering, grants and the always-confirm list | 5A | 17 | T02, T03, T07 | L |
| X01 | Shell and file tool in the sandbox (Reach 1) | 5A | 18 | K01, T10 | M |
| X02 | Application control registry and ladder selector (Reach 2) | 5A | 18 | T01, H02, T10 | L |
| D01 | Dedicated browser profile (Playwright, optional install) | 5A | 18 | R05, T04, T06 | M |
| D02 | AT-SPI reader (accessibility rung) | 5A | 18 | N08, R05 | M |
| X03 | LibreOffice control | 5A | 19 | X02 | L |
| X04 | Scriptable application adapters | 5A | 19 | X02 | L |
| X05 | Shortcut maps and input maps | 5A | 19 | X02, D02 | M |
| Q06 | Control reliability benchmark | 5A | 20 | X03, X04, D02 | M |
| I05a | Native control (acceptance) | 5A | 21 | R05, N08, K05, T10, X01, X02, X03, X04, X05, D01, D02, Q06 | M |
| D03 | Screenshots and input | 5B | 19 | N08, R05 | L |
| D04 | Headless virtual desktop in a container | 5B | 19 | N08 | L |
| S05 | Vision grounding adapter, dual path | 5B | 20 | N08, D03, K05, R05 | L |
| V01 | Virtual desktop session manager | 5B | 20 | D03, D04, T10 | L |
| S01 | Screen capture engine | 5B | 20 | D02, D03, N05 | L |
| E03 | Server: vision metering and limits | 5B | 20 | E01, K05 | M |
| S02 | Text extraction pipeline | 5B | 21 | S01, R05 | L |
| V02 | Live view and take-over | 5B | 21 | V01 | L |
| V03 | Shared mode and input arbitration (replaces D05) | 5B | 21 | V01, D03 | L |
| X06 | Pointer and keyboard action layer with verification | 5B | 21 | X02, D03, S05, T10 | L |
| T11 | Reader/actor for pixels and the task-scope guard | 5B | 21 | T04, S05 | L |
| V04 | The tray control panel (the dial) | 5B | 21 | T10, T07 | L |
| V05 | Multi-pointer X11 spike (research) | 5B | 22 | V03 | S |
| S03 | Screen memory store and search | 5B | 22 | S02, M01, N05 | M |
| X07 | Guide mode | 5B | 22 | S02, X02 | M |
| Q07 | GUI red-team suite | 5B | 22 | X06, T11, V01 | L |
| S04 | Screen-memory tool for runs | 5B | 23 | S03, T04 | M |
| W08 | The Menux Map page | 5B | 23 | K04, A06, M04, X02 | L |
| W09 | Screen-memory timeline and settings | 5B | 23 | S03, K04 | M |
| Q08 | Screen-memory privacy and canary tests | 5B | 23 | S03, Q04 | M |
| I05b | Eyes and hands (acceptance) | 5B | 24 | D03, D04, S05, V01, S01, E03, S02, V02, V03, X06, T11, V04, V05, S03, X07, Q07, S04, W08, W09, Q08 | M |
| X08 | Specialist tool kit | 5C | 25 | X02, R05 | L |
| M09 | Experience memory | 5C | 25 | M01, X02 | M |
| N09 | Menux session image (optional) | 5C | 25 | N08, V01, D03 | L |
| D07 | Windows-side helper: design spike | 5C | 25 | N07, N08 | M |
| X09 | Self-built tools and adapters | 5C | 26 | X08, M05, T10 | L |
| X10 | Game loop runner and input maps | 5C | 26 | X05, X06 | L |
| M10 | Learn by demonstration | 5C | 26 | S03, M05, X06 | L |
| M11 | GUI skill self-repair | 5C | 26 | M09, A06, X06 | M |
| M12 | Skill templates and the curated library | 5C | 26 | M04, M05, Q02, T11, R05 | L |
| R06 | Companion docs and trust pages | 5C | 26 | R02, S03, V04 | M |
| I05c | Companion (acceptance) | 5C | 27 | X08, M09, N09, D07, X09, X10, M10, M11, M12, R06 | M |
| D06, H09–H11, H13 | Independent Phase 5 items | 5 | unscheduled | per WP | M–L |
| D08 | Windows-side helper: build | 6 | 28 | D07 | XL |
| M08, T09, H12, R01, R03, R04, audit | Phase 6 items | 6 | 28+ | per WP | M–XL |

---

## 16. Your first week on Menux

1. **Confirm M2C has reached M2** and every §1 row is present. If not, finish those M2C WPs first.
2. **Lock decisions D1–D10 and D13** (D11 and D12 can wait).
3. **Wave 1 in parallel:** K00 (read-only), A01, T01.
4. **Wave 2 in parallel:** K01 (the careful one: run M2C's whole test suite before and after), K02, K03.
5. **Then Phase 1.** When "send me a good-morning message at 07:30" works end to end on your own machine, charged to your own pool, with nothing stored on your servers, the design is proven and Phase 2 (safety) is the next thing, not more features.
6. **The Companion Expansion (Phase 5) is not part of your first week, or your first months.** It starts only after the beta (`MT-I04`). When it does, begin with `R05` (licence record), `N08` (hardware probe), `K05` and `T10` (the safety layer), and release 5A before touching a screenshot.

*End of the Menux build guide.*