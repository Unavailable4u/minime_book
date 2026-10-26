# Menux Feature Guide

*Minime agentic automation*

**Purpose:** the user manual and feature register for Menux, MiniMe's local-first personal automation system.

**Status:** Menux is a staged product plan built on the M2C engine. This guide records the intended user experience and trust model while clearly separating planned, gated, and future capabilities.

- **Available or inherited:** behavior provided by MiniMe/M2C foundations or already defined as a shared contract.
- **Planned:** described in the current Menux build plan but not necessarily implemented.
- **Gated:** requires M2C maturity, security review, legal review, credentials, or a later milestone.
- **Companion (planned, gated on Phase 4):** the Companion Expansion in §17–§27: shell, application, accessibility and vision control, a virtual desktop, screen memory, and learned and shared skills. None of it is part of v1 or of the 59-work-package beta plan. It is designed here so that v1 does not close doors on it.

### Architectural Synchronization (Overrides O1–O8 from `Menux___Build_Execution_Guide.md`)

Where the earlier standalone design note (`doc-menux-product.html`) and this guide or `Menux___Build_Execution_Guide.md` differ, **these 8 synchronized rules govern**:

| Override ID | Architectural Rule | How It Connects Across the Book |
| :--- | :--- | :--- |
| **O1 · Local-First Node Authority** | Scheduler, Run Engine, Approval Manager, 6 channel adapters, 9 connectors, Playwright browser, and Argon2id vault run on the user's device (`~/.menux/`) | Server holds zero connector tokens, zero automation YAML, and zero permanent run logs (`minime_server_management_guide.md` §9) |
| **O2 · One Account, One Cap, One Shared Ledger** | Uses the user's MiniMe plan (`Free / Basic $9 / Moderate $29 / Ultimate $79`) and logs into `usage_ledger` with `surface='menux'` | Reuses `0012_usage_ledger_and_plans.sql` built in MiniMe `Tech-A/B` + M2C `S01` |
| **O3 · Ephemeral 24h Redis Buffer** | In-flight server session state lives in Redis for at most 24h (idle 2h, max 500 events / 256 KB) so multi-hour approvals can resume | Enforced by canary test `MT-Q04` (zero user content in Postgres) |
| **O4 · Built on `minicore/` After M2C M2** | Starts once M2C reaches Invite-Only Beta (`M2`), reusing `minicore/`, device-code auth, and `bubblewrap` | Planned window on Master Timeline: **Mar – Jun 2027** (59 WPs, 16 waves, 133 pts) |
| **O5 · Backend Route Namespace** | Server routes mount under `/api/menux/*` (`backend/menux/` / `backend/mate/`) with `profile="mate"` | Shares brain turn loop with `/api/codeagent/*` |
| **O6 · Reader / Actor Pipeline for Untrusted Data** | Any run ingesting untrusted emails, web pages, or stranger messages runs a tool-less Reader pass before the Actor pass | Blocks indirect prompt injection (`MT-T04`, `MT-Q02`) |
| **O7 · Coding Delegated to M2C CLI** | Menux never implements a second code editor; coding tasks invoke `m2c run --json` over local IPC (`MT-M07`) | Preserves M2C's git checkpoints and OS sandbox |
| **O8 · Official Google Scopes Gated on CASA** | Local CalDAV/IMAP/ICS work immediately; official Google OAuth scopes wait for verification & legal gate (`MT-G03`) | Matches `MiniMe_Financial_Strategy_Rulebook.md` compliance gates |

### Companion Extensions (CX1–CX7, added in revision 1.1)

These seven rules govern the Companion Expansion (§17–§27). They sit beside O1–O8 and never relax them: the local-first rules, the shared account and the T0–T5 tiers all still apply.

| Extension | Rule | Where |
| :--- | :--- | :--- |
| **CX1 · Reach Levels and the Control Ladder** | Menux's reach grows in five levels (Reach 0–4). For every task it uses the most reliable method that can do the job (commands, application scripting, accessibility, shortcuts, vision and pointer), and every method inherits the same tiers, approvals, panic button and audit log | §17, §18 |
| **CX2 · Linux First, WSL2 Second** | Native Linux gets the full feature set. WSL2 gets everything that works inside Linux. Controlling Windows applications needs a separate Windows-side helper that is designed in Phase 5C and built in Phase 6 | §25 |
| **CX3 · The User Always Wins** | Pointer and keyboard work runs on Menux's own virtual desktop by default. On the user's real screen Menux takes turns and yields the instant the user moves | §19 |
| **CX4 · Screen Memory Is Local, Off by Default and Visible** | Text-first capture on events, raw images deleted after extraction, sensitive applications excluded, encrypted on the device, never stored on the server | §20 |
| **CX5 · Two Perception Paths** | Everything that needs to "see" works on a CPU-only machine (with cloud help, by consent) and works faster and more privately on a machine with a GPU | §21 |
| **CX6 · Skills Are Shared as Sanitized, Signed Templates** | The user's real automations and data stay on the device. Only a stripped, parameterized, scanned and signed template can be shared | §23 |
| **CX7 · Reuse or Build, After a Licence Check** | A third-party component is used only after its licence has been reviewed and the decision recorded. If it does not fit, Menux builds its own | §27 |

---

## 1. What Menux Is

Menux is a personal automation node that runs on the user's device. It watches schedules, events, files, messages, and other approved triggers, then asks the MiniMe reasoning engine to decide what to do and executes approved local tools.

Menux is intended for work such as:

- sending a morning summary;
- watching a folder and processing new files;
- checking a calendar or mailbox;
- notifying the owner when a condition changes;
- drafting an email or message;
- running a repeatable project workflow;
- delegating coding work to M2C;
- maintaining local memory and skills;
- responding to a paired channel such as Telegram;
- asking for approval before an external or irreversible action.

The local node is the scheduler, connector host, credential vault, memory store, approval store, and tool executor. The MiniMe server supplies the model-driven Brain, planning, orchestration, metering, and account-level limits. The server is not intended to become the permanent home of automation specifications, connector tokens, or run history in v1.

**Direction.** Menux is designed to grow beyond notifications and small file changes into an agentic companion that can use the computer the way a person does, or better: running commands, driving applications, reading what is on the screen, remembering what the user was doing, and learning repeated work as skills. That growth is staged as five Reach levels (§17) and is built only after the beta (Phase 4). The v1 product described in §2–§16 is Reach 0 and is complete without it.

---

## 2. Trust and Data Placement

### 2.1 Device as source of truth

The following data is intended to stay on the device:

- automation specifications;
- schedules and trigger state;
- run events and history;
- approvals and denials;
- memory files and local search indexes;
- skills and skill manifests;
- connector credentials;
- Telegram or other channel tokens;
- settings;
- audit records;
- local checkpoints;
- tool outputs needed for local history.

State is intended to live under `~/.menux/`, including a SQLite database plus automation, memory, skill, log, and configuration files. The directory should be protected with restrictive permissions.

### 2.2 Server persistence

The server persistently stores only the minimum account and economics information required to run the service:

- account identity;
- paired device registry and credential hash;
- usage ledger entries;
- plan and quota;
- minimal error counters;
- webhook registry metadata and secret hashes.

The persistent server ledger should not contain prompts, code, file paths, connector content, or tool outputs.

### 2.3 Ephemeral server content

During an active run, the server may hold an encrypted in-flight conversation buffer so the model loop can operate and prompt-cache prefixes remain stable. The intended limits are an idle timeout of about two hours and a hard cap of 24 hours. The buffer is deleted when the run ends or expires.

Webhook payloads use a short-lived delivery queue. The intended default is delivery within ten minutes or dropping the payload, with a maximum payload size of 64 KB.

### 2.4 Third parties

Model providers receive the prompt content needed for a run. Telegram receives messages sent through the user's bot. Connectors receive the data required by their own APIs. Menux's honest privacy statement is therefore:

> Your automations, memory, skills, and connector credentials are stored on your device. When an automation runs, the content it needs is sent to our servers and model providers to produce the result; we do not keep it after the run ends. Messages from people you have not paired are treated as data, never as instructions. You can pause everything with one button.

---

## 3. Installation and Node Lifecycle

### 3.1 Prerequisite

Menux depends on M2C's shared foundations. The intended starting gate is M2C's invite-only beta milestone. M2C supplies:

- protocol and golden fixtures;
- shared account and usage ledger;
- device pairing and JWT/revocation;
- device socket and resumable runs;
- model adapters and tool use;
- server loop and tool broker;
- local SQLite store and checkpoints;
- policy engine and sandbox;
- secrets redaction;
- hooks, skills, instructions, and memory loaders;
- web relay and device page;
- evaluation and red-team suites.

Menux should not duplicate these controls.

### 3.2 Node commands

The intended command family includes:

- `menux init`;
- `menux login`;
- `menux status`;
- `menux run`;
- `menux stop`;
- `menux service install`;
- `menux service uninstall`;
- `menux doctor`;
- `menux automation list`;
- `menux automation validate`;
- `menux automation dry-run`;
- `menux automation enable|disable`;
- `menux vault add|list|remove`;
- channel pairing and connector commands.

Some commands remain design targets until the corresponding build packages land.

### 3.3 Foreground and service operation

