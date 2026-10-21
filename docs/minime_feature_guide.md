# MiniMe Feature Guide

**Purpose:** the user manual and feature register for MiniMe.

**Status basis:** this guide describes the implementation and planning material available in the MiniMe repository at the time it was written. It is intentionally more product-oriented than the Atlas pages, API inventory, architecture notes, or build plans. Those documents explain how the system is built; this document explains what a person can do with it.

The words **Available**, **Partially wired**, and **Planned** are important:

- **Available** means the repository contains a reachable implementation or a complete user workflow.
- **Partially wired** means the UI, backend, or generation path exists but some part of the end-to-end experience is incomplete, optional, or still being hardened.
- **Planned** means the capability is described in the roadmap or design documents but should not be treated as shipped.

### Ecosystem Synchronization & Companion Chapters

MiniMe Web (`surface='web'`) is the flagship workspace surface of a three-product ecosystem sharing **one account, one subscription tier, one `minicore/` runtime library, and one `usage_ledger` (`0012`)**:

| Book Chapter | Guide File | Role in the Connected MiniMe Book |
| :--- | :--- | :--- |
| **Ch. 1 · Rulebook** | `MiniMe_Financial_Strategy_Rulebook.md` | Governing constitution for pricing (`$0 / $9 / $29 / $79`), token caps, 8 LLM providers, COGS ≤ 45%, hiring, and funding |
| **Ch. 2 · Technical Roadmap** | `minime_technical_roadmap.md` | Engineering sequence `Tech-A` → `Tech-H`, model hygiene, and cross-track timeline |
| **Ch. 3 · Server Guide** | `minime_server_management_guide.md` | Metric-gated server split stages (`Stage 1` single box → `Stage 5` fleet) |
| **Ch. 4 · MiniMe Feature Guide** | `minime_feature_guide.md` *(this guide)* | Complete feature manual for the MiniMe Web application across all 8 workspace tabs and 25 areas |
| **Ch. 5 & 6 · M2C Guides** | `m2c_feature_guide.md` & `m2c_build_plan.md` | Local-first terminal & editor coding agent (`m2c`, `surface='m2c'`, 64 WPs) |
| **Ch. 8 & 9 · Menux Guides** | `menux_feature_guide.md` & `Menux___Build_Execution_Guide.md` | Local-first personal automation node (`menux`, `surface='menux'`, 59 WPs) |
| **Ch. 11–14 · FBEBC Guides** | `fbebc-research-program-guide.md` + companions | Fitness-Band Elitist Bacterial Colony research track (`Stage 1` preprint → `Stage 2` `backend/agents/evolution/`) |

---

## 1. What MiniMe Is

MiniMe is a personal, workspace-centered AI operating environment. It is not only a chat box and not only a project manager. It combines:

- conversational work with persistent chats;
- workspaces that hold the context, sources, notes, plans, generated artifacts, and progress for a project;
- a roster of specialized AI agents that can research, reason, write, review, test, design, and organize work;
- structured notebooks for turning source material into knowledge and study material;
- staged project execution from research through planning, building, testing, and growth;
- a code workbench for inspecting and changing project files with review gates;
- knowledge graphs, backlinks, clusters, facts, corrections, and generated diagrams;
- hardware and mechanical design assistance;
- external integrations such as Google Calendar, MCP servers, PageSpeed, UptimeRobot, web search, prices, audio, and video;
- live progress, notifications, usage accounting, quota visibility, and traceable agent execution.

The central idea is that a task should not disappear when a chat response finishes. Work is promoted into a durable workspace, organized into stages, and made available to later chats and tools.

---

## 2. The Main User Experience

### 2.1 Sign in and enter the application

MiniMe uses Supabase-backed authentication. The shell provides:

- a login screen;
- a signed-in account menu showing the current account;
- sign-out;
- protected application views;
- an initial loading screen while session, chats, workspaces, and usage data are bootstrapped;
- persisted navigation state so a refresh can restore the last active tab and active chat.

The frontend is a Next.js application. The backend is a FastAPI service. In local development they normally run as separate frontend and backend containers.

### 2.2 Navigate by stage

The primary application tabs are:

1. **Chat**
2. **Notebooks**
3. **Research**
4. **Plan**
5. **Build**
6. **Test**
7. **Growth**
8. **Role Library**
9. **Workflow Templates**
10. **Token Usage**
11. **Settings**

Tabs are loaded lazily where practical. Once opened, a tab stays mounted during navigation so a user does not lose local UI state merely by switching tabs. The active tab is stored locally and restored after a refresh.

Workspace-aware tabs expose a workspace data bubble in the shell. The bubble is a compact, collapsible facts surface for the active workspace. Its collapsed state is remembered separately per tab; it does not change the chat working-panel collapse state.

### 2.3 Responsive and mobile use

MiniMe has a structural mobile navigation path rather than only shrinking the desktop layout. Mobile support includes:

- a mobile header;
- a mobile chat drawer;
- per-tab project or workspace picker drawers;
- responsive sheets for modal content;
- mobile-specific notebook, research, plan, build, test, and growth views;
- touch-friendly graph and diagram interaction;
- a mobile working-panel drawer;
- preserved active chat and workspace state.

Some complex surfaces use a different mobile composition because a desktop file explorer, graph, or multi-panel workbench cannot be made usable by CSS resizing alone.

---

## 3. Chat

### 3.1 Persistent chats

A user can:

- create a chat;
- open an existing chat;
- rename a chat;
- delete a chat after confirmation;
- switch between chats from the sidebar;
- attach a chat to one or more workspaces where the workflow allows it;
- open a chat from a notification, workflow template, or workspace surface;
- inspect prior messages and generated outputs;
- continue a task later instead of restarting from an empty conversation.

Chat titles and workspace relationships are persisted by the backend. The frontend remembers the active chat locally for fast restoration.

### 3.2 Workspace chat docks

Workspace tabs include an embedded chat dock. This allows a person to work on a notebook, plan, build, test, or growth surface while asking questions about the selected workspace without leaving the stage.

The dock supports:

