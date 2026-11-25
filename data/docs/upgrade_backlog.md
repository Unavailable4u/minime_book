# Upgrade Backlog: Features To Build Later (an incremental register)

**Written:** 2026-11-24. **Appendix C** of the book. **Repos:** `minime_book` (this file lives in `data/docs/upgrade_backlog.md`); `MiniMe` read at commit `cd0bc23` (2026-11-24, after the whole fix series `SX-01` to `SX-29`).

This file is the one place where every feature you might build later is written down: **what** it is, **where it came from** (a repo, a plan section, or "my idea"), **why**, **where in the code** it would go, **how** it would be added, and **when it counts as done**. It grows by small patches. Nothing in it has been built; an entry is a decision aid and a work order, not a promise.

**How to read it.** Section 1 is the short table you scan. Each row has an entry with the same ID in the *Batch* sections at the end of the file. A feature moves through the statuses in section 4: it starts as `candidate`; you decide `accepted`, `parked` or `dropped`; it later becomes `building` and `done`.

**What is not here.** The MiniMe fix series (`SX-01` to `SX-29`, all applied) is finished and is not repeated. Section 5 shows where each part of the original upgrade plan went, so you can see that nothing was lost. Section 6 lists what was considered and deliberately not made into a feature, with the reason.

**Sections 0, 1 and 2 are generated** from the entries by `python scripts/check_backlog.py --write`. Never edit them by hand; edit an entry and run the script.

## 0. At a glance

*Generated from the entries by `python scripts/check_backlog.py --write`. Do not edit by hand.*

**87 features** in 4 batches: 84 candidate · 0 accepted · 0 building · 0 done · 3 parked · 0 dropped.

| Product | candidate | accepted | building | done | parked | dropped | Total |
|---|---|---|---|---|---|---|---|
| MiniMe | 42 | 0 | 0 | 0 | 1 | 0 | 43 |
| M2C | 23 | 0 | 0 | 0 | 1 | 0 | 24 |
| Menux | 9 | 0 | 0 | 0 | 1 | 0 | 10 |
| Shared | 7 | 0 | 0 | 0 | 0 | 0 | 7 |
| Book | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| **All** | **84** | **0** | **0** | **0** | **3** | **0** | **87** |

## 1. Register

*Generated from the entries by `python scripts/check_backlog.py --write`. Do not edit by hand.*