On systems with systemd, Menux is intended to install a systemd user service. Where systemd is unavailable, such as many WSL2 setups, it runs in the foreground or through a guided keep-alive process.

The node provides:

- a single-instance lock;
- graceful shutdown;
- startup recovery;
- next-run status;
- current login state;
- connector health;
- paused or disabled automation state;
- local event logging.

### 3.4 WSL2 behavior

WSL2 is supported with an important limitation: automations run only while the WSL instance is alive. Menux is intended to provide guided keep-alive setup and a `doctor` warning when it is missing.

For always-on use, the plan recommends a small Linux machine or other continuously running host. Menux does not promise Windows desktop automation from WSL2. Desktop control reaches Linux GUI applications inside WSLg only, not ordinary Windows applications.

Native Linux receives the full intended feature set. Native Windows and macOS are deferred for the initial product.

The same split applies to the Companion Expansion (§25). WSL2 users get everything that runs inside Linux: commands, files, Linux applications in WSLg, a browser inside WSL, automations and skills. Controlling Windows applications such as Microsoft Office or SolidWorks is not available until a Windows-side helper exists (designed in Phase 5C as `D07`, built in Phase 6 as `D08`, and only if its review passes). The honest launch message for Windows users is: *Menux works on the Linux side of your PC and on your files today; controlling Windows apps comes later.*

---

## 4. Automation Specifications

### 4.1 Declarative automation files

An automation is a declarative YAML specification validated against a JSON Schema. The intended fields include:

- `id`;
- description;
- trigger;
- agent profile and instructions;
- model class;
- optional reader/actor pipeline;
- connector and channel capabilities;
- folder grants with read or read-write access;
- maximum trust tier;
- unattended policy;
- approval rules;
- egress domains;
- per-run budget;
- daily budget;
- monthly budget;
- quiet hours;
- missed-run behavior;
- failure notification policy.

A spec is not active merely because a file exists. It must parse, pass semantic validation, and be enabled by the owner.

### 4.2 Validation rules

Validation checks include:

- required fields and valid types;
- known trigger types;
- known capabilities;
- capability tier no higher than the automation's declared ceiling;
- unattended automations limited to approved tiers;
- untrusted-content tools requiring a reader/actor pipeline;
- a closed list of allowed egress modes;
- positive budgets;
- valid connector and channel references;
- valid folder permissions;
- consistent missed-run policy.

Unknown capabilities should be treated as high risk and denied rather than silently accepted.

### 4.3 Drafting with the Planner

A user can describe an automation in natural language. The server-side Planner receives:

- the request;
- the node's capability list;
- tier and read/write metadata;
- connector descriptions without secrets.

The Planner returns:

- a draft automation spec;
- a plain-language summary;
- the required trust tier;
- an estimated credit range;
- open questions;
- validation errors if the draft is invalid.

The server validates the draft before returning it and may retry once with structured validation feedback. The draft is not supposed to become active automatically.

### 4.4 Dry run

Dry run executes an automation with writes simulated. It can use real or fixture reads while connector writes and owner notifications return a recorded "would do this" result.

A dry-run report shows:

- triggers and selected steps;
- data that would be read;
- writes or messages that would be attempted;
- approvals that would be requested;
- capabilities and trust tiers;
- estimated usage;
- blocked or missing permissions.

A dry run must not call a real write-capable connector.

### 4.5 Automation lifecycle

Automations move through states such as:

- draft;
- validated;
- disabled;
- enabled;
- queued;
- running;
- completed;
- failed;
- skipped;
- paused;
- awaiting approval.

An owner can inspect, enable, disable, pause, resume, and remove automations. The local store retains a per-automation timeline.

---

## 5. Triggers and Scheduling

### 5.1 Trigger types

The planned trigger vocabulary includes:

- manual;
- cron schedule;
- interval;
- heartbeat;
- file change;
- webhook;
- poll;
- message;
- delegated task;
- channel callback.

Each trigger should carry enough identity to deduplicate repeated delivery.

### 5.2 Cron and interval scheduling

The local scheduler is intended to support:

- time zones;
- daylight-saving transitions;
- cron expressions;
- fixed intervals;
- manual execution;
- jitter so many users do not call the model at exactly the same second;
- duplicate-trigger suppression;
- restart recovery;
- missed-run policy.

A scheduler restart should not cause accidental duplicate runs.

### 5.3 Missed runs

A specification can decide what happens when the node was offline:

- run immediately;
- skip the missed run;
- run only if it is newer than a configured number of minutes;
- notify the owner that it was missed.

The policy is evaluated at startup and after sleep or reconnect.

### 5.4 Heartbeat gating

Heartbeats are not intended to call a model on every poll. A local pre-check should determine whether something changed first. Only then should the automation spend credits on a model call.

This protects the shared account pool and prevents idle automations from becoming a hidden source of cost.

### 5.5 Webhooks

Inbound webhooks use a server relay because a device behind NAT may not have a public URL. The relay should:

- verify the webhook registry and signature;
- hold the payload only briefly;
- forward it to the paired device;
- acknowledge delivery;
- delete it after delivery or expiry;
- enforce the payload-size limit;
- avoid storing the content in Postgres or ordinary logs.

The device remains responsible for interpreting and executing the trigger.

---

## 6. Trust Tiers and Unattended Work

### 6.1 T0 to T5 model

Menux's intended automation tiers are:

- **T0 Observe:** read-only observation and status checks.
- **T1 Derive:** summaries, drafts, classifications, and derived workspace content.
- **T2 Notify:** send a notification to the owner or request approval.
- **T3 Act externally:** reversible external actions.
- **T4 Change system or data:** broader writes, shell activity, or changes outside the project.
- **T5 Irreversible:** destructive, financial, legal, or otherwise irreversible actions.

The exact capability registry determines which tools belong to which tier.

| Trust Tier | Risk Class | Representative Capabilities | Default Execution & Approval Rule |
| :--- | :--- | :--- | :--- |
| **T0 · Read-Only Local** | Minimal | Read local notes, list schedules, query local memory (`MT-M01`) | Runs automatically; allowed in unattended runs |
| **T1 · Read External / Local Draft** | Low | Read calendar/RSS/weather, write local draft or staging file (`MT-H03`) | Runs automatically; untrusted inputs pass through Reader (`MT-T04`) |
| **T2 · Notify Owner / Safe Write** | Moderate (Unattended Ceiling) | Send notification to paired owner channel (Telegram/Slack/Email to self), update local memory | **Maximum tier allowed unattended (`unattended_ceiling = T2`)** |
| **T3 · External Write / Third-Party Send** | High | Send email/message to third party, create shared calendar event, POST to external webhook, delegate edit to M2C | **Requires explicit cryptographic owner approval (`nonce` + 15m TTL)** |
| **T4 · Browser Action / Shell / System** | Very High | Playwright authenticated form submit (`MT-W01`), sandboxed shell script, skill install | **Requires explicit step-by-step owner approval with parameter preview** |
| **T5 · Financial / Credential / Destructive** | Critical | Payment/checkout action, vault export, deleting non-staged files, modifying security policy | **Blocked unattended; requires interactive local CLI confirmation + re-auth** |

### 6.2 Effective tier

A tool's effective tier is the higher of:

- the M2C risk level declared by the tool;
- the tier declared by the Menux connector or automation.

An unknown capability is treated as T5 and denied. A user cannot lower a tool's real risk by writing a smaller number in YAML.

### 6.3 Unattended ceiling

Unattended automations have a stricter ceiling than interactive runs. The intended default is that unattended operation may observe, derive, and notify, while external action requires an explicit policy and later graduation.

Rules include:

- an automation cannot list a capability above its tier ceiling;
- a T2 automation can notify and ask the owner, but not silently perform a T3/T4/T5 action;
- untrusted content must be separated from trusted instructions;
- scheduled quota exhaustion skips the run and notifies once instead of retrying forever;
- per-automation and daily budgets are enforced locally;
- account pool, rate, and concurrency limits are enforced server-side.

### 6.4 Approvals

Approvals can be requested through the browser inbox, Telegram, desktop notification, or another configured channel. An approval record includes an opaque approval ID and nonce so a stale or forged callback cannot authorize a different action.

An approval should describe:

- the automation and run;
- the proposed action;
- the data or target involved;
- the trust tier;
- the reason the action was blocked;
- the available decision;
- the expiry or cancellation state.

### 6.5 Panic button

Menux is intended to provide a one-action pause for all automations. Panic behavior should:

- stop starting new runs;
- cancel or request cancellation for active runs;
- block connector actions;
- keep the local audit record;
- notify the owner when the system is paused;
- require an explicit resume action.

A panic state must survive a node restart until the owner clears it.

### 6.6 Context-based tiering and grants (Companion)

The tiers describe the **effect** of an action, not the mechanism that performs it. Two rules follow, both implemented by `MT-T10`:

- **Tier follows effect and context.** Typing into a window is not always the same risk. `input.contained`, pointer and keyboard input inside a disposable virtual desktop that holds no accounts, no real files and only allowlisted network access, is T1. The same input on a profile that is logged into the user's accounts, or on the real desktop, is T3 or T4 by what it can change. When the context cannot be established, the higher tier applies.
- **Grants replace step-by-step approval only inside their scope.** A grant is scoped (an application, a folder, a site or a session), time-limited, revocable, logged and visible in the tray. Inside its scope it stands in for the per-step approval that T3 and T4 normally need. It never covers the always-confirm list (§22.5) and it never raises the unattended ceiling by itself; raising a ceiling still goes through graduation (`MT-A06`).

