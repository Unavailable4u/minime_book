# MiniMe Atlas - machine-readable summary

Snapshot 2026-10-21, commit ea56d44.

- 801 files, 160,153 lines of code, 9,116 functions, 175 API routes, 554 commits.
- Graph: 13,004 nodes, 29,813 links (Graphify run of 2026-10-05, commit `febb685`; not regenerated with the census, the graph is built separately).

## Data files
- data/census.json: per-file and per-function metrics, routes, git history, dependencies.
- data/docs/MiniMate___Build_Execution_Guide.md
- data/docs/MiniMe_Financial_Strategy_Rulebook.md
- data/docs/STATUS.md
- data/docs/fbebc-phase1-implementation-guide.md
- data/docs/fbebc-preprint-workshop-paper-guide.md
- data/docs/fbebc-research-program-guide.md
- data/docs/minimake_build_plan.md
- data/docs/minime_server_management_guide.md
- data/docs/minime_technical_roadmap.md

## Complete 14-Chapter Book Inventory (Synchronized)
- **Part I — Strategy, Governance & Master Sequence**: `MiniMe_Financial_Strategy_Rulebook.md`, `minime_technical_roadmap.md`, `minime_server_management_guide.md`
- **Part II — MiniMe Core Flagship (Web Workspace)**: `minime_feature_guide.md` (25 subsystems, 73 agent modules / 46 router roles)
- **Part III — MiniMake (Local-First Terminal & Editor Coding Agent)**: `minimake_feature_guide.md` (16 sections), `minimake_build_plan.md` (64 WPs, 12 waves, 157 pts), `guides/MiniMake___Product___Build_Guide.html`
- **Part IV — MiniMate (Local-First Personal Automation Agent)**: `minimate_feature_guide.md` (18 sections), `MiniMate___Build_Execution_Guide.md` (59 WPs, 16 waves, 133 pts), `guides/MiniMate___Product___Build_Guide.html`
- **Part V — FBEBC Research Program**: `fbebc-research-program-guide.md`, `fbebc-phase1-implementation-guide.md`, `fbebc-preprint-workshop-paper-guide.md`, `STATUS.md`
- **Unified Ecosystem Principles**:
  1. **One Account, One Plan Cap, One Shared Ledger (`0012_usage_ledger_and_plans.sql`)**: Built once in `Tech-A`/`Tech-B` + `S01`, shared across `surface in ('web', 'minimake', 'minimate', 'system')`.
  2. **Local-First Trust & Zero Server Bloat (Overrides O1–O8)**: MiniMake and MiniMate run all tools, files, shells, cron jobs, channels, Playwright, and encrypted vaults on the user's device; the server runs the stateless brain turn loop (`/api/codeagent/*`, `/api/minimate/*`), usage accounting, and a tiny 2h/24h Redis event buffer.
  3. **Shared `minicore/` Package**: Extracted in `MK_P00` and shared by `backend/`, `minimake_cli/`, and `minimate/`.
