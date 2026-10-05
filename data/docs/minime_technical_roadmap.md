# MiniMe — Technical Implementation Roadmap

**Companion to:** `MiniMe — Complete Production & Market Roadmap` (business plan, unchanged)
**Scope of this document:** engineering only — what gets built, in what order, gated by what evidence, mapped against (but tracked separately from) the business roadmap's Phase 0 → 3b.

**How to read this doc:** every technical phase below (Tech-A, Tech-B, ...) names which Business Phase it runs alongside, and what business-side gate (if any) has to clear before it can start. Nothing here changes the business roadmap's timeline, funding logic, or phase names — this is the "what do I actually build, this week, in what order" layer underneath it.

---

## 0. Recommendation: where Brain design starts

You asked for my call on this, so here it is, with the reasoning:

**Brain gets an internal-only prototype during late Business Phase 2 (Basic live, generating real revenue and real usage data) — not Phase 0/1, and not held back entirely until Phase 3a.**

Reasoning:

- **Not Phase 0/1** — there's no real task-shape data yet to design a meta-planner against. Brain's whole value is choosing structure based on what tasks actually look like; before Basic has live traffic, you'd be designing it against guesses, the same mistake the business roadmap explicitly avoids elsewhere ("gate every tier's build on real demand signal, not speculation" — Part 3.6). Phase 0/1 is also solo-only per your own hiring table; Brain is the single highest-complexity piece of this whole system, and building it alongside first-launch pressure is the "two tiers' operational load at once" failure mode your own roadmap flags as the riskiest moment in the whole plan.
- **Not purely "starts in Phase 3a"** — if Brain's core mechanism (structure-as-declarative-plan, primitive composition, template promotion) is invented for the first time under the pressure of an actual committed Moderate build, you're testing your riskiest new mechanism and shipping a paying-tier product on the same clock. That inverts your own "prove before build" discipline.
- **The middle path**: once Basic is live and stable (Business Phase 2, after its own exit criteria are trending but before Moderate's gates are declared met), spend a bounded slice of time on an **internal-only, non-shipping prototype** — feed it real historical task data from `routing_memory.py`'s logs, let it propose structures for tasks you already know the right answer to, and score it against what Panel/staff_task actually did. No real users ever touch it. By the time Business Phase 3a's gates (3.5 operational capacity, 3.6 demand signal) actually clear, you're not inventing Brain from zero — you're integrating something already de-risked against real data.

This is also the cleanest way to avoid the two axes (mode-gating vs. package-gating) fighting each other later: you get to observe, before committing, whether Brain's judgment is actually good enough to be worth the latency/cost it adds under expert/beast — instead of finding that out in production, on a paying Moderate customer's task.

---

## 1. The two-track view

```
BUSINESS TRACK (unchanged):
Phase 0 ──────────────► Phase 1 ──► Phase 2 (Basic live) ──► Phase 3a (Moderate) ──► Phase 3b (Ultimate)
  Foundation              Pilot        Real launch              Demand-gated            Demand-gated

TECHNICAL TRACK (this doc):
Tech-A   Tech-B                Tech-C          Tech-D              Tech-E        Tech-F        Tech-G      Tech-H
Instrument Basic-harden   [gap: live &      Brain proto      Moderate       Monitor v2   Ultimate    Code-authoring
& baseline  for real users  stable, no        (internal only,  scaffolding +  (stream-     brain tier   (gated,
                            new tech work    against real     Brain          based,       (frontier    no fixed
                            here — this is   historical data) integration    closed-loop) model)      date, see
                            the deferred-                                                              §8)
                            scaffolding
                            window you
                            chose]
```

The gap between Tech-B and Tech-C is deliberate — you chose to defer scaffolding rather than build it into Basic, so that window is "Basic runs in production, gets real data, nothing new gets engineered" until Business Phase 2's exit criteria are trending toward met and it's time to start prepping for Moderate.

---

## 2. Tech-A — Instrumentation & Baseline

**Runs alongside:** Business Phase 0 (Foundation)
**Starts:** now
**Gate to start:** none — this is explicitly the first thing to build, per your own roadmap's checklist item #1.
**Gate to exit:** cost-per-task and latency data flowing for every agent call, queryable, before Phase 1's pilot begins.

### What gets built

1. **Per-call logging**, on every agent invocation regardless of role: provider, model, tokens in/out, wall-clock time, agent_key, role, tier/path, cost (computed from provider's real per-token pricing, not estimated). This hooks into wherever agent calls already funnel through today (the relay/emitter event stream) — you're not building a new call path, just attaching a logger to the existing one.
2. **A queryable store for it** — doesn't need to be fancy; a table keyed by task_id/agent_key/timestamp is enough at this stage. This becomes the dataset Tech-D's Brain prototype trains its judgment against later, and the dataset Business Phase 1's real cost-per-task validation (the whole point of the pilot, per your business roadmap) depends on.
3. **A basic query/report layer** — even a script that dumps "cost per task, p50/p95 latency per agent, per tier" is enough. This is the thing that replaces every placeholder dollar figure in the business roadmap's Part 7 earnings model with real numbers.

### Explicitly not in scope here

- Dashboards, admin panels, polish — those are Business Phase 2 deliverables once real billing exists. Tech-A is instrumentation for *your* decisions, not a user-facing feature.

### Why this is first, unconditionally

Every other technical decision downstream — which models actually belong in Basic's registry, whether decomposition-vs-consolidation testing (roadmap 3.3) shows what you expect, whether Brain's later judgment is actually better than Panel's — depends on this data existing. Building anything else first means building on guesses you'll have to redo.

---

## 3. Tech-B — Harden Basic for Real Users

**Runs alongside:** Business Phase 0 (late) through Phase 1 (Pilot) → Phase 2 (Launch)
**Starts:** once Tech-A is logging real data
**Gate to start:** Tech-A exit criteria met
**Gate to exit:** Business Phase 2's own exit criteria (Basic break-even on hosting+API from real revenue, demand-signal gate for Moderate being watched)

This phase is **deliberately not** about the Brain/EO-authoring ideas from our discussion — none of that belongs here. This is: take the system exactly as it exists today (SGA → Inspector → Panel → staff_task → executor, 74 agents, existing registry) and make it safe and correct to run against real paying users and real money. Scope matches what you said explicitly: security/multi-tenancy details are "later," so this list is deliberately narrow.

### What gets built

1. **Real multi-tenancy** — per-user isolation in the relational DB and vector memory store, identity + active tier carried through the full call chain (agents → memory bus → relay → billing meter). This was already correctly scoped as non-negotiable in your business roadmap's Part 4.1 — it belongs here, not later.
2. **Provider migration**: move the free-tier keys for Basic's five providers to paid accounts, at the counts your own roadmap flags as a working estimate to replace with real numbers — don't over-build the reserve/rotation logic for throughput reasons paid keys may no longer have; keep 2 keys per provider for failover, and only add more once Tech-A's real concurrency data says you need to.
3. **Billing plumbing** — Stripe metered billing, tier as a first-class field in the billing model from day one (per your business roadmap's Part 4.4), even though only one tier (Basic) is live. Building this multi-tier-aware from the start is cheap now and expensive to retrofit later — this is the one piece of "build for the future" that belongs in Tech-B rather than the deferred window, because billing schema changes touch real customer records once they exist, and that's much more painful to migrate later than a config file is.
4. **Usage/cost dashboard, admin panel, audit logging** — matches your business roadmap's Phase 2 technical work exactly; no changes needed to that plan.
5. **Decomposition-vs-consolidation empirical testing (business roadmap 3.3)**, run for the first time here against Basic's actual paid models, using Tech-A's cost/latency data as the scoring signal — this is where "test it, don't assume it" gets its first real evidence.

### What explicitly does NOT happen in Tech-B

- No parameterizing Panel's chains by tier.
- No extending the `hires` schema with `freedom_envelope`/`decisions_locked`.
- No Monitor v1.
- No tier filter added to `dynamic_chain.py`'s fallback candidate pool.

You chose to defer all of this to Tech-C, right before Moderate — worth restating explicitly here so it doesn't creep back in under "might as well, while I'm in this file anyway" pressure during Tech-B. Every hour spent generalizing code for a tier that doesn't exist yet is an hour not spent hardening the tier that's about to take real money.

---

## 4. Tech-C — Moderate Scaffolding (the deferred work, now due)

**Runs alongside:** end of Business Phase 2 (Basic live and stable) → start of Phase 3a
**Starts:** once Basic's operational load is manageable per Business Phase 3's own gate 1 (3.5) — this is the same gate, reused; scaffolding shouldn't start earlier than the business roadmap already says Moderate's *build* shouldn't start.
**Gate to exit:** the scaffolding is in place and tested against Basic's existing traffic with zero behavior change, before any Moderate-specific logic is turned on.

This is the work you explicitly chose to defer — now it's due, and it's due *before* Tech-D's Brain integration and Tech-E's Moderate build, because both of those depend on it existing.

### What gets built

1. **Parameterize `panel.py`'s member chains by tier.** Replace the hardcoded `MEMBER_B_CHAIN`/`MEMBER_C_CHAIN` constants with a `PANEL_CHAINS[tier]` lookup. Basic's tier continues resolving to exactly what it uses today — this must be a no-op for Basic traffic, verified by re-running Tech-A's cost/latency baselines against it before moving on.
2. **Extend the `hires` schema.** Add `decisions_locked` and `freedom_envelope` fields to the `{role, agent_key, brief}` shape `staff_task()` produces. Basic continues populating these as empty/full-freedom by default — again, no behavior change for existing traffic, just headroom for Moderate to populate them meaningfully.
3. **Add a tier filter to `dynamic_chain.py`'s candidate pool.** Fallback/shuffle logic stays same-tier only, per your own instinct that cross-tier shuffling doesn't make sense. This is a small, contained change to `_candidate_pool()`/`_rank_accounts()`.
4. **Monitor v1** — the narrow-scope version: a subscriber to the existing `relay/emitter.py` event stream that can flag (not yet repair) inter-layer contradictions, generalizing the pattern already present in `reviewer.py`/`security_aggregator`/`output_guard.py`. This ships as a passive observer first; its repair authority and its Brain-facing escalation path (Tech-F) come later, once you've seen what it actually flags in practice.
5. **Provider/model shortlist for Moderate's mid-tier candidates** — informed by real Basic-tier data from Tech-A/Tech-B, not guessed at in the business roadmap's Part 4.2 tables (which are explicitly marked as working estimates for this exact reason).

### Why this order, specifically

Every item above is a generalization of something that already exists in the current codebase — none of it is new invention, all of it is "take the hardcoded version and make it read from a tier parameter instead." That's exactly why deferring it cost you nothing: there was no design risk sitting in the deferred window, only sequencing risk, and doing it right before Moderate means you're generalizing against a system you now have months of real production behavior on, not a system you're still guessing about.

---

## 5. Tech-D — Brain Prototype (internal only)

**Runs alongside:** overlaps the tail of Business Phase 2, informed by my recommendation in §0
**Starts:** once Tech-A/Tech-B have produced a meaningful volume of real routing_memory outcomes to prototype against — not on a fixed calendar date, on data volume.
**Gate to exit:** Brain's proposed structures, scored against real historical tasks, match or beat what Panel/staff_task actually did on a meaningful sample — before any real user (even a Moderate beta user) ever sees Brain-authored output.

This is where the actual research work from our discussion happens — safely, because nothing here ships.

### What gets built

1. **The primitive set, formalized.** Not new code — a declarative catalog of the composable shapes that already exist: *classify* (Inspector's shape), *committee-vote* (Panel's shape, parameters: member count, lineage, synthesis rule), *staff-and-execute* (staff_task/executor, parameter: hire list source), *loop-gate* (loop_controller's shape, parameters: iteration count, redo scope), *validate/repair* (Monitor v1's shape). Writing this catalog down explicitly is itself real engineering work — it's the contract Brain's output has to conform to.
2. **The Brain's input menu**, wired but not yet live-called: `capabilities.list_capabilities()`, `structure.py`'s saved templates, `routing_memory.py`'s similar-outcome retrieval — same sources discussed earlier, assembled into whatever context format the Brain model will actually consume.
3. **The offline eval harness.** Take real (anonymized) historical tasks from routing_memory's logs. For each, have Brain propose a structure (which primitives, what parameters, what roles — including net-new role prompts via the existing `add_role_prompt` mechanism). Compare the outcome quality and cost/latency against what actually happened. This is a batch/offline process — no live traffic touches it.
4. **Template promotion logic, tested but not live**: the "provisional until proven" mechanism discussed earlier — a new structure only gets promoted into the shared template library after Monitor confirms a genuinely good outcome, not just "didn't crash." Build and test this logic against the offline harness now, so it's proven before Tech-E turns it on for real.

### Explicitly out of scope for Tech-D

- No executable-code authoring (that's Tech-H, and it's gated separately — see §8).
- No live user traffic, not even a small beta.
- No changes to Basic or Moderate's actual production behavior.

### Exit criteria, concretely

Define this in writing before starting, matching your own roadmap's discipline of defining "converting" for the end-2026 checkpoint before you're in the middle of deciding it: pick a real threshold (e.g., "Brain's proposed structure matches or beats Panel's actual historical choice on cost-adjusted outcome quality for ≥ X% of a representative sample, across at least N task types") before you start scoring, so you're not tempted to declare victory on a good-looking run.

---

## 6. Tech-E — Brain Integration into Moderate

**Runs alongside:** Business Phase 3a (Moderate build)
**Starts:** both Business Phase 3a's own gates clear (3.5 operational capacity, 3.6 demand signal) **and** Tech-D's exit criteria are met — this phase does not start on either condition alone.
**Gate to exit:** matches Business Phase 3a's own exit criteria (Moderate live, priced, self-sustaining or accretive).

### What gets built

1. **Brain goes live, gated by mode + package** — only for expert/beast modes, only for Moderate/Ultimate package tiers, exactly as discussed: mode controls whether Brain engages at all, package controls how good the model behind it is. Fast/auto traffic never touches any of this, on either tier — zero latency risk to the paths that need to stay fast.
2. **Ordering**: Inspector always runs first, honestly, uncorrupted — its output feeds Brain, Brain never feeds back into it. Brain runs between Inspector and Panel, consuming Inspector's classification plus the Tech-D input menu, producing a process plan instead of Panel automatically running its default committee vote.
3. **Standing defaults, persisted**: Brain's own "which primitives always run for this task shape" decisions get written to the same store as structure templates, so repeat-shape tasks reuse a proven default instead of re-reasoning every time — the cascade-caching discipline extended one layer up.
4. **The privilege boundary, enforced in code, not policy**: Brain can invent new roles and new prompts via the existing `add_role_prompt` mechanism; it cannot grant any agent access beyond what `quota_sentinel.py`/`injection_guard.py`/`redaction_guard.py`/`output_guard.py` already allow, regardless of what it decides. This needs to be structurally impossible for Brain to route around, not just a convention Brain is instructed to follow.
5. **Frontend/architecture privacy, audited explicitly**: confirm `relay/emitter.py`'s event stream — now carrying Brain's structural reasoning and Panel votes, not just task progress — never leaks into whatever channel the frontend actually consumes. This is a deliberate audit pass here, not an assumption carried over from Tech-B.

---

## 7. Tech-F — Monitor v2 (closed-loop, stream-based)

**Runs alongside:** Business Phase 3a, shortly after Tech-E goes live — once there's real Brain-authored traffic for Monitor to actually watch.
**Gate to start:** Tech-E live with real (even if low-volume) Moderate traffic.
**Gate to exit:** Monitor demonstrably catches at least one class of real inter-layer problem in production that Monitor v1 (passive, Tech-C) would only have flagged after the fact.

### What gets built

1. **Per-step subscription**, not per-pass: Monitor becomes a live subscriber to `relay/emitter.py`'s stage-completion events (not just `loop_controller`'s end-of-pass gatekeeper check), so it can act while a task is still running, not only after it finishes.
2. **Three-way authority, exactly as scoped in our discussion**: ignore / self-repair (small stuff — a bad brief, a missing parameter) / interrupt-and-hand-to-Brain (anything structural). The self-repair boundary should start narrow — parameter-level fixes only — and only widen (e.g., to "skip a primitive Brain specified") once you've watched it operate for a while and trust its judgment on that specific call. Don't grant the wider authority on day one.
3. **`loop_controller`'s gatekeeper extended**: its existing stop/redo-all/redo-specific decision gets a fourth option — hand back to Brain for a genuine replan, not just a mechanical redo of the same plan.

---

## 8. Tech-G — Ultimate's Brain Tier

**Runs alongside:** Business Phase 3b (Ultimate)
**Gate to start:** matches Business Phase 3b's own gates (same 3.5/3.6 discipline, one tier up) — no separate technical gate needed, since Tech-E/F will already have proven the mechanism at Moderate's scale.

### What gets built

Structurally, nothing new — this is Tech-E/F's mechanism, with Ultimate's package tier resolving to a frontier-model Brain instead of a mid-tier one, per the `PANEL_CHAINS`/tier-parameterization work done back in Tech-C. The engineering lift here should be genuinely small if Tech-C through Tech-F were built correctly — that's the entire point of parameterizing by tier instead of forking. If Ultimate's build turns out to require real new engineering beyond a config/model swap, that's a signal something in Tech-C's generalization wasn't actually general — worth treating as a finding, not just pushing through.

---

## 9. Tech-H — Executable Code-Authoring (gated, no fixed date)

**Runs alongside:** nothing in particular — this is explicitly not calendar-anchored, matching how your business roadmap treats the daemon (Part 4.5): a later, deliberately deferred, separately-audited project, mentioned here so it's not forgotten, not scheduled.

**Gate to start:** Tech-E/F have been running in production long enough that Brain's *declarative* composition (structure, roles, prompts — no new code) is demonstrably trustworthy at Moderate and/or Ultimate scale. Starting Tech-H before that evidence exists means testing your riskiest mechanism before your second-riskiest one is even proven.

### What gets built, when this phase actually starts

1. **Sandbox execution environment**: brain-generated code runs against fully mocked externals — not just a fake message bus, but no real credentials reachable from that execution context at all, so even a malicious or badly-misaligned generation cannot reach a real system regardless of intent.
2. **Automated first-pass filtering**: route every generation through the CI security scan you already have (Gitleaks + Semgrep) before any human ever looks at it.
3. **Hard usage ceilings, scoped per generation attempt**: a max-token cap and a max-attempt cap on the same generation, not just a running aggregate budget — so one runaway loop can't quietly spend the whole ceiling before it trips.
4. **Mandatory human review, permanently — not a phase you graduate out of.** Every new executable integration that requests real external access gets manual sign-off before it's ever wired to real credentials, indefinitely. This is the one place in the whole system where "the model is good enough now" is never sufficient on its own — the risk being guarded against is intent/design failure, which sandbox testing catches for bugs but not reliably for subtler misalignment.
5. **Permanent-primitive promotion, decided explicitly**: once a piece of brain-generated code passes sandbox + CI scan + human review, decide in writing whether it becomes a permanently trusted primitive (reusable autonomously afterward, like `calendar_agent.py` is today) or requires review on every individual use. Recommendation stands from our discussion: review the code once, trust the primitive after — but write this decision down before Tech-H starts, not while under pressure to ship a specific integration.

---

## 10. Master Technical Timeline

| Tech Phase | Business Phase alongside | Starts when | Exit gate |
|---|---|---|---|
| A — Instrumentation & baseline | Phase 0 | Now | Cost/latency data flowing for every agent call |
| B — Harden Basic for real users | Phase 0 (late) → 1 → 2 | Tech-A exit | Business Phase 2's own exit criteria |
| *(deferred window — no new tech work)* | Phase 2, live | — | — |
| C — Moderate scaffolding | End of Phase 2 → start of 3a | Business gate 3.5 clears | Scaffolding live, zero behavior change to Basic |
| D — Brain prototype (internal only) | Tail of Phase 2 | Meaningful routing_memory data volume exists | Brain beats/matches Panel on offline historical eval |
| E — Brain integration into Moderate | Phase 3a | Business gates 3.5 & 3.6 clear AND Tech-D exit met | Business Phase 3a's own exit criteria |
| F — Monitor v2 (closed-loop) | Phase 3a, shortly after E | Tech-E live with real traffic | Monitor catches a real problem live that v1 would've missed |
| G — Ultimate's Brain tier | Phase 3b | Business Phase 3b gates clear | Config/model-swap only, if C-F were built correctly |
| H — Code-authoring | Unscheduled | Tech-E/F proven trustworthy in production | Never fully autonomous — permanent human gate on new external access |

---

## 11. What this roadmap deliberately does not include

Matching your business roadmap's own discipline of naming what's out of scope, not just what's in:

- Security/compliance hardening beyond what's needed for Tech-B's real-user launch (explicitly deferred, per your own instruction at the start of this discussion).
- The daemon (already separately deferred in the business roadmap, Part 4.5 — unaffected by anything here).
- Any executable-code authoring before Tech-H's gate clears — including "just a small one" as a shortcut during Tech-D or Tech-E. If this temptation shows up mid-build, it's a sign the gate is being second-guessed under pressure, not a sign the gate was wrong.
- Any scaffolding work during Tech-B (the deferred window you chose) — restated here as a hard boundary, not just a scheduling note.