The panic button (§6.5) revokes every grant.

---

## 7. The Automation Run

### 7.1 Run kinds

Runs carry `profile: "automation"` and a `run_kind` such as:

- interactive;
- scheduled;
- triggered;
- heartbeat;
- delegated.

The run kind affects default budgets, approval behavior, notifications, and retry policy.

### 7.2 Run orchestration

The node-side runner is intended to:

1. load and validate the automation;
2. check whether it is enabled, paused, or inside quiet hours;
3. check local per-run and per-automation budgets;
4. assemble trusted instructions and memory;
5. connect to the server brain;
6. send the profile, run kind, spec, and relevant context;
7. receive proposed tool calls;
8. route each call to the correct local executor;
9. apply policy and approval gates;
10. return labelled tool results;
11. write every event locally;
12. notify the owner when required;
13. complete, pause, skip, fail, or resume the run.

### 7.3 Reader and actor pipeline

When an automation reads untrusted content, the plan supports a reader/actor separation:

- the **reader** extracts or summarizes data;
- the **actor** receives only a constrained, typed result;
- untrusted instructions inside the source remain data;
- the actor cannot treat arbitrary source text as a system instruction;
- the final action still passes through tier and approval policy.

This is intended for email, web pages, documents, messages, and other content that may contain prompt injection.

### 7.4 Retry and failure behavior

The lifecycle should support:

- transient-error retry with backoff;
- maximum retry counts;
- one owner notification per failure episode rather than one per attempt;
- explicit skipped state for quota or policy;
- paused state for approval or panic;
- resume after a disconnect;
- clean cancellation of in-flight tools;
- restart recovery from local events.

A run must not continue silently after the user has stopped it.

### 7.5 Local event log

The device event log records enough information to understand what happened:

- trigger identity;
- run identity;
- automation identity;
- tool proposals;
- approval requests and decisions;
- tool results or redacted summaries;
- usage events;
- retries;
- failures;
- notifications;
- final state.

Secrets and inappropriate content are redacted. The local log is the history authority, not the ephemeral server buffer.

---

## 8. Connectors and Channels

### 8.1 Connector manifests

A connector declares:

- its name;
- authentication method;
- tools and JSON Schemas;
- per-tool trust tier;
- read/write class;
- allowed egress domains;
- rate limits;
- result-size limits;
- fixtures for tests;
- trust label;
- possible confirmation phrase.

The connector host validates arguments, applies the user's allow/ask/block stance, injects credentials only inside the connector process, enforces network restrictions, caps results, and labels returned data.

### 8.2 Connector stances

A user can configure a capability stance:

- **allow:** use within the declared tier and policy;
- **ask:** request confirmation each time or according to the configured rule;
- **block:** deny the capability.

A connector cannot access an undeclared domain or use a credential outside its declared operation.

| Connector / Channel | Kind | Stance (`Read` / `Draft` / `Act`) | Base Trust Tier | Key Security Boundary & Work Package |
| :--- | :--- | :--- | :--- | :--- |
| **Telegram Bot (`MT-H02`)** | Bidirectional Channel | Read owner commands / Notify / Inline Approve (`✅`/`❌`) | `T2` (owner) / Untrusted (strangers) | Pinned owner `chat_id`; HMAC-signed callback nonces; stranger messages quarantined as data |
| **Email IMAP / SMTP (`MT-H04`)** | Connector + Channel | Read inbox (`Reader` pass) / Draft reply / Send (`T3`) | `T1` (read/draft) · `T3` (send) | App-password/OAuth in local Argon2id vault (`MT-N04`); untrusted bodies stripped of instructions |
| **Calendar CalDAV / ICS (`MT-H05`)** | Connector | Read events / Propose slot / Create invite (`T3`) | `T1` (read) · `T3` (invite others) | Local timezone & conflict check before proposing calendar writes |
| **Local Watched Folders (`MT-H03`)** | Connector + Trigger | Read granted folder / Write to staging dir | `T1` (staging) · `T3` (outside staging) | Explicit per-automation `folder_grants`; blocks `~/.ssh`, `~/.menux/vault.enc`, `.env*` |
| **Playwright Browser (`MT-W01`)** | Headless Automation | Read allowed domains / Fill & click (`T4`) | `T1` (read-only) · `T4` (stateful act) | Ephemeral context per run; blocks `file://`, RFC1918 local IPs, and password/payment fields |
| **Inbound Webhooks (`MT-H08`, `MT-G04`)** | Trigger | Receive signed JSON payload (≤ 64 KB, 10m TTL) | `T1` (ingest via Reader) | HMAC-SHA256 verification; payload deleted from server relay immediately after node pull |
| **M2C IPC Bridge (`MT-M07`)** | Sibling Delegation | Invoke `m2c run --json` on local repo | `T2` (Ask/Plan) · `T3` (Edit/Patch) | Inherits M2C's `bubblewrap` sandbox, git checkpoints, and path guard |
| **Official Google Workspace (`MT-G03`)** | Gated OAuth Connector | Gmail / Drive / Calendar official OAuth scopes | **Gated (Phase 6)** | Requires Google CASA security audit, Limited Use compliance, and legal sign-off |

### 8.3 Telegram

Telegram is the first planned channel and uses the user's own bot token with long polling. The device talks outbound to Telegram, so a public inbound endpoint is not required.

Telegram features include:

- owner pairing with a one-time code;
- owner-only notifications;
- Markdown escaping;
- long-message splitting;
- inline approval buttons;
- callback nonce validation;
- rate limiting and API backoff;
- token storage in the local vault;
- ignoring callbacks from non-owners.

Messages from unpaired people are labelled as stranger content and do not reach the run starter by default.

### 8.4 Email

The first email plan uses IMAP with an app password. The intended initial scope is read and draft only. Sending mail or broader Google OAuth is not assumed to be available.

Email is a high-risk connector because messages may contain untrusted instructions and personal data. Reader/actor separation, redaction, and approval are required before an automation can cause an external effect.

### 8.5 Calendar

The initial calendar direction is CalDAV or ICS feeds. The automation can read events, derive summaries, and notify the owner. Creating or changing calendar events belongs to a higher trust tier and requires the connector's declared policy.

### 8.6 Files

File tools can:

- list approved directories;
- read approved files;
- search local content;
- write only within granted paths;
- report changes;
- respect protected paths;
- operate in dry-run mode;
- attach trust labels to file-derived content.

Folder grants distinguish read-only from read-write access.

### 8.7 Browser automation

Playwright and headless Chromium are planned as an optional installation. Browser automation is disabled by default because it has a large dependency and can affect external systems. Sites, domains, credentials, and actions must be governed by capability and tier policy.

The browser tool can reuse parts of MiniLocker's browsing design: refusing non-http(s) navigation, returning page text as data that is scanned and fenced before the model sees it, and a set of hostile-page attack scenarios used as tests. MiniLocker's browser runs in a Docker container behind an egress proxy; Menux uses a dedicated Playwright profile and the proxy allowlist instead (`D01`), so the container and proxy code is not reused. MiniLocker has no approve-before-submit step for web forms; the `T4` form submit (`MT-W01`) needs one, so that gate is new work. See `m2c_build_plan.md` §11.6.

Under the Control Ladder (§18) Playwright is the *application-native* rung for web pages: it reads and drives pages through the browser's own interfaces, which is more reliable and more private than screenshots. Pointer-and-screenshot control of a browser is the last resort and runs on the virtual desktop (§19).

### 8.8 Future connectors

The connector host is intended to support additional services through manifests. Official Google connectors are gated by legal and compliance review because Gmail restricted scopes, CASA assessments, verification, Limited Use requirements, and model-provider handling of mail content create material obligations.

A bring-your-own OAuth client may be available earlier for personal testing. It should not be described as the same thing as a generally available official Google integration.

---

## 9. Memory and Knowledge

### 9.1 Local memory

Menux can store reusable memory on the device:

- owner preferences;
- automation outcomes;
- recurring facts;
- summaries;
- connector-specific context;
- project notes;
- prior decisions;
- failure lessons;
- trusted instructions.

Memory should be visible, searchable, editable, and deletable.

### 9.2 Search

The initial design uses SQLite FTS5 rather than embeddings. This keeps the first version local and avoids sending all memory content to an embedding provider.

Search can be scoped by:

- automation;
- project;
- source or connector;
- date;
- trust label;
- memory type.

### 9.3 Memory poisoning defenses

External messages and connector data are not automatically trusted memory. The system should:

- label source and trust;
- separate facts from instructions;
- prevent arbitrary content from changing system policy;
- require review before promoting a generated skill or durable instruction;
- allow the owner to inspect the provenance of a memory item.

### 9.4 Skills

A skill is a reusable automation behavior with a manifest. A skill can define:

- instructions;
- required capabilities;
- input and output shapes;
- connector use;
- tier and egress requirements;
- tests and fixtures;
- version metadata.

