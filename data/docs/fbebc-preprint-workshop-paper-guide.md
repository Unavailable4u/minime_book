# FBEBC Preprint / Workshop Paper Guide

**A standalone writing and submission guide for Stage 1's output**

This covers turning Stage 1's build (from `fbebc-research-program-guide.md`) into an arXiv preprint and, if timing and results allow, a workshop submission. It assumes Stage 1's experiment is done or nearly done — this is about writing it up correctly and honestly, not about building anything further.

---

## 1. Target venues, and how to hold them

| Venue | Role | Bar | Notes |
|---|---|---|---|
| **arXiv** | Primary, non-negotiable target | No peer review | Establishes priority, gets you a citable link, zero timeline risk. Do this regardless of everything else. |
| **ICLR 2026 Workshop on AI with Recursive Self-Improvement** | Stretch submission | Workshop-level | Direct topical fit — self-modifying agents, governance, evaluation is exactly their scope. **Verify the current CFP and deadline before planning around it** — workshop dates and even existence for a given year can shift; check openreview.net or the ICLR site directly. |
| **GI@ICSE (Genetic Improvement workshop)** | Stretch submission | Workshop-level | LLM-driven evolutionary code optimization is their whole focus — a strong topical match. Same caveat: verify the current year's CFP and deadline. |
| GECCO / PPSN | Later target, not now | Full conference | Save for the Stage 2 (MiniMe-integrated) paper, which will have a stronger empirical story. |
| Main-track NeurIPS/ICML/ICLR, Q1 journals (JAIR, AIJ) | Later, second paper | High | Realistic once you have Stage 2's production results behind you, not for this first pass. |

**Hold these loosely.** A workshop's CFP deadline might not align with your 4-week Stage 1 timeline — that's fine. The arXiv preprint is the deliverable that matters regardless of any workshop deadline; treat a workshop submission as a bonus if the timing lines up, not a requirement that should stretch Stage 1's cap.

---

## 2. Paper skeleton and page budget

Most ML/AI workshops use an 4–8 page limit excluding references, in a NeurIPS- or ICLR-style two-column format (verify against the actual CFP once you pick a target — page limits and templates vary and change year to year). Structure for that budget:

| Section | Approx. length | Purpose |
|---|---|---|
| Title + Abstract | — | One-sentence hook + what you built + what you found |
| 1. Introduction | 0.75–1 page | Motivate the problem, state contributions as a list |
| 2. Related Work | 1–1.5 pages | Position against the literature you already have citations for |
| 3. Method (FBEBC) | 1.5–2 pages | The architecture, condensed |
| 4. Safety Analysis | 0.5–1 page | The invariants, the barrier, what you tested |
| 5. Experimental Setup | 0.5 page | Task, model, budget — full honesty here |
| 6. Results | 1–1.5 pages | Figures/tables, the ablation |
| 7. Limitations | 0.5 page | Explicit, not buried |
| 8. Conclusion & Future Work | 0.25 page | Point at Stage 2 as concrete future work |
| Appendix (uncounted) | as needed | Full ADV case table, hyperparameters, prompts |

---

## 3. Section-by-section writing guide

### 3.1 Title

Aim for a title that names the mechanism, not just the domain. Candidates:

- *"Fairness-Bounded Elite-Band Cloning: A Structurally Immutable Governance Layer for LLM-Driven Program Synthesis"*
- *"Score Non-Authorship as a Design Principle for Self-Modifying Code Agents"* (if you want to foreground the reward-hacking angle specifically)

Pick the one that matches your strongest result — if the ablation (elite-band vs. single-winner) is your best evidence, lead with that; if the barrier-integrity result is strongest, lead with the governance framing.

### 3.2 Abstract

A tight template (150–200 words):

