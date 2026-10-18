# MiniMate Feature Guide

**Purpose:** the user manual and feature register for MiniMate, MiniMe's local-first personal automation system.

**Status:** MiniMate is a staged product plan built on the MiniMake engine. This guide records the intended user experience and trust model while clearly separating planned, gated, and future capabilities.

- **Available or inherited:** behavior provided by MiniMe/MiniMake foundations or already defined as a shared contract.
- **Planned:** described in the current MiniMate build plan but not necessarily implemented.
- **Gated:** requires MiniMake maturity, security review, legal review, credentials, or a later milestone.

### Architectural Synchronization (Overrides O1–O8 from `MiniMate___Build_Execution_Guide.md`)

Where the earlier standalone design note (`doc-minimate-product.html`) and this guide or `MiniMate___Build_Execution_Guide.md` differ, **these 8 synchronized rules govern**:

| Override ID | Architectural Rule | How It Connects Across the Book |
| :--- | :--- | :--- |
| **O1 · Local-First Node Authority** | Scheduler, Run Engine, Approval Manager, 6 channel adapters, 9 connectors, Playwright browser, and Argon2id vault run on the user's device (`~/.minimate/`) | Server holds zero connector tokens, zero automation YAML, and zero permanent run logs (`minime_server_management_guide.md` §9) |
| **O2 · One Account, One Cap, One Shared Ledger** | Uses the user's MiniMe plan (`Free / Basic $9 / Moderate $29 / Ultimate $79`) and logs into `usage_ledger` with `surface='minimate'` | Reuses `0012_usage_ledger_and_plans.sql` built in MiniMe `Tech-A/B` + MiniMake `S01` |
| **O3 · Ephemeral 24h Redis Buffer** | In-flight server session state lives in Redis for at most 24h (idle 2h, max 500 events / 256 KB) so multi-hour approvals can resume | Enforced by canary test `MT-Q04` (zero user content in Postgres) |
| **O4 · Built on `minicore/` After MiniMake M2** | Starts once MiniMake reaches Invite-Only Beta (`M2`), reusing `minicore/`, device-code auth, and `bubblewrap` | Planned window on Master Timeline: **Mar – Jun 2027** (59 WPs, 16 waves, 133 pts) |
| **O5 · Backend Route Namespace** | Server routes mount under `/api/minimate/*` (`backend/minimate/` / `backend/mate/`) with `profile="mate"` | Shares brain turn loop with `/api/codeagent/*` |
| **O6 · Reader / Actor Pipeline for Untrusted Data** | Any run ingesting untrusted emails, web pages, or stranger messages runs a tool-less Reader pass before the Actor pass | Blocks indirect prompt injection (`MT-T04`, `MT-Q02`) |
| **O7 · Coding Delegated to MiniMake CLI** | MiniMate never implements a second code editor; coding tasks invoke `minimake run --json` over local IPC (`MT-M07`) | Preserves MiniMake's git checkpoints and OS sandbox |
| **O8 · Official Google Scopes Gated on CASA** | Local CalDAV/IMAP/ICS work immediately; official Google OAuth scopes wait for verification & legal gate (`MT-G03`) | Matches `MiniMe_Financial_Strategy_Rulebook.md` compliance gates |

---

## 1. What MiniMate Is

MiniMate is a personal automation node that runs on the user's device. It watches schedules, events, files, messages, and other approved triggers, then asks the MiniMe reasoning engine to decide what to do and executes approved local tools.

MiniMate is intended for work such as:

- sending a morning summary;
- watching a folder and processing new files;
- checking a calendar or mailbox;
- notifying the owner when a condition changes;
- drafting an email or message;
- running a repeatable project workflow;
- delegating coding work to MiniMake;
- maintaining local memory and skills;
- responding to a paired channel such as Telegram;
- asking for approval before an external or irreversible action.

The local node is the scheduler, connector host, credential vault, memory store, approval store, and tool executor. The MiniMe server supplies the model-driven Brain, planning, orchestration, metering, and account-level limits. The server is not intended to become the permanent home of automation specifications, connector tokens, or run history in v1.

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