- switching the active chat associated with the selected workspace;
- creating a new chat in the current workspace;
- collapsing the entire dock;
- resizing the dock where the desktop layout allows it;
- opening and collapsing the separate working panel;
- keeping the chat and working panel together when the full dock is collapsed;
- sending context from the current tab into the chat;
- opening generated results back in the owning stage;
- jumping from a notification to the relevant chat or generated content.

### 3.3 Ask and Edit modes

The chat composer can operate in at least two important modes:

- **Ask:** ask questions, request analysis, or have MiniMe generate an answer without proposing file changes.
- **Edit:** ask MiniMe to plan or propose changes to project files. Changes enter the code proposal and review flow rather than silently modifying files.

Build context chips can be attached to the chat. A chip identifies a file, component, symbol, or other relevant code context. Chips can be cleared, opened, or used to tell the editor which context the request concerns.

### 3.4 Agent execution and live progress

A submitted task can be:

- previewed before execution;
- confirmed before execution when the workflow requires an explicit approval step;
- routed through a generalist or specialized agent chain;
- decomposed into parallel branches where safe;
- paused;
- resumed;
- streamed as it runs;
- inspected through a step-by-step trace;
- reviewed through a working panel;
- recorded with usage and outcome metadata.

The user can see requested roles, selected agents, agent starts, token chunks, completion events, errors, handoffs, branch activity, and final rendering. A trace can show more detail than the final answer, while the final answer remains organized for normal reading.

Long-running agent work uses a dedicated task pool so it does not consume the ordinary HTTP thread budget. Saturation and timeout conditions are surfaced as controlled failures rather than leaving requests hanging indefinitely.

### 3.5 Chat input intelligence

MiniMe can classify a message against registered internal tools, study actions, and connected MCP tools. This classification is intended to recognize requests such as:

- generate flashcards or a quiz;
- build a study guide;
- create a mind map or workflow;
- generate a podcast, presentation, or video overview;
- update study progress;
- use a connected external tool.

The classification pass is designed to be non-destructive. A classification failure should fall back to normal chat rather than blocking the message. The system can also attach workspace and topic context to a chat turn so answers are grounded in the selected project material.

### 3.6 Notifications and live events

MiniMe uses live event channels for events such as:

- agent started;
- agent token chunk;
- agent completed;
- agent error;
- requested role;
- usage update;
- quota alert;
- task or workspace progress;
- generation started;
- generation completed;
- generation failed;
- note or artifact proposed;
- workspace promoted;
- panel content written;
- code files updated.

The notification bell provides a cross-chat inbox. Opening a notification can navigate to the relevant chat or workspace.

---

## 4. Workspaces and Projects

### 4.1 Workspace lifecycle

A workspace is MiniMe's durable project container. A user can:

- create a workspace;
- name and rename it;
- open it from the stage where it belongs;
- promote it to another stage;
- attach existing chats;
- create a new chat inside it;
- detach or delete chats from it;
- manage members;
- change member roles or permissions where supported;
- leave a workspace;
- remove the owner or manage ownership operations where authorized;
- delete the workspace;
- export its chats and stored artifacts;
- import a previously exported workspace manifest;
- inspect workspace audit activity;
- view workspace facts in the shell data bubble.

Workspace stages include note/notebook, research, plan, build, test, and growth. Promotion moves the project through the intended product lifecycle and takes the user to the corresponding tab.

### 4.2 Workspace collaboration

Workspaces support multi-person collaboration concepts, including:

- membership lists;
- owner and member administration;
- member attribution grants;
- workspace votes;
- attribution settings;
- audit records.

The exact permission available to a person depends on authentication and workspace ownership checks. Workspace-scoped routes consistently verify that the requesting user may access the workspace.

### 4.3 Workspace facts and durable context

Workspace facts are project-wide truths that should be reused across chats and agents. The built-in categories include:

- brand voice;
- target user;
- technology stack;
- custom facts.

Facts are read into conversation memory automatically. A user does not need to paste the same project assumptions into every new chat. The custom area also stores structured project data such as mechanical specifications, parts, wiring, instructions, and integration settings.

Facts may be edited directly. Agent-proposed facts can enter a candidate queue where the user accepts or rejects them instead of allowing an uncertain extraction to become permanent automatically.

### 4.4 Workspace data overlays

Workspace-aware tabs can show a compact facts panel without leaving the current view. This panel is intentionally separate from the chat working panel. It can be collapsed, reopened, and remembered independently for Chat, Notebooks, Research, Plan, Build, Test, and Growth.

### 4.5 Export and import

Workspace export can package the chats attached to a workspace into supported artifact formats. A single chat can return one artifact; multiple chats can be bundled into a ZIP. Workspace import accepts the exported manifest and restores supported data.

Export is intended for portability, backup, and moving durable work into the MiniMe book or another archive. It is not a substitute for database backups.

---

## 5. The Agent System

### 5.1 General routing

MiniMe has a registry of roles and agent implementations. A request can be routed through a starter general agent filter, an inspector, a panel or committee, staffed specialists, execution agents, reviewers, and a final organizer.

The system can:

- select suggested agents;
- honor explicitly requested roles;
- map roles to available agent keys;
- run compatible work in parallel;
- preserve dependency order where one result feeds another;
- collect intermediate outputs;
- hand off work between roles;
- loop on review or repair when the workflow permits it;
- stop, redo, or resume work through the task controller;
- render a final answer from the structured result.

### 5.2 Representative specialist abilities

The current agent roster includes specialized capabilities for:

- academic search and web research;
- source ingestion and source management;
- PDF and video ingestion;
- voice ingestion;
- web clipping;
- fact detection and fact summarization;
- concept linking;
- backlinks and note clusters;
- citation graph construction;
- contradiction prefiltering;
- correction location;
- note taking, note tables, and topic notes;
- extraction tables;
- mind maps and workflow suggestions;
- study content, quizzes, flashcards, and study guides;
- podcast scripts, rehearsal scripts, slide decks, and text-to-speech;
- report writing, documentation, and output organization;
- idea planning and feature planning;
- architecture, dependency, schema, and component diagrams;
- code writing, code editing, code review, and test writing;
- static scanning, security review, performance review, duplication review, and output guarding;
- hardware specification, component specification, prices, dimensions, and mechanical design;
- deployment configuration and deployment actions;
- calendar actions and connected integrations.

