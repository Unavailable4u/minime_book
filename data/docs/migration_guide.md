# Migration Guide: Rust, TypeScript and a Hardened Python Backend

*Minime agentic automation: what to convert, what to keep, and the order to do it*

**Version 1.1 · 2026-11-21 (first issued 2026-11-14) · Appendix A of the connected book (it is not one of the 14 chapters).** Companion to `m2c_build_plan.md` (rev 1.2), `m2c_feature_guide.md` (rev 1.2), `Menux___Build_Execution_Guide.md` (rev 1.2) and `protocol/README.md` in the MiniMe repo. Where this guide and one of those disagree about **which language something is written in**, this guide wins; on everything else they win.

> **What this guide does.** It turns one decision into work: the M2C client and the Menux node are rebuilt in **Rust**, the web frontend and the Menux controller move to **TypeScript**, and the **backend stays Python** and is hardened and measured. It lists 43 patch-sized work packages (`MG-*`), their order, how each is proven correct, and what to do with the old `daemon/`.
>
> **Revision 1.1 (2026-11-21): the Rust decision is now a gate, not a given.** The benefits of the Rust client were argued in revision 1.0, not measured. Revision 1.1 adds a time-boxed spike, `MG-Z10`, with written pass criteria and three possible outcomes (`PROCEED`, `STAY PYTHON`, `EXTEND ONCE`); decisions `DM-2`, `DM-3` and `DM-9` are provisional until it records `PROCEED` (§1.1). Every `MG-R*` package, and the book edits in `MG-Z09`, now wait for it. Revision 1.1 also adds §9.1, which orders this migration against the **Provider Consolidation Guide** (Appendix B) so the two never edit the same file at once. Everything in the **Z** track except `MG-Z09`, and the **F**, **D** and **B** tracks, is unaffected by the gate.
>
> **Evidence basis.** Read from the MiniMe repo at commit `94af156` ("wave 9 part 2 complete") and the book at `aaca7f1`. **No tests were run, nothing was built, and no crate or package version was checked** (revision 1.1 adds one run: see §13). Line numbers and counts are from those commits and will drift. Where a statement depends on something that was not verified, the work package that verifies it is named.
>
> **No calendar.** Work is ordered by dependency, not by date. Sizes use the book's scale (S = 1, M = 2, L = 4, XL = 8 points) and are estimates.

---

## 0. How to use this guide

- **Read §1 to §4 once.** They are the decisions, the target picture, the facts the plan rests on, and the rules that stop the migration from going wrong.
- **Work from §5.** Pick a work package whose dependencies are done, open its entry in §6, generate one patch with the template in §11.
- **Start with the gate.** Do `MG-Z00` to `MG-Z07` first, then `MG-Z10` (§1.1). Do not start any `MG-R*` package until `MG-Z10` has written `PROCEED` in a decision record.
- **The patch workflow is the one in `m2c_build_plan.md` §0**: one work package is one patch, tests first, one writer per shared file, log each patch in `PATCHES.md`, regenerate rather than hand-edit hunks.
- **Prefix.** Work packages are `MG-<track><nn>` (for example `MG-R03`). **Always write the `MG-` prefix.** The M2C build plan already has `B00` to `B12` (browser cleanup), the Menux guide has `R05` and `D02`, and both books number their decisions `D1` to `D38`, so a bare `B03`, `R05` or `D04` is ambiguous. Tracks: **Z** foundations, **F** frontend, **D** daemon retirement, **B** backend hardening, **R** Rust client.

---

## 1. Decisions

| ID | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| **DM-1** | **The backend, including `backend/codeagent/`, stays Python** and is hardened and measured (track B). | It is I/O-bound (model streams, Postgres, Redis, device sockets) and already `async` where it matters. It is wired into `backend/eo/` (ledger, devices, provider keys) and changes with every prompt and adapter. The wire contract already isolates it from the clients. | `MG-B06` decides with numbers from `MG-B00`/`MG-B01`. |
| **DM-2** | **Provisional until `MG-Z10` records `PROCEED`.** The M2C client is rebuilt in Rust, as a Cargo workspace whose shared crates are named `minicore-*` from day one. | It runs on the user's machine: one static-ish binary, no Python to install, small idle footprint, and compile-time checking where the safety code lives (policy, paths, redaction, sandbox). | `MG-Z10` (§1.1). After `PROCEED`: never for the safety crates; the TUI library is an open choice (§12). |
| **DM-3** | **Provisional until `MG-Z10` records `PROCEED`.** The Menux node is built in Rust on the same crates; the **phone/web controller is TypeScript**; **browser automation is a TypeScript sidecar** process behind `ControlBackend` (MX9). | Menux has not started (planned after M2C reaches M2), so nothing is ported: it is built right the first time. Playwright's supported bindings are Node, Python, Java and .NET, not Rust. | `MG-Z10` (§1.1); after `PROCEED`, per connector in Phase 3 (§8). If the gate says `STAY PYTHON`, the Menux node follows the file names the Menux build guide already uses (`.py`). |
| **DM-4** | **The frontend moves to TypeScript, leaf-first and file by file.** No big-bang, no freeze. Independent of the Rust gate. | 109 `.jsx` and 73 `.js` files in Next.js 14; Next compiles TypeScript natively, and JS and TS can coexist. | At the `MG-F02` checkpoint (§6.2): each converted file stands alone, so the track can stop at any point. |
| **DM-5** | **The contract is data.** Wire: `protocol/v1/*.json` plus `protocol/fixtures/`. Behavior: `protocol/conformance/` vectors (new). Every language must pass the same files. | This is what makes a three-language system safe to change. A Rust port is "done" when it passes what the Python reference passes. | Never. |
| **DM-6** | **`daemon/` is retired, not ported.** M2C already ported its path guard and file tools and went well beyond it. | See §6.3: it is not a plain deletion, because the daemon's approval gate is shared with server-side MCP. | `MG-D00` records the option chosen. |
| **DM-7** | **`uv` replaces `pip` for installs** in CI and Docker. Pinned `requirements.txt` files stay; no lockfile migration now. | Near-free and faster. | Never. |
| **DM-8** | **Python M2C is frozen at a tag and kept as the reference.** It is deleted only after the Rust client has shipped and one release has overlapped. | The reference is what the vectors and the differential tests are proven against. | After `MG-R13`. |
| **DM-9** | **After `MG-Z10` records `PROCEED`, client work packages not yet built are built in Rust**, never in Python first (§7). Server halves stay Python. Until then, and if the gate says `STAY PYTHON`, they are built in Python as the build plan says. | Building in Python and porting later is paying twice, once the language is settled. | `MG-Z10`. |
| **DM-11** | **The Rust choice is a gate.** `DM-2`, `DM-3` and `DM-9` stand only after a time-boxed spike (`MG-Z10`) meets criteria written down **before** the spike starts. The outcome is `PROCEED`, `STAY PYTHON` or `EXTEND ONCE`, and it is recorded in an ADR. | The benefits of Rust here (install, footprint, compile-time checks) were argued, not measured, and the port is about 55 points. A spike costs a small fraction of that and turns an opinion into a recorded result. | Only through a new, dated ADR. |
| **DM-10** | **Rust must never be more permissive than the Python reference** on any policy, path or redaction case, unless a reviewed note says the reference was too strict. | These are the safety properties. A port that is faster and looser is a regression. | Never. |


### 1.1 The Rust decision gate (`MG-Z10`)

**What is being decided.** Whether the M2C client and the Menux node are built in Rust (`DM-2`, `DM-3`, `DM-9`), or stay in Python. The F, D and B tracks and the conformance vectors do not depend on the answer: the vectors are a language-neutral specification and are worth having either way.

**What the spike is.** A time-boxed port of `minicore-secrets` (the redaction code, `m2c/src/m2c/secrets/redact.py` and `env.py`) in Rust, run against the `MG-Z04` vectors and a differential corpus. It is chosen because it is the hardest small piece: it is security code, it uses regex features Rust's `regex` crate is said not to support (lookaround, possessive quantifiers), it has a ready-made oracle (the Python reference) and it is small enough to finish. Full procedure: `MG-Z10` in §6.1.

**The three outcomes.**

| Outcome | When | What changes |
| --- | --- | --- |
| **PROCEED** | All hard criteria (C1 to C3) pass **and** at least one benefit criterion (B1 to B3) passes. | `DM-2`, `DM-3`, `DM-9` become final. `MG-Z09` runs (the guides are edited to say Rust). The `MG-R*` packages start. The spike's code becomes the first draft of `MG-R02`. |
| **STAY PYTHON** | A hard criterion fails, or no benefit criterion passes. | `DM-2`, `DM-3` and `DM-9` are reversed by ADR. The Python client stays the product. The Menux node is built in Python on the `minicore` package, as the Menux build guide already describes. `MG-Z09` does not run; the list below does instead. The conformance vectors stay and run on the Python client. |
| **EXTEND ONCE** | The result is inconclusive for a reason you can name (for example, one pattern family is still unresolved and the rest passed). | One more time-box, with the reason written in the ADR. A second `EXTEND ONCE` is not allowed: the next result must be `PROCEED` or `STAY PYTHON`. |

**If the outcome is `STAY PYTHON`, apply these edits** (a short patch; nothing else in this guide needs to change):

1. Mark `DM-2`, `DM-3`, `DM-9` as **reversed by ADR-xxxx** and set `DM-8` to "Not applicable".
2. In §5, mark every `MG-R*` package and `MG-Z08`'s Rust half, `MG-Z07` and `MG-Z09` as **dropped**, and keep `MG-Z08`'s TypeScript half.
3. In `m2c_build_plan.md` and `Menux___Build_Execution_Guide.md`, leave the Python wording as it is. Add one line to each, pointing at the ADR.
4. Keep `protocol/conformance/` and its Python runner. They become the regression suite for the Python client.
5. Record, in the ADR, which Rust benefits were still wanted and what the Python alternatives are (for example: shipping the client as a single-file bundle with its own interpreter, if install friction was the reason; or, if speed was the reason, porting only the functions that a real profile shows to be hot and keeping the client in Python, as `fast-anything` does: see `UB-082` in Appendix C).

**Who decides.** You. The gate is a method for not deciding from opinion: the criteria are written first (§6.1, `MG-Z10`, step 1), the measurements are taken, and the outcome follows from the table.

---

## 2. Target architecture

```
                         ┌────────────────────────────────────────────────┐
   protocol/             │  CONTRACT (data, language-neutral)             │
                         │  protocol/v1/*.json      wire schemas          │
                         │  protocol/fixtures/      golden transcripts    │
                         │  protocol/conformance/   behavior vectors (new)│
                         └───────────────┬───────────────┬────────────────┘
                                         │               │
              ┌──────────────────────────┘               └─────────────────────────┐
              │ every consumer must pass the same files                              │
              ▼                                                                      ▼
   ┌─────────────────────┐   WS /v1/code/device   ┌──────────────────────────────────────┐
   │ DEVICE (Rust)       │◄──────────────────────►│ SERVER (Python, hardened)            │
   │ m2c  (CLI, TUI)     │   protocol v1          │ backend/codeagent  loop, broker,     │
   │ menux node (later)  │                        │   buffer, metering, ws               │
   │ crates: minicore-*  │                        │ backend/eo  ledger, devices, ...     │
   │  protocol paths     │                        │ backend/api  REST for the web app    │
   │  secrets policy     │                        │ relay / gateway (language: MG-B06)      │
   │  store link auth    │                        └───────────────▲──────────────────────┘
   │  sandbox            │                                        │ REST + realtime
   └─────────┬───────────┘                                        │ (OpenAPI types, MG-F01)
             │ JSON over stdio                       ┌────────────┴─────────────┐
             ▼                                       │ WEB (TypeScript, Next 14)│
   ┌─────────────────────┐                           │ frontend/app             │
   │ browser sidecar (TS)│                           │ Menux controller (TS)    │
   │ Playwright, no keys │                           └──────────────────────────┘
   └─────────────────────┘
```

Two rules hold the picture together: **the device and the server meet only at the protocol**, and **a language boundary is always a data boundary** (JSON schema, JSON-RPC over stdio, or OpenAPI), never a shared library.

---

## 3. What the code says today

All from the commits named above. "Lines" are physical lines.

