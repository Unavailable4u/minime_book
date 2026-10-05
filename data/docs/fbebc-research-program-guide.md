# FBEBC Research Program — From Zero-Cost Preprint to MiniMe-Integrated Production Research

**A standalone, two-stage execution guide**

This guide covers the full arc we settled on: a small, time-boxed, zero-cost proof-of-concept now, feeding an arXiv preprint; then a separately funded, MiniMe-integrated production research stage later, gated on Basic tier revenue. It assumes you've read (or will keep alongside this) the earlier **Phase 1 Implementation Guide** (`fbebc-phase1-implementation-guide.md`) — that document is the deep reference for every mechanism named here. This guide tells you what to keep from it, what to cut, what to defer, and in what order, for *this specific two-stage plan*.

The companion document, **`fbebc-preprint-workshop-paper-guide.md`**, covers writing and submitting the paper itself. This guide covers building the thing the paper is about.

---

## 0. The shape of the whole program

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1 — Preprint (now, 4 weeks, $0)                            │
│ Toy tasks · correctness-only · free-tier LLM · your laptop       │
│ Output: arXiv preprint + open-source repo + (maybe) workshop sub │
└─────────────────────────────────────────────────┬─────────────────┘
                                                    │
                                          ▼ GATE (§3)
                                          Basic tier launched,
                                          ops manageable,
                                          research budget line defined
                                                    │