This list describes the role vocabulary in the codebase. Availability of a role in a particular user flow depends on the selected stage, task type, enabled provider, and configured credentials.

At commit `febb685`, the repository contains **73 Python modules in `backend/agents/`** (59 specialist agent modules + 14 package/support modules) mapped across **46 distinct router roles** in `backend/eo/registry.py` (`ROLE_PROMPTS_SEED`):

| Agent Family | Module Count | Representative Modules in `backend/agents/` | Primary Router Roles & Model Tier |
| :--- | :--- | :--- | :--- |
| **Executive Orchestration & Meta** | 9 | `panel.py`, `inspector.py`, `starter.py`, `synthesizer.py`, `reviewer.py`, `critic.py` | `inspector`, `panel_member_a/b/c`, `synthesizer`, `reviewer` (Fast / Standard / Expert) |
| **Code & Software Engineering** | 11 | `code_editor.py`, `coder.py`, `architect.py`, `debugger.py`, `tester.py`, `security_scanner.py`, `deployer.py` | `code_editor`, `coder`, `architect`, `debugger`, `tester` (DeepSeek V3.2 / Qwen3-Coder / Claude) |
| **Research & Source Intelligence** | 12 | `academic_search.py`, `researcher.py`, `source_manager_exec.py`, `source_quality_flagger.py`, `contradiction_prefilter.py`, `fact_checker.py` | `researcher`, `fact_checker`, `source_planner` (Gemini 2.5 Flash / Sonar / Standard) |
| **Notebooks, Study & Knowledge Graph** | 11 | `mindmap_agent.py`, `flashcard_agent.py`, `quiz_agent.py`, `study_guide_agent.py`, `backlink_detector.py`, `cluster_agent.py` | `mindmap`, `study_guide`, `quiz`, `backlink_detector` (Fast / Standard) |
| **Hardware, CAD & Mechanical (`mech/`)** | 12 | `blueprint_agent.py`, `cad_coder.py`, `mech/validator.py`, `mech/repair.py`, `mech/manufacturability.py`, `parts_sourcer.py` | `blueprint`, `cad_coder`, `mech_validator` (Expert / DeepSeek R1 / CadQuery) |
| **Media, Visuals & Presentations** | 8 | `diagram_agent.py`, `wireframe_agent.py`, `slide_agent.py`, `audio_overview.py`, `video_overview.py`, `image_agent.py` | `diagram`, `wireframe`, `image_gen` (`gemini-3.1-flash-lite-image` / `3.1-flash-image`), `tts` |
| **Growth, Ops & External Tools** | 10 | `calendar_agent.py`, `seo_auditor.py`, `growth_strategist.py`, `mcp_bridge.py`, `price_watcher.py` | `calendar`, `seo_auditor`, `growth` (Fast / Standard) |

### 5.3 Safety boundaries around agents

Agent outputs pass through controls intended to reduce unsafe or invalid behavior:

- prompt and instruction injection guards;
- redaction and personally identifiable information scrubbing;
- quota sentinels;
- output guards;
- static security scanning;
- reviewer and security aggregator stages;
- tool-call budgets;
- dependency-aware execution;
- explicit user confirmation for sensitive actions;
- proposal-before-apply behavior for code and deployment changes;
- audit logging.

The daemon and local filesystem features have additional approval boundaries. External actions should be treated as privileged operations, not as ordinary text generation.

---

## 6. Notebooks

Notebooks are the knowledge and study workspace for source material. The current notebook navigation groups functionality into **Library**, **Diagrams**, **Study**, **Insights**, and **Corrections**.

### 6.1 Library

The Library brings source management and source relationships together.

Users can:

- ingest source material into a workspace;
- view source nodes;
- see multi-section documents grouped under one source;
- open source sections;
- rename source nodes;
- delete source nodes;
- inspect source metadata and generated content;
- detect backlinks between sources and notes;
- review source relationships;
- use source scope when generating notebook content.

Supported ingestion paths include the dedicated source/file flows for:

- pasted or clipped web content;
- video;
- generic imports;
- PDFs;
- voice/audio.

Ingestion may split a source into section nodes and connect them with `same_source` relationships. This makes long documents navigable without losing their parent-source identity.

### 6.2 Diagrams

Diagrams combines the mind map and workflow surfaces.

Users can:

- view a knowledge graph of notebook topics and relationships;
- select a topic node;
- generate a topic-specific study workflow;
- revisit saved workflows after a refresh;
- view suggested routes through the material;
- inspect Mermaid diagrams;
- pan, zoom, and interact with diagrams on desktop and touch devices;
- open related chats from a topic or workflow.

A topic workflow is generated for the clicked topic and can be persisted in the workspace. It is not merely temporary React state.

### 6.3 Study

The Study surface turns source material into active learning tools:

- flashcards with a flip interaction;
- quizzes with an answer runner and grading;
- study guides rendered as formatted Markdown;
- quiz attempt history;
- missed-question review;
- per-topic study progress;
- a board of topics in not started, ongoing, or done states;
- reset and manual progress controls;
- actions to ask about a step;
- actions to work through a step.

Study content can be generated for the entire notebook or for selected source nodes. The UI preserves generated panels and can show unread indicators when new content has appeared since the user last viewed a sub-tab.

### 6.4 Insights

Insights collects structured discoveries:

- extracted facts;
- fact candidates awaiting acceptance;
- suggested notes;
- note candidates awaiting acceptance;
- proposed clusters of related concepts;
- accepted or rejected cluster candidates;
- pending-count indicators;
- graph-backed relationships and node summaries.

The accept/reject pattern is deliberate: the system can suggest durable knowledge, but the user remains the authority over what becomes part of the workspace.

### 6.5 Corrections and Patch Review