1. One sentence: the problem (LLM-driven evolutionary code search lacks a structurally enforced trust boundary between the untrusted generator and the evaluation harness).
2. One sentence: what you built (FBEBC — name the 2–3 core mechanisms: Σ-Δ separation, score non-authorship, elite-band selection).
3. One sentence: what you tested it on and how (circle packing, N generations, M seeds — be specific with numbers).
4. One or two sentences: what you found (barrier held across N evaluations; elite-band selection outperformed single-winner selection by X; be honest if a result is modest).
5. One sentence: what's explicitly out of scope (no latency/timing claims — say this plainly, don't let a reader discover it only in Limitations).

### 3.3 Introduction

Standard shape: problem → gap in existing work → your contribution → roadmap of the paper. Concretely:

- **Open with the non-stationary search problem**: LLM-driven code evolution (FunSearch, AlphaEvolve, DGM) has produced real results, but the governance question — what stops the untrusted proposer from corrupting its own evaluation — is either unaddressed or explicitly flagged as future work (cite DGM's own admission here, since it's a strong, honest data point in your favor).
- **State your contribution as a numbered list.** Reviewers scan for this. Something like:
  1. A six-gate admission pipeline with byte-identity post-conditions on immutable code regions.
  2. A score-non-authorship scoring architecture where the candidate never has write access to its own fitness value.
  3. A frozen, pre-registered edit-distance metric, decoupling the fairness measure from the threshold decision.
  4. An empirical comparison of elite-band vs. single-winner selection under evaluation noise on a controlled benchmark task.
- **Say explicitly what this paper does not claim**: no latency-fairness result, no large-scale adversarial red-team, single benchmark task, small compute budget. Do this in the introduction, not just in limitations — reviewers respect papers that scope themselves honestly up front.

### 3.4 Related Work

You already have the citation master list from earlier — use it directly, organized into the same four clusters:

1. **Optimization/step-bounding** (TRPO, PPO, CMA-ES) — contrast: their bounds are for policy stability, yours are for comparison fairness.
2. **Population-based selection** (PBT, MAP-Elites, AlphaGo Zero) — contrast: elite-band selection vs. truncation/niche-archival/single-winner.
3. **Theoretical self-modification & governance** (Gödel Machines, Tiling Agents, Corrigibility, Concrete Problems in AI Safety) — this is your strongest differentiation section; ground the Σ-Δ barrier and score non-authorship explicitly in these.
4. **SOTA LLM code-agent taxonomy** (FunSearch, AlphaEvolve, DGM, OpenEvolve, CodeEvolve, ShinkaEvolve, AdaEvolve) — position FBEBC as addressing a governance gap this taxonomy leaves open, using DGM's own admitted unmodifiable-governance future-work flag as your strongest single piece of evidence that the gap is real and acknowledged by the field itself.

**Copyright discipline while writing this section:** paraphrase every described mechanism in your own words. Don't quote paper abstracts or lift phrasing — describe what each system does structurally, in your own sentences. A comparison table (mechanism vs. mechanism) is fine and expected; verbatim text from the papers is not.

**Verify your citation details before submission** — check the exact publication venue, year, and any headline figures you cite (e.g., DGM's reported failure rate) against the primary source. A wrong figure in a related-work table is the kind of small error that undermines otherwise solid work.

### 3.5 Method

Condense the Phase 1 guide's architecture into the space you have. Prioritize, in order:

1. The Σ-Δ separation and why it's structurally, not conventionally, enforced (one paragraph + a simplified version of the trust-zone diagram from the Phase 1 guide).
2. The six-gate admission pipeline (a table: gate name, what it checks, cost — this compresses well).
3. The frozen edit-distance metric and why it's defined before any threshold is set (this is a specific, citable methodological choice worth a full paragraph — it's the kind of thing a careful reviewer notices and rewards).
4. Elite-band selection, contrasted directly with AlphaGo Zero's single-winner rule.

Push implementation-level detail (exact regex patterns, full code listings) to the appendix. The body should read as "here is the architecture and why each piece is there," not "here is the codebase."

