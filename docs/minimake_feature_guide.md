# MiniMake Feature Guide

**Purpose:** the user manual and feature register for MiniMake, the local-first coding agent built on the MiniMe platform.

**Status:** MiniMake is specified and being built in phases. This guide records the intended product behavior from the current build plan. It labels planned behavior explicitly because the plan contains work packages, not proof that every package has shipped.

- **Available or inherited:** behavior already present in the MiniMe web application or explicitly carried forward into MiniMake.
- **Planned:** behavior described by the MiniMake build plan but not yet verified as released.
- **Gated:** behavior that requires a milestone, safety review, legal decision, or external service configuration first.

### Architectural Synchronization (Overrides O1–O8 from `minimake_build_plan.md`)

Where the earlier standalone design note (`doc-minimake-product.html`) and this guide or `minimake_build_plan.md` differ, **these 8 synchronized rules govern**:

| Override ID | Architectural Rule | How It Connects Across the Book |
| :--- | :--- | :--- |
| **O1 · Local-First Data Placement** | Repo files, SQLite `index.db`, git checkpoints, and shell/test runs stay on the user's device; server keeps only `usage_ledger` + 2h Redis buffer | Keeps server RAM/CPU near zero (`minime_server_management_guide.md` §9) |
| **O2 · One Account, One Cap, One Ledger** | Shares the user's MiniMe tier (`Free / Basic $9 / Moderate $29 / Ultimate $79`) via `usage_ledger` (`surface='minimake'`, WP `S01`) | Built once with MiniMe `Tech-A/B` (`MiniMe_Financial_Strategy_Rulebook.md` Rule 4) |
| **O3 · Linux & WSL2 First** | v1 targets native Linux and Windows via WSL2 (`bubblewrap`); native Windows & macOS deferred to post-GA | Enforced by `minimake doctor` (`C04`, `C21`) |
| **O4 · Python CLI + `minicore/`** | Distributed via `uv tool install minimake` / `pipx`; shares `minicore/` package with `backend/` and `minimate/` | Extracted in WP `P00` (`Wave 1`) |
| **O5 · Backend Route Namespace** | Server package lives at `backend/codeagent/` mounted under `/api/codeagent/*` | Avoids collision with existing `backend/agents/coder.py` |
| **O6 · Phase 0 Browser Slimming** | Removes browser Python `Run`, `Terminal`, and `Local-folder mode` (`MK_B02–B06`); replaces with CLI handoff | Synchronized with `minime_feature_guide.md` §9.3 & §17.2 |
| **O7 · Account Required (No Offline v1)** | Reasoning loop runs on MiniMe server using the 8-provider router; requires sign-in (`minimake login`) | Preserves Rulebook model routing & prompt caching |
| **O8 · Profile Field (`profile="code"`)** | Every run carries `profile: "code"` so `minimate` can reuse the same protocol with `profile: "mate"` | Shared contract in `minicore/protocol.py` (`P00`) |

---

## 1. What MiniMake Is

MiniMake is a coding-focused agent that works with a user's project on the user's device while using the MiniMe server and model providers for reasoning. It is intended to combine:

- a terminal-first coding workflow;
- a browser editor and project explorer;
- AI chat with Ask and Edit modes;
- proposed changes instead of silent file mutation;
- checkpoints, rewind, history, and conflict review;
- a local policy engine and sandbox;
- skills, hooks, memory, secrets handling, and MCP tools;
- headless use for automation and MiniMate delegation;
- one shared account and usage pool across MiniMe, MiniMake, and MiniMate.

The product's trust model is local-first, not local-only. Project files, history, settings, approvals, checkpoints, and local logs are intended to remain on the device. Relevant code and prompt context are sent to the MiniMe server and model providers during a run. The service keeps usage numbers and only the short-lived in-flight content needed to complete an active run; it does not promise that code never leaves the device.

MiniMake is designed for Linux and WSL2 in version 1. Native Windows, WSL1, and macOS are not part of the initial supported platform promise.

---

## 2. Installation and Environment

### 2.1 Supported environment

The initial supported environments are:

- Ubuntu 22.04 or newer;
- Debian 12;
- current Fedora;
- Arch Linux on a best-effort basis;
- Ubuntu running inside WSL2 as the primary Windows path.