| ID | Feature | In short | Product | Source | Size | Status | Batch |
|---|---|---|---|---|---|---|---|
| UB-001 | Move the web app from Next.js 14 to a supported line | Next 14.2.35 gets no more fixes; move to 16.x with React 19, new Sentry and Mermaid, before the accepted-risk lines expire. | MiniMe | Plan S2, Spec U3, fix guide section 7 | L | candidate | B01 |
| UB-002 | Decide Pillow against moviepy, then act | 59 Pillow findings are accepted only because moviepy needs Pillow below 12; pick keep, test Pillow 13, or drop moviepy. | MiniMe | Fix guide D-1, Spec 2.1 | M | candidate | B01 |
| UB-003 | Move e2b, bracex and wcmatch together | The wcmatch fix needs e2b 2.64 and bracex 3.2; three pins must move as one. | MiniMe | Fix guide D-2 | M | candidate | B01 |
| UB-004 | Put the Caddy config in the repo and set the edge limits | The proxy config is not in either repo; commit it, then add a body-size limit, HSTS and edge rate limits. | MiniMe | Spec U4 and U5.4, Plan S3 and S5 | M | candidate | B01 |
| UB-005 | Block cloud-metadata and link-local addresses at the host firewall | Defence in depth for the SSRF fix: the backend container cannot reach 169.254.169.254 even if a check has a bug. | MiniMe | Spec U1.7, Plan S1, fix guide section 6 | S | candidate | B01 |
| UB-006 | Run URL fetches behind an egress proxy or in the sandbox | Optional extra layer: do the risky fetching in the E2B sandbox or behind a proxy that enforces the same rules. | MiniMe | Plan S1 (defence in depth) | M | candidate | B01 |
| UB-007 | Audit every other server-side fetch of a user-influenced URL | Find any remaining fetch whose URL comes from a user, a search result or a server reply, and route it through url_guard. | MiniMe | Plan S1 ("other fetchers"), MCP spec guidance [W] | M | candidate | B01 |
| UB-008 | Per-user ingest quotas | One user cannot run unlimited clips, videos, imports, PDFs and voice notes: a quota that answers 429 with Retry-After. | MiniMe | Spec U5.5, Plan S5 | M | candidate | B01 |
| UB-009 | Daily ingest cost cap tied to the usage ledger | Refuse an ingest when the user's pool or day budget is spent, so ingestion cannot push COGS past the 45% target. | MiniMe | Spec U5.6 | M | candidate | B01 |
| UB-010 | Cap voice length before transcribing | Only file size is capped on voice notes; refuse long recordings before faster-whisper starts. | MiniMe | Spec U5.3, fix guide (patch 23 left unused) | S | candidate | B01 |
| UB-011 | Re-set the size caps with a cost model | The caps from the fix series are placeholders; set them from measured cost. | MiniMe | Fix guide D-3 | S | candidate | B01 |
| UB-012 | Turn the report-only CSP into an enforced one | Collect violation reports for a week, fix them, then enforce the policy from SX-29. | MiniMe | SX-29 follow-up, Plan S3, Spec U4.4 | M | candidate | B01 |
| UB-013 | A small blocking promptfoo gate | 10 to 20 deterministic must-pass cases that fail CI, while the broad LLM suite stays advisory. | MiniMe | Plan S7.4, Spec U2.4 | M | candidate | B01 |
| UB-014 | Run the promptfoo red-team with a two-tenant provider | Probe prompt injection, cross-tenant leaks and memory poisoning against staging with synthetic data only. | MiniMe | promptfoo red-team docs [W], promptfoo (MIT, read at `4a30804`) [R], Plan 3.2, Spec T5 | M | candidate | B01 |
| UB-015 | First Strix run on staging | An AI pentest agent tries to read tenant A's data from tenant B through every route and tool. | MiniMe | Strix (Apache-2.0, read at `9ed84f9`) [R], Plan 3.3, Spec T6 | M | candidate | B01 |
| UB-016 | Property tests with Hypothesis | Random-input tests for the pure engines: manufacturability checks, the URL guard and the shell parser. | Shared | Plan 3.4, Spec T3, Hypothesis (MPL-2.0, read at `b9d568c`) [R] | M | candidate | B01 |
| UB-017 | Nightly API fuzzing with Schemathesis | Fuzz every FastAPI route, with and without auth, and fail on any 5xx or schema violation. | MiniMe | Plan 3.1 and 3.4, Spec T4, Schemathesis (MIT, read at `15b71f5`) [R] | M | candidate | B01 |
| UB-018 | Add cost-per-task and web-product scenarios to the load harness | Extend the device load harness planned in MG-B00 with notebook, PDF and runaway-loop scenarios, measured as cost per task. | Shared | Plan 3.5, Spec T7, Appendix A `MG-B00`, Locust (MIT, read at `5084aa1`) [R] | M | candidate | B01 |
| UB-019 | A practice lab with Django and nginx on your own machine | Learn the fuzz, load and pentest tools on throwaway targets before pointing them at staging. | Shared | Spec T8 | S | candidate | B01 |
| UB-020 | Pre-audit package for the daemon | Hand the auditor the hostile-URL table, the red-team corpus, Strix reports, daemon tests and a one-page threat model. | MiniMe | Plan S8, Spec U8 | M | candidate | B01 |
| UB-021 | SBOM on release | Produce a software bill of materials for the backend and frontend when you cut a release. | MiniMe | Plan S7.5 | S | candidate | B01 |
| UB-022 | Pin scanner binaries and images by digest | Tighten the supply chain further: pin every downloaded tool and Docker image by digest or hash. | MiniMe | Plan S7.3 | S | candidate | B01 |
| UB-023 | Lurkr as an advisory CI step | A static, offline scanner for risky agent capabilities in workflows and tool code, run as review items only. | MiniMe | Lurkr [W] | S | candidate | B01 |
| UB-024 | Dependabot for the Docker images | Add a docker entry to Dependabot, but only if GitHub finds the non-standard Dockerfile names. | MiniMe | Fix guide D-4 | XS | candidate | B01 |
| UB-025 | Security headers for the book site | Add nosniff, Referrer-Policy and a frame rule to the book's vercel.json. | Book | Spec U4.5 | XS | candidate | B01 |
| UB-026 | Record the fix patch guide in the book | Keep the SX series guide as a book appendix so the history of what was fixed is not lost. | Book | the MiniMe fix patch guide | S | candidate | B01 |
| UB-027 | Refresh the book after the fixes and upgrades | The book's census and graph describe commit 3727ae3; refresh them after the fix series and again after bigger upgrades. | Book | Fix guide section 7, `UPDATING.md` | M | candidate | B01 |
| UB-028 | Verify-on-stop in the agent loop | If the model edits files and then stops without running a test or build, ask it once or twice to verify first. | M2C | Spec M1, Plan 4.2, Hermes `agent/verification_stop.py` and `agent/turn_stop_gates.py` (MIT, read at `c84e8d7f`) [R] | M | candidate | B01 |
| UB-029 | Skills loader for M2C | Load SKILL.md folders (name and description only at start), enforcing allowed-tools as a ceiling. | M2C | Spec M2, Agent Skills standard [W], M2C plan item C14 | M | candidate | B01 |
| UB-030 | Add promptfoo's coding-agent risk categories to the Q07 corpus and list the gaps | Q07 is already planned; take promptfoo's coding-agent risk categories and write rows only for what the current tests miss. | M2C | Spec M3, Plan 4.5, M2C build plan Q07, Appendix A `MG-Z03`, promptfoo (MIT, read at `4a30804`) [R] | S | candidate | B01 |
| UB-031 | Golden tasks for the coding agent | Ten past bug-fix commits turned into tasks with a failing test, run with a fixed budget, to get your own pass rate and cost. | M2C | Spec M4, promptfoo (MIT, read at `4a30804`) [R] | M | candidate | B01 |
| UB-032 | Local MCP client for M2C | Run MCP servers under M2C's sandbox and network policy, with approval-time hashing of each tool definition. | M2C | Spec M5, Plan S6 and 4.3 and 4.4, M2C plan item C23 | L | candidate | B01 |
| UB-033 | Deferred tool loading with search over tool specs | When an MCP server exposes many tools, keep their descriptions out of the prompt and find them on demand. | M2C | Codex and Hermes (Plan 4.2), Hermes `tools/tool_search.py` (MIT, read at `c84e8d7f`) [R] | M | candidate | B01 |
| UB-034 | Offer codebase-memory-mcp as an optional local server | A code knowledge-graph MCP server the user can install themselves, running device-local under the sandbox. | M2C | codebase-memory-mcp [R] | S | candidate | B01 |
| UB-035 | Rehearse MCP attacks against M2C with Argus | Use a red-team tool with a built-in vulnerable demo agent to rehearse tool-poisoning and rug-pull attacks. | M2C | Argus [README] | S | candidate | B01 |
| UB-036 | Stuck detection beyond identical failures | Warn when the same call repeats even if it succeeds, then ask a model to self-check after many turns; let the user decide. | M2C | Gemini CLI and OpenCode (Plan 4.2), Gemini CLI `packages/core/src/services/loopDetectionService.ts` (Apache-2.0, read at `60f8082`) [R] | M | candidate | B01 |
| UB-037 | Mid-turn user steering | Let the user add a message while the agent works, inserted behind an anti-injection marker. | M2C | Hermes (Plan 4.2), Hermes `agent/prompt_builder.py` (MIT, read at `c84e8d7f`) [R] | M | candidate | B01 |
| UB-038 | An instruction-hierarchy contract in the system prompt | One ranked list of instruction sources (user, repo, skills, MCP, external data last) instead of scattered prohibitions. | M2C | Mistral Vibe (Plan 4.2), Vibe `vibe/core/prompts/cli_ml4_2026-10_v2.md` (Apache-2.0, read at `fb7511a`) [R] | S | candidate | B01 |
| UB-039 | Observe mode before enforce mode for new policy rules | Ship each new rule in a log-only mode first, record what it would have blocked, then enforce. | M2C | Prismor (Plan 4.2) | M | candidate | B01 |
| UB-040 | Check whether sandbox denials are already stored | Before building a violation log, read what `events.py` and the network proxy callback already keep. | M2C | Spec M6 | S | candidate | B01 |
| UB-041 | Signed, narrowing grants for subagents | Each handoff to a subagent can only narrow what it may do: tools, argument limits, expiry. | M2C | Tenuo [R] | L | candidate | B01 |
| UB-042 | Compaction that re-injects the task goal, with a lossless log | When the context is compacted, put the original goals back in; keep the full transcript so only the model's view shrinks. | M2C | Mistral Vibe, Gemini CLI, UNCUT, OpenHands (Plan 4.2), Gemini CLI `prompts/snippets.ts` and `context/chatCompressionService.ts` (Apache-2.0, read at `60f8082`) [R], Hermes `agent/context_compressor.py` and `context_compressor_prompt_rules.py` (MIT, read at `c84e8d7f`) [R] | M | candidate | B01 |
| UB-043 | An independent verifier context and step-graph validation | A second, separate model context checks the result; a multi-step plan is validated before any step starts. | M2C | zeroshot [R] | L | candidate | B01 |
| UB-044 | Plan mode that is structural, plus a spec-first interview | In plan mode only a plan file is writable; add a spec-first interview that ends in checkable acceptance criteria. | M2C | Mistral Vibe, Ouroboros, Nightshift (Plan 4.2) | M | candidate | B01 |
| UB-045 | A precision-first review command | A diff reviewer that gives line-level comments and favours few, correct findings over many. | M2C | open-code-review [R], Strix `skills/scan_modes/diff.md` (Apache-2.0, read at `9ed84f9`) [R], Plan 4.2 | L | candidate | B01 |
| UB-046 | Add a hash chain to the local event store | A previous-hash and entry-hash on each event plus a verify function; the M2C plan already names MiniLocker's chain.py as the model. | Shared | M2C build plan C02 and section 11.6 (MiniLocker `ledger/chain.py`, your own project), Spec 6.1; ZizkaDB (idea only) | S | candidate | B01 |
| UB-047 | Menux memory store with sources, validity and FTS5 | One migration for sources, memories with valid-from and valid-to, dependencies and a full-text index. | Menux | Spec 6.1, Plan 5.2 (Mnemosyne, Graphiti/Zep, mempalace, claude-mem) | M | candidate | B01 |
| UB-048 | Trust rule and a review queue for new memories | Anything from a web page, tool output or an imported CLAUDE.md enters as an untrusted candidate; only a user action promotes it. | Menux | Spec 6.1, Plan 5.2 (MemoSync, promptfoo memory-poisoning plugin), Gemini CLI `agents/skill-extraction-agent.ts` (Apache-2.0, read at `60f8082`) [R] | M | candidate | B01 |
| UB-049 | Correcting a source retires its dependents, and deletes cascade | Fix or delete a source and everything derived from it leaves retrieval but stays readable in a history view. | Menux | Spec 6.1, Plan 5.2 (Mnemosyne, agentmemory) | M | candidate | B01 |
| UB-050 | Show the working memory before a task, and report what was used | Before each task list the memories the agent intends to use with a reason; after it, show which were followed. | Menux | Spec 6.1, Plan 5.2 (MemoSync UX) | M | candidate | B01 |
| UB-051 | Retention scores and hot, warm and cold tiers | Decay plus access boost to prune memory. Both documents say to skip this until volume is measured. | Menux | agentmemory (Plan 5.2), Spec 6.1.6 | M | parked | B01 |
| UB-052 | Learned workflows modelled on webcmd | Three levels: live browser control, a remembered sitemap of pages and actions, and compiled workflows for repeatable tasks. | Menux | webcmd (Apache-2.0 as reported) [R], Plan 5.3 | L | candidate | B01 |
| UB-053 | crawl4ai as an optional web reader | A self-hostable crawler to Markdown, only after the licence record and with every URL through url_guard rules. | Menux | crawl4ai (Apache-2.0 as reported) [R] | S | candidate | B01 |
| UB-054 | A capability-listing command | A `menux capabilities` style command that tells the user what the agent can do, borrowed from Agent-Reach. | Menux | Agent-Reach (UX idea only) [R] | XS | candidate | B01 |
| UB-055 | A Blender skill pack | Export and optimisation checklists from a 94-skill Blender pack, as a Menux skill pack. | Menux | blender-skills by arjun988 (MIT as reported) [R] | M | candidate | B01 |
| UB-056 | An independent claim-check pass for research reports | After a report is drafted, a separate model call checks each claim against its cited source and flags unsupported ones. | MiniMe | Spec P1, Plan 6.1 (hyperresearch, Research Toolkit, Storm and GPT Researcher as references) | M | candidate | B01 |
| UB-057 | Generation that survives a closed tab | A notebook or course generation keeps running on the server if the user closes the browser. | MiniMe | OpenMAIC [R], Plan 6.2 | L | candidate | B01 |
| UB-058 | Project-based learning with an AI tutor, milestone by milestone | A guided project mode where a tutor checks progress at each milestone. | MiniMe | OpenMAIC [R], Plan 6.2 | L | candidate | B01 |
| UB-059 | Chat about any slide element | Select an element on a generated slide and ask about it. | MiniMe | OpenMAIC [R], Plan 6.2 | M | candidate | B01 |
| UB-060 | Course-level undo | Undo a whole generated course step, not only the last edit. | MiniMe | OpenMAIC [R], Plan 6.2 | M | candidate | B01 |
| UB-061 | Export to PPTX and HTML | Let users download generated slides or notebooks as PowerPoint and standalone HTML. | MiniMe | OpenMAIC [R], Plan 6.2; slide-generation references in UB-080 | M | candidate | B01 |
| UB-062 | A knowledge base with @-mentions | Attach sources to a workspace and mention them by name in chat. | MiniMe | OpenMAIC [R], Plan 6.2 | M | candidate | B01 |
| UB-063 | Use OpenMAIC's published advisories as a free test checklist | Its security advisory list names the classes of bug a study app has; check each against MiniMe. | MiniMe | OpenMAIC advisories [R] | S | candidate | B01 |
| UB-064 | A repeatable skills pipeline: select, scan, rewrite, evaluate, label, regress | A written process and a small scanner so every seed skill is vetted the same way before it is kept. | Shared | Plan section 7, ponytail (method) [README], Hermes `tools/skills_guard.py` (MIT, read at `c84e8d7f`) [R] | M | candidate | B01 |
| UB-065 | Growth tab seed skills from marketingskills | Rewrite a marketing skill set as seeds for the Growth tab roles, after confirming those roles exist. | MiniMe | marketingskills (MIT as reported), Spec P2, Plan 6.3 | M | candidate | B01 |
| UB-066 | Research and notebooks seeds from scientific-agent-skills | Pick a handful of the 177 science skills by actual usage, rewrite them as seeds. | MiniMe | scientific-agent-skills [R], Plan section 7 | M | candidate | B01 |
| UB-067 | M2C built-in skills and a behaviour baseline | Rewrite skills from anthropics/skills, mattpocock/skills, addyosmani/agent-skills and one Karpathy-style CLAUDE.md as M2C built-ins. | M2C | anthropics/skills, mattpocock/skills, addyosmani/agent-skills, andrej-karpathy-skills (MIT as reported) | M | candidate | B01 |
| UB-068 | Security reviewer prompts and a vetted security skills library | Turn Strix's playbooks into security_reviewer prompts and the 818 community security skills into a reference library. | MiniMe | Strix playbooks (Apache-2.0, `LICENSE` read at `9ed84f9`), Anthropic-Cybersecurity-Skills (community, not affiliated) | M | candidate | B01 |
| UB-069 | Role ideas from gstack and BMAD | Take process ideas such as a security-officer role using OWASP and STRIDE; do not import in bulk. | MiniMe | gstack, BMAD-METHOD [R] | S | candidate | B01 |
| UB-070 | An optional writing-quality pass from humanizer | A style pass that removes AI-writing tells, for quality and not for concealment. | MiniMe | humanizer [R] | S | candidate | B01 |
| UB-071 | The overhang and draft check in the mechanical engine | The one manufacturability check the code itself says is missing. | MiniMe | Spec P3 (the module's own docstring) | M | candidate | B01 |
| UB-072 | Compare text-to-cad's per-process rules with yours | Read its machining, sheet-metal, moulding and 3D-printing rule sets and adopt the rules you lack. | MiniMe | text-to-cad (MIT as reported) [R], Plan 6.5 | S | candidate | B01 |
| UB-073 | Spike: can build123d replace FreeCAD inside the E2B template? | Measure install size, cold start, STEP and STL output and determinism. | MiniMe | text-to-cad (build123d route) [R], Spec P3 | M | candidate | B01 |
| UB-074 | An "analyse this part" stress check | A possible future capability using CalculiX-style stress analysis. | MiniMe | text-to-cad (stress checks via CalculiX) [R], Plan 6.5 | L | parked | B01 |
| UB-075 | Cost experiments before adopting any compressor or router | Replay real traces with and without output compression, terse agent messages and cheaper models, and compare cost and quality. | Shared | Spec P4, Plan 6.6 (headroom, caveman, Mixdog), Gemini CLI `routing/strategies/numericalClassifierStrategy.ts` (Apache-2.0, read at `60f8082`) [R] | M | candidate | B01 |
| UB-076 | Design and build techniques from impeccable, taste-skill and ui-ux-pro-max | Adopt techniques (not code) such as a command vocabulary of polish, bolder, critique and audit, and test them. | MiniMe | impeccable, taste-skill, ui-ux-pro-max-skill [README] | M | candidate | B01 |
| UB-077 | Screenshot-to-code for the wireframe flow | Use ideas from screenshot-to-code to turn an uploaded image into a first wireframe. | MiniMe | screenshot-to-code [README] | M | candidate | B01 |
| UB-078 | A diagram generator from diagram-design | One self-contained HTML plus SVG file per diagram, across many diagram types. | MiniMe | diagram-design (51 types as reported), archify (already in the book pipeline) [README] | M | candidate | B01 |
| UB-079 | Spike: HTML to deterministic video with hyperframes | Test whether hyperframes could replace moviepy in the video overview builder. | MiniMe | hyperframes [README] | M | candidate | B01 |
| UB-080 | Study slide-generation references | Read open-slide and ppt-master for ideas on generating slides. | MiniMe | open-slide, ppt-master [README] | S | candidate | B01 |
| UB-081 | Cross-check the MG-Z10 spike with rust-anything | Use rust-anything to record, diff, fuzz and shadow the Rust redaction port against Python, as a second check beside the vectors. | M2C | rust-anything (MIT, read at `b5025d4`), Appendix A `MG-Z04` and `MG-Z10`, trial of 2026-11-24 | M | candidate | B02 |
| UB-082 | Port only profiled hot functions with fast-anything | A Python-staying alternative to a rewrite: profile a real workload, port only the measured hot functions, prove them on recorded calls. | Shared | fast-anything (MIT, read at `ccf46b4`), Appendix A `MG-Z10` (Python alternatives) and `MG-B01`, trial of 2026-11-24 | M | candidate | B02 |
| UB-083 | Break the import cycle so m2c units can be bridged one by one | The tool saw about 20,500 lines in one import cycle; break it only if you choose the unit-by-unit bridge instead of the rebuild. | M2C | rust-anything `analyze` on m2c (trial of 2026-11-24, its report read) | M | parked | B02 |
| UB-084 | Record what a run created, so undo and approvals touch only that | A per-run list of the objects an automation created, so cleanup and any approval exemption apply only to things the run itself made. | Menux | Strix test-object registry (Apache-2.0, read at `9ed84f9`) [R], Menux feature guide sections 6.1 and 7.5 | S | candidate | B03 |
| UB-085 | Switch off core dumps and debugger attach for the M2C client at start | Set no-core-dump and no-same-user-debugger-attach for the M2C client before it handles a secret (Linux and macOS), as Codex does. | M2C | Codex `codex-rs/process-hardening/src/lib.rs` (Apache-2.0, read at `06f334a`) [R] | XS | candidate | B04 |
| UB-086 | Session goal mode with a token budget and a no-progress stop | One goal the agent works on across turns; it stops at a token budget, after 3 turns without progress, or after 3 turns of failed tools. | M2C | Mistral Vibe `vibe/app_server/_goal_engine.py` (Apache-2.0, read at `fb7511a`) [R] | M | candidate | B04 |
| UB-087 | One helper that frames text the model must treat as data | Steering messages, compaction summaries and goal objectives all need the same escaping, marker and look-alike handling; write it once. | M2C | my idea, from Hermes `agent/prompt_builder.py` (MIT, `c84e8d7f`), Gemini CLI `prompts/snippets.ts` (Apache-2.0, `60f8082`) and Vibe `_goal_engine.py` (Apache-2.0, `fb7511a`) [R] | S | candidate | B04 |

## 2. Batches

*Generated from the entries by `python scripts/check_backlog.py --write`. Do not edit by hand.*

| Batch | Date | What it added | Features | IDs |
|---|---|---|---|---|
| B01 | 2026-11-24 | Upgrade plan and verified spec of 21 Nov 2026, minus the finished SX series | 80 | UB-001 to UB-080 |
| B02 | 2026-11-24 | rust-anything and fast-anything, from a trial on m2c | 3 | UB-081 to UB-083 |
| B03 | 2026-11-26 | Review of promptfoo, Strix, Hypothesis, Schemathesis and Locust | 1 | UB-084 |
| B04 | 2026-11-26 | Review of gemini-cli, hermes-agent, mistral-vibe and codex | 3 | UB-085 to UB-087 |

## 3. How to add features (the patch recipe)

**For a Claude session that has only this file and the repo link.** The person works on Windows, reviews other repos by hand, and then asks for one patch that adds what they decided to keep. One patch, one batch.

**Session start (always)**

1. `git clone https://github.com/Unavailable4u/minime_book.git && cd minime_book && git log -3 --oneline`. Work from the current default-branch HEAD.
2. Run `python scripts/check_backlog.py --check`. It must pass **before** you change anything. If it does not, stop and say so.
3. Run `python scripts/check_backlog.py --next-id` for the next free ID and `--list` to see what exists. **IDs are never reused**, even for a dropped feature.

**What to ask the person for, per feature** (do not invent any of it)

- **Source**: a repo URL (and the commit or release you read), a web page, a plan section, or the words `my idea`.
- **What it should do** in their words, which product it belongs to (`MiniMe`, `M2C`, `Menux`, `Shared`, `Book`), and any decision they have already made.

**Per feature, do this**

1. **If the source is a repo: clone it and read its `LICENSE` yourself.** Add or update its row in section 7 (`Reported licence`, `Checked`). Code or text may be copied only if the licence allows it for a paid product; otherwise write `ideas only`. A licence taken from a README or from the earlier plan is `reported`, not `checked`.
2. **Check the current code.** For a MiniMe, M2C or Menux feature, clone `MiniMe`, `grep` for the files you name, and say what already exists. If something similar is built, say so in **Notes.** or do not add the feature (add a row to section 6 instead). Tag what you checked `[V✓]`.
3. **Check this file and the other chapters.** Search the register and section 6 for the same idea, and `grep` the guides in `data/docs/` for it and for their work-package IDs (`MG-*` in Appendix A, `PV-*` in Appendix B, the `C`, `L`, `Q`, `S` items of the M2C build plan, the Menux guide). A duplicate is an error: reference the existing item, or extend the old entry, instead of adding a second one.
4. **Write the entry** with the template below. Keep it under about 30 lines. Say plainly what is a design idea that nobody has run.
5. **Append** a new `## Batch Bnn (YYYY-MM-DD): what this batch added` section **at the end of the file** (next batch number, today's date), with the entries below it in ID order. A status change or a new source row for an old feature does not need a batch: edit it in place and use `--set-status`.
6. Run `python scripts/check_backlog.py --write`, then `--check`, then `python scripts/test_check_backlog.py`. `--write` rebuilds sections 0, 1 and 2 (the table, the counts, the batch list) from your entries. **Put a blank line before every list** (`--check` refuses a list that follows text directly: the book's builder would show it as run-on text).
7. **Rebuild the reader page and the indexes** (needs `pip install markdown==3.11.2`, only for this step): `python scripts/build_backlog_page.py --write`, then `python scripts/build_index.py`, then `python scripts/build_status.py`. Every change to this file, even a status change, needs the first command; `check_backlog.py --check` fails when `doc-upgrade-backlog.html` was built from an older version of the file.
8. Make the patch (it carries the Markdown, the page and the regenerated `data/index/` files):

```bash
git switch -c ub-bNN-short-name
git add -A
git commit -m "UB-BNN: <what this batch adds>" -m "<features and sources, plain words>" -m "Tested: <commands and results>"
git format-patch -1 --stdout > UB-BNN_short-name.patch
```

9. **Prove it applies:** clone fresh, `git am` the patches in order, and run the three commands of step 6 and every command of `.github/workflows/site-check.yml` again there. Apply with `git am` (which commits), not `git apply`: two book tests fail while a chapter page has uncommitted changes.

**The entry template**

````markdown
### UB-nnn: Short feature title (M)

> One line for the register table (140 characters at most, no "|").

**Product** MiniMe · **Source** repo or plan section or "my idea" · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓]

**What.** What it is, in plain words.

**Why.** The problem it solves, and what it costs not to have it.

**Where.** The files and symbols it touches, as found today.

**How.** Numbered steps. Small enough that each step could be one patch.

**Done when.** Checks that someone else could run.

**Notes.** Optional: licence limits, risks, open questions, deadlines. Required when the status is parked or dropped.
````

`Depends` is `—` or feature IDs (`UB-012, UB-013`). `Decision` is `none` or the decision that must be made first. The separator between the fields is a middle dot with a space on each side.

**Rules for every batch**

- Edit only this file, `scripts/check_backlog.py` and its test when the shape itself changes. **Do not touch** the other chapters, the generated `doc-*.html` pages, `data/index/` or `content/nav.json`: those come from the book's own build.
- Do not claim a fact you did not read or run. Anything carried over from another document keeps its original tag, or `[S]`.
- Never put a secret, token or real user data in an entry. Line endings are LF.
- **Another chapter** may be edited only when a finding changes what it says (for example a new caveat in an existing work package). Edit its `.md` and its `doc-*.html` with the same wording, using exact-match replacements that fail when the text is missing, **and recompute the banner** of that page (word count, read time, section count; `scripts/build_backlog_page.py` shows the formulas and reproduces Appendix B's page byte for byte). Run the site checks. Say in the report that the HTML was edited by hand and not produced by the external builder. A feature that is already planned in a chapter is not added here.
- `llms.txt` and `data/summary.md` carry **no counts** of features or batches (the generated tables hold them), so a new batch never makes them stale.
- Do not implement anything. When a feature is accepted and its turn comes, it gets its own patch guide, like the `SX` series did.
- Report with each patch: `Patch` · `Base commit` · `Features added (ID and title)` · `Sources and licences read` · `What already existed in the code` · `Commands run and results` · `Not run or not verified` · `Decisions needed from you`.

**Changing a decision.** Run `python scripts/check_backlog.py --set-status UB-nnn accepted --note "why"`. It edits the entry, adds a row to section 8 and regenerates the tables. Dropping or parking needs a reason.

**The reader page.** Chapters (`doc-*.html`) are normally produced by the book's external builder, which this repository does not contain. For this appendix, `scripts/build_backlog_page.py` does the same job: it converts this file with Python-Markdown (tables, fenced code, table of contents), takes the page frame from an existing chapter page, and writes `doc-upgrade-backlog.html`. Run against Appendix B's source it gives that page byte for byte, which is how its recipe was checked. The two aggregate pages `journey.html` and `tables.html` are not touched: they come from the external builder, so they do not list this appendix until it runs.

## 4. Field vocabulary and rules

**Status**

| Status | Meaning |
| --- | --- |
| `candidate` | Written down. Not decided. Everything starts here. |
| `accepted` | You decided to build it. It waits for its turn. |
| `building` | Patches for it are being written or applied. |
| `done` | Built and applied. Add the patch names to **Notes.** |
| `parked` | Good idea, wrong time, or blocked. **Notes.** says why and what would reopen it. |
| `dropped` | Decided against. **Notes.** says why, so it is not proposed again. |

**Product:** `MiniMe` (the web product and its backend), `M2C` (the coding agent client and its server side), `Menux` (the automation agent), `Shared` (touches more than one of them, or the tooling around them), `Book` (this repository).

**Size** (a rough guess, as in the fix guide): `XS` under an hour, `S` under a day, `M` a few days, `L` one to two weeks, `XL` more. When unsure, take the larger.

**Evidence tags.** `[V✓]` read or run by whoever wrote the entry in the code at the commit named in the intro; `[V]` read in the code by the earlier plan or spec (carried over, not re-checked); `[T]` run by them; `[R]` read in a cloned reference repo; `[W]` taken from a web page; `[README]` README only, not studied; `[GK]` general knowledge, a lead to confirm; `[U]` a design nobody has run; `[S]` carried from an earlier document unchecked.

**Licence rule.** The earlier spec states that the reference repos were not re-read and that licences are unverified. Before any code or text is copied from a source, read its `LICENSE` and record it in section 7. AGPL and non-commercial sources give **ideas only**. The one hard rule: never use `openclaude` or leaked Claude Code source in any form; learn Claude Code's features from its public documentation.

## 5. Where the original upgrade plan went

The "upgrade plan" (21 Nov 2026) and its "verified spec" were split three ways. This table is the map.

| Plan or spec item | Where it went |
| --- | --- |
| Plan S1, spec U1: SSRF guard for web clip, video ingest, datasheets | **Done** in MiniMe as `SX-04` to `SX-08` (`backend/utils/url_guard.py`). Still open: UB-005, UB-006, UB-007 |
| Plan S6, spec U7: MCP client hardening | **Done** as `SX-24` (URL rules), `SX-25` (injection guard), `SX-26` (re-approve on change), `SX-27` (no user token in headers). The M2C side is UB-032 |
| Spec U2: Python bumps (groups A, B, C) | **Done** as `SX-11` to `SX-15`. Pillow is UB-002, wcmatch and e2b are UB-003 |
| Spec U2: audit job, allow-list, Dependabot, Python 3.12, README | **Done** as `SX-09`, `SX-10`, `SX-17`, `SX-02`, `SX-01`. Docker Dependabot is UB-024 |
| Spec U2.4, plan S7.4: blocking promptfoo subset | UB-013 |
| Plan S7: SBOM, digest pins, Lurkr | UB-021, UB-022, UB-023 |
| Plan S2, spec U3: Next.js 14 to 16 | UB-001. The lockfile-only `npm audit fix` is **done** as `SX-16` |
| Plan S3, spec U4: headers and CSP | **Done** as `SX-28` and `SX-29` (report-only). Enforcing is UB-012; the Caddy file and edge limits are UB-004; the book's `vercel.json` is UB-025 |
| Plan S4, spec U6: avatar `innerHTML` | **Done** as `SX-03` |
| Plan S5, spec U5: upload limits and quotas | **Done**: size caps as `SX-20`, `SX-21`, `SX-22`. Open: UB-008, UB-009, UB-010, UB-011 |
| Plan S8, spec U8: pre-audit package for the daemon | UB-020 |
| Plan section 3, spec section 4: test program T3 to T8 | UB-016 (T3), UB-017 (T4), UB-014 (T5), UB-015 (T6), UB-018 (T7), UB-019 (T8) |
| Plan section 4, spec section 5: M2C | UB-028 to UB-045 |
| Plan 5.2, spec 6.1: Menux memory | UB-046 to UB-051 |
| Plan 5.3: browsing | UB-052, UB-053, UB-054 |
| Plan 5.1 desktop control, spec 6.2 | Already in the Menux plan (decision D35, item R05); not a new feature |
| Plan 6.1, spec P1: research claim check | UB-056 |
| Plan 6.2: OpenMAIC patterns | UB-057 to UB-063 |
| Plan 6.3, section 7, spec P2: skills | UB-064 to UB-070 |
| Plan 6.4: build and design | UB-076, UB-077, UB-078 |
| Plan 6.5, spec P3: mechanical engine | UB-071 to UB-074 |
| Plan 6.6, spec P4: cost experiments | UB-075 |
| Plan 6.7: media | UB-079, UB-080 |
| Fix guide section 7, "left for later": Caddy limits, firewall, quotas | UB-004, UB-005, UB-008, UB-009 |
| Fix guide section 7: the book repo | UB-026, UB-027 |

## 6. Considered, not added

| Item | Why it is not a feature | Revisit when |
| --- | --- | --- |
| Plan Appendix A.1, A.2: the sketched SSRF guard | Replaced: the spec found the sketch allowed NAT64 and IPv4-compatible forms; `SX-04` and `SX-05` built the checked version on `urllib3` | never |
| Truncation-poisoning guard (idea from Pi) | Already built: `truncated_arguments` is a refusal message in `backend/codeagent/loop.py` [V✓] | never |
| Environment scrubbing before commands (Gemini CLI) | Already built: `m2c/src/m2c/secrets/env.py`, eight layers including a value scan [V✓] | never |
| Protected paths read-only (Codex) | Already built: the bubblewrap profile makes `.git`, `.m2c` and shell start-up files read-only [V✓ `sandbox/profile.py`] | never |
| Exact unique-match edits (Mistral Vibe) | Already built: `edit_file` fails with `string_not_unique` [V✓ `tools/files.py`] | an LLM "edit fixer" only if failure data shows the need |
| Identical-failure stop, step limit, tool-call budget | Already built in `backend/codeagent/loop.py` [V✓]. The extension is UB-036 | — |
| Domain allow-list, folder trust, network proxy blocklist | Already built (`netpolicy.py`, `trust/fingerprint.py`, `netproxy.py`) [V✓ files exist] | — |
| `agent-desktop` for desktop control | Already planned in the Menux plan (D35, R05) | R05 records the licence |
| `browser-use` | Study only: it has the model write Python against the browser, which fights tiered approvals unless sandboxed | a sandboxed design exists |
| `Agent-Reach` login copying | Avoid the pattern (copies your browser logins into its own profile). Only its capability listing is kept: UB-054 | never |
| `openclaude`, any leaked Claude Code source | Hard rule: never used in any form | never |
| `nginx` | You use Caddy | never |
| `x64dbg-mcp-server` | Not relevant (a debugger plugin; an example of GUI-as-MCP) | never |
| `OpenMontage`, `openvid`, `OpenViking`, `ZizkaDB`, `academic-research-skills` | AGPL or non-commercial licences as reported: ideas only, no code | a licence is checked and fits |
| `ECC` (1,089 skills) | Read only: mixed provenance, including share-alike material | — |
| `BMAD-METHOD` | Heavy; ideas only (see UB-069) | — |
| `h5i` | The repo the awesome-list links to is a Rust web framework, not the tool described | the right repo is found |
| `PhreshOS`, `gsd-build` | GitHub organisation pages, not repos. The plan asked which repos you meant | you tell us |
| Plan label "C20 review" and "D18" | Mislabelled: in the M2C plan C20 is "Pull and push client" and review is L05 (UB-045); D18 means different things in the M2C and Menux plans, so quote the document with the ID | — |
| Plan claim "MCP output already passes the injection guard" | Was false when written; `SX-25` made it true | — |
| Plan claim "M2C is mostly planned, not built" | Wrong: about 65 modules are built; see UB-028 to UB-045 for what is really missing | — |
| Rebuilding M2C and Menux in Rust, the conformance vectors, the `minicore-secrets` gate | Already planned in Appendix A (`DM-2`, `DM-3`, `DM-11`, packages `MG-Z*` and `MG-R*`); not a feature here | `MG-Z10` records an outcome |
| Retention scores and hot/warm/cold tiers | Kept as UB-051, status `parked`: the spec says skip until memory volume is measured | prompts get too large |
| Locust, for load tests and as the runner of the `MG-B00` WebSocket harness | Same job as the k6 script you already have (`backend/scripts/minime_loadtest.js`) [S]. Locust is gevent-based and brings flask and pyzmq, so it would need its own environment, and its core has no raw WebSocket user [R]. Not read: `pytest_locust` and the separate aiolocust project | k6 and the Python harness of UB-018 cannot do a scenario |
| promptfoo `code-scan` PR reviewer | It scans PRs through a hosted scanner service, so your diffs would leave your infrastructure [R]. UB-045 covers the need | — |
| promptfoo eval runner, Python providers, `llm-rubric`, provider compare | Already in use: `backend/evals/promptfoo/` and the CI job `promptfoo` [S]. The one gap is UB-013 | — |
| Strix SARIF 2.1.0 export | Only useful if Strix runs in CI; UB-015 is one run on staging [R] | Strix moves into CI |
| Strix coverage ledger with provenance (idea only) | A good concept: it records what was looked at, labelled agent-reported or observed. Only its docstring was read, and it needs a redesign for MiniMe [R] | the first Strix run (UB-015) shows what a coverage record would need |
| Strix risk-classifier gate (labels `deletes_data`, `changes_target`, `disrupts_service`, `safe`) | Already planned as `L07` in the M2C build plan. Take the four labels into `L07`'s labelled-call set. Its own docstring says it guards a careless agent, not a hostile one, so code rules and the sandbox keep the last word, as `L07` and Menux section 6.7 say [R] | `L07` starts |
| Hypothesis `ghostwriter.equivalent` | A technique for work already planned in Appendix A: the differential corpus of `MG-Z04` and `MG-Z10` step 6, which backs `DM-10` (Rust never more permissive than Python). It generates inputs where the vectors freeze them. Calling the Rust side needs a bridge nobody has designed [R] | `MG-Z10` records `PROCEED` (first learn the shape with one test of two Python redaction functions) |
| Hypothesis `extra/lark.py` grammar strategy | A technique for `MG-Z03`: generate shell commands from a small grammar to feed the shell-parsing vectors and the Python-against-Rust comparison. Only its docstring was read; whether a small shell grammar fits is untested [R] | `MG-Z03` starts on shell parsing |
| Codex Guardian and Hermes smart approval, for `L07` | Already planned as `L07` in the M2C build plan; the chapter was not edited. Take into `L07`: Codex's reviewer prompt (`codex-rs/prompts/templates/guardian/policy.md`) has headings for data exfiltration, credential probing, persistent security weakening and destructive actions [R]. Hermes's reviewer (`tools/approval_smart.py`) answers APPROVE, DENY or ESCALATE, strips recognisable shell comments first, wraps the command in `<command>` delimiters, tells the model to ignore instructions inside them, and escalates when it sees manipulation text [R]. A model verdict may only raise a call to "ask", never lower a rule's decision; deny rules and the sandbox keep the last word. Design ideas [U]: run it in observe mode first (UB-039), score it on a labelled call set (the review suggested about 30 per category; the Strix labels are in the row above), and measure how often it escalates a harmless call | `L07` starts |
| Hermes command-obfuscation cases, for `Q07` | Already planned as `Q07`; the chapter was not edited. Hermes flags hidden Unicode variation selectors after letters or digits (`tools/approval_variation_selectors.py`) and masks newlines inside quotes so data lines do not trip rules, while keeping `$(...)` bodies executable (`tools/approval_quoted_newlines.py`) [R]. A grep of `m2c/src/m2c/policy/` finds no variation-selector or zero-width handling [V✓]. Turn each case into a `Q07` row; if one passes the policy, fix `policy/` (`shellparse.py`) | `Q07` starts |
| Gemini subagent contract, for `L02` | Already planned as `L02` (Subagents); the chapter was not edited. Take: a subagent ends by calling a typed `complete_task` tool; separate end states, including `GOAL` and `MAX_TURNS`; a default of 30 turns (`DEFAULT_MAX_TURNS`) and a time limit in minutes [R `agents/types.ts`]. The 1-minute grace period after a limit was carried from the review [S]. Combine with UB-041 (narrowing grants) | `L02` starts |
| Codex rules with reasons and examples, for `C25` | Already planned as `C25` (rule hygiene); the chapter was not edited. Codex's `prefix_rule` has a decision (allow, prompt, forbidden), a `justification` that appears in prompts and refusals (with a suggested alternative for forbidden rules), and `match` and `not_match` example invocations checked when the rules load, like unit tests [R `execpolicy/README.md`]. Add a reason and must-match and must-not-match examples to the TOML rules of `policy/rules.py`, and refuse to load a rule whose examples fail [U] | `C25` starts |
| Hook events and failure rule, for `C13` | Already planned as `C13` (Hooks); the chapter was not edited. Codex's `HookEventName` has 14 events at `06f334a` (the review counted 15): PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, SessionStart, SessionEnd, UserPromptSubmit, SubagentStart, SubagentStop, Stop, Interrupt, PreModelRequest, PostModelRequest [R]. The plan's list also has PostToolUseFailure and lacks PostCompact, Interrupt and the two model-request events. Take Codex's idea of one JSON schema per event under `protocol/`. For failure, Vibe has a **per-hook** `strict` flag, off by default, which its config model rejects on any hook type outside `STRICT_HOOK_TYPES`; the default timeout is 60 seconds [R `vibe/core/hooks/models.py`]. The review had called five types fail-closed; the code makes that an opt-in. Adopt the shape: only types that can block may be strict, strict is explicit, and a strict hook that fails or times out blocks | `C13` starts |
| Late language-server verdicts, for `L04` | Already planned in `L04` (Verification loop and Stop hooks); the language server is `L08` (Phase 5). Hermes waits briefly after the final answer for diagnostics on the files it edited and feeds them back, at most three notes per turn [R]. Add to the UB-028 gate once `L08` exists | `L08` is built |
| Vibe's Python core with a Rust TUI, for `MG-Z10` | A possible `MG-Z10` outcome; Appendix A was not edited. Vibe's Rust TUI is a thin JSON-RPC client over stdio and never imports Python internals (`docs/adr/0016-rust-cli-delivery-surface.md`) [R], so the safety code stays in Python. `DM-2` argues for Rust partly because the compiler checks the safety code, so this outcome trades that away; you must accept the trade before it is named | the `MG-Z10` criteria are written (Appendix A rule 10: commit them first) |
| Codex proxy-side secret substitution (idea only) | The sandbox sees placeholders and a trusted proxy swaps in the real secret after the destination is authorised (`network-proxy/src/secret_substitution.rs`; the module header was read, the mechanism not traced) [R]. It needs a proxy that opens TLS. M2C's proxy is a CONNECT proxy and bridge (`C11b` in the build plan) and cannot rewrite headers inside TLS, so this is a redesign (XL) with a new certificate authority | a real case of a secret reaching the sandbox, or a design that adds no local CA |
| Codex and Hermes automatic memory writers (idea only) | Both write memory with no review step (Codex's second-phase agent; Hermes's fork after each turn) [R], which conflicts with UB-048. The two safe parts (redact before extraction; the fork trick with a queue as its only output) are in UB-048 Notes | UB-048 is built |
| Gemini Conseca (idea only) | An LLM writes a least-privilege policy for each task and a second check enforces it. Its tests show it returns ALLOW when disabled or when it finds no user prompt, so it fails open [R `safety/conseca/conseca.test.ts`]. Safe for you only if it can tighten and never loosen, and fails closed | `L07` is built and you want per-task narrowing (see UB-041) |
| Vibe per-hunk checkpoints | `m2c/src/m2c/checkpoints.py` already snapshots whole files before each step and rewinds to a step [S]. Vibe keeps an append-only log of keep and revert decisions, and reverting a hunk drags the hunks built on it [R]. That needs a UI | people ask for per-hunk undo |
| Codex limited network mode (MITM with a process-local CA) | `sandbox/netproxy.py` and `netpolicy.py` already limit hosts [S]. Method-level limits need TLS interception, and a new certificate authority is new attack surface [R `network-proxy/src/mitm.rs`] | a POST to an allowed host shows up as an exfiltration finding |
| Vibe import of foreign plugins (Codex, Claude Code, Kimi, OpenCode) | It pulls third-party hooks and MCP configs into your trust boundary [R `core/plugins/_compatibility.py`: format detection read, adapters not]. `C14` only needs `SKILL.md` folders | you want the plugin ecosystem and have a trust design for it |
| Codex V8 code mode | The model writes JavaScript that runs in a sandboxed V8 and calls tools [R `code-mode-runtime/Cargo.toml`]. Heavy dependencies (D14), model-written code, and its own approval design | never for the Python client |
| Codex `apply_patch` | `edit_file` exists (`tools/files.py`); the build plan lists an apply_patch tool at wave 13 or later [S]. Codex matches a patch hunk exactly, then ignoring trailing spaces, then trimmed [R `apply-patch/src/seek_sequence.rs`: file name only]. See the "Exact unique-match edits" row | counts of `string_not_unique` failures show the need |
| Gemini tool-output masking | Already built: `backend/codeagent/context.py` caps large tool results and clears the oldest outputs [V✓ docstring] | never |
| Gemini policy integrity hash and RE2 patterns | Hashing exists in `m2c/src/m2c/trust/fingerprint.py` (sha256) [V✓]. RE2 would add a runtime dependency, which D14 forbids | never |
| Hermes Kanban worker stop guard | It forces a worker on Hermes's own multi-agent board to end with a terminal board call [R]. Nothing in your plans uses such a board | you build a board |

## 7. Sources register

One row per source. `Checked` is `—` until you or a session has opened the source and read its licence; then write what was checked and when. Licences below are **as reported by the earlier plan or spec, not verified**. Links are `—` where the earlier documents gave only a name; add the link when you review the source.

| Source | Link | Reported licence | Verdict | Used in | Checked |
| --- | --- | --- | --- | --- | --- |
| MiniMe fix patch guide (SX series) | — | own work | done | UB-026 | — |
| Upgrade plan, 21 Nov 2026 | — | own work | input | UB-001 | — |
| Verified upgrade spec, 21 Nov 2026 | — | own work | input | UB-001 | — |
| Next.js security releases (May, Sept, Oct 2026) | — | web source | input | UB-001 | — |
| promptfoo | https://github.com/promptfoo/promptfoo | MIT (`LICENSE` read at `4a30804`) | USE (hosted generation and telemetry are on by default: see UB-014) | UB-013, UB-014, UB-030, UB-031, UB-048 | licence read 2026-11-26; read from source, not run |
| Strix | https://github.com/usestrix/strix | Apache-2.0 (whole repo; `LICENSE` read at `9ed84f9`) | USE (Alpha; telemetry on by default: see UB-015) | UB-015, UB-045, UB-056, UB-068, UB-084 | licence read 2026-11-26; the licence of `containers/opengrep-rules` not checked; read from source, not run |
| Hypothesis | https://github.com/HypothesisWorks/hypothesis | MPL-2.0 (`LICENSE.txt` read at `b9d568c`, "except where explicitly noted otherwise") | USE (test dependency only; copied files stay MPL, so do not vendor them) | UB-016, UB-017 | licence read 2026-11-26; read from source, not run |
| Schemathesis | https://github.com/schemathesis/schemathesis | MIT (`LICENSE` read at `15b71f5`) | USE | UB-017 | licence read 2026-11-26; read from source and docs, not run |
| k6 | — | not stated | in use (`backend/scripts/minime_loadtest.js`) | UB-018 | — |
| Locust | https://github.com/locustio/locust | MIT (`LICENSE` read at `5084aa1`) | SKIP | UB-018, section 6 | licence read 2026-11-26; read from source and docs, not run |
| Django | — | not stated | READ | UB-019 | — |
| pip-audit, npm audit | — | not stated | in use | UB-021 | — |
| Lurkr | — | MIT | TRY | UB-023 | — |
| anthropic sandbox-runtime | — | Apache-2.0 | LEARN | UB-032 | — |
| Greywall | — | not stated | LEARN | UB-032 | — |
| codebase-memory-mcp | — | not stated | USE (optional) | UB-034 | — |
| Argus | — | not stated | TRY | UB-035 | — |
| Gemini CLI | https://github.com/google-gemini/gemini-cli | Apache-2.0 (`LICENSE` read at `60f8082`) | LEARN (code may be copied only with the licence and notices kept and changes marked; usage statistics are on by default, `privacy.usageStatisticsEnabled` is true in `settingsSchema.ts`, and what is sent was not read) | UB-036, UB-042, UB-048, UB-075, section 6 | licence read 2026-11-26; read from source, not run |
| Hermes (hermes-agent) | https://github.com/NousResearch/hermes-agent | MIT (root `LICENSE` read at `c84e8d7f`, Nous Research 2025); 17 nested `LICENSE` or `NOTICE` files exist under `optional-skills/`, `skills/`, `plugins/` and `apps/desktop/src/plugins/hermes-bots`, and their terms were not read | LEARN (take nothing from those folders before reading its licence; `plugins/security-guidance` has a NOTICE and was reported as Apache-2.0 by the review; the root holds `hermes_constants_scratch*.py` files that look like scratch code) | UB-028, UB-033, UB-037, UB-042, UB-048, UB-064, UB-087, section 6 | root licence read 2026-11-26; read from source, not run; no telemetry client found by search, not exhaustive |
| Mistral Vibe | https://github.com/mistralai/mistral-vibe | Apache-2.0 (`LICENSE` read at `fb7511a`) | LEARN (code may be copied only with the licence and notices kept and changes marked; it needs Python 3.12 and uses 3.12 syntax such as `type` aliases, so check any file before it goes into code with a 3.11 floor; telemetry is on by default per the review, which was not re-read: `enable_telemetry`, posting to `/v1/datalake/events` on api.mistral.ai) | UB-038, UB-042, UB-044, UB-086, UB-087, section 6 | licence read 2026-11-26; read from source, not run |
| Codex | https://github.com/openai/codex | Apache-2.0 plus a `NOTICE` (it records code derived from Ratatui, MIT) (`LICENSE` and `NOTICE` read at `06f334a`). The vendored bubblewrap is LGPL-2 (`codex-rs/vendor/bubblewrap/COPYING`): never copy it | LEARN (code may be copied only with the licence and notices kept and changes marked; analytics are on unless `analytics_enabled` is explicitly false, per the review, not re-read) | UB-033, UB-048, UB-085, section 6 | licence read 2026-11-26; read from source, not run |
| OpenCode (design ideas) | — | not stated | LEARN | UB-036 | — |
| Pi (design ideas) | — | not stated | LEARN | section 6 | — |
| Tenuo | — | not stated | LEARN | UB-041 | — |
| Prismor | — | not stated | LEARN | UB-039 | — |
| UNCUT | — | not stated | LEARN | UB-042 | — |
| OpenHands (event log) | — | not stated | LEARN | UB-042 | — |
| zeroshot | — | not stated | LEARN | UB-043 | — |
| Ouroboros, Nightshift | — | not stated | LEARN | UB-044 | — |
| open-code-review | — | not stated | LEARN | UB-045 | — |
| Mixdog | — | not stated | LEARN | UB-075 | — |
| Cordum, Preloop, Caura, Orca | — | not stated | READ | — | — |
| Mnemosyne | — | not stated | LEARN | UB-047, UB-049 | — |
| MemoSync | — | not stated | LEARN | UB-048, UB-050 | — |
| agentmemory | — | not stated | LEARN | UB-049, UB-051 | — |
| mempalace | — | not stated | LEARN | UB-047 | — |
| claude-mem | — | not stated | LEARN | UB-047 | — |
| Graphiti / Zep | — | not stated | LEARN | UB-047 | — |
| Mem0, Letta, Cognee | — | not stated | READ | — | — |
| ZizkaDB | — | AGPL | ideas only | UB-046 | — |
| MiniLocker (your own project) | — | own work | REUSE (optional) | UB-046 | — |
| rust-anything | https://github.com/erkamyaman/rust-anything | MIT (`LICENSE` read at `b5025d4`) | TRY (optional tooling) | UB-081, UB-083 | licence read 2026-11-24; not audited, not run here |
| fast-anything | https://github.com/EL4CTEO/fast-anything | MIT (`LICENSE` read at `ccf46b4`) | TRY (optional tooling) | UB-082 | licence read 2026-11-24; not audited, not run here |
| OpenViking | — | AGPL | ideas only | — | — |
| webcmd | — | Apache-2.0 | LEARN | UB-052 | — |
| crawl4ai | — | Apache-2.0 | USE (optional) | UB-053 | — |
| agent-desktop | — | Apache-2.0 | USE | section 6 | — |
| browser-use | — | not stated | study only | section 6 | — |
| Agent-Reach | — | not stated | LEARN | UB-054 | — |
| blender-skills (arjun988) | — | MIT | LEARN | UB-055 | — |
| hyperresearch | — | MIT | LEARN | UB-056 | — |
| Research Toolkit | — | MIT (README level) | LEARN | UB-056 | — |
| Storm, GPT Researcher | — | not stated | READ | UB-056 | — |
| OpenMAIC | — | MIT (since June 2026) | LEARN | UB-057, UB-058, UB-059, UB-060, UB-061, UB-062, UB-063 | — |
| ponytail | — | not stated | LEARN | UB-064 | — |
| marketingskills | — | MIT | SEEDS | UB-065 | — |
| scientific-agent-skills | — | not stated | SEEDS | UB-066 | — |
| anthropics/skills | — | not stated | READ, SEEDS | UB-067 | — |
| mattpocock/skills | — | not stated | SEEDS | UB-067 | — |
| addyosmani/agent-skills | — | not stated | SEEDS | UB-067 | — |
| andrej-karpathy-skills | — | MIT | SEEDS | UB-067 | — |
| Anthropic-Cybersecurity-Skills | — | community project, not affiliated | READ, SEEDS | UB-068 | — |
| gstack | — | not stated | LEARN | UB-069 | — |
| BMAD-METHOD | — | not stated | LEARN | UB-069 | — |
| ECC | — | mixed, includes share-alike | READ | section 6 | — |
| humanizer | — | not stated | LEARN | UB-070 | — |
| text-to-cad | — | MIT | LEARN, spike | UB-072, UB-073, UB-074 | — |
| impeccable, taste-skill, ui-ux-pro-max-skill | — | not stated | LEARN | UB-076 | — |
| screenshot-to-code | — | not stated | LEARN | UB-077 | — |
| diagram-design | — | not stated | LEARN | UB-078 | — |
| archify | — | not stated | in use | UB-078 | — |
| headroom | — | not stated | TEST first | UB-075 | — |
| caveman | — | not stated | LEARN | UB-075 | — |
| hyperframes | — | not stated | LEARN, spike | UB-079 | — |
| open-slide, ppt-master | — | not stated | LEARN | UB-080 | — |
| OpenMontage, openvid | — | AGPL; non-commercial | ideas only | section 6 | — |
| academic-research-skills | — | non-commercial | ideas only | section 6 | — |
| brainless | — | check first | USE (marketing, docs) | — | — |
| awesome-agents, awesome-selfhosted, awesome-harness-engineering lists | — | lists | READ | — | — |
| sofagent, Orca AI Incident Archive, SEC-bench, SkillsBench, LLMLingua, context-mode, E2B and Sandbox SDK, Arize Phoenix, Manifest | — | not examined | not examined | — | — |

## 8. Decision log

Every change of status, and every general decision about this backlog. `--set-status` adds the rows for status changes.

| Date | ID | Change | Note |
|---|---|---|---|
| 2026-11-24 | — | batch B01 created | all features start as candidate; the SX series is excluded as done |
| 2026-11-24 | — | batch B02 created | rust-anything and fast-anything added as optional tooling; Appendix A (`MG-Z04`, `MG-Z10`) edited to match |
| 2026-11-26 | — | batch B03 created | five reference repos read and their licences recorded; the review's recommendations applied: existing entries extended in place (UB-014 to UB-018, UB-030, UB-031, UB-045, UB-048, UB-056, UB-068), UB-084 added, eight items recorded in section 6. Other chapters not edited |
| 2026-11-26 | — | batch B04 created | four reference repos (gemini-cli, hermes-agent, mistral-vibe, codex) read and their licences recorded; the review's recommendations applied as the decisions: existing entries extended in place (UB-028, UB-033, UB-036, UB-037, UB-038, UB-042, UB-048, UB-064, UB-075), UB-085 to UB-087 added, 18 rows added to section 6. Other chapters not edited |

## Batch B01 (2026-11-24): Upgrade plan and verified spec of 21 Nov 2026, minus the finished SX series

*Source documents:* the upgrade plan, the verified upgrade spec and the MiniMe fix patch guide (all three in the person's hands), plus a re-check of the code at MiniMe `cd0bc23`. Where the plan and the spec disagree, the spec (which checked the code) wins. Every feature starts as `candidate`. The two documents' own recommendation is noted in **Notes.** where they gave one.

### UB-001: Move the web app from Next.js 14 to a supported line (L)

> Next 14.2.35 gets no more fixes; move to 16.x with React 19, new Sentry and Mermaid, before the accepted-risk lines expire.

**Product** MiniMe · **Source** Plan S2, Spec U3, fix guide section 7 · **Status** candidate · **Depends** — · **Decision** Target line: 16.x (Active LTS) or 15.5.x (Maintenance LTS) · **Evidence** [V✓] [W] [GK]

**What.** Replace `next 14.2.35` and `react 18.3.1` with a supported Next line (the plan prefers 16.x; 15.5.x is a smaller step but also needs React 19), together with `eslint-config-next`, `@sentry/nextjs` above 10.76.1 and `mermaid` above 12.1.0.

**Why.** Next 14.x is not a supported line, so every future advisory has no fix. Today 12 `next` and 2 `postcss` findings sit in `.github/audit-allowlist.txt` as accepted until **2027-02-21** [V✓]; after that date the `dependency-audit` job fails. Real exposure today is low: no `'use server'`, `next/image`, `use cache` or `beforeInteractive`, and the middleware only refreshes the Supabase session [V per spec].

**Where.** `frontend/package.json` and lockfile; `frontend/next.config.js` (a `webpack:` hook, Sentry options, and the `securityHeaders.js` module from `SX-28`); `frontend/middleware.js`; `frontend.Dockerfile` (three stages on `node:20-slim` [V✓]); `patches/react-window+2.3.0.patch` (applied by `postinstall` with `patch-package`); `scripts/vendor-pyodide.mjs`; the CI `frontend-lint` job; `.github/audit-allowlist.txt`.

**How.**

1. On a branch, record a baseline: `npm ci`, `npm run build`, `npm run lint`, `npm test`.
2. On the day, run `npm view next dist-tags` and take the newest Active-LTS patch (the spec saw 16.4.6 needed on 21 Nov; anything from 16.2.0 before 16.3.6 has an `ImageResponse` RCE).
3. Move to React 19 and read each UI dependency's `peerDependencies`: `@react-three/fiber`, `@react-three/drei`, `recharts`, `reactflow`, `@codesandbox/sandpack-react`, `react-force-graph-2d`, `react-window`, `@xterm/*`. Expect a major bump for the three.js pair [GK].
4. Read Next's **official** upgrade guide, not memory. Leads to confirm: `cookies()` and `headers()` become async (`app/page.js`, `middleware.js`); `middleware` may be renamed `proxy`; the default bundler may change; `next lint` may be removed, which breaks the `lint` script and the CI job [GK].
5. Re-apply and re-verify the `react-window` patch; re-run `vendor-pyodide.mjs` and confirm `public/pyodide/` loads.
6. Move `frontend.Dockerfile` off `node:20-slim` (CI already uses Node 22.22.0).
7. Bump Mermaid and check `MermaidDiagram.jsx`; bump Sentry.
8. Delete the 14 `next` and `postcss` lines from the allow-list in the same patch (the job fails on a line whose finding is gone).

**Done when.** `npm audit --omit=dev --audit-level=high` is clean; on staging the smoke list passes: sign-in, workspace load, a notebook generation, each preview iframe (`PreviewPane`, `UrlPreview`, `WireframePreview`, `ArtifactRenderer`), a Mermaid diagram, the 3D views, the terminal, the Pyodide runner and a Sentry test event.

**Notes.** **Deadline 2027-02-21** unless the allow-list is renewed on purpose. Until it lands: keep authorization out of `middleware.js`; do not adopt Server Actions, `next/image` or Cache Components. After it lands, CSP nonces can be reconsidered (UB-012). Plan this as several patches, one per step above.

### UB-002: Decide Pillow against moviepy, then act (M)

> 59 Pillow findings are accepted only because moviepy needs Pillow below 12; pick keep, test Pillow 13, or drop moviepy.

**Product** MiniMe · **Source** Fix guide D-1, Spec 2.1 · **Status** candidate · **Depends** — · **Decision** D-1: (a) keep and re-accept, (b) test Pillow 13, (c) stop using moviepy · **Evidence** [V✓] [T]

**What.** `pillow 11.3.0` has many advisories; every fix is 12.1.1 or newer, but `moviepy 2.2.1` (already the newest) requires `pillow<12`. Choose one of three options and carry it out.

**Why.** The allow-list holds 59 Pillow lines expiring **2027-02-21** [V✓]. Pillow is used only by the video overview builder.

**Where.** `backend/requirements.txt` (`pillow`, `moviepy`); `backend/agents/video_overview_builder.py` imports `moviepy` and `PIL` [V✓]; `backend/tests/unit/test_agent_video_overview_builder.py`; the allow-list.

**How.**

1. Default is (a): keep the pin and renew the lines for at most 90 days, on purpose.
2. For (b): in a scratch environment install Pillow 13 with `moviepy` using no-deps; run the unit test; render one real overview; check the `guardrails-ai` ceilings in `requirements.txt`.
3. For (c): replace the rendering step (see UB-079) and remove both packages.
4. Delete exactly the allow-list lines that the chosen option fixes.

**Done when.** `pip-audit` shows no Pillow finding, or the renewed lines carry a new reason and an expiry of at most 90 days.

**Notes.** **Deadline 2027-02-21.** If UB-079 replaced moviepy, the constraint would disappear (unverified).

### UB-003: Move e2b, bracex and wcmatch together (M)

> The wcmatch fix needs e2b 2.64 and bracex 3.2; three pins must move as one.

**Product** MiniMe · **Source** Fix guide D-2 · **Status** candidate · **Depends** — · **Decision** D-2: accept 24 minor versions of e2b API change, or keep accepting the finding · **Evidence** [V✓] [T]

**What.** `wcmatch 11.2` needs `e2b 2.64.0` (repo has 2.30.0) and `bracex 3.2.x` (repo has 3.0); they resolve together [T].

**Why.** One allow-list line (`GHSA-53PM-WGXF-C6QF`) expires **2027-02-21**.

**Where.** `backend/requirements.txt`; `e2b` is imported by `backend/agents/sandbox_tester.py`, `backend/agents/static_scan.py` and `backend/eo/mech_validator.py` [V✓].

**How.**

1. Read the e2b changelog between 2.30 and 2.64 for breaking changes in what those three files call.
2. Bump the three pins in a scratch virtualenv; run `cd backend && pytest tests/unit tests/static -q` and the integration tests if a database exists.
3. Run one real sandbox run if an E2B key is available (say so if not).
4. Delete the allow-list line.

**Done when.** The tests pass and the allow-list line is gone with the audit still green.

**Notes.** Falls back to renewing the line if the API change is too large.

### UB-004: Put the Caddy config in the repo and set the edge limits (M)

> The proxy config is not in either repo; commit it, then add a body-size limit, HSTS and edge rate limits.

**Product** MiniMe · **Source** Spec U4 and U5.4, Plan S3 and S5 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [GK]

**What.** A reviewed copy of the production Caddy configuration under a new folder (for example `deploy/`), and the proxy-level limits the app cannot do for itself.

**Why.** No Caddyfile exists in `MiniMe` [V✓: none found, no `deploy/` folder]. So headers, body limits and caching at the proxy are unknown, and `SX-28` deliberately left HSTS to the proxy.

**Where.** New `deploy/Caddyfile` and a short `deploy/README.md`; app caps in `backend/api/uploads.py` (`IMPORT_MAX_BYTES` 10 MB, `PDF_MAX_BYTES` and `VOICE_MAX_BYTES` 25 MB by default [V✓]).

**How.**

1. **You supply** the current Caddy configuration (remove secrets).
2. Commit it with a README saying how it is deployed.
3. Add `request_body { max_size ... }` above the app caps so oversize bodies stop at the edge.
4. Add HSTS at the proxy.
5. Add edge rate limiting: Caddy core has none, a module is needed, so read the current docs first [GK].
6. Find out whether Caddy or a CDN caches RSC responses (the plan's open question about RSC cache poisoning).

**Done when.** A 1 GB upload is refused at the proxy; a header scan shows HSTS plus the four headers from `SX-28`; the config is reviewed like code.

**Notes.** Needs information only you have. Belongs with UB-005 as one session.

### UB-005: Block cloud-metadata and link-local addresses at the host firewall (S)

> Defence in depth for the SSRF fix: the backend container cannot reach 169.254.169.254 even if a check has a bug.

**Product** MiniMe · **Source** Spec U1.7, Plan S1, fix guide section 6 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V] [GK]

**What.** A firewall rule on the host (or the provider's network settings) that stops the backend container reaching `169.254.169.254` and the link-local range.

**Why.** `url_guard` (`SX-04`, `SX-05`) is the first line; a second, independent line means a validator bug is not fatal. It also answers the plan's open question: can the backend host reach cloud metadata at all?

**Where.** The host, not the repo. A note belongs in `deploy/README.md` once UB-004 exists.

**How.**

1. From inside the backend container, try to reach the metadata address and record the result.
2. Add the rule in the way your host supports (container network chain or the provider's firewall).
3. Repeat the test; it must now fail.

**Done when.** The before and after tests are written down and the rule is documented.

**Notes.** Needs your hosting details; nothing to build in the repo.

### UB-006: Run URL fetches behind an egress proxy or in the sandbox (M)

> Optional extra layer: do the risky fetching in the E2B sandbox or behind a proxy that enforces the same rules.

**Product** MiniMe · **Source** Plan S1 (defence in depth) · **Status** candidate · **Depends** — · **Decision** Worth the complexity next to UB-005? · **Evidence** [V✓] [U]

**What.** Move `safe_get` and `safe_stream` traffic out of the backend process, either into the existing E2B sandbox or through an egress proxy that applies the same address rules (the M2C `netproxy` is a model).

**Why.** Even with the firewall, a bug in the in-process guard would run with the backend's network. A separate process or machine contains it.

**Where.** `backend/utils/url_guard.py`; callers `agents/web_clipper.py` and `agents/component_spec_lookup.py`; `m2c/src/m2c/sandbox/netproxy.py` as a reference.

**How.**

1. Pick: sandbox per fetch (the code already notes E2B cold-start cost for tools [V]) or one long-lived proxy.
2. Put the choice behind the `safe_get` interface so callers do not change.
3. Keep `url_guard` checks in front as well.

**Done when.** With the in-process checks disabled in a test, a fetch of an internal address still fails.

**Notes.** Probably not worth it if UB-005 is done; keep as an option.

### UB-007: Audit every other server-side fetch of a user-influenced URL (M)

> Find any remaining fetch whose URL comes from a user, a search result or a server reply, and route it through url_guard.

**Product** MiniMe · **Source** Plan S1 ("other fetchers"), MCP spec guidance [W] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [W]

**What.** A written audit plus fixes. The clip, video and datasheet paths are done (`SX-06` to `SX-08`); this covers the rest.

**Why.** The plan lists webhooks, link previews, image fetches and MCP metadata URLs as possible paths. At `cd0bc23` these files still call `requests`, `httpx` or `urlopen` [V✓ grep]: `eo/mcp_client.py`, `agents/academic_search.py`, `utils/web_search.py`, `api/routes/workspace_data.py`, `api/deps.py`, `agents/calendar_agent.py`, `utils/llm_client.py`, `utils/embedding.py`, `eo/integrations.py`, `agents/web_researcher.py`, `agents/pagespeed_agent.py`, `agents/deploy_agent.py`. From the call lines most look like fixed vendor hosts, but that was not read file by file.

**Where.** The files above, and `eo/mcp_client.py` for URLs a server hands back.

**How.**

1. For each file write one row: where the URL comes from (constant, user, search result, server reply) and whether it is trusted.
2. Move every untrusted one to `safe_get` or `safe_stream`.
3. Add a static test that fails when a new bare `requests.get` with a variable URL appears outside a short allow-list of files.

**Done when.** The table is in the report, no untrusted-URL fetch is left outside `url_guard`, and the static test passes.

### UB-008: Per-user ingest quotas (M)

> One user cannot run unlimited clips, videos, imports, PDFs and voice notes: a quota that answers 429 with Retry-After.

**Product** MiniMe · **Source** Spec U5.5, Plan S5 · **Status** candidate · **Depends** — · **Decision** D-3: the limits per kind · **Evidence** [V✓]

**What.** A dependency `enforce_ingest_quota(user_id, kind)` that counts calls per user, kind and window and returns HTTP 429 with `Retry-After`.

**Why.** Each ingest costs an outbound fetch plus model work, so abuse is also a cost attack on the COGS target. There is no shared limiter today; the existing ones are specific (`code_runs.py`, device pairing, `eo/concurrency_gate.py`).

**Where.** `backend/api/routes/notebooks.py` (the clip, video, import, pdf and voice handlers); `backend/eo/devices.py` has a `RateLimited` error [V✓] and, per the spec, uses the `memory.bus` Redis store; `backend/api/uploads.py` for the size caps.

**How.**

1. Read how `eo/devices.py` stores its counters and reuse that pattern.
2. Write the dependency with per-kind limits from environment settings.
3. Add it to the five routes.
4. Return a clear message and `Retry-After`.

**Done when.** The N+1th ingest in the window returns 429; the window rolls; two users do not affect each other; tests cover all three.

### UB-009: Daily ingest cost cap tied to the usage ledger (M)

> Refuse an ingest when the user's pool or day budget is spent, so ingestion cannot push COGS past the 45% target.

**Product** MiniMe · **Source** Spec U5.6 · **Status** candidate · **Depends** UB-008 · **Decision** D-3: a cost model per ingest kind · **Evidence** [V✓]

**What.** Before an ingest starts, estimate its cost and call the ledger; refuse with a clear message when the budget is gone; record the real cost after.

**Why.** Quotas by count (UB-008) do not stop a few very expensive ingests.

**Where.** `backend/eo/usage_ledger.py` (`check`, `commit`, `usage_summary` exist [V✓]); `docs/usage-ledger-call-sites.md`; the five ingest routes.

**How.**

1. Measure typical cost per kind (UB-018 helps).
2. Call `check` with the estimate before the work; `commit` the real usage after.
3. Show the user a plain message when refused.

**Done when.** A user near the cap is refused before any outbound fetch; the ledger shows the ingest rows.

### UB-010: Cap voice length before transcribing (S)

> Only file size is capped on voice notes; refuse long recordings before faster-whisper starts.

**Product** MiniMe · **Source** Spec U5.3, fix guide (patch 23 left unused) · **Status** candidate · **Depends** — · **Decision** D-3: the maximum duration · **Evidence** [V✓]

**What.** Read the duration of the uploaded audio and refuse it above a limit with HTTP 400.

**Why.** A small compressed file can hold hours of audio; transcription time and cost follow duration, not bytes. `VOICE_MAX_BYTES` is 25 MB by default [V✓].

**Where.** The `/notes/voice` handler in `backend/api/routes/notebooks.py` and the transcription call behind it (find it with `grep -rn faster_whisper backend`).

**How.**

1. Probe duration cheaply (a media library or `ffprobe`) [GK].
2. Add a named constant, environment-overridable, in `api/uploads.py`.
3. Test with a generated short silent file under and over the limit.

**Done when.** An over-long file gets a clear 400 and the transcriber is never called.

### UB-011: Re-set the size caps with a cost model (S)

> The caps from the fix series are placeholders; set them from measured cost.

**Product** MiniMe · **Source** Fix guide D-3 · **Status** candidate · **Depends** — · **Decision** D-3 · **Evidence** [V✓]

**What.** Review and justify every cap. At `cd0bc23`: `CLIP_MAX_BYTES` 5,000,000 (`agents/web_clipper.py`), `DATASHEET_MAX_BYTES` 25,000,000 (`agents/component_spec_lookup.py`), `IMPORT_MAX_BYTES` 10,000,000, `PDF_MAX_BYTES` 25,000,000, `VOICE_MAX_BYTES` 25,000,000 (`api/uploads.py`, env-overridable), `PDF_MAX_PAGES` 500, `PDF_MAX_CHARS` 2,000,000 (`agents/pdf_ingestor.py`) [V✓].

**Why.** The fix guide said these were placeholders because no cost model existed.

**Where.** The files above and UB-018's measurements.

**How.**

1. After UB-018 and UB-009, take cost per task from the ledger.
2. Choose values per kind and write them in one table in the docs.
3. Keep the environment overrides.

**Done when.** Each value has a stated reason.

### UB-012: Turn the report-only CSP into an enforced one (M)

> Collect violation reports for a week, fix them, then enforce the policy from SX-29.

**Product** MiniMe · **Source** SX-29 follow-up, Plan S3, Spec U4.4 · **Status** candidate · **Depends** — · **Decision** D-7: where CSP reports go (Sentry report URL or a small endpoint) · **Evidence** [V✓]

**What.** `frontend/securityHeaders.js` sends `Content-Security-Policy-Report-Only` and reads `CSP_REPORT_URI` at build time; without it no `report-uri` is sent [V✓]. This feature collects reports and switches to enforcing.

**Why.** A report-only policy protects nothing.

**Where.** `frontend/securityHeaders.js`, `frontend/next.config.js`, its test `frontend/app/lib/__tests__/securityHeaders.test.mjs`, `frontend.Dockerfile` (copies the module, `SX-28b`).

**How.**

1. Decide where reports go (D-7) and set `CSP_REPORT_URI` for the build.
2. Run on staging for about a week and load every preview type, the Pyodide worker, Sentry and Pusher.
3. Fix each violation by adjusting the policy or the code.
4. Change the header name to the enforcing one in the module and its test (the test now asserts report-only); keep a report-only copy to tighten further.
5. Use nonces only after UB-001.

**Done when.** The enforced policy gives no violations in the UB-001 smoke list.

**Notes.** Needs a staging environment.

### UB-013: A small blocking promptfoo gate (M)

> 10 to 20 deterministic must-pass cases that fail CI, while the broad LLM suite stays advisory.

**Product** MiniMe · **Source** Plan S7.4, Spec U2.4 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [V]

**What.** A second promptfoo config and a second CI job without `continue-on-error`.

**Why.** The existing `promptfoo` job is `continue-on-error: true` because LLM calls make it flaky. A gate only works if it never calls a model.

**Where.** `.github/workflows/ci.yml` (job `promptfoo`); `backend/evals/promptfoo/` (`promptfooconfig.yaml`, `tests/`, `providers/role_provider.py`); `backend/eo/injection_guard.py`, whose `score_snippet` calls an LLM classifier for part of its work [V].

**How.**

1. Write `promptfooconfig.gate.yaml` with deterministic assertions only (no LLM judge), on fixed fixture inputs and the guard's deterministic parts.
2. Cover injection guard, a cross-tenant leak case and PII.
3. Add the job with SHA-pinned actions like the others; no secrets.

**Done when.** The job is red on a deliberately broken case and green on the base commit.

### UB-014: Run the promptfoo red-team with a two-tenant provider (M)

> Probe prompt injection, cross-tenant leaks and memory poisoning against staging with synthetic data only.

**Product** MiniMe · **Source** promptfoo red-team docs [W], promptfoo (MIT, read at `4a30804`) [R], Plan 3.2, Spec T5 · **Status** candidate · **Depends** — · **Decision** May test generation go to promptfoo's hosted service (`api.promptfoo.app`, which receives the target `purpose` text), or must everything stay local? If local, the remote-only plugins are out · **Evidence** [V✓] [W] [R] [S]

**What.** A red-team run whose provider calls the staging HTTP API with two tenants' tokens.

**Why.** The existing `role_provider.py` replays roles through `llm_client` and never calls the HTTP API [V], so tenant isolation is untested by it.

**Where.** `backend/evals/promptfoo/` (new provider and config); promptfoo `0.122.0` per the lockfile [V]. The reading in **Notes.** was of HEAD `4a30804` (v0.126.0), not of 0.122.0, so plugin names and remote-only status may differ in the pinned version [R].

**How.**

1. Run `promptfoo redteam init` to confirm plugin names for the installed version.
2. Start from the plan's config: plugins `owasp:agentic`, `owasp:llm`, `indirect-prompt-injection`, `cross-session-leak`, `agentic:memory-poisoning`, `bola`, `bfla`, `rbac`, `excessive-agency`, `pii:direct`; strategies `jailbreak`, `jailbreak-templates`, `crescendo` [W].
3. Use your own provider key through `redteam.provider` and set `PROMPTFOO_DISABLE_TELEMETRY=1`. That stops the PostHog telemetry, which is on by default [R]. **It does not stop test generation going to the hosted service:** remote generation is on by default and is turned off with `PROMPTFOO_DISABLE_REMOTE_GENERATION` [R]. With it off, the remote-only plugins (memory-poisoning, `bola`, `bfla`, SSRF, MCP, `indirect-prompt-injection`, data-exfil and `rag-*`) produce no tests [R]. The other plugins of step 2 were not sorted.
4. Keep the local ones. `cross-session-leak` has user A plant a secret and user B try to extract it, graded on a planted `match` string, so it fits the two-tenant provider with no remote service (the grader body was not read) [R]. Check `backend/tests/canary/` (8 files, not read) for overlap first [S]. The multi-turn strategies `crescendo` and `iterative` use a red-team provider of your own when one is set (condition lines read only), which keeps attack prompts off the hosted server; confirm the config key against the installed version [R].
5. **Synthetic data only.** Record the baseline; fix each finding or record why not.

**Done when.** A baseline is recorded and a 10 to 20 case subset feeds UB-013.

**Notes.** Needs staging and two throwaway tenants. For cross-tenant object access, UB-017's deterministic object-level check is the better first test and UB-015 (Strix) the next; `bola` and `bfla` here are remote-only and judged by an LLM from text [R]. promptfoo HEAD asks for Node `^22.22.2 || ^24.15.0 || >=26`, while CI is on 22.22.0 (UB-001); read the `engines` field of the version you install before you bump it [R]. Do not run its example agent provider configs with `approval_policy: never` against a real checkout [R]. Its `code-scan` PR reviewer is in section 6.

### UB-015: First Strix run on staging (M)

> An AI pentest agent tries to read tenant A's data from tenant B through every route and tool.

**Product** MiniMe · **Source** Strix (Apache-2.0, read at `9ed84f9`) [R], Plan 3.3, Spec T6 · **Status** candidate · **Depends** UB-008 · **Decision** none · **Evidence** [V✓] [R] [S]

**What.** One run of Strix against staging with stack-matched playbooks (FastAPI, Next.js, Supabase, LLM applications).

**Why.** It finds chained authorization flaws that unit tests miss. Run it after the ingest limits so it finds new problems, not known ones.

**Where.** Staging only. Inputs: `openapi.json` (the API does not disable it [V]), the `/v1/code` WebSocket contract, the clip and video routes.

**How.**

1. Create two throwaway tenants with seeded data.
2. Use a budget-capped, run-scoped LLM key and rotate it afterwards.
3. Reproduce every finding by hand before fixing; turn each into a permanent regression test.
4. Set the run up safely: `STRIX_TELEMETRY=0` (telemetry to PostHog and the Scarf gateway is on by default), pin the sandbox image `ghcr.io/usestrix/strix-sandbox:1.4.1` by digest (UB-022) because it is pulled by tag, and keep Strix in its own environment, not in `backend/requirements.txt`: its pins (`openai-agents[litellm]<0.20`, `litellm`, `boto3`, `docker`, `cryptography<49`) will likely clash with the backend's [R].
5. Run it after UB-017's object-level authorization check. That check is deterministic and gives a clear pass or fail, so Strix is spent on what a fixed check cannot see [R].

**Done when.** The run completed; findings triaged within a week; the cross-tenant objective reported "not achieved" with evidence of what was tried.

**Notes.** Never production, never third-party targets. Needs Docker and an LLM key. Strix is classed Alpha, is LLM-driven and runs offensive tools, so use synthetic accounts only [R]. Verify first (function names only read): Strix merges duplicate findings by LLM plus CVE and package identity; compare that with `backend/agents/security_aggregator.py` before copying anything [S]. Its coverage ledger and SARIF export are in section 6.

### UB-016: Property tests with Hypothesis (M)

> Random-input tests for the pure engines: manufacturability checks, the URL guard and the shell parser.

**Product** Shared · **Source** Plan 3.4, Spec T3, Hypothesis (MPL-2.0, read at `b9d568c`) [R] · **Status** candidate · **Depends** — · **Decision** Whether C25 (safe "always allow") is built before the state-machine step · **Evidence** [V✓] [GK] [R] [S]

**What.** Hypothesis tests that must never crash or produce NaN.

**Why.** Edge cases in pure code are cheap to find this way. Hypothesis is not in the backend requirements [V✓: none found].

**Where.** `backend/eo/mech_manufacturability.py` (the `check_*` functions); `backend/utils/url_guard.py` (random hosts); `m2c/src/m2c/policy/shellparse.py` (M2C is a separate package, so it needs its own dev dependency).

**How.**

1. Add Hypothesis to the backend test requirements, pinned (the audit gate then covers it).
2. Write one property per target: no exception, no NaN, and for the guard "never allows a blocked address".
3. Turn any failing example into a plain regression test.
4. Later, add one `RuleBasedStateMachine` over the approval policy: random sequences of approve, always-allow, `cd` and restart, with the invariant that a call the rules deny is never allowed (a design idea [U]). Those sequences are where C25 bugs would hide, and the current table-driven test (`m2c/tests/policy/test_policy_decide_table.py`) is a different kind of test [R] [S].

**Done when.** The properties run in CI without skipping.

**Notes.** Property-style tests already exist as plain pytest in `m2c/tests/policy/test_policy_invariants.py` and `test_policy_robustness.py`; Appendix A (`MG-Z03`) deliberately keeps properties out of the language-neutral vectors and in Python. Hypothesis adds generated inputs to those; check first that it finds something they do not. Hypothesis, and so Schemathesis (UB-017), needs a compiled Rust module from v6.156.0 on (built with maturin) [R]. Check that wheels exist for the Windows dev machine and `python:3.12-slim`, because a source build needs a Rust toolchain. MPL-2.0 is fine as a test-only dependency; copied files stay MPL, so do not copy its files into the product [R]. UB-016 and UB-017 can share one pinned Hypothesis. Verify first (names only read): do `provisional.urls()`, `provisional.domains()` and `ip_addresses` produce IPv4-mapped, NAT64 and odd-IP forms for `url_guard.py`? If not, write your own generators. A grammar-based generator for shell commands (`extra/lark.py`) is in section 6.

### UB-017: Nightly API fuzzing with Schemathesis (M)

> Fuzz every FastAPI route, with and without auth, and fail on any 5xx or schema violation.

**Product** MiniMe · **Source** Plan 3.1 and 3.4, Spec T4, Schemathesis (MIT, read at `15b71f5`) [R] · **Status** candidate · **Depends** — · **Decision** Can staging hold two long-lived test users, and may the nightly run spend LLM money (if not, exclude those routes or use the fake model adapter that `MG-B00` describes)? · **Evidence** [V] [GK] [R] [S]

**What.** A scheduled job running Schemathesis against staging's `/openapi.json`, including a deterministic cross-tenant check (step 3).

**Why.** Finds 500s, schema drift and missing auth checks across the whole API.

**Where.** A new scheduled workflow; `backend/api/server.py` serves `/openapi.json` (not disabled [V]).

**How.**

1. Read Schemathesis's current docs for flags (the plan marks them unchecked). Read so far, from the docs and CLI (not the stateful or targeted guides): in-process mode `from_asgi("/openapi.json", app)` (the FastAPI app is at `backend/api/server.py:274` [S]), `--rate-limit`, `--max-time`, `--request-timeout` and operation filters [R].
2. Run with a throwaway tenant's token and with none; use synthetic data. In-process mode still reaches the real database and the LLM providers, so use staging settings and a fake model adapter first.
3. Add the object-level authorization check (`src/schemathesis/specs/openapi/object_authorization.py`). It replays one user's read of their own object as every other configured user and fails if another user gets the same object back; public or shared objects are ignored [R]. It needs two users' tokens (`backend/scripts/get_test_jwt.py` mints them, and `require_auth` in `backend/api/deps.py:107` takes a Bearer JWT [S]), an `auth.json` with `fixedHeaders` for each, `peers = ["alice","bob"]` in `schemathesis.toml` as the review read it, and a create or per-user list route plus a GET by id [R].
4. Record accepted failures in a `--baseline` file: they are reported but do not fail the run, and update and prune flags exist [R, CLI docs only; model code not read]. It is the same pattern as `.github/audit-allowlist.txt` [S], and the nightly run then fails only on new failures.
5. Keep it nightly and non-blocking at first, then decide.

**Done when.** A first run is triaged and each finding is fixed or recorded, and the object-level check has run with two users on staging.

**Notes.** Needs staging. Schemathesis sends POST, PUT and DELETE requests, so staging only [R]. It builds on Hypothesis (`hypothesis>=6.130.12,<7`), so the wheel caveat of UB-016 applies. Your pins for anyio, click, pytest, PyYAML, requests, rich and typing_extensions fall inside its ranges; harfile, hypothesis, hypothesis_graphql, jsonschema_rs, pyrate-limiter and werkzeug would be new [R]. It is classed Production/Stable, has 283 test files, and a grep found no telemetry or upload code [R]. `[auth.wfc]` cannot be mixed with `[auth.basic]` or `[auth.openapi.*]` [R]. Not checked: how long a Supabase token lasts, and whether its `loginEndpointAuth` works against Supabase. Verify first (directory names only read): its stateful mode, which chains create, read and delete calls; read `docs/guides/stateful-testing.md` and try it on your id-returning routes.

### UB-018: Add cost-per-task and web-product scenarios to the load harness (M)

> Extend the device load harness planned in MG-B00 with notebook, PDF and runaway-loop scenarios, measured as cost per task.

**Product** Shared · **Source** Plan 3.5, Spec T7, Appendix A `MG-B00`, Locust (MIT, read at `5084aa1`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V] [GK] [R] [S]

**What.** Not a second harness. Appendix A (`MG-B00`, `backend/loadtest/`) already plans a program that opens N device WebSockets with five scenarios (idle hold, busy, reconnect storm, slow consumer, resume) and a scripted fake model adapter. This feature adds what that harness does not measure: cost per task, and the web product's heavy paths.

**Why.** `MG-B00` measures connections, memory and latency. Cost per task from `usage_ledger` is the number that sets prices and tests the 45% COGS rule.

**Where.** `backend/loadtest/scenarios.py` (new, from `MG-B00`); `backend/eo/concurrency_gate.py`; `backend/eo/usage_ledger.py`. Already in the repo: the k6 script `backend/scripts/minime_loadtest.js` (191 lines, with `ramping-vus`, thresholds and a `db_pool_pressure` scenario) and `backend/scripts/seed_load_test_data.py` [S].

**How.**

1. Build `MG-B00` first, with its rule that the server refuses the fake adapter when a production flag is set (a load test must not spend money on providers).
2. Add scenarios: many concurrent notebook generations; a large PDF and a long transcript; concurrency-gate saturation; a runaway agent loop (does the budget cut-off fire).
3. Record p95 latency, queue depth and cost per task from the ledger for each; use synthetic data on staging.

**Done when.** A table with those three numbers exists for every added scenario, produced by the same harness as `MG-B01`.

**Notes.** You already have a k6 load test (see **Where.**), and `MG-B00` in Appendix A does not mention it [V✓ grep of `migration_guide.md`]. Before you write the web-product scenarios of step 2 in the Python harness, check whether the k6 script can hold them. Keep the device WebSocket harness as custom asyncio: Locust's core has no raw WebSocket user (only `contrib/socketio.py` and `mqtt.py`) [R]. Locust is skipped (section 6).

### UB-019: A practice lab with Django and nginx on your own machine (S)

> Learn the fuzz, load and pentest tools on throwaway targets before pointing them at staging.

**Product** Shared · **Source** Spec T8 · **Status** candidate · **Depends** — · **Decision** Confirm what you meant: the spec read "Django and nginx are stress-test targets" as practice targets · **Evidence** [V]

**What.** A throwaway `docker-compose` with a stock Django app (from the clone you have) and nginx serving static files, bound to `127.0.0.1`.

**Why.** Lets you tune budgets and learn Schemathesis, k6 and Strix safely.

**Where.** A new folder outside the product code, for example `labs/`.

**How.**

1. Write the compose file; bind to loopback only.
2. Run each tool once and note settings.

**Done when.** Each tool has run against the lab and its settings are written down.

**Notes.** Never point these tools at a host you do not own. If you meant something else by Django and nginx, change or drop this feature.

### UB-020: Pre-audit package for the daemon (M)

> Hand the auditor the hostile-URL table, the red-team corpus, Strix reports, daemon tests and a one-page threat model.

**Product** MiniMe · **Source** Plan S8, Spec U8 · **Status** candidate · **Depends** UB-013, UB-014, UB-015 · **Decision** none · **Evidence** [V✓] [V]

**What.** A folder or document set that makes the paid audit cheaper and more focused.

**Why.** The server guide defers the daemon until a funded audit [V per plan]; clean non-daemon surfaces first mean the audit finds new things.

**Where.** `daemon/` (`path_guard.py`, `preview_proxy.py`, `tools.py`, `connection.py`, `minime_daemon.py`, `tests/` [V✓]).

**How.**

1. After UB-013 to UB-015, collect: the `url_guard` test table, the promptfoo corpus, the Strix reports, the daemon test suite.
2. Write a one-page threat model.

**Done when.** The package exists and nothing in it is an unfixed high finding.

### UB-021: SBOM on release (S)

> Produce a software bill of materials for the backend and frontend when you cut a release.

**Product** MiniMe · **Source** Plan S7.5 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [GK]

**What.** A release step that generates an SBOM from `backend/requirements.txt` and `frontend/package-lock.json`.

**Why.** Lets you answer "are we affected" quickly the next time a package is compromised.

**Where.** `.github/workflows/ci.yml` or a new release workflow.

**How.**

1. Read the current documentation and choose a generator; pin its version.
2. Run it with `contents: read` only and no secrets; attach the file as an artifact.

**Done when.** A release produces both files.

### UB-022: Pin scanner binaries and images by digest (S)

> Tighten the supply chain further: pin every downloaded tool and Docker image by digest or hash.

**Product** MiniMe · **Source** Plan S7.3 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [W]

**What.** An inventory of everything CI and the Dockerfiles download, then pinning each by digest or hash.

**Why.** In March 2026 attackers force-pushed credential-stealing code to most `trivy-action` tags; SHA-pinned users were unaffected [W]. Actions are already pinned by SHA; the Dockerfiles use tags (`python:3.12-slim`, `node:20-slim` [V✓]).

**Where.** `.github/workflows/ci.yml` (`secrets-scan` with Gitleaks and Semgrep, `dependency-audit`), `backend.Dockerfile`, `frontend.Dockerfile`.

**How.**

1. List every binary, image and `curl`ed script.
2. Pin each; keep scanners in jobs with no deployment secrets and minimal `permissions:`.
3. Let Dependabot propose updates (see UB-024).

**Done when.** No unpinned download remains in CI or the images.

### UB-023: Lurkr as an advisory CI step (S)

> A static, offline scanner for risky agent capabilities in workflows and tool code, run as review items only.

**Product** MiniMe · **Source** Lurkr [W] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [W]

**What.** A non-blocking job with a baseline file.

**Why.** It flags risky capabilities in workflows and Python tool code. The plan reports it as MIT, offline and without telemetry, but early-stage with few releases, so findings are review items.

**Where.** A new job in `.github/workflows/ci.yml`.

**How.**

1. Read its current README and licence.
2. Pin the version; run with `continue-on-error`; commit a baseline.

**Done when.** It runs, the baseline is recorded, and nothing is blocking.

### UB-024: Dependabot for the Docker images (XS)

> Add a docker entry to Dependabot, but only if GitHub finds the non-standard Dockerfile names.

**Product** MiniMe · **Source** Fix guide D-4 · **Status** candidate · **Depends** — · **Decision** D-4 · **Evidence** [V✓]

**What.** `backend.Dockerfile` and `frontend.Dockerfile` have non-standard names.

**Why.** The images are outside Dependabot today. A cooldown also delays security pull requests for that manifest.

**Where.** `.github/dependabot.yml` (exists, from `SX-17` [V✓]).

**How.**

1. Read GitHub's Dependabot reference to see whether it finds those names.
2. If yes, add the entry; if not, rename the files or skip.

**Done when.** The decision is recorded and, if added, the YAML parses.

### UB-025: Security headers for the book site (XS)

> Add nosniff, Referrer-Policy and a frame rule to the book's vercel.json.

**Product** Book · **Source** Spec U4.5 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓]

**What.** `vercel.json` sets `X-Robots-Tag`, cache rules and `nosniff` only on `/data/src/` today [V✓].

**Why.** Basic hardening of the published atlas.

**Where.** `minime_book/vercel.json`; its checks live in `scripts/test_check_site.py`.

**How.**

1. Add to `/(.*)`: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.
2. For framing, use `X-Frame-Options: SAMEORIGIN` (or CSP `frame-ancestors 'self'`), **not** `DENY`: the book builds iframes itself (`assets/js/figures.js`, `assets/js/shell.js` [V✓]).
3. Run `python scripts/test_check_site.py` and `python scripts/check_site.py`.

**Done when.** The headers are present on a preview deploy and every figure and embedded view still loads.

### UB-026: Record the fix patch guide in the book (S)

> Keep the SX series guide as a book appendix so the history of what was fixed is not lost.

**Product** Book · **Source** the MiniMe fix patch guide · **Status** candidate · **Depends** — · **Decision** Is a finished guide worth a book page? · **Evidence** [V✓]

**What.** Add the guide as a Markdown file under `data/docs/` with the summary and index lines.

**Why.** It records decisions D-1 to D-8 and the SX order. Its own header still says "nothing has been applied", which is now untrue.

**Where.** `data/docs/` (new file), `data/summary.md`, `llms.txt`; the reader page comes from the external builder.

**How.**

1. Copy the guide; add a one-line status at the top: all `SX-01` to `SX-29` applied (patches 18, 19 and 23 intentionally unused).
2. Add it to `data/summary.md` and `llms.txt` as an appendix or a record.

**Done when.** `python scripts/check_site.py` passes and the file is listed.

### UB-027: Refresh the book after the fixes and upgrades (M)

> The book's census and graph describe commit 3727ae3; refresh them after the fix series and again after bigger upgrades.

**Product** Book · **Source** Fix guide section 7, `UPDATING.md` · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓]

**What.** Run the book's own update routine against MiniMe's current commit.

**Why.** `data/summary.md` says "Snapshot 2026-11-19, commit 3727ae3" [V✓]; MiniMe is now at `cd0bc23` with the whole SX series.

**Where.** MiniMe (graph rebuild with Copilot) and `minime_book` (`scripts/update_all.py`); chapters that describe things the SX series changed (CI jobs, headers, upload limits, MCP rules).

**How.**

1. Follow `UPDATING.md`: commit MiniMe, rebuild the graph with the prompt in that file, run `python scripts/update_all.py`.
2. Read the chapters that mention CI, headers, uploads and MCP and correct them.
3. Run it again after UB-001 and the other big upgrades.

**Done when.** `update_all.py` passes and the Coverage page shows census, graph and notes at the same commit.

### UB-028: Verify-on-stop in the agent loop (M)

> If the model edits files and then stops without running a test or build, ask it once or twice to verify first.

**Product** M2C · **Source** Spec M1, Plan 4.2, Hermes `agent/verification_stop.py` and `agent/turn_stop_gates.py` (MIT, read at `c84e8d7f`) [R] · **Status** candidate · **Depends** — · **Decision** Default on or off (Hermes ships it off) · **Evidence** [V✓] [R]

**What.** When the model ends its turn, and this run executed a file-changing tool with no later test, lint or build result, do not finish: add one continuation message asking it to run the project's verification command. At most two continuations per run.

**Why.** Premature "done" is a common agent failure. The server loop has no verify-on-stop [V✓: no match for "verif" in `loop.py`]. The M2C plan item L04 (verification loop and Stop hooks) waits for hooks; this version does not.

**Where.** `backend/codeagent/loop.py` (`AgentLoop`; the `NOTICE_*` constants near line 208 show how to add a notice); tests in `backend/tests/unit/test_codeagent_loop.py` with `loop_testkit.py`.

**How.**

1. Track, per turn, a ledger of the file-changing tool calls and of the commands run after them, so "verified" means a matching command ran after the last change. Hermes keeps such a ledger of commands [R].
2. Skip the check when every changed file is prose or data with nothing to run. Hermes exempts `.md`, `.markdown`, `.mdx`, `.rst`, `.txt`, `.text`, `.adoc`, `.asciidoc`, `.org`, `.log`, `.csv` and `.tsv`, so a README edit never demands a test [R].
3. At the finish point, if a change has no later verification and fewer than two continuations were used, append the continuation instead of ending.
4. Emit a new `NOTICE_VERIFY_*` event like the existing ones.
5. Reuse the step limit and budget limits so it cannot loop.

**Done when.** A fake model that edits then stops gets exactly one extra turn; one that edits, runs a test, then stops finishes normally; one that edits only a `.md` file finishes normally; the limit of two holds.

**Notes.** Deciding what counts as a "verification" tool needs a short list (shell commands matching test, lint, build). See UB-043 for the independent-validator version. Hermes ships this off by default, with at most two nudges, and says in its code that a documentation edit must never demand a verification script [R]. Whether the nudge goes in as a user-role message was carried from the review and not re-read [S]. The ledger is the real work, and UB-086 (goal mode) needs the same evidence for "complete", so build it once. Hermes also waits briefly after the final answer for language-server diagnostics on the files it edited and feeds back at most three notes (`_MAX_LSP_TURN_END_NOTES = 3`) [R]. That needs a language server (`L08`, Phase 5 of the M2C build plan) and belongs to `L04`; the chapter was not edited (section 6).

### UB-029: Skills loader for M2C (M)

> Load SKILL.md folders (name and description only at start), enforcing allowed-tools as a ceiling.

**Product** M2C · **Source** Spec M2, Agent Skills standard [W], M2C plan item C14 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [W]

**What.** A new `m2c/src/m2c/skills/` package that parses `SKILL.md` frontmatter and loads the body on demand.

**Why.** `SKILL.md` skills are adopted by 9 of 11 coding harnesses in the plan's study [W]. M2C has no loader [V✓: no `skills` package]; `trust/fingerprint.py` only reserves `.m2c/skills`, `.agents/skills`, `.claude/skills`.

**Where.** New `m2c/src/m2c/skills/`; uses `m2c/src/m2c/trust/` (folder trust) and `m2c/src/m2c/policy/` (enforce the ceiling).

**How.**

1. Re-read the Agent Skills specification before coding. As the plan summarises it: `name` 1 to 64 characters, lowercase letters, digits and hyphens, equal to the folder name; `description` up to 1024 characters; optional `allowed-tools`.
2. Load name and description at start and the body on demand.
3. Load skills from an untrusted folder only after the folder is trusted.
4. Treat `allowed-tools` as a ceiling that the policy engine enforces, never a suggestion.
5. Defaults for skill-initiated actions: pipe-to-shell, base64-decode-to-shell, credential-path reads (`.ssh`, `.aws`, `.npmrc`) and unknown outbound domains are ask-or-deny.

**Done when.** A bad name or oversize description is rejected; a skill cannot call a tool outside its `allowed-tools`; an untrusted folder's skill is not loaded; a skill in `.agents/skills/` works end to end.

**Notes.** Third-party skills often tell agents to run `curl | bash` installers [R], which is why step 5 matters.

### UB-030: Add promptfoo's coding-agent risk categories to the Q07 corpus and list the gaps (S)

> Q07 is already planned; take promptfoo's coding-agent risk categories and write rows only for what the current tests miss.

**Product** M2C · **Source** Spec M3, Plan 4.5, M2C build plan Q07, Appendix A `MG-Z03`, promptfoo (MIT, read at `4a30804`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R] [S]

**What.** Not a new corpus. `Q07` (the bypass corpus, added in revision 1.2 of the M2C build plan) is planned, and Appendix A authors it once, as language-neutral vectors (`MG-Z03`, step 4). This entry adds a source of categories and an inventory of gaps. **It cannot copy cases from promptfoo.** Its 14 coding-agent categories are listed in `src/redteam/constants/codingAgents.ts`, but the attack prompts are generated by `api.promptfoo.app`: those plugins are in `REMOTE_ONLY_PLUGIN_IDS`, and `createRemotePlugin` returns nothing when remote generation is off [R]. What can be taken is the taxonomy, the grader rubrics and the 3,514-line `verifiers.ts`, which judge the agent's commands and outputs [R].

**Why.** Cases such as `curl ... | bash`, base64-decode-to-shell, reads of `~/.ssh`, `~/.aws`, `~/.npmrc`, writes to `.git/hooks` and command-substitution tricks must give `ask` or `deny`. `m2c/tests/policy/` already holds many of them (`test_policy_decide_table.py`, `test_policy_shellparse.py`, `test_policy_review_findings.py` [V✓ grep counts]); only the missing categories are worth adding. promptfoo's categories are wider than the groups in Q07: they include CI and hook planting, test tampering and hidden-secret exfiltration [R]. The gap looks real: the docstring of `m2c/src/m2c/sandbox/profile.py` says the project directory is writable, including files the person's tools run later, and a grep found no handling of `.github`, package scripts or git hooks in `m2c/src` [S]. **But** section 6 records that the bubblewrap profile makes `.git` read-only [V✓], so check the git-hook case before you call it a gap. `m2c/tests/redteam/` does not exist yet [S].

**Where.** `m2c/tests/policy/`; `m2c/src/m2c/policy/shellparse.py` and `decide.py`; the vectors folder `protocol/conformance/` once `MG-Z02` and `MG-Z03` exist.

**How.**

1. List which Q07 categories already have a test.
2. Read promptfoo's category list and verifiers, then write the missing rows yourself where `MG-Z03` puts the vectors (or in the table-driven test, so `MG-Z03` exports them later). Start with 6 to 8 rows: writes to `.github/workflows`, to `package.json` scripts, to a Makefile and to test files; a write to a git hook (to confirm the sandbox refuses it); and secrets printed in an encoded form. Each row names the expected decision.
3. Each case must yield `ask` or `deny`; where Python is too permissive, tag it `known-fail-python` as `MG-Z03` describes.

**Done when.** Every category has at least one case that yields `ask` or `deny`, in one place only.

**Notes.** Do not create a second corpus next to the vectors. Verify first (file names only read): promptfoo's Unicode strategies `homoglyph.ts` and `asciiSmuggling.ts` may add rows to Q07's terminal-safety group; `secrets/redact.py:188` and `tui/safe.py:57` already strip format (Cf) characters [S].

### UB-031: Golden tasks for the coding agent (M)

> Ten past bug-fix commits turned into tasks with a failing test, run with a fixed budget, to get your own pass rate and cost.

**Product** M2C · **Source** Spec M4, promptfoo (MIT, read at `4a30804`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** A baseline table of pass rate and cost per task, rerun whenever the model or prompt changes.

**Why.** The plan insists on your own numbers rather than vendor claims. There is no eval harness for M2C: `backend/evals/` holds only `promptfoo` [V✓].

**Where.** New `backend/evals/m2c/` (the M2C plan's Q02 location); `m2c -p` headless mode (`m2c/src/m2c/headless.py`).

**How.**

1. Pick 10 past MiniMe or M2C commits that fixed a bug.
2. For each, make a repo state before the fix and a failing test as the success check.
3. Run the agent on each with the same budget; record pass or fail, steps and credits.
4. Make the verifier tamper-evident: hash the protected test files before the run and fail the task if they changed, as promptfoo's coding-agent verifier does (protected-file hash checks plus heuristics) [R]. One comparison keeps the scores honest.
5. When the runner asserts on how a task went, copy promptfoo's assertion shapes (tool-call counts, order as exact or in-order, arguments, goal success) and not its engine, which needs OpenTelemetry traces [R]. Running the same shapes over M2C's own event log is a design idea [U].

**Done when.** A baseline table exists and has been rerun once after a change.

### UB-032: Local MCP client for M2C (L)

> Run MCP servers under M2C's sandbox and network policy, with approval-time hashing of each tool definition.

**Product** M2C · **Source** Spec M5, Plan S6 and 4.3 and 4.4, M2C plan item C23 · **Status** candidate · **Depends** — · **Decision** Write our own sandbox profile or wrap Anthropic's `sandbox-runtime` as a pinned child process (short spike) · **Evidence** [V✓] [W]

**What.** An MCP client inside M2C (stdio servers), kept local-only as the M2C plan's decision says.

**Why.** There is no MCP client in M2C [V✓: no `mcp` package; `policy/modes.py` only mentions MCP]. The MiniMe side is hardened by `SX-24` to `SX-27`; the same rules must hold here.

**Where.** New `m2c/src/m2c/mcp/`; `m2c/src/m2c/sandbox/` (`bwrap.py`, `netproxy.py`, `netpolicy.py`); `m2c/src/m2c/policy/`.

**How.**

1. Spike (a day): own profile versus `sandbox-runtime` (Apache-2.0, Seatbelt on macOS and bubblewrap on Linux, proxy-based filtering, TypeScript API [W]). M2C is Python, so it is a design reference or a separate process. Greywall is a similar container-free sandbox [README].
2. Run each server under the sandbox with the network proxy.
3. Hash each tool definition at approval and re-ask on change (as `SX-26` does on the server side).
4. Treat tool descriptions and results as untrusted data.
5. Keep large tool schemas out of the prompt (UB-033).

**Done when.** Tests with a fake server: a changed description triggers re-approval; a result with an injection phrase is flagged; a non-`https` remote URL is refused.

**Notes.** Dynamic Client Registration is deprecated as of protocol version 2026-07-28 [W]; do not build new dependence on it.

### UB-033: Deferred tool loading with search over tool specs (M)

> When an MCP server exposes many tools, keep their descriptions out of the prompt and find them on demand.

**Product** M2C · **Source** Codex and Hermes (Plan 4.2), Hermes `tools/tool_search.py` (MIT, read at `c84e8d7f`) [R] · **Status** candidate · **Depends** UB-032 · **Decision** none · **Evidence** [R] [U]

**What.** A small search tool (BM25 over names and descriptions) the model calls to load the tools it needs.

**Why.** Big MCP schemas eat the context window and the cache.

**Where.** The UB-032 client; the server prompt assembly in `backend/codeagent/` (`prompts.py`, `context.py`).

**How.**

1. Index tool names and descriptions per server at connect.
2. Expose three bridge tools, as Hermes does: `tool_search` (find), `tool_describe` (load the full schema of chosen tools) and `tool_call` (run one) [R]. A tool's schema is loaded only after it is chosen.
3. Keep the list of loaded tools stable inside a turn for cache stability.
4. Optionally embed a short listing of the tools in the prompt under a budget. Hermes takes the smaller of 4,000 tokens and a share of the context window, and shrinks the listing in stages (full, then names only, then a bare bridge) when it does not fit [R].
5. Bound each call: Hermes allows 7 queries per `tool_search` call and 10 names per `tool_describe` call [R].
6. Run the real tool name through the policy engine and the approval path, never the name `tool_call` [U].

**Done when.** A server with 50 tools adds only the bridge tools to the prompt, and a task that needs two of them still works. A call made through `tool_call` is allowed, asked or denied by the rule for the tool it names.

**Notes.** Step 6 is a design idea that nobody has run: a bridge tool hides the real tool from any rule written against tool names, so check how `policy/` and the approvals see a bridged call before step 2. Codex's search is BM25 and returns 8 results by default; that figure came from the earlier review and was not re-read [S]. It is a ranking function that could sit inside `tool_search`.

### UB-034: Offer codebase-memory-mcp as an optional local server (S)

> A code knowledge-graph MCP server the user can install themselves, running device-local under the sandbox.

**Product** M2C · **Source** codebase-memory-mcp [R] · **Status** candidate · **Depends** UB-032 · **Decision** none · **Evidence** [R]

**What.** Documentation and a tested example config; no bundling.

**Why.** It gives the agent structural code search. Its `CBM_ALLOWED_ROOT` setting is the kind of containment wanted [R].

**Where.** M2C docs; the UB-032 client.

**How.**

1. Read its licence and current README.
2. Write the config for a sandboxed run limited to the project root.
3. **Never run its installer**, which edits many client configs [R].

**Done when.** One documented run works under the sandbox.

### UB-035: Rehearse MCP attacks against M2C with Argus (S)

> Use a red-team tool with a built-in vulnerable demo agent to rehearse tool-poisoning and rug-pull attacks.

**Product** M2C · **Source** Argus [README] · **Status** candidate · **Depends** UB-032 · **Decision** none · **Evidence** [README]

**What.** A cheap rehearsal against the new MCP client; the demo agent needs no API key.

**Why.** Finds gaps in UB-032 before real servers do.

**Where.** The UB-032 client and its tests.

**How.**

1. Read Argus's README and licence (not studied in depth yet).
2. Point it at a test M2C configuration only.
3. Convert each real finding into a regression test.

**Done when.** One run is recorded and its findings triaged.

### UB-036: Stuck detection beyond identical failures (M)

> Warn when the same call repeats even if it succeeds, then ask a model to self-check after many turns; let the user decide.

**Product** M2C · **Source** Gemini CLI and OpenCode (Plan 4.2), Gemini CLI `packages/core/src/services/loopDetectionService.ts` (Apache-2.0, read at `60f8082`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** A hash of tool plus sorted arguments, counted across a turn; warn first, then ask the model whether it is stuck after N turns; a detected "doom loop" becomes a permission question to the user.

**Why.** The loop already stops after three identical **failures** (`identical_failure_limit`, `_canonical_key` [V✓]); a loop of repeated successful calls is not covered.

**Where.** `backend/codeagent/loop.py` (`_canonical_key`, `LoopConfig`, the `NOTICE_*` constants).

**How.**

1. Count repeats of the same key regardless of outcome.
2. At a threshold, emit a warning notice; at a higher one, a model self-check call (metered). Gemini's numbers are a good first guess: the same tool call 5 times, a model check after 30 turns, and a loop confirmed at confidence 0.9 [R].
3. On a confirmed loop, pause and ask the user (reusing the existing pause path).

**Done when.** Fake-model tests: ten identical successful calls trigger the warning (and so does the fifth, if you start at Gemini's threshold); a varied sequence does not.

**Notes.** Gemini's constants (`TOOL_CALL_LOOP_THRESHOLD = 5`, `CONTENT_LOOP_THRESHOLD = 10` repeats of 50-character chunks, `LLM_CHECK_AFTER_TURNS = 30`, a check interval that adapts between 5 and 15 turns, `LLM_CONFIDENCE_THRESHOLD = 0.9`) were read [R]. The content-chunk detector watches repeated streamed text, which is a different loop from a repeated tool call; it is optional here. Tune the numbers on replays of your own traces (the ledger of UB-075) before you trust them.

### UB-037: Mid-turn user steering (M)

> Let the user add a message while the agent works, inserted behind an anti-injection marker.

**Product** M2C · **Source** Hermes (Plan 4.2), Hermes `agent/prompt_builder.py` (MIT, read at `c84e8d7f`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** A queue of user messages that the loop picks up between tool calls.

**Why.** Today a person must cancel and restart to redirect. The loop has no steering [V✓: no match in `loop.py`].

**Where.** `backend/codeagent/loop.py`; the protocol (`protocol/v1/`) would need a new client message (additive); the TUI.

**How.**

1. Add the message type and a per-run queue.
2. Deliver queued text as its own user message after the newest tool result, wrapped in an opening and a closing marker. Hermes uses `[OUT-OF-BAND USER MESSAGE ...]` and `[/OUT-OF-BAND USER MESSAGE]` [R].
3. Tell the model in the system prompt to trust that marker only in the latest turn, so a marker replayed from old history has no authority. The review reported Hermes does this; only the marker constants were re-read [S].
4. Relabel look-alikes in tool output. Hermes relabels text that imitates its own control frames, such as "CONTEXT COMPACTION", "CONTEXT SUMMARY]", "PRIOR CONTEXT" and "Runtime note:", and the marker itself [R]. Make your own list from your own frames (the `NOTICE_*` messages, the goal envelope of UB-042, the steer marker). UB-087 proposes one helper for this.
5. Cover it in `protocol/` fixtures and the contract tests.

**Done when.** A steering message sent during a run appears in the next model call exactly once, and a tool result containing the marker does not. A tool result containing a look-alike of any of your control frames is relabelled, and a marker in an older turn carries no authority.

### UB-038: An instruction-hierarchy contract in the system prompt (S)

> One ranked list of instruction sources (user, repo, skills, MCP, external data last) instead of scattered prohibitions.

**Product** M2C · **Source** Mistral Vibe (Plan 4.2), Vibe `vibe/core/prompts/cli_ml4_2026-10_v2.md` (Apache-2.0, read at `fb7511a`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** One short ranked section in the server prompt.

**Why.** A single ranking is easier to test than many separate "do not" lines.

**Where.** `backend/codeagent/prompts.py`.

**How.**

1. Read the current prompt and list its prohibitions.
2. Write the ranking; replace duplicated lines. Vibe's has seven levels, lowest number wins: critical instructions that nothing overrides; user messages (newer beat older); the repo's `AGENTS.md` files (the one closest to the task wins); the user's own `AGENTS.md`; overridable defaults in the system prompt; skills and MCP output; external data, treated as data and never as instructions [R]. Map the levels to your own sources, and write the wording yourself.
3. Put the irreversible actions that need fresh approval in the top level, and say that one approval does not carry over to a different target. Vibe's critical section says the second [R].
4. Add a test that the section exists and is stable (cache order).

**Done when.** The prompt has the ranking and the existing prompt tests pass. A fake tool result that says to ignore the rules above is treated as data.

### UB-039: Observe mode before enforce mode for new policy rules (M)

> Ship each new rule in a log-only mode first, record what it would have blocked, then enforce.

**Product** M2C · **Source** Prismor (Plan 4.2) · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** A rule flag `observe` that records a would-have-blocked event without blocking.

**Why.** New deny rules can break real work; observation shows the cost first.

**Where.** `m2c/src/m2c/policy/` (`rules.py`, `decide.py`); the event store (`m2c/src/m2c/store/events.py`).

**How.**

1. Add the flag and the event type.
2. Make `decide` return the normal decision but log the would-have-blocked one.
3. Add a command to list them.

**Done when.** A rule in observe mode never blocks and always logs; switching it to enforce blocks.

### UB-040: Check whether sandbox denials are already stored (S)

> Before building a violation log, read what `events.py` and the network proxy callback already keep.

**Product** M2C · **Source** Spec M6 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V]

**What.** A short read-only investigation with a written answer; a store is added only if one is missing.

**Why.** The sandbox design reference includes a violation log; building it twice would waste time.

**Where.** `m2c/src/m2c/store/events.py`; the record callback in `m2c/src/m2c/sandbox/netproxy.py`.

**How.**

1. Read both and list what is persisted when a denial happens.
2. If nothing, add an event type and a viewer.

**Done when.** The answer is written, and a denial is visible to the user afterwards.

### UB-041: Signed, narrowing grants for subagents (L)

> Each handoff to a subagent can only narrow what it may do: tools, argument limits, expiry.

**Product** M2C · **Source** Tenuo [R] · **Status** candidate · **Depends** — · **Decision** Waits for subagents to exist (M2C plan item L02) · **Evidence** [R] [U]

**What.** A grant object signed by the parent, checked by the policy engine, that a child can only restrict further.

**Why.** Makes delegation safe by construction.

**Where.** `m2c/src/m2c/policy/`; future subagent code (not built).

**How.**

1. Wait for L02; then design the grant fields (allowed tools, argument constraints, expiry).
2. Implement narrowing as an intersection, never a union.

**Done when.** A child cannot call anything its parent's grant does not allow.

**Notes.** Blocked until subagents exist; keep as a design input.

### UB-042: Compaction that re-injects the task goal, with a lossless log (M)

> When the context is compacted, put the original goals back in; keep the full transcript so only the model's view shrinks.

**Product** M2C · **Source** Mistral Vibe, Gemini CLI, UNCUT, OpenHands (Plan 4.2), Gemini CLI `prompts/snippets.ts` and `context/chatCompressionService.ts` (Apache-2.0, read at `60f8082`) [R], Hermes `agent/context_compressor.py` and `context_compressor_prompt_rules.py` (MIT, read at `c84e8d7f`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** Re-injection of the original task statement after a compaction, and a guarantee that nothing is deleted from the stored log.

**Why.** Compaction already exists (`backend/codeagent/context.py`, notice `context_compacted` [V✓]); goal drift after compaction is the gap. The local store keeps events append-only per the M2C plan.

**Where.** `backend/codeagent/context.py`, `backend/codeagent/loop.py`, `m2c/src/m2c/store/events.py`.

**How.**

1. Read what compaction does today and what the store keeps.
2. Add a short "goal envelope" message after each compaction.
3. Test that the full log is unchanged by compaction.
4. Write the template for the model summary (`L03` in the M2C build plan; the plan was not edited, so this entry carries the template). Gemini's is an XML `<state_snapshot>` with the sections `<overall_goal>`, `<active_constraints>`, `<key_knowledge>`, `<artifact_trail>`, `<file_system_state>`, `<recent_actions>` and `<task_state>` [R]. Add Hermes's `## Unverified / Working Hypotheses` section, so a guess is never restated as fact [R].
5. Put two rules in the summariser's prompt. Text inside the history that tells the model to ignore its instructions is not obeyed (Gemini says so in its prompt [R]). The summary must not answer a request that appears inside the history (Hermes; carried from the review and not re-read [S]).
6. Take Gemini's two numbers as first guesses to compare with the constants in `context.py`: compress at 0.5 of the window and keep the newest 0.3 (`DEFAULT_COMPRESSION_TOKEN_THRESHOLD`, `COMPRESSION_PRESERVE_THRESHOLD`) [R].

**Done when.** After a forced compaction, the first model call contains the original task, and the stored events are identical. A history line that says to ignore previous instructions does not change the summary call, and a guess made in the history lands under "Unverified".

**Notes.** Compaction here is still mechanical (clear the oldest tool outputs, cap large results, repeat the person's messages) [V✓ docstring of `context.py`], so steps 4 to 6 are for the model summary that does not exist yet. Hermes also replaces secrets with `[REDACTED]` in the summary input [S]; the server side would need its own redactor for that. Write your own wording: Gemini's template is Apache-2.0, so copied text would need its notice.

### UB-043: An independent verifier context and step-graph validation (L)

> A second, separate model context checks the result; a multi-step plan is validated before any step starts.

**Product** M2C · **Source** zeroshot [R] · **Status** candidate · **Depends** UB-028 · **Decision** Waits for subagents · **Evidence** [R] [U]

**What.** The verifier from UB-028 run in its own context, and a check that a plan has no unbounded loops or unreachable branches.

**Why.** A model grading its own work in the same context is weak.

**Where.** `backend/codeagent/loop.py`; future subagent code.

**How.**

1. After UB-028, run verification in a fresh context with only the diff and the task.
2. Validate any step graph before running it.

**Done when.** The verifier cannot see the author's reasoning, and a malformed graph is rejected.

### UB-044: Plan mode that is structural, plus a spec-first interview (M)

> In plan mode only a plan file is writable; add a spec-first interview that ends in checkable acceptance criteria.

**Product** M2C · **Source** Mistral Vibe, Ouroboros, Nightshift (Plan 4.2) · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** Plan mode already denies every mutation and needs approval to leave (`plan_exit`) [V✓ `policy/modes.py`]. This adds a writable plan file and an interview step.

**Why.** Makes the plan a real artifact the user can approve, with a definition of done.

**Where.** `m2c/src/m2c/policy/modes.py`; `backend/codeagent/prompts.py`.

**How.**

1. Allow writes only to one plan file in plan mode.
2. Add an interview prompt that ends in a spec with acceptance criteria.
3. Keep the `plan_exit` approval.

**Done when.** In plan mode only the plan file can be written; the spec contains checkable criteria.

### UB-045: A precision-first review command (L)

> A diff reviewer that gives line-level comments and favours few, correct findings over many.

**Product** M2C · **Source** open-code-review [R], Strix `skills/scan_modes/diff.md` (Apache-2.0, read at `9ed84f9`) [R], Plan 4.2 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R]

**What.** The `review` command (M2C plan item L05, `/review` and `/security-review`; the plan's label "C20" was wrong).

**Why.** The project reports higher precision at about one ninth of the tokens with lower recall; those are vendor numbers and must be measured on your own diffs.

**Where.** New M2C command; server prompt; eval from UB-031's pattern.

**How.**

1. Build a diff-to-comments flow with tools and structured line comments.
2. Write the scope rules of the review prompt from Strix's diff mode, in your own words: for a PR, removed controls, newly reachable sinks and weakened helpers are in scope [R]. It is prompt text only, so it is cheap to try.
3. Run it on your own past diffs and compare precision and cost.

**Done when.** You have your own precision and cost figures.

### UB-046: Add a hash chain to the local event store (S)

> A previous-hash and entry-hash on each event plus a verify function; the M2C plan already names MiniLocker's chain.py as the model.

**Product** Shared · **Source** M2C build plan C02 and section 11.6 (MiniLocker `ledger/chain.py`, your own project), Spec 6.1; ZizkaDB (idea only) · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [S]

**What.** `entry_hash = sha256(prev_hash + canonical entry)` in `m2c/src/m2c/store/events.py`, plus `verify_chain()`.

**Why.** The M2C build plan lists this reuse as optional: `minilocker/ledger/chain.py` hash-chains events (`prev_hash` and `hash` per row) and reads back a log whose last line was torn by an interrupted write [S]. The store's own comment says a later hash chain can cover its stored bytes [V✓]. Both M2C and Menux benefit; one log, not two.

**Where.** `m2c/src/m2c/store/events.py`, `m2c/src/m2c/store/migrations.py`. The reference, `minilocker/ledger/chain.py`, is in your MiniLocker project, which was not available when this entry was written.

**How.**

1. Read MiniLocker's `chain.py` and reuse its design (it is your own code, so no licence question).
2. Add a migration for the two columns; compute the hashes on append; write `verify_chain()`.
3. Keep the torn-final-line tolerance when reading the log back.
4. **No code from ZizkaDB** (AGPL).

**Done when.** Tampering with one row makes `verify_chain()` fail; an interrupted write still leaves a valid database; the docs say the chain **detects edits and is not signed or anchored**, as the plan requires.

### UB-047: Menux memory store with sources, validity and FTS5 (M)

> One migration for sources, memories with valid-from and valid-to, dependencies and a full-text index.

**Product** Menux · **Source** Spec 6.1, Plan 5.2 (Mnemosyne, Graphiti/Zep, mempalace, claude-mem) · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R] [W]

**What.** Tables `sources`, `memories`, `memory_deps` and `memories_fts`, with `valid_at`, `invalid_at` and `superseded_by` windows in SQLite (no graph database).

**Why.** The Menux plan already chose SQLite FTS5 and no embeddings (D9). The research found no embedding retrieval in the coding agents studied [W].

**Where.** `m2c/src/m2c/context/memory.py` (398 lines [V✓]) and `m2c/src/m2c/store/` as the base; Menux has no code yet.

**How.**

1. Write one migration in the style of `m2c/store/migrations.py`.
2. Columns as in the spec: sources(id, uri, content_hash, trust_tier, fetched_at); memories(id, text, scope, source_id, trust_tier, created_at, valid_at, invalid_at, superseded_by, last_access, access_count); memory_deps(memory_id, depends_on).
3. Retrieval uses plain scope filters; evaluate with end-to-end questions, not recall@k alone.

**Done when.** A fixed Q&A set gives stable answers; the old version of a memory stays readable.

### UB-048: Trust rule and a review queue for new memories (M)

> Anything from a web page, tool output or an imported CLAUDE.md enters as an untrusted candidate; only a user action promotes it.

**Product** Menux · **Source** Spec 6.1, Plan 5.2 (MemoSync, promptfoo memory-poisoning plugin), Gemini CLI `agents/skill-extraction-agent.ts` (Apache-2.0, read at `60f8082`) [R] · **Status** candidate · **Depends** UB-047 · **Decision** none · **Evidence** [R] [W]

**What.** A write path with trust tiers and a queue; no code path promotes automatically.

**Why.** Memory poisoning is a known attack; this is the defence the plan wants tested.

**Where.** The UB-047 tables; the Menux memory tools.

**How.**

1. Every write from external content gets tier `untrusted`.
2. Show new candidates in a queue; importing an existing `CLAUDE.md` creates candidates. Store each candidate as a reviewable patch. Gemini's background agent writes memory changes only as unified-diff `.patch` files under `.inbox/<kind>/`, one canonical file per kind, and treats transcripts as evidence and never as instructions [R].
3. Promotion only through a user action.

**Done when.** A poisoned web page cannot produce a trusted memory, tested with your own three-turn case: plant a memory, poison it, ask a follow-up.

**Notes.** promptfoo's `agentic:memory-poisoning` plugin is remote-only: its grader was read, but its cases are generated on `api.promptfoo.app` [R]. Use it only for the shape of the test and write the three turns yourself. The same plugin is in UB-014 step 2, where it returns nothing if remote generation is off. Two other reference repos write memory with no review step, so neither is copied as it is (section 6): Codex's second phase lets an agent write the memory folder with approvals set to never, and Hermes forks an agent after each turn that writes straight to its stores under a tool whitelist [S]. Two parts are safe to take: redact secrets before the extractor sees a transcript (Codex does this in its first phase [S]), and the fork-after-each-turn trick, if its output lands only in this queue.

### UB-049: Correcting a source retires its dependents, and deletes cascade (M)

> Fix or delete a source and everything derived from it leaves retrieval but stays readable in a history view.

**Product** Menux · **Source** Spec 6.1, Plan 5.2 (Mnemosyne, agentmemory) · **Status** candidate · **Depends** UB-047, UB-046 · **Decision** none · **Evidence** [R]

**What.** `invalid_at` set on dependents through `memory_deps`; cascade delete written to the hash chain.

**Why.** User-visible deletion must really remove things, and the record of it must be tamper-evident.

**Where.** The UB-047 tables; the UB-046 chain.

**How.**

1. On source correction, mark dependents invalid and hide them from retrieval.
2. On deletion, cascade and append a chain entry.
3. Add a history view.

**Done when.** Dependents vanish from retrieval but remain inspectable; `verify_chain()` fails if a deletion row is altered.

### UB-050: Show the working memory before a task, and report what was used (M)

> Before each task list the memories the agent intends to use with a reason; after it, show which were followed.

**Product** Menux · **Source** Spec 6.1, Plan 5.2 (MemoSync UX) · **Status** candidate · **Depends** UB-047 · **Decision** none · **Evidence** [R]

**What.** A confirmation step with drop or add, and a post-task record.

**Why.** Puts the user in control of what the agent remembers.

**Where.** The Menux run start; the UB-047 `access_count` fields.

**How.**

1. Select candidate memories for the task with one-line reasons.
2. Let the user drop items first.
3. After the task, record which were used.

**Done when.** A dropped memory is never used in the run.

### UB-051: Retention scores and hot, warm and cold tiers (M)

> Decay plus access boost to prune memory. Both documents say to skip this until volume is measured.

**Product** Menux · **Source** agentmemory (Plan 5.2), Spec 6.1.6 · **Status** parked · **Depends** UB-047 · **Decision** none · **Evidence** [R]

**What.** A retention score and three tiers.

**Why.** Only useful if prompts get too large.

**Where.** The UB-047 tables.

**How.**

1. Wait until memory volume makes prompts too big.
2. Tune the plan's reference values (decay 0.01; cut-offs 0.7, 0.4, 0.15) on your own data.
3. Prove the fixed Q&A set does not regress after pruning.

**Done when.** The Q&A set gives the same answers before and after pruning.

**Notes.** Parked on the spec's own advice (the constants come from a project it did not examine). Reopen when memory volume grows.

### UB-052: Learned workflows modelled on webcmd (L)

> Three levels: live browser control, a remembered sitemap of pages and actions, and compiled workflows for repeatable tasks.

**Product** Menux · **Source** webcmd (Apache-2.0 as reported) [R], Plan 5.3 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R]

**What.** A design for Menux's learned workflows; keep Playwright (D01).

**Why.** It maps directly onto the planned learned-workflow feature.

**Where.** The Menux browser tool (not built).

**How.**

1. Read webcmd's code and licence in full.
2. Write a one-page design: sitemap store, compile step, tiered approvals.

**Done when.** A design page exists and is reviewed.

### UB-053: crawl4ai as an optional web reader (S)

> A self-hostable crawler to Markdown, only after the licence record and with every URL through url_guard rules.

**Product** Menux · **Source** crawl4ai (Apache-2.0 as reported) [R] · **Status** candidate · **Depends** — · **Decision** Waits for the Menux licence record (R05) · **Evidence** [R]

**What.** Optional reading of web pages as Markdown.

**Why.** Useful for web reading; any fetch must follow the SSRF rules.

**Where.** The Menux web tools.

**How.**

1. Record the licence decision (R05).
2. Run it behind the guard.

**Done when.** A fetch of an internal address through it fails.

### UB-054: A capability-listing command (XS)

> A `menux capabilities` style command that tells the user what the agent can do, borrowed from Agent-Reach.

**Product** Menux · **Source** Agent-Reach (UX idea only) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R]

**What.** One command listing capabilities and their tier.

**Why.** Users need to know what exists without reading docs. Do **not** copy its login-copying behaviour.

**Where.** The Menux CLI (not built).

**How.**

1. Read the capability registry once it exists.
2. Print it grouped by tier.

**Done when.** The listing matches the registry.

### UB-055: A Blender skill pack (M)

> Export and optimisation checklists from a 94-skill Blender pack, as a Menux skill pack.

**Product** Menux · **Source** blender-skills by arjun988 (MIT as reported) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R]

**What.** A Menux pack, not a mechanical-engine feature.

**Why.** The transferable part is the checklists (export pipeline, asset optimisation, collision proxy).

**Where.** Menux skills (not built).

**How.**

1. Read the repo and its licence.
2. Rewrite the useful checklists in your own words.

**Done when.** The pack passes the skills pipeline in UB-064.

### UB-056: An independent claim-check pass for research reports (M)

> After a report is drafted, a separate model call checks each claim against its cited source and flags unsupported ones.

**Product** MiniMe · **Source** Spec P1, Plan 6.1 (hyperresearch, Research Toolkit, Storm and GPT Researcher as references) · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R] [README]

**What.** A new `backend/agents/claim_checker.py`. Input: a draft and its cited source texts. Output per claim: supported, contradicted or unresolved, with the passage. The three closure states are reworded from Strix's counterevidence rules (confirmed, ruled out naming the control, unresolved) [R]; the earlier "unsupported" and "not found" are both **unresolved**.

**Why.** Stops confident claims that the sources do not back. No such module exists [V✓: nothing named `claim` in `backend/agents/`].

**Where.** New `backend/agents/claim_checker.py`; wired after the drafting step of the research flow (`backend/agents/web_researcher.py` and `backend/agents/academic_search.py` are the existing sources).

**How.**

1. Split the draft into claims; for each, find the supporting passage in the cited source.
2. Run it in a separate model call from the writer (so it cannot agree with itself).
3. Return flags with passages; show them in the report.
4. Close every claim; none stays open. **Supported** (give the passage), **contradicted** (name the passage that says otherwise) or **unresolved** (say what was searched).

**Done when.** Fixture drafts with known unsupported claims are closed as contradicted or unresolved by deterministic asserts, and you have reviewed the flag rate on 10 real reports.

**Notes.** `hyperresearch` and `Research Toolkit` are MIT as reported; read before copying anything.

### UB-057: Generation that survives a closed tab (L)

> A notebook or course generation keeps running on the server if the user closes the browser.

**Product** MiniMe · **Source** OpenMAIC [R], Plan 6.2 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** A background job with progress the user can return to.

**Why.** Long generations are lost today when the tab closes (to confirm in the code).

**Where.** `backend/api/routes/notebooks.py` (for example `_generate_video_overview`) and the frontend notebook tab.

**How.**

1. First write a one-page design: where state lives, how a result is claimed, what it costs.
2. Check the "no content at rest" posture before storing results.

**Done when.** A generation started, tab closed, and reopened shows the finished result.

**Notes.** Only the idea is recorded; it needs a design pass.

### UB-058: Project-based learning with an AI tutor, milestone by milestone (L)

> A guided project mode where a tutor checks progress at each milestone.

**Product** MiniMe · **Source** OpenMAIC [R], Plan 6.2 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** A study mode built around a project with milestones and tutor feedback.

**Why.** Deeper learning than one-off answers.

**Where.** The study and notebooks surface.

**How.**

1. Read OpenMAIC's implementation and licence (MIT since June 2026 as reported).
2. Write a design with milestone data, tutor prompts and cost per session.

**Done when.** A reviewed design exists.

### UB-059: Chat about any slide element (M)

> Select an element on a generated slide and ask about it.

**Product** MiniMe · **Source** OpenMAIC [R], Plan 6.2 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** Element-level context for chat.

**Why.** Faster questions about exactly what the user sees.

**Where.** The slide or artifact preview components.

**How.** Design first: how elements get stable ids, and how the chosen element reaches the model.

**Done when.** A reviewed design exists and a prototype answers about a selected element.

### UB-060: Course-level undo (M)

> Undo a whole generated course step, not only the last edit.

**Product** MiniMe · **Source** OpenMAIC [R], Plan 6.2 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** A version history at the level of a course or notebook.

**Why.** Protects users from a bad regeneration.

**Where.** The notebook storage and its routes.

**How.** Design first: what a version is, how long it is kept, how it fits the retention rules.

**Done when.** A reviewed design exists.

### UB-061: Export to PPTX and HTML (M)

> Let users download generated slides or notebooks as PowerPoint and standalone HTML.

**Product** MiniMe · **Source** OpenMAIC [R], Plan 6.2; slide-generation references in UB-080 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** Two export formats.

**Why.** Users want to take the work elsewhere.

**Where.** The notebook export code (`backend/api/routes/notebooks.py`) and the frontend.

**How.**

1. Choose a library for PPTX (check its licence and the audit gate).
2. Keep the sandboxed-iframe model when previewing HTML; sanitise slide HTML on export.

**Done when.** A generated deck opens in PowerPoint and the HTML export opens offline.

### UB-062: A knowledge base with @-mentions (M)

> Attach sources to a workspace and mention them by name in chat.

**Product** MiniMe · **Source** OpenMAIC [R], Plan 6.2 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [U]

**What.** Named sources and a mention picker.

**Why.** Makes grounding explicit and easy.

**Where.** `backend/agents/source_manager.py` and the chat composer.

**How.** Design first: how a mention resolves to a source and how tenant isolation is kept.

**Done when.** A reviewed design exists.

### UB-063: Use OpenMAIC's published advisories as a free test checklist (S)

> Its security advisory list names the classes of bug a study app has; check each against MiniMe.

**Product** MiniMe · **Source** OpenMAIC advisories [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R]

**What.** A short table: advisory class, does MiniMe have the same path, where it is tested.

**Why.** The plan lists: sanitised slide HTML, validated provider addresses and refused redirects, expiring access tokens, a render-service network policy and hardened document parsing. Several are covered by the SX series; the rest are checks to run.

**Where.** A table in the docs or the report.

**How.** Read the advisories (for example `GHSA-g87c-cm4q-cw5x` for addresses and redirects) and mark each as covered, open or not applicable.

**Done when.** Every class has a row and each open row is a candidate feature or a test.

### UB-064: A repeatable skills pipeline: select, scan, rewrite, evaluate, label, regress (M)

> A written process and a small scanner so every seed skill is vetted the same way before it is kept.

**Product** Shared · **Source** Plan section 7, ponytail (method) [README], Hermes `tools/skills_guard.py` (MIT, read at `c84e8d7f`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [T] [README] [R]

**What.** The six steps from the plan, with a scanner script and a before-and-after eval method.

**Why.** Several third-party skills tell agents to run `curl | bash`. The plan's own regex scan of 49 repos found no hidden payloads but was shallow [T].

**Where.** A script and a doc; `backend/eo/skill_library.py` for storage.

**How.**

1. **Select** one skill for a named need. 2. **Scan** for hidden Unicode, injection phrases, pipe-to-shell, credential paths and exfiltration domains. 3. **Rewrite** in your own words to the Agent Skills format and record the origin in `metadata.adapted_from`. 4. **Evaluate**: same agent with and without the skill on 10 to 20 real tasks (ponytail ran 39 tasks, five runs each [README]). 5. **Label trust**: built-in, user or third-party. Hermes's guard has four tiers (builtin, trusted, community, agent-created) and one table that maps tier and scan verdict to an action: builtin allows all three verdicts; trusted allows safe and caution and blocks dangerous; community allows only safe; agent-created allows safe and caution and asks on dangerous [R `INSTALL_POLICY`]. Use that table as the install policy. 6. **Regress** whenever the model changes.

**Done when.** One skill has gone through all six steps and the result is recorded.

**Notes.** The Hermes scanner's own header lists a known gap: language file-write calls aimed at the agent's own configuration are only low severity [R]. Cover that case in your scan. Do not copy skills out of the Hermes repo without reading each folder's licence: 17 nested `LICENSE` or `NOTICE` files exist under `skills/`, `optional-skills/`, `plugins/` and one desktop plugin, and their terms were not read (section 7).

### UB-065: Growth tab seed skills from marketingskills (M)

> Rewrite a marketing skill set as seeds for the Growth tab roles, after confirming those roles exist.

**Product** MiniMe · **Source** marketingskills (MIT as reported), Spec P2, Plan 6.3 · **Status** candidate · **Depends** UB-064 · **Decision** Do `seo_auditor` and `growth_strategist` exist or still need building? · **Evidence** [V✓] [R]

**What.** Seeds for `growth_strategist` and `seo_auditor`.

**Why.** **A mismatch to resolve first:** the book's feature guide lists `seo_auditor.py` and `growth_strategist.py` as modules, but neither exists in MiniMe at `cd0bc23` and neither appears anywhere in git history [V✓]. So either the roles are still to be built (then this feature belongs to that work) or the guide is wrong.

**Where.** `backend/eo/skill_library.py`: `_load_skills()` seeds `SKILL_SEED` into the live store **once**, so editing the seed does not reach an existing deployment; new seeds go through `write_skill(title, doc_text, source=...)` [V✓].

**How.**

1. Settle the mismatch above.
2. Read the repo's `LICENSE` (the plan says MIT; the spec did not check).
3. Run each skill through UB-064; add with `write_skill` in a one-off script.

**Done when.** Each kept skill beat its "without" run on your tasks.

### UB-066: Research and notebooks seeds from scientific-agent-skills (M)

> Pick a handful of the 177 science skills by actual usage, rewrite them as seeds.

**Product** MiniMe · **Source** scientific-agent-skills [R], Plan section 7 · **Status** candidate · **Depends** UB-064 · **Decision** none · **Evidence** [R]

**What.** A few seeds, not the whole set.

**Why.** Quality over volume; the plan says "pick a handful by usage".

**Where.** `backend/eo/skill_library.py` through `write_skill`.

**How.** Choose by what users actually ask for, then UB-064.

**Done when.** Each kept skill beat its "without" run.

### UB-067: M2C built-in skills and a behaviour baseline (M)

> Rewrite skills from anthropics/skills, mattpocock/skills, addyosmani/agent-skills and one Karpathy-style CLAUDE.md as M2C built-ins.

**Product** M2C · **Source** anthropics/skills, mattpocock/skills, addyosmani/agent-skills, andrej-karpathy-skills (MIT as reported) · **Status** candidate · **Depends** UB-029, UB-064 · **Decision** none · **Evidence** [R]

**What.** Built-ins for `init`, `verify`, `review`, `create-skill`, and a small baseline of "think first, keep it simple, surgical edits, goal-driven".

**Why.** The loader (UB-029) needs something worth loading.

**Where.** M2C built-in skills (new).

**How.** For each source: read the licence, rewrite in your words, run UB-064. The Karpathy file is small enough to rewrite and evaluate.

**Done when.** Each built-in passed its before-and-after run.

### UB-068: Security reviewer prompts and a vetted security skills library (M)

> Turn Strix's playbooks into security_reviewer prompts and the 818 community security skills into a reference library.

**Product** MiniMe · **Source** Strix playbooks (Apache-2.0, `LICENSE` read at `9ed84f9`), Anthropic-Cybersecurity-Skills (community, not affiliated) · **Status** candidate · **Depends** UB-064 · **Decision** none · **Evidence** [R]

**What.** Rewritten prompts and a vetted subset.

**Why.** Reuses real playbooks (FastAPI, Next.js, Supabase, LLM applications, agentic systems). If copied, Apache-2.0 attribution must be kept; rewriting is better.

**Where.** The `security_reviewer` role prompts; the M2C bypass corpus (UB-030).

**How.** Read, rewrite, vet each skill; the big set is "large and uneven". Strix has 30 vulnerability playbooks, 4 analysis playbooks and 4 scan modes, all Markdown [R]. Start with `idor`, `ssrf`, `llm_prompt_injection`, `agentic_system_security`, `severity_calibration` and `counterevidence` (the last also feeds UB-056).

**Done when.** The prompts pass UB-064 and the library lists only vetted skills.

### UB-069: Role ideas from gstack and BMAD (S)

> Take process ideas such as a security-officer role using OWASP and STRIDE; do not import in bulk.

**Product** MiniMe · **Source** gstack, BMAD-METHOD [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R]

**What.** A short list of roles worth having.

**Why.** Ideas only; BMAD is heavy.

**Where.** The role registry.

**How.** Read both; write which roles add something yours lacks.

**Done when.** A short reviewed list exists.

### UB-070: An optional writing-quality pass from humanizer (S)

> A style pass that removes AI-writing tells, for quality and not for concealment.

**Product** MiniMe · **Source** humanizer [R] · **Status** candidate · **Depends** UB-064 · **Decision** none · **Evidence** [R]

**What.** An optional step after drafting.

**Why.** Cleaner prose.

**Where.** The writer roles.

**How.** Read, rewrite as a skill, run UB-064.

**Done when.** It beats the "without" run on quality.

### UB-071: The overhang and draft check in the mechanical engine (M)

> The one manufacturability check the code itself says is missing.

**Product** MiniMe · **Source** Spec P3 (the module's own docstring) · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓]

**What.** Detect unsupported overhang beyond `draft_angle_deg`.

**Why.** `backend/eo/mech_manufacturability.py` already has the standoff, exclusion, cutout and collision checks and `build_manufacturability_report`; its docstring says the overhang check has no real geometry to run on yet and is deferred to Phase 9 [V✓].

**Where.** `backend/eo/mech_manufacturability.py` (`build_manufacturability_report` at line 593).

**How.**

1. Read the docstring and the Phase 9 note.
2. Decide whether a spec-level approximation is useful before real geometry (UB-073).
3. Add the check with unit tests.

**Done when.** The report includes the new check and its tests pass.

### UB-072: Compare text-to-cad's per-process rules with yours (S)

> Read its machining, sheet-metal, moulding and 3D-printing rule sets and adopt the rules you lack.

**Product** MiniMe · **Source** text-to-cad (MIT as reported) [R], Plan 6.5 · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [R] [V✓]

**What.** A comparison table and a list of missing rules.

**Why.** The spec says the "compare with Phase 6" work is mostly done; what remains is rules you do not have.

**Where.** `backend/eo/mech_manufacturability.py`.

**How.** Read its rule sets; mark each as present, absent or not applicable; add the absent ones in small patches.

**Done when.** The table exists.

### UB-073: Spike: can build123d replace FreeCAD inside the E2B template? (M)

> Measure install size, cold start, STEP and STL output and determinism.

**Product** MiniMe · **Source** text-to-cad (build123d route) [R], Spec P3 · **Status** candidate · **Depends** — · **Decision** Adopt build123d or keep the FreeCAD plan · **Evidence** [V✓] [R]

**What.** A one-page decision with numbers.

**Why.** Real geometry export is planned through FreeCAD in E2B; the code notes E2B cold start is costly [V].

**Where.** The E2B template; `backend/eo/mech_validator.py`.

**How.**

1. Install build123d in a scratch template; measure size and cold start.
2. Generate STEP and STL from one input twice; compare bytes.

**Done when.** The numbers and the decision are written.

### UB-074: An "analyse this part" stress check (L)

> A possible future capability using CalculiX-style stress analysis.

**Product** MiniMe · **Source** text-to-cad (stress checks via CalculiX) [R], Plan 6.5 · **Status** parked · **Depends** UB-073 · **Decision** none · **Evidence** [R]

**What.** Stress analysis as a user-facing feature.

**Why.** The plan calls it a possible future capability.

**Where.** The mechanical engine.

**How.** Revisit after UB-073.

**Done when.** Not scheduled.

**Notes.** Parked: needs real geometry first; reopen after UB-073.

### UB-075: Cost experiments before adopting any compressor or router (M)

> Replay real traces with and without output compression, terse agent messages and cheaper models, and compare cost and quality.

**Product** Shared · **Source** Spec P4, Plan 6.6 (headroom, caveman, Mixdog), Gemini CLI `routing/strategies/numericalClassifierStrategy.ts` (Apache-2.0, read at `60f8082`) [R] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [R]

**What.** A table of cost and quality per variant.

**Why.** Vendor numbers are unverified: headroom reports 21 to 57 percent in four scenarios and little on prose; caveman marks some results interim [R].

**Where.** `backend/eo/usage_ledger.py` for traces and costs.

**How.**

1. Take a sample of real traces from the ledger.
2. Replay with: tool-output compression (headroom-style; set `HEADROOM_OFFLINE=1`, it ships an anonymous beacon by default [R]), terse agent-to-agent messages (never on user-facing study content), a cheaper model for search, edit and review, and a complexity-score router. Gemini's classifier scores each task from 1 to 100 and a threshold picks the stronger or the cheaper model alias [R].
3. Compare cost and quality on a fixed set; adopt only where quality holds.

**Done when.** The table exists.

**Notes.** Gemini's default threshold is 90, and a remote value from its settings service overrides it when the value is between 0 and 100 [R `getResolvedClassifierThreshold`]. Do not adopt a threshold you cannot see or set yourself: pick yours from the replays of step 1.

### UB-076: Design and build techniques from impeccable, taste-skill and ui-ux-pro-max (M)

> Adopt techniques (not code) such as a command vocabulary of polish, bolder, critique and audit, and test them.

**Product** MiniMe · **Source** impeccable, taste-skill, ui-ux-pro-max-skill [README] · **Status** candidate · **Depends** UB-064 · **Decision** none · **Evidence** [README]

**What.** Techniques for the Build and design flows.

**Why.** READMEs only so far; the plan says to verify with before-and-after evals.

**Where.** The Build tab prompts.

**How.** Read, rewrite, run UB-064.

**Done when.** The result beats the "without" run.

### UB-077: Screenshot-to-code for the wireframe flow (M)

> Use ideas from screenshot-to-code to turn an uploaded image into a first wireframe.

**Product** MiniMe · **Source** screenshot-to-code [README] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [README]

**What.** An image-to-wireframe step.

**Why.** Speeds the wireframe flow.

**Where.** `WireframePreview.jsx` and its backend.

**How.** Read the repo and licence; design the prompt and the preview; keep the sandboxed iframe.

**Done when.** A sample image produces a usable wireframe.

### UB-078: A diagram generator from diagram-design (M)

> One self-contained HTML plus SVG file per diagram, across many diagram types.

**Product** MiniMe · **Source** diagram-design (51 types as reported), archify (already in the book pipeline) [README] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [README]

**What.** Diagram generation in the product.

**Why.** archify is already used for the book; this extends the idea to users.

**Where.** The Build tab.

**How.** Read both; choose types users need first.

**Done when.** One type works end to end.

### UB-079: Spike: HTML to deterministic video with hyperframes (M)

> Test whether hyperframes could replace moviepy in the video overview builder.

**Product** MiniMe · **Source** hyperframes [README] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [V✓] [README]

**What.** A short spike with measured output.

**Why.** `video_overview_builder.py` uses `moviepy` and `PIL` [V✓]; replacing moviepy would also remove the Pillow constraint in UB-002 (unverified).

**Where.** `backend/agents/video_overview_builder.py`.

**How.** Render one overview both ways; compare quality, speed, size and determinism.

**Done when.** A written comparison exists.

### UB-080: Study slide-generation references (S)

> Read open-slide and ppt-master for ideas on generating slides.

**Product** MiniMe · **Source** open-slide, ppt-master [README] · **Status** candidate · **Depends** — · **Decision** none · **Evidence** [README]

**What.** A short reading note.

**Why.** Feeds UB-061.

**Where.** None; a note only.

**How.** Read both and write what is reusable.

**Done when.** The note exists.

## Batch B02 (2026-11-24): rust-anything and fast-anything, from a trial on m2c

*Source:* two tools, both MIT (licences read), tried on a scratch copy of m2c in an earlier session, plus the tool's own "Rust migration plan: m2c" report. **Appendix A already plans the Rust work** (`MG-Z04` vectors, the `MG-Z10` gate, `MG-B00` and `MG-B01`), so most of what the trial found is written into Appendix A (a clarification in `MG-Z04`, an optional-tooling note in `MG-Z10`, a Python alternative in section 1.1). Only the three items Appendix A does not plan are features here. Figures from the trial that were not re-run are tagged `[S]`; what was re-checked in the code on 2026-11-24 is tagged `[V✓]`. The tools themselves were **not run** for this batch: building them needs a Rust toolchain that the sandbox could not reach.

### UB-081: Cross-check the MG-Z10 spike with rust-anything (M)

> Use rust-anything to record, diff, fuzz and shadow the Rust redaction port against Python, as a second check beside the vectors.

**Product** M2C · **Source** rust-anything (MIT, read at `b5025d4`), Appendix A `MG-Z04` and `MG-Z10`, trial of 2026-11-24 · **Status** candidate · **Depends** — · **Decision** Use the tool at all, or keep to the hand-written differential run in `MG-Z10` step 6 · **Evidence** [V✓] [R] [S]

**What.** An optional trial inside `MG-Z10`, not a new work package. The tool's loop is: profile, analyze, bridge, record, port, `diff`, `fuzz`, bench, `shadow`, `gate`, then `enable` or `report` [R]. Bridge only `m2c/src/m2c/secrets/redact.py`, as its own unit through PyO3, and let the port be checked against what the Python original does.

**Why.** It is a second, independent check next to the `MG-Z04` vectors. `fuzz` looks for cases the recording missed and `--keep` adds them; `shadow` runs both implementations side by side; `enable` swaps the Rust in for Python callers [R], so the existing secret-handling tests could run against the Rust build (an idea, not tried [U]). The trial bridged 8 functions of `secrets/` and recorded 3,693 cases, 2,199 of them from m2c's own tests [S]. **But** its default corpus held no input with a secret and the longest input was 48 characters; after adding m2c's tests, 46% of the `redact` cases held a secret, covering 14 of the 26 rule kinds, and the 1,223 `contains_secret` cases held none [S]. A Rust `redact` that detected nothing would have passed `diff` on the default corpus.

**Where.** `m2c/src/m2c/secrets/redact.py` imports only the standard library, and `_RULES` holds 26 kinds [V✓]. The tests are in `m2c/tests/secret_handling/` (7 files): all 577 tests pass in a fresh environment with the declared dependencies [V✓, re-run 2026-11-24]. Work in a scratch copy; the tool writes its crates under `rust/`. The inputs to feed it are the `MG-Z04` vectors.

**How.**

1. Read the tool's own warning first: `record`, `diff` and `gate` run your code many times, so use a **copy of the project, a test database and no production credentials**.
2. Write the `MG-Z10` criteria first and commit them (Appendix A rule 10). The tool's `gate` is an extra check, not a replacement for C1 to C3.
3. Run `analyze`, then `bridge` for `redact.py` only (not the `secrets/` folder: see **Notes.**).
4. Feed `record` the `MG-Z04` vectors and the near-miss corpus of C1, with positive rows for `contains_secret` and for all 26 kinds. Do not accept a green `diff` on the default corpus.
5. Run `diff`, `fuzz --keep`, `shadow` and `gate`; read the `report`.
6. Keep the recordings out of git and use **fake secrets only** (built from pieces, as `secret_fakes.py` does), because a recording is a file holding the inputs.

**Done when.** On a corpus that meets C1 (at least 20,000 inputs, at least 2,000 near-misses per detector family) `diff` and `fuzz` show no case where Rust redacts less than Python, and every rule kind has positive rows.

**Notes.** The tool's own report gives `secrets/` a readiness of 27 and `interact/` 64, `trust/` 55; the earlier summary said 25 for `secrets/`, so quote the report. It marked `auth/` as blocked, but the only cause is a lazy `importlib.import_module("keyring")` at `auth/credentials.py:305` [V✓]. It called m2c a server because of the sandbox bridge and probe sockets, which is wrong for a command-line client. Whether PyO3's generated code can satisfy `#![forbid(unsafe_code)]` (C3) was not checked, so keep the port in its own crate. Licence and behaviour were read, not audited.

### UB-082: Port only profiled hot functions with fast-anything (M)

> A Python-staying alternative to a rewrite: profile a real workload, port only the measured hot functions, prove them on recorded calls.

**Product** Shared · **Source** fast-anything (MIT, read at `ccf46b4`), Appendix A `MG-Z10` (Python alternatives) and `MG-B01`, trial of 2026-11-24 · **Status** candidate · **Depends** — · **Decision** None until a real baseline exists · **Evidence** [R] [S] [V✓]

**What.** The tool's loop: `scan` profiles the app and ranks functions by time and portability; `port` records up to 500 real calls and creates a one-function Rust crate; `verify` replays them; `bench` times the whole app; `enable` and `disable` swap it in and out, reversibly [R]. It ports top-level, deterministic functions that take plain data [R].

**Why.** Its premise is to port the slow few percent, not the whole app, which is the "Python alternative" that Appendix A section 1.1 asks you to record if the gate says `STAY PYTHON`. **The trial evidence is thin:** a synthetic workload of 1,500 texts through redaction and 6,000 shell commands through parsing took 3.65 s, with `redact._scan` at 50% of the time and `shellparse.parse` at 19% [S]. That shows what is hot only if those run at volume; real m2c time is mostly model streaming and I/O [S]. Do not port on that evidence. The MiniMe backend was not profiled: there is no load harness yet (`MG-B00`).

**Where.** Candidates: `m2c/src/m2c/secrets/redact.py` (`_scan`) and `m2c/src/m2c/policy/shellparse.py` (`parse`), both pure functions on strings [V✓ by listing]. For the backend, whatever the `MG-B01` baseline shows.

**How.**

1. Wait for the `MG-B00` and `MG-B01` backend numbers. For m2c, define a real workload: a scripted session with fake credentials.
2. Run `fast-anything doctor`, then `scan -- <command>` on a **copy** of the project.
3. Port only functions that are top-level, deterministic and take plain data.
4. `verify` against recorded calls **and** the `MG-Z04` and Q07 corpora; a port in a security path (redaction, policy) must never redact or allow less than Python.
5. `bench` the whole app and adopt only a gain that matters.

**Done when.** A real profile shows a function above an agreed share of run time, the port matches Python on the corpora, and the whole-app `bench` shows a gain worth the extra build step.

**Notes.** It puts a Rust toolchain build on the Python client's install path, which works against benefit B1 in Appendix A; compare it with the single-file bundle. `fast-anything go --agent claude` hands your code to a coding agent: use a copy with no credentials. `port` records real calls, so the same fake-secrets rule as UB-081 applies.

### UB-083: Break the import cycle so m2c units can be bridged one by one (M)

> The tool saw about 20,500 lines in one import cycle; break it only if you choose the unit-by-unit bridge instead of the rebuild.

**Product** M2C · **Source** rust-anything `analyze` on m2c (trial of 2026-11-24, its report read) · **Status** parked · **Depends** — · **Decision** Bridge route against the `minicore` rebuild of Appendix A · **Evidence** [V✓] [S]

**What.** Remove the cross-package imports that tie the units together, for example `secrets/env.py` importing `..paths` and `..logging_setup`, so that units become leaves a tool can port on their own.

**Why.** The tool's report puts `m2c/`, `auth/`, `context/`, `link/`, `sandbox/`, `secrets/`, `store/`, `tools/`, `trust/` and `tui/` (20,498 lines) into one piece, so most of m2c cannot be ported unit by unit. Only `interact/` and `policy/` are outside it (wave 0). Readiness per the report: `interact/` 64, `trust/` 55, `store/` 50, `secrets/` 27, `context/` 18, `policy/` 0 [S].

**Where.** `m2c/src/m2c/secrets/env.py` lines 65 and 66 import `..logging_setup` and `..paths` [V✓]. The other edges come from the tool's report and were not re-derived.

**How.**

1. Re-run `analyze` and read its import graph.
2. Pick the edges to cut (for example pass the config directory and the logger in as parameters).
3. Cut one edge per patch, with the whole M2C test suite as the check.
4. Re-run `analyze`; each of `secrets/`, `store/` and `trust/` should be its own piece.

**Done when.** `analyze` lists those units as separate pieces.

**Notes.** Parked because no current route needs it: Appendix A rebuilds `minicore-*` crates from vectors, and the function-level tools (UB-081 on `redact.py`, UB-082) do not care about the cycle. Reopen it if you decide to bridge units one at a time.

## Batch B03 (2026-11-26): Review of promptfoo, Strix, Hypothesis, Schemathesis and Locust

*Source:* a review of five reference repos, read from source and docs with nothing installed or run, made against MiniMe `121e06c` (2026-11-25); the rest of this file was written at `cd0bc23`. Reference commits: promptfoo `4a30804`, Strix `9ed84f9`, Hypothesis `b9d568c`, Schemathesis `15b71f5`, Locust `5084aa1`. The five licences were read again when this batch was written. In this batch `[R]` is a reading of those repos, and `[S]` is a code check by the review session (greps on MiniMe `121e06c`), carried over and not re-run here. The review's recommendations were taken as the decisions: **EXTEND** items were written into the entries that already exist (edited in place, so they are not repeated here: UB-014 to UB-018, UB-030, UB-031, UB-045, UB-048, UB-056, UB-068), **IDEA ONLY** and **SKIP** items went to section 6, **VERIFY FIRST** items became "verify first" leads in those entries' notes, and the licence rows of section 7 were filled in. Where the work package belongs to another chapter (`Q02`, `Q07`, `L07`, `MG-Z03`, `MG-Z04`), the entry or section 6 row here carries the addition and the chapter was **not** edited. One item is a new feature.

### UB-084: Record what a run created, so undo and approvals touch only that (S)

> A per-run list of the objects an automation created, so cleanup and any approval exemption apply only to things the run itself made.

**Product** Menux · **Source** Strix test-object registry (Apache-2.0, read at `9ed84f9`) [R], Menux feature guide sections 6.1 and 7.5 · **Status** candidate · **Depends** — · **Decision** Whether an object a run created may ever skip an approval (Strix does this; the tiers of section 6.1 of the Menux guide say nothing about it) · **Evidence** [R] [V✓] [U]

**What.** A registry kept for each run: every outside object the run created, with the run and the event that created it, and a state. Strix keeps such a registry of what a run created, can export it, and drops secret-like details when it does [R]. For Menux the design idea is to build it from the local event log of section 7.5 of the Menux guide, which already records tool results, and not to add a second store [U].

**Why.** It gives undo and cleanup a precise target ("only what this run made") and lets an approval rule tell an object the run created from one that was already there. Nothing in the Menux guide records this today [V✓ grep of `menux_feature_guide.md`].

**Where.** Menux has no code yet. The event log of section 7.5 is the source of truth; `m2c/src/m2c/store/events.py` is the closest existing store [V✓ per UB-046].

**How.**

1. Settle the decision above first. Strix's own gate, which lets run-created objects skip approval, guards a careless agent and not a hostile one, so any exemption must not replace the code-enforced tiers of section 6.7 [R].
2. Define the record (object kind, id, run id, creating event id, state). The code writes it from tool results; the model never writes it.
3. Drop secret-like values when the registry is exported, as section 7.5 requires of the log.
4. Use it for undo and cleanup. Use it in an approval rule only if step 1 allows.

**Done when.** After a test run, the registry lists exactly the objects that the run's events show as created. An object of the same kind that existed before the run is not listed. An exported registry holds no secret-like value.

**Notes.** An idea until Menux has an event log; Strix's version was read, not run.

## Batch B04 (2026-11-26): Review of gemini-cli, hermes-agent, mistral-vibe and codex

*Source:* a review of four reference repos (33 capabilities), read from source with nothing installed or run, made against MiniMe `121e06c`; the rest of this file was written at `cd0bc23`. Reference commits read again when this batch was written: gemini-cli `60f8082`, hermes-agent `c84e8d7f`, mistral-vibe `fb7511a`, codex `06f334a`. The four licences were read again. In this batch `[R]` is a reading of those repos, `[V✓]` is a check of MiniMe `121e06c` made while writing it, and `[S]` is a fact carried from the review and not re-read. **The decision column of the review was empty, so its recommendations were taken as the decisions**, as in B03: **ADD** became new features (UB-085, UB-086), **EXTEND** items were written into the entries that exist (edited in place, so they are not repeated here: UB-028, UB-033, UB-036, UB-037, UB-038, UB-042, UB-048, UB-064, UB-075), and **IDEA ONLY** and **SKIP** items went to section 6. Where the work package belongs to another chapter (`L02`, `L04`, `L07`, `C13`, `C25`, `Q07`, `MG-Z10`), the section 6 row carries the addition and the chapter was **not** edited. One new feature, UB-087, is my own idea and not a decision from the review: drop it if you disagree.

**Corrections to the review found while re-reading:** (1) Vibe's strict hooks are an opt-in flag on each hook, not five types that fail closed. (2) Codex's `HookEventName` has 14 events, not 15. (3) The review said to build goal mode after the metering item `S10`; `S10` is already built (`backend/codeagent/metering.py` exists [V✓]). (4) Vibe's goal engine uses Python 3.12 syntax, but the server loop runs on `python:3.12-slim` [V✓], so only code placed in `m2c/` (floor 3.11) is affected. (5) Codex leaves hardening on Windows as an empty TODO, and Python's `resource` module does not exist on Windows, where the dev machine runs.

### UB-085: Switch off core dumps and debugger attach for the M2C client at start (XS)

> Set no-core-dump and no-same-user-debugger-attach for the M2C client before it handles a secret (Linux and macOS), as Codex does.

**Product** M2C · **Source** Codex `codex-rs/process-hardening/src/lib.rs` (Apache-2.0, read at `06f334a`) [R] · **Status** candidate · **Depends** — · **Decision** Whether a failed hardening call stops the client (Codex exits with code 5, 6 or 7) or only warns · **Evidence** [R] [V✓] [U]

**What.** A small function called first in `m2c.cli.main`. On Linux it sets `PR_SET_DUMPABLE` to 0 and the core-file size limit to 0; on macOS it calls `ptrace(PT_DENY_ATTACH)` and sets the core-file limit to 0. Codex does this before its `main` starts, and also strips `LD_*` (Linux) and `DYLD_*` (macOS) variables from its own environment [R]. On Windows Codex does nothing: the function body is a TODO [R].

**Why.** The client's memory holds the session token and the files it reads. A core dump, or a debugger attached by another process of the same user, could read them. The policy engine guards what the model does, not what other local processes do. A grep of `m2c/src` finds no `RLIMIT_CORE` and no `PR_SET_DUMPABLE`, and a grep of `daemon/` finds neither [V✓].

**Where.** `m2c/src/m2c/cli.py` (`main`, line 419 [V✓]); a new `m2c/src/m2c/hardening.py`; `m2c/src/m2c/doctor.py`, which already records the platform, to report the result. The Menux daemon (`daemon/minime_daemon.py`, Python) holds longer-lived secrets and could call the same function.

**How.**

1. Write `harden_process()` with the standard library only (`ctypes`, `resource`, `sys`), so the dependency test of D14 still passes.
2. Linux: call `prctl(PR_SET_DUMPABLE, 0)` through `ctypes.CDLL(None, use_errno=True)`; macOS: `ptrace(PT_DENY_ATTACH)`. Look the constants up in the system headers or `man` pages, they were not read from the OS here [GK].
3. Import `resource` only on Unix: it does not exist on Windows [GK]. On Windows return "not applied: windows" and keep starting. No per-process Windows equivalent was looked at [U].
4. Call it before the configuration and the auth store are read, and keep the result (applied, failed, unsupported) for `m2c doctor`.
5. Decide the failure policy (see **Decision**). Add a documented opt-out for debugging, because a process that is not dumpable cannot be attached to by tools such as `gdb` or `py-spy` [GK].
6. Separate question, a design idea [U]: Codex's environment stripping does not carry over, because Python has already loaded what `LD_PRELOAD` points to. The sandbox starts commands with `--clearenv` [V✓ `sandbox/bwrap.py`], so `LD_*` does not reach them there. `secrets/env.py` is a deny list by name and does not name `LD_PRELOAD` or `DYLD_INSERT_LIBRARIES` [V✓], so for a run outside bwrap decide whether to add those two names (not all `LD_*`: toolchains use `LD_LIBRARY_PATH`).

**Done when.** On Linux a test run in a subprocess reads back `PR_GET_DUMPABLE` as 0 and `RLIMIT_CORE` as (0, 0) after the call. A macOS test is skipped elsewhere. On Windows `m2c` still starts and `doctor` says hardening was not applied. The dependency test still passes.

**Notes.** An idea nobody has run here; Codex's version was read, not run. It is a dozen lines of system calls: write them fresh and keep the Codex file as the reference, so no notice is needed in your code.

### UB-086: Session goal mode with a token budget and a no-progress stop (M)

> One goal the agent works on across turns; it stops at a token budget, after 3 turns without progress, or after 3 turns of failed tools.

**Product** M2C · **Source** Mistral Vibe `vibe/app_server/_goal_engine.py` (Apache-2.0, read at `fb7511a`) [R] · **Status** candidate · **Depends** — · **Decision** Whether to build it only after UB-028 and UB-036, so the goal reuses their evidence ledger and loop stop instead of a second copy · **Evidence** [R] [V✓] [U]

**What.** A goal mode. The person states one objective; after each turn, if the goal is still active and nothing stopped it, the loop adds a continuation turn. In Vibe's engine [R]: a turn ends the goal as paused (user interrupt), usage-limited, blocked (a failed turn, 3 turns with no progress or 3 turns of failed tools: `STREAK_LIMIT = 3`) or budget-limited, and the model itself can mark it complete, blocked or paused. The token budget and what is left of it are told to the model. The objective is HTML-escaped and wrapped in a `<goal_objective>` block so it reads as data. The continuation prompt asks for work from evidence, and a completion must name its evidence (a test run, command output or a file).

**Why.** Today a run ends when the model stops, and a long task needs the person to type "continue". There is no goal mode in M2C: the only match for "goal" in `m2c/src` is in `store/migrations.py` and is unrelated [V✓]. The earlier review said to wait for the metering item `S10`; it is built (`backend/codeagent/metering.py` [V✓], and the build plan lists it as built), so the budget has a source.

**Where.** `backend/codeagent/loop.py` and `backend/codeagent/metering.py` (the server loop owns budgets and stop rules); `run_manager.py` and `runs.py` for per-run state; `protocol/v1/` for additive messages (set goal, goal status); the TUI. The server runs on Python 3.12 [V✓ `backend.Dockerfile`], and Vibe's file uses `type` aliases (3.12 syntax) [R]; the 3.11 floor of D1 applies only to code in `m2c/`.

**How.**

1. Settle the decision above.
2. Keep a goal record per run: objective, token budget, status, reason and two streak counters. Write changes as events in the append-only store and not as a mutable table [U].
3. After each turn apply Vibe's rule order [R]: user interrupt, usage limit, failed turn, budget reached, no-progress streak of 3, failure streak of 3.
4. Build the continuation message with the objective inside an escaped, marked block (use UB-087), the tokens used and left, and the rule that completion needs named evidence. Check that evidence against the UB-028 ledger [U].
5. Make a budget mandatory. Vibe allows no budget at all (`token_budget is None` [R]); do not copy that default [U].
6. Every continuation goes through the normal policy and approvals, and a goal never widens a permission. A call that needs approval pauses the goal with a visible status instead of being denied silently [U].
7. Add the protocol messages with fixtures.

**Done when.** Fake-model tests: a goal completed with evidence ends `complete`; three turns that change nothing end `blocked` with the reason; three turns of failed tools end `blocked`; the token budget stops the run; an objective that contains `</goal_objective>` stays inside its block; a user interrupt pauses the goal.

**Notes.** Runaway cost is the main risk, so the budget and the step limit both stay in force. Take the rules, not the code: Vibe's engine is tied to its own goal-state types. If code is ever copied, the Apache-2.0 notice and a mark on the changes are required.

### UB-087: One helper that frames text the model must treat as data (S)

> Steering messages, compaction summaries and goal objectives all need the same escaping, marker and look-alike handling; write it once.

**Product** M2C · **Source** my idea, from Hermes `agent/prompt_builder.py` (MIT, `c84e8d7f`), Gemini CLI `prompts/snippets.ts` (Apache-2.0, `60f8082`) and Vibe `_goal_engine.py` (Apache-2.0, `fb7511a`) [R] · **Status** candidate · **Depends** — · **Decision** Build it before UB-037, UB-042 and UB-086, or let each write its own and merge them later · **Evidence** [R] [V✓] [U]

**What.** One module in `backend/codeagent/` with three parts: a function that escapes, wraps and marks a piece of text for a named kind of frame; a function that relabels text imitating one of your own frames inside a tool result; and one list of the frame kinds. Users would be the steer message of UB-037, the goal envelope and summary of UB-042, the objective of UB-086, and the existing `NOTICE_*` messages.

**Why.** Three entries each need a marker, and each marker is a place where a look-alike can get through. Hermes needed a list of strings that imitate its control frames [R], Gemini tells its summariser to ignore instructions found in the history [R], and Vibe escapes the objective so it cannot close its own block [R]. One shared list makes a new kind of frame get the same cover. This is an idea; nobody has run it.

**Where.** `backend/codeagent/prompts.py`, `loop.py` (`NOTICE_*`), `context.py`. The files that already mention an injection guard are `broker.py`, `prompts.py` and `adapters/toolcalls.py` [V✓ grep]; read how they mark outside text first and reuse it if it fits.

**How.**

1. Read the current markers (`NOTICE_*` and the injection guard files above).
2. Define the frame kinds and one escaping rule: escape `<`, `>` and `&`, as Vibe does for the objective, so text cannot close its own tag [R].
3. Write the look-alike relabelling and apply it only to tool results on their way to the model. Keep the original in the stored log, so UB-042's lossless log stays lossless.
4. Write a table test: each frame kind against hostile payloads (a closing tag, a look-alike heading, a nested marker).
5. Use it in UB-037, UB-042 and UB-086.

**Done when.** For every frame kind, no hostile payload can close or forge the frame. A tool result that contains any kind's marker is relabelled. The existing prompt tests pass.

**Notes.** The risk is a relabelling list that mangles real output, for example a README that contains the words "Runtime note:". That is why step 3 relabels only inside tool results and keeps the stored original.
