# M2C L26 Feature Guide

*Minime to Code · Level 26 (L26). Levels work like release versions: the next release will be L27.*

**Purpose:** the user manual and feature register for M2C, the local-first coding agent built on the MiniMe platform.

**Status:** M2C is specified and being built in phases. This guide records the intended product behavior from the current build plan. It labels planned behavior explicitly because the plan contains work packages, not proof that every package has shipped.

- **Available or inherited:** behavior already present in the MiniMe web application or explicitly carried forward into M2C.
- **Planned:** behavior described by the M2C build plan but not yet verified as released.
- **Gated:** behavior that requires a milestone, safety review, legal decision, or external service configuration first.

> **Revision 1.2 (2026-11-14).** This revision records what exists in the code today and corrects places where this guide had drifted from the build plan. **Built (from a read of the code; tests were not run):** login and logout, device link, the chat terminal UI, headless `-p`, the local policy engine with the modes `plan`, `ask` and `accept-edits`, checkpoints and `/rewind`, secrets redaction, the folder-trust prompt (`m2c trust`), the bubblewrap sandbox with its network proxy, and the server loop behind `/v1/code/*`. **Not built yet:** hooks, skills, subagents, model-written compaction, web tools, handoff, MCP, worktrees and packaging. The per-WP table is `m2c_build_plan.md` §0.6. **Corrections:** the commands and tools in §2.4 and §5.2 now match the code; the work-package IDs and effort counts in §13 now match the plan's index; O4 and O5 below are fixed. **New:** §17 (what other coding agents do and what M2C takes from them) and §18 (ideas not yet scheduled). The plan gained six work packages: C25, Q07, Q08, Q09, C28 and C27.

### Architectural Synchronization (Overrides O1–O8 from `m2c_build_plan.md`)

Where the earlier standalone design note (`doc-m2c-product.html`) and this guide or `m2c_build_plan.md` differ, **these 8 synchronized rules govern**:

| Override ID | Architectural Rule | How It Connects Across the Book |
| :--- | :--- | :--- |
| **O1 · Local-First Data Placement** | Repo files, SQLite `index.db`, git checkpoints, and shell/test runs stay on the user's device; server keeps only `usage_ledger` + 2h Redis buffer | Keeps server RAM/CPU near zero (`minime_server_management_guide.md` §9) |
| **O2 · One Account, One Cap, One Ledger** | Shares the user's MiniMe tier (`Free / Basic $9 / Moderate $29 / Ultimate $79`) via `usage_ledger` (`surface='m2c'`, WP `S01`) | Built once with MiniMe `Tech-A/B` (`MiniMe_Financial_Strategy_Rulebook.md` Rule 4) |
| **O3 · Linux & WSL2 First** | v1 targets native Linux and Windows via WSL2 (`bubblewrap`); native Windows & macOS deferred to post-GA | Enforced by `m2c doctor` (`C04`, `C21`) |
| **O4 · Python CLI + `minicore/`** | Distributed via `uv tool install m2c` / `pipx` (packaging is Phase 6). Runs today as a self-contained package; the shared `minicore/` library is **not extracted yet**. Menux's `MT-K01` extracts it from M2C once M2C reaches M2 | `P00` built the protocol contract in `protocol/v1/`; the library comes later |
| **O5 · Backend Route Namespace** | Server package lives at `backend/codeagent/`, served under `/v1/code/*` (as built; an earlier draft said `/api/codeagent/*`) | Avoids collision with existing `backend/agents/coder.py` |
| **O6 · Phase 0 Browser Slimming** | Removes browser Python `Run`, `Terminal`, and `Local-folder mode` (`MK_B02–B06`); replaces with CLI handoff | Synchronized with `minime_feature_guide.md` §9.3 & §17.2 |
| **O7 · Account Required (No Offline v1)** | Reasoning loop runs on MiniMe server using the 8-provider router; requires sign-in (`m2c login`) | Preserves Rulebook model routing & prompt caching |
| **O8 · Profile Field (`profile="code"`)** | Every run carries `profile: "code"` so `menux` can reuse the same protocol with `profile: "mate"` | Shared contract in `minicore/protocol.py` (`P00`) |