State is intended to live under `~/.minimate/`, including a SQLite database plus automation, memory, skill, log, and configuration files. The directory should be protected with restrictive permissions.

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

Model providers receive the prompt content needed for a run. Telegram receives messages sent through the user's bot. Connectors receive the data required by their own APIs. MiniMate's honest privacy statement is therefore:

> Your automations, memory, skills, and connector credentials are stored on your device. When an automation runs, the content it needs is sent to our servers and model providers to produce the result; we do not keep it after the run ends. Messages from people you have not paired are treated as data, never as instructions. You can pause everything with one button.

---

## 3. Installation and Node Lifecycle

### 3.1 Prerequisite

MiniMate depends on MiniMake's shared foundations. The intended starting gate is MiniMake's invite-only beta milestone. MiniMake supplies:

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

MiniMate should not duplicate these controls.

### 3.2 Node commands

The intended command family includes:

- `minimate init`;
- `minimate login`;
- `minimate status`;
- `minimate run`;
- `minimate stop`;
- `minimate service install`;
- `minimate service uninstall`;
- `minimate doctor`;
- `minimate automation list`;
- `minimate automation validate`;
- `minimate automation dry-run`;
- `minimate automation enable|disable`;
- `minimate vault add|list|remove`;
- channel pairing and connector commands.

Some commands remain design targets until the corresponding build packages land.

### 3.3 Foreground and service operation

On systems with systemd, MiniMate is intended to install a systemd user service. Where systemd is unavailable, such as many WSL2 setups, it runs in the foreground or through a guided keep-alive process.

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

WSL2 is supported with an important limitation: automations run only while the WSL instance is alive. MiniMate is intended to provide guided keep-alive setup and a `doctor` warning when it is missing.

For always-on use, the plan recommends a small Linux machine or other continuously running host. MiniMate does not promise Windows desktop automation from WSL2. Desktop control reaches Linux GUI applications inside WSLg only, not ordinary Windows applications.

Native Linux receives the full intended feature set. Native Windows and macOS are deferred for the initial product.

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

MiniMate's intended automation tiers are:

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
| **T3 · External Write / Third-Party Send** | High | Send email/message to third party, create shared calendar event, POST to external webhook, delegate edit to MiniMake | **Requires explicit cryptographic owner approval (`nonce` + 15m TTL)** |
| **T4 · Browser Action / Shell / System** | Very High | Playwright authenticated form submit (`MT-W01`), sandboxed shell script, skill install | **Requires explicit step-by-step owner approval with parameter preview** |
| **T5 · Financial / Credential / Destructive** | Critical | Payment/checkout action, vault export, deleting non-staged files, modifying security policy | **Blocked unattended; requires interactive local CLI confirmation + re-auth** |

### 6.2 Effective tier

A tool's effective tier is the higher of:

- the MiniMake risk level declared by the tool;
- the tier declared by the MiniMate connector or automation.

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

MiniMate is intended to provide a one-action pause for all automations. Panic behavior should:

- stop starting new runs;
- cancel or request cancellation for active runs;
- block connector actions;
- keep the local audit record;
- notify the owner when the system is paused;
- require an explicit resume action.

A panic state must survive a node restart until the owner clears it.

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
| **Local Watched Folders (`MT-H03`)** | Connector + Trigger | Read granted folder / Write to staging dir | `T1` (staging) · `T3` (outside staging) | Explicit per-automation `folder_grants`; blocks `~/.ssh`, `~/.minimate/vault.enc`, `.env*` |
| **Playwright Browser (`MT-W01`)** | Headless Automation | Read allowed domains / Fill & click (`T4`) | `T1` (read-only) · `T4` (stateful act) | Ephemeral context per run; blocks `file://`, RFC1918 local IPs, and password/payment fields |
| **Inbound Webhooks (`MT-H08`, `MT-G04`)** | Trigger | Receive signed JSON payload (≤ 64 KB, 10m TTL) | `T1` (ingest via Reader) | HMAC-SHA256 verification; payload deleted from server relay immediately after node pull |
| **MiniMake IPC Bridge (`MT-M07`)** | Sibling Delegation | Invoke `minimake run --json` on local repo | `T2` (Ask/Plan) · `T3` (Edit/Patch) | Inherits MiniMake's `bubblewrap` sandbox, git checkpoints, and path guard |
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