| Area | Fact | Why it matters here |
| --- | --- | --- |
| **M2C client** | `m2c/src/m2c/`: 27,152 lines of Python, 105 test files, 37,411 lines of tests. Runtime deps: `websockets` (only `m2c/link`), `prompt_toolkit` and `rich` (only `m2c/tui/app.py`), enforced by a test (D14). | The tests are bigger than the code. They are the real specification and the main asset of the port. |
| **M2C size by package** | `tools` 3,581 · `sandbox` 3,193 · `policy` 3,115 · `tui` 3,004 · `link` 1,959 · `context` 1,530 · `auth` 1,420 · `checkpoints.py` 1,301 · `store` 1,233 · `headless.py` 1,190 · `runner.py` 1,146 · `secrets` 932 · `trust` 836 · `doctor.py` 481 · `cli.py` 468 · `repl.py` 421 · `session_setup.py` 413 · `interact` 408 | Sets the port order and the sizes in §5. |
| **Policy engine** | `policy.decide(request, context) -> Decision`: "all of it is data, none is read from the environment". `shellparse.parse` alone is a ~1,200-line function family. | A pure function is the best possible port target: inputs and outputs can be written down as vectors. |
| **Secret redaction** | `secrets/redact.py` uses **11 lookaround assertions** (`(?<!…)`, `(?!…)`) and **2 possessive quantifiers** (`{0,64}+`, `{20,200}+`). Rust's `regex` crate **rejects lookaround at compile time** and **accepts the possessive quantifiers without error but gives them a different meaning** (checked in revision 1.2, §13): `[a-z]{2,5}+a` never matches `aaaa` in Python 3.11 and later, and matches it in Rust. `context/instructions.py` also uses a lookbehind and a backreference (the code-span pattern `` (`+).+?\1 ``). | The most surprising cost of the port (see `MG-R02`, `MG-R08`). |
| **Fake secrets in tests** | `m2c/tests/secret_handling/secret_fakes.py` assembles every fake secret **at run time from pieces**, because Gitleaks runs in the pre-commit hook and CI and `m2c/tests/` is not on its allowlist. | Vectors cannot simply contain fake keys as literals (see `MG-Z04`). |
| **Wire contract** | `protocol/v1/`: 15 message types, 11 tool schemas, Draft 2020-12, cross-file `$ref`. 4 golden transcripts (13, 26, 26, 15 lines) and 60 invalid examples that must each fail on a named keyword and path. `validate.py` also keeps a byte-identical client copy at `m2c/src/m2c/protocol/v1/`. | Ready-made conformance for the wire. The client copy path must move (`MG-Z08`, `MG-R00`). |
| **Socket limits** | `codeagent/ws.py`: hello timeout 10 s, max message 1 MiB, max 3 parallel runs, credential revalidation **every 30 s per connection**, close codes 1008/1009/1011/4400/4401/4403/4408/4409/4426/4429. | Revalidation alone means N/30 credential checks per second for N connected devices (1,000 → ~33/s; 10,000 → ~333/s). `MG-B01` measures what each costs. |
| **Connection registry** | `codeagent/connections.py` `InMemoryRegistry`: live sockets of this process only, by design; `S11` is to add cross-process presence in Redis and a Redis-backed handshake limiter. `buffer.py` talks to Redis through the Upstash client (`memory.bus.redis`). | The scale work (track B) is already designed in the code's own comments. |
| **Async vs sync** | Backend: 221 `async def` against 2,411 plain `def`. Outside tests and scripts, **26 `requests.*` calls and 7 `time.sleep` calls** (33 sites) in `agents/`, `utils/`, `api/` and `eo/`. | Not necessarily a problem: plain `def` handlers and dependencies run on FastAPI's threadpool, so a blocking call there ties up a worker thread, not the event loop. But the sites are unclassified (`MG-B04`). |
| **Frontend** | `app/components` 100 `.jsx`, `app/context` 8 `.jsx`, `app/lib` 55 `.js`, `app/hooks` 11 `.js`. No `tsconfig.json`, no `jsconfig.json`, no PropTypes. Next 14.2.35, React 18.3.1. Tests: 49 `*.test.mjs` run by `node --test`, CI on **Node 22.22.0**. | TypeScript can start immediately; tests are plain Node. |
| **Giant frontend files** | `NotebooksTab.jsx` 3,690 · `SessionContext.jsx` 2,718 · `WorkspaceChatPanel.jsx` 2,601 · `EditorWorkbench.jsx` 2,448 · `BuildTab.jsx` 2,067 · `GrowthTab.jsx` 1,822 · `TestTab.jsx` 1,600 · `WorkspaceDockContext.jsx` 1,590 | These eight need a staged conversion (`MG-F00`, `MG-F04`). |
| **Daemon** | `daemon/`: 16 files. Backend side: `eo/local_workspace.py` (WS `/ws/daemon/{workspace_id}`), `eo/local_workspace_tools.py`, `api/routes/local_workspace.py`. **`api/routes/mcp.py` and `eo/mcp_agent_tools.py` reuse the daemon's approval functions.** A code comment says the routes and daemon "stay until M2C Phase 5". | Retiring it is a small refactor first, then deletions (§6.3). |
| **Measured startup of the Python client** | In this guide's cloud sandbox, 5 runs each: `m2c --version` 117–130 ms; `m2c doctor` 134–174 ms; bare `python -c pass` 14 ms; importing the TUI libraries ~155 ms warm (458 ms cold). Not your machine. | A baseline for `MG-R12`, not a reason to port: against model replies that take seconds, this is not what users feel. The reasons are in DM-2. |

---

## 4. Rules of the migration (stop the line)

If any of these is broken, stop and fix it before the next patch.

1. **A vector enters `protocol/conformance/` only if the frozen Python reference passes it.** The vectors describe what exists, so a failing vector is a bug in the vector.
2. **Never edit a vector to make Rust pass.** A vector changes only with a written reason, and, if it makes a safety decision looser, a second look. Rule DM-10 applies.
3. **The protocol changes only by addition**, schema first. Regenerate the Rust and TypeScript types and the fixtures in the same patch.
4. **No new Rust dependency without an entry in `rust/deps-allowlist.toml`** (name, exact version, reason, licence). This is D14 in Rust form. Pin exactly and use only releases that are more than two weeks old, as the Python side does.
5. **`#![forbid(unsafe_code)]` in every crate.** An exception is one named module with a recorded reason (the likely candidates are in `minicore-paths` and `minicore-sandbox`).
6. **Security code fails closed and is differential-tested**, not only unit-tested (`MG-R02`, `MG-R03`).
7. **One writer per shared file at a time**, as in the existing plan. Shared files in this migration: `.github/workflows/ci.yml`, `protocol/validate.py`, `backend/api/server.py`, `frontend/package.json`.
8. **No `// @ts-nocheck` outside the allowlist** `frontend/ts-nocheck-allowlist.txt`, and that list may only shrink.
9. **Do not delete a Python module until its Rust replacement has passed `MG-R12`**, and do not delete the Python client until one release after `MG-R13` (DM-8).
10. **No `MG-R*` package starts, and `MG-Z09` does not run, until `MG-Z10` has recorded `PROCEED`** in an ADR. The criteria in that ADR are written before the spike starts and are not edited afterwards (§1.1).
11. **Follow §9.1 when this migration and the Provider Consolidation Guide are both in flight**: the backend files they share have one writer at a time, and the Consolidation Guide goes first on them.

---

## 5. Work-package index

| ID | Work package | Size | Depends on | Wave |
| --- | --- | --- | --- | --- |
| **MG-Z00** | Freeze and tag the Python M2C reference | S | - | 1 |
| **MG-Z01** | Switch Python CI and Docker installs to uv | S | - | 1 |
| **MG-Z02** | Conformance vector format and Python runner | M | MG-Z00 | 2 |
| **MG-Z03** | Policy vectors (decide, rules, modes, shell parsing) | L | MG-Z02 | 3 |
| **MG-Z04** | Secret-redaction vectors | M | MG-Z02 | 3 |
| **MG-Z05** | Path-guard vectors (M2C and daemon cases) | M | MG-Z02 | 3 |
| **MG-Z06** | Local-store compatibility fixtures | S | MG-Z00 | 2 |
| **MG-Z07** | Rust workspace, toolchain and CI | M | MG-Z00 | 2 |
| **MG-Z08** | Protocol codegen (Rust, TypeScript) and fixture replay | M | MG-Z07 | 3 |
| **MG-Z09** | Book edits for the new plan (runs only on `PROCEED`) | S | MG-Z10 | 5 |
| **MG-Z10** | Rust decision gate: the `minicore-secrets` spike | L | MG-Z04, MG-Z07 | 4 |
| **MG-F00** | TypeScript foundation and test-runner spike | M | - | 1 |
| **MG-F01** | Generate API types from FastAPI's OpenAPI | M | MG-F00 | 2 |
| **MG-F02** | Convert app/lib modules | L | MG-F00, MG-F01 | 3 |
| **MG-F03** | Convert hooks and context providers | M | MG-F02 | 4 |
| **MG-F04** | Convert components, directory by directory | XL | MG-F03 | 5 |
| **MG-F05** | Strict everywhere, drop allowJs | M | MG-F04 | 6 |
| **MG-D00** | Decide the fate of the shared action gate | S | - | 1 |
| **MG-D01** | Extract the neutral action gate | M | MG-D00 | 2 |
| **MG-D02** | Remove frontend daemon surfaces | S | MG-D01 | 3 |
| **MG-D03** | Remove backend daemon routes, registry and events | M | MG-D01, MG-D02 | 4 |
| **MG-D04** | Delete daemon/ and its CI job | S | MG-D03, MG-Z05 | 5 |
| **MG-B00** | Load-test harness | M | - | 1 |
| **MG-B01** | Baseline run, numbers recorded in the book | S | MG-B00 | 2 |
| **MG-B02** | Redis-backed presence and handshake limiter | M | MG-B01 | 3 |
| **MG-B03** | Gateway process split | L | MG-B02 | 4 |
| **MG-B04** | Blocking-call audit on hot paths | M | MG-B01 | 3 |
| **MG-B05** | Typing ratchet and response models | M | - | 1 |
| **MG-B06** | Gateway language decision record | S | MG-B03, MG-B04 | 5 |
| **MG-R00** | minicore-protocol | M | MG-Z08, MG-Z10 | 5 |
| **MG-R01** | minicore-paths | M | MG-Z05, MG-Z07, MG-Z10 | 5 |
| **MG-R02** | minicore-secrets (starts from the `MG-Z10` spike) | L | MG-Z04, MG-Z07, MG-Z10 | 5 |
| **MG-R03** | minicore-policy | XL | MG-Z03, MG-R01 | 6 |
| **MG-R04** | minicore-store | M | MG-Z06, MG-Z07, MG-Z10 | 5 |
| **MG-R05** | minicore-link and minicore-auth | L | MG-R00, MG-R04 | 6 |
| **MG-R06** | minicore-sandbox | XL | MG-R01, MG-Z07 | 6 |
| **MG-R07** | m2c-tools and the tool runner | L | MG-R00, MG-R01, MG-R02, MG-R03, MG-R05, MG-R06 | 7 |
| **MG-R08** | m2c-context, trust and interact | M | MG-R03, MG-R04 | 7 |
| **MG-R09** | m2c-checkpoints | M | MG-R01, MG-R04 | 6 |
| **MG-R10** | m2c-headless, cli and doctor | L | MG-R07, MG-R08, MG-R09 | 8 |
| **MG-R11** | m2c-tui | XL | MG-R07, MG-R08, MG-R09 | 8 |
| **MG-R12** | Parity suite and install test | L | MG-R10, MG-R11 | 9 |
| **MG-R13** | Cutover to the Rust client | S | MG-R12 | 10 |

**Totals**

| Track | Work packages | Points |
| --- | --- | --- |
| Z · Foundations | 11 | 22 |
| F · Frontend to TypeScript | 6 | 20 |
| D · Retire the daemon | 5 | 7 |
| B · Backend hardening (Python) | 7 | 14 |
| R · M2C client to Rust | 14 | 55 |
| **All** | **43** | **118** |

**Waves** (everything in a wave can run in parallel once the previous waves it depends on are done):

| Wave | Work packages |
| --- | --- |
| 1 | MG-Z00, MG-Z01, MG-F00, MG-D00, MG-B00, MG-B05 |
| 2 | MG-Z02, MG-Z06, MG-Z07, MG-F01, MG-D01, MG-B01 |
| 3 | MG-Z03, MG-Z04, MG-Z05, MG-Z08, MG-F02, MG-D02, MG-B02, MG-B04 |
| 4 | MG-F03, MG-D03, MG-B03, **MG-Z10 (the gate)** |
| 5 | MG-F04, MG-D04, MG-B06, MG-Z09, MG-R00, MG-R01, MG-R02, MG-R04 (all `MG-R*` and `MG-Z09` only on `PROCEED`) |
| 6 | MG-F05, MG-R03, MG-R05, MG-R06, MG-R09 |
| 7 | MG-R07, MG-R08 |
| 8 | MG-R10, MG-R11 |
| 9 | MG-R12 |
| 10 | MG-R13 |

Sizes are estimates on the book's scale. By points, the critical path is `MG-Z00 → MG-Z02 → MG-Z04 → MG-Z10 → MG-R01 → MG-R03 → MG-R07 → MG-R11 → MG-R12 → MG-R13` (36 of the 118 points): the gate comes first, then the policy crate, then the tool runner and the TUI. (Without the gate, as in revision 1.0, it was 32 of 114.) The policy vectors (`MG-Z03`) are the longest pole *before* the gate, and they run in parallel with it. By count, the longest chain is ten work packages (the ten waves). The **F**, **D** and **B** tracks run beside it and do not block it, except that `MG-D04` needs `MG-Z05` (the daemon's path-guard cases must be harvested before `daemon/` is deleted).

---

## 6. Work packages in detail

### 6.1 Track Z · Foundations