---

## 1. What M2C Is

M2C is a coding-focused agent that works with a user's project on the user's device while using the MiniMe server and model providers for reasoning. It is intended to combine:

- a terminal-first coding workflow;
- a browser editor and project explorer;
- AI chat with Ask and Edit modes;
- proposed changes instead of silent file mutation;
- checkpoints, rewind, history, and conflict review;
- a local policy engine and sandbox;
- skills, hooks, memory, secrets handling, and MCP tools;
- headless use for automation and Menux delegation;
- one shared account and usage pool across MiniMe, M2C, and Menux.

The product's trust model is local-first, not local-only. Project files, history, settings, approvals, checkpoints, and local logs are intended to remain on the device. Relevant code and prompt context are sent to the MiniMe server and model providers during a run. The service keeps usage numbers and only the short-lived in-flight content needed to complete an active run; it does not promise that code never leaves the device.

M2C is designed for Linux and WSL2 in version 1. Native Windows, WSL1, and macOS are not part of the initial supported platform promise.

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

The intended distribution is a Python package installed with `uv tool install m2c` or `pipx`, plus an installer script that:

- installs or checks `uv`;
- checks for `ripgrep`;
- checks for `git`;
- checks for `bubblewrap`;
- installs the command-line client;
- runs `m2c doctor`;
- explains missing dependencies and supported alternatives.

A bundled native binary may be added later. It is not required for the first release.

### 2.3 Account and connectivity

M2C requires a signed-in MiniMe account and a network connection because the reasoning engine is server-side. Offline mode is not part of v1.

The device is paired with the account through a device credential flow. The server stores the device registry and credential hash, not the user's project content. Devices can be revoked.

### 2.4 Commands

**Commands and flags that exist today** (from `m2c --help`; the list is checked by the Q08 docs test once that exists):

| Command or flag | Purpose |
| :--- | :--- |
| `m2c` | Opens the chat terminal UI in the current folder (`--plain` for a line-by-line fallback) |
| `m2c login` / `m2c logout` | Device-code pairing with the MiniMe account (`--device-name`); the credential is stored locally and the server keeps only its hash |
| `m2c doctor` | Preflight checks (`--project PATH` to check a folder) |
| `m2c trust` | Shows and manages folder-trust decisions (`--list`, `--forget PATH`); a project's own settings, hooks and skills are used only after the folder is trusted |
| `m2c -p "task"` (`--print`) | Headless run. `--output-format text\|json` (`stream-json` is planned, C28), `--mode plan\|ask\|accept-edits`, `--allow RULE`, `--deny RULE`, `--sandbox auto\|required\|off`, `--cwd PATH` |
| `--version` | Prints the version |
| In the chat | `/help`, `/rewind`, `/exit` |

**Environment variables:** `M2C_HOME` (where local state lives), `M2C_LOG_LEVEL`, `M2C_SERVER_URL`.

**Exit codes of `m2c -p`:** 0 success · 1 general failure · 2 usage error · 3 policy denial (a tool would ask or was denied) · 4 quota exhausted · 5 not logged in or the device was revoked · 130 ended by Ctrl-C · 143 ended by SIGTERM.

**Planned commands**, with the work package that owns each. Names may change before release.

| Planned | Work package | Note |
| :--- | :--- | :--- |
| `m2c init` and an `M2C.md` project file | `C12` built the instruction loading; the `init` skill comes with `C14` | |
| `/compact`, `/diff`, `/usage`, `/mode`, `/why` | `L03`, `C09`, `S10`, `C06`, `C25` | `/why` shows which rule or mode decided the last call |
| `m2c -p ... --output-format stream-json` | `C28` | One JSON event per line; the interface Menux uses for delegation |
| `m2c review` | `C20` | Diff review with reviewer and security roles |
| `m2c handoff` | `S11`, `C16` | Summary bundle between the CLI and the web Build tab |
| `--worktree`, `m2c service ...`, `m2c vault ...`, `m2c status`, `m2c resume`, `m2c stop` | **no work package yet** | Earlier drafts of this guide listed them. Either add a WP (see §18) or drop them |
| Managed settings and presets | `C27` | For companies; Phase 5 |