### 3.6 Safety Analysis

This is where you state, precisely, what "0% barrier violation" means for *your* scaled-down suite — don't inherit the full Phase 1 guide's language wholesale, since you ran 8–10 cases, not 24, and no live red-team. Be exact:

> "We evaluate against an 8-case adversarial suite covering boundary-integrity attacks (Tier A: marker forgery, contract violation) and score-non-authorship attacks (Tier C: direct score injection, timer manipulation). All 8 cases were blocked as expected across N evaluation runs. We did not conduct a live adversarial red-team campaign or evaluate sandbox-escape resistance at the scale a production deployment would require; see Limitations."

State your five invariants (I1–I5 from the Phase 1 guide) briefly, and note which ones you actually tested (I1 fixity, I2 dualism, I3 score non-authorship are directly testable at this scale; I5 interruptibility is easy to include cheaply — do it if you have a spare afternoon, it's a strong, cheap addition).

### 3.7 Experimental Setup

Full honesty here is what makes the paper credible rather than embarrassing under scrutiny:

- **Exact model identifier and date used** for Σ (e.g., "gemini-2.5-flash-lite, accessed via the Google AI Studio free tier, September–October 2026" — API models get silently updated, so pinning the date is a real reproducibility signal).
- **Population size, generation count, seed count** — the exact numbers from your run, not rounded.
- **Compute environment**: Docker on a personal machine, explicitly not gVisor/bare-metal, explicitly no timing measurement.
- **Task definition**: circle packing, n=26, referencing AlphaEvolve as the source of this benchmark choice.
- **Total API calls and approximate cost** ($0, free tier — say so plainly; it's a legitimate and interesting fact about accessibility of this kind of research, not something to hide).

### 3.8 Results

What to actually produce:

1. **Fitness-over-generations curve** — best-in-population fitness per generation, for each seed (small multiples or overlaid lines with a mean). This is your core "the mechanism works" evidence.
2. **Rejection taxonomy breakdown** — a bar chart or table of how many candidates were rejected at each gate (`E_BOUNDARY_VIOLATION`, `E_CONTRACT_VIOLATION`, etc.). This is free, interesting data you already logged, and it's the kind of result nobody else in this exact form has published, since most systems in your related work don't report a typed rejection taxonomy at all.
3. **Elite-band vs. single-winner ablation** — final fitness distribution under each selection rule, same budget, same seeds. Report this with appropriate humility if the effect is small or noisy given your sample size (see §6 on statistical honesty).
4. **Barrier integrity table** — the 8/8 (or however many) adversarial cases, pass/fail, one row each.

### 3.9 Limitations

Write this as a real, itemized list, not a hedge paragraph:

- No latency or timing-fairness evaluation; all fitness is correctness-only.
- Single benchmark task; generalization to other domains untested.
- Small compute budget (state the exact call count) limits statistical power, especially for the ablation.
- Reduced adversarial suite (8–10 cases, one tier of severity); no live red-team campaign.
- Docker-based isolation, not gVisor/hardware-virtualized; the security boundary is weaker than a production deployment would require.
- Single free-tier model as Σ; results may not generalize to stronger or differently-trained models.

This list is a feature, not a weakness, when it's this explicit — it tells reviewers you understand exactly what you have and haven't shown.

### 3.10 Future Work

Point directly at Stage 2 as concrete, already-planned future work: applying the mechanism to a real production multi-agent system's configuration, using real deployment evals as the fitness oracle, and reintroducing cost/latency as a fitness dimension where it has real operational meaning. This is a genuinely strong forward pointer because it's not speculative — you have an actual real system and plan lined up, which is unusual and a plus.

### 3.11 Reproducibility statement

Most workshops now expect one. State: full code released at [your repo URL], exact seeds logged, exact model version/date logged, free-tier nature of the LLM access noted (meaning exact reproduction depends on the provider not having changed the model behind that identifier — flag this honestly as a limitation of reproducibility in this specific line of research, not just your paper).

---

## 4. Formatting and submission logistics

### 4.1 Template

Use the standard NeurIPS or ICLR LaTeX style — most ML workshops accept or require one of these regardless of the specific venue, and Overleaf has both pre-loaded as templates. Check the actual target workshop's CFP for which one it wants.

### 4.2 arXiv category

Primary category: **cs.NE** (Neural and Evolutionary Computing) — this is the most accurate fit for an evolutionary-search-plus-governance paper. Cross-list:
- **cs.AI** (general AI) — broadens discoverability
- **cs.SE** (Software Engineering) — relevant given the code-synthesis framing
- **cs.CR** (Cryptography and Security) — relevant given the barrier/adversarial-robustness content

### 4.3 The endorsement issue

arXiv requires an **endorsement** for first-time submitters in most categories, including cs.NE. This trips people up if they don't plan for it. Your options, in order of ease:

1. **Ask your advisor** (the one you're already planning to talk to about MiniMe) if they have an arXiv author history in a relevant category — if so, they can endorse you directly.
2. **Ask any professor or published researcher** you know in CS/AI — endorsement just requires the endorser to have their own qualifying submission history in that category.
3. Check arXiv's current endorsement process at arxiv.org/help/endorsement — requirements and the exact mechanism can change, so verify before you're blocked by it at submission time, not after.

Start this conversation early — during Week 3 or 4 of Stage 1, not the day you try to submit.

### 4.4 Timeline fit

Writing fits inside Stage 1's existing Week 4 (see the research program guide's §1.4). If a workshop deadline doesn't align with that timeline, submit to arXiv on schedule and treat the workshop as an optional later submission of the same or a lightly revised paper — don't let an external deadline pull you into extending Stage 1's cap.

---

## 5. Statistical honesty (read this before writing Results)

With 3 seeds and a single task, you cannot make strong statistical claims, and trying to will hurt the paper's credibility more than a modest, honest claim would. Concretely:

- **Report ranges or individual seed results, not just a mean**, when N is this small. "Final fitness across 3 seeds: 2.14, 2.09, 2.21" is more honest and more useful to a reader than "mean fitness 2.15 ± 0.05" dressed up to look like it has more statistical weight than 3 points support.
- **Don't compute a p-value on 3 seeds and present it as significance.** If you want a formal comparison for the ablation, a simple non-parametric approach (e.g., stating "elite-band selection produced a higher final fitness in 3 of 3 seeds") is more honest than a t-test that assumes more than your sample supports.
- **Frame the ablation as suggestive, not conclusive**, if that's what your sample size actually supports: "these results are directionally consistent with elite-band selection reducing sensitivity to evaluation noise, though the sample size (3 seeds) does not support a strong statistical claim" is a sentence reviewers respect.
- **Never round toward a nicer-looking number.** If your improvement over generations is modest, report the modest number. A modest, well-governed result is a legitimate contribution; an inflated one invites the exact scrutiny that sinks papers at review.

---

## 6. Pre-submission checklist

- [ ] Every claim in the abstract is backed by a specific number or figure in the body
- [ ] Limitations section is explicit and itemized, not a single hedging sentence
- [ ] Every citation's venue/year/headline figure has been checked against the primary source
- [ ] No quoted text longer than a short phrase from any cited paper; everything is paraphrased
- [ ] Exact model identifiers and access dates are stated for every LLM used (Σ and judge, if applicable)
- [ ] Code repository is public, cleaned, and linked, with seeds and exact run configs included
- [ ] arXiv category chosen, endorsement secured or in progress
- [ ] Figures are legible at print size, with axis labels and units
- [ ] The one required ablation (elite-band vs. single-winner) is reported, even if the result is modest
- [ ] A reader who only reads the abstract and limitations would come away with an accurate picture of what was and wasn't shown