#### MG-Z00 · Freeze and tag the Python M2C reference · S · Wave 1

*Files:* a git tag, and a new `m2c/PARITY.md`.

*What:*

1. Tag the commit the Python client is frozen at: `git tag -a m2c-py-ref -m "Python M2C reference for the Rust migration"` (at the time of writing, `94af156`). Push the tag.
2. Write `m2c/PARITY.md`: the checklist the Rust client must meet. Copy it from the code, not from memory: every command and flag in `m2c --help`; the exit codes (0 success, 1 general failure, 2 usage, 3 policy denial, 4 quota, 5 not logged in or revoked, 130 Ctrl-C, 143 SIGTERM); the environment variables (`M2C_HOME`, `M2C_LOG_LEVEL`, `M2C_SERVER_URL`); the 11 tools; the three modes (`plan`, `ask`, `accept-edits`); what is written under `M2C_HOME`; and the list of built work packages from `m2c_build_plan.md` §0.6.
3. State the freeze rule at the top of that file: after the tag, `m2c/` (Python) accepts **only security fixes**, and each one lands together with a conformance vector.
4. What is **not** frozen: `backend/codeagent/`, `backend/eo/`, `protocol/` (additive changes only).

*Done when:* the tag is pushed and `PARITY.md` has been checked line by line against `m2c --help` run at the tag.

#### MG-Z01 · Switch Python CI and Docker installs to `uv` · S · Wave 1

*Files:* `.github/workflows/ci.yml`, `backend.Dockerfile`, any README that says `pip install`.

*What:* `uv pip install` is a drop-in for the fully pinned requirement files you already have.

- **CI** (line numbers at `94af156`): `pip install -r requirements.txt` in `test` (58), `canary` (401) and `promptfoo` (535); `pip install -e ".[dev]"` in `m2c-test` (211); `pip install -r protocol/requirements.txt` in `protocol` (328); `pip install ruff==0.17.1` in `lint` (74); `pip install --no-deps -e ../m2c` in `canary` (404). Line 105 belongs to the `daemon-test` job, which `MG-D04` deletes, so leave it.
- **Docker:** `RUN pip install --no-cache-dir -r requirements.txt` becomes `uv pip install --system --no-cache -r requirements.txt`, with the `uv` binary copied from Astral's published image **pinned by version** (`COPY --from=ghcr.io/astral-sh/uv:<version> /uv /usr/local/bin/uv`). Look the version up at the time; none is chosen here.
- **Actions:** if you add a setup action, pin it by commit SHA with a version comment, like every other action in `ci.yml`. The SHA is not given here because it was not looked up.
- **Do not** introduce a `uv.lock`, change build backends, or touch `m2c/pyproject.toml` (it still uses `hatchling` until `MG-R13`). The `requirements.txt` comments explaining pin conflicts (the `click` cap from `guardrails-ai`, the `lxml` pin) stay as they are.

*Done when:* every job is green, the backend image builds, and the before/after time of the `test` job and of the image build is in the patch description. If `uv` rejects a pin set that `pip` accepted, treat that as a real finding about the pins, not a reason to revert.

#### MG-Z02 · Conformance vector format and Python runner · M · Wave 2

*Files:* `protocol/conformance/README.md`, `protocol/conformance/schema/vector.json`, `protocol/conformance/run_python.py`, CI job `conformance-python`.

*What:* one JSON object per line, one decision per line, in `protocol/conformance/<area>/<name>.jsonl`.

```json
{"id": "policy/shell/compound-with-denied-part",
 "area": "policy",
 "desc": "A compound command is as bad as its worst part",
 "input": {
   "request": {"tool": "bash", "input": {"command": "ls && curl http://x"}, "risk": "R2"},
   "context": {"mode": "ask", "project_root": "/home/u/proj", "home": "/home/u",
               "project_trusted": false, "non_interactive": false, "cwd": null,
               "layers": {"user":    {"allow": ["bash(ls)"], "ask": [], "deny": ["bash(curl:*)"]},
                          "managed": {"allow": [], "ask": [], "deny": []},
                          "project": {"allow": [], "ask": [], "deny": []}}}},
 "expect": {"action": "deny"},
 "source": "m2c/tests/policy/test_policy_decide_table.py",
 "tags": ["shell", "compound"]}
```

*This example is illustrative.* `MG-Z03` generates the real rows from the existing tests, and the Python runner proves each one.

- **Fields.** `id` (unique, `area/group/name`), `area`, `desc`, `input`, `expect`, `source` (the Python test it came from, or `"new"`), `tags`. `expect` lists only what must match (for policy: `action`, optionally `matched_rule`, `risk`, `basis`; never the free-text `reason`).
- **Runner.** `run_python.py [--area X] [--tag T]` loads the vectors and calls the Python implementation through an adapter table (`ADAPTERS = {"policy": ..., "secrets": ..., "paths": ...}`), and exits non-zero on any mismatch. A second mode, `--oracle`, reads vectors from stdin and writes the Python answer for each: the differential fuzzers in `MG-R02` and `MG-R03` use it.
- **Known failures.** A vector tagged `known-fail-python` is expected to fail on the reference (the reference has a bug) and to pass on Rust. The runner treats it as an expected failure and prints the list.
- **Rules.** §4 rules 1 and 2. Vectors are data only: no code, no environment. Path vectors describe a small file tree that each runner builds in a temporary directory (`MG-Z05`).

*Done when:* the schema validates every vector, the runner fails on a deliberately broken vector (a test proves this), and the CI job is green.

#### MG-Z03 · Policy vectors · L · Wave 3

*Files:* `protocol/conformance/policy/`, an adapter in `run_python.py`.

*Sources:* `m2c/tests/policy/` (8 test files and `policy_helpers.py`): `test_policy_decide_table`, `_rules`, `_modes`, `_shellparse`, `_interact`, `_invariants`, `_robustness`, `_review_findings`.

*What:*

1. **Export the table-driven tests.** Wrap `decide(...)` and `shellparse.parse(...)` with a recorder, run the existing tests once, and dump each `(input, output)` pair. Remove duplicates, then review the dump by hand. Rule sets are plain strings (`bash(git status)`), paths are plain strings, nothing touches disk (`policy_helpers.py` already works this way).
2. **`shellparse` needs a JSON projection**: `parse(command) -> ParseResult` of `Part`, `Word` and `Redirect` objects. Define the projection once in the adapter (for example words as text plus a quoting flag) and document it in the vector README. Vectors compare the projection.
3. **Do not export property tests.** `test_policy_invariants` and `test_policy_robustness` express properties, not cases. Keep them as Python tests, write the equivalent `proptest` properties in `MG-R03`, and add concrete instances as vectors.
4. **Author the Q07 bypass corpus here, as vectors.** `Q07` is in the build plan and not built (§0.6). Writing it as vectors from the start means both languages run it. Groups, from the plan: compound commands (`&&`, `;`, pipes, `$(...)`, backticks, process substitution, here-documents, `bash -c`, `env X=1 cmd`, `xargs`, `find -exec`, `timeout`, `sudo`); one program named in a rule running another (aliases, `PATH` shadowing, `./git`); deny rules versus relative paths, `cd`, symlinks, letter case, restarts; settings and trust; sandbox-protected paths; control characters in names and output.
5. **Where the Python reference is too permissive**, record the safe answer as `expect` and tag the row `known-fail-python`. That is how the corpus finds real bugs.

*Done when:* every row of `test_policy_decide_table` is exported (the counts match), every Q07 group has rows, the runner is green with the known-fail list documented, and the vector README lists the shellparse projection.

#### MG-Z04 · Secret-redaction vectors · M · Wave 3

*Files:* `protocol/conformance/secrets/`.

*Sources:* `m2c/tests/secret_handling/`: `test_secrets_corpus`, `_detectors`, `_env`, `_memory`, `_runner`, `_stream`.

*What:*

1. **Detectors.** For every detector kind in `secrets/redact.py` (AWS keys, tokens, JWTs, URL credentials, `Authorization` headers, `--password` style flags, assignments, high-entropy candidates), positive rows (the secret must not survive) and negative rows (ordinary developer text must be left alone: hashes, UUIDs, base64 of non-secrets, file paths). Exercise the public functions `redact`, `contains_secret` and `scan_lines` separately, each with positive rows. A trial of a recording tool on 2026-11-24 (see the optional tooling note in `MG-Z10`) reported that recording only the existing tests left `contains_secret` with no positive input and covered 14 of the 26 rule kinds in `_RULES`; the 26 was re-counted in the code, the 14 was not re-run.
2. **Chunk boundaries.** `_stream` rows: `input.chunks` is a list, and a secret split across two chunks must still be caught.
3. **Environment.** `secrets/env.py` rows: environment in, sanitized environment out.
4. **Fake secrets and Gitleaks.** Vectors must not contain a credential-shaped literal, or the pre-commit hook and CI fail. Store each fake as **pieces** the runner joins (`"parts": ["gh", "p_", "<body>"]`), the same idea as `secret_fakes.py`'s `_cat`. If Gitleaks still flags a body, the fallback is to add `protocol/conformance/secrets/` to the `.gitleaks.toml` allowlist **and** add a test that fails if any row there lacks `"fake": true`. Prefer the pieces; the allowlist switches scanning off for that folder.
5. **Do not use Python's seeded `random` to make fakes.** Rust cannot reproduce that stream. The vectors hold concrete values.

*Done when:* each detector kind has positive and negative rows for both `redact` and `contains_secret`, the stream-split rows exist, the runner is green, and Gitleaks is green on the commit.

#### MG-Z05 · Path-guard vectors · M · Wave 3

*Files:* `protocol/conformance/paths/`.

*Sources:* `m2c/tests/tools/test_tools_paths.py`, `m2c/tests/tools/test_tools_path_guard_port.py` (ported from `daemon/tests/test_path_guard.py`), and `daemon/tests/test_path_guard.py` itself.

*What:* each row holds a small tree spec (`{"files": {"a/b.txt": "x"}, "dirs": [...], "symlinks": {"link": "../outside"}}`), an operation (`resolve`, `open_read`, `open_write`), a root and a path, and the expected result (`{"ok": true, "resolved": "a/b.txt"}` or `{"error": "<name from tools/paths.py>"}`). Runners build the tree in a temp directory and substitute `{ROOT}`. Cover: `..` traversal, absolute paths, `~`, symlinks pointing outside, symlinks inside, dot segments, trailing slashes, NUL bytes, very long paths, case, Unicode normalization.
**Also compare the daemon's test file with the M2C port** and add any case that exists only in the daemon's tests, so deleting `daemon/` loses nothing (`MG-D04` depends on this).
A race (a symlink swapped between check and use) cannot be a static row; it becomes a Rust-only test in `MG-R01`.

*Done when:* every case in both test files is exported or explicitly marked as race-only, and the runner is green.

#### MG-Z06 · Local-store compatibility fixtures · S · Wave 2

*Files:* `rust/fixtures/store/`, `m2c/tests/store/make_golden.py`.

*What:* the Rust client must open what the Python client wrote, and the reverse, while the two overlap. `store/migrations.py` creates `sessions`, `events`, `approvals`, `checkpoints` and `schema_version`.

1. A script, run at the frozen tag, builds a small deterministic database through the Python store API (several sessions, events, approvals, checkpoints). Commit the `.sqlite` file and a JSON dump of its logical content.
2. Do the same for every other file the Python client writes under `M2C_HOME`: the credential file (`0600`), the folder-trust decisions, the settings layers. List them in `PARITY.md`.

*Done when:* a Python test reopens the golden database and matches the dump, and the file list under `M2C_HOME` is complete.

#### MG-Z07 · Rust workspace, toolchain and CI · M · Wave 2

*Files:* `rust/Cargo.toml`, `rust/rust-toolchain.toml`, `rust/deny.toml`, `rust/deps-allowlist.toml`, `.github/workflows/ci.yml`.

*What:*

**Layout** (Python and Rust coexist under one repo until `MG-R13`):

```
rust/
  Cargo.toml  Cargo.lock  rust-toolchain.toml  deny.toml  deps-allowlist.toml
  crates/
    minicore-protocol  minicore-paths  minicore-secrets  minicore-policy
    minicore-store     minicore-link   minicore-auth     minicore-sandbox
    m2c-tools  m2c-context  m2c-checkpoints  m2c-tui  m2c-cli   (bin: m2c)
  fixtures/
```

The `minicore-*` crates are exactly the shared pieces the Menux guide lists for `MT-K01`. Naming them now is what turns `MT-K01` from an extraction into a boundary check (§8).

Then:

- **Pin the toolchain** in `rust-toolchain.toml`; commit `Cargo.lock`; CI uses `--locked`.
- **CI jobs:** `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test --workspace --locked`, `cargo deny check`, `cargo audit`, the conformance job for Rust (added as vectors arrive), and a dependency-allowlist test that reads `cargo metadata` and fails on any crate without an entry (§4 rule 4).
- **Candidate crates** (candidates only; verify the current version and licence and pin exactly in the patch that adds each): `tokio`; `serde`, `serde_json`; `jsonschema`; `tokio-tungstenite`; `rusqlite` (bundled SQLite); `clap`; `ratatui` with `crossterm`; `regex`; `rustix` or `nix`; `keyring` (optional feature); `tracing`; `thiserror`, `anyhow`; `similar`; `toml`; `sha2`; `proptest`; `insta`.
- **Targets:** x86_64 and aarch64 Linux (WSL2 runs on both). Linux first, as the book already says (CX2). glibc versus musl is decided in `MG-R05` (§12).