---

## 3. Core Coding Workflow

### 3.1 Start a coding run

A user can describe a coding task in natural language. M2C sends the task, relevant project context, policy state, and selected profile to the server-side run loop.

Each run carries `profile: "code"`. This keeps coding assumptions explicit and lets Menux use the same engine with a different automation profile later.

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
3. let M2C inspect the repository;
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

The browser's v1 editor is cloud-project focused. The older local-folder mode and terminal panel are intentionally removed from the browser plan as M2C takes over local execution. The backend local workspace routes may remain during migration.

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

Python files are not intended to run directly inside the browser preview. Python execution belongs in the controlled M2C environment. Pyodide remains for chat artifacts where a small browser-side Python result is explicitly supported.

### 4.3 Local project access

M2C's local client can access the project through a guarded local tool layer. The path guard prevents access outside approved roots or protected paths. A local operation can be:

- read-only;
- a proposed write;
- an approved write;
- denied by policy;
- blocked because the path is protected.

The product should not treat a natural-language request as permission to read every file on the machine.

### 4.4 History and recovery

M2C stores local history and checkpoints so a user can recover from an unwanted change. Intended operations include:

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

The coding profile is deliberately separate from Menux's automation profile even though both use the same engine.

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

**The tool catalog in the code today** is the eleven tools of `protocol/v1/tools/*.json`. The list above is the long-term intent; this table is what exists. A tool that is not in the catalog (an MCP tool, a later tool) is denied by the policy engine until a WP adds it.

| Tool | Class | Risk | Default decision (`plan` / `ask` / `accept-edits`) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `read_file`, `list_dir`, `glob`, `grep` | Read | R0 | Allow / Allow / Allow | Path rules and `.m2cignore` still apply; protected paths such as `.env*` fall back to ask |
| `edit_file`, `write_file` | Edit | R1 | Deny / Ask / Allow inside the project | A checkpoint is taken before a change (`C10`); protected paths always ask |
| `delete_path` | Delete | R1, up to R4 | Deny / Ask / Ask | Never auto-allowed; recoverable through `/rewind` |
| `bash` | Shell | R2 | Deny / Ask / Ask | Runs inside the bubblewrap sandbox; no mode default ever allows it. Reaching the network or leaving the project raises the risk to R3 |
| `plan_exit` | Plan | R0 | Ask | The only way out of plan mode |
| `ask_user`, `tasks` | Interact | R0 | Allow in every mode | They only show something to the person (`ask_user` is the prompt); a deny rule still wins |

Planned additions: `web_fetch` and `web_search` (`C17`, tainted results), `apply_patch` (Phase 5), `symbol_search`/`repo_map` (`L08`), and MCP tools (`C23`). Earlier drafts of this guide named `run_command`, `run_tests`, `git_status_diff`, `diagnostics`, `symbol_search`, `todo_write` and `web_fetch_docs`; those names do not exist in the code.

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

Long coding tasks need more context than one model request can hold. M2C is intended to support:

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

**Modes in the current build:** `plan` (reads only; every change is denied and `plan_exit` asks to leave), `ask` (the default; edits, deletes and shell ask) and `accept-edits` (edits inside the project to non-protected paths are allowed; deletes and shell still ask). The "Ask mode" and "Edit mode" of §3.2 and §3.3 describe the workflow, not the setting names. `auto` (L07) is planned and not available. **Rules:** `tool(pattern)` allow and deny rules; deny wins. **"Always allow" (D16, `C25`):** the `a` key in the prompt saves only the exact call, and only if that call would be allowed when checked again against the new rule set, so a compound command with one denied part is never always-allowed. **A sandbox is not an approval (D17):** a command that runs in the sandbox still follows the normal flow; skipping the prompt for sandboxed commands is a later opt-in setting that is off by default.

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