Skill drafts are intended to be reviewed by the owner and security/review roles before activation. A marketplace is a later, gated feature and requires scanning and signing.

---

## 10. Notifications and Inbox

### 10.1 Owner notifications

Menux can notify the owner about:

- completed runs;
- failed runs;
- skipped quota runs;
- pending approvals;
- panic state;
- connector failures;
- missed schedules;
- unusual activity;
- requested clarification;
- generated drafts;
- automation changes.

Notification detail can be minimized so a channel shows only a safe summary instead of private message bodies.

### 10.2 Browser inbox

The web application is intended to show a live automation inbox containing:

- current run state;
- pending approvals;
- failures;
- paused automations;
- recent notifications;
- device connectivity;
- links to the relevant automation or run.

The inbox is a live relay in v1, not a permanent server-side archive of all automation content.

### 10.3 Channel approval callbacks

Interactive channel buttons carry an opaque approval ID and nonce. The node verifies:

- the callback came from the paired owner;
- the approval still exists;
- it belongs to the correct automation and run;
- it has not expired or already been decided;
- the requested decision is allowed.

---

## 11. Menux and M2C Cooperation

Menux can delegate coding tasks to the installed M2C CLI through local IPC. This allows an automation to say, for example:

- inspect a repository after a dependency alert;
- run the project's tests;
- prepare a patch for a known issue;
- summarize a code review;
- update a changelog draft;
- create a proposal for owner approval.

Menux should not implement a second coding sandbox. M2C remains responsible for code-specific policy, checkpoints, file proposals, and execution limits. The delegation boundary carries the automation profile and trust context into a headless coding run.

Delegated code changes remain proposals unless the automation's declared tier, policy, and approval path explicitly allow the action.

---

## 12. Economics and Budgets

### 12.1 One account and one pool

Menux shares one account and one credit pool with:

- the MiniMe web application;
- M2C;
- other future MiniMe surfaces.

Usage is visible per surface, but the cap is shared. This avoids a user paying for separate hidden pools and prevents a scheduled automation from bypassing interactive usage limits.

### 12.2 Local budgets

Each automation can have:

- per-run credits;
- per-day credits;
- per-month credits;
- tool-call limits;
- maximum run duration;
- maximum retries;
- connector-specific rate limits;
- notification limits.

The device enforces per-automation and daily budgets using server usage events. If the local budget is exhausted, the run is skipped or stopped according to policy.

### 12.3 Server limits

The server enforces:

- account pool availability;
- per-user rate limits;
- concurrency limits;
- provider limits;
- pre-flight budget checks;
- post-call usage commits.

When the shared pool is exhausted, scheduled runs are skipped and the owner is notified once. They are not retried in a loop.

### 12.4 Cost estimates

The Planner and dry-run surfaces can provide an estimated credit range. Estimates are not guarantees. Final usage is recorded after the model call and shown in the shared usage view.

---

## 13. Operations, Doctor, and Recovery

### 13.1 `menux doctor`

The diagnostic command is intended to check:

- supported operating system;
- Linux or WSL2 state;
- whether the WSL instance can stay alive;
- Python and package versions;
- local directory permissions;
- SQLite state;
- vault key source and security level;
- account login and device pairing;
- server connectivity;
- Telegram or connector credentials without printing them;
- scheduler health;
- systemd user service availability;
- sandbox and `bubblewrap`;
- Playwright installation if enabled;
- *(Companion, Phase 5A)* CPU features, RAM, GPU and VRAM, and the recommended perception path (§21);
- *(Companion)* display server, compositor, screencast and RemoteDesktop portals, `/dev/uinput` access, and accessibility state;
- *(Companion)* measured control reliability per application and per rung;
- stale migrations;
- clock and time-zone configuration.

The output should explain fixes rather than merely report a failed boolean.

### 13.2 Restart recovery

After a restart, Menux should:

- reacquire the single-instance lock;
- reload enabled automations;
- identify runs that were interrupted;
- apply missed-run policy;
- avoid duplicate trigger delivery;
- resume only when the run checkpoint and policy permit it;
- notify the owner about incomplete or skipped work.

### 13.3 Pause and resume

The owner can pause all automations or one automation. Pause should prevent new work and stop external actions. Resume should be explicit and auditable.

### 13.4 Logs and audits

Local logs should record the event sequence without exposing secrets. Audit views should answer:

- what triggered the run;
- what the Brain proposed;
- what tools were called;
- what approvals were requested;
- what was allowed or denied;
- what data left the device;
- what notification was sent;
- why the run completed, failed, skipped, or paused.

---

## 14. Product Phases

### Phase 0: foundations

Inventory finished M2C code, extract shared `minicore`, add the automation profile, extend the protocol, define the automation schema, and define the trust-tier registry.

### Phase 1: first automation

The walking skeleton is:

1. install the node;
2. sign in and pair the device;
3. configure a Telegram bot;
4. describe or create a scheduled automation;
5. run the server Brain;
6. send a safe T2 notification to the owner;
7. meter the run under the shared Menux surface.

No broad unattended external action is required for this milestone.

### Phase 2: safe unattended operation

Add tiers, approvals, the reader/actor split, taint tracking, panic, the browser inbox, email/calendar/file readers, and stronger automation budgets.

### Phase 3: memory, skills, and triggers

Add memory search, memory poisoning defenses, skill manifests, reviewed skill drafts, file/webhook/poll triggers, and heartbeat gating.

### Phase 4: invite-only beta

Add planner chat, M2C delegation, WSL keep-alive guidance, cost estimates, browser automation surfaces, and complete operational documentation.

### Phase 5: the Companion Expansion (5A, 5B, 5C)

Phase 5 grows Menux from Reach 0 to Reach 4 (§17). It starts only after the beta milestone `MT-I04`, and each sub-phase ends with its own acceptance milestone and can be released on its own.

- **Phase 5A, native control (Reach 1–2):** reuse-or-build licence review, hardware probe in `doctor`, protocol 1.2, context-based tiering and grants, shell and file tool in the sandbox, the application-control registry and ladder selector, LibreOffice and scriptable-application adapters, AT-SPI reader, shortcut and input maps, dedicated browser profile, control reliability benchmark. Milestone `MT-I05a`.
- **Phase 5B, eyes and hands (Reach 3):** screenshots and input, headless virtual desktop with session manager, live view and take-over, shared mode with input arbitration, the tray control panel, screen memory (capture, extraction, store, search), dual-path vision grounding with server metering, the pointer-and-keyboard action layer with verification, guide mode, the Menux Map, and the GUI red-team and privacy suites. Milestone `MT-I05b`.
- **Phase 5C, companion (Reach 4):** specialist tool kit and self-built tools, experience memory, learning by demonstration, GUI skill self-repair, skill templates and a curated shared library, game loop runner, optional session image, Windows-helper design spike, companion docs. Milestone `MT-I05c`.

Voice (`D06`) and the other connectors (`H09–H11`, `H13`) are independent of 5A–5C and are scheduled separately.

### Phase 6: ecosystem and release

Potential additions include a scanned and signed community skill marketplace (building on the curated library from Phase 5C), the Windows-side helper for WSL2 users, team features, official Google connectors if legally approved, external security audit, packaging, support, and general availability.