*Done when:* `cargo test --workspace --locked` is green on the empty skeleton, every CI job runs, and the allowlist test is proven red when a crate is added without an entry.

#### MG-Z08 · Protocol codegen and fixture replay · M · Wave 3

*Files:* `protocol/validate.py` (a second sync target), `rust/crates/minicore-protocol/schemas/`, `protocol/generated/ts/`, CI check.

*What:*

1. **Spike first.** The schemas are Draft 2020-12 with cross-file `$ref` (`common.json#/$defs/uuid`), a custom `x-m2c-types` keyword, and a payload chosen by the envelope's `t`. Code generators differ in how much of that they handle. Try one Rust generator (for example `typify`) and one TypeScript generator (for example `json-schema-to-typescript`) on the real files and record what works. **If generation cannot express the `t`-tagged payloads, hand-write the Rust enum and the TypeScript union.** Generation is a convenience; the fixture replay below is the guard.
2. **Commit the generated output** and add a CI check that regenerates and fails on any diff, the same idea as `validate.py --check-client-copy`.
3. **Fixture replay.** In Rust and in TypeScript: parse every line of `protocol/fixtures/*.jsonl` into the types and serialize it back to equal JSON; run `check_transcript` (sequence runs, call-id pairing, resume cursors, terminal states, as `validate.py` does); and require that every one of the 60 `invalid_examples.jsonl` rows is rejected **on the keyword and path it names**. For TypeScript runtime validation use Ajv's 2020-12 class.
4. **Sync target.** `validate.py --sync-client` copies the schemas into `m2c/src/m2c/protocol/v1/`. Add the Rust crate's `schemas/` directory as a second target with the same byte-identical check. Keep the Python target until `MG-R13`.

*Done when:* Rust and TypeScript replay all four transcripts, reject all 60 invalid rows for the named reason, and the regenerate-and-diff check is green.

#### MG-Z09 · Book edits for the new plan (runs only on `PROCEED`) · S · Wave 5

*Precondition (revision 1.1):* `MG-Z10` has recorded `PROCEED`. Until then the existing guides keep their current wording, which already says Python for M2C and uses `.py` file names for Menux. If the gate records `STAY PYTHON`, this package does not run; apply the short edit list in §1.1 instead.

*Files (in this book repo):* `data/docs/m2c_feature_guide.md` (and its mirror in `docs/`), `data/docs/m2c_build_plan.md`, `data/docs/Menux___Build_Execution_Guide.md`, `data/docs/menux_feature_guide.md`, `docs.html`, `llms.txt`, `data/summary.md`, `consistency.html`.

*What:* make the existing guides agree with DM-1 to DM-10.