Projects should live in the Linux filesystem, such as `~/code/project`. Projects under `/mnt/c` are discouraged because of filesystem performance and permission differences. `doctor` warns about unsuitable project locations and may refuse to sandbox them.

Native Windows is not supported by the first version. WSL1 is not supported. macOS is deferred until a later sandbox backend is available.

### 2.2 Installation

The intended distribution is a Python package installed with `uv tool install minimake` or `pipx`, plus an installer script that:

- installs or checks `uv`;
- checks for `ripgrep`;
- checks for `git`;
- checks for `bubblewrap`;
- installs the command-line client;
- runs `minimake doctor`;
- explains missing dependencies and supported alternatives.

A bundled native binary may be added later. It is not required for the first release.

### 2.3 Account and connectivity

MiniMake requires a signed-in MiniMe account and a network connection because the reasoning engine is server-side. Offline mode is not part of v1.

The device is paired with the account through a device credential flow. The server stores the device registry and credential hash, not the user's project content. Devices can be revoked.

### 2.4 Initial commands

The intended command family includes:

- `minimake login`;
- `minimake logout`;
- `minimake init`;
- `minimake doctor`;
- `minimake status`;
- `minimake run`;
- `minimake resume`;
- `minimake stop`;
- `minimake service install`;
- `minimake service uninstall`;
- `minimake vault add|list|remove`;
- headless execution for MiniMate and scripts.

Exact command names are subject to the release package and may change while the protocol stabilizes.

| Command / Surface | Arguments & Flags | Primary Purpose | Work Package |
| :--- | :--- | :--- | :--- |
| `minimake login` / `logout` | `--device-name`, `--all` | OAuth 2.0 RFC 8628 device-code pairing with MiniMe web account; stores token in OS keychain | `S02`, `C02` |
| `minimake init` | `[path]` | Initializes `.minimake/` config, `.minimakeignore`, and `MINIMAKE.md` project instructions | `C01`, `L03` |
| `minimake doctor` | `--json`, `--fix` | 14-point preflight check: OS/WSL2, `/mnt/c` path warning, `git`, `rg`, `bwrap`, auth, and sandbox smoke test | `C04`, `C21` |
| `minimake` (Interactive TUI) | `[-m ask\|edit\|auto]`, `[--resume <id>]` | Full-screen Textual/Rich terminal UI with streaming diff viewer, approval prompt bar, and slash commands | `C01`, `C12` |
| `minimake run` (Headless) | `"<prompt>" --json --max-usd <n>` | Non-interactive coding run for CI pipelines and **MiniMate IPC delegation (`MT-M07`)** | `C03`, `C17` |
| `minimake review` | `[--staged \| --branch <ref>]` | Local pre-commit/PR diff review powered by `reviewer` & `security_scanner` sub-agents | `C20` |
| `minimake handoff` | `<workspace_id>` | Pushes/pulls a compact summary bundle between local CLI and MiniMe Web Build tab | `S11`, `C16` |
| Slash `/mode`, `/diff`, `/rewind`, `/compact`, `/usage` | In-session TUI commands | Switch `ask\|edit\|auto`, inspect diffs, roll back git checkpoints (`C10`), compact context (`L02`), or check shared pool | `C10`, `C12`, `L02` |

---

## 3. Core Coding Workflow

### 3.1 Start a coding run

A user can describe a coding task in natural language. MiniMake sends the task, relevant project context, policy state, and selected profile to the server-side run loop.

Each run carries `profile: "code"`. This keeps coding assumptions explicit and lets MiniMate use the same engine with a different automation profile later.

A run can be:

- interactive from the terminal;
- started from the browser Build tab;
- started headlessly by another local process;
- resumed after a disconnect;
- cancelled by the user;
- stopped by a policy, budget, or sandbox limit.

### 3.2 Ask mode

Ask mode is for analysis without applying project edits. Typical requests include:

- explain a function or architecture;
- find where a behavior is implemented;
- identify likely bugs;
- propose an implementation plan;
- inspect tests and dependencies;
- summarize a repository area;
- compare approaches;
- review a diff;
- explain an error or failing test.