### 8.8 Future connectors

The connector host is intended to support additional services through manifests. Official Google connectors are gated by legal and compliance review because Gmail restricted scopes, CASA assessments, verification, Limited Use requirements, and model-provider handling of mail content create material obligations.

A bring-your-own OAuth client may be available earlier for personal testing. It should not be described as the same thing as a generally available official Google integration.

---

## 9. Memory and Knowledge

### 9.1 Local memory

MiniMate can store reusable memory on the device:

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

MiniMate can notify the owner about:

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

## 11. MiniMate and MiniMake Cooperation

MiniMate can delegate coding tasks to the installed MiniMake CLI through local IPC. This allows an automation to say, for example:

- inspect a repository after a dependency alert;
- run the project's tests;
- prepare a patch for a known issue;
- summarize a code review;
- update a changelog draft;
- create a proposal for owner approval.

MiniMate should not implement a second coding sandbox. MiniMake remains responsible for code-specific policy, checkpoints, file proposals, and execution limits. The delegation boundary carries the automation profile and trust context into a headless coding run.

Delegated code changes remain proposals unless the automation's declared tier, policy, and approval path explicitly allow the action.

---

## 12. Economics and Budgets

### 12.1 One account and one pool

MiniMate shares one account and one credit pool with:

- the MiniMe web application;
- MiniMake;
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

### 13.1 `minimate doctor`

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
- stale migrations;
- clock and time-zone configuration.

The output should explain fixes rather than merely report a failed boolean.

### 13.2 Restart recovery

After a restart, MiniMate should:

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

Inventory finished MiniMake code, extract shared `minicore`, add the automation profile, extend the protocol, define the automation schema, and define the trust-tier registry.

### Phase 1: first automation

The walking skeleton is:

1. install the node;
2. sign in and pair the device;
3. configure a Telegram bot;
4. describe or create a scheduled automation;
5. run the server Brain;
6. send a safe T2 notification to the owner;
7. meter the run under the shared MiniMate surface.

No broad unattended external action is required for this milestone.

### Phase 2: safe unattended operation

Add tiers, approvals, the reader/actor split, taint tracking, panic, the browser inbox, email/calendar/file readers, and stronger automation budgets.

### Phase 3: memory, skills, and triggers

Add memory search, memory poisoning defenses, skill manifests, reviewed skill drafts, file/webhook/poll triggers, and heartbeat gating.

### Phase 4: invite-only beta

Add planner chat, MiniMake delegation, WSL keep-alive guidance, cost estimates, browser automation surfaces, and complete operational documentation.

### Phase 5: desktop and voice

Potential additions include Linux desktop control through AT-SPI or `ydotool`, a headless desktop container, voice input/output, and more connectors.

### Phase 6: ecosystem and release

Potential additions include a scanned and signed skill marketplace, team features, official Google connectors if legally approved, external security audit, packaging, support, and general availability.