A user can submit a plain-language correction and optionally scope it to a source or node. MiniMe attempts to locate the affected topic and propose a structured correction.

The correction workflow is:

1. enter the correction;
2. optionally choose a scope;
3. let the correction locator find the matching topic and operation;
4. receive either a no-match explanation or a queued candidate;
5. review the before/after patch;
6. accept or reject it.

A correction is not silently applied when it requires review.

### 6.6 Generated media and presentations

Notebook generation can produce:

- a two-host podcast script;
- synthesized podcast audio;
- a slide-style video overview with narration;
- presentation rehearsal audio;
- a slide deck or presentation text;
- Markdown content with tables, headings, and Mermaid diagrams.

Workspace-scoped audio and video are saved and served through ownership-checked routes. A user must generate an artifact before its media URL exists. Regeneration follows last-write-wins behavior for the workspace panel.

### 6.7 Notebook generation from chat

The chat can request notebook capabilities using natural language. The system classifies the request and dispatches one or more generation targets. A mixed request can report each branch separately, so one failed target does not necessarily erase successful results from the same request.

Generation events appear in the chat notification path, and generated panels can be opened from the notification row.

---

## 7. Research

The Research stage is for discovery and evidence collection before a project is turned into a plan.

It supports:

- research workspaces;
- nested chats tied to a research project;
- source ingestion and organization;
- academic and web research;
- citation-oriented outputs;
- source quality flags;
- contradiction detection and review;
- backlink discovery;
- concept linking;
- extraction tables;
- report and documentation generation;
- architecture and dependency diagrams;
- promotion of a research workspace into planning.

Research outputs can be grounded in the workspace sources rather than relying only on a free-form model response. Source scope can be narrowed to relevant nodes when a task concerns only one part of the research corpus.

---

## 8. Plan

The Plan stage converts a project idea or research result into a structured execution plan.

### 8.1 Planning workspaces

A planning workspace can contain:

- chats and planning decisions;
- the current plan;
- feature cards;
- feature statuses of missing, in progress, and done;
- module specifications;
- architecture diagrams;
- API and schema views;
- wireframes;
- component and dependency information;
- a blueprint-style device or product specification where relevant;
- promotion controls to move the project into Build or another stage.

### 8.2 Generated planning artifacts

Planning agents can produce:

- product requirements and feature plans;
- architecture diagrams;
- API contracts;
- schema diagrams;
- component dimension tables;
- dependency maps;
- feasibility analysis;
- devil's advocate analysis;
- contradiction reports;
- suggested workflows;
- wireframe specifications;
- structured module specifications containing inputs, outputs, descriptions, and edge cases.

Generated content can be stored in workspace panels so it survives a refresh and can be reused by Build and chat.

### 8.3 Wireframes

Wireframes let a user inspect a proposed interface before implementation. The preview can:

- render the proposed screen;
- inspect elements;
- select an element and request a change in chat;
- show warnings or integration concerns;
- turn a wireframe into a code proposal for review.

Wireframe-to-code is proposal-based. It does not bypass the same review path used for other AI-generated edits.

### 8.4 Hardware and product blueprint features

For product or device projects, the planning surface can hold a structured device specification with:

- a product summary;
- tags;
- an optional generated image URL;
- a parts list;
- quantities and categories;
- vendor and price data;
- wiring nodes and edges;
- mechanical enclosure dimensions;
- component placements;
- generated instructions grouped into phases and steps.

Instruction steps are individually checkable. The parts table supports price refresh. Three-dimensional-print parts can use estimated print cost and material/archetype rules instead of an inappropriate market lookup. Price outliers are flagged rather than silently discarded.

---

## 9. Build

Build is the execution workbench for a selected build-stage workspace. It has four sub-views:

1. **Tasks**
2. **Instructions**
3. **Editor**
4. **Wireframes**

### 9.1 Tasks

Tasks show the feature or work-item board. The default status columns are:

- Missing;
- In Progress;
- Done.

The board is based on the workspace plan and feature status. A person can use chat to ask what to build, open task-related context, and promote work onward.

### 9.2 Instructions

Instructions show the device or project execution checklist. A user can:

- view phases;
- expand steps;
- mark an individual step complete or incomplete;
- ask MiniMe about a step;
- choose **Work on this** to open a context-aware build request;
- use the step's related files or draft as the starting context for an edit.

Checklist completion is intentionally separate from wholesale regeneration of the device specification.

### 9.3 Editor workbench

The Editor is a full code workbench rather than a plain text box. It includes:

- a project file explorer;
- folders and files;
- new-file creation;
- new-folder creation;
- file rename, move, and delete operations;
- editor tabs;
- CodeMirror-based code editing;
- language-aware editing support;
- dirty-state tracking;
- save behavior;
- formatting-on-save where supported;
- project search;
- quick open;
- recent files;
- context menus;
- code context chips;
- problems/findings panel;
- console panel;
- history panel;
- history comparison;
- conflict comparison;
- preview column;
- device and viewport toolbar;
- URL preview;
- wireframe preview;
- reload and open-new-tab actions;
- bottom panels that can be resized or toggled;
- a pending proposal tray;
- review mode;
- server-versus-local version comparison;
- ZIP download of workspace files.

The editor works against cloud workspace files (`workspace_code_files` in PostgreSQL) and synchronizes with the **M2C local-first architecture (`m2c_build_plan.md` Override O6, Phase 0 `MK_B00–B12`)**:

| Build Workbench Surface | Browser Disposition (`Phase 0` Sync) | Governing Work Package / Companion Guide |
| :--- | :--- | :--- |
| **Cloud File Explorer, CodeMirror Editor, Multi-Tab & Save** | **Retained in Browser (`Available`)** — full cloud project editing with dirty-state and conflict guards (`MK_B08–B11`) | `minime_feature_guide.md` §9.3, `m2c_build_plan.md` §4 |
| **AI Edit Proposals, Hunk Review, History, Problems & Console** | **Retained in Browser (`Available`)** — review-gated diffs, version comparison, and HTML/React/URL preview | `minime_feature_guide.md` §9.4–9.5 |
| **Pyodide Chat Artifacts (`ArtifactRenderer.jsx`)** | **Retained & Self-Hosted (`MK_B02`)** — runs inline Python charts/calculators inside chat artifacts via Web Worker | `m2c_build_plan.md` `B02` |
| **Browser Python `Run` in Preview Pane** | **Removed in Phase 0 (`MK_B03`)** — replaced with neutral empty state; real Python execution runs locally in **M2C CLI** | `m2c_build_plan.md` O6 & `B03` |
| **Browser `Terminal` Sub-Tab & Browser `Local-Folder Mode`** | **Removed in Phase 0 (`MK_B04–B06`)** — replaced by the **"Work locally with M2C"** CLI handoff banner and `/api/codeagent/*` live view | `m2c_feature_guide.md` §8.1, `m2c_build_plan.md` `B04–B06` |

### 9.4 AI-assisted code editing

The code editing flow is:

1. provide a request in Ask or Edit mode;
2. include relevant file or symbol context;
3. let MiniMe generate a proposed change;
4. inspect the files and hunks in the review surface;
5. keep all, keep selected changes, or reject;
6. write accepted changes to the workspace;
7. inspect resulting problems and console output;
8. use the server comparison or history view when the local and server versions differ.

AI proposals include summaries and affected paths. A proposal remains pending until the user resolves it. Conflicts receive a dedicated comparison view rather than being silently overwritten.

### 9.5 Code findings and repair

The workbench can display code findings when the backend can provide them. Findings can be opened at their file location. The console can offer **Fix with AI**, which routes the problem back into the chat Edit flow with the relevant context.

Problems may be unavailable for a workspace or provider; the UI distinguishes unavailable findings from an empty findings list.

### 9.6 Deployment from Build

Build includes a deploy surface for:

- proposing deployment configuration;
- reviewing generated configuration;
- replacing a pending proposal with a new proposal;
- writing approved configuration;
- moving an application toward go-live;
- configuring UptimeRobot monitoring;
- storing the monitoring integration settings in protected workspace data.

Deployment actions are deliberately separated into propose, write, and go-live steps. A generated configuration is not automatically made live.

---

## 10. Test

The Test stage provides a project space for simulation and validation before release.

It supports:

- test-stage workspaces;
- nested chats;
- simulation requests;
- generated test plans;
- test-oriented agent routing;
- security and static checks;
- review of findings and proposed fixes;
- promotion to Growth when the project is ready.

The backend exposes simulation and test-oriented task paths. The exact test depth depends on the selected workflow and configured agents. Tests should be treated as evidence attached to a workspace, not merely as a chat answer.

MiniMe also includes a separate research-oriented evolution/sandbox subsystem in the repository. That subsystem uses bounded candidate changes, validation gates, Docker isolation, ledgers, checkpoints, and score-based adoption. It is an engineering/research capability and should not be confused with automatically executing arbitrary user code in the normal application.

---

## 11. Growth

Growth is the post-build stage for launch preparation, marketing, measurement, and ongoing project development.

It supports:

- growth-stage workspaces;
- chats and project management;
- marketing and launch planning;
- calendar integration;
- content and campaign-oriented agent work;
- PageSpeed content audits;
- monitoring integration;
- promotion and handoff from Test.

### 11.1 Google Calendar

When connected, the Calendar panel can:

- list events for a date range;
- create events;
- delete events;
- use OAuth connect and callback flows;
- report that the integration is not connected rather than pretending an event operation succeeded.

### 11.2 PageSpeed audit

A workspace can run a PageSpeed Insights audit against a URL and choose a strategy such as mobile. Results are fetched live rather than treated as permanent workspace content. Invalid URLs and provider errors are returned as visible failures.

---

## 12. Role Library

The Role Library is the reusable role and prompt catalog.

Users can:

- browse role entries;
- inspect role descriptions and metadata;
- save or update role prompts;
- pin roles;
- select roles for a task or workflow;
- maintain a stable vocabulary for recurring work.

Roles are separate from a single chat message. A role can be reused across workflows and routed to a different provider or agent implementation as the registry changes.

---

## 13. Workflow Templates

Workflow Templates turn a repeatable multi-role process into a reusable template.

Users can:

- browse templates;
- inspect the roles and structure in a template;
- create a template;
- edit a template;
- delete a template;
- open a template in chat;
- start a task from a template;
- save a successful run or role selection for reuse.

Templates are useful when the user wants a consistent process rather than asking MiniMe to invent a new chain on every task.

---

## 14. Token Usage, Quotas, and Cost Visibility

The Token Usage tab exposes operational usage information instead of hiding it behind the model.

It can show:

- current quota;
- verified daily usage;
- usage by agent key;
- usage history;
- cross-session usage updates;
- quota alerts;
- provider/model-related usage where available;
- historical records scoped to the user or workspace.

The backend also maintains usage and cost instrumentation for agent calls, including provider, model, input/output tokens, wall time, agent key, role, tier/path, and computed cost where configured.

The system has budget controls at multiple levels:

- per-request or per-task tool budgets;
- provider retry and rate-limit handling;
- agent pool capacity;
- daily model request or token caps in the research Sigma subsystem;
- graceful stop and checkpoint behavior when a daily budget is exhausted.

Usage data is intended to answer practical questions such as which agent is expensive, whether a workflow is slow, and whether a tier can support real users.

### Unified Cross-Surface Plans & Shared Credit Pool (`Rulebook Part 7` + `Tech-A/B` + `S01`)

Per `MiniMe_Financial_Strategy_Rulebook.md` (Rules 4–8) and `m2c_build_plan.md` Override O2, **one MiniMe account and one shared monthly token/dollar pool (`usage_ledger` + `user_plans` in migration `0012`)** govern **MiniMe Web (`surface='web'`)**, **M2C (`surface='m2c'`)**, and **Menux (`surface='menux'`)**:

| Plan Tier | Monthly Price (USD / BDT) | Standard Pool | Deep / Expert Pool | Brain / Frontier Pool | Active Surfaces & Cap Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Free** | `$0` / `৳0` | 150K tokens/day (hard daily ceiling) | Preview only | None | Web + M2C + Menux preview; Free budget capped at `$150/mo` total (`Rule 8`) |
| **Basic** | `$9/mo` (`$90/yr`) · `৳799/mo` | **12M** tokens/mo | **1.5M** tokens/mo | None (Panel vote) | Shared across Web, M2C CLI, and Menux Node (`COGS-at-cap ≤ $3.49`, `41%`) |
| **Moderate** | `$29/mo` (`$290/yr`) · `৳2,499/mo` | **40M** tokens/mo | **6.0M** tokens/mo | **1.2M** tokens/mo (Batch Brain) | Unlocks in `S3a` (`Tech-C/E`); shared across all 3 surfaces (`COGS-at-cap ≤ $11.55`, `42%`) |
| **Ultimate** | `$79/mo` (`$790/yr`) · `৳6,999/mo` | **120M** tokens/mo | **20.0M** tokens/mo | **4.5M** tokens/mo (Real-Time Brain) | Unlocks in `S3b` (`Tech-G`); shared across all 3 surfaces (`COGS-at-cap ≤ $31.80`, `43%`) |

---

## 15. Settings and Profile

Settings and profile surfaces support personal defaults and reusable preferences.

A user can manage:

- profile fields;
- corrections and learned preferences;
- preferred output format;
- reusable output-format instructions;
- account access and sign-out;
- integration state;
- workspace-independent application preferences;
- persistent UI selections stored locally, such as active tab, selected notebook, selected sub-tab, sidebar collapse, and dock collapse.

Profile corrections can be stored and reused by future responses. The system distinguishes personal profile memory from workspace facts so a user's general preference does not accidentally become a project-wide truth.

---

## 16. Knowledge Graph and Structured Data

The knowledge graph is a cross-cutting feature used most visibly by Notebooks, Research, and Insights.

It can represent:

- source sections;
- topics;
- notes;
- facts;
- backlinks;
- citations;
- clusters;
- suggested relationships;
- node summaries;
- graph edges;
- workflow and mind-map relationships.

Users can:

- view graph nodes and edges;
- select nodes;
- rename nodes;
- delete nodes;
- inspect node summaries;
- view topic graphs;
- create or remove edges where the UI supports it;
- detect backlinks;
- propose clusters;
- accept or reject cluster candidates;
- promote graph discoveries into notes or study material.

Graph-backed content is workspace-scoped and subject to ownership checks. It is not merely a visualization layer; it is a source of retrieval context for later tasks.

---

## 17. External Tools and Integrations

### 17.1 MCP servers

MiniMe can connect to configured Model Context Protocol servers. It can:

- list configured MCP servers;
- inspect connection status;
- discover server tools;
- include connected tools in chat intent classification;
- propose a workspace-scoped MCP action;
- ask the user to confirm or deny the action;
- execute only after the approval path allows it.

MCP tools are treated as external capabilities. The system does not assume that a natural-language request should immediately perform an external side effect.

### 17.2 Local workspace bridge

The local workspace bridge can:

- report local connection status;
- list a guarded directory;
- read a guarded file;
- propose a local action;
- confirm or deny a local action.

The path guard and approval workflow are essential parts of this feature. **Synchronization Note (`m2c_build_plan.md` Override O6):** While the backend routes (`backend/eo/local_workspace.py` and `local_workspace_tools.py`) exist in the repository baseline, the browser UI's direct local-folder picker is retired in **Phase 0 (`MK_B05–B06`)** in favor of pairing the **M2C CLI (`m2c`)** and **Menux Node (`menux`)** via device-code authentication (`minicore/`). This ensures all local file and shell operations run inside the local OS sandbox (`bubblewrap`) rather than through a browser tab.

### 17.3 Web research and clipping

MiniMe agents can search the web, clip web content, ingest it into a workspace, and use it as research material. Search providers can be configured with fallback behavior and should fail gracefully when a provider is unavailable.

### 17.4 Component and parts research

Hardware-oriented flows can look up:

- component specifications;
- dimensions;
- datasheets;
- part prices;
- vendor listings;
- estimated 3D-print costs;
- price anomalies.

Price refresh is explicit and updates the workspace parts data rather than silently replacing unrelated workspace facts.

### 17.5 Calendar, monitoring, and performance tools

In addition to Calendar, PageSpeed, and UptimeRobot, the backend has provider-facing support for model APIs, audio synthesis, video construction, and deployment operations. Each integration has its own credentials, error behavior, and approval boundary.

---

## 18. Deployment and Operations Features

MiniMe's operational features are part of the product because they are required to run it reliably.

### 18.1 Health and diagnostics

The backend exposes:

- a health endpoint;
- database latency probes;
- chat-page cache statistics;
- database pool statistics;
- agent-task pool statistics;
- starter-agent statistics;
- Laya routing statistics;
- tool-budget statistics;
- conversation-thread statistics;
- ledger-event statistics;
- quota and usage history.

These are primarily operator and admin surfaces, not normal end-user features.

### 18.2 Error tracking and tracing

Sentry can capture errors and performance traces when configured. The application remains usable in local development without a Sentry DSN. Agent events and audit records provide additional task-level visibility.

### 18.3 Persistence and resilience

The implementation includes:

- relational persistence for users, chats, workspaces, nodes, edges, candidates, panels, progress, and audit data;
- Redis-backed or cache-backed paths where appropriate;
- vector or semantic retrieval support;
- chat page caching;
- semantic and routing caches;
- database pool warm-up and bounded connection use;
- dedicated agent task pools;
- graceful shutdown behavior;
- resumable long-running tasks;
- research loop checkpoints;
- append-only or chained ledgers for selected research operations.

### 18.4 Docker deployment

The repository separates frontend and backend Docker build contexts. Docker Compose runs the services together for development and early deployment. The server-management plan intentionally gates more complex infrastructure such as load balancers, worker pools, and Kubernetes on real usage and revenue rather than adding it prematurely.

---

## 19. Security and Trust Features

Security is distributed across the whole product rather than isolated in one screen.

### 19.1 Identity and ownership

