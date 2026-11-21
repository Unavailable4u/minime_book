# Menux — Build Execution Guide

*Minime agentic automation*

### From "M2C is done" to a personal automation system: ordered, parallelizable, patch-sized work packages

*Version 1.3 · 2026-11-21 (1.2: 2026-11-14) · companion to `menux_guide.md` (what to build), `m2c_build_plan.md` (how M2C is built, whose patch workflow this guide reuses) and `m2c_guide.md`. Where this guide and `menux_guide.md` disagree, **this guide wins** (§2).*

> **Revision 1.1 (2026-10-26): the Companion Expansion.** Phase 5 is rewritten and split into **5A (native control), 5B (eyes and hands) and 5C (companion)** (§10); new tracks `X`, `V` and `S` (§4.2); new decisions D15–D25 (§3); extensions CX1–CX7 and the Companion trust copy (§2); new reserved numbers (§4.5); new waves 17–27 (§4.6); new tests, risks and index rows. **Phases 0–4 are unchanged: 59 work packages, 16 waves, 133 points.** Phase 5 adds 45 work packages and about 133 points and starts only after `MT-I04`. The user-facing description is in `menux_feature_guide.md` §17–§27.

> **Revision 1.2 (2026-11-14): the device mesh and cross-platform control.** Two new phases after 5C: **5R (remote control and the device mesh)** and **5P (platforms and satellites)** (§10.6, §10.7). A phone, a browser, a chat app or a second computer linked to the MiniMe account can control, approve and sync with a node; Windows and macOS are reached through **satellites** that use agent-desktop as the accessibility backend. New extensions MX1–MX9 and the mesh trust copy (§2); new decisions D26–D38 (§3); new track `P` (§4.2); reserved migrations `0022` and `0023`, a separate protocol namespace `protocol/mesh/v1` and the route `WS /v1/mate/mesh` (§4.5); waves 28–34 (§4.6). **The Windows-side helper (`D07`, `D08`) is replaced by the Windows satellite `P03`; `D02` is re-scoped from M to L; `R05` gains the new candidates.** **Phases 0–4 are unchanged: 59 work packages, 16 waves, 133 points.** Phase 5 is now 68 work packages and about 204 points (5A 13/34, 5B 21/67, 5C 10/32, 5R 17/49, 5P 7/22). One M2C follow-up is needed first: `S03b`, device self-revoke (§1). The user-facing description is in `menux_feature_guide.md` §28–§37.

> **Revision 1.3 (2026-11-21): usability, reach and evidence.** Written after reading the shipped open-source agent Mercury Agent (`menux_feature_guide.md` §40), the M2C code at `3727ae3`, the Migration Guide (Appendix A) and the Provider Consolidation Guide (Appendix B). It closes the gaps that comparison found without touching the safety design. **New track `U`** (§4.2) and a new **Phase 4U** (§9.1): `U01` recipes (automations that need no model), `U02` starter templates and a guided `menux init`, `U03` degraded mode, `U06` the security evidence pack, and `Q11` a scripted-model scenario harness: 5 work packages, 8 points, **recommended before `MT-I04` and not counted in the 59 work packages and 133 points of Phases 0–4, which are unchanged (16 waves)**. **Phase 5P gains `U05`**, a limited native Windows and macOS node that is built only if `P06` passes written criteria (§10.7); Phase 5 is now 69 work packages and about 208 points. `D06` (voice) is extended, not duplicated. **New decisions D39–D46** (§3); the matching user-facing rules `UX1–UX6` are in `menux_feature_guide.md`. **Language:** file names ending `.py` in this guide are the Python reference names; whether the node is built in Rust is decided by the gate `MG-Z10` in Appendix A (§1.1), and nothing in this guide changes either way except the file extensions.

---

## 0. How to use this guide

The patch workflow is the one in `m2c_build_plan.md` §0 (one work package = one patch, tests first, git worktrees for parallel patches, apply in wave order, log in `PATCHES.md`, regenerate rather than hand-edit hunks, stop-the-line rules in §13 there). Differences for Menux:

- **IDs use the prefix `MT-`** (for example `MT-N02`). Patch files: `MT_N02_scheduler.patch`, kept in `patches/`.
- **Most new code lives in new packages** (`minicore/`, `menux/`, `backend/mate/`), so conflicts are rare; §4.4 lists the few shared files.
- **Companion work packages (Phase 5)** reuse the existing track letters where they fit (`D`, `M`, `T`, `Q`, `R`, `K`, `N`, `E`, `W`, `I`) and add three: `X` (control), `V` (virtual desktop and the control panel) and `S` (screen memory and vision). Revision 1.2 adds a fourth, `P` (platforms and satellites). Size labels map to points roughly as S=1, M=2, L=4, XL=8; this is an approximation of how the 133 points of Phases 0–4 were counted.
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
| Device **self-revoke** endpoint (`POST /v1/code/devices/revoke`, proposed in `m2c/src/m2c/auth/login.py`; today `m2c logout` only deletes the local credential) | **S03b** (new M2C follow-up, not counted in Menux's totals) | `menux logout` revoking the device, and the mesh distrusting it (Phase 5R, `E04`, `N11`) |
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
- **Desktop control on WSL2 only reaches Linux GUI apps inside WSLg, not Windows applications.** Do not promise Windows automation. The Companion Expansion keeps this limit at launch. Revision 1.2 replaces the planned Windows-side helper (`D07`, `D08`) with the **Windows satellite** `P03` (Phase 5P, using agent-desktop), paired to the WSL2 node over loopback or the relay (CX2, D36). The node itself stays Linux.
- Windows folders (`/mnt/c/...`) can be granted **read-only by default**, with a warning about speed and permission quirks.
- macOS and native Windows **nodes**: not supported (a time-boxed spike, `P06`, studies it). Windows and macOS **satellites** are planned in Phase 5P.

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
| **CX2** | Linux first, WSL2 second | Native Linux gets everything. WSL2 gets everything that runs inside Linux. Windows and macOS applications are controlled through a **satellite** paired to a node (`P02–P04`, Phase 5P, using agent-desktop); the Windows-side helper (`D07`, `D08`) is replaced by `P03`. A Windows-only or Mac-only user still needs a node. No promise before 5P | P02, P03, P04, N08 |
| **CX3** | The user always wins | Pointer work defaults to the virtual desktop (Background). On the real screen Menux takes turns and yields on any user input. The user can watch, take over and hand back | D04, V01–V03 |
| **CX4** | Screen memory: local, off by default, visible | Event-driven, text first, raw images deleted after extraction, sensitive apps excluded, encrypted with a vault-derived key, never stored on the server, indicator always visible, one-key pause | S01–S04, Q08 |
| **CX5** | Two perception paths | Everything that sees has a CPU-only path (accessibility and CPU OCR, cloud grounding only with consent) and a GPU path (local models). `doctor` recommends one; the user can override | N08, S05, E03 |
| **CX6** | Skills shared as sanitized, signed templates | Real automations and data never leave the device. Templates are stripped, parameterized, scanned, trialled with canary secrets, signed, installed disabled | M12 (curated), M08 (marketplace) |
| **CX7** | Reuse or build, after a licence check | No candidate is imported before `R05` records a decision; every candidate sits behind a Menux interface with an own-build fallback | R05 |

**Tier follows effect and context (T10).** The capability registry may assign a tier by context. `input.contained` (pointer and keyboard input inside a disposable virtual desktop with no accounts, no real files and allowlisted egress only) is T1; the same input on a logged-in profile or the real desktop is T3–T4. Unknown context takes the higher tier. **Grants** (scoped, time-limited, revocable) substitute for per-step approval of T3–T4 inside their scope and never cover the **always-confirm list**: payments; passwords, keys and vault export; deleting files outside staging or granted scratch; sending to a new third party or destination; changing the dial, grants, policy or logging; installing software, tools or skills; any unrecognized capability or context. This rule must be validated by the GUI red-team suite (Q07) before Phase 5B is released.

### Trust copy for the Companion (addendum to O8)

> **What Menux sees.** Screen awareness and screen memory are off until you turn them on, and an indicator is visible whenever they run. Menux reads text from your screen on your device and keeps it, encrypted, on your device. Password managers, banking pages and private windows are excluded by default. When a task needs a model to look at a screenshot, only that image, or a text description of it, is sent, only with your permission, and we don't keep it after the run ends. Menux works on its own virtual desktop by default and steps aside the moment you use your mouse or keyboard. Some actions, such as payments, deleting files, using passwords and sending to someone new, always need your confirmation. You can pause, search, export or delete everything Menux remembers at any time.

### Mesh extensions (MX1–MX9)

Added in revision 1.2. They govern the device mesh (Phases 5R and 5P) and sit beside O1–O8 and CX1–CX7; they never relax them. The user-facing description is `menux_feature_guide.md` §28–§37.

| # | Extension | Rule | Where it is built |
| --- | --- | --- | --- |
| **MX1** | Three roles | A device is a **node** (the full Menux and the only place a run lives), a **satellite** (executes a limited set of capabilities for a node) or a **controller** (sends commands and approvals, executes nothing). A device may hold more than one role | K06, N10, P02 |
| **MX2** | Local policy is final | The device that executes an action applies its own tiers, grants and dial. A remote origin can keep or raise a tier, never lower it. A satellite's dial can only narrow what the node may do | T12, T13, P02 |
| **MX3** | The server is a pipe | The relay forwards end-to-end encrypted, signed frames. It cannot read them, forge a command, replay one, add a controller or approve at T4 or above. It sees metadata only | K06, T12, E04, Q09 |
| **MX4** | Node-approved pairing | Adding a controller or satellite needs approval **on the node** (or from an already-trusted trusted-display controller with step-up, never above its own ceiling). A stolen MiniMe login is not enough | N11, K06 |
| **MX5** | Controller classes cap remote power | Local, trusted display, web, chat. The web class is capped at T3 and chat approvals at T3 because their code or transport is not ours to trust; T4 needs a trusted display with step-up; T5 and vault export are local only | T13, T14, G05, W11 |
| **MX6** | Panic and deny always work | From every controller, with no step-up, reaching every node in the mesh, surviving restart and retried until acknowledged | T12, N10 |
| **MX7** | Sync is opt-in and never moves secrets | Per category, off by default. The vault, connector tokens, screen memory and the knowledge index never sync. Records are encrypted with a mesh key; an offline peer gets an encrypted mailbox of at most 24 hours | M13, E04, Q10 |
| **MX8** | Tighten at once, loosen with care | Panic, lower ceilings, new exclusions and paused devices propagate immediately from any controller. Raising a limit does not propagate; it is done on the device or from a trusted display with step-up | T13, M13 |
| **MX9** | Backends behind interfaces | agent-desktop and every other control backend sit behind `ControlBackend` (CX7), run as a pinned separate process, and have every command in the capability registry; an unknown command is T5 and denied | D02, P03, P04, R05 |

### Trust copy for the mesh (addendum to O8)

> **Your devices.** Linking a phone, tablet or another computer lets it send commands to your Menux node, up to the limit you set for that device. Every new device must also be approved on your node, so the website alone cannot add one. Commands and approvals are signed on your device and encrypted end to end; our servers pass them along but cannot read or forge them, and they see only that a device talked to another and when. A phone or browser can approve routine actions; actions that change your system need a device that shows you exactly what you are approving, and the most dangerous ones can only be approved at the node itself. If you turn on sync, your automations, skills and notes are encrypted before they leave your device, and a copy waits on our servers for at most 24 hours if your other device is offline. Your vault, passwords and screen memory never sync. You can pause, limit or remove any device, and Panic works from all of them.

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
| D23 | Windows | **WSL2 at launch with honest limits; Windows reached through a satellite (`P03`, Phase 5P); the earlier helper spike and build (`D07`, `D08`) are replaced** | CX2; see D35 and D36 |
| D24 | Games | **Opt-in game profile; strategy, turn-based and slow live tasks; no anti-cheat circumvention; notice shown** | Real-time action titles are out of scope |
| D25 | Context-based tiering | **Tier follows effect and context; contained input in a disposable session is T1; grants are scoped and time-limited; always-confirm list is a hard floor** | `T10`; validated by `Q07` |
| D26 | Device roles | **Node, satellite and controller (MX1).** A computer node is Linux, WSL2 or a mini-PC; satellites are Windows, macOS or a second Linux box; controllers are phone or browser, `menux remote` and chat | A satellite needs a node |
| D27 | Mesh transport and protocol | **A separate namespace `protocol/mesh/v1` and a separate socket `WS /v1/mate/mesh`**; the M2C v1 envelope is not touched. Relay by default; a direct local link (loopback on by default, LAN off by default) when available | M2C's v1 envelope enum is closed, so mesh messages must not be added to it |
| D28 | Pairing | **Node-approved**, with a six-word fingerprint shown on both sides and the ceiling chosen on the node. A trusted-display controller with step-up may approve a new controller below its own ceiling | MX4 |
| D29 | Crypto | **Per-device identity keys and an authenticated key exchange with end-to-end encrypted frames.** Candidates: Ed25519, X25519, a Noise-style handshake; library chosen in `R05` behind a Menux interface with an own-build fallback | No custom primitives |
| D30 | Controller classes and ceilings | **Local up to T5; trusted display up to T4; web up to T3 (never a trusted display); chat approvals up to T3 and no T4**; T5, vault export, key changes and loosening the dial are local only | MX5 |
| D31 | Step-up | **WebAuthn passkey assertion bound to the approval ID, nonce, action digest and expiry, verified by the node** against the public key stored at pairing | T14 |
| D32 | Sync | **Opt-in per category, off by default; mesh key; encrypted mailbox of at most 24 hours (proposed); tombstones kept 30 days (proposed); never the vault, connector tokens, screen memory or the knowledge index** | MX7 |
| D33 | Leases and failover | **One writer per scheduled automation, held by a short server-kept lease (proposed 90 seconds, renewed every 30); failover is off unless the spec says `failover: true`; when the server is unreachable a node skips rather than duplicates** | N12 |
| D34 | Command lifetimes | **Status and pause may wait up to 10 minutes; anything T2 or above is never queued and never replayed after expiry; clock-skew window 120 seconds (all proposed)** | T12 |
| D35 | agent-desktop | **Use it as the accessibility rung on Linux, Windows and macOS, as a pinned separate process behind `ControlBackend`, after `R05` clears its licence; our own AT-SPI reader stays as the fallback on Linux** | MX9; supersedes the "build our own Windows helper" path in D23 |
| D36 | Windows and macOS strategy | **Satellites paired to a node, not a native node in v1.** A Windows-only or Mac-only user needs WSL2, a Linux box or a mini-PC. `P06` is a time-boxed spike on a native node; **revision 1.3: it has written acceptance criteria and may unlock a limited native node (`U05`, decision D43)** | Replaces `D07` and `D08` |
| D37 | Mobile | **The installable web app is the phone controller (web class, up to T3, passkey step-up). No native mobile app in this plan**; `menux remote` on a computer is the trusted-display controller | Revisit after 5R |
| D38 | Remote live view | **View only for the web class; take-over needs a trusted display with step-up; end-to-end encrypted; nothing recorded or stored on the server; a visible indicator on the desktop; own security review** | `V06` |
| D39 | Security does not depend on the model | **Tiers, approvals, the reader/actor requirement, unattended taint denial and the always-confirm list are enforced in code and never vary with the model, its size or its plan. No setting, flag or "strong model" mode relaxes them** | `Q11` proves identical decisions across model labels. Prior art: another agent relaxed its injection prompts for strong models and later had to tighten them for unattended runs (`menux_feature_guide.md` §40) |
| D40 | Recipes | **`kind: recipe` automations run a fixed list of steps from a closed action catalogue: no model call, zero credits, no server needed. Same tiers, dry run and graduation; the unattended ceiling stays T2** | `U01` |
| D41 | Degraded mode | **The node never stops silently. With no server, an exhausted pool or a paused account, recipes keep running, model runs follow the spec's missed-run policy, and the owner is told once per state change** | `U03` |
| D42 | First value | **Six signed starter templates and a guided `menux init`. Templates install disabled, run a dry run, then run attended, and graduate like any automation. The docs publish the measured number of owner actions from install to first success** | `U02` |
| D43 | Native Windows and macOS | **`P06` gets written acceptance criteria. If it passes, a limited native node (`U05`) is built: scheduler, OS key-store vault, channels, read connectors, recipes and sealed tools. No shell tool, skill scripts or browser sidecar, and nothing above T2, until an OS sandbox exists. If `P06` fails, D36 stands** | Refines D36 |
| D44 | Openness and evidence | **Decide by `R05` whether the node, satellites and protocol are published as source under a licence the owner chooses (recommendation: publish them, keep the server private). Publish a security evidence pack with every release (`U06`)** | Proposed; M2C's own licence decision (its D11) is still open |
| D45 | Channels beyond Telegram, Slack and Discord | **WhatsApp and Signal are not planned until a licence and terms review (the `R05` pattern) finds a permitted path. No unofficial client library is used on an owner's personal account** | `menux_feature_guide.md` §15.7 |
| D46 | Model classes by plan | **Menux on Basic and Free runs on the four paid models of the Provider Consolidation Guide (Appendix B), the Standard class. Advanced, Expert and the Brain exist only when Moderate and Ultimate launch (its PD-6). Cost estimates (`E02`) and budgets name the class** | `menux_feature_guide.md` §12.5 |

D15–D25 are Companion decisions. They can wait until the beta is under way, but must be locked before the first Phase 5 patch.

D26–D38 are mesh decisions. They must be locked before the first Phase 5R patch.

D39–D46 are revision 1.3 decisions. Lock D39 before the first Phase 2 patch (`T02`); D40 and D41 before `U01`; D42 before `U02`; D43 before `P06`; D44 and D45 before `R05`; D46 before `E02`.

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
| **4U** | Usability and reach (revision 1.3) | Recipes, starter templates and guided first run, degraded mode, scripted-model scenario harness, security evidence pack | Recommended before **MT-I04**; not counted in Phases 0–4 |
| **5A** | Native control (Reach 1–2) | Licence record, hardware probe, protocol 1.2, context-based tiering and grants, shell and file tool, application registry and ladder selector, LibreOffice and app adapters, AT-SPI, shortcut and input maps, browser profile, reliability benchmark | **MT-I05a** |
| **5B** | Eyes and hands (Reach 3) | Screenshots and input, virtual desktop with live view and take-over, shared mode, tray dial, screen memory, dual-path grounding, pointer layer with verification, guide mode, Menux Map, GUI red-team and privacy suites | **MT-I05b** |
| **5C** | Companion (Reach 4) | Specialist tool kit and self-built tools, experience memory, learning by demonstration, self-repair, skill templates and curated library, game loop, session image | **MT-I05c** |
| **5R** | Remote control and the device mesh | Mesh protocol and device identity, signed commands, controller classes and the remote trust ladder, passkey step-up, node-approved pairing, mesh relay, Devices page, phone and web controller, chat hardening, sync spaces, placement and leases, remote live view, mesh red-team and privacy suites | **MT-I05r** |
| **5P** | Platforms and satellites | Platform abstraction, satellite runtime, Windows and macOS satellites on agent-desktop, per-OS benchmark, native-node spike | **MT-I05p** |
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
| **D** | Desktop: browser profile, accessibility, screenshots and input, virtual desktop container, voice |
| **X** | Control: shell tool, application registry and ladder selector, application adapters, input maps, pointer layer, guide mode, specialist tools, games |
| **V** | Virtual desktop sessions, live view, shared mode, the tray control panel |
| **S** | Screen memory and vision: capture, extraction, store, search, grounding |
| **P** | Platforms: platform abstraction, satellite runtime, Windows and macOS satellites, native-node spike (revision 1.2) |
| **U** | Usability and reach (revision 1.3): recipes, starter templates and the guided first run, degraded mode, security evidence, and the limited native node |
| **E** | Server-side economics and abuse controls, and (revision 1.2) the mesh relay |
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
          M04+M05+Q02+T11+R05 ──► M12      N08+V01+D03 ──► N09
          R02+S03+V04 ──► R06          all of 5C ──► I05c

PHASE 5R  K03+R05 ──► K06     A01+A07 ──► A08      K06+T02+T07 ──► T12      K06+E01+S03b ──► E04
          T12+T10 ──► T13      T12+T03 ──► T14      T12+N02+E04 ──► N10      K06+E04+T12 ──► N11
          E04+N11+K04 ──► W10  T13+T14+E04+N10+K04 ──► W11      T13+G02+T12 ──► G05
          N10+T12+M01+M04 ──► M13      N10+E04+A08 ──► N12
          V02+N10+T13+T12 ──► V06      E04+M13+Q04 ──► Q10
          T12+T13+T14+W11+G05+N12+M13+V06 ──► Q09      all of 5R ──► I05r

PHASE 5P  K01+N07 ──► P01 ──► P06 (also N08)      T12+N10+P01+T10 ──► P02
          P02+D02+R05+T10 ──► P03      P02+D02+R05 ──► P04      P03+P04+Q06 ──► P05      all of 5P ──► I05p

INDEPENDENT   D06 (voice), H09–H11, H13

PHASE 6   M08 (marketplace, builds on M12),
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
| `menux/src/menux/node/service.py` | N01 → N02 → N04 → N03 → N07 → U03 (each extends the node's event loop; `U03` adds the degraded-mode state machine last) |
| `backend/migrations/` | Numbers are **reserved** (§4.5) |
| `minicore/src/minicore/tiers/registry.py` | T01 owns it; T10 adds context-based tiering and the always-confirm list; later WPs only register capabilities |
| `menux/src/menux/control/**` (application profiles, selector) | X02 owns the registry and selector; X03–X05, X08 and X09 add profiles and tools |
| `menux/src/menux/desktop/**` (capture, input, sessions) | D02 → D03 → D04 → V01; S01 and S05 add modules; V02–V04 are separate modules |
| `protocol/v1/*` | K03 (1.1) and K05 (1.2) are additive new files |
| `backend/mate/` | E03 adds `vision`; M12 adds `skills`; neither edits existing routes |
| `protocol/mesh/v1/*` | K06 only; later additions are new files. The M2C `protocol/v1` envelope is never touched by mesh work |
| `backend/mate/mesh/**` | E04 owns the relay, registry, presence, leases and mailbox; N12 and M13 add handlers through registries |
| `menux/src/menux/mesh/**` | K06 (keys, trust edges) → T12 (signed commands) → N10 (client) → N11 (pairing), M13 (sync), N12 (placement) |
| `menux/src/menux/satellite/**` | P02 owns the runtime; P03 and P04 add platform backends |
| `minicore/src/minicore/platform/**` | P01 owns it; later WPs add implementations (`U05` adds the native Windows and macOS node backends). Must pass both products' tests |
| MiniMe Devices page (frontend, from M2C `X01`) | W10 extends it; it does not add a second page |
| `minicore/src/minicore/automation/**` (spec, schema) | A01 owns the spec and schema. `U01` adds the `recipe` kind and its `steps` in **new files** referenced from the schema; no existing field changes |
| `menux/src/menux/cli/**` (`init`, `doctor`) | N07 owns `doctor`; `U02` adds `init` after it; `U06` adds `evidence` |
| `menux/tests/` harnesses | Q01 → Q11 (Q11 adds `menux/tests/scenarios/`; it edits nothing that exists) |

### 4.5 Reserved numbers

| Item | Number |
| --- | --- |
| Migration: webhook relay registry | **0017** (H08) |
| Migration: push-notification subscriptions (optional) | **0018** (W-late) |
| Migration: marketplace catalog | **0019** (M08) |
| Migration: skill templates (curated library) | **0020** (M12) |
| Migration: vision usage, only if `usage_ledger` cannot carry it | **0021** (E03) |
| Migration: mesh registry (device roles, trust edges as device IDs, states, remote ceilings) | **0022** (E04) |
| Migration: encrypted mailbox (ciphertext, size, recipient, expiry) | **0023** (E04) |
| Protocol | additive revision **1.1** (K03), additive revision **1.2** (K05); the mesh uses its **own namespace `protocol/mesh/v1`** (K06), not the M2C envelope |
| Server routes | `/v1/mate/*` (planner, relay, webhooks), `/v1/mate/vision/*` (E03), `/v1/mate/skills/*` (M12), `WS /v1/mate/mesh` and `/v1/mate/devices/*` (E04) |

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
| **25** | X08, M09, N09 | per WP (§10 lists each dependency) |
| **26** | X09, X10, M10, M11, M12, R06 | per WP (§10 lists each dependency) |
| **27** | I05c | per WP (§10 lists each dependency) |
| **28** | K06, A08, P01 | K03+R05; A01+A07; K01+N07 |
| **29** | T12, E04, P06 | K06+T02+T07; K06+E01+S03b; P01+N08 |
| **30** | T13, T14, N10, N11 | T12+T10; T12+T03; T12+N02+E04; K06+E04+T12 |
| **31** | W10, W11, G05, M13, N12, P02 | per WP (§10.6 and §10.7 list each dependency) |
| **32** | V06, Q10, P03, P04 | per WP |
| **33** | Q09, P05 | per WP |
| **34** | I05r, I05p | per WP |
| **35+** | M08, T09, H12, R01, R03, R04, audit (Phase 6) | I05c and I05r; M12 for M08 |

**Phase 4U earliest waves (revision 1.3).** These do not renumber the waves above. A 4U work package may start in the wave its dependencies allow: `U01` 9, `U03` 10, `Q11` 11, `U02` 16, `U06` 16. `U05` (Phase 5P) can start in wave 30, after the `P06` decision in wave 29.

Phase 5 waves overlap on purpose: a 5B work package may start as soon as its own dependencies exist. Waves 28–34 (5R and 5P) can start as soon as their dependencies exist, including alongside 5A–5C. The acceptance milestones `I05a`, `I05b`, `I05c`, `I05r` and `I05p` gate the **release** of each sub-phase, not the work. `D06` (voice) and `H09–H11`, `H13` are independent and unscheduled.

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

### 9.1 Phase 4U — Usability and reach (revision 1.3)

Added in revision 1.3 after comparing Menux with a shipped open-source agent (`menux_feature_guide.md` §40). It is **recommended before `MT-I04`** and **not counted** in the 59 work packages and 133 points of Phases 0–4. The user-facing rules are `UX1–UX6` and the decisions are D39–D43 and D46. File names are the Python reference names (see the language note in the revision 1.3 header). Sizes use the same scale (S=1, M=2, L=4, XL=8): 5 work packages, 8 points.

### MT-U01 · No-model automations (recipes) · M · Earliest wave 9

*Depends on:* A01, N04, T05, A05. *Decision:* D40.

*Why:* some useful automations need no reasoning: move a download, copy a backup, append to a log, notify when a file changes or a page differs. Running them through a model costs credits, needs the server, and adds a prompt-injection surface for no benefit.

*What:* a second automation kind, `kind: recipe`, whose body is an ordered list of `steps` from a **closed action catalogue** (`minicore/src/minicore/automation/recipe.py`): `move_file`, `copy_file`, `append_text`, `read_file` (inside a folder grant), `http_get` (egress allowlist only), `diff_against_last`, `when` (simple comparisons on earlier step outputs: equals, contains, changed, size above), and the sealed tools `notify_owner` and `save_report` (`T05`). **Not in the catalogue:** a shell, a permanent delete (a delete moves the file to a recoverable folder), a write to a new recipient, and any model call. Every step has a tier in the capability registry (`T01`); the recipe's effective tier is the highest of its steps; the unattended ceiling is T2 (O6). Data read from an untrusted source (a web page, a downloaded file) is tainted (`T06`) and may reach only the sealed tools. The schema rejects an unknown action (fail closed). The dry run (`A03`) lists exactly what would happen; versions and graduation (`A06`) apply unchanged, and the anomaly detector (`T08`) still watches run counts and runtimes. A recipe makes **no planner call at run time**. The Planner may still *draft* a recipe when asked; the draft is validated like any spec.

*Done when:* a folder-watch → move → notify recipe runs with the network disabled and writes zero `usage_ledger` rows; the schema rejects a step outside the catalogue and any attempt to raise a tier in YAML; the dry run lists each action; a tainted read cannot reach `http_get` or a `move_file` outside its grant.

*Tests:* spec validation vectors; the `T06` taint tests applied to recipes; the `Q04` canary shows no recipe content on the server.

### MT-U03 · Degraded mode · S · Earliest wave 10

*Depends on:* U01, N04, K02, A05. *Decision:* D41.

*What:* one state machine in the node: `online`, `degraded(reason)` or `paused`, where the reason is one of: server unreachable, sign-in expired, pool exhausted, account paused, plan changed. While `degraded`: recipes keep running on schedule; model runs follow the spec's missed-run policy (skip, run once when back, or ask); local heartbeat pre-checks still run (`A05`). The owner gets **one** message per state change through the primary channel, not one per run, and `menux status`, `doctor` and the inbox show the reason and what is affected. Nothing at T2 or above is replayed when the state returns (the D34 rule). There is no infinite retry (§16 of the feature guide).

*Done when:* with the network cut, a recipe runs on schedule, a model run is skipped or queued as its spec says, exactly one notification is sent, and nothing above T2 is replayed on reconnect; a fake-clock test covers a three-day outage.

### MT-Q11 · Scripted-model scenario harness · M · Earliest wave 11

*Depends on:* Q01, T02, T04, T06. *Decision:* D39.

*What:* a deterministic fake model adapter that replays a scripted sequence of model outputs and tool calls, including hostile ones, so every policy, taint, reader/actor, approval and budget scenario can be replayed in CI with **no model call and no credits**. The scenarios cover the `Q02` corpus categories at the decision level (for example: "an unattended run with tainted context requests an egress tool: the decision is deny"). Includes the **model-independence test for D39**: each scenario runs under several model labels and size classes (Standard, Advanced, Expert, unknown) and requires **identical** policy decisions. Adds `menux/tests/scenarios/`; `Q01` (live-model evals) and `Q02` (red-team fixtures) are unchanged and still run.

*Done when:* the scenario suite runs offline and fast enough to run on every patch; a test-only flag that deliberately weakens the policy is caught by at least one scenario; the identical-decision test is green.

### MT-U02 · Starter templates and the guided first run · M · Earliest wave 16

*Depends on:* U01, A03, A06, H03, N07. *Decision:* D42.

*What:* (1) **Six signed starter specs** shipped with the node (`menux/src/menux/templates/*.yaml`): *morning brief* (calendar and mail read, digest to Telegram), *download sorter* (recipe), *folder watcher* (recipe), *site-change or feed digest* (`H07`), *calendar reminder* (`H05`) and *weekly summary of a knowledge folder* (`M06`, needs Phase 3). Each states its tier, capabilities, egress and cost estimate (`E02`, or zero for a recipe). A template installs **disabled**, runs a dry run, then runs attended; graduation (`A06`) is unchanged. A template is an ordinary spec: it gets no privilege a user-written spec cannot get. (2) **`menux init`:** one guided command that checks the platform (`N07` probes), explains and helps set up the WSL2 keep-alive if needed, signs in with the device code, walks through creating the owner's Telegram bot and pairing (`H03`), installs one template, shows its dry run, runs it attended and prints what to do next. Each step says what is stored where (the O8 copy). It never edits Windows settings itself.

*Done when:* on a fresh WSL2 Ubuntu and on a fresh Linux machine, a tester who follows only the printed steps reaches a successful attended run; the number of owner actions and the time taken are **measured and recorded** in the `R02` docs (not promised in advance); every template passes validation and its dry run cannot write.

### MT-U06 · Security evidence pack · S · Earliest wave 16

*Depends on:* Q02, Q03, Q04, R02. *Decision:* D44.

*What:* `menux evidence` (and a docs page) emits, for the release build: the version and signing information; the dependency and licence list (`docs/menux/third_party.md` and the lockfile); the red-team, canary and scenario suite results as **counts and suite names, never payloads**; the `doctor` sandbox probe results; and the open-findings list from the latest external review.

*Done when:* a release cannot be tagged without the evidence file, and every number in it matches the CI run that produced the build (`menux evidence --check`).

---

## 10. Phase 5 — The Companion Expansion

Phase 5 starts only after the beta milestone **MT-I04**. It grows Menux from Reach 0 (observe and notify) to Reach 4 (specialist tools and learning) and is split into five releases (5A, 5B and 5C, then the mesh work 5R and 5P added in revision 1.2), each with its own acceptance milestone, so the plan can stop after any of them. The user-facing description is `menux_feature_guide.md` §17–§37; the rules are CX1–CX7 and MX1–MX9 (§2) and decisions D15–D38 (§3).

5A–5C are **Linux-native**. On WSL2 only Linux GUI apps are reachable until the Windows satellite (5P) exists (CX2). 5R adds controllers and the mesh; 5P adds satellites for Windows and macOS. Third-party components named below are **candidates**: no WP imports one until `R05` has recorded a licence decision (CX7). Sizes map roughly to points as S=1, M=2, L=4, XL=8.

| Release | Reach | Work packages | Points | Waves | Milestone |
| --- | --- | --- | --- | --- | --- |
| 5A Native control | 1–2 | 13 | 34 | 17–21 | MT-I05a |
| 5B Eyes and hands | 3 | 21 | 67 | 19–24 | MT-I05b |
| 5C Companion | 4 | 10 | 32 | 25–27 | MT-I05c |
| 5R Remote control and mesh | – | 17 | 49 | 28–34 | MT-I05r |
| 5P Platforms and satellites | – | 8 | 26 | 28–34 (`U05` from 30) | MT-I05p |
| **Phase 5 total** | | **69** | **208** | | |

For scale: Phases 0–4 are 59 WPs and 133 points. Phase 5 is now about one and a half times that. Revision 1.2 changed the 5A–5C numbers (`D07` removed, `D02` re-sized from M to L) and added 5R and 5P; revision 1.1 counted 45 WPs and about 133 points. Revision 1.3 added `U05` to 5P (68 → 69 work packages, about 204 → about 208 points); the separate Phase 4U (§9.1, 5 work packages, 8 points) is counted in neither Phases 0–4 nor Phase 5.

### 10.1 Phase 5A — Native control (Reach 1–2)

Commands, files, application scripting, accessibility and the safety layer that everything later depends on. No screenshots and no pointer yet.

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **R05** | Reuse-or-build licence review | S | 17 | – | Feature guide §27 (CX7). Read the licence of every candidate in the §27 table, classify it, and record a decision (dependency, separate process, study only, or build our own) in `docs/menux/third_party.md`; add `NOTICE` entries, pin versions, and write the own-build fallback plan for each. **Blocks** D01, D02, D03, S01, S02, S05, X03, X04, X08 and M12, and from revision 1.2 K06, T14, P03 and P04, from importing any candidate. The §27 table of the feature guide now also lists agent-desktop and the mesh crypto and WebAuthn libraries. *Done when:* every candidate has a recorded decision and CI fails if a dependency is missing from the record. |
| **N08** | Hardware and display probe for `doctor` | M | 17 | N07 | Extends N07. Reports CPU features, RAM, GPU and VRAM, display server (Wayland or X11), compositor, screencast and RemoteDesktop portals, `/dev/uinput` access, AT-SPI state and container runtime, then recommends the perception path (CPU-only or GPU) and explains every warning with a fix. *Done when:* fixtures for GNOME, KDE, Hyprland, i3, X11, no-GPU and GPU machines. |
| **K05** | Protocol 1.2 (vision and session messages) | S | 17 | K03 | Additive revision: image and element-list message parts with a `consent` field and size limits, `perception_path` in run metadata, event types for screen actions, and `mode` (`background`, `shared`, `takeover`). New files only. *Done when:* golden fixtures; M2C and Menux tests stay green. |
| **T10** | Context-based tiering, grants and the always-confirm list | L | 17 | T02, T03, T07 | Feature guide §6.6 and §22. A capability's tier may depend on context (for example `input.contained` is T1 inside a disposable virtual desktop with no accounts and T3–T4 on a profile with logged-in accounts or real files); scoped, time-limited, revocable **grants** replace step-by-step approval for T3–T4 inside their scope; the **always-confirm list** is a hard floor that grants and the dial cannot lower; unknown context is treated as the higher tier. *Done when:* tests for every row of the floor, grant expiry and revocation, panic revoking grants, and "a user cannot lower a tier by editing YAML" still holding. |
| **X01** | Shell and file tool in the sandbox (Reach 1) | M | 18 | K01, T10 | Runs commands through the `minicore` sandbox (`bubblewrap`); classifies each command by effect (read-only T0–T1, writes inside granted folders T2–T3, system changes T4, destructive T5); allow and deny lists, output caps, timeouts, dry run, and no network unless the automation's egress list allows it. Reuses M2C's shell tool through `minicore`. *Done when:* red-team cases for command injection, path escapes and destructive commands pass. |
| **X02** | Application control registry and ladder selector (Reach 2) | L | 18 | T01, H02, T10 | Per-application control profiles (id, window match, rungs available, tools, shortcut map, per-operation tier, quirks, measured reliability) and the selector from feature guide §18.3: highest reliable rung first, precondition and postcondition checks, one retry, step down, outcome recorded, Guide mode at the end of the line. New package `menux/src/menux/control/`. *Done when:* selector tests with fake apps for every rung, including "all rungs fail" ending in a message to the owner, never a silent failure. |
| **D01** | Dedicated browser profile (Playwright, optional install) | M | 18 | R05, T04, T06 | Unchanged from the earlier plan: separate profile, never the user's daily one; sandboxed; domains through the proxy allowlist; page text is untrusted and tainting. **Reuse (MiniLocker, `m2c_build_plan.md` §11.6):** URL-scheme refusal, page text returned as data with scan and fence, and `attacks/browser_attacks.py` as tests; the Docker and proxy parts are not reused, and approve-before-submit is new work. Registered in X02 as the application-native rung for web pages. |
| **D02** | Accessibility backend (agent-desktop behind `ControlBackend`, own AT-SPI reader as the Linux fallback) | L | 18 | N08, R05 | Accessibility tree first: role plus name targeting; element references that expire; `doctor` reports whether accessibility is enabled and warns if a screen reader must be stopped. **Revision 1.2:** the primary backend is **agent-desktop** (Apache-2.0 as reported on 2026-11-14; confirm in R05) run as a pinned separate process, one session per run, its state directory relocated under `~/.menux/control/` (`0700`), text passed on standard input, trace screenshots off by default and traces redacted before the audit log. Every agent-desktop command is entered in the capability registry with a tier (feature guide §34.5); an unknown command is T5 and denied; a batch takes the highest tier among its entries; held-input commands are denied. Delivery states (`delivered_verified`, `delivered_unverified`, `not_delivered`) feed the selector's retry rule: **retry only when a retry is safe, and check the postcondition first when delivery is unverified** (`X02`). Skills store locators (application, role, name, native ID), never references. The same backend is reused by the Windows and macOS satellites (`P03`, `P04`). **Fallback:** our own AT-SPI reader on Linux (the `computer-use-linux` MCP server remains a candidate), behind the same `ControlBackend` interface. *Done when:* the Linux task suite passes on both backends and an unregistered command is refused. |
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

Specialist tools, learning, sharing and games. (Revision 1.2 removed the Windows-helper design spike `D07`; Windows is handled by `P03`.)

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **X08** | Specialist tool kit | L | 25 | X02, R05 | A template and test harness for building a purpose-made tool for an application that has no scripting interface or an unreliable one (tool manifest, tier per operation, fixtures, sandboxed tests, versioning). First targets are chosen by user demand; CAD is the leading candidate. *Done when:* one tool for a listed application passes its fixtures. |
| **M09** | Experience memory | M | 25 | M01, X02 | Records which rung and steps worked for which application and task, with outcome and cost; consulted by the selector; local, viewable and deletable; labelled untrusted until confirmed by repeated success. |
| **N09** | Menux session image (optional) | L | 25 | N08, V01, D03 | An installable session (package or script first, later a VM or bootable image) with the display session, portals, `uinput` permission, accessibility and virtual-desktop tooling preconfigured. A full distribution is out of scope until after GA (D22). |
| **X09** | Self-built tools and adapters | L | 26 | X08, M05, T10 | Menux drafts an adapter script or tool for an application, tests it in the sandbox, and proposes it as a reviewed skill install (T4). Never self-activating. |
| **X10** | Game loop runner and input maps | L | 26 | X05, X06 | Opt-in game profile; a fast local loop (frame sampling, small decisions) with the large model as strategist; engine tools (for example a chess engine) run as separate processes after R05; runs on the virtual desktop; shows the anti-cheat notice; no circumvention. |
| **M10** | Learn by demonstration | L | 26 | S03, M05, X06 | Record mode captures the user doing a task (accessibility events and screen memory); Menux drafts a parameterized skill, dry-runs it, and queues it for review (M05). |
| **M11** | GUI skill self-repair | M | 26 | M09, A06, X06 | When a postcondition fails after a UI change, try another rung, propose a patched skill version, review it, and keep versions with rollback (A06). |
| **M12** | Skill templates and the curated library | L | 26 | M04, M05, Q02, T11, R05 | Sanitizer (strip paths, names, emails, tokens, IDs, URLs), parameterization, permission manifest, static scan, canary-secret sandbox trial, publisher identity and signature. The server stores only the template (migration `0020`), never the user's runs or data. Installing a template on another device shows the manifest, tier, egress and applications and stays disabled until the owner enables it. First-party curated library plus opt-in "submit for review"; the open marketplace is M08 (Phase 6). |
| **R06** | Companion docs and trust pages | M | 26 | R02, S03, V04 | The screen-memory trust copy, the perception-path explanation, the dial and grants guide, the WSL2, satellite and Windows or macOS honesty page, and the licences page. |
| **I05c** | Companion (acceptance) | M | 27 | X08, M09, N09, X09, X10, M10, M11, M12, R06 | See §10.5. |

### 10.4 Independent Phase 5 items

Not part of 5A–5C; schedule them when wanted, after `MT-I04`.

| WP | Title | Notes |
| --- | --- | --- |
| **D06** | Voice | Push-to-talk and voice notes through channels first; transcripts are treated as normal owner messages only from the paired device or channel. *Revision 1.3:* voice notes through Telegram come first and are **opt-in**; the audio and transcript leave the device to a speech-to-text provider through the server (metered under `surface='menux'`); the audio is deleted after transcription; a voice note from anyone but the paired owner is a stranger message (`G02`). The speech provider is not covered by the Provider Consolidation Guide and is chosen when this item is scheduled. |
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
- [ ] The trust pages match the system's behavior (`R06`).

### 10.6 Phase 5R — Remote control and the device mesh

Added in revision 1.2. Controllers, signed commands, node-approved pairing, sync, placement and the web or chat approval paths. The user-facing description is `menux_feature_guide.md` §28–§33 and §36; the rules are MX1–MX9 (§2) and the decisions are D26–D34, D37 and D38 (§3). It starts only after `MT-I04`, can overlap 5A–5C once its dependencies exist, and is releasable on its own. It also needs the M2C follow-up `S03b` (device self-revoke, §1), which is an M2C patch and is not counted here.

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **K06** | Mesh protocol, device identity and trust edges | L | 28 | K03, R05 | New namespace `protocol/mesh/v1` (new files only; the M2C v1 envelope is not touched): hello with roles and capability names, signed command, acknowledgement, presence, lease, sync-record and mailbox frames, with limits and golden fixtures. Node-side device identity key (OS key store, vault fallback), trust-edge store, six-word fingerprint, mesh-key wrapping. Crypto choices go through `R05` behind a Menux interface. *Done when:* fixtures validate; key rotation and revocation tests pass; M2C and Menux tests stay green. |
| **A08** | Placement fields in the automation spec | S | 28 | A01, A07 | Additive revision of the `A01` schema: `runs_on`, `prefer`, `requires`, `failover` (default `false`). The Planner sees capability names only. *Done when:* old specs still validate and a spec cannot lower a tier through the new fields. |
| **T12** | Signed command channel and replay protection | L | 29 | K06, T02, T07 | Feature guide §31.5. Every remote command is signed by the controller's device key and carries ID, endpoints, command, argument digest, issue time, lifetime and counter. Checks in order: signature, not revoked, lifetime and skew, counter, known command (unknown fails closed), class and ceiling, then the normal policy. Idempotent by command ID; accepted, refused and done acknowledgements. Approvals travel as signed commands, which closes the Phase 2 gap in feature guide §31.8. *Done when:* replay, reorder, expired, wrong-endpoint and unknown-command cases are refused. |
| **E04** | Server: mesh relay, device registry, presence, leases and mailbox | XL | 29 | K06, E01, S03b | `WS /v1/mate/mesh` and `/v1/mate/devices/*`; migration `0022` (roles, trust edges as device IDs, states, remote ceilings) and `0023` (mailbox ciphertext with size, recipient and expiry); presence; leases in Redis with opaque IDs; per-device and per-account rate limits; revocation closes sockets. Stores no frame bodies and no content. *Done when:* the extended canary (`Q10`) passes and a relay that drops or reorders frames cannot cause a wrong action. |
| **T13** | Controller classes, ceilings and the remote trust ladder | M | 30 | T12, T10 | Feature guide §30–§31. Class and ceiling per device, the approval table by tier and class, travel mode, session limits, tighten-at-once propagation. A controller cannot raise its own class or ceiling. *Done when:* every cell of the table in §31.2 has a test. |
| **T14** | Passkey step-up | M | 30 | T12, T03 | WebAuthn assertion bound to approval ID, nonce, action digest and expiry; the node stores the public key and verifies it itself; assertions are single-use and expire in minutes. |
| **N10** | Mesh client in the node | M | 30 | T12, N02, E04 | Connects, reconnects with backoff, presence, applies commands through the normal policy, fans Panic out to every node in the mesh until acknowledged (survives restart), local link (loopback on, LAN off). |
| **N11** | Pairing commands and flows | M | 30 | K06, E04, T12 | `menux pair controller`, `menux pair satellite`, `menux remote pair`, `menux devices`, `menux logout` (self-revoke through `S03b`). Node-approved pairing with the six-word check and the ceiling chosen on the node; approval from a trusted-display controller with step-up; every other controller is notified. |
| **W10** | Devices page for the mesh | M | 31 | E04, N11, K04 | Extends the MiniMe Devices page built for M2C (`X01`); does not add a second one. Add-a-device choices, roles, capabilities, last seen, linked node, remote ceiling, pause, revoke, content-free activity, and the mesh trust copy. |
| **W11** | Phone and web controller (installable web app) | M | 31 | T13, T14, E04, N10, K04 | Status, inbox, approvals with passkey step-up, Panic, run now, pause and resume, proposals. Web class only: T3 at most; T4 requests are forwarded to a trusted display. Optional Web Push through migration `0018` with minimal text. Its code is served by the server, which is why the class is capped. |
| **G05** | Chat controller hardening | M | 31 | T13, G02, T12 | Owner-pinned chat identity, signed approvals for T3 with nonce, T4 refused with a pointer to a trusted display, status, pause and run-now only. Telegram first; Slack and Discord (`H10`) reuse it. |
| **M13** | Sync spaces | L | 31 | N10, T12, M01, M04 | Feature guide §32. Categories, mesh key, versioned content-addressed records, conflicts keep both, tombstones and "forget", encrypted mailbox client, initial snapshot, items arrive disabled. Never vault, connector tokens, screen memory or the knowledge index. |
| **N12** | Placement, leases and failover | M | 31 | N10, E04, A08 | Feature guide §33. `runs_on` and `requires` routing, the lease protocol, takeover only with `failover: true` after the missed-run policy, fire time as idempotency key, a node that cannot reach the server skips rather than duplicates. |
| **V06** | Remote live view (view only) | L | 32 | V02, N10, T13, T12 | End-to-end encrypted remote path for the `V02` viewer; web class view only, take-over from a trusted display with step-up; visible indicator on the desktop; nothing recorded or stored on the server; its own security review. |
| **Q10** | Mesh privacy and canary extension | M | 32 | E04, M13, Q04 | **Blocks release.** At rest the server holds only ciphertext for at most 24 hours, deleted on delivery; no frame bodies or run content in logs; notification text minimal; sync never carries secrets or screen memory. |
| **Q09** | Mesh red-team suite | L | 33 | T12, T13, T14, W11, G05, N12, M13, V06 | **Blocks release.** Server forges, replays or reorders commands; server adds a controller; hostile web controller code; stolen phone; compromised satellite returns poisoned data; relay man-in-the-middle; revoked device lingers; sync injection; flooding; account takeover. |
| **I05r** | Remote control and mesh (acceptance) | M | 34 | K06, A08, T12, E04, T13, T14, N10, N11, W10, W11, G05, M13, N12, V06, Q09, Q10 | See the exits below. |

**MT-I05r · Remote control and mesh (acceptance)**

- [ ] A phone controller pairs through the node, approves a T3 action with a passkey and is refused a T4 action, which goes to a trusted display and succeeds there.
- [ ] The server, modified to forge, replay, drop or reorder frames, cannot cause an action the node did not approve (`Q09`).
- [ ] A stolen-phone drill: revoke from the web account and from another controller; the node distrusts the key and rotates the mesh key even when the server is told to lie.
- [ ] Panic from the web, from chat and from a trusted display stops every node, survives a restart and is not undone by a reconnect.
- [ ] Two nodes: a lease prevents a double run; failover happens only when the spec allows it; a node without server contact skips instead of duplicating.
- [ ] Sync moves a spec, a skill and a note, which arrive disabled; the canary shows only ciphertext for at most 24 hours on the server and no vault, token or screen memory anywhere in sync (`Q10`).
- [ ] The Devices page and the mesh trust copy match the system's behavior.

### 10.7 Phase 5P — Platforms and satellites

Added in revision 1.2. Windows and macOS control through satellites, and the platform layer they need. It replaces the Windows-side helper (`D07`, `D08`). The user-facing description is `menux_feature_guide.md` §34–§35; the rules are MX1, MX2 and MX9 and the decisions are D35 and D36. The satellite runtime needs the mesh (`T12`, `N10`), so 5P starts after those exist.

| WP | Title | Size | Wave | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| **P01** | Platform abstraction in `minicore` | L | 28 | K01, N07 | Interfaces for paths, key store, service manager, process control and capability flags per operating system, with Linux as the reference implementation. Additive: `minicore` changes must pass both products' tests. *Done when:* Linux behavior is unchanged and a stub backend runs the interface tests. |
| **P06** | Native-node feasibility spike (research) | M | 29 | P01, N08 | Time-boxed. What would it take to run a node natively on Windows or macOS (sandbox, vault, service manager, scheduler)? Output is a findings note and a go or no-go; the product does not depend on it. **Revision 1.3: write these acceptance criteria into the note before starting.** *Go* only if (a) a vault design on the OS key store passes the vault tests adapted per OS; (b) a background-task design survives logout and restart without elevation; (c) the scheduler's missed-run and DST tests pass on the OS; (d) the subset of the red-team and canary suites that applies passes on a CI runner for each OS; and (e) the note lists every feature the limited node would lack. A *go* unlocks `U05` (decision D43). |
| **P02** | Satellite runtime | L | 31 | T12, N10, P01, T10 | A small daemon that pairs with a node, offers named capabilities, applies its **own** dial and grants (it can only narrow what the node may do), shows an always-visible tray indicator that goes red while controlled, and returns results labelled `origin: satellite:<name>`. |
| **P03** | Windows satellite | L | 32 | P02, D02, R05, T10 | agent-desktop (Windows UI Automation) behind `ControlBackend`; signed installer and updater; runs in the user's interactive session; no elevated windows or UAC; notification mirroring; pairing with a WSL2 node over loopback or the relay. Physical input stays off until the Shared-mode arbiter (`V03`) is ported. **Replaces `D07` and `D08`.** |
| **P04** | macOS satellite | L | 32 | P02, D02, R05 | agent-desktop (AX) behind `ControlBackend`; signed and notarized package; guided Accessibility and Screen Recording permissions that Menux never grants itself; notification mirroring. |
| **P05** | Control benchmark per operating system | M | 33 | P03, P04, Q06 | The fixed task set of `Q06` on Windows and macOS satellites, plus agent-desktop version-pin checks (release notes, command list against the capability registry); results published in `doctor`. **Blocks the 5P release.** |
| **U05** | Limited native node for Windows and macOS | L | 30 | P06 (go), P01, N02, N05, U01, U02, U03 | Only if `P06` ends *go* (D43). A node that runs natively with: the scheduler as a per-user background task (Task Scheduler, launchd), a vault on the OS key store (Credential Manager, Keychain), Telegram (`H03`), connectors that need no sandbox (IMAP read and draft, CalDAV and ICS, poll and RSS, files inside grants, the webhook relay), recipes (`U01`), sealed tools (`T05`), the `doctor` subset and degraded mode (`U03`). **Not offered, and `doctor` says so:** the shell tool, skill scripts, the browser sidecar, and anything above T2 that needs the Linux sandbox. The trust copy says plainly that without an OS sandbox the node cannot run code from skills. If the node is built in Rust (Appendix A, `MG-Z10` = PROCEED) it reuses the same crates; if it stays Python, `P06` must cost a Python build for each OS. *Done when:* a Windows-only user with no WSL2 completes `menux init`, a recipe and a Telegram digest; the applicable red-team and canary suites are green on Windows and macOS runners; the docs list exactly what is missing. |
| **I05p** | Platforms and satellites (acceptance) | M | 34 | P01, P02, P03, P04, P05, P06 | See the exits below. |

**MT-I05p · Platforms and satellites (acceptance)**

- [ ] A Windows satellite paired to a WSL2 node runs an automation that drives a Windows application through accessibility, under the node's tiers, with the satellite's own dial able to refuse it.
- [ ] A macOS satellite paired to a Linux node does the same.
- [ ] Every agent-desktop command is in the capability registry; an unregistered command is denied; a batch takes the highest tier among its entries.
- [ ] An action reported as delivered but unverified is not retried until its postcondition has been checked.
- [ ] Session traces are redacted before they reach the audit log and are deleted with the run.
- [ ] The control benchmark (`P05`) is published per operating system and rung.
- [ ] The documentation says plainly what a satellite cannot do (elevated windows, locked screens, applications with no accessibility tree) and that a Windows-only or Mac-only user still needs a node (`P06` records the outlook).
- [ ] If `U05` was built: a Windows-only user with no WSL2 completes the guided first run; the node refuses the shell tool, skill scripts and anything above T2 and says why; the docs list what is missing.

---

## 11. Phase 6 — Ecosystem and release

| WP | Title | Notes |
| --- | --- | --- |
| **—** | Windows-side helper (`D07`, `D08`) | **Replaced in revision 1.2** by the Windows satellite `P03` (Phase 5P). Kept here only so old references resolve. |
| **M08** | Marketplace with scanning and signing | Migration `0019`; permission manifests required; static scan, sandboxed trial with canary secrets, publisher verification, signing, yanking; **community content off by default**. Builds on the template pipeline and curated library from `M12` (Phase 5C). |
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
| Download sorter or folder watcher with no model (a recipe) | U01, H06, N03; keeps working with the server down (U03) |
| Any scheduled recipe while the server is unreachable | U01, U03 |
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
| Approve or deny an action from my phone | K06, T12, T13, T14, E04, N10, N11, W11 (T3 at most from the browser; T4 needs a trusted display) |
| Press Panic from my phone or chat | T12, N10, E04, W11 or G05 (works from every controller, no step-up) |
| Get Telegram approvals that cannot be forged by the server | T12, G05 |
| Add, limit, pause and revoke my devices from my MiniMe account | E04, N11, W10 (and S03b for `menux logout`) |
| Control a Windows app from my WSL2 or Linux node | P01, P02, P03, D02, X02, T10, T12, N10 |
| Control a Mac from my Linux node | P01, P02, P04, D02, X02, T10, T12, N10 |
| Same automations and skills on my laptop and my Raspberry Pi | M13, N12, A08 |
| Let the Pi run my morning brief when the laptop sleeps | N12, E04, A08 (spec `failover: true`) |
| Watch a Background session from my phone | V06 (view only; take-over from a trusted display) |

---

## 13. Tests and commands

| Area | Command | Notes |
| --- | --- | --- |
| Backend | `cd backend && pytest tests/unit tests/integration -v` | Includes `backend/mate` tests |
| Core | `cd minicore && pytest` | Must stay green for both products |
| M2C | `cd m2c && pytest` | Unchanged by Menux work |
| Menux | `cd menux && pytest` | Sandbox tests skip loudly if `bwrap` is missing |
| Protocol | `python protocol/validate.py` | Includes the 1.1 fixtures; the mesh v1 fixtures (K06) are added as a separate set |
| Frontend | `cd frontend && npm test && npx next lint && npx next build` |  |
| Evals | `python -m evals.menux.run --suite automations` | Costs real credits |
| Red team | `pytest menux/tests/redteam -v` | Blocks release |
| Canary | `pytest backend/tests/integration/test_no_content_at_rest.py` | Extended by MT-Q04 |
| Soak | `pytest menux/tests/soak -v` | Fake clock; slow |
| GUI red team | `pytest menux/tests/redteam_gui -v` | Q07; blocks Phase 5B release |
| Screen-memory privacy | `pytest menux/tests/screen_privacy -v` and the extended canary | Q08, Q04; blocks Phase 5B release |
| Control reliability | `python -m evals.menux.run --suite control` | Q06; costs real credits on the CPU path; results go to `doctor` |
| Licence record | `python scripts/check_third_party.py` | R05; fails if a dependency is missing from `docs/menux/third_party.md` (agent-desktop and the mesh crypto libraries are now in the table) |
| Mesh red team | `pytest menux/tests/redteam_mesh -v` | Q09 (command proposed); blocks Phase 5R release |
| Mesh privacy | `pytest menux/tests/mesh_privacy -v` and the extended canary | Q10 (command proposed); blocks Phase 5R release |
| Platform control benchmark | `python -m evals.menux.run --suite control` on a Windows and a macOS satellite | P05 (the OS option is proposed); blocks Phase 5P release |
| Scenario harness | `pytest menux/tests/scenarios -v` | Q11 (command proposed); no model calls; runs on every patch |
| Evidence pack | `menux evidence --check` | U06 (command proposed); blocks the release tag |

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
| The Companion and the mesh are larger than all of v1 | Say so in planning (Phase 5 is now about 208 points against 133 for Phases 0–4, roughly one and a half times); do not schedule it inside the March–June 2027 window; stop after any sub-phase if needed; 5R and 5P are separately releasable |
| Pointer and vision control is less reliable than users expect | The ladder prefers reliable rungs; verification around every action; Guide mode; published benchmark (Q06); weak rungs default to "ask first"; the docs say plainly what is slow or fragile |
| Screen memory becomes a privacy incident | Off by default; visible indicator; text first; raw images deleted; exclusions; encryption with a vault-derived key; nothing on the server; Q08; trust copy and legal review (R03) updated before 5B ships |
| Prompt injection through pixels or on-screen text | Reader for pixels and the task-scope guard (T11); Q07; scoped, time-limited grants; always-confirm floor |
| Tier-by-context is wrong somewhere and contained input is not really contained | Default to the higher tier when context is unclear; Q07 tests escapes from the virtual desktop; the session has no accounts and allowlisted egress |
| Wayland and compositor variability | `doctor` matrix; portals first, `uinput` fallback; X11 fallback; session image (N09); Q06 numbers per compositor |
| A licence surprise (copyleft, AGPL weights, source-available) | `R05` first; interfaces around every candidate; own-build fallback written in advance |
| Shared skills become a supply-chain attack | Templates only; sanitizer; manifests; scan; canary trial; signing; installed disabled; community content off by default |
| CPU-only users get a poor experience, or GPU users get a different product | One interface with two implementations; the same task suite must pass on both; CPU path text-first with consent for images |
| Users set "Full control" and get hurt | The always-confirm floor; time-limited grants; panic; every action logged and reviewable |
| The server, or a stolen MiniMe login, is used to command a node | Signed commands, node-approved pairing, passkey step-up, local-only floor (T5, vault export); Q09 tests a forging, replaying and reordering server |
| Earlier approval paths pass a bare nonce through the server (Phase 2 inbox and chat buttons) | Until `T12` exists treat T3 approvals from the inbox as trusting the server; keep T4 off chat; `T12` moves approvals to signed commands |
| Hostile or compromised web controller code (the server serves it) | The web class is capped at T3 and a passkey is bound to the exact action; T4 needs a trusted display (`menux remote`) |
| A lost or stolen phone | Revoke from the web, another controller or the node; the node rotates the mesh key; sessions expire; Panic; travel mode |
| Sync leaks secrets or lets a bad device inject content | Opt-in categories; vault, tokens, screen memory and knowledge index excluded; items arrive disabled; memory keeps its trust label; Q10 |
| Two nodes run the same automation, or none does | One-writer lease, fire time as idempotency key, skip when the server is unreachable, `failover` off by default; N12 tests |
| agent-desktop changes, disappears or does not fit its licence | `R05` first; a pinned separate process behind `ControlBackend`; command list checked against the capability registry on every bump; own AT-SPI fallback on Linux; fixes written application-agnostic and offered upstream |
| Windows and macOS accessibility is thinner than the Linux numbers suggest | Per-OS benchmark (`P05`); a rung below its threshold is "ask first"; vision only where accessibility is weak; the docs list what a satellite cannot reach |
| Windows-only and Mac-only users have no node | Say so plainly; `P06` studies a native node; WSL2 or a small Linux machine is the advice until then |
| The mesh doubles the surface to secure | Separate protocol namespace; Q09 and Q10 block release; the mesh can ship after 5A–5C or not at all |
| Solo-founder capacity | Waves are a ceiling; Phase 0 to I01 is the proof; Phase 2 is the minimum before anyone else runs it |
| Recipes become a second, weaker automation language | A closed action catalogue; the same tiers, taint, dry run and graduation; no shell; the schema rejects unknown actions (`U01`) |
| Starter templates hand new users privileges they have not earned | A template is an ordinary spec, installs disabled, runs a dry run and then attended (`U02`) |
| The limited native node is mistaken for the full node | `U05` only if `P06` passes; `doctor` and the docs list what is missing; the unattended ceiling is T2 (D43) |
| Security prompts get relaxed for strong models later | D39, and the identical-decision test in `Q11` |
| The evidence pack claims more than is true | Counts and suite names only, produced by the CI run that built the release (`U06`) |

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
| U01 | No-model automations (recipes) | 4U | 9+ | A01, N04, T05, A05 | M |
| U03 | Degraded mode | 4U | 10+ | U01, N04, K02, A05 | S |
| Q11 | Scripted-model scenario harness | 4U | 11+ | Q01, T02, T04, T06 | M |
| U02 | Starter templates and guided first run | 4U | 16+ | U01, A03, A06, H03, N07 | M |
| U06 | Security evidence pack | 4U | 16+ | Q02, Q03, Q04, R02 | S |
| R05 | Reuse-or-build licence review | 5A | 17 | – | S |
| N08 | Hardware and display probe for `doctor` | 5A | 17 | N07 | M |
| K05 | Protocol 1.2 (vision and session messages) | 5A | 17 | K03 | S |
| T10 | Context-based tiering, grants and the always-confirm list | 5A | 17 | T02, T03, T07 | L |
| X01 | Shell and file tool in the sandbox (Reach 1) | 5A | 18 | K01, T10 | M |
| X02 | Application control registry and ladder selector (Reach 2) | 5A | 18 | T01, H02, T10 | L |
| D01 | Dedicated browser profile (Playwright, optional install) | 5A | 18 | R05, T04, T06 | M |
| D02 | Accessibility backend (agent-desktop, own AT-SPI fallback) | 5A | 18 | N08, R05 | L |
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
| X09 | Self-built tools and adapters | 5C | 26 | X08, M05, T10 | L |
| X10 | Game loop runner and input maps | 5C | 26 | X05, X06 | L |
| M10 | Learn by demonstration | 5C | 26 | S03, M05, X06 | L |
| M11 | GUI skill self-repair | 5C | 26 | M09, A06, X06 | M |
| M12 | Skill templates and the curated library | 5C | 26 | M04, M05, Q02, T11, R05 | L |
| R06 | Companion docs and trust pages | 5C | 26 | R02, S03, V04 | M |
| I05c | Companion (acceptance) | 5C | 27 | X08, M09, N09, X09, X10, M10, M11, M12, R06 | M |
| D06, H09–H11, H13 | Independent Phase 5 items | 5 | unscheduled | per WP | M–L |
| K06 | Mesh protocol, device identity and trust edges | 5R | 28 | K03, R05 | L |
| A08 | Placement fields in the automation spec | 5R | 28 | A01, A07 | S |
| T12 | Signed command channel and replay protection | 5R | 29 | K06, T02, T07 | L |
| E04 | Server: mesh relay, device registry, presence, leases and mailbox | 5R | 29 | K06, E01, S03b | XL |
| T13 | Controller classes, ceilings and the remote trust ladder | 5R | 30 | T12, T10 | M |
| T14 | Passkey step-up | 5R | 30 | T12, T03 | M |
| N10 | Mesh client in the node | 5R | 30 | T12, N02, E04 | M |
| N11 | Pairing commands and flows | 5R | 30 | K06, E04, T12 | M |
| W10 | Devices page for the mesh | 5R | 31 | E04, N11, K04 | M |
| W11 | Phone and web controller (installable web app) | 5R | 31 | T13, T14, E04, N10, K04 | M |
| G05 | Chat controller hardening | 5R | 31 | T13, G02, T12 | M |
| M13 | Sync spaces | 5R | 31 | N10, T12, M01, M04 | L |
| N12 | Placement, leases and failover | 5R | 31 | N10, E04, A08 | M |
| V06 | Remote live view (view only) | 5R | 32 | V02, N10, T13, T12 | L |
| Q10 | Mesh privacy and canary extension | 5R | 32 | E04, M13, Q04 | M |
| Q09 | Mesh red-team suite | 5R | 33 | T12, T13, T14, W11, G05, N12, M13, V06 | L |
| I05r | Remote control and mesh (acceptance) | 5R | 34 | K06, A08, T12, E04, T13, T14, N10, N11, W10, W11, G05, M13, N12, V06, Q09, Q10 | M |
| P01 | Platform abstraction in `minicore` | 5P | 28 | K01, N07 | L |
| P06 | Native-node feasibility spike (research) | 5P | 29 | P01, N08 | M |
| U05 | Limited native node for Windows and macOS (only if P06 is *go*) | 5P | 30 | P06, P01, N02, N05, U01, U02, U03 | L |
| P02 | Satellite runtime | 5P | 31 | T12, N10, P01, T10 | L |
| P03 | Windows satellite (replaces D07 and D08) | 5P | 32 | P02, D02, R05, T10 | L |
| P04 | macOS satellite | 5P | 32 | P02, D02, R05 | L |
| P05 | Control benchmark per operating system | 5P | 33 | P03, P04, Q06 | M |
| I05p | Platforms and satellites (acceptance) | 5P | 34 | P01, P02, P03, P04, P05, P06, U05 (if built) | M |
| M08, T09, H12, R01, R03, R04, audit | Phase 6 items | 6 | 35+ | per WP | M–XL |

---

## 16. Your first week on Menux

1. **Confirm M2C has reached M2** and every §1 row is present. If not, finish those M2C WPs first.
2. **Lock decisions D1–D10 and D13** (D11 and D12 can wait).
3. **Wave 1 in parallel:** K00 (read-only), A01, T01.
4. **Wave 2 in parallel:** K01 (the careful one: run M2C's whole test suite before and after), K02, K03.
5. **Then Phase 1.** When "send me a good-morning message at 07:30" works end to end on your own machine, charged to your own pool, with nothing stored on your servers, the design is proven and Phase 2 (safety) is the next thing, not more features.
6. **The Companion Expansion (Phase 5) is not part of your first week, or your first months.** It starts only after the beta (`MT-I04`). When it does, begin with `R05` (licence record), `N08` (hardware probe), `K05` and `T10` (the safety layer), and release 5A before touching a screenshot. The device mesh (5R) and the Windows and macOS satellites (5P) are also after the beta; before 5R starts, ask for the M2C follow-up `S03b` (device self-revoke), lock D26–D38, and add agent-desktop and the crypto libraries to `R05`'s table.

*End of the Menux build guide.*