| Phase & Milestone | Waves | Work Packages | Effort Points | Key Deliverable & Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0 · Foundations & Contracts** | Waves 1–2 | `MT-K00–K03`, `MT-A01`, `MT-T01` (6 WPs) | 12 pts | Prerequisite check on `minicore/` (`MT-K00`), automation YAML JSON Schema (`MT-A01`), `T0–T5` tier matrix (`MT-T01`) |
| **Phase 1 · First Automation (`MT-I01`)** | Waves 3–5 | `MT-N01–N02`, `MT-N04–N06`, `MT-G01`, `MT-A02–A04`, `MT-H01`, `MT-H03`, `MT-I01` (12 WPs) | 28 pts | Local daemon (`~/.menux/`), Argon2id vault (`MT-N04`), APScheduler cron (`MT-H01`), dry-run engine (`MT-A03`), first live morning briefing (`MT-I01`) |
| **Phase 2 · Safe Unattended Operation (`MT-I02`)** | Waves 6–9 | `MT-H02`, `MT-H04–H06`, `MT-T02–T08`, `MT-A05–A06`, `MT-K04`, `MT-G02`, `MT-G04`, `MT-W01`, `MT-Q01–Q02`, `MT-Q04`, `MT-I02` (21 WPs) | 49 pts | Telegram inline approvals (`MT-H02`), Reader/Actor pipeline (`MT-T04`), panic switch (`MT-T07`), Playwright (`MT-W01`), prompt-injection & canary tests (`MT-I02`) |
| **Phase 3 · Memory, Skills & Triggers (`MT-I03`)** | Waves 10–12 | `MT-M01–M07`, `MT-N03`, `MT-H07–H08`, `MT-G03`, `MT-E01`, `MT-Q03`, `MT-I03` (14 WPs) | 30 pts | Provenance-tagged memory (`MT-M01`), poisoning defense (`MT-M02`), signed skill manifests (`MT-M04`), M2C delegation (`MT-M07`) |
| **Phase 4 · Invite-Only Beta (`MT-I04`)** | Waves 13–16 | `MT-A07`, `MT-N07`, `MT-E02`, `MT-Q05`, `MT-R02`, `MT-I04` (6 WPs) | 14 pts | Natural-language Planner draft (`MT-A07`), WSL2 keep-alive helper (`MT-N07`), cost estimator (`MT-E02`), 7-day unattended soak (`MT-I04`) |
| **Phase 5A · Native Control (`MT-I05a`)** | Waves 17–21 | `MT-R05`, `MT-N08`, `MT-K05`, `MT-T10`, `MT-X01`, `MT-X02`, `MT-D01`, `MT-D02`, `MT-X03`, `MT-X04`, `MT-X05`, `MT-Q06`, `MT-I05a` (13 WPs) | 32 pts | Licence record (`MT-R05`), hardware probe (`MT-N08`), context-based tiering and grants (`MT-T10`), ladder selector (`MT-X02`), LibreOffice and app adapters (`MT-X03–X04`), reliability benchmark (`MT-Q06`) |
| **Phase 5B · Eyes and Hands (`MT-I05b`)** | Waves 19–24 | `MT-D03`, `MT-D04`, `MT-S05`, `MT-V01`, `MT-S01`, `MT-E03`, `MT-S02`, `MT-V02`, `MT-V03`, `MT-X06`, `MT-T11`, `MT-V04`, `MT-V05`, `MT-S03`, `MT-X07`, `MT-Q07`, `MT-S04`, `MT-W08`, `MT-W09`, `MT-Q08`, `MT-I05b` (21 WPs) | 67 pts | Virtual desktop with live view (`MT-V01–V02`), shared mode (`MT-V03`), tray dial (`MT-V04`), screen memory (`MT-S01–S04`), dual-path grounding (`MT-S05`), GUI red-team (`MT-Q07`), privacy suite (`MT-Q08`), Menux Map (`MT-W08`) |
| **Phase 5C · Companion (`MT-I05c`)** | Waves 25–27 | `MT-X08`, `MT-M09`, `MT-N09`, `MT-D07`, `MT-X09`, `MT-X10`, `MT-M10`, `MT-M11`, `MT-M12`, `MT-R06`, `MT-I05c` (11 WPs) | 34 pts | Specialist tool kit (`MT-X08`), learning by demonstration (`MT-M10`), self-repair (`MT-M11`), skill templates and curated library (`MT-M12`), game loop (`MT-X10`), Windows-helper design (`MT-D07`) |
| **Phase 6 · Ecosystem & GA** | Post-5C | Community marketplace (`MT-M08`), Windows-side helper build (`MT-D08`), team policy, Google connectors if approved, packaging | Gated on `MT-I05c` | CASA verification for Google scopes, external security audit |

Phases 0–4 total 59 work packages and 133 points and are unchanged by the Companion Expansion. Phase 5 is counted separately: 45 work packages and about 133 points on the same scale (S=1, M=2, L=4, XL=8, approximate), roughly the size of the whole v1 plan. It is therefore scheduled after the beta and is not part of the March–June 2027 window.

---

## 15. Future and Gated Features

### 15.1 Desktop control

Desktop control is no longer only a future idea: it is the Companion Expansion (§17–§27), planned for Phase 5 and gated on the beta. It is still not the first trust boundary. Every form of it requires:

- Linux desktop APIs or controlled input tooling;
- a headless desktop container where appropriate;
- explicit screen and input permissions;
- stronger T4/T5 approvals;
- protection against acting on the wrong window or account;
- context-based tiering, grants and the always-confirm list (§6.6, §22);
- the virtual desktop as the default place for pointer work (§19);
- the GUI red-team and screen-memory privacy suites green before any release (§26).

WSL2 desktop control remains limited to Linux GUI applications in WSLg until a Windows-side helper exists (§25).

### 15.2 Voice

Voice input and output are planned for a later phase. Voice introduces microphone permissions, audio retention decisions, transcription errors, speaker ambiguity, and another channel for prompt injection. It should inherit the same trust and approval model rather than bypass it.

### 15.3 Team features

Team automation requires a new ownership model for:

- shared automations;
- approval delegation;
- connector credentials;
- audit visibility;
- budgets;
- pause authority;
- skill publishing.

It is not a simple multi-user switch.

### 15.4 Skill marketplace

A marketplace is gated on:

- manifest validation;
- malware and secret scanning;
- signing and publisher identity;
- version pinning;
- permission disclosure;
- revocation;
- update review;
- sandbox and reputation signals.

A curated first-party skill library with an opt-in "submit for review" path (`MT-M12`, Phase 5C) comes first. The open community marketplace (`MT-M08`) stays in Phase 6 and is off by default.

### 15.5 Official Google integrations

Gmail and some Drive scopes may require verification, CASA assessment, Limited Use compliance, and legal review. Menux should not promise official OAuth connectors until those obligations are resolved.

### 15.6 Menux Cloud

A cloud-hosted automation mode is explicitly not part of v1. It would require a separate trust model because automation specs, credentials, memory, and run content would no longer be device-only. It should be an opt-in product with separate disclosure and security review, not a silent change to the local node.

---

## 16. What Menux Does Not Promise

Menux does not promise:

- always-on operation when the device or WSL2 instance is stopped;
- Windows desktop automation from WSL2;
- that messages from strangers become trusted instructions;
- unrestricted unattended shell, browser, email, or financial actions;
- that a connector token leaves the local vault;
- that model providers never receive the content needed for a run;
- that a dry run performs real writes;
- that a scheduled automation retries forever after quota exhaustion;
- that a roadmap phase is already released;
- that an official Google integration exists before verification and legal gates pass;
- that cloud-hosted automations are available in v1;
- that a user can lower a capability's real trust tier by editing YAML;
- that Menux can operate every application: reliability differs by application and by control method, and `doctor` publishes the measured numbers;
- that pointer-and-screenshot control is as reliable or as fast as commands or application scripting;
- that screen memory exists unless the user turns it on, or that it records anything the user excluded;
- that screenshots never leave the device: on the CPU-only path an image may be sent to a model for a task, but only with the user's consent;
- that Menux works in real-time or competitive online games, or that it will bypass anti-cheat;
- that a shared skill is safe because it was shared: every shared skill is a template that is reviewed and enabled locally;
- that a third-party component is used when its licence does not allow it;
- that the Companion Expansion ships on any date: it is gated on Phase 4.

The honest product promise is local storage and execution, controlled remote reasoning, explicit trust tiers, visible approvals, bounded budgets, and recoverable automation state. For the Companion Expansion the promise adds: the user can always see what Menux sees, stop what Menux does, and delete what Menux remembers.

---

## 17. The Companion Vision and Reach Levels

*Status: planned, gated on Phase 4 (`MT-I04`). Nothing in §17–§27 is part of v1.*

### 17.1 What the Companion is

The Companion Expansion turns Menux from an automation node that observes, drafts and notifies into an agentic companion that can use the user's computer the way a person does, or better. It can run commands, drive applications, read what is on the screen, remember what the user was doing, and turn repeated work into skills. The user decides how much of this is allowed, can see everything Menux sees and does, and can stop it with one action.

The Companion is not a second product. It is the same node, the same account and credit pool, the same tiers (`T0–T5`), the same approvals, panic button and audit log, with more ways to act. Where an automation could previously only notify, it may now also act, within the limits the user sets (§22).

### 17.2 Reach levels

| Reach | Name | What Menux can do | Main mechanisms | Phase |
| :--- | :--- | :--- | :--- | :--- |
| **0** | Observe and notify | Schedules, triggers, drafts, notifications, approvals (§1–§16) | Connectors, channels, reader/actor | 0–4 (v1) |
| **1** | Commands, files and APIs | Run shell commands and scripts in a sandbox; work with granted folders and web APIs | Sandboxed shell tool, folder grants | 5A |
| **2** | Application and accessibility control | Drive applications through their own scripting interfaces, the accessibility tree and keyboard shortcuts; automate web pages through Playwright | LibreOffice, scriptable-application adapters, AT-SPI, shortcut maps | 5A |
| **3** | Vision and pointer | See the screen, find elements by sight, click and type on a virtual desktop or in turns on the real one; remember what was on screen | Capture, grounding, virtual desktop, screen memory | 5B |
| **4** | Specialist tools and learning | Purpose-built tools for hard applications (for example CAD), tools Menux drafts for itself, skills learned from demonstration, shared skill templates, strategy games | Tool kit, experience memory, skill templates | 5C |

A higher Reach level never replaces a lower one; it adds options. The reach a user actually has is also capped by the Control Dial (§22).

### 17.3 Releases

Each Reach level ships as its own release with its own acceptance milestone (`MT-I05a`, `MT-I05b`, `MT-I05c`). A release is useful on its own and the plan can stop there. The order is deliberate: the most reliable and most private methods come first, and vision and screen memory, the most sensitive features, come only after the safety layer (context-based tiering, grants, the dial) exists.

### 17.4 What the Companion does not change

- The device stays the source of truth (O1). The server still stores only the account, the ledger and short-lived run buffers.
- One account and one credit pool (O2). Vision calls and longer runs are metered under `surface='menux'`.
- The unattended ceiling stays at T2 unless the owner raises it through graduation (`MT-A06`).
- Coding still goes to M2C (O7). Menux does not become a second code editor.