┌─────────────────────────────────────────────────▼─────────────────┐
│ STAGE 2 — MiniMe-Integrated (post-launch, funded by revenue)      │
│ Real agents · real evals · real cost data · isolated research fork│
│ Output: production case study + internal PRs + (maybe) 2nd paper │
└─────────────────────────────────────────────────────────────────┘
```

Two rules govern the whole program, and everything below is downstream of them:

1. **Stage 1 is time-boxed, not scope-boxed.** You cap it at 4 weeks and ship whatever you have, rather than expanding scope to hit a quality bar. A capped preprint beats an uncapped project that eats Phase 0's runway.
2. **Stage 2 never touches live MiniMe directly.** It runs in an isolated fork against a staging copy of your data stores. Every promotion into the real system goes through a human-reviewed PR — no exceptions, regardless of how well Stage 2 is going.

---

## STAGE 1 — Preprint Research Plan

### 1.1 What's cut from the original design, and why

The Phase 1 guide was written for a publication-grade, adversarially-hardened, timing-fair system. That's the wrong bar for a 4-week solo preprint. Here's the explicit scope cut:

| Component | Full design (Phase 1 guide) | Stage 1 scope | Why |
|---|---|---|---|
| Sandbox runtime | gVisor, seccomp, cpuset pinning | **Docker with basic hardening** (`--network=none`, `--read-only`, `--cap-drop=ALL`, `--pids-limit`) | gVisor setup/tuning costs days you don't have. Docker's isolation is weaker but sufficient for a research prototype whose adversary is an undirected optimizer, not a targeted attacker — and you'll say so plainly in Limitations. |
| Fitness signal | Correctness + latency, timing cross-checked | **Correctness only** | This is the change that makes the whole project free — see the earlier conversation on why latency-based fitness is what forces bare metal. Dropping it doesn't remove the novel parts (barrier architecture, score non-authorship, frozen edit metric). |
| Adversarial suite | 24 cases, 5 tiers, live red-team (K≥500) | **8–10 cases covering Tiers A (boundary) and C (reward-hacking)**, no live red-team | You're one person with 4 weeks. A focused subset that hits the two tiers that actually matter for a correctness-only system (boundary integrity, score non-authorship) is honest and sufficient for a preprint. State the reduced scope explicitly in the paper. |
| Noise/determinism controls | Full environment fingerprinting, seed injection, CPU pinning | **Seed injection only** | You need reproducibility (same seed → same result), not noise-floor characterization — that's a Stage 2/latency-only concern that doesn't apply here. |
| Ledger | Hash-chained, SQL schema, full fingerprint | **Simplified hash chain, fewer columns** | Keep the hash chain (it's ~30 minutes of work and gives you a real provenance claim for the paper) but drop the environment-fingerprint columns that only matter for timing claims. |
| Task suite | Full ADRS/ARC-AGI-2/Frontier-CS benchmarks | **1 warm-up toy task + 1 real benchmark task (circle packing)** | See §1.2. |

Everything else — the Σ-Δ structural separation, the six-gate admission pipeline, the EVOLVE-BLOCK parser and bounded applicator, the frozen AST edit-distance metric, elite-band selection, the manifest-verified barrier — **carries over unchanged**. These are the actual intellectual contributions, and they cost nothing extra to keep.

### 1.2 Task selection

You need tasks that are (a) cheap to score, (b) scored by a deterministic function of the output, not by wall-clock time, and (c) recognizable to reviewers so your results are interpretable against the literature you're already citing.

**Warm-up task (week 1–2, pipeline debugging only, not reported in the paper): improve a bin-packing heuristic.**
Given a list of item sizes and a bin capacity, evolve a function that assigns items to bins. Score = number of bins used (lower is better) on a small fixed instance set. Trivial to implement, trivial to verify, and it exists purely so you find your pipeline's bugs on a cheap task before spending your real experiment's API budget.

**Primary task (week 3, the one you report): circle packing.**
Maximize the sum of radii of `n` non-overlapping circles packed inside a unit square. This is deliberately the same task AlphaEvolve showcased publicly, which buys you three things:
- A known, cited reference point to sanity-check your results against (you're not claiming to beat it — you're demonstrating the governance mechanism works on a task the field already recognizes).
- Purely geometric, programmatic scoring: sum of radii, with a fast overlap check (`O(n²)` pairwise distance check) as the correctness gate. No timing dimension anywhere in the definition.
- A clean EVOLVE-BLOCK target: a single `candidate_packing(n) -> list[(x, y, r)]` function, easy to contract-pin (fixed signature, fixed return shape).

Use `n = 26` (a size AlphaEvolve reported on) so your numbers are directly comparable in the related-work discussion, but be honest that your run count and compute budget are orders of magnitude smaller — that comparison is about validating the mechanism works, not about matching their result.

```python
# EVOLVE-BLOCK-START: circle_packing
def candidate_packing(n: int) -> list[tuple[float, float, float]]:
    """Return n (x, y, r) tuples: circle centers and radii, all inside
    the unit square [0,1]x[0,1], pairwise non-overlapping.
    CONTRACT: signature fixed. Return exactly n tuples.
    """
    # Generation-0 seed: naive grid placement, small fixed radius.
    import math
    side = math.ceil(math.sqrt(n))
    r = 1.0 / (2 * side)
    out = []
    for i in range(n):
        x = (i % side + 0.5) * (1.0 / side)
        y = (i // side + 0.5) * (1.0 / side)
        out.append((x, y, r))
    return out
# EVOLVE-BLOCK-END: circle_packing
```

Host-side scorer (correctness gate + fitness, no oracle needed here since the objective *is* the fitness — this is one of the nice properties of optimization tasks vs. classification tasks):

```python
def score_packing(circles: list[tuple[float, float, float]], n: int) -> dict:
    if len(circles) != n:
        return {"fitness": 0.0, "valid": False, "reason": "wrong_count"}
    for x, y, r in circles:
        if r <= 0 or x - r < -1e-9 or x + r > 1 + 1e-9 or y - r < -1e-9 or y + r > 1 + 1e-9:
            return {"fitness": 0.0, "valid": False, "reason": "out_of_bounds"}
    for i in range(len(circles)):
        for j in range(i + 1, len(circles)):
            x1, y1, r1 = circles[i]; x2, y2, r2 = circles[j]
            if (x1 - x2) ** 2 + (y1 - y2) ** 2 < (r1 + r2) ** 2 - 1e-9:
                return {"fitness": 0.0, "valid": False, "reason": "overlap"}
    return {"fitness": sum(r for _, _, r in circles), "valid": True}
```

### 1.3 Zero-cost resource stack (concrete)

| Need | Resource | Limit to respect |
|---|---|---|
| Σ-LLM | Gemini 2.5 Flash-Lite, free tier via AI Studio | ~1,000 requests/day, no card required (verify current limits at ai.google.dev/gemini-api/docs/rate-limits before you start — these move) |
| Dev environment | Your laptop | Linux or WSL2, not macOS/Windows Docker Desktop (VM layer breaks the isolation semantics you're testing) |
| Sandbox execution | Same laptop, Docker | No timing claims, so no noisy-neighbor concern |
| Version control / CI | GitHub (free), your Student Pack's Copilot for coding assistance while you build | — |

Total infrastructure cost: **$0.** The only scarce resource is your daily LLM request quota and your own time.

### 1.4 Week-by-week plan (hard cap: 4 weeks)

**Week 1 — Core mechanism, no LLM calls yet.**
- Day 1–2: Repo scaffold, `P_0` seed for both tasks, manifest builder (`delta/integrity/manifest.py` from the Phase 1 guide, unchanged).
- Day 3–5: EVOLVE-BLOCK parser + bounded applicator (`blocks.py`, `applicator.py`, unchanged from the Phase 1 guide) + contract verification (`contracts.py`). Unit-test all of this against hand-written diffs — no LLM needed to validate the applicator's post-conditions.
- Day 6–7: Frozen AST edit-distance metric (`metrics.py`, unchanged — freeze it now, before you've seen any real mutation data).

**Week 2 — Sandbox, ledger, and the mutation loop.**
- Day 8–9: Docker sandbox (simplified flags per §1.1), supervisor/child process split for the bin-packing warm-up task.
- Day 10–11: Simplified ledger (hash chain, correctness-only columns). Wire admission gates G0–G3 (skip G4's fairness *threshold* — you still record the edit-distance metric, you just don't reject on it yet) and G5 (integrity re-check).
- Day 12–14: Σ client against Gemini free tier, rejection-feedback loop, end-to-end run on the **warm-up task**. Debug until a full generation cycle runs clean.

**Week 3 — The real experiment.**
- Day 15: Switch to the circle-packing task. Sanity-check `P_0` scores correctly.
- Day 16–20: Run the actual experiment. See §1.5 for the exact call budget and how many days this realistically needs given free-tier limits — plan to let it run in the background across most of this week while you do other things.
- Day 19–21 (overlapping): Run the scoped 8–10 case adversarial suite (Tiers A and C from the Phase 1 guide's Appendix B) against your own pipeline. Fix anything that fails.

**Week 4 — Analysis, ablation, writing.**
- Day 22–23: Run the one required ablation: **elite-band selection vs. single-winner selection** (AlphaGo-Zero-style, >55% win margin) on the same task and budget. This is your one comparative result — don't skip it, it's what turns "we built a thing" into "we tested a claim."
- Day 24–26: Produce the figures/tables (see the paper guide for exactly what's needed), write the draft.
- Day 27–28: Buffer for revisions, code cleanup for the public repo release, arXiv submission.

If you overrun, **cut scope, not the cap** — ship with fewer generations or a smaller ablation before you extend past 4 weeks.

### 1.5 Call-budget math (so you know if a week is realistic)

Assume population 40, generations 25 per run, 3 seeds for the primary task plus 1 elite-band-vs-single-winner ablation run pair (2 more runs):

```
40 candidates × 25 generations = 1,000 mutation calls per run
5 runs total (3 seeds + 2 ablation conditions) = 5,000 calls
At ~1,000 free-tier requests/day → 5 days of continuous quota use
```

That comfortably fits inside Week 3's 7 days, including buffer for failed/rejected calls that don't count against your "useful" total but still consume quota. If you find the daily cap binding, drop to population 25–30 or 2 seeds rather than extending the timeline — a smaller, honestly-reported experiment beats a rushed larger one.

### 1.6 Exit checklist — Stage 1 is done when:

- [ ] `P_0` improves measurably over generations on circle packing (even a modest gain is a valid, reportable result)
- [ ] Manifest integrity holds across every evaluation in every run (this is your barrier-integrity claim, scaled down but real)
- [ ] The 8–10 case adversarial suite passes
- [ ] The elite-band vs. single-winner ablation ran and produced a comparable result
- [ ] Ledger chain verifies end-to-end
- [ ] Repo is clean enough to open-source (README, seeds, exact model version/date used — Gemini models get updated silently, so log the exact model ID and the date you ran)
- [ ] Draft written per the paper guide
- [ ] arXiv account created, category chosen (see paper guide §4)

### 1.7 Explicit "do not do this in Stage 1" list

Scope creep is the main risk to the 4-week cap. Do not, during Stage 1:

- Add latency/timing measurement "just to have the data" — it doesn't fit the story you're telling and it's expensive to make trustworthy.
- Expand the adversarial suite toward the full 24 cases — 8–10 well-chosen cases is defensible for a preprint's scope.
- Add a second benchmark task beyond circle packing "for robustness" — one well-executed task beats two rushed ones.
- Start integrating with MiniMe in any way. That's Stage 2, gated (see §3), and pulling it forward defeats the entire point of time-boxing Stage 1.
- Chase gVisor or bare-metal rental "to be safe" — you already decided the timing dimension is out of scope, so the isolation bar that motivated bare metal doesn't apply here.

---

## 2. Between Stage 1 and Stage 2 (indefinite gap — this is fine)

There's no fixed timeline here. Stage 1 produces a preprint and, ideally, a workshop submission. Then you go back to MiniMe's Phase 0/1 roadmap and focus there. **Do not try to run Stage 2 in parallel with launching Basic.** The gate below exists precisely to prevent that.

---

## 3. The gate between Stage 1 and Stage 2

Stage 2 starts only when **all** of these are true — the same discipline your MiniMe roadmap already applies to starting the Moderate tier:

1. **Basic tier is launched and generating revenue.** Not "about to launch" — actually live and billing.
2. **Basic's day-to-day operational load is manageable** without consuming most of your attention (your roadmap's own §3.5 gate, applied here too).
3. **A separate research budget line is defined in writing**, capped, and explicitly ring-fenced from Basic's operating burn (e.g., "up to $50/month of Basic's margin, revisited quarterly"). If a bad month in the research fork would threaten Basic staying break-even, the budget is too large or Basic isn't ready yet.
4. **You've written down, in advance, what "attested" and "promotable" mean** for a candidate agent/prompt config in this context — your own version of the Phase 1 guide's exit criteria, scaled to this use (see §4.7 below for a starting template).

Don't start Stage 2 on momentum from a good Stage 1 result. Start it when these four conditions are independently true.

---

## STAGE 2 — MiniMe-Integrated Research Plan

### 4.1 What changes from Stage 1, and why it's now worth the cost

Two things flip in Stage 2, and both are justified by the fact that you're now optimizing something with real financial consequences rather than a toy benchmark:

- **Latency/cost re-enters the fitness function.** In Stage 1 it was pure overhead with no payoff. In Stage 2, a candidate agent config that's 20% cheaper per task at equal quality is a real margin improvement for Basic — this is precisely the kind of comparison your roadmap's Part 3.3 already asks you to make by hand ("run the same task both ways... compare real output quality"). FBEBC automates that, and now it's worth the infrastructure to measure it honestly.
- **The task suite becomes real MiniMe evals**, not toy tasks. Your `backend/evals/promptfoo` suite already exists — you're not building a benchmark from scratch.

### 4.2 Choosing the mutation target: prompt text, not Python source

This is the single most important safety decision for Stage 2, and your own repo hands you the right answer.

Your role prompts (`eo/registry.py::ROLE_PROMPTS_SEED`) live in **Upstash Redis**, are fetched live by `providers/role_provider.py`, and are already mutable at runtime through the existing Panel brief-writer / `PUT /api/roles/{role_name}` path. This means **prompt text is already treated as data, not code**, in your architecture — it's fetched, not imported or executed as source.

That makes prompt-text evolution a dramatically lower-risk EVOLVE-BLOCK target than mutating `.py` files in `backend/agents/` or `backend/eo/`:

| | Mutating `.py` source (backend/agents, backend/eo) | Mutating prompt text (Redis-backed) |
|---|---|---|
| Blast radius if wrong | Can change control flow, imports, capability surface | Changes what an LLM is told; the calling code path is unchanged |
| Relationship to `DEFERRED.md` | **This is exactly the deferred "write/execute capability on the backend's own code" item** — the atomicity problem is explicitly unsolved | Not what that item is about at all — prompts aren't executed, they're passed as input to `generate_text()` |
| Rollback | Needs the verify-then-promote/atomic-swap design that's explicitly not designed yet | Trivial — write the old string back to Redis |
| Existing tooling | None yet | `role_provider.py`, the whole promptfoo suite, and the `provider_override` / `compare/providers.promptfooconfig.yaml` pattern already exist |

**Decision: Stage 2 evolves role prompt text only.** Treat Python source-code self-modification as a *separate, later* project — one that genuinely does need the atomic-write/verify-then-promote design `DEFERRED.md` flags as undesigned, and shouldn't be attempted until that design work happens on its own, deliberately, the same way the daemon is being deliberately deferred. Don't let Stage 2's success tempt you into quietly expanding scope into source mutation — that's a materially different risk category and deserves its own gate, not an upgrade path from this one.

### 4.3 Isolation architecture

```
┌───────────────────────────────────────────────────────────┐
│  LIVE MiniMe (untouched by any of this)                    │
│  Production Redis · Production Postgres · Real user traffic│
└───────────────────────────────────────────────────────────┘
                         ▲
                         │  (one-way: promoted PRs merge in,
                         │   reviewed by you, nothing writes
                         │   back automatically)
┌────────────────────────┴──────────────────────────────────┐
│  RESEARCH FORK (isolated)                                   │
│  - git clone of the repo, separate directory/VM             │
│  - staging Redis instance (NOT the production Upstash URL)  │
│  - `ROLE_PROMPTS_SEED` copied in as P_0 for each role tested │
│  - promptfoo's role_provider.py + your test YAMLs, reused    │
│    unmodified as the Δ scorer                                │
│  - Σ-LLM proposes replacement prompt strings                 │
│  - Δ evaluates via promptfoo against the SAME rubric/asserts │
│    used in CI today                                          │
└───────────────────────────────────────────────────────────┘
```

Hard rule: **the research fork's `.env` points at a staging Redis and staging provider keys, never the production `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN` or production LLM keys.** Check this before every run, not just once — a copy-pasted `.env` is the most likely real failure mode here, not an adversarial escape.

### 4.4 Building the Δ-scorer on top of what already exists

Your promptfoo suite already grades most roles with `llm-rubric` (an LLM judges the output against a stated rubric) and a few with `type: python` deterministic asserts (like `output_organizer`). This is your oracle — but it needs one adjustment for FBEBC's score-non-authorship principle to hold meaningfully:

- **Pin the judge model version explicitly**, separate from whatever model Σ uses to propose prompt mutations. If Σ and the judge are the same model, a mutation that happens to match that model's own stylistic preferences could look better than it actually is — a soft version of reward hacking. Use a different model family for the judge where practical (e.g., Σ on Gemini, judge on a different provider you already have a key for from your existing `role_provider.py` provider list — Groq, Mistral, etc.).
- **Log every judge verdict into the ledger**, not just the pass/fail. This gives you judge-drift as a monitored metric over time (if the judge model gets silently updated by its provider, your grading criteria shift under you — worth knowing, not worth panicking over).
- **Prefer deterministic asserts over rubric grading wherever a role allows it.** For roles like `output_organizer` that already have `type: python` structural checks, use those as the primary gate and treat rubric grading as secondary — deterministic checks aren't gameable the way an LLM judge softly can be.
- Reuse the exact `provider_override` mechanism already in your test files to keep judge calls deterministic and reproducible, the same way it's used today to pin CI to a specific Groq key.

### 4.5 Promotion pipeline

```
Σ proposes prompt variant
   ↓
Δ runs it through role_provider.py against existing promptfoo cases
   (staging Redis, staging keys)
   ↓
Passes all assertions + judge score above threshold?
   ↓ yes
Candidate logged as "attested" in the ledger, with full diff + score history
   ↓
Opens as a PR: old prompt vs. new prompt, side by side, with the eval
   run's full output attached
   ↓
YOU review it — same as any other config change
   ↓
Merge → new string written to ROLE_PROMPTS_SEED (or, once you're
   confident, directly to production Redis via the existing Panel
   brief-writer path — never automatically)
```

No step in this pipeline writes to anything live without your explicit merge action. This is the same posture your roadmap already holds toward every other production change.

### 4.6 Budget and compute

- **Compute:** No latency claims means Docker-on-a-small-rented-VM is fine here too — you don't need bare metal even in Stage 2, *unless* you specifically want to validate that a prompt change also improves real task latency (a legitimate thing to want, since latency affects your cost-per-task). If you do want that, that's the one place a short, cheap rental (a few days on a small Hetzner/Azure-credit box, per the earlier cost guide) earns its keep — rent it for the validation run only, not as standing infrastructure.
- **LLM cost:** Real API calls now, on your actual production provider keys' *staging* equivalents (or the free tiers of the same providers if their limits suffice for this smaller-scale task). Budget: start at the $10–30/month range and adjust based on how many roles you're actively evolving.
- **Ledger:** keep this on a genuinely separate budget line from Basic's operating burn, per the gate in §3.

### 4.7 A starting template for "attested and promotable"

Write your own version of this before Stage 2's first run, per the gate condition in §3.4:

- [ ] Candidate passes 100% of the role's existing promptfoo assertions (no regressions)
- [ ] Judge score (where rubric-graded) is at or above the current production prompt's score on the same held-out cases
- [ ] Manifest integrity held throughout the evaluation (no sandbox/scorer tampering — carried over unchanged from Phase 1)
- [ ] AST/text edit distance from the seed prompt is recorded (even without a hard cap, tracking drift matters — this is your Gap-3-equivalent for this stage)
- [ ] A human has read the full diff and the full eval transcript before merging — not just the score

### 4.8 What this produces

Beyond the direct product value (better or cheaper prompts, a real answer to Part 3.3's manual A/B-testing question, now automated), this stage gives you:

- A genuine production case study — "we applied a safety-governed evolutionary search mechanism to a live SaaS's agent configuration and it produced measurably better prompts, validated against our existing eval suite, with zero unreviewed production writes." That's a materially stronger paper than the Stage 1 toy-task preprint, and a natural candidate for the GECCO or stronger-workshop target discussed earlier.
- Real cost-per-task data feeding back into Part 6/7 of your roadmap's earnings model — this stage isn't purely a research side-project, it's also doing work your roadmap already says needs doing.

---

## 5. Master timeline

| Period | What's happening | Funded by |
|---|---|---|
| Now, 4 weeks | Stage 1: preprint build + write-up | $0 (free tiers only) |
| After Stage 1 | Return full attention to MiniMe Phase 0 | — |
| Indefinite gap | MiniMe Phase 0 → Phase 1 (pilot) → Phase 2 (Basic launch) | Per the MiniMe roadmap, unchanged |
| Gate clears (§3) | Decide to start Stage 2 | — |
| Post-launch | Stage 2: MiniMe-integrated research, capped monthly budget | Basic's revenue, ring-fenced |

Nothing in this guide changes your MiniMe roadmap's own timeline. Stage 1 fits before or alongside early Phase 0 work precisely because it's capped and free; Stage 2 is, by design, just another item in your existing self-funding cascade.