M2C includes or inherits:

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

**Boundary regression corpus (`Q07`, planned).** Bugs in permission matching and sandboxing repeat across coding agents: compound commands, wrapper programs, relative deny patterns, symlinks, settings files that the agent can edit, control characters in output. `Q07` keeps one table of such cases with the decision M2C must give each, and every future policy or sandbox bug adds a row as part of its fix. `Q09` does the same for crashes and resume, and `Q08` fails the build when the docs and the code disagree.

### 6.7 Prior art and reused components

Parts of the safety layer are adapted from MiniLocker, an earlier MiniMe-family project (a hackathon entry) that tested agent sandboxing, injection handling and tamper-evident logging. M2C reuses specific modules (tolerant tool-call parsing, the untrusted-content fence, an optional hash-chained log, and attack scenarios) and rewrites others. M2C does not run on MiniLocker's Docker sandbox: its boundary is the local `bubblewrap` sandbox and the device policy engine. Reused code counts only once it passes the M2C work package's own tests. The module-by-module map is in `m2c_build_plan.md` §11.6.

**Outside references (D13).** M2C learns from public documentation, public changelogs, observable behavior and code under a licence that has been read and recorded. It does not use leaked, unlicensed or source-unavailable code, including copies re-uploaded under a permissive licence. See §17.

---

## 7. Hooks, Skills, Instructions, and Memory

### 7.1 Hooks

Hooks let a project or user run controlled actions around a coding event, such as before a run, after a proposal, after an accepted change, or after a test. Hooks are subject to the same policy and sandbox rules as other tools.

A hook should declare what it does, what paths it needs, and whether it can make an external request. Hidden side effects are not an intended feature.

**Contract (D15, `C13`, planned).** A command hook receives the event as JSON on standard input. Exit code 0 means "no objection" and the normal policy still decides; exit code 2 blocks the action and sends the hook's message to the model; any other code only warns. **A hook can tighten (ask, deny) and never loosen:** its "allow" does not override deny rules, protected paths, the taint rules, the sandbox or the folder-trust rule. Hooks have a timeout and a trimmed environment, their output is redacted like a tool result, and project hooks run only after the folder is trusted. The model cannot edit hook files: the sandbox refuses writes to them (a `Q07` case).

### 7.2 Skills

Skills are reusable packages of instructions, tools, files, and policy metadata. A skill can teach M2C a project-specific workflow such as:

- how to run the test suite;
- how to follow a repository's code style;
- how to deploy a service;
- how to review a database migration;
- how to generate a particular artifact.

Skill loading is manifest-driven. Skills can be reviewed and scanned before use. Future skill drafts are intended to enter a review queue rather than becoming active immediately.

A skill that declares tools or hooks does not run unattended (headless, or called by Menux) until the owner has an explicit allow rule for it, and a skill can never grant itself more than policy allows. Skills are local files; the server-side skill store used by the web agents (`backend/eo/skill_library.py`) is a different design and is not used by M2C.

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

M2C can retain local memory about a project, including:

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

The MiniMe Build tab is the browser companion for M2C. It provides:

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

The browser is a control and review surface. The local M2C client becomes the trusted place for local files, local policy, sandboxing, and terminal-oriented workflows.

### 8.2 Device page and pairing

The web application is intended to show:

- paired devices;
- online or offline status;
- last-seen time;
- revoke-device actions;
- the current M2C client version;
- pairing instructions;
- local node health where available.

### 8.3 Remote live view

The browser can receive a live relay of an active local run. The relay is not a historical content store by default. The browser can inspect current progress while the device remains the source of truth for the run record.

### 8.4 Shared usage