---

## 18. The Control Ladder

### 18.1 The rule

For every task Menux uses the most reliable method that can do the job, and falls back one rung at a time. Reliability, privacy and cost all improve towards the top of the ladder.

| Rung | Method | Examples | Reliability |
| :--- | :--- | :--- | :--- |
| **1** | Commands, files and APIs | Convert a file, `git status`, rename 500 files, call a web API | Highest |
| **2** | Application scripting | LibreOffice through its UNO interface; FreeCAD, Blender and OpenSCAD through Python or the command line; web pages through Playwright | High |
| **3** | Accessibility tree | Read and activate named controls (buttons, menus, fields) through AT-SPI | Medium to high; depends on the application exposing them |
| **4** | Keyboard shortcuts | Send known shortcuts such as save or export; per-application shortcut maps | Medium; depends on window focus |
| **5** | Vision and pointer | Find elements by appearance, move the pointer, type; for custom-drawn applications, games and anything without accessibility | Lowest, slowest and most costly |

For an application with a registered **specialist tool** (§18.4), that tool is tried first for the operations it covers. When no rung can do the job, or the Control Dial does not allow it, Menux uses **Guide mode** (§18.6).

### 18.2 Application control profiles

Each application has a control profile: an identifier, how to recognize its window, which rungs are available, its tools and shortcut map, the tier of each operation, known quirks, and the last measured reliability. Profiles live in a local registry (`MT-X02`). Menux can draft a profile for a new application; the owner reviews it. Profiles contain no personal data and can be shared as templates (§23.6).

### 18.3 The selector

1. Check that the Control Dial allows this application and this rung (§22).
2. Pick the highest rung the profile supports.
3. Check the preconditions: the target exists, is visible and enabled, and is in the expected window and account.
4. Act.
5. Verify the postcondition: the expected change is visible or readable.
6. On failure, retry once, then step down one rung. Record the outcome (§23.2).
7. If every allowed rung fails, stop and tell the owner what happened and what the next step would be. A silent failure is a defect.

### 18.4 Specialist tools

Some applications cannot be driven well by scripting, accessibility or shortcuts: CAD is the leading example. For these Menux uses a specialist tool, a purpose-built tool for one application with a manifest, a tier per operation, fixtures and tests. Two sources:

- **Built by us** for major sectors, chosen by user demand (`MT-X08`).
- **Drafted by Menux** for an application the user needs (`MT-X09`). A drafted tool is a skill install, which is T4: it is tested in the sandbox, shown to the owner, versioned, and never self-activating.

### 18.5 Verification

- **Preconditions and postconditions** around every action, as above.
- **Fresh element references.** Pointer actions target an element reference from the latest accessibility or grounding result, not remembered coordinates. A failed extraction clears the cached elements so a stale reference cannot be clicked.
- **Checkpoints.** Multi-step plans may be proposed several steps at a time to save model calls, but each step is still verified before the next runs.
- **Fail closed.** If a target cannot be verified, the run stops; it does not guess.

### 18.6 Guide mode

When Menux may not act, cannot control the application, or the user simply prefers it, Menux can still *look* (if screen awareness is allowed, §20) and tell the user the next step in words or as an on-screen hint. Guide mode sends no input events and needs only T0–T1. It is the reason Menux is useful even in an application it cannot control.

---

## 19. Working Alongside the User

### 19.1 The principle

**The user always wins.** Menux must never fight the user for the mouse or keyboard, and the user must always be able to see and stop what Menux is doing.

### 19.2 Three modes

| Mode | Where Menux works | When it is used | What the user sees |
| :--- | :--- | :--- | :--- |
| **Background** (default for pointer work) | Menux's own virtual desktop | Any task that needs the pointer or a graphical window | Nothing, unless they open the live view; a notification says "working in the background" |
| **Shared** | The user's real screen, in turns | Tasks that must happen in an application the user already has open | A visible ghost cursor; Menux acts only while the user is idle and yields the moment the user touches the mouse or keyboard |
| **Watch and take over** | Menux's virtual desktop, shown live | When the user wants to check on Menux, help it, or finish a step themselves | A live window of Menux's desktop; the user can take control and hand it back |

Many tasks need no mode at all: commands, files, application scripting and browser automation do not touch the pointer (Reach 1–2), so they never conflict with the user.

### 19.3 The virtual desktop

A separate display session owned by Menux, disposable and isolated from the real session. It has its own browser profile and application instances, no access to the user's files except a granted staging folder, and network access only through the allowlist. Logged-in accounts exist there only if the user grants a specific site. Some applications refuse to run twice; for those Menux falls back to Shared mode or to application scripting.

### 19.4 Live view and take-over

A remote-desktop-style viewer, bound to localhost and authenticated, shows the virtual desktop. The user can watch, take over (their input goes to the virtual desktop) and hand back. Every handover is logged. Viewing from another device through the relay is not part of the first release and would need its own security review.

### 19.5 Shared mode and input arbitration

Menux detects user activity on the real session. On any user input it stops its own input at once, and it resumes only after the user has been idle for a configurable time (the default is to be tuned in testing, starting at about three seconds). If Menux and the user would collide, Menux moves the task to the virtual desktop by itself and tells the user. Shared mode is never unattended.

### 19.6 The tray control panel

A tray icon (or hidden icon, where the desktop allows it) gives quick control without opening a terminal:

- pause or resume Menux, and the panic button;
- the current mode, and a button to open the live view;
- on/off switches for screen awareness, screen memory and browser capture;
- the Control Dial: global ceiling, per-application allow, ask or block, and the list of active grants (§22);
- a hotkey for pause and panic.

Where a desktop has no tray, `menux dial` offers the same controls on the command line.

### 19.7 Platform notes

Wayland deliberately restricts screen capture and synthetic input, so the experience depends on the compositor. `menux doctor` reports a support matrix (GNOME, KDE, Hyprland, i3, COSMIC; Wayland and X11). Portal prompts may appear. An optional preconfigured session (§25.3) removes most of the setup. A research spike (`MT-V05`) will test whether two independent pointers can share the user's screen on X11; the product does not depend on the result.

---

## 20. Screen Awareness and Screen Memory

### 20.1 Two different features

- **Screen awareness** is Menux looking at the screen *now*, for a task: "what is on this page", "which button do I press". It needs a grant for the task.
- **Screen memory** is Menux remembering what was on screen *over time* so it can help later: "what was that article I read on Tuesday?". It is the most sensitive feature in the product.

Each has its own switch. Both are **off by default**.

### 20.2 Always visible, always pausable

Whenever capture is running an indicator is visible, and a single key or tray click pauses it. A run cannot hide the indicator.

### 20.3 What is captured, and when

Capture is **event-driven**, not continuous: on window focus changes, navigation, clicks, and pauses in scrolling or typing. Identical or near-identical captures are dropped. Capture pauses when the user is idle and can be limited on battery.

### 20.4 Text first

1. Menux reads the **accessibility text** of the window.
2. Where an application exposes none, it falls back to **OCR**.
3. Secrets and card-number patterns are redacted before anything is stored.
4. A small **thumbnail** may be kept for a short time (a proposed default is 24 hours) so the user can recognize a result. The **raw image is deleted** after extraction unless the user pins it.

Most captures therefore store only text and metadata.

### 20.5 What is never captured by default

Password managers; banking and payment pages and applications; private or incognito browser windows; windows that contain a password field; Menux's own vault and approval screens; and anything on the user's exclusion list (by application, site or window title).

### 20.6 Storage

Screen memory lives only on the device, under `~/.menux/screen/`: a SQLite database with FTS5 search (no embeddings, consistent with decision D9), encrypted with a key derived from the vault key. Each record carries the time, application, window title, URL (for browsers), source (accessibility or OCR) and a trust label. Proposed defaults, to be confirmed in testing: text kept 30 days, thumbnails 24 hours, with a disk cap that evicts the oldest first. The user can forget the last N minutes, forget one application, forget everything, and export their data.

### 20.7 Using the memory

Example: "what was that article I read on Tuesday about heat pumps?" The memory tool searches the local index and returns results with provenance. Results are **untrusted data**: they pass through the Reader (`MT-T04`), can never act as instructions, and become durable memory only through review (`MT-M03`).

### 20.8 What leaves the device

Nothing is stored on the server. Text or an image leaves the device only for a run that needs it, only within the user's permission, and is not kept after the run ends. A raw screen stream is never sent to the server. Audio capture is not part of this expansion; it belongs to the later voice work (§15.2) and would be opt-in on its own.

### 20.9 The timeline

A web page and tray entry (`MT-W09`) let the user scroll and search their screen memory, see what is excluded, change retention, and delete.

---

## 21. Perception Paths: CPU-Only and GPU

### 21.1 One interface, two paths

Everything that needs Menux to "see" is built behind one interface so that a machine without a GPU is a first-class user, not an afterthought.