Ask mode can use read-only tools, repository search, code context, and generated artifacts. It should not silently write project files.

### 3.3 Edit mode

Edit mode is for proposing code changes. The expected flow is:

1. describe the requested change;
2. provide or select relevant files, symbols, or context chips;
3. let MiniMake inspect the repository;
4. generate a proposal;
5. review affected files and hunks;
6. keep all, keep selected changes, or reject;
7. write accepted changes;
8. run checks and inspect problems.

The approval boundary is a product feature. An AI response is not the same thing as an accepted file change.

### 3.4 Context selection

The user can give the agent context through:

- the current file;
- selected text;
- a symbol or component;
- a path from the explorer;
- project search results;
- code context chips;
- a task or instruction step from Build;
- a previous proposal or error output;
- repository-wide architecture context when needed.

The context assembler is responsible for trimming and organizing this information. It should preserve the most relevant content first and report when a size cap means only part of a file was kept.

### 3.5 Streaming and progress

The client receives a live run stream rather than waiting for one opaque final response. The stream can contain:

- run started;
- planning or classification;
- tool proposed;
- approval requested;
- tool result;
- model token chunks;
- file proposal updates;
- reviewer output;
- warnings;
- run completion;
- run failure;
- cancellation;
- quota or budget events.

The browser shows live progress through the chat dock and working panel. The terminal client shows a scrollback-friendly stream intended for long tasks.

---

## 4. Files and Project Workspace

### 4.1 Project explorer

The browser editor and local client are intended to provide:

- file and folder listing;
- folder expansion and collapse;
- new file creation;
- new folder creation;
- file rename;
- file move;
- file delete;
- delete-and-recreate support;
- path validation;
- project search;
- quick open;
- recent files;
- multiple editor tabs;
- dirty-state indicators;
- save behavior;
- ZIP download.

The browser's v1 editor is cloud-project focused. The older local-folder mode and terminal panel are intentionally removed from the browser plan as MiniMake takes over local execution. The backend local workspace routes may remain during migration.

### 4.2 Code editor

The editor workbench includes or inherits:

- CodeMirror editing;
- language-aware code editing;
- editor tabs;
- formatting on save where supported;
- selection and context actions;
- problems panel;
- console panel for preview output;
- history panel;
- version comparison;
- conflict comparison;
- preview column;
- device and viewport toolbar;
- HTML and React preview;
- dev-server URL preview;
- wireframe preview;
- resizable bottom panels.

Python files are not intended to run directly inside the browser preview. Python execution belongs in the controlled MiniMake environment. Pyodide remains for chat artifacts where a small browser-side Python result is explicitly supported.

### 4.3 Local project access

MiniMake's local client can access the project through a guarded local tool layer. The path guard prevents access outside approved roots or protected paths. A local operation can be:

- read-only;
- a proposed write;
- an approved write;
- denied by policy;
- blocked because the path is protected.

The product should not treat a natural-language request as permission to read every file on the machine.

### 4.4 History and recovery

MiniMake stores local history and checkpoints so a user can recover from an unwanted change. Intended operations include:

- create a checkpoint before a risky run;
- inspect file versions;
- compare current and previous versions;
- restore an earlier version;
- rewind a run;
- resume from a checkpoint;
- resolve a conflict between local and server versions;
- retain a tombstone when a file is moved or deleted.

The device log is the source of truth. A server-side in-flight buffer expiring should not destroy the local run record; the client can resend the necessary state during `run.resume`.

---

## 5. Agent Loop and Tools

### 5.1 Server-side reasoning loop

The server runs the coding profile through a shared agent loop. The loop can:

- assemble the request context;
- choose a model adapter;
- ask the model for a tool call or response;
- validate a tool request;
- request user approval where required;
- dispatch the tool;
- return the tool result to the model;
- enforce budgets;
- retry transient provider failures;
- compact context when it becomes too large;
- call reviewers or security roles;
- stop on policy violations;
- produce a final answer and event record.

The coding profile is deliberately separate from MiniMate's automation profile even though both use the same engine.

### 5.2 Built-in coding tools

The intended coding tool catalog includes:

- list files and directories;
- read files;
- search with `ripgrep`;
- inspect symbols and code elements;
- compare versions;
- propose edits;
- apply approved edits;
- create, move, rename, and delete files;
- run approved checks;
- inspect test and lint output;
- read preview or console output;
- create checkpoints;
- restore or rewind;
- ask the user a clarification question;
- delegate a bounded subtask;
- use configured MCP tools.

Tool schemas are explicit. Unknown tools and malformed arguments fail closed.

| Tool Name | Category | Default Approval (`Ask` / `Edit` / `Auto`) | Sandbox & Guardrails | Work Package |
| :--- | :--- | :--- | :--- | :--- |
| `read_file`, `list_dir`, `glob_search`, `grep_search` | Read & Search | Allowed / Allowed / Allowed | Path-jailed to repo root; blocks `.env*`, `~/.ssh`, and `.minimakeignore` | `C05` |
| `symbol_search`, `repo_map` | Code Index | Allowed / Allowed / Allowed | Queries local SQLite `index.db` (`FTS5` + tree-sitter symbol table) | `C06`, `C09` |
| `git_status_diff`, `diagnostics` | Inspection | Allowed / Allowed / Allowed | Read-only `git status`/`diff` and linter/LSP problem collection | `C05`, `C08` |
| `edit_file`, `write_file`, `apply_patch` | File Mutation | Denied / **Prompt Diff** / Auto in repo | Atomic temp-write + rename; creates git shadow checkpoint (`C10`) before mutation | `C07`, `C10` |
| `delete_file` | File Deletion | Denied / **Prompt Always** / **Prompt Always** | Never auto-approved; recoverable via git checkpoint rewind | `C07` |
| `run_command`, `run_tests` | Shell Execution | Denied / **Prompt Command** / Allowlisted tests | Executed inside `bubblewrap` (`X01`); strips secrets (`X02`); blocks dangerous commands | `C08`, `X01` |
| `ask_user`, `todo_write`, `web_fetch_docs` | Control & Docs | Allowed / Allowed / Allowed | Structured clarification prompt (`L01`), task list tracker, and domain-gated doc fetch | `L01`, `C15` |

### 5.3 Subagents and delegation

The agent can use specialized roles for:

- repository exploration;
- implementation planning;
- code writing;
- code review;
- test writing;
- security review;
- performance review;
- documentation;
- dependency mapping;
- architecture and schema analysis;
- output organization.

Subagents have their own budgets and context boundaries. The main run remains responsible for combining their outputs and presenting a coherent result.

### 5.4 Compaction and long runs

Long coding tasks need more context than one model request can hold. MiniMake is intended to support:

- rolling summaries;
- preservation of task constraints;
- checkpointed run state;
- selective replay of relevant tool outputs;
- compaction before the context limit;
- resumable runs after a connection interruption.

Compaction must not silently discard a safety instruction, approval decision, protected-path rule, or user constraint.

---

## 6. Safety and Trust

### 6.1 Policy engine

Every tool has a risk level and policy requirements. The policy engine can consider:

- read versus write;
- inside-project versus outside-project path;
- shell or process execution;
- network access;
- irreversible effects;
- requested user mode;
- protected paths;
- unattended versus interactive execution;
- connector or MCP trust level;
- per-run and account budgets.

Security decisions fail closed. Metering and telemetry helpers fail open where the plan explicitly allows it, so an analytics outage does not break an otherwise safe request.

### 6.2 Modes and approvals

The product is designed around modes that control how much autonomy is allowed. A mode can require:

- no approval for read-only project inspection;
- confirmation before file writes;
- confirmation before shell or network activity;
- confirmation before touching paths outside the project;
- confirmation before irreversible operations;
- a complete deny for a capability.

Approval records are stored locally and included in the audit trail. A later step cannot pretend that an approval happened if it did not.

### 6.3 Sandbox

Untrusted or high-risk work runs in a sandbox. The first Linux implementation uses `bubblewrap` and a controlled network path. The sandbox is intended to provide:

- restricted filesystem visibility;
- read-only roots where possible;
- approved writable project paths;
- sanitized environment variables;
- no accidental secret inheritance;
- process and resource limits;
- network allowlists or no network;
- explicit command policy;
- a clear timeout and cancellation path.