The web app, M2C, and later Menux use one account, one plan, and one credit pool. Usage is shown by surface for transparency, but enforcement is server-side at every model call.

---

## 9. MCP and External Tools

### 9.1 Local MCP client

M2C can host local MCP connections. The client is intended to:

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

**Where it runs (D18, `C23`).** MCP servers run on the device, never on the MiniMe server, so the data they touch stays local. The server-side MCP client in the backend (`backend/eo/mcp_client.py`) serves the web agents and is only a protocol reference. A server's tool names and descriptions are untrusted data and taint the session; rules match a tool's exact name; servers start inside the sandbox unless the owner marks one as trusted.

### 9.2 External network access

Network access is controlled by policy and sandbox. A tool or skill should declare allowed domains. Web content is tainted and must not silently become a trusted instruction or be allowed to write project files without the appropriate gate.

---

## 10. Usage, Budgets, and Economics

### 10.1 One shared pool

M2C does not have a separate hidden allowance from the web application. The account ledger covers:

- web application work;
- M2C runs;
- Menux runs;
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

## 11. Headless and Menux Delegation

M2C is intended to work without the interactive terminal UI. Headless mode lets Menux or another local orchestrator:

- submit a coding task;
- pass a project and profile;
- receive streamed events;
- answer approval requests through the local policy path;
- resume or cancel a run;
- collect a structured result;
- retain the event log on the device.

Menux should hand coding work to the installed M2C CLI through local IPC. This preserves M2C's sandbox, policy, and file safety instead of duplicating a second code execution engine.

**The interface today** is `m2c -p "task" --output-format json` (or `text`), with `--mode`, `--allow`, `--deny`, `--sandbox` and `--cwd`, and the exit codes listed in §2.4. In headless mode a call that would ask is not answered by a prompt: it ends the run with exit code 3, so an unattended run cannot widen its own permissions. **Planned (`C28`):** `--output-format stream-json`, one event per line plus a final result line, which is what Menux's delegation test (`MT-A07`) needs. An earlier name, `m2c run --json`, never existed.

---

## 12. Operations and Diagnostics

`m2c doctor` is intended to diagnose:

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

`m2c login` -> connect device -> send hello -> receive streamed model reply -> write a content-free usage ledger row -> show device and usage in the web app.

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