Protected routes verify the Supabase JWT and enforce user/workspace ownership. Workspace data, media, files, facts, panels, candidates, and task history are not intended to be readable by an unrelated user.

### 19.2 Approval gates

The following actions can require an explicit proposal and confirmation:

- code edits;
- deployment configuration writes;
- go-live actions;
- local filesystem operations;
- MCP external actions;
- candidate acceptance;
- correction application;
- cluster acceptance;
- fact acceptance.

### 19.3 Content and prompt protections

The agent path includes safeguards for:

- instruction injection;
- secrets and sensitive data redaction;
- personally identifiable information;
- malformed or unsafe output;
- quota abuse;
- tool overuse;
- security scan findings;
- provider failures and retry storms.

### 19.4 Research sandbox

The separate candidate-evolution research pipeline provides stronger experimental controls:

- pinned container images;
- network isolation;
- read-only root filesystem;
- PID and memory limits;
- non-root execution;
- no host secret passthrough;
- score-smuggling defenses;
- admission gates;
- hash-chain ledger records;
- checkpoint/resume;
- controlled candidate adoption.

This is an experimental evolution environment, not a promise that every normal MiniMe agent can execute arbitrary code safely without review.

---

## 20. Important User Workflows

### 20.1 Learn from a document

1. Create or open a notebook workspace.
2. Ingest a PDF, web clip, video, generic import, or voice source.
3. Review the source tree and section nodes.
4. Generate a mind map, study guide, flashcards, or quiz.
5. Use the topic workflow from the mind map.
6. Answer quiz questions and inspect missed attempts.
7. Mark topics as not started, ongoing, or done.
8. Ask chat about a source or topic.
9. Accept useful facts, notes, and clusters.
10. Export the resulting chats or artifacts.

### 20.2 Turn research into a product plan

1. Create a research workspace.
2. Search, clip, and ingest sources.
3. Link concepts and review contradictions.
4. Generate reports, citations, architecture, and dependency views.
5. Promote the workspace into Plan.
6. Generate features, modules, API/schema artifacts, and wireframes.
7. Review the plan and mark feature status.
8. Promote the workspace into Build.

### 20.3 Build with AI assistance

1. Open the Build tab and select a build workspace.
2. Inspect Tasks and Instructions.
3. Choose a step or file and send it to chat.
4. Switch to Edit mode when a file change is desired.
5. Review the proposed files and hunks.
6. Keep or reject changes.
7. Inspect problems, console output, history, and preview.
8. Resolve conflicts explicitly.
9. Review deployment configuration.
10. Write and go live only after the appropriate approval.

### 20.4 Correct a notebook without losing control

1. Open Corrections.
2. Describe the correction in plain language.
3. Choose a source or topic scope if known.
4. Review the located before/after candidate.
5. Accept it to apply the correction or reject it to discard it.
6. Re-run related generated content if the source scope has changed.

### 20.5 Use an external tool safely

1. Configure or connect the MCP server or integration.
2. Confirm that the server is connected and its tools are available.
3. Ask for the external action in chat.
4. Inspect the proposed action.
5. Confirm or deny it.
6. Review the resulting event, audit record, or generated artifact.

---

## 21. What Is Not the Same Thing as a Shipped Feature

The repository contains many plans, prototypes, experimental agents, disabled capability entries, and future product documents. The following distinctions prevent confusion:

- A role file does not necessarily mean the role is reachable from every tab.
- A backend endpoint does not necessarily mean a polished frontend exists for it.
- A UI card does not necessarily mean the provider credentials are configured.
- A capability manifest may list disabled or future capabilities for discovery and debugging.
- A roadmap phase is a future target, not current behavior.
- A research sandbox is not the same as general-purpose production code execution.
- A generated panel may be persisted while its media playback or download route is still under construction.
- A feature may be available only to workspace owners or authenticated users.
- An integration can be implemented but inactive until its environment variables and external account are configured.

When adding a feature to this guide, record its status and the required configuration instead of calling every code path “live.”

---

## 22. Future Feature Register

This section records the intended future direction so future work does not disappear from memory. These items are **not all current user features**.

### 22.1 Production Basic hardening

Planned work includes:

- full multi-tenant isolation across relational and vector stores;
- paid provider migration and controlled failover;
- Stripe metered billing;
- cost and usage dashboards;
- stronger rate limiting;
- production monitoring and audit polish;
- empirical decomposition versus consolidation testing;
- real demand and cost gates before opening higher tiers.

### 22.2 Moderate tier and Brain scaffolding

The technical roadmap plans a deferred Moderate stage with:

- tier-parameterized panel chains;
- decisions-locked and freedom-envelope hire metadata;
- same-tier dynamic routing pools;
- a passive Monitor v1;
- a provider/model shortlist based on real Basic usage;
- an internal Brain prototype evaluated against historical routing outcomes;
- declarative primitives such as classify, committee vote, staff-and-execute, loop-gate, and validate/repair;
- template promotion only after proven good outcomes.

### 22.3 Brain integration

Later, Brain is intended to choose a process structure for suitable expert or beast modes and higher package tiers. The intended boundary is:

- Inspector classifies first;
- Brain chooses a declarative plan;
- Panel and execution follow that plan;
- Brain can propose roles and prompts;
- Brain cannot bypass quota, injection, redaction, or output controls;
- standing defaults can be cached only after evidence;
- Brain remains out of the fast paths until its latency and quality are justified.

### 22.4 Monitor v2

A later closed-loop Monitor is intended to subscribe to stage-completion events while a task is running and choose among:

- ignore;
- self-repair for narrow parameter-level problems;
- interrupt and return to Brain for structural replanning.

The repair authority is intentionally meant to start narrow and expand only after real production evidence.

### 22.5 Ultimate tier

The Ultimate tier is intended to reuse the Brain and Monitor mechanism with a frontier-model Brain configuration. Its gate is operational capacity plus demand, not a calendar date.

### 22.6 Executable code-authoring

Executable code-authoring is deliberately deferred and permanently constrained. Before it can be considered, the plan requires:

- fully mocked externals;
- no real credentials in the execution context;
- mandatory Gitleaks and Semgrep filtering;
- per-generation token and attempt ceilings;
- mandatory human review for any new real external access;
- an explicit decision about whether a reviewed primitive can later be trusted autonomously.

The intended future is not unrestricted autonomous deployment.

### 22.7 Infrastructure evolution

The server-management plan expects infrastructure to evolve only when justified:

- Phase 0: one Docker Compose host with HTTPS, backups, and health checks;
- Phase 1: one hardened host with monitoring and rate limiting;
- Phase 2: load balancer plus replicated frontend/backend nodes;
- Phase 3a: dedicated background workers for long-running jobs;
- Phase 3b: Kubernetes or an equivalent orchestrator when tier count, queue depth, and team size justify it.

The daemon remains out of internet-facing deployment until it receives its own security audit.

| Technical / Business Phase | Target Window | Core Capabilities Unlocked | Governing Gate |
| :--- | :--- | :--- | :--- |
| **Tech-A · Instrumentation & Baseline** | Oct 2026 – Apr 2027 (`S0`) | Per-call dollar/token telemetry (`llm_call_log` + `usage_ledger` `0012`), Groq & Gemini 3.1 Flash Image roster cleanup | Immediate priority (#1 checklist item) |
| **Phase 0–6 · M2C & Menux** | Jan – Jun 2027 (`S0`) | Local-first `m2c` coding CLI (`Jan–Feb 2027`) and `menux` automation node (`Mar–Jun 2027`) sharing `minicore/` | Nov 2026 architecture & shared ledger lock |
| **Tech-B · Harden Basic for Launch** | Mar 2027 – Jan 2028 (`S1 → S2`) | Multi-tenant RLS, paid provider keys (2/vendor), SSLCommerz/bKash/Nagad + MoR billing, quota enforcement | Tech-A exit criteria met |
| **FBEBC Stage 2 · Evolution Engine** | Mar 2028+ (`Post-Basic`) | Ports `EvolutionEngine` (`elite_band` + `single_winner`) into `backend/agents/evolution/` | Gates `G1–G4` (Basic live, ops green, research budget line) |
| **Tech-C & Tech-D · Moderate Prep & Brain Proto** | Jul 2028 – Jan 2029 (`Late S2`) | `PANEL_CHAINS[tier]`, passive Monitor v1, and internal-only Brain prototype scored offline against `routing_memory` | Business Gate 3.5 (ops manageable) + routing data volume |
| **Tech-E & Tech-F · Moderate + Brain + Monitor v2** | H1 – Q3 2029 (`S3a`) | Live Brain meta-planner for `expert`/`beast` on Moderate (`$29`), plus closed-loop stream Monitor v2 | Gates 3.5 & 3.6 + Tech-D offline benchmark win |
| **Tech-G · Ultimate Frontier Brain** | Jul 2029 – Dec 2030 (`S3b`) | Frontier Brain tier (`$79`) via config/model resolution over Tech-C–F primitives | S3a self-sustaining + Ultimate demand gate |
| **Tech-H · Executable Code-Authoring** | Unscheduled (Permanent Gate) | Sandboxed primitive synthesis with mandatory Gitleaks/Semgrep + permanent human sign-off | Tech-E/F proven trustworthy in production |

---

## 23. How to Maintain This Manual

Every new MiniMe feature should add or update four things:

1. **User behavior:** what a person can do and what result they should see.
2. **State and ownership:** where the result is stored, who can access it, and whether it survives refresh.
3. **Approval and failure behavior:** what requires confirmation and what happens when a provider, model, or dependency fails.
4. **Status:** Available, Partially wired, or Planned, with the implementation or plan path recorded.

When a feature changes, update the relevant tab section and the future register if its roadmap status changes. Keep API details in the existing API documentation; this guide should explain the experience and the decisions that matter to a user.

---

## 24. Feature Coverage Checklist

Use this checklist when reviewing a new MiniMe release:

- [ ] Authentication and account menu still work.
- [ ] Active tab and active chat restore after refresh.
- [ ] Workspace creation, rename, membership, promotion, and deletion are clear.
- [ ] Chat can create, rename, open, delete, and continue conversations.
- [ ] Workspace chat docks preserve context and collapse state.
- [ ] Task preview, confirmation, pause, stream, resume, and trace behavior are visible.
- [ ] Agent progress and errors reach the user without silent failure.
- [ ] Notebook sources, graphs, generated panels, study tools, and corrections are durable.
- [ ] Generated audio/video can be retrieved after generation.
- [ ] Research outputs can be promoted into planning.
- [ ] Plan artifacts and wireframes are reviewable.
- [ ] Build edits remain proposals until accepted.
- [ ] Local filesystem and MCP actions require the expected approval path.
- [ ] Problems, console output, history, conflicts, and preview are available in Build.
- [ ] Test and Growth workspaces can be created and promoted.
- [ ] Calendar, PageSpeed, monitoring, and price integrations fail visibly when disconnected.
- [ ] Usage, quota, and cost data are understandable.
- [ ] Facts, profile preferences, candidates, corrections, clusters, and audit records have clear ownership.
- [ ] Mobile layouts expose the same essential workflows.
- [ ] Planned features are labeled as planned rather than presented as shipped.

---

## 25. Source Map

The implementation surfaces this guide summarizes are primarily located in:

- `frontend/app/components/AppShell.jsx`
- `frontend/app/components/WorkspaceChatPanel.jsx`
- `frontend/app/components/tabs/`
- `frontend/app/components/notebooks/`
- `frontend/app/components/workbench/`
- `backend/api/routes/`
- `backend/agents/`
- `backend/eo/`
- `docs/`
- `MOBILE_PLAN.md`
- `DEFERRED.md`
- `graphify-out/GRAPH_REPORT.md`
- `minime_technical_roadmap.md`
- `minime_server_management_guide.md`

The API, architecture, code, data, tests, and roadmap pages in MiniMe Book remain the authoritative deep technical references. This guide is the user-facing feature layer that connects those references into one manual.