- **`m2c_feature_guide.md`:** O4 and §2.2 (distribution is a signed binary plus the installer script, Python is no longer required; keep `uv tool install` text only for the frozen reference); every "Python 3.11" requirement; the `minicore/` wording (it becomes workspace crates); the dependency policy (D14 becomes the crate allowlist).
- **`m2c_build_plan.md`:** D1 (Python ≥ 3.11) and D14; add a short "§0.7 Migration status" pointing at this guide; `C22` packaging (binary releases, checksums and signing instead of a wheel); `Q01` CI; `Q08` (the docs-drift check runs against the Rust `m2c --help`); `P00` (the client-copy path); §0.6 gets a "Rust" status column as packages port.
- **`Menux___Build_Execution_Guide.md`:** the precondition (Menux starts when the **Rust** M2C reaches M2); `K00` (inventory of the Rust workspace); `K01` (size L becomes S: the crates already exist, §8); `D1` scheduler (`croniter`), `D3` vault libraries, `D7` (YAML 1.1 versus 1.2, §8), Playwright as a sidecar, the prompt template ("Python" becomes "Rust"), and the risk row "extracting `minicore` breaks M2C".
- **`docs.html`:** the `minicore` node of the architecture panel says the shared `minicore/` library was "extracted in M2C Wave 1" (`P00`). The build plan says `P00` created `protocol/`, and `minicore/` does not exist yet. Rewrite the text to describe the planned `minicore-*` crates.
- **In the MiniMe repo (not this book), at `MG-D04`:** mark the daemon entry in `DEFERRED.md` `[RESOLVED]` with how it closed (the file's own convention), and add a "Superseded" note to `docs/decisions/0003-cli-attach-daemon-dir.md`. Do not delete decision records.

*Done when:* a search of the three guides for "Python 3.11", "`uv tool install m2c`" and "`minicore/`" finds only intentional mentions, and the consistency page lists this guide.

#### MG-Z10 · Rust decision gate: the `minicore-secrets` spike · L · Wave 4

*Files:* `rust/crates/minicore-secrets/` (on a spike branch), `rust/spikes/idle-daemon/`, `scripts/spikes/idle_daemon.py`, `protocol/conformance/secrets/` (the `MG-Z04` vectors, read-only here), and a new decision record `docs/decisions/<next number>-rust-client-gate.md` in the MiniMe repo.

*Why this and not a smaller test:* it is security code, it needs the regex features that Rust's `regex` crate is said to lack (§3, §13), it has a built-in oracle (the Python reference through `run_python.py --oracle`) and a vector set (`MG-Z04`), and it is small enough to finish. It also decides whether the pieces that follow, `minicore-paths` and `minicore-policy`, are worth porting.

*What:*

1. **Write the criteria first.** Create the decision record. Put in it: the date, the time box (default **5 working days**, counted from step 3), the thresholds below (or your own), and the sentence "the outcome follows from the table in §1.1". **Commit it before writing any Rust** (rule 10). Do not edit the thresholds afterwards; if they were wrong, write a new record.
2. **Classify the patterns.** List every regular expression in `secrets/redact.py` and `secrets/env.py` and mark each as *portable* (plain `regex` syntax), *lookaround*, *possessive*, *backreference* or *other*. §3 counts 11 lookaround assertions and 2 possessive quantifiers; **re-count them** and record the numbers. Re-run the check recorded in §13 on the `regex` version you will pin, and record that version: lookaround must fail to compile, and a possessive quantifier must be listed as a **silent** difference (it compiles and means an ordinary repeat), so it needs a lint, not only a rewrite (step 4).
3. **Port the portable group first** in `minicore-secrets` using the exact version in `rust/deps-allowlist.toml`. Run the `MG-Z04` vectors for those detectors.
4. **Port the rest** with the approach in `MG-R02`: an explicit check of the character before and after the match instead of `(?<!X)` and `(?!X)`, and a bounded equivalent for each possessive quantifier. Add a test that fails the build if any pattern source in the Rust crate contains a possessive quantifier (`*+`, `++`, `?+` or `}+` outside a character class or an escape), because the `regex` crate compiles those without error. Use a backtracking engine only if a rewrite is impossible, and then only with a backtrack limit. For each pattern, record which technique was used.
5. **Stream carry-over.** Port the chunk-boundary behaviour (the `MG-Z04` stream rows).
6. **Differential run.** Generate a corpus from the fake-secret builders plus mutations and near-misses (see C1), run both implementations, and triage every divergence as a Rust bug, a Python bug (write a `known-fail-python` vector) or an accepted difference with a note.
7. **Measure** the benefit criteria, even if a hard criterion has already failed, because the numbers decide what the `STAY PYTHON` alternatives should be.
8. **Decide.** Fill in the table below in the record, write the outcome, and apply the edits in §1.1 that go with it.

**Hard criteria (all must pass):**

| # | Criterion | Suggested threshold (write yours in step 1) |
| --- | --- | --- |
| **C1** | **Correctness.** | 100% of the `MG-Z04` rows pass. Zero divergences where Rust redacts **less** than Python, over a differential corpus of at least 20,000 inputs, at least 2,000 of them near-misses for each detector family. (Rust redacting more is allowed with a note, DM-10.) |
| **C2** | **Effort.** | Finished inside the time box, **or** the work left, estimated from the detector families already done, is at most 40% of the time box. |
| **C3** | **Reviewability and safety.** | `#![forbid(unsafe_code)]` holds. Every replacement of a lookaround or possessive pattern has its own named test and a comment naming the Python line. Worst-case time on the adversarial corpus (long near-matches, repeated characters) is **no worse than the Python reference's**; record both. |

**Benefit criteria (at least one must pass; each is measured, not argued):**

| # | Criterion | How to measure | Suggested threshold |
| --- | --- | --- | --- |
| **B1** | **Install friction.** | On a clean Ubuntu 22.04 container and a default WSL2 Ubuntu, write down the exact commands needed to run the Python M2C (including how to obtain a Python at or above the version `pyproject.toml` requires) and to run a Rust binary. `bubblewrap` and `ripgrep` are needed by **both**, so do not count them. | The Python path needs at least one extra step the binary does not (for example adding a package source or installing a separate Python). The package index already shows why (§13): Ubuntu 22.04 ships Python 3.10 and `pyproject.toml` requires 3.11 or later. Record the exact commands from a real container anyway. |
| **B2** | **Idle footprint.** | Build two stubs that do nothing but hold an open SQLite file and one idle WebSocket client: `scripts/spikes/idle_daemon.py` (asyncio) and `rust/spikes/idle-daemon/`. After 10 minutes idle, record resident memory and wake-ups per minute. This is the figure that matters for a daemon that runs 24 hours a day (Menux). | Rust uses at most half the resident memory of Python. |
| **B3** | **Defects found.** | Count the divergences in step 6 where **Python** was the wrong one (each becomes a `known-fail-python` vector). | At least one real Python bug or ambiguity. (This pays off even if the outcome is `STAY PYTHON`: fix it in Python.) |

**Not counted as benefits:** raw speed (it is recorded, not a goal), binary size by itself, and "Rust is safer" as a general statement. Only what this spike measured counts.

**Optional tooling (added 2026-11-24; it changes none of the criteria above).** Two MIT-licensed tools (licences read in their repositories; neither was audited) can help with steps 6 and 7. `rust-anything` records what the Python original does, replays it against the Rust port with `diff`, looks for missed cases with `fuzz` and can run both side by side with `shadow`. `fast-anything` profiles a workload and ports only the hot functions. Entries `UB-081` to `UB-083` in Appendix C hold the details. A trial run on m2c showed the following.

- **A recording is only as good as its inputs.** The tool's default generated corpus held no input that contained a secret, and its longest input was 48 characters (trial figures, not re-run). A Rust `redact` that detected nothing would have passed `diff` on it. Feed the tool the `MG-Z04` vectors and the near-miss corpus of C1, and do not accept a green `diff` on the default corpus.
- **Run it on a copy, with fake secrets only.** Recording runs the original code on many inputs, and the tool's own README says to use a copy of the project and no production credentials. Never record a real session through `redact` or `env`: the recordings are files and would hold the real values. Build fakes from pieces as `secret_fakes.py` does (`MG-Z04`, step 4).
- **The first unit is `redact.py`, not the `secrets/` folder.** `redact.py` imports only the standard library; `env.py` imports `..paths` and `..logging_setup`, which ties it to the rest of the client. Given the whole package, the tool treated about 20,500 lines as one tangled piece (trial figure, not re-run).
- **Read its flags before acting on them.** It marked `auth/` as blocked for dynamic code; the only cause is the lazy `importlib.import_module("keyring")` in `auth/credentials.py`. It also called m2c a server because of the sandbox bridge and probe sockets, although m2c is a command-line client.
- **Keep the port logic apart from the binding.** C3 requires `#![forbid(unsafe_code)]`; keep the port in a pure-Rust crate and any Python binding (PyO3) in a separate one. Whether generated binding code can satisfy that rule was not checked.

**What this spike cannot tell you.** It covers about 900 of the client's 27,000 source lines and none of the policy crate, the sandbox crate or the terminal UI, which are the three largest packages (`XL`, `XL`, `XL`). C2 is therefore a **lower bound** on the cost of the port. That is why `MG-R03` carries a checkpoint (§6.5): if the policy crate takes more than twice its estimate, run this gate again as a new dated record.

*Done when:* the record lists a measured value for every criterion, states the outcome (`PROCEED`, `STAY PYTHON` or `EXTEND ONCE` with its reason), and the matching edits are applied (`MG-Z09` unblocked, or the §1.1 list applied).

*Rollback:* none; the spike lives on a branch. On `STAY PYTHON`, keep the branch for reference and remove the Rust jobs that `MG-Z07` added to CI.

---

### 6.2 Track F · Frontend to TypeScript

#### MG-F00 · TypeScript foundation and test-runner spike · M · Wave 1

*Files:* `frontend/package.json`, `frontend/tsconfig.json` (new), `frontend/ts-nocheck-allowlist.txt` (new), `.github/workflows/ci.yml` (`frontend-lint`).

*What:*

**1. Dependencies.** Add devDependencies `typescript`, `@types/node`, `@types/react`, `@types/react-dom` and a script `"typecheck": "tsc --noEmit"`. Add that script to the `frontend-lint` job.
**2. `tsconfig.json`**, starting point:

```json
{
  "compilerOptions": {
    "target": "ES2022", "lib": ["dom", "dom.iterable", "esnext"],
    "module": "esnext", "moduleResolution": "bundler", "jsx": "preserve",
    "allowJs": true, "checkJs": false, "strict": true, "noEmit": true,
    "isolatedModules": true, "skipLibCheck": true, "resolveJsonModule": true,
    "allowImportingTsExtensions": true, "erasableSyntaxOnly": true,
    "verbatimModuleSyntax": true, "incremental": true
  },
  "include": ["next-env.d.ts", "app/**/*", "middleware.js"],
  "exclude": ["node_modules"]
}
```

`allowJs` without `checkJs` means unconverted JS is not checked; **a converted file is strictly checked from the moment it is renamed.** That is the ratchet, no baseline file needed. Keep `next.config.js`, `tailwind.config.js`, `postcss.config.js` and the Sentry config files as JavaScript: Next 14 reads a JavaScript config.

**3. Spike the test runner.** Your CI uses Node 22.22.0, and the Node 22.18.0 release turned on native type stripping by default ([release notes](https://nodejs.org/blog/release/v22.18.0)). Take the smallest `app/lib` module that a `.test.mjs` imports, rename it to `.ts`, change the import in the test to the `.ts` specifier, and run `npm test`, `npm run typecheck` and `npm run build`. Type stripping removes types but does not rewrite anything else, which is why the config above has `erasableSyntaxOnly` (no `enum`, namespaces or parameter properties; it needs TypeScript 5.8 or newer, so pick the `typescript` version with that in mind), `verbatimModuleSyntax` (type-only imports use `import type`) and `allowImportingTsExtensions` (so the bundler accepts `.ts` specifiers). It also cannot run JSX, so **tests may import `.ts` modules and never `.tsx`**: keep the logic that tests exercise in `.ts` files. If the spike fails on 22.22.0, the fallback is `node --import tsx --test`, which adds a `tsx` devDependency; record whichever you choose.

**4. The no-check allowlist.** The eight files over 1,500 lines (§3) may carry `// @ts-nocheck` while they are split. List them in `frontend/ts-nocheck-allowlist.txt`; a CI step fails if a file outside the list uses `@ts-nocheck` or if the list grows.

*Done when:* `typecheck`, `build` and `test` are green with the spike file converted, and the choice (native stripping or `tsx`) is recorded.

#### MG-F01 · Generate API types from FastAPI's OpenAPI · M · Wave 2

*Files:* `backend/scripts/dump_openapi.py` (new), `frontend/app/lib/api/schema.d.ts` (generated, committed), `frontend/app/lib/api/client.ts`, `frontend/app/lib/events.ts`, `frontend/package.json` (`gen:api`).

*What:* the frontend talks to the backend over REST and Pusher, not over the device protocol, so its contract is the OpenAPI document FastAPI already produces.

1. `dump_openapi.py` imports `api.server.app` and prints `app.openapi()`. If importing the app needs environment variables, run it with the same environment as the CI `test` job.
2. Generate `schema.d.ts` with an OpenAPI-to-TypeScript generator (`openapi-typescript` is the usual choice), commit it, and add a CI step that regenerates and fails on any diff.
3. A small typed wrapper around `authFetch` in `client.ts`, generic over path and method.
4. **Routes without a `response_model` produce loose types.** Tightening them is `MG-B05`. Start with the eight to ten routes the frontend calls most.
5. **Realtime events have no schema.** Write `app/lib/events.ts` by hand, a typed map of the Pusher event names and payloads taken from `backend/relay/emitter.py`. Emitting a schema from Python later is optional.

*Done when:* the generated file is committed with its diff check, at least one real call site uses the typed wrapper end to end, and `events.ts` covers every event the frontend subscribes to.

#### MG-F02 · Convert `app/lib` modules · L · Wave 3

*Files:* the 55 `.js` files under `frontend/app/lib/` (including `preview/` and `workbench/`) and the tests that import them.

*Order:* modules that touch backend data first (`authFetch`, `devices`, `usage`, `streamTicket`, `ingestDispatch`, `pusherClient`, `chatMessageCache`, `latestRequest`), then the rest (`notebookAffinities`, `notebookCapabilities`, `highlightCode`, `clearLocalAppState`, `langfuseTraceId`, `pyodideRunner`, `supabaseClient`, `supabaseServer`, then `preview/` and `workbench/`).

*What:* rename `.js` to `.ts`, type the exports from `schema.d.ts` and `events.ts`, update the import specifiers in tests to `.ts`. Convert at most about ten files per patch.

*Done when:* `app/lib` has no `.js` (except where a file must stay JavaScript, with the reason in a comment), and `typecheck`, `build` and `test` are green.

*Checkpoint (revision 1.1):* count the real bugs the type checker found in this package and compare them with the time it took. `MG-F03` to `MG-F05` are optional: each converted file stands alone, so the track can stop here or continue one directory at a time. Record the choice in `PATCHES.md`. This decision does not depend on the Rust gate.

#### MG-F03 · Convert hooks and context providers · M · Wave 4

*Files:* `frontend/app/hooks/` (11 files), `frontend/app/context/` (8 files).

*What:* **do not convert `hooks/useDaemonStatus.js`; `MG-D02` deletes it.** `SessionContext.jsx` (2,718 lines) and `WorkspaceDockContext.jsx` (1,590) go on the no-check allowlist first; before removing the comment, extract their reducers, selectors and pure helpers into `.ts` modules and type those. That is also where hidden bugs sit.

*Done when:* hooks and context are `.tsx`/`.ts`, the two giant providers are either converted or on the allowlist with an extraction plan, and CI is green.

#### MG-F04 · Convert components, directory by directory · XL · Wave 5

*Files:* `frontend/app/components/` (100 `.jsx`, including `tabs/` and `workbench/`).

*What:* leaf components first (presentational, no context), then components that use contexts, then the `tabs/*Tab.jsx` files last. About ten files per patch. Third-party types: `reactflow`, `recharts`, `react-force-graph-2d`, the `@codemirror/*` packages and xterm ship their own; add `@types/three` if a 3D component is converted. **Giant files in two steps:** (1) rename to `.tsx`, add them to the allowlist, extract pure logic into `.ts` modules and type those; (2) split the component until the `@ts-nocheck` can be removed. The files are `NotebooksTab`, `WorkspaceChatPanel`, `EditorWorkbench`, `BuildTab`, `GrowthTab`, `TestTab`.

*Done when:* no `.jsx` remains under `app/components/`, and the allowlist holds only files with a written split plan.

#### MG-F05 · Strict everywhere, drop `allowJs` · M · Wave 6

*What:* empty and delete `ts-nocheck-allowlist.txt`, set `allowJs: false`, turn the ESLint `no-explicit-any` rule from warning to error, and consider `noUncheckedIndexedAccess` as an option (§12).

*Done when:* no `.js` or `.jsx` is left under `frontend/app/` apart from configuration files, and `typecheck` is green with `strict`.

---

### 6.3 Track D · Retire the daemon

**Why this is not a plain deletion.** `daemon/` is superseded: M2C's `tools/paths.py`, `tools/files.py` and `tools/search.py` carry "Ported from daemon/…" headers (a test asserts it), and M2C adds a policy engine, a bubblewrap sandbox, a network proxy and a reconnecting device link. But the backend half is entangled with something that stays:

- `eo/local_workspace_tools.py` holds both the daemon calls (`call_daemon`) and the propose / confirm / deny gate.
- `api/routes/mcp.py` imports the gate functions from it and says it deliberately reuses the same ones; `eo/mcp_agent_tools.py` mirrors it. That gate protects **server-side MCP for the web agents**, which stays.
- `relay/emitter.py` fires `LOCAL_TOOL_*` events that the MCP path also uses.
- `frontend/app/lib/workbench/fileProviders.js` (line 13) carries a comment, "The backend local_workspace routes and daemon/ stay until M2C Phase 5." This guide moves that earlier on purpose; its condition is that the browser's Local-folder mode is already gone. That was Phase 0 of the M2C build plan (its own work packages numbered B03 to B06, which are unrelated to this guide's track B); §0.6 of the plan lists three of them as built and one as not checked, so confirm which one covered Local-folder before MG-D02.
- `eo/local_workspace.py` has its own process-local `_connections` dict for daemon sockets. It is not the M2C registry (`codeagent/connections.py`) and disappears with `MG-D03`.
- **Not part of this:** `eo/ws_registry.py` and its test are the web UI's WebSocket bridge, unrelated to the daemon. Keep them.

#### MG-D00 · Decide the fate of the shared action gate · S · Wave 1

*Files:* a new decision record in the MiniMe repo, `docs/decisions/<next free number>-daemon-retirement.md` (numbers 0001 to 0003 exist).

*Options:* **A (recommended)** extract the gate into a neutral module both paths use, then delete the daemon half. **B** leave `local_workspace_tools.py` as it is and delete only `daemon/` and the socket route (dead code stays). **C** retire server-side MCP for web agents too (D18 says M2C's MCP is device-only; the web agents still use `eo/mcp_client.py`, so this is a product decision).

*Done when:* the record names the option and pastes the result of `grep -rn "local_workspace_tools" backend frontend` as its inventory.

#### MG-D01 · Extract the neutral action gate · M · Wave 2

*Files:* new `backend/eo/action_gate.py`; `eo/local_workspace_tools.py`, `eo/mcp_agent_tools.py`, `api/routes/mcp.py`.

*What:* move the propose / confirm / deny functions and their audit-event emission into `action_gate.py`. Behavior-preserving: keep a re-export shim in `local_workspace_tools.py` until `MG-D03`. Do not rename the event types the MCP path emits.

*Tests that must stay green:* `tests/unit/test_eo_local_workspace_tools_mcp_gate.py`, `test_eo_mcp_agent_tools.py`, `test_eo_mcp_client.py`, and the route tests.

*Done when:* `grep` shows no MCP code importing from `local_workspace_tools`.

#### MG-D02 · Remove frontend daemon surfaces · S · Wave 3

*Files:* `app/hooks/useDaemonStatus.js` (delete), its callers, the daemon tool-call log in `components/AgentStepList.jsx` and `context/WorkspaceDockContext.jsx`, the comment in `app/lib/workbench/fileProviders.js`, and `app/lib/workbench/__tests__/localFolderRemoved.test.mjs` (it currently asserts that the hook still polls `/local/status`; rewrite it to assert that nothing does).

*What:* a search for `daemon|local.?workspace` in `frontend/app` matches `LandingPage`, `workbench/BottomPanel`, `Explorer`, `UrlPreview`, `EditorWorkbench`, `agentRoleIcons`, `RoutingTraceGraph`, `PendingActionBar`, `AgentStepList` and `useDaemonStatus`. Not all are real callers: review each. Keep any handling of the shared `LOCAL_TOOL_*` events that MCP calls still produce.

*Done when:* no frontend code requests `/local/` routes, and `lint`, `test` and `build` are green.

#### MG-D03 · Remove backend daemon routes, registry and events · M · Wave 4

*Files:* delete `eo/local_workspace.py` (WS `/ws/daemon/{workspace_id}`, `_connections`, the `MINIME_PAIRING_TOKEN` check) and `api/routes/local_workspace.py`; edit `api/server.py` (the imports near lines 95 and 133 and the `include_router` calls near 387–388), `relay/emitter.py` (remove only daemon-specific callers), `eo/introspection.py` and `api/routes/code_edit.py` (comments); tests `test_eo_local_workspace.py`, `test_eo_local_workspace_tools.py`, and the daemon-specific part of `test_task_routes_full_payload.py`; the shim from `MG-D01`.

*Done when:* `pytest tests/unit tests/integration tests/static` is green, a static test asserts that `/ws/daemon/{workspace_id}` is not in the route table, and `MINIME_PAIRING_TOKEN` appears nowhere in code or docs.

#### MG-D04 · Delete `daemon/` and its CI job · S · Wave 5

*Files:* `daemon/` (16 files), the `daemon-test` job in `ci.yml` (lines 76–106) and the comment in `m2c-test` that mentions it (near line 116); wording in `m2c/pyproject.toml` (comments about sharing pins with `daemon/requirements.txt`) and the docstring at `m2c/tests/test_cli.py:233`; `DEFERRED.md` and `docs/decisions/0003-…` as in `MG-Z09`.

*Checked:* no M2C test reads a file from `daemon/`; the mentions are comments and docstrings. The tests that assert the "Ported from daemon/…" headers read M2C's own source, so they stay.

*Done when:* `git grep -n "daemon/"` finds only decision records and history, and CI is green without the job. Requires `MG-Z05`.

---

### 6.4 Track B · Backend hardening (Python)

#### MG-B00 · Load-test harness · M · Wave 1

*Files:* `backend/loadtest/` (new: `run.py`, `scenarios.py`, `README.md`, its own requirements file; **not** `backend/requirements.txt`).

*What:* a program that opens N device WebSockets and behaves like real clients, so the server's numbers come from measurement.

- **Handshake** (from `protocol/v1/hello.json` and `welcome.json`): connect to `/v1/code/device`, send `hello` with `protocol_versions`, `device_credential`, `client_version`, `capabilities`; expect `welcome` with `protocol`, `min_protocol`, `token_ttl_s`, `limits`. The server gives a client 10 s to send `hello`.
- **Credentials.** Devices are stored by the SHA-256 hash of the credential (`eo/devices.py`). The harness creates N test devices in a **staging database** with random credentials whose hashes it inserts. **Never run it against production data.**
- **No real model calls.** `codeagent/model_adapter.py` defines the provider-neutral `ModelAdapter` (a stream of `TextDelta`, `ToolCall`, `Usage`). Add a scripted fake adapter that can be selected only by an explicit staging setting, and make the server refuse to start with it when a production flag is set. Without this, a load test spends money on providers.
- **Scenarios:** **S1** idle hold (connect N, ping every ~25 s, hold for 10 minutes); **S2** busy (a fraction start runs with scripted tool calls and approvals); **S3** reconnect storm (restart the server, all N reconnect, with and without jitter); **S4** slow consumer (some clients stop reading; check that the per-connection send lock does not stall others); **S5** resume (drop and resume with `run.resume{last_seq}` under load).
- **Ramp:** 100, 1,000, 5,000, 10,000 connections, as far as the staging box allows.
- **Measure:** handshake time p50/p95/p99; server memory per connection; event-loop lag (`asyncio` slow-callback logging); database and Redis operations per second per idle connection; CPU; time to full recovery in S3; close codes seen (4429 means the rate limiter fired).

*Done when:* all five scenarios run against staging with the fake adapter, results are written to `loadtest/results/<run>.json`, and the README says exactly how to set up a staging database.

#### MG-B01 · Baseline run, numbers recorded in the book · S · Wave 2

*What:* run `MG-B00` on the current code at the chosen staging size and put the table in `minime_server_management_guide.md` (this book) next to its existing scale triggers.
**Hypotheses to test, not conclusions:** (1) the 30-second revalidation per connection is the first cost to appear (N/30 credential checks per second); (2) `buffer.py` writes every replayed event to Redis through the Upstash client, which is an HTTP request per command (and retries once, so a push can land twice, as its own comments say), so replay-buffer round trips, not Python, may dominate at load; (3) event-loop lag shows up with S2 before CPU does.

*Done when:* the table is in the book with the staging hardware stated, and each hypothesis is marked confirmed or refuted.

#### MG-B02 · Redis-backed presence and handshake limiter · M · Wave 3

*Files:* `codeagent/connections.py` (the `ConnectionRegistry` and `HandshakeLimiter` interfaces), a Redis-backed implementation, wiring in `ws.py`.

*What:* the `S11` pieces the code comments already name. Live sockets stay process-local (they cannot leave the process) and cross-process presence ("is this device online anywhere") goes to Redis with a TTL and heartbeat; the failed-handshake limiter moves to Redis so several gateway processes share one budget; per-user limits. If `MG-B01` shows Upstash round trips dominate, put a TCP Redis client behind the existing `RedisLike` interface in `buffer.py` for the hot paths.

*Done when:* two gateway processes behind the test harness report correct presence and a shared limiter, and S1 and S3 are re-run with before/after numbers.

#### MG-B03 · Gateway process split · L · Wave 4

*What:* read `S11` in `m2c_build_plan.md` and the process-split section in `minime_server_management_guide.md` first. This work package **is** `S11`'s process split, started earlier and measured. The migration adds three requirements: do it in Python; re-run `MG-B00` before and after; and keep the gateway behind a narrow interface (`DeviceConnection`, `ConnectionRegistry`, the envelope send path), so `MG-B06` can swap its implementation without touching the loop.

*Done when:* the gateway and the loop run as separate processes, a graceful drain on deploy works, and S1 to S5 meet the targets in the book.

#### MG-B04 · Blocking-call audit on hot paths · M · Wave 3

*What:* classify every blocking call, with evidence. A grep outside tests and scripts finds 33 sites.

- **`requests.*` (26):** `agents/component_spec_lookup.py` (5), `agents/academic_search.py` (4), `agents/calendar_agent.py` (3), `utils/web_search.py` (3), `api/deps.py` (2: the user lookups by email and by id), `api/routes/workspace_data.py` (2: the Google Calendar OAuth callback), and one each in `utils/llm_client.py`, `utils/embedding.py`, `eo/integrations.py`, `agents/web_researcher.py`, `agents/pagespeed_agent.py`, `agents/deploy_agent.py` and `check_hf_embedding.py` (a script).
- **`time.sleep` (7):** `utils/llm_client.py` (6, retry and backoff) and `utils/retry.py` (1).
- **Classify each as** **on the event loop** (a real problem: wrap in `asyncio.to_thread` or move to `httpx.AsyncClient`), **on a worker thread** (fine at current scale; add timeouts and a shared `requests.Session`), or **in a script** (ignore). The `api/deps.py` and OAuth-callback sites are plain `def` functions, which FastAPI runs on its threadpool, so they are worker-thread sites, not event-loop ones. The sites that matter most are the model client (`utils/llm_client.py`, which sleeps in its retry loop on every LLM call) and anything reached from an `async def` or from `codeagent/`.
- **Find the ones a grep cannot see:** run the server under S2 with slow-callback logging (`loop.slow_callback_duration`).

*Done when:* a table classifies every site with evidence, every event-loop site is fixed, and S2 shows no callback over 100 ms.

#### MG-B05 · Typing ratchet and response models · M · Wave 1

*Files:* `backend/pyproject.toml` (it already holds the ruff config), a CI job.

*What:* add a type checker (pyright or mypy) in basic mode on `codeagent/`, `eo/devices.py`, `eo/usage_ledger.py` and `api/routes/devices.py`, non-blocking for one cycle and then blocking on those paths; the list of checked paths only grows. Add Pydantic `response_model`s to the routes the frontend calls most; this is what makes `MG-F01`'s generated types precise.

*Done when:* those paths are blocking in CI and the first ten routes have response models.

#### MG-B06 · Gateway language decision record · S · Wave 5

*Files:* `docs/decisions/00NN-gateway-language.md`.

*What:* with the numbers from `MG-B01` and `MG-B03`, apply the triggers already in the book (paid users ≥ 100, sustained Pusher connections > 80, p95 CPU > 60%, and the capacity target of 1,000 concurrent CLI sessions in under 50 MB of Redis) and choose one of: stay Python; a Rust gateway for the socket and replay layer behind the same interface; a Rust relay only for the Menux mesh (MX3 says the server is a pipe).

*Rule:* switch only if the hardened Python gateway cannot meet the target on the chosen machine size.

*Done when:* the record exists with its inputs attached.

---

### 6.5 Track R · M2C client to Rust

**Gate.** Nothing in this track starts until `MG-Z10` has recorded `PROCEED` (rule 10). If it records `STAY PYTHON`, this whole track is dropped (§1.1).

**How every port works.** (1) Read the Python module and write a one-page behavior inventory in the patch description. (2) Export or reuse the vectors (`MG-Z03`–`MG-Z06`). (3) Write the Rust tests first. (4) Implement. (5) For security code, run a differential fuzzer against the Python reference through `run_python.py --oracle`. (6) A divergence is either a Rust bug or a Python bug; Python bugs get a `known-fail-python` vector and the Rust follows the safe answer (DM-10).

#### MG-R00 · `minicore-protocol` · M · Wave 5

*Python source:* `protocol/validate.py`, `m2c/src/m2c/protocol/` (client schema copy).

*What:* generated or hand-written types from `MG-Z08`; `validate_message` strict by default and a tolerant mode that relaxes **exactly one thing** (unknown optional properties outside tool input), as `validate.py` does; `check_transcript`; the schemas embedded with `include_str!` from the synced copy.

*Done when:* all four transcripts replay, all 60 invalid examples are rejected for the named reason, the byte-identical schema check is in CI, and a `cargo-fuzz` target over the envelope parser finds no panic.

#### MG-R01 · `minicore-paths` · M · Wave 5

*Python source:* `tools/paths.py` (ported from `daemon/path_guard.py`).

*What:* normalization, root containment, and no-follow opens done **relative to a directory descriptor** (`openat2` with `RESOLVE_BENEATH`/`RESOLVE_NO_SYMLINKS` where the kernel has it, component-by-component `O_NOFOLLOW` otherwise), through `rustix` or `nix`. The Python guard checks then opens; Rust should not copy that race. Handle names as bytes or `OsStr`, not `String`: a Linux file name need not be UTF-8.

*Tests:* the `MG-Z05` vectors, plus Rust-only tests that swap a symlink in a loop between check and use.

*Done when:* all `MG-Z05` vectors pass, the race tests pass, and `forbid(unsafe_code)` holds (or the exception is recorded).

#### MG-R02 · `minicore-secrets` · L · Wave 5

*Python source:* `secrets/redact.py`, `secrets/env.py` (932 lines).

*The problem:* Rust's `regex` crate has no lookaround (it refuses to compile it) and no possessive quantifiers (it accepts the syntax and treats it as an ordinary repeat, which is **worse**, because nothing fails), and the detectors use both (§3). Ban the possessive syntax with a test before porting any pattern.

*Start from the spike.* On `PROCEED`, the `MG-Z10` branch is the first draft of this package, and its decision record already lists the technique chosen for each pattern.

*Approach:* keep the `regex` crate, because it matches in linear time and cannot be sent into catastrophic backtracking. Rewrite `(?<!X)` and `(?!X)` as an explicit check of the character before and after a match, and each possessive quantifier as an equivalent bounded form. **Equivalence is proven by the vectors and the fuzzer, not assumed.** `fancy-regex` supports lookaround, but it backtracks (a denial-of-service risk on every tool result and stream chunk), so use it only if a rewrite is impossible, with a backtrack limit.

*Also:* redaction runs across stream chunk boundaries (`MG-Z04` rows); the Rust version keeps that carry-over.

*Tests:* the `MG-Z04` vectors; a differential fuzzer that generates text from the corpus plus mutations and compares findings with the Python oracle; a benchmark (recorded, not a goal).

*Done when:* all vectors pass and the fuzzer runs to the agreed length with every divergence triaged.

#### MG-R03 · `minicore-policy` · XL · Wave 6

*Checkpoint (revision 1.1):* the `MG-Z10` spike did not cover this package. If it takes more than **twice its estimate**, stop and run the gate in §1.1 again as a new, dated record, using this package's own numbers.

*Python source:* `policy/` (3,115 lines): `rules.py`, `modes.py`, `shellparse.py` (`parse`), `decide.py` (`decide`).

*What:* port in dependency order: `rules` (parsing and matching, layers), `modes`, `shellparse`, then `decide`. The public surface stays `decide(Request, Context) -> Decision`, pure, with no environment access. Port the invariant and robustness tests as `proptest` properties (deny beats ask beats allow; a protected path always asks; a compound command is as bad as its worst part).

*Differential fuzzing:* generate commands from a grammar and by mutating the Q07 corpus; compare `action`, `risk` and `basis` with the Python oracle. Run it for a fixed time in CI nightly and for longer before `MG-R13`. **Every divergence is triaged.** Rust must not be more permissive than Python anywhere (DM-10).

*Done when:* all `MG-Z03` vectors pass, every Q07 group passes (including the `known-fail-python` rows), the fuzzer is clean for the agreed time, and the crate holds no `unsafe`.

#### MG-R04 · `minicore-store` · M · Wave 5

*Python source:* `store/` (1,233 lines; tables `sessions`, `events`, `approvals`, `checkpoints`, `schema_version`).

*What:* `rusqlite` with bundled SQLite. **Same schema, same migration numbers, same SQL text, and the same pragmas as the Python migrations** (read `store/migrations.py` and copy them; do not guess). One writer task; reads through a pool.

*Done when:* Rust opens the `MG-Z06` golden database; a database created by Python at the tag is read, appended to by Rust, and read back by Python.

#### MG-R05 · `minicore-link` and `minicore-auth` · L · Wave 6

*Python source:* `link/` (1,959 lines: `client.py`, `reconnect.py`) and `auth/` (1,420 lines: device-code login, credential storage).

*What:* a WebSocket client (`tokio-tungstenite` is the candidate) with reconnect, backoff and `run.resume{last_seq}`; the handshake limits (hello within 10 s, 1 MiB messages); a table mapping every close code (1008, 1009, 1011, 4400, 4401, 4403, 4408, 4409, 4426, 4429) to the same client behavior as `reconnect.py`, with one test per code; TLS through `rustls` (no OpenSSL dependency, to be confirmed by the spike). Auth: the device-code login over HTTPS (choose a small HTTP client, `ureq` or `reqwest`, in the spike); credential in a `0600` file, or the OS keyring as an optional feature, in the **same file format the Python client wrote** (`MG-Z06`).

*Spike (decides §12):* glibc versus musl. The keyring backends differ (a C `libdbus` binding versus a pure-Rust one) and that decides whether a static musl build is possible.

*Done when:* fixture 03 (disconnect and resume) passes against a fake server, Rust reads a Python-written credential and the reverse, `logout` removes it, and 4401/4403 produce the documented behavior.

#### MG-R06 · `minicore-sandbox` · XL · Wave 6

*Python source:* `sandbox/` (3,193 lines): `bwrap.py` (argument builder), `profile.py`, `probe.py`, `netpolicy.py`, `netproxy.py` (CONNECT proxy), `bridge.py`.

*What:* first export the **pure** parts as vectors from `tests/sandbox/` (14 test files): a policy in, the exact `bwrap` argument list out; a network policy in, an allow or deny decision per host, port and IP literal out. Prove them on Python, then implement. `bwrap` stays an external binary and `doctor` still checks for it. The proxy and bridge are `tokio` tasks. Helper processes the sandbox starts get an environment with no tokens or keys. **D17 holds:** a sandboxed command still follows the permission flow, and auto-allow is refused when the probe fails. Tests that need a real `bwrap` run only where it is installed, the same condition as today.

*Done when:* the exported vectors pass, the sandbox tests that need `bwrap` pass on a runner that has it, and the Q07 sandbox rows (protected `.m2c/` files, the shared git directory of a worktree) pass.

#### MG-R07 · `m2c-tools` and the tool runner · L · Wave 7

*Python source:* `tools/` (3,581 lines: `files.py`, `search.py`, `shell.py`, `paths.py`) and `runner.py` (1,146 lines, `C24`).

*What:* the 11 tools of `protocol/v1/tools/` (`read_file`, `list_dir`, `glob`, `grep`, `edit_file`, `write_file`, `delete_path`, `bash`, `plan_exit`, `ask_user`, `tasks`). `glob` and `grep` keep shelling out to `rg`, which the README already requires. The runner executes server-proposed calls under the policy, redacts results, streams `tool_stream`, and returns `tool_result`. Port the nine `tests/tools/` files as Rust tests with the same inputs. Watch: Python's `fnmatch` and Rust glob crates do not agree on every pattern, so the policy's glob handling must go through the `MG-Z03` vectors, not an assumption.

*Done when:* transcripts 01 to 04 pass end to end against a fake server, and every case in `tests/tools/` has a Rust equivalent.

#### MG-R08 · `m2c-context`, trust and interact · M · Wave 7

*Python source:* `context/` (1,530 lines, `C12`), `trust/` (836 lines, `C26`), `interact/` (408 lines).

*What:* the instruction loader, whose `@path` import and code-span rules use a lookbehind and a backreference in Python; write them as small hand-built scanners and cover them with vectors (add a `context` area to `protocol/conformance/`). Folder trust: the fingerprint **coverage set** (`.m2c/hooks`, `.m2c/skills`, `.agents/skills`, `.claude/skills`, and every file that can change policy) must be identical to Python's; the hash values need not be, because a different value only makes the user trust a folder once more, which fails closed. `ask_user` and `tasks`.

*Done when:* the instruction vectors pass, a vector lists the fingerprint coverage set, and an untrusted folder's project settings and hooks are ignored.

#### MG-R09 · `m2c-checkpoints` · M · Wave 6

*Python source:* `checkpoints.py` (1,301 lines, `C08`/`C10`).

*What:* start with a one-page behavior inventory (this file was not read in detail for this guide). Keep shelling out to `git`, as today: `git` is already a hard requirement. A checkpoint made by Python at the tag must be restorable by Rust and the reverse if they share an on-disk format; if they do not, say so in `PARITY.md` and handle it at cutover.

*Done when:* `/rewind` round-trips in both directions on the golden fixtures, and a checkpoint is never half written (the `Q09` crash rows pass).

#### MG-R10 · `m2c-headless`, cli and doctor · L · Wave 8

*Python source:* `headless.py` (1,190), `cli.py` (468), `doctor.py` (481), `session_setup.py` (413), `repl.py` (421).

*What:* `clap` for the command line. Commands and flags exactly as in `PARITY.md`: `login [--device-name]`, `logout`, `doctor [--project PATH]`, `trust [--list|--forget PATH]`, `-p/--print` with `--output-format text|json`, `--mode plan|ask|accept-edits`, `--allow`, `--deny`, `--sandbox auto|required|off`, `--cwd`, `--plain`, `--version`. Exit codes 0, 1, 2, 3, 4, 5, 130, 143 with SIGINT and SIGTERM cancelling the run first (`tokio::signal`). `doctor` drops the Python check and adds an architecture line; it keeps the checks for `git`, `rg`, `bwrap`, the project location (warn on `/mnt/c`) and the config directory. In headless mode a call that would ask ends the run with exit code 3.

*Done when:* every `PARITY.md` row for commands, flags, exit codes and environment variables passes, and `-p --output-format json` output equals the Python client's on the golden runs after a normalizer removes timestamps and ids.

#### MG-R11 · `m2c-tui` · XL · Wave 8

*Python source:* `tui/` (3,004 lines, `prompt_toolkit` and `rich`).

*What:* a rewrite on `ratatui` and `crossterm`, not a line-by-line port. Behavior parity checklist: streaming reply text; the approval prompt and its keys; `/help`, `/rewind`, `/exit`; the `--plain` line-by-line fallback; terminal resize; Ctrl-C semantics; **terminal safety** (control characters in file names, paths, tool output and `-p` text are neutralized before they reach the terminal, the Q07 terminal rows); WSL2 terminals. Snapshot tests with `insta` over `ratatui`'s test backend.

*Done when:* the checklist is green, the snapshot tests cover the approval and diff views, and the `--plain` mode works with no TTY.

#### MG-R12 · Parity suite and install test · L · Wave 9

*What:*

1. **Golden-run parity.** Run the same scenario scripts through the Python client (at the tag) and the Rust client against the same fake server; compare the normalized event streams, the local store, and exit codes.
2. **Every vector and fixture** green in Python, Rust and (for the wire) TypeScript.
3. **Install test** in a clean Ubuntu container and a WSL2-like environment: install the binary, run `m2c doctor`, run one `-p` task against a fake server.
4. **Canary and red-team** (`Q06`, `Q03`) run against the Rust client. The `canary` CI job today installs the Python client with `pip install --no-deps -e ../m2c` (`ci.yml` line 404); it must install the Rust binary instead.
5. **Crash and resume** (`Q09`): kill the client at each step of a run; the local log must hold every completed turn or a clear marker.
6. **Footprint.** Re-measure startup and idle memory on your machine and record them beside the Python numbers in §3.
7. A long differential-fuzz run of `MG-R02` and `MG-R03`.

*Done when:* all of the above are green and the numbers are recorded.

#### MG-R13 · Cutover to the Rust client · S · Wave 10

*What:* tag the first Rust release; switch the `m2c-test` and `canary` jobs to `cargo`; update the README, `§2.2` and `C22` (release binaries, checksums, signing, the installer script that already checks for `bubblewrap`); retire `m2c/pyproject.toml` from the default build. **Keep the Python tree and the `m2c-py-ref` tag for one release** (DM-8), then delete the Python client.

*Done when:* a fresh install from the release artifact passes `MG-R12`'s install test and `PARITY.md` is fully ticked.

---

## 7. M2C work packages not built yet: where each lands

From `m2c_build_plan.md` §0.6 (rev 1.2). **Client halves are built in Rust (DM-9, once `MG-Z10` records `PROCEED`); server halves stay Python; web halves are TypeScript.** If the gate records `STAY PYTHON`, the client halves are built in Python as the build plan says.

| Work package | Client (Rust) | Server (Python) | Web (TypeScript) |
| --- | --- | --- | --- |
| `C13` hooks (D15: JSON on stdin, exit codes, tighten-only) | yes, new crate module on `minicore-policy` | none | none |
| `C14` skills (local files, never unattended without an allow rule) | yes | none | none |
| `C16` background subagents and the `m2c handoff` bundle | yes | `S11` side | Build-tab handoff |
| `C17` taint tracking and `web_fetch` / `web_search` | yes (`web_fetch` runs locally through the sandbox proxy) | `web_search` route (reuses `utils/web_search.py`) | none |
| `C25` safe "always allow" (D16) | yes | none | none |
| `C28` `--output-format stream-json` | yes | none | none |
| `C20`, `C21`, `L05`, `L06` review and security roles, doctor extensions | yes | role prompts | none |
| `L01` remainder, `L02` subagents, `L03` model-written summaries, `L04` | the client part of each | **the loop and context assembler** (`loop.py`, `context.py`) | none |
| `X03`, `X04` remote live view, `X01`/`X02` devices and usage pages | relay client side | relay | **yes** (uses the `MG-F01`/`MG-Z08` types) |
| `Q07` bypass corpus | vectors written in `MG-Z03` | none | none |
| `Q08` docs-drift check | runs against the Rust `--help` | none | none |
| `Q09` crash and resume tests | Rust fault-injection suite | fake server | none |
| `Q01`, `Q02`, `Q03`, `Q06` CI, evals, red-team, canary | run against the Rust binary | `backend/tests/canary` | none |
| `S11` server hardening | none | **track B** | none |
| `S12` beta allowlist and plan hooks | none | yes | settings UI |
| `C22` packaging, `X05`, `X06` release | binary release pipeline | none | docs |
| `C18`, `C19`, `L07`, `L08`, `C23`, `C27`, `S13` (Phase 5) | Rust | as needed | as needed |

---

## 8. Menux (Phase 3)

Menux starts when the Rust M2C reaches M2, the same milestone as before (if `MG-Z10` records `STAY PYTHON`, when the Python M2C reaches M2, and the rest of this section reverts to the Menux build guide's own wording). Nothing in Menux is built yet, so nothing is ported. What changes in the Menux guide:

| Menux element | Python-era plan | New plan |
| --- | --- | --- |
| `MT-K00` inventory | read-only inventory of the finished M2C | the same, of the Rust workspace |
| `MT-K01` extract `minicore` (size L, "extracting `minicore` breaks M2C") | move finished Python code into a shared package | **size S: a boundary check.** The `minicore-*` crates already exist from `MG-Z07`. K01 verifies that Menux depends only on them and that both products' tests pass. |
| Node runtime, scheduler (`D1`: `croniter` + SQLite) | Python | Rust. Add `scheduler/next_fire` vectors with `croniter` as the oracle before writing the Rust. |
| Spec format (`D7`: YAML validated by JSON Schema, "same parser on server and node") | PyYAML on both | **The server's PyYAML is YAML 1.1 and Rust YAML crates are mostly 1.2.** They disagree on `yes`/`no`/`on`/`off`, some number forms and merge keys. Define a strict subset, validate with JSON Schema on both sides, and add vectors that include the awkward scalars. |
| Vault (`D3`: OS keyring, else passphrase-derived, else `0600` file) | Python libraries | Rust: `keyring`, an Argon2id crate, an AEAD crate, zeroizing wrappers. Use audited primitives; do not invent any. |
| Tiers `T0`–`T5`, reader/actor (O6), approvals | Python `policy` extension | extension of `minicore-policy`. **Write the Menux policy tests as conformance vectors first**, then implement in Rust only. |
| Connectors (9) and channel adapters (6) | Python libraries | Decide **per connector**: a native Rust client, or a sidecar (TypeScript or Python) behind a connector interface when the Rust client is immature. Telegram's HTTP API is easy; IMAP and CalDAV are the ones to check. |
| Browser (Playwright) | Python, in the node | **TypeScript sidecar**, JSON over stdio, behind `ControlBackend` (MX9). The sidecar never holds tokens; the node injects what each call needs. |
| `agent-desktop` for Windows and macOS satellites | separate pinned process | unchanged |
| Coding delegation (O7) | `m2c -p "task" --output-format json` | unchanged: a process boundary is still the right one (it keeps M2C's checkpoints and sandbox). `stream-json` once `C28` lands. |
| Mesh (5R): signed commands, end-to-end encrypted frames, passkey step-up (`D31`) | Python | Rust node; schemas in `protocol/mesh/v1` go through the same codegen as `MG-Z08`. Use maintained crates for the primitives and for WebAuthn verification on the node. **Get an external review of the mesh design before it ships** (the guide already plans its own security review). |
| Controller (phone and web, `D37`) | web app | **TypeScript**, in the same Next.js app or a separate installable web app (§12); types from `protocol/mesh/v1`; the browser's WebAuthn API for step-up. |
| Relay `WS /v1/mate/mesh` (MX3: "the server is a pipe") | Python in the backend | Python first; the best Rust-gateway candidate later, decided by `MG-B06`. |

---

## 9. CI after the migration

| Job | Today | After |
| --- | --- | --- |
| `test` (backend) | `pip install -r requirements.txt`, pytest | `uv pip install`, pytest, type check on the ratchet paths (`MG-B05`), OpenAPI diff (`MG-F01`) |
| `lint` | ruff | unchanged |
| `daemon-test` | pytest on `daemon/` | **removed** (`MG-D04`) |
| `m2c-test` | pytest on the Python client | frozen until `MG-R13`, then replaced by the Rust jobs |
| `protocol` | schema and fixture checks, `pip install` | adds the Rust and TypeScript fixture replay and the regenerate-and-diff check (`MG-Z08`) |
| `conformance-python` | none | **new** (`MG-Z02`): all vectors on the reference |
| Rust jobs | none | **new** (`MG-Z07`): `fmt`, `clippy`, `test`, `deny`, `audit`, the allowlist test, conformance, nightly fuzz |
| `frontend-lint` | `npm run lint` | adds `npm run typecheck` and the no-check allowlist check |
| `frontend-test` | `node --test` | unchanged command; some tests import `.ts` |
| `canary` | installs the Python client | installs the Rust binary (`MG-R12`/`MG-R13`) |
| `secrets-scan`, `promptfoo` | as they are | unchanged (`promptfoo` gets `uv`) |
| load test | none | **manual or nightly against staging** (`MG-B00`), never against production |

### 9.1 Sequencing with the Provider Consolidation Guide (revision 1.1)

The **Provider Consolidation Guide** (Appendix B, `PV-00` to `PV-20`) replaces the free-tier providers with four paid models and a paid search service. It edits backend files that this migration also touches. Order the two like this.

| Rule | Why |
| --- | --- |
| **The Consolidation Guide goes first on every file it names as shared**: `backend/utils/llm_client.py`, `backend/eo/model_catalog.py`, `backend/utils/key_balancer.py`, `backend/config/provider_limits.json`, `backend/eo/registry.py`, `backend/eo/dynamic_chain.py`, `backend/agents/generic_worker.py`, `backend/utils/web_search.py`, `backend/requirements.txt`, `backend/.env.example`, `backend/config/*.json`, `.github/workflows/ci.yml`. | One writer per shared file (rule 7). Its patches replace large parts of these files. |
| **Land the CI edits of `MG-Z01`, `MG-Z07` and `MG-Z08` before `PV-00` starts, or after `PV-18`, not in between.** | Both change `ci.yml`, and `MG-Z01` changes how requirements are installed. |
| **`MG-B04` (blocking-call audit) and `MG-B05` (typing ratchet) wait for `PV-14`.** | `llm_client.py` contains blocking sleeps that `PV-14` rewrites; auditing it first wastes the audit. |
| **Do not convert `TokenUsageTab.jsx` (`PV-16`) or `LandingPage.jsx` (`PV-18`) to TypeScript before those packages are done.** | The Consolidation Guide edits both. |
| **Run `MG-B01` (the load baseline) only after the `PV-19` go-live.** | Numbers measured against free-tier keys are not the numbers the product will have. |
| **These may run at any time, in parallel with the Consolidation Guide:** `MG-Z00`, `MG-Z02` to `MG-Z06`, `MG-Z10`, `MG-D00` to `MG-D04`, `MG-F00` to `MG-F02` (except the two files above), and the whole **R** track. | They touch no file the Consolidation Guide names. |

---

## 10. Risks

| Risk | Where it bites | What to do |
| --- | --- | --- |
| **Regex semantics.** The detectors use lookaround and possessive quantifiers; Rust's `regex` has neither. | `MG-R02`, `MG-R08` | Linear-time engine plus explicit boundary checks; prove equivalence with vectors and the fuzzer. Do not reach for a backtracking engine by default. |
| **Shell parsing differences.** `shellparse` is the largest single function family and security-critical. | `MG-R03` | Pure-function port, differential fuzzing against the oracle, Q07 corpus, Rust never more permissive. |
| **Glob and path semantics.** `fnmatch`, Unicode normalization, trailing slashes, symlinks and non-UTF-8 names differ between Python and Rust. | `MG-R01`, `MG-R07` | Vectors for each; bytes, not `String`, for local paths. |
| **TOCTOU in the path guard.** Check-then-open is racy. | `MG-R01` | Descriptor-relative operations; race tests. |
| **Store compatibility.** Two clients writing one `M2C_HOME` during overlap. | `MG-R04`, `MG-R09` | Same SQL and pragmas; golden databases; compatibility tested both ways at the tag. |
| **TUI rewrite is a rewrite.** `prompt_toolkit` and `ratatui` are different models. | `MG-R11` | Behavior checklist and snapshot tests; do not chase pixel parity. |
| **Static linking and the keyring.** Secret Service bindings can block a musl build. | `MG-R05` | Spike before choosing; the choice is recorded (§12). |
| **Three-language drift.** Types and behavior silently diverge. | everywhere | DM-5: schemas, fixtures and vectors are the only definition, enforced in CI. |
| **YAML 1.1 vs 1.2** between the Python planner and the Rust node. | Menux `D7` | Strict subset plus JSON Schema plus awkward-scalar vectors. |
| **Scope creep during the port.** New features land in Python "just this once". | all | DM-9 and §4 rule 9. The frozen tag makes the rule visible. |
| **Load test touches production or real model keys.** | `MG-B00` | Staging database only; a fake model adapter that cannot be enabled when a production flag is set. |
| **TypeScript giant files stall.** | `MG-F04` | Two-step conversion with the allowlist that only shrinks. |
| **The gate is skipped, or its criteria are bent after the fact.** | `MG-Z10` | The criteria are committed in a decision record before the spike (rule 10) and the outcome follows from the table in §1.1. |
| **The spike passes but the full port is much bigger.** It covers about 900 of 27,000 client lines and none of the policy, sandbox or TUI crates. | `MG-R03` and later | The checkpoint in `MG-R03`: more than twice the estimate means run the gate again as a new record. |
| **Rust learning curve.** | `R*` | Start with `MG-R00` and `MG-R01` (small, well specified, fully vectored); they teach the toolchain on code you can check. |

---

## 11. Prompt template for one port patch

Same style as the Menux guide's template.

```
You are generating ONE patch for the MiniMe repo at commit [SHA].
Work package: [MG-ID: title] from docs/migration_guide.md (section 6).
Read first: m2c/PARITY.md, the Python module(s) named in the work package
(at tag m2c-py-ref), the matching tests, protocol/conformance/[area]/ and its
README, and sections 1, 4 and 10 of the migration guide.
Constraints: touch only [crates / files]; follow the Rust workspace conventions
(forbid(unsafe_code), no dependency not in rust/deps-allowlist.toml); the Rust
must never be more permissive than the Python reference (DM-10); fail closed on
anything unknown; do not edit a conformance vector to make a test pass.
Process: write a one-page behavior inventory of the Python module -> write the
Rust tests first (vectors, then properties) -> implement -> run
`cargo fmt --check`, `cargo clippy -D warnings`, `cargo test --workspace --locked`
and `python protocol/conformance/run_python.py --area [area]` before and after.
Security code: add or extend the differential fuzzer against `--oracle`.
Output one unified diff, [MG_ID]_[slug].patch, that applies with `git apply`
on [SHA]. List each "Done when" item with the evidence for it. If the work
package is wrong against the real code, STOP and report.
```

---

## 12. Decisions that are still yours

| # | Decision | Recommendation | Decide at |
| --- | --- | --- | --- |
| 1 | Daemon gate: option A, B or C (§6.3) | **A** | `MG-D00` |
| 2 | Does server-side MCP for the web agents stay? | Yes for now; it is separate from M2C's device-local MCP (D18) | `MG-D00` |
| 3 | glibc or musl for the released binary | Let the `MG-R05` spike decide; prefer whichever lets the keyring work | `MG-R05` |
| 4 | TUI library | `ratatui` + `crossterm` | `MG-R11` |
| 5 | Gateway language | Python until `MG-B06` has numbers | `MG-B06` |
| 6 | Menux controller: inside the Next.js app or a separate installable web app | Separate app if it needs its own service worker and offline shell; same app otherwise | before Menux Phase 5R |
| 7 | Rust client or sidecar for each Menux connector | Per connector (§8) | Menux Phase 3 |
| 8 | How long the Python client is kept after `MG-R13` | One release | `MG-R13` |
| 9 | `noUncheckedIndexedAccess` in TypeScript | Optional; turn on after `MG-F05` if the churn is acceptable | `MG-F05` |
| 10 | Where the load test runs (staging size) | The smallest box that can reach the target connection count | `MG-B01` |
| 11 | The gate's thresholds (C1 to C3, B1 to B3) and the time box | Use the suggested defaults in `MG-Z10`; write them into the decision record before the spike | `MG-Z10`, step 1 |
| 12 | If the gate says `STAY PYTHON`: how users get the Python client without installing a separate Python | Decide from the `B1` measurement (for example a single-file bundle that carries its own interpreter) | `MG-Z10` |

---

## 13. Evidence and what was not checked

**Read:** the MiniMe repo at `94af156`: `m2c/` (layout, line counts, `pyproject.toml`, README, the policy, secrets and store entry points and their test file lists), `protocol/` (README, `validate.py` header, schemas list, fixtures), `backend/codeagent/` (module headers, `ws.py` constants, `connections.py`, `buffer.py`), `backend/` (daemon-related files and their cross-references, dependency list, blocking-call grep), `frontend/` (package files, directory and file counts, largest files, test layout), `.github/workflows/ci.yml`, `backend.Dockerfile`, `DEFERRED.md`; the book at `aaca7f1`: the three guides' changed sections, `UPDATING.md`, `llms.txt`.

**Measured:** the Python client's startup, in a cloud sandbox, five runs per command (§3). Not on your machine.

**Not done:** no test was run (Python, Rust or TypeScript); nothing was built; no crate, package or tool version was verified, and none is recommended by number; `checkpoints.py`, `link/`, `auth/`, `sandbox/` and `tui/` were sized but not read in detail (their work packages begin with a behavior inventory for that reason); the policy and redaction function bodies were not reviewed; the claim that Rust's `regex` crate lacks lookaround and possessive quantifiers was confirmed and corrected in revision 1.2 (below), but only for the one version tested; the Node type-stripping claim rests on the release notes cited in `MG-F00` and must be confirmed on your Node 22.22.0 by that work package's spike; the size of every work package is an estimate.

**Revision 1.1 additions (2026-11-21).** Read from the MiniMe repo at `3727ae3`: `secrets/redact.py` (657 lines; a text search found 10 lines with lookaround syntax and 2 with possessive quantifiers; §3's count of 11 and 2 counts assertions, so re-count in `MG-Z10`), the secret-handling test folder (84 test functions in files whose path contains "secret"), and the policy module layout. **Run once:** the M2C test suite, in a cloud sandbox as root, with `ripgrep` and `bubblewrap` not installed: 6,401 passed, 134 skipped (the skips are the tests that need those two tools; they run in CI, which installs them). **Read in part:** the Provider Consolidation Guide (its hazards, decisions, patch index, `PV-06` and `PV-18`). **Not done in revision 1.1:** the `MG-Z10` spike itself; no Rust was written or built; Rust's `regex` limits and the Python version on a clean Ubuntu 22.04 were not checked and are `MG-Z10` steps.

**Revision 1.2 checks (2026-11-21, run in a Linux sandbox; none of this replaces `MG-Z10`).**

- **Rust `regex` limits, run.** A small program was built against `regex` 1.13.2 (`regex-syntax` 0.8.12) with Rust 1.75 (the Ubuntu 24.04 package). Lookahead and lookbehind (`(?<!x)`, `(?<=x)`, `(?!x)`, `(?=x)`) fail to compile with "look-around, including look-ahead and look-behind, is not supported". Backreferences (`(a)\1`) fail with "backreferences are not supported". Atomic groups (`(?>a+)`) fail as an unrecognized flag. **Possessive quantifiers do not fail:** `a*+`, `a++`, `a?+` and the bounded form `{n,m}+` all compile, and they behave as an ordinary greedy repeat. `a*+a` matches `aaa` in Rust and does not match in Python 3.12. The two real patterns in `secrets/redact.py` were tested as fragments (`[A-Za-z0-9_.-]{0,64}+` on line 337 and `[A-Za-z0-9+/_-]{20,200}+={0,2}` on line 351 of the copy in `data/src/`): both compile in Rust, and a pattern that adds the lookahead from line 351 is rejected. So lookaround is a loud failure and possessive is a silent one; the lint in `MG-Z10` step 4 exists for that reason.
- **Python on Ubuntu 22.04, read from the package index, not from a container.** The `jammy` and `jammy-updates` indexes list `python3` as 3.10.4 and 3.10.6 (the `python3.10` package is 3.10.12). The only 3.11 is `python3.11` 3.11.0~rc1 in `jammy-updates/universe`, a release candidate. There is no `python3.12`. `bubblewrap` 0.6.1 is in `main` and `ripgrep` 13.0.0 is in `universe`. M2C declares `requires-python >=3.11` (decision D1), so a clean 22.04 needs another Python source (a third-party repository, `uv`, `pyenv` or a build from source) before the Python client runs, and that is the extra step `B1` expects. Not run: an actual 22.04 container, so the exact commands and the default WSL2 Ubuntu image are still `MG-Z10` work.
- **Not checked in revision 1.2:** Rust behaviour on other `regex` versions, Python 3.11 versus 3.12 differences in the possessive syntax beyond the one example, and anything on Windows or macOS.

**Sources:** [Node.js v22.18.0 release notes](https://nodejs.org/blog/release/v22.18.0) (native type stripping on by default).