Sandbox configuration is part of the trust boundary, not merely an optimization.

### 6.4 Secrets

Secrets are stored in a local vault and should never be placed in:

- model prompts unless a connector explicitly requires a safe token reference;
- tool results;
- logs;
- generated diffs;
- the browser event stream;
- the sandbox environment without sanitization.

The planned vault supports an OS keyring where available, a passphrase-derived key, or a protected key file as a less secure fallback. `doctor` reports the fallback level without printing the secret.

### 6.5 Injection and output protection

MiniMake includes or inherits:

- prompt and instruction injection defenses;
- secret and PII redaction;
- taint tracking for web or untrusted content;
- output guards;
- static scanning;
- Gitleaks and Semgrep in CI;
- security review roles;
- code proposal review;
- no-content canary tests proving prompts and source code are not written to persistent server storage.

Content from a web page, issue, file, or external connector is data by default. It does not become an instruction merely because it contains imperative language.

### 6.6 Red-team and evaluation coverage

The quality plan includes evaluations for:

- path traversal;
- protected-path writes;
- shell escape;
- secret enumeration;
- prompt injection;
- unsafe network access;
- tool budget exhaustion;
- malformed tool arguments;
- score or result smuggling in experimental flows;
- cancellation and resume correctness;
- content leakage to Postgres or logs.

These are release gates, not optional documentation exercises.

---

## 7. Hooks, Skills, Instructions, and Memory

### 7.1 Hooks

Hooks let a project or user run controlled actions around a coding event, such as before a run, after a proposal, after an accepted change, or after a test. Hooks are subject to the same policy and sandbox rules as other tools.

A hook should declare what it does, what paths it needs, and whether it can make an external request. Hidden side effects are not an intended feature.

### 7.2 Skills

Skills are reusable packages of instructions, tools, files, and policy metadata. A skill can teach MiniMake a project-specific workflow such as:

- how to run the test suite;
- how to follow a repository's code style;
- how to deploy a service;
- how to review a database migration;
- how to generate a particular artifact.

Skill loading is manifest-driven. Skills can be reviewed and scanned before use. Future skill drafts are intended to enter a review queue rather than becoming active immediately.

### 7.3 Instructions

Project instructions define durable local conventions, such as:

- required test commands;
- files that must not be edited;
- formatting rules;
- architectural boundaries;
- commit or release rules;
- preferred libraries;
- security restrictions.

The run manager must preserve these instructions through context assembly and compaction.

### 7.4 Memory

MiniMake can retain local memory about a project, including:

- useful commands;
- architecture facts;
- recurring failure modes;
- accepted conventions;
- previous decisions;
- user preferences;
- task summaries.

Memory is stored on the device and can be searched locally. A memory item should be inspectable and removable. Untrusted content should not be allowed to poison durable instructions without review.

---

## 8. Browser Integration

### 8.1 Build tab

The MiniMe Build tab is the browser companion for MiniMake. It provides:

- task and feature board;
- instruction checklist;
- code editor workbench;
- wireframe preview;
- chat dock;
- code proposals;
- review and keep/reject actions;
- Problems and Console panels;
- history and conflict comparisons;
- preview and dev-server URL support;
- deployment proposal cards.

The browser is a control and review surface. The local MiniMake client becomes the trusted place for local files, local policy, sandboxing, and terminal-oriented workflows.

### 8.2 Device page and pairing

The web application is intended to show:

- paired devices;
- online or offline status;
- last-seen time;
- revoke-device actions;
- the current MiniMake client version;
- pairing instructions;
- local node health where available.

### 8.3 Remote live view

The browser can receive a live relay of an active local run. The relay is not a historical content store by default. The browser can inspect current progress while the device remains the source of truth for the run record.

### 8.4 Shared usage

The web app, MiniMake, and later MiniMate use one account, one plan, and one credit pool. Usage is shown by surface for transparency, but enforcement is server-side at every model call.

---

## 9. MCP and External Tools

### 9.1 Local MCP client

MiniMake can host local MCP connections. The client is intended to:

- configure a server command;
- start and stop the server;
- discover tools;
- search the tool catalog;
- assign trust levels;
- validate schemas;
- enforce network and path policy;
- require confirmation for risky calls;
- redact secrets from results;
- record tool events locally.

MCP is an extension point, not an automatic trust upgrade. A connected server can be blocked, read-only, or approval-required.

### 9.2 External network access

Network access is controlled by policy and sandbox. A tool or skill should declare allowed domains. Web content is tainted and must not silently become a trusted instruction or be allowed to write project files without the appropriate gate.

---

## 10. Usage, Budgets, and Economics

### 10.1 One shared pool

MiniMake does not have a separate hidden allowance from the web application. The account ledger covers:

- web application work;
- MiniMake runs;
- MiniMate runs;
- system operations where applicable.

Usage is measured in cost-weighted credits. The user can see usage by surface and an approximate remaining-session view.

### 10.2 Per-run limits

Every run can have:

- a maximum credit budget;
- a maximum token budget;
- a maximum tool-call count;
- a maximum wall-clock duration;
- a maximum retry count;
- a maximum child-agent budget;
- a sandbox resource limit.

The server performs a pre-flight availability check and commits usage after the model call. The client cannot be trusted to enforce the account cap by itself.

### 10.3 Failure and interruption

When a provider, connection, or worker fails:

- the local event log remains available;
- the active run can be resumed when enough state is present;
- transient provider failures may retry with backoff;
- an exhausted account pool stops the run cleanly;
- a stopped or cancelled run does not continue invisibly;
- the user receives a clear reason and next action.

---

## 11. Headless and MiniMate Delegation

MiniMake is intended to work without the interactive terminal UI. Headless mode lets MiniMate or another local orchestrator:

- submit a coding task;
- pass a project and profile;
- receive streamed events;
- answer approval requests through the local policy path;
- resume or cancel a run;
- collect a structured result;
- retain the event log on the device.

MiniMate should hand coding work to the installed MiniMake CLI through local IPC. This preserves MiniMake's sandbox, policy, and file safety instead of duplicating a second code execution engine.

---

## 12. Operations and Diagnostics

`minimake doctor` is intended to diagnose:

- supported operating system;
- WSL2 state;
- project filesystem location;
- Python version;
- package installation;
- `uv`, `pipx`, `git`, and `ripgrep`;
- `bubblewrap` availability;
- account and device pairing;
- credential health;
- network reachability;
- local database permissions;
- sandbox smoke test;
- provider configuration;
- stale or incompatible state migrations.

The backend and web application expose operator diagnostics for:

- database latency;
- database pool state;
- agent pool state;
- tool budgets;
- usage and quota;
- cache behavior;
- conversation threads;
- audit and ledger events.

Sentry can provide error and performance tracing when configured.

---

## 13. Release Milestones

### Phase 0: browser and foundation cleanup

The browser editor is made coherent and safe: remove browser Run, Terminal, and Local folder mode; retain editor, explorer, AI proposals, review, history, Problems, Console, previews, planning, and ZIP download; harden database tests, Pyodide chat artifacts, CORS, validation errors, and unsaved-edit protection.

### Phase 1: walking skeleton

The first complete path is:

`minimake login` -> connect device -> send hello -> receive streamed model reply -> write a content-free usage ledger row -> show device and usage in the web app.

### Phase 2: internal coding agent

The agent edits real files with approvals, checkpoints, rewind, TUI, headless operation, and the first real coding task milestone.

### Phase 3: safe daily driver

Add sandboxing, hooks, skills, secrets, taint tracking, context compaction, subagents, ask-user and tasks tools, evaluations, red-team tests, and content-leakage canaries.

### Phase 4: invite-only beta

Add handoff, remote live view, review commands, plan chains, invite controls, usage and device surfaces, and production hardening.

### Phase 5: platform expansion

Potential additions include ACP, worktrees, request classification, LSP and repository maps, local MCP, process separation, and an external security audit.

### Phase 6: release

Packaging, documentation, support, legal review, and release gates lead to general availability.