| Phase & Milestone | Waves | Work Packages | Effort Points | Key Deliverable & Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0 · Foundations & Contracts** | Waves 1–2 | `MT-K00–K03`, `MT-A01`, `MT-T01` (6 WPs) | 12 pts | Prerequisite check on `minicore/` (`MT-K00`), automation YAML JSON Schema (`MT-A01`), `T0–T5` tier matrix (`MT-T01`) |
| **Phase 1 · First Automation (`MT-I01`)** | Waves 3–5 | `MT-N01–N02`, `MT-N04–N06`, `MT-G01`, `MT-A02–A04`, `MT-H01`, `MT-H03`, `MT-I01` (12 WPs) | 28 pts | Local daemon (`~/.minimate/`), Argon2id vault (`MT-N04`), APScheduler cron (`MT-H01`), dry-run engine (`MT-A03`), first live morning briefing (`MT-I01`) |
| **Phase 2 · Safe Unattended Operation (`MT-I02`)** | Waves 6–9 | `MT-H02`, `MT-H04–H06`, `MT-T02–T08`, `MT-A05–A06`, `MT-K04`, `MT-G02`, `MT-G04`, `MT-W01`, `MT-Q01–Q02`, `MT-Q04`, `MT-I02` (21 WPs) | 49 pts | Telegram inline approvals (`MT-H02`), Reader/Actor pipeline (`MT-T04`), panic switch (`MT-T07`), Playwright (`MT-W01`), prompt-injection & canary tests (`MT-I02`) |
| **Phase 3 · Memory, Skills & Triggers (`MT-I03`)** | Waves 10–12 | `MT-M01–M07`, `MT-N03`, `MT-H07–H08`, `MT-G03`, `MT-E01`, `MT-Q03`, `MT-I03` (14 WPs) | 30 pts | Provenance-tagged memory (`MT-M01`), poisoning defense (`MT-M02`), signed skill manifests (`MT-M04`), MiniMake delegation (`MT-M07`) |
| **Phase 4 · Invite-Only Beta (`MT-I04`)** | Waves 13–16 | `MT-A07`, `MT-N07`, `MT-E02`, `MT-Q05`, `MT-R02`, `MT-I04` (6 WPs) | 14 pts | Natural-language Planner draft (`MT-A07`), WSL2 keep-alive helper (`MT-N07`), cost estimator (`MT-E02`), 7-day unattended soak (`MT-I04`) |
| **Phases 5–6 · Desktop, Voice & GA** | Post-Beta | Linux AT-SPI desktop, voice, signed marketplace, GA | Gated on `MT-I04` | Headless desktop container, CASA verification for Google scopes, external security audit |

---

## 15. Future and Gated Features

### 15.1 Desktop control

Desktop automation is not the first trust boundary. If added, it requires:

- Linux desktop APIs or controlled input tooling;
- a headless desktop container where appropriate;
- explicit screen and input permissions;
- stronger T4/T5 approvals;
- protection against acting on the wrong window or account.

WSL2 desktop control remains limited to Linux GUI applications in WSLg.

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

### 15.5 Official Google integrations

Gmail and some Drive scopes may require verification, CASA assessment, Limited Use compliance, and legal review. MiniMate should not promise official OAuth connectors until those obligations are resolved.

### 15.6 MiniMate Cloud

A cloud-hosted automation mode is explicitly not part of v1. It would require a separate trust model because automation specs, credentials, memory, and run content would no longer be device-only. It should be an opt-in product with separate disclosure and security review, not a silent change to the local node.

---

## 16. What MiniMate Does Not Promise

MiniMate does not promise:

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
- that a user can lower a capability's real trust tier by editing YAML.

The honest product promise is local storage and execution, controlled remote reasoning, explicit trust tiers, visible approvals, bounded budgets, and recoverable automation state.

---

## 17. Maintenance Checklist

For every MiniMate release, verify:

- [ ] `minimate doctor` identifies platform, WSL, service, vault, account, and sandbox problems.
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
- [ ] MiniMake delegation preserves MiniMake's policy and sandbox.
- [ ] Memory provenance, deletion, and poisoning defenses are testable.
- [ ] Browser inbox is live-relay behavior, not accidental permanent content storage.
- [ ] Telegram callbacks from non-owners are rejected.
- [ ] Legal and compliance gates are visible for Google and marketplace features.
- [ ] Planned and gated capabilities remain labeled accurately.

---

## 18. Source Map

The main planning sources for this manual are:

- `data/docs/MiniMate___Build_Execution_Guide.md`;
- `data/docs/minimake_build_plan.md`;
- the MiniMe device, usage, task, workspace, and integration surfaces;
- the planned `minicore/`, `minimate/`, and `backend/mate/` packages;
- the protocol, policy, sandbox, connector, memory, and quality work packages described by the build guide.

This document is the user-facing feature layer. The build guide remains authoritative for patch order, exact modules, tests, dependency gates, and implementation status.