| Step | CPU-only path | GPU path |
| :--- | :--- | :--- |
| Read text on screen | Accessibility text; CPU OCR | Same, with faster OCR |
| Find an element to click | Accessibility element if available; otherwise cloud grounding on a downscaled, cropped screenshot, with per-task consent | A local grounding model on the device |
| Understand a screen | Cloud vision, on demand | A local vision-language model (optional) |
| Privacy | Text first; an image leaves the device only when a task needs it and the user has agreed | Images stay on the device; only text descriptions go to the cloud |
| Cost | Cloud vision calls are metered in the shared credit pool | Local work costs no vision credits; planning calls are still metered |
| Speed | Slower per step | Faster per step |

### 21.2 Choosing a path

`menux doctor` probes the hardware (`MT-N08`) and recommends a path. The user can override it, and Menux falls back automatically if a local model is unavailable. Without consent for images, Menux runs in **text-only mode**: it can use accessibility text and Guide mode, and it says what it cannot do.

### 21.3 Cost and consent

Cloud vision is shown in cost estimates (`MT-E02`) and limited on the server (`MT-E03`). Consent is per task class, remembered locally, and revocable.

### 21.4 Models and licences

Local models are an optional download with a clear size warning. The weights and code of each candidate model have their own licences, reviewed through `MT-R05` (§27) before anything is bundled or depended on.

### 21.5 Honest limits

Pointer-and-screenshot control is the slowest and least reliable rung, and slowest on the CPU path. The documentation says so, and the benchmark (`MT-Q06`) publishes the measured numbers.

---

## 22. The Control Dial: Permissions, Grants and the Always-Confirm List

### 22.1 The global ceiling

The user chooses how much Menux may do on their own device:

| Setting | Meaning |
| :--- | :--- |
| **Observe only** | Menux may read and notify. Nothing is changed. |
| **Ask first** | Every action that changes anything needs approval. |
| **Trusted** (default for Reach 0–2) | Menux acts within the tier rules of §6: T0–T2 freely, T3–T4 with approval. |
| **Full control** | Menux may act on its own at T3–T4 **inside the scope of the user's grants** (§6.6). The always-confirm list (§22.5) still applies. |

Raising the ceiling for an unattended automation uses graduation (`MT-A06`); it is never silent.

### 22.2 Per-application stance

For every application and every rung the user can set **allow**, **ask** or **block**. Examples: allow LibreOffice at rungs 1–2; ask before any pointer control in a browser; block the password manager entirely. A blocked application cannot be seen, captured or controlled.

### 22.3 Per-capability switches

Screen awareness, screen memory (by source), browser capture, clipboard access, input synthesis, shell, and (later) audio each have their own switch, reachable from the tray.

### 22.4 Grants

A grant is a scoped, time-limited, revocable permission: "let Menux use LibreOffice on this folder for the next hour". Inside its scope it replaces the per-step approval of T3–T4 actions. It is logged, shown in the tray, and revoked by panic. A grant can never cover the always-confirm list.

### 22.5 The always-confirm list

Whatever the dial or any grant says, Menux **always** asks the owner before it:

- makes a payment or completes a checkout;
- types, reads aloud or exports a password, key or vault entry;
- deletes files outside Menux's own staging area or an explicitly granted scratch folder;
- sends content to a new third party or a new destination that is not already inside a grant;
- changes Menux's own dial, grants, policy or logging, or turns off the audit log;
- installs software, a tool or a skill;
- performs any action in a capability or context that Menux does not recognize (treated as T5).

### 22.6 Where the controls live

The tray or hidden icon, `menux dial`, the web inbox, and a hotkey for panic. Settings are stored locally and survive a restart; panic overrides everything.

---

## 23. Self-Built Automations, Learning, Skill Sharing and the Menux Map

### 23.1 Menux builds its own automations

When a task would benefit from a repeatable automation or skill, Menux can draft one, dry-run it, test it, and revise it later as needs change. A draft goes to the review queue (`MT-M05`); **nothing becomes active until the owner enables it**. An owner may opt in to automatic enabling for drafts whose capabilities are all T1 or lower. That option is off by default.

### 23.2 Experience memory

Menux records which rung and which steps worked for which application and task, with the outcome and cost, and uses it to pick a faster path next time. It is local, the owner can view and delete it, and it is labeled untrusted until repeated success confirms it (`MT-M09`).

### 23.3 Learning by demonstration

In record mode the user shows Menux a task once. Menux uses the accessibility events and screen memory to draft a parameterized skill, dry-runs it, and queues it for review (`MT-M10`).

### 23.4 Self-repair

Graphical skills break when an application's interface changes. When a postcondition fails, Menux tries another rung, proposes a patched version of the skill, and keeps the old version for rollback after review (`MT-M11`, `MT-A06`).

### 23.5 The Menux Map

An all-in-one map shows how Menux is connected to everything: applications, connectors, channels, skills, automations and grants, with the links between them, each automation's tier, last run and health. Clicking a node opens the local specification or skill for editing; edits go to the device, never to the server. The map is built from local data and served live through the UI relay (`MT-K04`), so it adds nothing to server storage. It also highlights grants that are wider than recent use (`MT-W08`).

### 23.6 Sharing skills

Skills can be shared so that another user's Menux can build the same automation instantly, but **only as a sanitized, signed template**, never as the user's real automation or data:

1. **Sanitize:** strip file paths, names, email addresses, tokens, identifiers and URLs that contain them.
2. **Parameterize:** replace specifics with named parameters.
3. **Permission manifest:** list capabilities, tiers, egress and applications.
4. **Scan and trial:** static scan, then a sandboxed trial with canary secrets.
5. **Sign:** publisher identity and signature.
6. **Store:** the server keeps only the template (migration `0020`), never runs or personal data.
7. **Install elsewhere:** the receiving owner sees the manifest, tier, egress and applications, binds the parameters locally, and the skill stays disabled until enabled.

Release order: a **first-party curated library** with an opt-in "submit for review" path (`MT-M12`, Phase 5C), then the open community marketplace (`MT-M08`, Phase 6, off by default).

### 23.7 Why this strictness

A skill runs with the user's permissions. Public registries for agent skills have already carried malicious skills, and memory and scheduler abuse are known attacks on always-on agents. Templates, manifests, scanning, signing and local enabling keep sharing useful without making it the easiest way to attack a user.

---

## 24. Games and Input Maps

### 24.1 Input maps

An input map names an application's actions and their keys: for example movement keys for a game, or an editor's shortcuts. Maps are user-defined, validated, stored per application, and usable by any automation (`MT-X05`).

### 24.2 Scope

Menux can play and automate **strategy and turn-based games** (chess, board, card and puzzle games), and **slow-paced live games** such as idle or resource-management games. For these it can use an engine as a tool (for example a chess engine run as a separate process). For anything timed it splits the work: the large model is the strategist and a fast local loop is the executor (`MT-X10`).

### 24.3 Out of scope

Real-time action titles at human-competitive speed, anything that bypasses anti-cheat, and competitive online play where automation is prohibited. Whether an online service allows automation is the user's responsibility. The game profile is **off by default**, shows a notice when enabled, and runs on the virtual desktop where possible.

### 24.4 Tiering

A game window in a disposable session with no accounts is contained input (T1, §6.6). A game account is an account: input into a logged-in online game is tiered by context (T3–T4).

---

## 25. Platforms and Distribution

### 25.1 Linux first

Native Linux is the reference platform. Ubuntu, Debian and Fedora are the supported distributions for release testing (as in the GA checklist). GNOME and KDE are first-class; Hyprland, i3 and COSMIC are best effort, according to the `doctor` support matrix.

### 25.2 Wayland and X11

Wayland requires portals for screen capture and synthetic input, and may prompt the user. `/dev/uinput` access and accessibility must be enabled; `doctor` explains how. An X11 session remains a fallback where Wayland is not workable.

### 25.3 The Menux session image

To remove setup problems, an optional preconfigured **Menux session** (`MT-N09`) provides the display session, portals, `uinput` permission, accessibility settings and virtual-desktop tooling. It starts as a package or install script, later a VM or bootable image. **A full Linux distribution is out of scope until after GA**; the session image captures most of the benefit without the cost of maintaining drivers, updates and security for an operating system.

### 25.4 WSL2

| Works on WSL2 | Does not work on WSL2 (yet) |
| :--- | :--- |
| Commands, files, scripts, Git; automations, memory, skills, approvals | Controlling Windows applications such as Microsoft Office, SolidWorks or Windows games |
| Reading and writing Windows files under `/mnt/c` (read-only by default) | Seeing or capturing the Windows desktop |
| Linux applications in WSLg; a browser inside WSL | Sending keyboard and mouse input to Windows applications |
| Everything in Reach 0–2 that runs inside Linux | Always-on operation when the WSL instance is stopped |

### 25.5 The Windows-side helper

To control Windows applications, a small native Windows process in the user's session would expose screenshots, input and Windows UI Automation to the WSL2 node over an authenticated local channel, while the reasoning, memory, tiers and approvals stay where they are. It is designed and threat-modelled in `MT-D07` (Phase 5C) and built in `MT-D08` (Phase 6) only if the review passes. It is not a product promise.

### 25.6 Native Windows and macOS

Deferred, as before.

---

## 26. Companion Safety Additions

### 26.1 Screen content is untrusted