| Phase & Milestone | Waves | Work Packages | Effort Points | Key Deliverable & Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0 · Browser Cleanup (`M0`)** | Waves 0–2 | `B00–B12` (13 WPs) | 20 pts | Self-host Pyodide (`B02`), remove browser Python Run/Terminal/Local-folder (`B03–B06`), fix save/move & CORS (`B07–B12`) |
| **Phase 1 · Walking Skeleton (`M0`)** | Waves 1–3 | `P00`, `S01–S06`, `C01–C04`, `X01–X02`, `I01` (14 WPs) | 34 pts | Extract `minicore/`, shared `usage_ledger` (`S01`), device login, hello turn over SSE, `bwrap` wrapper (`I01` pass) |
| **Phase 2 · Internal Coding Agent (`M1`)** | Waves 4–6 | `C05–C10`, `C12`, `S07–S10`, `I02` (12 WPs) | 30 pts | Local read/write/shell tools, SQLite FTS5 index, git checkpoints & rewind, TUI diff approval (`I02` self-hosting dogfood pass) |
| **Phase 3 · Safe Daily Driver** | Waves 7–9 | `C11`, `C13–C15`, `L01–L04`, `Q01–Q03`, `Q06`, `I03` (13 WPs) | 36 pts | Hooks, skills, `MINIMAKE.md`, context compaction (`L02`), sub-agents (`L04`), red-team & canary suites (`I03` pass) |
| **Phase 4 · Invite-Only Beta (`M2`)** | Waves 10–12 | `S11–S12`, `C16–C17`, `C20–C21`, `X03–X04`, `L05–L06`, `Q04`, `I04` (12 WPs) | 37 pts | Web Build-tab handoff (`S11`/`C16`), headless mode for MiniMate (`C17`), taint tracking (`X03`), plan chains (`L06`), beta launch (`I04`) |
| **Phases 5–6 · Scale & Release (`M3 / GA`)** | Post-M2 | Editor extensions, ACP, worktrees, GA packaging | Gated on M2 | VS Code / JetBrains / Neovim adapters, macOS Seatbelt, external security audit, public GA |

---

## 14. What MiniMake Does Not Promise

MiniMake does not promise:

- that source code never leaves the device;
- unrestricted shell or filesystem access;
- automatic application of every AI suggestion;
- safe execution of arbitrary code without sandbox and policy checks;
- native Windows support in v1;
- offline reasoning;
- browser-based execution of every language;
- that a connected MCP server is trusted by default;
- that a roadmap item is already released;
- that a failed telemetry service will explain every event without gaps.

The honest product promise is local-first storage, controlled remote reasoning, explicit approvals, bounded execution, and recoverable work.

---

## 15. Maintenance Checklist

For every MiniMake release, verify:

- [ ] Login, device pairing, revocation, and reconnect work.
- [ ] `doctor` detects unsupported platforms and missing sandbox dependencies.
- [ ] Ask mode cannot silently write files.
- [ ] Edit proposals show affected files and require the expected approval.
- [ ] Checkpoints, history, rewind, restore, and conflict comparison work.
- [ ] Protected paths and traversal attempts fail closed.
- [ ] Secrets do not reach prompts, logs, tool results, or sandbox environments.
- [ ] Sandbox network and filesystem boundaries are tested on real supported hosts.
- [ ] Cancelled and timed-out runs stop their child work.
- [ ] Disconnect and resume preserve the local event log.
- [ ] Context compaction preserves instructions and approvals.
- [ ] MCP tools declare trust, schema, domains, and approval behavior.
- [ ] Usage charges the shared account pool and does not rely on client-side counting.
- [ ] Browser live view does not become an unintended history store.
- [ ] MiniMate can invoke headless MiniMake without bypassing policy.
- [ ] Content-free server persistence canary tests pass.
- [ ] Backend, frontend, CLI, sandbox, and red-team suites are green.
- [ ] Planned or gated features remain labeled accurately.

---

## 16. Source Map

The main planning sources for this manual are:

- `data/docs/minimake_build_plan.md`;
- MiniMe Build tab and workbench implementation;
- backend local workspace, code proposal, task, and deployment routes;
- the protocol, server, client, loop, policy, sandbox, and quality work packages described by the build plan.

This document is the user-facing layer. The build plan remains authoritative for patch order, exact module ownership, test commands, milestone gates, and implementation status.