**Counts (recounted from the plan's index in revision 1.2).** Sizes: S=1, M=2, L=4, XL=8 points. Phases 0–4 are **69 work packages and about 163 points**; the earlier headline of 157 points (64 packages) did not include the six read-only audits (AUD1–6) and does not include the five packages this revision adds. The four packages the build added on its own (C24, C26, S14, S15) are done and not counted.

| Phase & Milestone | Waves | Work Packages | Effort Points | Key Deliverable & Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0 · Browser Cleanup (`M0`)** | 0–3 | `B00–B12` (13 WPs, plus six audits `AUD1–6`) | 17 pts | Self-host Pyodide (`B02`), remove browser Python Run, Terminal and Local-folder (`B03–B06`), fix save, move and CORS (`B07–B12`) |
| **Phase 1 · Walking Skeleton (`M0`)** | 1–4 | `P00`, `S01–S06`, `C01–C04`, `X01–X02`, `I01` (14 WPs) | 37 pts | Protocol contract (`P00`), shared `usage_ledger` (`S01`), device login, a "hello" turn over the socket, the first end-to-end pass (`I01`). **Built** |
| **Phase 2 · Internal Coding Agent (`M1` prerequisite)** | 5–8 | `S07–S10`, `C05–C10`, `C12`, `I02` (12 WPs) | 35 pts | Local read, write and shell tools, checkpoints and rewind, the terminal UI, headless mode, and the dogfood pass (`I02`). **Built**; `I02` itself not confirmed |
| **Phase 3 · Safe Daily Driver (`M1`)** | 9–10 | `C11`, `C13–C17`, `L01–L04`, `S11`, `Q01–Q03`, `Q06`, `I03`, plus new `C25`, `Q07`, `Q08`, `Q09` (20 WPs) | 52 pts (was 47) | Sandbox, hooks, skills, secrets, taint, compaction, subagents, red-team and canary suites (`I03`). **In progress:** `C11`, `C15` built, `L01` partly |
| **Phase 4 · Invite-Only Beta (`M2`)** | 11–12 | `S12`, `C20–C21`, `X03–X04`, `L05–L06`, `Q04`, `I04`, plus new `C28` (10 WPs) | 22 pts (was 21) | Review commands, remote live view, plan chains, invites, streaming headless output for Menux (`C28`), beta launch (`I04`) |
| **Phase 5 · Platform Expansion (`M3`)** | 13+ | `C18`, `C19`, `L07`, `L08`, `C23`, `S13`, plus new `C27` (7 WPs) | 26 pts (was 24) | ACP, worktrees, auto mode, repository maps, local MCP, managed settings and presets, external security audit |
| **Phase 6 · Release (`GA`)** | 13+ | `C22`, `X05`, `X06` (3 WPs) | 6 pts | Packaging, documentation, support, legal review, general availability |

The web Build-tab handoff (`S11`, `C16`) belongs to Phase 3 in the plan's index (it is a prerequisite for the Phase 4 beta). Editor adapters (VS Code, JetBrains, Neovim) and a macOS sandbox are not in any work package yet; see §18.

---

## 14. What M2C Does Not Promise

M2C does not promise:

- that source code never leaves the device;
- unrestricted shell or filesystem access;
- automatic application of every AI suggestion;
- safe execution of arbitrary code without sandbox and policy checks;
- native Windows support in v1;
- offline reasoning;
- browser-based execution of every language;
- that a connected MCP server is trusted by default;
- that a roadmap item is already released;
- that a hook, skill or MCP server can loosen a permission (they can only tighten, D15);
- that a sandbox replaces approval (D17);
- that every command or tool named in an older draft of this guide exists (§2.4 and §5.2 list what does);
- that a failed telemetry service will explain every event without gaps.

The honest product promise is local-first storage, controlled remote reasoning, explicit approvals, bounded execution, and recoverable work.

---

## 15. Maintenance Checklist

For every M2C release, verify:

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
- [ ] Menux can invoke headless M2C without bypassing policy.
- [ ] Content-free server persistence canary tests pass.
- [ ] Backend, frontend, CLI, sandbox, and red-team suites are green.
- [ ] Planned or gated features remain labeled accurately.
- [ ] The README, §2.4 and §5.2 list exactly the commands, flags, tools and dependencies that exist (the `Q08` check passes).
- [ ] The `Q07` bypass corpus and the `Q09` crash and resume suite pass; every policy or sandbox fix added a row.
- [ ] "Always allow" saves only the exact call, and a deny rule still wins after `cd`, restart and reconnect.
- [ ] No code from a leaked or unlicensed source entered the repository (D13).

---

## 16. Source Map

The main planning sources for this manual are:

- `data/docs/m2c_build_plan.md`;
- MiniMe Build tab and workbench implementation;
- backend local workspace, code proposal, task, and deployment routes;
- the protocol, server, client, loop, policy, sandbox, and quality work packages described by the build plan;
- `MiniLocker` (the `draft` repo, reviewed at commit `54520a2`) as a source of reusable modules and attack scenarios, as mapped in `m2c_build_plan.md` §11.6;
- the `m2c/`, `backend/codeagent/` and `protocol/` trees of the MiniMe repository (revision 1.2 status, `m2c_build_plan.md` §0.6);
- the public changelog and example settings of the official Claude Code repository, read as documentation only (`m2c_build_plan.md` §11.7);

This document is the user-facing layer. The build plan remains authoritative for patch order, exact module ownership, test commands, milestone gates, and implementation status.

---

## 17. Prior Art: What Other Coding Agents Do and What M2C Takes

**Rule (D13).** M2C uses public documentation, public changelogs, observable behavior and code whose licence has been read. It does not use leaked, unlicensed or source-unavailable code, including a copy re-uploaded under a permissive licence, and it is not written as a close rewrite of any such code. This guide therefore names no repository that republishes proprietary source. The comparison below is limited to what public changelogs and example files say.

| Area | What comparable agents do | What M2C takes | Where |
| :--- | :--- | :--- | :--- |
| Permission rules | `tool(pattern)` rules; a long history of fixes for compound commands, wrapper programs, relative patterns and symlinks | Turn each past bug class into a test row before it can happen here | `Q07` |
| "Always allow" | Saves a rule from the prompt | Save only the exact call, re-check it, never broader | `C25`, D16 |
| Sandbox | Sandboxed commands still follow the permission flow; auto-allow is an opt-in | Same rule; off by default | D17 |
| Hooks | JSON on stdin, exit codes, blocking events | Same contract, but tighten-only | `C13`, D15 |
| Skills and commands | Folder-based, can declare tools | Local files only; no unattended run without an allow rule | `C14` |
| MCP | A major extension point and a major attack surface | Device-local only; descriptions are untrusted; exact-name rules | `C23`, D18 |
| Subagents | Separate context, own model | Own model class and budget; retry truncated answers | `L02` |
| Compaction | Summaries, user instructions kept | Never drop recent turns after a crash; react to "context too long" | `L03`, `Q09` |
| Headless | `-p`, JSON, streaming JSON, service exit codes | `stream-json` for Menux; the exit-code table stays | `C28` |
| Organization policy | Managed settings, strict presets | A managed layer that a lower layer cannot loosen | `C27` |
| Terminal safety | Control characters in output and file names | Neutralise before printing | `Q07` |

**Where M2C is already ahead of what the public record shows:** the fail-closed tool catalog with a test that stops it drifting from the protocol, the "risk may be raised by the client and never lowered" rule, the content-free server design (O1) and the folder-trust fingerprint that already covers hook, skill and agent folders.

---

## 18. Ideas Not Yet Scheduled

These are suggestions, not commitments, and none has a work package yet. Each should become one only after the Phase 3 gate (`I03`).

| Idea | What it is | Why |
| :--- | :--- | :--- |
| **`/why` everywhere** | Beyond `C25`'s last-call explanation, an `m2c explain-policy` that shows, for a hypothetical call, which rule or mode would decide | Makes rules debuggable without trial and error |
| **Session rules with expiry** | An approval can be "for this session" or "for 30 minutes", listed and revocable with `/permissions` | Avoids permanent rules from a one-time yes |
| **`m2c replay`** | Re-run a saved local transcript against a new build with a fake model, and diff the tool calls | Cheap regression test for the golden tasks (`Q02`) with no model cost |
| **Repo-local subagents** | `.m2c/agents/*.md` with a name, tools and a model class; trusted through the folder-trust prompt | Lets a team ship its own reviewer or migrator |
| **Verify-loop presets** | `m2c init` detects the project's test and lint commands and writes them as the `verify` skill | Makes `L04` useful on day one |
| **Service-mode exit codes** | A separate documented set for a long-running `m2c` used by a supervisor | For unattended and Menux use |
| **Trust gate for apps and hooks** | One screen listing every hook, skill, agent and MCP server a folder wants to use, approved together | Folder trust (`C26`) already fingerprints them |
| **Native Windows and macOS** | A sandbox backend for each (Windows job objects and AppContainer, macOS Seatbelt), then Menux's device mesh can use M2C on every machine | Required by Menux revision 1.2; outside O3 for v1 |
| **Editor adapters** | VS Code, JetBrains and Neovim over ACP (`C18`) | Already named as Phase 5 intent |
| **Status, resume, stop, service, vault** | The commands earlier drafts of this guide listed | Decide: give each a work package, or remove it from the guide |

*End of the guide.*