Anything on the screen can contain instructions meant for an AI. The reader/actor split (§7.3) is extended to pixels (`MT-T11`): a tool-less Reader pass turns a screenshot or screen text into a typed result (elements, roles, names, and visible text as quoted data), and the Actor sees only that result. Visible text can describe the screen; it cannot instruct Menux.

### 26.2 The task-scope guard

Each run keeps its original task. An action that is off that task, such as a new domain, a new application, a terminal, a download-and-run, a permission dialog or a credential field, escalates to approval, even inside a grant.

### 26.3 Spoofed prompts

Operating-system permission prompts and in-application dialogs can be faked. Menux never grants OS-level permissions to itself; permission prompts are shown to the user and answered by the user.

### 26.4 Clipboard and file dialogs

Clipboard contents are untrusted data. Clipboard access has its own switch (§22.3).

### 26.5 Memory poisoning

Screen memory and experience memory are labeled untrusted and reach durable memory only through review (`MT-M03`).

### 26.6 Failure behavior

Everything fails closed. If a target cannot be verified, pointer actions stop. Panic suspends the virtual desktop session, stops new input and revokes all grants.

### 26.7 Tests that block release

| Suite | WP | What it proves |
| :--- | :--- | :--- |
| GUI red-team | `MT-Q07` | Hostile pages, fake dialogs, on-screen instructions, clipboard attacks and look-alike windows cannot drive an unsafe action |
| Screen-memory privacy and canary | `MT-Q08`, `MT-Q04` | No screen content at rest on the server; exclusions hold; deletion is real; the indicator cannot be hidden |
| Control reliability benchmark | `MT-Q06` | Measured success per application, rung and compositor; weak rungs default to "ask first" |

---

## 27. Reuse or Build: Licences and Candidate Components

### 27.1 The rule

Several existing projects could save months of work, but their licences differ. Before any Menux package depends on, bundles or copies from a third-party component, `MT-R05` must record a decision for it in `docs/menux/third_party.md`:

1. read the licence text itself, not a summary;
2. classify it (permissive; weak copyleft; strong or network copyleft; source-available or non-commercial; unknown);
3. decide: use as a dependency, use only as a separate process, study the design only, or build our own;
4. add the `NOTICE` entry and pin the version;
5. write the own-build fallback.

The owner of the project reviews and signs off each decision. If a licence does not fit, Menux builds its own component; that is an accepted outcome, not a failure.

### 27.2 Candidate components

The licences below are what the project pages and package metadata reported when reviewed on 2026-10-26. They are **not verified decisions**. Items marked *believed* come from memory and were not checked.

| Component | Role in Menux | Licence as reported | Action |
| :--- | :--- | :--- | :--- |
| `computer-use-linux` | Linux control layer: AT-SPI, portal screenshots, `ydotool` input, window targeting (`D02`, `D03`) | MIT (crate metadata) | Confirm; otherwise build our own behind `ControlBackend` |
| Screenpipe | Reference for screen memory (`S01–S03`) | Reported inconsistently: MIT on some of its pages, "source-available" in its repository | Read its `LICENSE` file; **copy no code** until resolved; otherwise design reference only |
| OmniParser | Screen parsing for grounding (`S05`) | Detection weights AGPL, caption weights MIT, as reported | AGPL may restrict commercial or closed use; review; fallback is our own detector with OCR and accessibility |
| UI-TARS, GTA1, Holo, Moondream and similar | Local grounding models (`S05`, GPU path) | Per model | Review each model's licence before bundling or recommending |
| `ydotool` | Wayland input injection (`D03`) | *Believed* copyleft | Verify; if needed write to `uinput` directly or use the RemoteDesktop portal |
| Playwright | Browser automation (`D01`) | *Believed* permissive | Verify |
| OCR engine (Tesseract-class) | CPU OCR (`S02`) | *Believed* permissive | Verify |
| Chess or other game engines | Engine tools (`X10`) | *Believed* strong copyleft for some | Use only as a separate process, after review |

### 27.3 Swap boundaries

Each candidate sits behind a Menux interface (`ControlBackend`, `Capturer`, `Grounder`, `OcrEngine`, `GameEngine`), so replacing it with our own implementation touches one module. The CPU-only and GPU paths (§21) are two implementations of the same `Grounder`.

---

## 28. Maintenance Checklist

For every Menux release, verify:

- [ ] `menux doctor` identifies platform, WSL, service, vault, account, and sandbox problems.
- [ ] The node uses a single-instance lock and shuts down cleanly.
- [ ] Automation YAML passes schema and semantic validation.
- [ ] Unknown capabilities fail closed.
- [ ] Capability tiers and connector tiers combine using the higher-risk rule.
- [ ] Dry run cannot perform real writes or sends.
- [ ] Cron, interval, time zone, DST, jitter, dedupe, and missed-run tests pass.
- [ ] Heartbeats do not call the model when nothing changed.
- [ ] Quota exhaustion skips scheduled work without an infinite retry loop.
- [ ] Panic pauses new work and blocks external actions.
- [ ] Approvals verify owner identity, nonce, expiry, and run identity.
- [ ] Stranger channel messages never become instructions by default.
- [ ] Connector tokens never appear in prompts, logs, results, or browser events.
- [ ] Reader/actor separation protects against untrusted content injection.
- [ ] File grants and protected paths are enforced.
- [ ] Webhook payloads expire and are deleted after delivery.
- [ ] Restart recovery does not duplicate triggers.
- [ ] Local event history remains available after server disconnect.
- [ ] Shared account credits are enforced server-side.
- [ ] M2C delegation preserves M2C's policy and sandbox.
- [ ] Memory provenance, deletion, and poisoning defenses are testable.
- [ ] Browser inbox is live-relay behavior, not accidental permanent content storage.
- [ ] Telegram callbacks from non-owners are rejected.
- [ ] Legal and compliance gates are visible for Google and marketplace features.
- [ ] Planned and gated capabilities remain labeled accurately.

**Companion Expansion releases (5A, 5B, 5C) also verify:**

- [ ] Every third-party component is in `docs/menux/third_party.md` with a recorded licence decision and an own-build fallback.
- [ ] The ladder selector uses the highest supported rung, steps down on failure, and ends in a message to the owner, never a silent failure.
- [ ] Every pointer or keyboard action checks its preconditions and verifies its postconditions; failed verification stops the run.
- [ ] Context-based tiering holds: contained input is T1 only in a disposable session with no accounts; unknown context takes the higher tier.
- [ ] Grants are scoped, expire, can be revoked, are logged, and never cover the always-confirm list.
- [ ] Panic stops the virtual desktop, revokes all grants and survives a restart.
- [ ] In Shared mode the user's input always wins and Menux yields.
- [ ] Screen memory is off by default, an indicator is visible whenever capture runs, exclusions hold, and "forget" really deletes (indexes and backups included).
- [ ] No screen content, screenshot or extracted text is at rest on the server (canary).
- [ ] The CPU-only path never sends an image without consent; the GPU path keeps images on the device.
- [ ] The GUI red-team suite (`MT-Q07`) is green on the release build.
- [ ] A shared skill template contains no personal strings from the seeded canary and installs disabled.
- [ ] The game profile is off by default and shows the anti-cheat notice.
- [ ] Reliability numbers per application, rung and compositor are published and match the benchmark.
- [ ] WSL2 and Windows documentation says plainly what is and is not controllable.

---

## 29. Source Map

The main planning sources for this manual are:

- `data/docs/Menux___Build_Execution_Guide.md`;
- `data/docs/m2c_build_plan.md`;
- the MiniMe device, usage, task, workspace, and integration surfaces;
- the planned `minicore/`, `menux/`, and `backend/mate/` packages;
- the protocol, policy, sandbox, connector, memory, and quality work packages described by the build guide.

This document is the user-facing feature layer. The build guide remains authoritative for patch order, exact modules, tests, dependency gates, and implementation status.

**Design references for the Companion Expansion (§17–§27).** These projects were reviewed on 2026-10-26 for design ideas only. They are not dependencies, and none of their code is used until `MT-R05` records a licence decision (§27):

- Microsoft UFO2: a host agent with application-specialized agents, a unified GUI-and-API action layer, hybrid accessibility-plus-vision control detection, and a Picture-in-Picture virtual desktop so agent and user can work at the same time.
- Agent S (Simular): experience-augmented hierarchical planning, continual memory of past tasks, an agent-computer interface, and the split between a planning model and a grounding model.
- Screenpipe: event-driven screen capture, accessibility text first with OCR fallback, local SQLite storage, content-type switches, and local-model support.
- `computer-use-linux` and similar Linux MCP servers: AT-SPI accessibility trees, screencast-portal screenshots, RemoteDesktop-portal and `ydotool` input, and window targeting across GNOME, KDE, Hyprland, i3 and COSMIC.
- OmniParser, UI-TARS and Cua: screen parsing and grounding models, and pairing a local grounding model with a cloud planner so that screenshots stay on the device.
- OpenClaw: skills as plain readable files, a heartbeat, layered memory, and one gateway for many channels; also the cautionary tale of malicious skills in a public registry, exposed instances, memory poisoning and heartbeat abuse (the reasons for CX6 and §26).
- AIOS: kernel-style services for agents (scheduler, context, memory, storage, tools and an access manager), a useful checklist for what a local agent runtime needs.
