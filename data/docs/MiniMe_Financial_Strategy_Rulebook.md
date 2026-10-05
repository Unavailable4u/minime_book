# MINIME AI — FINANCIAL & MODEL STRATEGY RULEBOOK

**Version 1.1 · Price snapshot: 2026-09-19 · Funding, legal and market research: 2026-09-20 · Next mandatory re-verification: 2026-12-15**
**Owner:** Founder · **Status:** Operating rulebook and financial constitution — the one document to consult before any money, model, hiring, funding or equity decision. Supersedes *"MiniMe AI: Master Strategic Financial & Commercial Enterprise Blueprint (2026–2029)"* wherever the two disagree.

> This is a rulebook, not a forecast. Every rule answers one question: *"I am at point X — what do I do?"*
> Every number carries a confidence label (Part 0.3). When a label says **[V]**, it was read from a provider's pricing page or a dated source on the snapshot date. When it says **[A]**, it is my planning assumption and must be replaced by measured data from Tech-A instrumentation as soon as that data exists.

---

# TABLE OF CONTENTS

**Book 1 — Models, prices and plans**
0. How to use this book
1. The 15 Golden Rules
2. Fixed facts, assumptions and dated time-bombs
3. Provider strategy (who we buy from, and who we stop using)
4. Price sheet (single source of truth for every price)
5. Model roster: which model runs where, per sector and per tier
6. Escalation, downgrade, failover and model-change rules
7. Plans, prices, token limits, Free tier, top-ups
8. Unit economics (per task, per user, per plan)
9. 36-month financial model, scenarios, and the OpEx governor
10. Infrastructure cost stages and gates

**Book 2 — Capital, funding, equity, profit and fallbacks**
11. Capital plan by stage: how much money, when, and exactly where it goes
12. Funding sources and strategy
13. Equity, dilution, valuation and net worth
14. Profit, reserves and distribution policy (when you may take money out)
15. Financial statements by stage
16. Pathways and fallback trees
17. Team, hiring, compensation and office
18. The FBEBC research program
19. Lessons from other startups: hardships and solutions

**Book 3 — Operating the plan**
20. Governance: dashboards, thresholds, fix ladder, rituals
21. Risk register
22. Open items (close before the decision they gate)
23. Corrections to the old blueprint, and change log
- Appendix A: How to recompute · Appendix B: Sources · Appendix C: Glossary

---

# 0. HOW TO USE THIS BOOK

## 0.1 Precedence
1. This rulebook overrides the old financial blueprint, the landing page's placeholder numbers, and the token limits in `minime_roadmap.md` Part 4.3.
2. The landing page must be edited to match Part 7 (list of required edits in 7.8). Never the other way round.
3. The technical roadmap (Tech-A … Tech-H) and the business roadmap (Phase 0 … 3b) still govern **sequence**. This book governs **money, models, funding, equity and hiring** inside that sequence.
4. Where the old financial blueprint, the business roadmap and this book disagree on a number, **this book wins**; the list of corrections is Part 23.1.

## 0.2 The clock used in this book
Money projections use a **launch clock**: **M1 = the first month the public Free tier and the paid Basic tier are both live.** Calendar dates are not used because your roadmap makes launch demand-gated (Basic launch follows the pilot; expected mid-to-late 2027 or later). Pre-launch stages **S0** (foundation) and **S1** (pilot and launch prep) sit before M1 (Part 11.1). If launch slips, every date in this book slips with it; no number changes.

## 0.3 Confidence labels
| Label | Meaning | What to do |
|---|---|---|
| **[V]** | Verified list price or fact on 2026-09-19 from a provider page or dated source | Re-verify at next quarterly check |
| **[A]** | Assumption (mix, utilization, tokens per task, share of local payers…) | Replace with measured data from Tech-A |
| **[U]** | Unverified or conflicting sources | Resolve before it drives a decision (Part 22) |

## 0.4 Update protocol (how to change this book safely)
Whenever a price, model or limit changes, do exactly this, in order:
1. Edit **Part 4** (price sheet) first. Nothing else contains a "source" price.
2. Re-run `minime_pricing_model.py` (Appendix A). It regenerates class costs, unit economics, P&L and cash.
3. Check the four **gates**: (a) COGS at cap ≤ 45% of the lowest net price per plan; (b) typical gross margin ≥ 70%; (c) Brain pool cost within budget; (d) Free budget within Part 7.4 limits. If any gate fails, apply the fix ladder in Part 20.3 **before** shipping anything.
4. Update Part 5 (roster) and Part 7 (plans) only if a gate changed.
5. Add a line to the change log (Part 23.2) with date, what changed, why.

## 0.5 Situation index — "I am at X, go to Y"
| Situation | Go to |
|---|---|
| A provider announced a price change or a promo is ending | 2.3 → 4 → Appendix A |
| Which model should agent/role R use on tier T? | 5.2 |
| An agent keeps failing or output quality is poor | 6.1 (escalation ladder) |
| Task needs coding / long context / vision / image / audio | 6.2 |
| Brain vendor is down, blocked or rate-limited | 6.5 |
| A user has used up a token pool | 6.4, 7.3 |
| Free-tier spend is rising | 7.4 |
| Thinking of adding or replacing a model | 6.7 |
| Thinking of changing a price or a limit | 7.7 |
| Thinking of hiring or spending money | 9.6 (OpEx governor) |
| Server is slow; should I move to the next infra stage? | 10.2 (gates) |
| A margin alarm fired | 20.3 |
| Something looks wrong in the old blueprint | 23.1 |
| How much money does the next stage need, and what is it spent on? | 11.4, 11.5 |
| Where can money come from? How many applications should I send? | 12 |
| Should I sell equity? At what price and terms? | 13.2 |
| When can I pay myself or take profit out? | 14.3, 14.4, 14.8 |
| A funding or other plan failed — what next? | 16 |
| Should I hire, rent or buy an office? | 17 |
| FBEBC research: cost, gates, funding | 18 |
| I am facing a hardship other startups faced | 19.3 |

---

# 1. THE 15 GOLDEN RULES

These are non-negotiable. If a proposal breaks one, the proposal changes, not the rule.

1. **No free-tier keys in production.** Free tiers of Google, Groq, HuggingFace and OpenRouter are for development and evals only. Google's free tier uses your content to improve its products; your landing page promises private-by-default. Production traffic runs on paid, first-party accounts. **[V]**
2. **Never one vendor on a critical path.** Every role has a primary and at least one cross-vendor fallback. The Brain has a hot standby at a different vendor. Precedent: Anthropic suspended Fable 5 and Mythos 5 for 19 days (June 12 – July 1, 2026) under U.S. export controls. **[V]**
3. **Pin model versions. Never route to a `-latest` alias.** Aliases silently change quality and price. Mistral's current lineup lists Medium 3.5 at $1.50/$7.50 while Large 3 costs $0.50/$1.50 — an alias can move you to a 3–5× costlier model without any code change. **[V]**
4. **Meter dollars, not just tokens.** Every LLM call logs provider, model, tokens in/out/cached and computed dollars. No dollar log, no launch (Tech-A exit gate).
5. **COGS-at-cap ≤ 45% of the lowest net price of each paid plan.** "Cap" means the user uses every pool 100%. This is the rule that protects you from the worst customer.
6. **Frontier tokens live in their own pool.** Brain and Expert tokens are metered separately from Standard tokens. A user can never spend frontier money by using Standard-priced quota.
7. **Degrade gracefully; never hard-stop.** When a pool runs out, the task continues on cheaper models with a visible notice and an upsell (top-up or upgrade). The user is never simply blocked mid-task.
8. **Free is a budget, not a promise.** The Free tier has a monthly dollar ceiling (7.4). When the ceiling is hit, per-user allowance shrinks automatically; it does not overspend.
9. **Infrastructure follows users, not the calendar.** Move to the next infra stage only when a gate in 10.2 fires.
10. **OpEx follows gross profit.** Monthly OpEx ≤ max($150, 70% of last month's gross profit) until cash is comfortably positive (9.6). Founders are equity-only until the ladder allows pay.
11. **Re-verify prices quarterly and before every pricing decision.** Prices in this industry moved several times in the last 90 days (DeepSeek repriced three times in Aug–Sep 2026; OpenAI cut Luna to $0.20/$1.20 on Jul 30; Gemini Flash prices double on Jan 1, 2027). **[V]**
12. **Every model is optional except the fallback.** The system must still produce a useful (lower-quality) answer if Brain, Expert models and Advanced models are all unavailable.
13. **Cheapest sufficient model wins, decided by evals, not by taste.** A model earns a slot by passing the role's eval set at the lowest cost; a more expensive one earns escalation only by beating it on the failures.
14. **Fund with non-dilutive money first; sell equity late, small, and priced on proof.** Prizes, grants, credits and revenue come before any equity; equity follows the ten tests in Part 13.2. Equity sold early is sold at its lowest price and can never be resold at the later one.
15. **Reserve before you distribute; earn before you hire.** No founder distribution until the operating reserve target is met (14.2, 14.4); every hire is approved by the OpEx governor (9.6) and a measured strain (17.3); a fallback exists for every plan (Part 16).

---

# 2. FIXED FACTS, ASSUMPTIONS AND DATED TIME-BOMBS

## 2.1 Constants used by every calculation
| Constant | Value | Label | Note |
|---|---|---|---|
| FX planning rate | **123 BDT / USD** | **[V]** | Market ≈ 123.0 (52-wk range 120.94–123.34). Old blueprint used 120. |
| FX stress rate | 135 BDT / USD | **[A]** | Roughly +10% depreciation |
| Input / output token split, workers | 70% / 30% | **[A]** | Reasoning tokens bill as output, so more output than old 80/20 |
| Input / output split, Brain | 85% / 15% | **[A]** | Brain reads much, writes short plans |
| Brain cache-read share of input | 50% | **[A]** | Needs a stable prompt prefix (6.3) |
| Typical plan-pool utilization | 55% | **[A]** | Replace with measured median |
| Free-tier monthly active share (MAFU) | 25% of registered | **[A]** | |
| Local (BDT) share of paying users | 65% | **[A]** | bKash leads with 70M+ users; MFS is >60% of online payments in Bangladesh **[V]** |
| Annual-plan discount factor on revenue | 0.97 | **[A]** | Annual = 10× monthly price |

## 2.2 Payment-fee planning rates (replace with contracted rates)
| Rail | Planning fee | Label | Evidence |
|---|---|---|---|
| bKash / Nagad / Rocket via aggregator | 2.5% blended | **[A]** | Nagad publishes 1.30% for merchants; SSLCommerz lists 2–4% for internet/mobile banking and 2.5% for Visa/Mastercard; old blueprint used 1.2–1.8% **[V]** |
| Local cards | 2.5% | **[V]** | SSLCommerz card rate |
| International card / PayPal-type | 4.5% + $0.30 | **[A]** | PayPal-type base ≈ 2.9% + $0.30 plus ≈ 2% cross-border **[V]** |
| One-time gateway setup | ≈ BDT 15,000 (SSLCommerz) | **[V]** | Older source; confirm |

## 2.3 Dated time-bombs (check this table every month)
| Date | Event | Effect | Action |
|---|---|---|---|
| **2026-10-02** | Gemini 2.5 Flash Image shutdown (per Google's pricing page) | Image module must use Gemini 3.1 image models | Use only 3.1 Flash-Lite Image / 3.1 Flash Image **[U: reconfirm date]** |
| **≥ 2026-11-21** | GPT-5.6 Sol promo price ($4/$20) may end; list is $5/$30 | Expert-class cost rises up to 50% | Budget at list price **[V]** |
| **2026-12-31** | Gemini 3.6/3.7/3.8 Flash intro price ($0.75/$3.75) ends | **Doubles to $1.50/$7.50 on 2027-01-01** | All 2027 budgets use the doubled price **[V]** |
| Any time | DeepSeek peak/off-peak pricing shifts | Only if DeepSeek is adopted (it is deferred, 3.2) | — |
| Any time | Fable/Mythos-class access restrictions | Brain outage | 6.5 |
| Any time | Groq model deprecations (llama-3.1-8b-instant and llama-3.3-70b-versatile ended 08/16/26) | Dead entries in `QUOTA_CONFIG` | Delete them now **[V]** |

## 2.4 Token-per-task assumptions (all **[A]** — the single most important numbers to measure)
| Task | Tokens | Where they go |
|---|---|---|
| Chat turn (SGA only) | 8,000 | Standard |
| Research run | 60,000 | Standard |
| Notebook generation (quiz, flashcards, study guide) | 40,000 | Standard |
| Balanced build run (Tier-2 pipeline) | 250,000 | Standard; 20% moves to Advanced if escalated |
| Deep run with Brain | 300,000 | 170k Standard + 100k Advanced + 30k Brain |

Tech-A must replace these with medians and 90th percentiles per task type. Until then, all capacity statements in Part 7 are approximate.

---

# 3. PROVIDER STRATEGY

## 3.1 The production stack (who we buy from)
| Role | Primary | Cross-vendor fallback | Last resort | Account type |
|---|---|---|---|---|
| **Standard workers** (Class S) | Groq (gpt-oss-120b, gpt-oss-20b) | OpenAI (GPT-5.6 Luna) | Google (3.1 Flash-Lite) → Mistral (Large 3) | Paid, first-party |
| **Advanced workers** (Class A) | Anthropic (Sonnet 5) + Google (Gemini Flash) | OpenAI (GPT-5.6 Terra) | Mistral (Large 3), Anthropic (Haiku 4.5) | Paid, first-party |
| **Expert** (Class E, Ultimate only) | Anthropic (Opus 5) | Google (Gemini 3.1 Pro) | OpenAI (Sol / Terra) | Paid, first-party |
| **Brain** | Anthropic (**Fable 5.1**) | OpenAI (**GPT-6 Astra**) | Anthropic Opus 5, then Panel-only path (6.5) | Paid, first-party |
| **Code specialists** | Mistral (Devstral 2 / Codestral) at Basic; Sonnet 5 / Gemini Flash / Terra at Moderate+ | Luna | Sonnet 5 | Paid |
| **Long-context / vision / PDF** | Google (3.1 Flash-Lite → Flash → 3.1 Pro) | OpenAI | — | Paid |
| **Image generation** | Google image models (3.1 Flash-Lite Image → 3.1 Flash Image → 3 Pro Image) | Degrade to text/SVG/Mermaid diagram | — | Paid |
| **TTS** | Azure neural voices (same voices `edge-tts` uses) | Gemini 3.1 Flash TTS | Disable audio, offer transcript | Paid |
| **STT** | `faster-whisper` on own worker | Groq Whisper large-v3-turbo | Gemini transcription | Own / paid |
| **Embeddings** | **Self-hosted all-MiniLM-L6-v2** (same 384-dim vectors, no re-index, $0) | OpenAI text-embedding-3-small (needs full re-embed) | — | Own |
| **Web search** | Tavily | Exa → Brave | Gemini grounding (only when needed) | Paid |
| **Code sandbox** | E2B | Queue and retry | — | Hobby → Pro |

## 3.2 Providers removed, demoted or deferred — and why
| Provider / practice | Decision | Reason |
|---|---|---|
| **OpenRouter** as production primary | **Demote to last-resort fallback / experiments only** | 5.5% fee on credit purchases; free models capped at ~20 rpm and 50–1,000 requests/day; no published uptime SLA on self-serve; the `openrouter/free` auto-router hides which model answered, which breaks eval reproducibility and privacy claims **[V]** |
| **HuggingFace chat router** | **Remove** | Credit pool ($0.10/month per account), not a production product |
| **Free-tier keys** (the "57 keys" pattern) | **Retire for production** | Privacy (Google free tier trains on content), rate limits (Gemini free RPD ≈ 20 on new models), key-sprawl operational risk, unpredictable quotas **[V]** |
| **Cloudflare Workers AI chat models** | **Remove from chains until priced and evaluated** | No verified price in this book; keep Cloudflare for DNS/CDN/WAF only |
| **Cerebras** | **Optional speed fallback** | gpt-oss-120b at $0.35/$0.75 is 2.3× Groq's input price **[V]** |
| **DeepSeek, Qwen, GLM, Kimi (Chinese-lab APIs)** | **Defer to Phase 3b+ and only via US/EU hosts** | Repriced repeatedly (DeepSeek V4.1 Flash now has peak and off-peak rates); direct APIs send user code to China-hosted servers, which conflicts with the privacy promise; reported regulatory uncertainty **[V]** |
| **Groq Llama 3.1 8B / 3.3 70B** | **Delete from `QUOTA_CONFIG`** | Deprecated 08/16/26 **[V]** |
| **Anthropic and OpenAI adapters** | **Build now** | The repo has no adapters for them; Brain and Advanced classes depend on them |

## 3.3 Account and key architecture (replaces the free-key pool)
1. **One organisation account per provider**, in the company's name, with a company payment method. No personal accounts.
2. **Four keys per provider:** `prod-paid`, `prod-free`, `staging`, `evals`. Separating `prod-free` from `prod-paid` makes Free spend visible and independently capped. Keep a second `prod-paid-b` key for rotation.
3. **Pre-fund and climb tiers before launch.** Anthropic raises API limits by cumulative purchases (a May 2026 source lists $5 / $40 / $200 / $400 thresholds — **[U]**, confirm in the console). Buy credits early in Phase 1 so the account already sits at the tier that carries launch traffic. Groq's Developer plan lists about 250K tokens/min and 1K requests/min on gpt-oss-120b **[V]**; request increases before launch.
4. **Two funding instruments.** Hold two internationally enabled cards (or USD accounts). A single card failure must not stop every vendor at once. **[U — see Part 22]**
5. **Spend guards at two layers:** provider-side budget alerts at 50% / 80% / 100%, and the internal rate ledger hard limits per class and per plan (7.2).
6. **Secrets:** no keys in the repo or in `.env.example`; per-environment secrets manager from Phase 2; rotate on any team change.

## 3.4 Failover design
| Trigger | Action |
|---|---|
| HTTP 429 / 5xx / timeout | One retry on the same provider (≤ 2 s backoff), then next provider in the role's chain |
| 5 failures in 60 s | Circuit-breaker: provider marked *degraded* for 5 min |
| p95 latency > 3× baseline for 10 min | Shift 50% of that class's traffic to the fallback |
| Provider daily spend > 130% of forecast | Alert and shift weights; do not silently continue |
| Any provider > 60% of a class's traffic | Rebalance (concentration rule) |

**Target traffic weights (planning):** Class S — Groq 55% / OpenAI 20% / Mistral 15% / Google 10%. Class A — Anthropic 50% / Google 25% / Mistral 15% / OpenAI 10%. Class E — Anthropic 55% / Google 30% / OpenAI 15%. **[A]** — tune by eval and by rate limits.

## 3.5 Vendor-risk rules
1. **Export-control precedent.** On June 12, 2026 Anthropic suspended Fable 5 and Mythos 5 to comply with U.S. Commerce Department export controls; access was restored July 1 after the controls were lifted on June 30. The order applied to foreign nationals, which includes a Bangladesh-registered company, so this risk is *not symmetric* with a U.S. startup's. The Brain therefore always has a cross-vendor standby and a no-Brain path (6.5). **[V]**
2. **Fable safety classifier.** Fable 5.x carries a safety classifier for vulnerability-finding content that can reroute some requests to a different model. Keep security-scanning agents off the Brain; run them on Class S/A models. **[V, secondary source — [U] on exact behaviour of 5.1]**
3. **Tokenizer inflation.** Fable 5.1's tokenizer yields about 30% more tokens for the same text; the meter counts real tokens, so "$10 per million" is about 30% dearer per character. Budget for it. **[V]**
4. **Concentration:** no single vendor above 60% of total frontier spend.
5. **Deprecation discipline:** subscribe to every provider's changelog; keep a 90-day migration buffer; the model-change protocol (6.7) applies to forced migrations too.
6. **Chinese-lab models** stay deferred (3.2) until you have a US/EU-hosted route and a privacy review.

## 3.6 Data-privacy rules (protect the landing-page promise)
1. Production runs only on paid tiers. Confirm each vendor's API data-use terms in writing at signup and record them in a vendor register **[U for each vendor]**.
2. Request zero-data-retention or the vendor's strongest retention setting where offered.
3. Redact secrets and PII before external calls (existing guardrail modules in the repo; treat as mandatory in Phase 2).
4. Publish a sub-processor list: Anthropic, OpenAI, Google, Groq, Mistral, Azure (TTS), Tavily/Exa/Brave (search queries leave the system), E2B (code executes there), Supabase, Upstash, Pusher, Sentry, Langfuse, payment gateways.
5. Never route user content to a free tier "just for testing".

## 3.7 Payment acceptance
| Audience | Rails | Fee planning | Notes |
|---|---|---|---|
| Bangladesh | bKash, Nagad, Rocket, local Visa/Mastercard/Amex via an aggregator (e.g., SSLCommerz, ShurjoPay) | 2.5% | Prices in BDT; settle in BDT; wallets dominate, so local share of paying users is planned at 65% |
| International | Visa/Mastercard/Amex through a merchant-of-record or Payoneer/2Checkout-type rail. **PayPal only if your structure can hold a business account — it is reported as unavailable to Bangladeshi merchants [U]** | 4.5% + $0.30 | Prices in USD; push annual plans to cut the fixed-fee drag |

Rules: (a) bill in the currency shown on the price card; (b) annual plan = 10× monthly; (c) recurring billing must be tested on wallet rails before launch, because wallet "subscriptions" are not the same as card recurring; **[U]** (d) keep chargeback and refund policy written before Phase 2. Open questions are in Part 22.

---

# 4. PRICE SHEET (SINGLE SOURCE OF TRUTH)

*All prices in USD per 1M tokens unless stated. "List" means the non-promotional price. Snapshot 2026-09-19.*

## 4.1 Language models
| Vendor | Model | Input | Output | Other | Label |
|---|---|---|---|---|---|
| Anthropic | **Fable 5.1** (`claude-fable-5-1`) | 10.00 | 50.00 | Cache read 0.25; cache write 12.50 (5 min) / 20 (1 h); **Batch 5 / 25**; ~30% more tokens per text | **[V]** |
| Anthropic | **Opus 5** (`claude-opus-5`) | 5.00 | 25.00 | | **[V]** |
| Anthropic | **Sonnet 5** (`claude-sonnet-5`) | 2.00 | 10.00 | Intro price made permanent | **[V]** |
| Anthropic | Haiku 4.5 (`claude-haiku-4-5-20251001`) | 1.00 | 5.00 | | **[V]** |
| OpenAI | **GPT-6 Astra** | 10.00 | 50.00 | Cached input 10%; Batch/Flex −50%; input > 272K tokens billed 2× input, 1.5× output | **[V]** |
| OpenAI | GPT-5.6 Sol | 5.00 | 30.00 | Promo $4/$20 through at least Nov 21, 2026 | **[V]** |
| OpenAI | GPT-5.6 Terra | 2.00 | 12.00 | One aggregator shows $2.50/$15 | **[U]** |
| OpenAI | **GPT-5.6 Luna** | 0.20 | 1.20 | Cut on Jul 30, 2026 (older pages show $1/$6); reasoning model | **[V]** |
| OpenAI | text-embedding-3-small | 0.02 | — | | **[V]** |
| Google | **Gemini 3.6 / 3.7 / 3.8 Flash** | **0.75 → 1.50** | **3.75 → 7.50** | Intro price through 2026-12-31, doubles 2027-01-01; batch −50% | **[V]** |
| Google | Gemini 3.5 Flash | 1.50 | 9.00 | Batch 0.75 / 4.50 | **[V]** |
| Google | Gemini 3.5 Flash-Lite | 0.30 | 2.50 | Batch 0.15 / 1.25 | **[V]** |
| Google | **Gemini 3.1 Flash-Lite** | 0.25 | 1.50 | Batch/Flex 0.125 / 0.75 | **[V]** |
| Google | Gemini 3.1 Pro (Preview) | 2.00 | 12.00 | ≤ 200K context; 4 / 18 above; batch 1 / 6; *preview status = stability risk* | **[V]** |
| Groq | **gpt-oss-120b** (`openai/gpt-oss-120b`) | 0.15 | 0.60 | ≈ 250K TPM / 1K RPM on Developer plan | **[V]** |
| Groq | **gpt-oss-20b** (`openai/gpt-oss-20b`) | 0.075 | 0.30 | | **[V]** |
| Groq | Qwen3.6-27B (`qwen/qwen3.6-27b`) | 0.60 | 3.00 | 4–5× gpt-oss-120b; use only where evals prove it | **[V]** |
| Groq | Whisper large-v3-turbo | $0.04 per audio hour | | | **[V]** |
| Mistral | **Large 3** | 0.50 | 1.50 | Pin the dated ID | **[V]** |
| Mistral | Medium 3.5 | 1.50 | 7.50 | Check what `mistral-medium-latest` resolves to before using it | **[V]/[U]** |
| Mistral | Small 4 | 0.15 | 0.60 | | **[V]** |
| Mistral | Codestral | 0.30 | 0.90 | | **[V]** |
| Mistral | **Devstral 2** | 0.40 | 2.00 | One aggregator lists 0.40 / 0.90 | **[U]** |
| Cerebras | gpt-oss-120b | 0.35 | 0.75 | Optional | **[V]** |
| DeepSeek (deferred) | V4.1 Flash | 0.30 | 1.20 | Half price off-peak | **[V]** |
| DeepSeek (deferred) | V4 Pro | 1.32 | 3.96 | Half price off-peak | **[V]** |

## 4.2 Non-LLM services
| Service | Price | Label |
|---|---|---|
| Google image output | 3.1 Flash-Lite Image **$0.0336** / 1K image; 3.1 Flash Image **$0.067** / 1K image ($0.045 at 0.5K); 3 Pro Image **$0.134** (1K/2K); batch −50% | **[V]** |
| Google TTS | Gemini 3.1 Flash TTS Preview $1 in / $20 out per 1M tokens (audio ≈ 25 tokens/sec ≈ **$0.03/min**) | **[V]** |
| Google transcription | Gemini 3.5 Transcribe ≈ **$0.005/min** | **[V]** |
| Google Search grounding | 5,000 free/mo, then $14 per 1,000 | **[V]** |
| Azure neural TTS | ≈ **$16 per 1M characters**; free tier 0.5M characters/month | **[V]** |
| Tavily search | **$0.008 per credit** (basic search = 1 credit, advanced = 2) | **[V]** |
| Exa search | $7 per 1,000 | **[V]** |
| Brave Search | $5 per 1,000 with a $5 monthly credit; free plan removed for new users | **[V]** |
| E2B sandbox | Hobby: $0 + one-time $100 credit, 1 h sessions, 20 concurrent. Pro: **$150/mo** + usage (≈ $0.000014 / vCPU-s, $0.0000045 / GiB-s → **≈ $0.0018 per 60-s run**) | **[V]** |
| Supabase | Free (pauses after 7 idle days — not for production); **Pro $25/mo** incl. $10 compute credit (growing app ≈ $36); Team $599 | **[V]** |
| Upstash Redis | Free 256 MB / 500K commands; pay-as-you-go **$0.20 per 100K commands**, $0.25/GB after 1 GB; fixed plans from $10; free vector index 10K documents | **[V]** |
| Pusher Channels | Sandbox free (100 connections, 200K msgs/day); **Startup $49** (500 conn, 1M msgs/day); **Pro $99** (2,000 conn) | **[V]** |
| Sentry, Langfuse, VPS | Not re-verified in this pass | **[U]** |

## 4.3 Blended cost per model at the planning split (computed)
Worker split 70/30; Brain rows use 85/15 and 50% cache reads.

| Model | $/1M tokens | | Model | $/1M tokens |
|---|---|---|---|---|
| gpt-oss-20b | 0.14 | | Sonnet 5 | 4.40 |
| gpt-oss-120b | 0.29 | | GPT-5.6 Terra | 5.00 |
| Mistral Small 4 | 0.29 | | Gemini 3.1 Pro | 5.00 |
| GPT-5.6 Luna | 0.50 | | Opus 5 | 11.00 |
| Gemini 3.1 Flash-Lite | 0.63 | | GPT-5.6 Sol | 12.50 |
| Mistral Large 3 | 0.80 | | **Fable 5.1 as Brain, real-time** | **11.86** |
| Devstral 2 | 0.88 | | **Fable 5.1 as Brain, batch** | **5.93** |
| Haiku 4.5 | 2.20 | | GPT-6 Astra as Brain, real-time | 12.18 |
| Gemini 3.x Flash (2027 price) | 3.30 | | Fable 5.1 uncached, no batch | 22.00 |

**Rule:** when a price is in doubt, budget at the list price of 2027 (not the promo).

---

# 5. MODEL ROSTER — WHICH MODEL RUNS WHERE

## 5.1 The five model classes
Every agent call belongs to one class. Classes, not individual models, are what plans meter (Part 7).

| Class | Purpose | Traffic composition inside the class **[A]** | Blended $/1M |
|---|---|---|---|
| **F — Free** | Free tier only; cheapest sufficient | gpt-oss-20b 40% · gpt-oss-120b 40% · GPT-5.6 Luna 20% | **0.27** |
| **S — Standard** | Default worker class, all paid plans | gpt-oss-120b 40% · Luna 20% · gpt-oss-20b 15% · Mistral Large 3 10% · Gemini 3.1 Flash-Lite 10% · Devstral 2 5% | **0.42** |
| **A — Advanced** | Hard steps and final synthesis (Moderate+) | Sonnet 5 40% · Gemini 3.x Flash 25% · Mistral Large 3 15% · Terra 10% · Haiku 4.5 10% | **3.43** |
| **E — Expert** | Hardest coding/reasoning, board-level output (Ultimate) | Opus 5 55% · Gemini 3.1 Pro 30% · Sol 15% | **9.43** |
| **B — Brain** | Planning, decomposition, adjudication (Moderate+) | Fable 5.1 (Astra as failover) | **11.86** real-time · **5.93** batch |

The Advanced mix is deliberately diversified because public coding benchmarks disagree: one August 2026 comparison has GPT-5.6 Terra and Gemini 3.7 Flash ahead of Sonnet 5 on terminal-style agentic benchmarks, while Sonnet 5 leads on knowledge-work and SWE-bench-style tests. Gemini Flash costs about a third of Terra at promo price and about two-thirds at the 2027 price. **Decide the actual weights by your own eval set (6.7); do not trust leaderboards.** **[U]**

## 5.2 Sector × tier matrix (the core table)
Cells list models in **fallback order** (first = primary). "—" means the capability is not offered on that plan.

| Sector / agent group | Free | Basic | Moderate | Ultimate |
|---|---|---|---|---|
| **Intake & routing** (SGA, Inspector, Responder) | gpt-oss-20b (SGA), gpt-oss-120b (Inspector, Responder) | same | same | same — *never upgrade routing; it is latency-critical and cheap* |
| **Committee votes** (Panel A/B/C) | 3 lineages: gpt-oss-120b · Mistral Large 3 · Gemini 3.1 Flash-Lite | same | same (Brain replaces Panel on Deep tasks; Panel is the fallback) | same |
| **Brain** (plan, decompose, adjudicate) | — | — (Panel + fixed pipelines) | **Fable 5.1 batch**, Deep mode only → Opus 5 → Panel | **Fable 5.1 real-time** + batch → **GPT-6 Astra** → Opus 5 → Panel |
| **Research & writing** (researchers' analysts, writers, editors, notebook generators) | F class | S class | S default; **A for final synthesis and long documents** | S default; A for synthesis; **E on request / hardest docs** |
| **Code authoring** (implementer, structure architect, fixer) | Snippets only, F class | Devstral 2 → Codestral → Luna → gpt-oss-120b | Gemini 3.x Flash → Sonnet 5 → Terra; S for boilerplate | Sonnet 5 → Terra; **Opus 5 for hardest steps**; Astra for terminal/computer-use-heavy work |
| **Review & verification** (reviewer pool, test writers, LLM parts of security scanners) | — | Three lineages: gpt-oss-120b · Mistral Large 3 · Gemini 3.1 Flash-Lite | + Sonnet 5 / Gemini Flash as final reviewer on high-severity findings | + Opus 5 final reviewer. **Never Fable** for security scanning (3.5) |
| **Structure / mechanical specs** (LLM-backed `mech_*` pools; deterministic validators stay authoritative) | — | gpt-oss-120b → Luna | Gemini Flash / Sonnet 5 at section level | Opus 5 for validation and repair only |
| **Long-context ingestion** (PDF, transcripts, large repos) | Gemini 3.1 Flash-Lite (small files) | Gemini 3.1 Flash-Lite | Gemini 3.x Flash | Gemini 3.1 Pro only above ~200K tokens (price steps up) |
| **Vision** (screenshots, wireframes, PDF pages) | Gemini 3.1 Flash-Lite | same | Gemini 3.x Flash | Gemini 3.1 Pro |
| **Image generation** | 3.1 Flash-Lite Image (2/mo) | 3.1 Flash-Lite Image (8/mo) | 3.1 Flash-Lite Image + 3.1 Flash Image (20/mo) | + 3 Pro Image for hero assets (40/mo) |
| **Audio** (podcast/overview TTS; STT) | — | Azure TTS (20K chars/mo); local Whisper | Azure TTS (60K chars/mo) | Azure TTS (100K chars/mo); Gemini TTS for premium voice |
| **Embeddings / memory** | self-hosted MiniLM | same | same | same |
| **Web search** | Tavily (8/mo) | Tavily (50/mo) | Tavily → Exa (150/mo) | Tavily → Exa → Brave (300/mo) |
| **Code sandbox** | — | E2B (40 runs/mo) | E2B (150) | E2B (400) |

**Text before pixels:** wireframes, flowcharts and diagrams are generated as Mermaid/SVG by text models at Standard cost. Use image models only when a raster is truly needed.

## 5.3 Mode behaviour
| Mode | Free | Basic | Moderate | Ultimate |
|---|---|---|---|---|
| **Quick** (fast, SGA-led) | Yes | Yes | Yes | Yes |
| **Balanced** (fixed pipeline, reviewers) | Limited by pool | Yes | Yes | Yes |
| **Deep** (Brain plans, delegates, adjudicates) | — | — | Yes (batch Brain) | Yes (real-time + batch Brain) |

## 5.4 How to apply this in the repo
1. `backend/eo/product_tier_map.py` holds role rows × tier columns with an `INHERIT` sentinel. Set each role's chain per the matrix above; use `INHERIT` when a tier reuses the tier below it. Add a **`free`** column (the file today has only basic / moderate / ultimate).
2. `backend/utils/llm_client.py` `QUOTA_CONFIG` still describes free-tier quotas and dead Groq models. Replace it with paid-tier limits from each provider's console and add Anthropic and OpenAI adapters.
3. `backend/eo/dynamic_chain.py` `PROVIDER_DEFAULT_MODEL`: pin explicit model IDs; remove aliases.
4. Panel member C currently points at `mistral-medium-latest`; change to a pinned **Mistral Large 3** ID (cheaper and current).
5. The Inspector currently uses Qwen3.6-27B ($0.60/$3.00); switch to gpt-oss-120b unless the classification eval shows a loss.
6. Illustrative row (adapt to the real structure):
```python
"implementer": {
    "free":     ["gpt-oss-120b"],                                   # snippets only
    "basic":    ["devstral-2", "codestral", "gpt-5.6-luna", "gpt-oss-120b"],
    "moderate": ["gemini-3.6-flash", "claude-sonnet-5", "gpt-5.6-terra"],
    "ultimate": ["claude-sonnet-5", "gpt-5.6-terra"],               # + escalation: claude-opus-5
},
```
   (IDs are illustrative; use each console's exact pinned identifier. Groq IDs in the repo are `openai/gpt-oss-120b`, `openai/gpt-oss-20b`; Gemini IDs `gemini-3.6-flash`, `gemini-3.1-flash-lite`; Claude IDs `claude-fable-5-1`, `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`.)

---

# 6. ESCALATION, DOWNGRADE, FAILOVER AND MODEL-CHANGE RULES

## 6.1 The escalation ladder (when to swap an agent to a stronger model)
Thresholds are starting values **[A]**; tune from Tech-A data.

| Step | Model class | Trigger to move up | Plan availability |
|---|---|---|---|
| 0 | **S** (default) | — | All paid plans |
| 1 | **A** | Any of: sandbox/validator fails on attempt 2 · structured-output parse fails twice · reviewer reports severity ≥ high · multi-file change (> 5 files) · spec or input > 20K tokens · final-synthesis step of a research/writing task | Moderate, Ultimate |
| 2 | **E** | A fails twice (attempt 4) · security-sensitive code (auth, payments, crypto, permissions) · the user chooses "max quality" | Ultimate |
| 3 | **Brain re-plan** | E fails once, or reviewers from different lineages disagree on the plan itself | Moderate (batch) / Ultimate |
| 4 | **Stop** | Attempt 5 reached | Return best partial result plus a plain explanation; never loop |

- **Basic has no A/E step.** On repeated failure: rotate to a different S-class lineage (e.g., gpt-oss-120b → Mistral Large 3 → Luna), then return the partial result and offer an upgrade. **Free** gets no escalation.
- **Per-run hard cost ceilings** (runaway guard) **[A]:** Free $0.05 · Basic $0.60 · Moderate $2.50 · Ultimate $8.00. Hitting a ceiling ends the run gracefully.

## 6.2 Task-type specialists (when to bring a specialist model)
| Need | Default | Upgrade | Trigger |
|---|---|---|---|
| Classification, extraction, routing, short summaries | gpt-oss-20b | — | Never upgrade |
| General reasoning, math, planning subtasks | Luna / gpt-oss-120b (raise reasoning effort first) | Sonnet 5 → Opus 5 | Fails after higher effort |
| Coding, single function or file | Devstral 2 / Codestral | Luna | Parse or test failure |
| Coding, multi-file, refactor | Gemini 3.x Flash / Sonnet 5 | Opus 5 | Step 1–2 triggers |
| Terminal / computer-use style workflows | Terra | GPT-6 Astra (Ultimate) | Long-horizon tool loops |
| Long documents, transcripts | Gemini 3.1 Flash-Lite | Flash → 3.1 Pro | > 200K tokens (price steps up above this) |
| Vision | Gemini 3.1 Flash-Lite | Flash → 3.1 Pro | Dense diagrams, small text |
| Raster image | 3.1 Flash-Lite Image ($0.034) | 3.1 Flash Image ($0.067) → 3 Pro Image ($0.134) | Text inside image, hero asset, user clicks "higher quality" (costs pool) |
| Speech out | Azure neural | Gemini Flash TTS | Premium-voice request |
| Speech in | Local `faster-whisper` | Groq Whisper Turbo | CPU queue > 5 min |
| Search | Tavily basic | Tavily advanced (2 credits) → Exa | Thin results |

## 6.3 Brain rules
1. **Engages:** Deep mode on Moderate/Ultimate; tier-3 tasks where the Inspector flags high complexity. **Does:** plan, decompose, choose agents and tiers, adjudicate disagreements, check the final synthesis. **Never does:** bulk code, security scanning, routine chat, classification.
2. **Budget per Brain run:** ≈ 30K tokens **[A]**, hard ceiling 60K and 4 calls. Overrun is logged as a defect.
3. **Cache discipline (this decides the Brain's real price):** static content first (capability catalogue, templates, policies), variable content last; keep the prefix byte-identical between calls; use the 1-hour cache for Deep runs. Track cache-hit rate. **Target ≥ 50%; below 30% means fix prompt ordering before spending more.** Fable 5.1 cache reads cost $0.25/M against $10/M uncached.
4. **Batch on Moderate:** Deep runs are asynchronous (Batch $5/$25). The UI must promise "queued, not instant".
5. **Never let the Brain pick models outside the user's plan pools.**
6. **Failed Brain calls do not consume the user's Brain pool.**

## 6.4 Downgrade rules
| Situation | Behaviour |
|---|---|
| Expert pool empty | Route to Advanced with a visible notice |
| Brain pool empty | Panel-only planning with a visible notice; offer a Brain top-up |
| Advanced pool empty | Route to Standard with a notice; offer an Advanced top-up |
| Standard pool empty | The **current run may finish using a 10% grace buffer**; new runs are blocked with a top-up / upgrade prompt |
| Plan-level rolling COGS > 45% of revenue | Reduce A/E routing weights automatically |
| Plan-level rolling COGS > 60% of revenue | Emergency: S-class only unless the user explicitly selects a higher class; alert the founder |

## 6.5 Brain outage playbook
1. Detect: 3 consecutive failures, or an announced restriction.
2. Fail over in order: **Fable 5.1 → GPT-6 Astra → Opus 5 → Panel-only path.**
3. Show "Brain unavailable — using standard planning"; do not charge Brain pool.
4. Cost check: Astra as Brain costs about $12.18/M (vs $11.86), so the budget effect is small; Opus 5 without caching is about $8/M at the 85/15 split.
5. If the outage exceeds 24 hours, tell paying Ultimate users; if it exceeds 7 days, offer a prorated credit.
6. After recovery, run the cache warm-up before shifting traffic back.

## 6.6 Cost levers, in order of value
1. **Prompt caching** on every repeated prefix (Brain first).
2. **Batch (−50%)** for everything non-interactive: Moderate Deep runs, notebook generation, nightly jobs.
3. **Output discipline:** cap `max_tokens`, lower reasoning effort by default (reasoning tokens bill as output).
4. **Memoise search and embeddings** (24-hour search cache; content-hash embeddings).
5. **Avoid > 200K-token contexts** (price steps up above 200K on Gemini 3.1 Pro; above 272K on Astra).
6. **Text diagrams before image generation.**
7. **Consolidate decomposition steps** where an eval shows equal quality (fewer calls = fewer repeated prefixes).

**Never:** retry loops without caps · send the whole repo on every step · use Brain for classification · silently fall back to a free key.

## 6.7 Model-change protocol (adding, replacing, or forced migration)
1. Put the candidate's price into Part 4 with a label.
2. Run the role's **eval set** (≥ 50 golden cases per role **[A]**) on the *evals* key. Record pass rate, cost per task, p95 latency.
3. **Accept** if pass rate ≥ current − 1 point at ≤ current cost, **or** ≥ current + 5 points at ≤ 1.5× cost.
4. **Canary** 5% of that role's traffic for 7 days on paid keys.
5. Watch error, failover and cache-hit rates; roll back if any worsens materially.
6. Update Part 5 and `product_tier_map.py`.
7. Re-run Appendix A; check the four gates (0.4).
8. Add a change-log line (23.2). For forced deprecations, run the same steps on a compressed schedule.

## 6.8 Signal → swap (quick reference)
| Signal | Swap |
|---|---|
| Basic reviewer pass rate < 85% on eval | Move reviewer #1 from gpt-oss-120b to Mistral Large 3 |
| Sandbox failure rate > 25% on Basic builds | Try Devstral 2 → Luna → gpt-oss-120b rotation; if still > 25%, raise the Basic mid-run refusal to "partial + upgrade" |
| Moderate Deep runs show > 20% Brain re-plans | Improve Inspector routing before paying for more Brain |
| Ultimate security-sensitive tasks fail at A | Escalate those to Opus 5 by default |
| Gemini Flash price doubles (2027-01-01) | Re-run Appendix A; shift Class A weights toward Sonnet 5 / Mistral Large 3 if margin gate fails |
| Provider error rate > 2% for 1 hour | Shift 50% of its traffic to the fallback |
| Image users regenerate > 30% of outputs | Move default from Flash-Lite Image to Flash Image (cost +$0.033 per image) |

---

# 7. PLANS, PRICES, TOKEN LIMITS, FREE TIER, TOP-UPS

> The $9 / $29 / $79 and 1M / 4M / 12M numbers on the landing page were placeholders. The numbers below are derived from the price sheet (Part 4), the model roster (Part 5) and the gates in 0.4. **They are launch-ready but still depend on [A] usage assumptions; confirm with Tech-A data before charging real customers (Part 22).**

## 7.1 The plan table (authoritative)
| | **Free** ("Founding Free") | **Basic** | **Moderate** | **Ultimate** |
|---|---|---|---|---|
| **Price / month (USD)** | $0 | **$9** | **$29** | **$79** |
| **Price / month (BDT, local rails)** | 0 | **BDT 899** | **BDT 2,999** | **BDT 8,499** |
| BDT price vs USD price at 123 | — | −19% | −16% | −12.5% |
| **Annual (10× monthly, "2 months free")** USD / BDT | — | $90 / 8,990 | $290 / 29,990 | $790 / 84,990 |
| **Standard-class tokens / month** | 300K (F class) | **4.0M** | **5.0M** | **6.0M** |
| **Advanced-class tokens / month** | — | — | **1.2M** | **3.0M** |
| **Expert-class tokens / month** | — | — | — | **0.4M** |
| **Brain tokens — batch / month** | — | — | **0.15M** | **0.2M** |
| **Brain tokens — real-time / month** | — | — | — | **0.25M** |
| **Total tokens / month** | 0.3M | 4.0M | 6.35M | 9.85M |
| Web searches / month | 8 | 50 | 150 | 300 |
| Generated images / month | 2 | 8 | 20 | 40 |
| Text-to-speech characters / month | — | 20K | 60K | 100K |
| Sandbox test runs / month | — | 40 | 150 | 400 |
| Modes | Quick + limited Balanced | Quick, Balanced | + Deep (batch Brain) | + Deep (real-time + batch Brain) |
| **Approx. capacity [A]** | ~40 chat turns or 1 small build-run-equivalent; code snippets only | ≈ 16 Balanced builds | ≈ 5 Brain-assisted Deep runs **and** ≈ 14 Balanced builds | ≈ 14 Deep runs (8 real-time + 6 batch) **and** ≈ 18 Balanced builds |
| Daily fair-use ceiling | 40K tokens | 20% of any pool per 24 h | same | same |

*Why these differ from the placeholders:* Standard tokens are so cheap ($0.42/M) that Basic can carry 4M of them; the expensive resource is Advanced/Expert/Brain tokens, so those are metered in small, separate pools. Total tokens (4.0M / 6.35M / 9.85M) land in the same order of magnitude as the old 1M / 4M / 12M, but no longer let a user spend frontier money with Standard quota.

## 7.2 How the meter works
1. **One ledger, four counters** (Standard, Advanced, Expert, Brain), keyed by the class of the model actually used. Dollars are logged separately for governance; users never see dollars.
2. **Count real, provider-reported tokens** (input + output; reasoning tokens count as output). Cached input tokens count normally in the user-facing meter (simple to explain) while the internal cost uses the cheaper cached price.
3. **Fable 5.1's tokenizer inflates counts by about 30%**; the Brain pool is denominated in real Fable tokens, so it already absorbs this.
4. **No rollover.** Pools refresh on the billing anniversary (annual plans refresh monthly).
5. **Show at most four numbers** in the UI, with a bar per pool and an 70% warning.
6. **Never bill by surprise:** no automatic overage charges. Users buy top-ups explicitly (7.3).

## 7.3 Top-up packs
| Pack | Price USD | Price BDT | Our cost | Multiple | Available on |
|---|---|---|---|---|---|
| Standard 5M tokens | $7 | 749 | $2.11 | 3.3× | Basic+ |
| Advanced 1M tokens | $12 | 1,249 | $3.43 | 3.5× | Moderate+ |
| Expert 0.5M tokens | $18 | 1,899 | $4.71 | 3.8× | Ultimate |
| Brain batch 200K tokens | $6 | 599 | $1.19 | 5.1× | Moderate+ |
| Brain real-time 100K tokens | $6 | 599 | $1.19 | 5.1× | Ultimate |

Rules: top-ups expire 90 days after purchase; consumed after the monthly pool; multiple ≥ 3× cost on every pack (BDT prices still keep ≥ 3.5×).

## 7.4 The Free tier ("Founding Free Window")
**Purpose:** marketing and audience building, deliberately funded and deliberately temporary. Your decision: keep it for the first 6–12 months, then move value into paid plans.

**Allowances:** 300K Free-class tokens/month (max 40K/day) · 8 searches · 2 images · Quick mode + limited Balanced · code snippets only · no Deep, no sandbox, no TTS, no API access.
**Cost per active Free user:** at cap **$0.21** (0.30M × $0.27 + 8 × $0.008 + 2 × $0.034); expected at 60% use **$0.13**.

**Budget governor (Rule 8):**
| Phase | Monthly Free ceiling |
|---|---|
| During the window (M1–M12) | **max($150, 25% of last month's MRR)** |
| After the window | max($100, 10% of last month's MRR) |

When the ceiling is reached, in this order: (1) cut the daily cap to 20K; (2) move new Free runs to off-peak batch with delay; (3) pause new Free sign-ups' allowance (waitlist). **Never** take capacity from paid users.

**Checkpoints:**
| When | Decision | Evidence needed |
|---|---|---|
| **M6** | Extend, shrink or keep | Activation rate; 30-day retention; paid conversion; Free cost as % of MRR; abuse rate |
| **M12** | Default action: **shrink to "Free Lite"** (150K tokens, 4 searches, 0 images, Quick only). Keep the full window to M18 only if Free cost ≤ 15% of MRR **and** cost per paid conversion ≤ $17 (about 3 months of Basic gross profit) | Same, plus cohort conversion curve |

**Anti-abuse (mandatory before launch):** verified email + phone OTP; one account per phone number and device fingerprint; disposable-email blocklist; CAPTCHA on sign-up; per-IP and per-device rate limits; flag accounts that burn > 80% of the pool in the first 24 hours; watch for reselling/proxy patterns.
**Upgrade prompts:** banner at 70% of a pool, upsell at 100% with a plan comparison.

## 7.5 Price-setting formula (use this when you must re-price)
1. Compute **COGS at cap** = Σ (pool × class $/M) + search + images + TTS + sandbox (Appendix A).
2. **Minimum price** = COGS at cap ÷ 0.45, evaluated at the *lowest* net price you charge (the BDT local price).
3. **Check** typical gross margin ≥ 70% at 55% utilization.
4. If a plan fails, change in this order: (a) routing weights, (b) pool sizes for *new* subscribers, (c) non-LLM allowances, (d) price for new subscribers, (e) price for existing subscribers (last resort, 30-day notice, 90-day grandfathering).

## 7.6 Discounts
Only the annual discount (2 months free) until six months of measured data exist. Any future promo must keep COGS at cap ≤ 55% of the promo price. Optional lever: a "founding member" price lock (12 months) for the first 500 paying users; the cost is only forgone future increases.

## 7.7 When to change prices or limits
Trigger any of: (a) a gate fails for two consecutive months; (b) a provider change moves a class cost by > 10%; (c) median utilization > 75% of pools; (d) a competitor changes the market anchor. Procedure = 7.5 step 4.

## 7.8 Edits required on the landing page (`frontend/app/components/LandingPage.jsx`)
| Current | Change to |
|---|---|
| Prices $9 / $29 / $79 labelled "illustrative" | Keep the numbers; remove "illustrative" only after the launch items in Part 22.1 are closed |
| BDT not shown | Show BDT prices (899 / 2,999 / 8,499) with bKash, Nagad, Visa, Mastercard and Amex badges (add a PayPal badge only once a PayPal business account is confirmed possible); add an annual toggle ($90 / $290 / $790) |
| Monthly tokens 1M / 4M / 12M | Replace with the pool numbers in 7.1 and the four pool names |
| No Free tier card | Add "Founding Free — for our first members" with allowances from 7.4 |
| "Fable 5" | Say **"Brain — Fable 5.1"** (or "frontier Brain") consistently; Moderate: "Brain on batch — not real-time" |
| Ultimate: "Every latest high- and mid-tier model, across every sector" | "Top-tier models from Anthropic, OpenAI and Google, chosen per task" (do not promise "every") |
| Privacy claims | Keep, but publish the sub-processor list (3.6) and confirm vendor terms first |
| "No credit card required to start" | Now true through the Free tier |

---

# 8. UNIT ECONOMICS

## 8.1 Cost per task (LLM only, computed from class costs; token counts are [A])
| Task | Tokens | Cost |
|---|---|---|
| Chat turn | 8K Standard | **$0.0034** |
| Research run | 60K Standard | **$0.025** |
| Notebook generation | 40K Standard | **$0.017** |
| Balanced build, all Standard | 250K | **$0.106** |
| Balanced build, 20% escalated to Advanced | 200K S + 50K A | **$0.256** |
| Deep run, batch Brain | 170K S + 100K A + 30K Brain | **$0.59** |
| Deep run, real-time Brain | same | **$0.77** |

**Add-ons:** search $0.008 each · sandbox run $0.0018 · image $0.034 / $0.067 / $0.134 · TTS about $0.16 per 10K characters.

## 8.2 Cost stack per plan when the user uses **100% of every pool** (COGS at cap)
| $ per user per month | Basic | Moderate | Ultimate |
|---|---|---|---|
| Standard pool | 1.69 | 2.11 | 2.53 |
| Advanced pool | — | 4.11 | 10.28 |
| Expert pool | — | — | 3.77 |
| Brain batch pool | — | 0.89 | 1.19 |
| Brain real-time pool | — | — | 2.96 |
| **LLM subtotal** | **1.69** | **7.11** | **20.73** |
| Search | 0.40 | 1.20 | 2.40 |
| Images | 0.27 | 0.94 | 2.68 |
| TTS | 0.32 | 0.96 | 1.60 |
| Sandbox | 0.07 | 0.27 | 0.72 |
| **Non-LLM subtotal** | **1.06** | **3.37** | **7.40** |
| **COGS at cap** | **2.75** | **10.48** | **28.13** |
| COGS at typical use (55%) | 1.51 | 5.76 | 15.47 |

## 8.3 Margin table (fee-adjusted, per paying user)
| | Basic | Moderate | Ultimate |
|---|---|---|---|
| Local price (BDT → USD at 123) / fee 2.5% | $7.31 / $0.18 | $24.38 / $0.61 | $69.10 / $1.73 |
| International price / fee (4.5% + $0.30) | $9.00 / $0.71 | $29.00 / $1.61 | $79.00 / $3.86 |
| **COGS at cap as % of local price (rule ≤ 45%)** | **37.6%** ✔ | **43.0%** ✔ | **40.7%** ✔ |
| **Gross margin at cap — local / international** | **59.9% / 61.6%** | **54.5% / 58.3%** | **56.8% / 59.5%** |
| **Gross margin typical (55%) — local / international** | **76.8% / 75.4%** | **73.9% / 74.6%** | **75.1% / 75.5%** |

**Blended gross profit per paid user per month** (65% local, typical use, monthly billing, annual factor 0.97): **Basic $5.79 (76%) · Moderate $18.50 (73%) · Ultimate $52.44 (75%).**

## 8.4 Break-even counts
| Fixed-cost bundle | Monthly | Basic users needed |
|---|---|---|
| Lean launch infra ($60) + Free budget ($150) | $210 | **≈ 36** |
| Phase 2 infra ($205) + Free budget ($150) | $355 | **≈ 61** |
| Phase 2 infra + Free budget + old-plan OpEx ($633) | $988 | **≈ 171** |

## 8.5 Sensitivities (gross margin, local / international)
| Case | Basic | Moderate | Ultimate |
|---|---|---|---|
| Base, at cap | 59.9 / 61.6% | 54.5 / 58.3% | 56.8 / 59.5% |
| **Everyone uses 90% of pools** | 63.7 / 64.7% | 58.8 / 61.9% | 60.9 / 63.1% |
| **LLM prices +25%, at cap** | 54.1 / 56.9% | 47.2 / 52.2% | 49.3 / 53.0% |
| **LLM prices +25%, typical** | 73.6 / 72.8% | 69.9 / 71.2% | 71.0 / 71.9% |
| **FX 135, at cap (local only)** | 56.2% | 50.3% | 52.8% |
| **Stress bundle** (FX 135 + LLM +25% + 80% use) | 59.4 / 64.0% | 53.4 / 60.7% | 55.2 / 61.4% |

*Note:* the first row already includes the 2027 doubled Gemini Flash price. At the 2026 promo price, Class A would cost $3.01/M instead of $3.43/M.
**Reading:** even at 100% use with +25% provider prices, no plan falls below ≈ 47% gross margin. Moderate is the tightest, because it carries the largest Advanced-to-price ratio.

---

# 9. 36-MONTH FINANCIAL MODEL, SCENARIOS, CASH AND THE OPEX GOVERNOR

## 9.1 What this model is (and is not)
- **Clock:** M1 = first month of public Free + Basic (0.2). Moderate opens after M12, Ultimate after M18 (demand-gated in your roadmap; modelling assumptions). Pre-launch stages S0 and S1 (Part 11) sit *before* M1.
- **User funnel:** your own targets from the old blueprint (registered Free 1,200 / 6,500 / 28,000 / 95,000 at M6 / M12 / M24 / M36; paid users as below), interpolated linearly. **They are unvalidated targets [A]**, not forecasts. The M6 Basic figure (40) is new.
- **Costs:** Parts 4–8. Free users cost $0.13 per monthly-active Free user during the window (60% of cap) and $0.07 after; 25% of registered Free users are active.
- **Two OpEx plans (the key idea of this book):**
  - **Plan A — "Lean / governed":** OpEx each month = min(team plan, max($150, 70% of last month's gross profit)). You buy the next rung of team, marketing and tooling only when the business has earned it. This is the default.
  - **Plan B — "Accelerated":** you spend the full **team plan** (Part 17.3) on schedule regardless of gross profit. It grows faster on paper and needs outside capital.
- **Excluded:** B2B/Enterprise (the old $1,500 and $5,750 MRR had no defined product or price), income tax (Part 14.6), FX conversion spread, refunds/chargebacks.

## 9.2 Snapshots (base case, revenue side)
| | M6 | M12 | M24 | M36 |
|---|---|---|---|---|
| Registered Free users | 1,200 | 6,500 | 28,000 | 95,000 |
| Basic / Moderate / Ultimate users | 40 / 0 / 0 | 120 / 0 / 0 | 450 / 120 / 25 | 1,850 / 680 / 190 |
| **Total paid** | **40** | **120** | **595** | **2,720** |
| **Revenue (MRR, net of annual discount)** | **$307** | **$920** | **$8,235** | **$44,700** |
| **ARR (MRR × 12)** | $3.7k | $11.0k | $98.8k | $536.4k |
| Paid-user COGS (55% use) | $60 | $181 | $1,758 | $9,654 |
| Free-tier cost | $38 | $207 | $476 | $1,615 |
| Payment fees | $15 | $44 | $341 | $1,797 |
| Infrastructure (stage) | $60 (lean) | $205 (Phase 2) | $753 (3a) | $2,600 (3b) |
| **Gross profit** | **$133** | **$282** | **$4,906** | **$29,033** |
| **Gross margin** | 43% | 31% | 60% | 65% |

*Reading:* Free cost is 22% of MRR at M12 (the price of the marketing window) and fades to 4% by M36. Early gross margin is low because fixed infrastructure divides over few users.

## 9.3 Annual P&L (base case; recognised revenue, not year-end ARR)
| | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Revenue | $5,058 | $53,304 | $335,840 |
| Paid-user COGS | ($998) | ($11,268) | ($72,425) |
| Free-tier cost | ($955) | ($3,702) | ($13,115) |
| Payment fees | ($241) | ($2,274) | ($13,559) |
| Infrastructure | ($1,010) | ($4,104) | ($21,965) |
| **Gross profit** | **$1,855** | **$31,957** | **$214,775** |
| **Gross margin** | **36.7%** | **60.0%** | **64.0%** |
| OpEx — **Plan A (governed)** | ($1,952) | ($19,133) | ($86,875) |
| **EBITDA — Plan A** | **($97)** | **$12,824** | **$127,900** |
| OpEx — **Plan B (accelerated team plan)** | ($9,737) | ($46,654) | ($97,456) |
| **EBITDA — Plan B** | **($7,882)** | **($14,697)** | **$117,319** |
| *Reference: old-blueprint OpEx* | *($7,600)* | *($41,400)* | *($175,500)* |

Pre-launch costs (S0 + S1 + launch one-offs, **$3,628**, Part 11) sit before Year 1 and are *not* in these EBITDA lines.

## 9.4 Old blueprint versus this book
| Item | Old blueprint | This book |
|---|---|---|
| Prices (monthly) | $6.42 / $20.42 / $45.83 (BDT 770 / 2,450 / 5,500) | $9 / $29 / $79 (BDT 899 / 2,999 / 8,499) |
| Included tokens | 3.5M / 12M / 35M | 4.0M / 6.35M / 9.85M split into four classes |
| Implied API cost per million tokens | $0.39 / $0.33 / $0.23 (cheaper for the top tier — impossible) | Class-based: $0.42 (S) → $3.43 (A) → $9.43 (E) → $11.86 (Brain) |
| M12 / M24 / M36 MRR | $770 / $7,985 / $40,221 (last two include B2B) | $920 / $8,235 / $44,700 (no B2B) |
| Year-3 revenue | $482,500 (= year-end ARR) | $335,840 recognised |
| Year-3 gross margin | 70.9% | 64.0% (after Free cost, infra, fees) |
| Free-tier compute | not costed | costed (7.4) |
| Cash breakeven | Month 15 | Plan A self-funds after an initial gap of about **$4.2k**; Plan B needs about **$27.9k** |
| Pre-launch capital | $500 seed assumed enough | **$3,628** needed before Month 1 (Part 11) |
| Infra at Phase 2 / 3a | $150 / $499 | $205 / $753 (verified components) |
| Statutory tax assumption | "software 100% VAT-exempt" | Imported services now carry 15% reverse-charge VAT unless you are an NBR-registered startup (Part 14.6) |

## 9.5 Scenarios (each with both plans; "external need" = deepest cumulative cash deficit including pre-launch, before any outside money)
| Scenario | Y3 revenue | Y3 gross margin | **Plan A** Y3 EBITDA | **Plan A** external need | **Plan B** Y3 EBITDA | **Plan B** external need |
|---|---|---|---|---|---|---|
| **Base** | $335.8k | 64.0% | $127.9k | **$4.2k** (M6) | $117.3k | **$27.9k** (M25) |
| **Conservative** (paid ×0.5, Free ×0.6) | $167.9k | 65.0% | $46.4k | **$4.8k** (M11) | $11.7k | **$59.8k** (M30) |
| **Heavy use** (90% of pools) | $335.8k | 50.2% | $89.6k | **$4.4k** (M7) | $71.2k | **$37.2k** (M26) |
| **Stress** (FX 135 + LLM +25% + 80% use) | $317.6k | 45.7% | $71.7k | **$4.6k** (M12) | $47.6k | **$43.2k** (M26) |

**Reading:** Plan A survives every scenario for **under $5k** of outside money. Plan B needs **$28k–$60k**. Buying speed with your own cash is a choice; the book makes you see its price before you make it.
**Hold a working buffer of $1,500** on top (Part 14.2).

## 9.6 The OpEx governor (Rule 10)
**Rule:** monthly OpEx ≤ **min(team-plan ceiling, max($150, 70% of last month's gross profit))**. Recalculate on the 1st of each month.

| Last month's gross profit | Maximum OpEx this month |
|---|---|
| < $214 | $150 (tools, domain, legal minimum only) |
| $500 | $350 |
| $1,000 | $700 |
| $2,000 | $1,400 |
| $5,000 | $3,500 |
| $10,000 | $7,000 |
| $15,000 | $10,500 |

**Spending priority when the governor allows more:** (1) tools, domain, legal, accounting → (2) reliability/instrumentation (Tech-A/B) contractor → (3) growth and marketing → (4) engineer hires per the team plan (17.3) → (5) founder pay per the ladder (14.3).
**Cash-floor alarm:** if cash < 2 months of (infra + Free budget + OpEx), freeze hiring and Free-window expansion.
**Override rule:** you may exceed the governor only with a written reason, a funded source (grant/prize/investment already in the bank, not promised), and a review date. Promised money is not cash.

## 9.7 Where capital deployment is now defined
The old blueprint's $500 / $5,000 splits are replaced by stage budgets in **Part 11** (how much each stage needs and where it goes), funding sources in **Part 12**, and equity rules in **Part 13**.

---

# 10. INFRASTRUCTURE COST STAGES AND GATES

## 10.1 Stages and monthly cost
| Component | **Lean launch** | **Phase 2 split** | **Phase 3a workers** | **Phase 3b K8s** |
|---|---|---|---|---|
| Compute nodes | VPS $25 | $48 | $180 | (all-in) |
| Load balancer | — | $12 | $24 | (all-in) |
| Database (Supabase) | Pro $25 | Pro + Small compute $36 | Pro + Large compute $110 | (all-in) |
| Redis / rate ledger (Upstash) | ~$5 pay-as-you-go | $20 | $60 | (all-in) |
| Vector memory | free tier | (in Redis line) | $50 | (all-in) |
| Realtime (Pusher) | Sandbox $0 (100 connections) | Startup $49 | Pro $99 | (all-in) |
| CDN / DNS / WAF | Cloudflare free ($0) | $0 | $20 | (all-in) |
| Observability (Sentry, Langfuse) | free tiers, domain ≈ $2 | $40 **[A]** | $60 **[A]** | (all-in) |
| Sandbox (E2B) | Hobby $0 | Hobby $0 | **Pro $150** | (all-in) |
| **Total (planning)** | **$60** | **$205** | **$753** | **$2,600 (±30%, [U])** |
| Old blueprint | $20 | $150 | $499 | $2,310 |

*Corrections vs old blueprint:* Pusher's cheapest paid plan is **$49**, not $20–40; Supabase's free tier pauses after a week idle, so production needs Pro ($25); E2B and Pusher were missing from the cost tables.

## 10.2 Stage gates ("splitting is gated, not scheduled")
Move up a stage when **any** gate fires (the server guide's operational triggers always outrank these user-count proxies):

| From → to | Move when |
|---|---|
| Lean → Phase 2 | Paid users ≥ 100 · **or** Pusher connections > 80 sustained · **or** p95 CPU > 60% · **or** you sign the first annual customer who expects uptime commitments |
| Phase 2 → 3a | Paid users ≥ 500 · **or** sandbox queue delay > 2 min · **or** worker CPU > 70% · **or** Pusher connections > 400 |
| 3a → 3b | Paid users ≥ 1,500 · **or** sustained node utilization > 70% after scaling out · **or** a customer needs isolation guarantees |

**Difference from your server guide:** the guide makes Phase 2 (Basic launch) the first real split. This book launches on the lean stack and splits when a gate fires, because the split costs about **$145 more per month** and needs roughly 25 extra Basic users to pay for itself. If you prefer the guide's sequence, add $145/month from M1 (reduces Year-1 gross profit by about $1.7k).

## 10.3 Capacity alarms
| Resource | Alarm |
|---|---|
| Any LLM provider tokens/min | > 60% of its limit at p95 → request increase or rebalance weights |
| Pusher connections | > 80% of plan cap |
| E2B concurrency | > 15 of 20 on Hobby |
| Supabase | Connection pool > 70% or storage > 6 GB of 8 GB included |
| Upstash | Commands trending above the pay-as-you-go break-even against a fixed plan (fixed plans start at $10) |

---

# 11. CAPITAL PLAN BY STAGE — HOW MUCH MONEY, WHEN, AND EXACTLY WHERE IT GOES

> **The purpose of this Part:** at every stage of the climb from ground to top, you can read (a) how much cash the stage needs, (b) which line items consume it, (c) what must be true before you spend it, and (d) which funding source is meant to pay for it (Part 12). All amounts are USD at 123 BDT/USD. **[A]** = planning estimate; **[V]** = verified figure.

## 11.1 The stage map
| Stage | Illustrative dates* | Roadmap phase | Team | Job of the money |
|---|---|---|---|---|
| **S0 — Foundation** | Sep 2026 → Jun 2027 (10 mo) | Phase 0 | 1 (you) | Finish reliability, paid-key evals, advisor conversation, FBEBC Stage 1 preprint, Seed Fund application (April 2027) |
| **S1 — Pilot & launch prep** | Jul 2027 → Dec 2027 (6 mo) | Phase 1 (Seed Fund pilot **or** BD-funded validation) | 1 (+ security contractor) | Prove real usage; register the company; legal documents; payment rails; security review |
| **Launch** | M0 → M1 (Jan 2028) | Phase 2 start | 1 (+ part-time dev) | One-off launch costs, then billing goes live |
| **S2 — Launch year** | M1–M12 | Phase 2 (Basic + Free window) | 1–2 | Survive the early gross-margin trough; earn the first 120 paid users |
| **S3a — Moderate** | M13–M24 | Phase 3a | 2–4 | Brain (batch) + Moderate tier; infra Phase 3a; first real hires |
| **S3b — Ultimate** | M19–M36 | Phase 3b | 4–8 | Real-time Brain + Ultimate tier; security/DevOps hire; audits; Kubernetes when gated |
| **S4 — Scale** | Year 4+ | Phase 4 | 8–15+ | Enterprise readiness, office, expansion — only if Year 3 delivered |

*Dates are illustrative. Your roadmap makes Basic launch demand-gated; if launch slips, the stage *order* and *sizes* stay, the dates move.

## 11.2 Pre-launch budgets (S0 + S1 + launch one-offs)
| Line item | S0 | S1 | Launch | Notes |
|---|---|---|---|---|
| Tools, subscriptions ($10/mo) | 100 | — | — | GitHub Student Pack covers coding assistance **[V per FBEBC guide]** |
| Domain + DNS (2 years) | 25 | — | — | |
| Paid eval credits (Anthropic, OpenAI, Google, Groq, Mistral) | 100 | — | — | Rule 1: production-grade keys from day one; needed to climb usage tiers |
| Hosting (VPS $25 + Supabase Pro $25 + Upstash ~$5 + tools $20 = $75/mo × 6) | — | 450 | — | Supabase free pauses when idle — not for pilot users |
| Pilot API / search / sandbox (≈100 testers) | — | 150 | — | ≈ $1.50 per tester |
| Tier and Brain evals (Fable / Astra / Sonnet A-B tests) | — | 250 | — | A Deep run costs $0.59–$0.77 |
| ToS + Privacy Policy drafting (lawyer) | — | 150 | — | Non-negotiable before billing (roadmap Part 11) |
| Contractor security review (BDT 50,000) | — | 407 | — | Roadmap: per-user rate/billing enforcement gap is a named risk |
| **Company registration, RJSC (BDT 72,730)** | — | **591** | — | **[V old blueprint]** includes legal retainer, trade licence, TIN/BIN steps |
| Bank + accounting setup | — | 100 | — | Corporate account must be able to receive grants |
| Payment-gateway setup (BDT 15,000) | — | 122 | — | **[V]** one-time aggregator setup (SSLCommerz); confirm per gateway |
| Contingency 15% on S1 | — | 333 | — | |
| International payment rail setup | — | — | 100 | Merchant-of-record / Payoneer-type rail (Part 3.7) |
| Trademark / brand check | — | — | 100 | Roadmap Part 11 |
| Launch content + community | — | — | 300 | Build-in-public, founder story (roadmap Part 10) |
| Anti-abuse tooling (Free tier) | — | — | 50 | Rule 8 |
| Accountant onboarding | — | — | 100 | |
| Launch contingency | — | — | 200 | |
| **Stage total** | **225** | **2,553** | **850** | **Pre-launch total: $3,628** |

### Three budget levels (pick one on purpose)
| Level | Pre-launch cash | What you cut or add | Consequence |
|---|---|---|---|
| **Bare minimum** | **≈ $1,900** | No lawyer (use reviewed templates), no paid contractor review (self-review + community), infra at $55/mo, launch content $200 | Higher legal and security risk; acceptable only for a closed pilot |
| **Recommended** | **$3,628** | The table above | The default for Plan A |
| **Comfortable** | **≈ $5,300** | Recommended + wider security review (BDT 100,000) + lawyer for shareholder/founder agreement + trademark filing + 3-month operating float | Least stressful; best if a grant lands |

## 11.3 Post-launch budgets — where each year's money goes
**Plan B (full team plan, Part 17.3) — every line is a choice you buy early:**
| Category (USD) | Year 1 (S2) | Year 2 (S3a) | Year 3 (S3b) |
|---|---|---|---|
| People (salaries + 10% on-cost) | 4,805 | 26,024 | 46,683 |
| Founder stipend (14.3) | — | 3,902 | 9,756 |
| Marketing | 1,800 | 8,400 | 18,000 |
| Tools, legal, accounting | 2,400 | 4,200 | 7,200 |
| One-offs (Tech-C/E contractor $1,200; pen-test $1,500; security/daemon audit $5,000; Kubernetes migration $2,000) | — | 1,200 | 8,500 |
| Equipment (laptops, BDT 90,000 each) | 732 | 2,927 | 1,463 |
| Office lease (from M25) | — | — | 5,854 |
| **OpEx total (Plan B)** | **9,737** | **46,654** | **97,456** |
| *Plus, from the model, paid by gross margin:* infrastructure | 1,010 | 4,104 | 21,965 |
| Paid-user COGS | 998 | 11,268 | 72,425 |
| Free-tier cost | 955 | 3,702 | 13,115 |
| Payment fees | 241 | 2,274 | 13,559 |

**Plan A (governed)** spends the same categories in the same order but only up to 70% of last month's gross profit: OpEx of **$1,952 / $19,133 / $86,875** in Years 1–3.

## 11.4 How much *outside* money each stage needs (base case, before any grant or investment)
| Stage | Plan A: added need | Plan A: cumulative | Plan B: added need | Plan B: cumulative |
|---|---|---|---|---|
| S0 Foundation | $225 | $225 | $225 | $225 |
| S1 Pilot + launch prep + launch one-offs | $3,403 | $3,628 | $3,403 | $3,628 |
| S2 Launch year (M1–M12) | $584 | **$4,212** | $7,882 | $11,510 |
| S3a (M13–M24) | $0 (self-funding) | $4,212 | $15,413 | $26,923 |
| S3b (M25–M36) | $0 | $4,212 | $968 | **$27,891** |

### Funding targets (what to go and get)
| Target | Amount | Composition |
|---|---|---|
| **Minimum to launch** | **≈ $3,000** | Bare-minimum pre-launch ($1.9k) + launch-year trough ($0.6k) + $0.5k buffer |
| **Plan A target (recommended)** | **≈ $5,700 → round to $6,000** | $4,212 base need + **$1,500 working buffer** |
| **Plan A, conservative revenue** | ≈ $6,300 | $4,824 + buffer |
| **Plan B target** | **≈ $29,400 → round to $30,000** | $27,891 + $1,500 buffer |
| **Plan B, conservative revenue** | ≈ $61,000 | $59,824 + buffer — this is the number that says "do not run Plan B without a backup" |
| **Plan B, heavy use** | ≈ $38,700 | $37,247 + buffer |

**Interpretation:** the first **$6,000** decides whether you launch cleanly. A single national-grant win (Tk 10 lakh ≈ $8,130) covers it entirely; the Aspire Seed Fund ($500) covers 8% of it; the CAA ($5,000) covers 83%.

## 11.5 The Master Spend Ledger (when, how much, on what, and the trigger)
| # | When | Item | Amount | Trigger — spend only when… |
|---|---|---|---|---|
| 1 | S0 M1 | Domain, DNS, evals credits | $125 | Start of Phase 0 |
| 2 | S0 monthly | Tools | $10/mo | — |
| 3 | S1 M1 | Hosting on paid Supabase + VPS | $75/mo | Pilot users exist |
| 4 | S1 | Lawyer: ToS + Privacy | $150 | Before any external user pays |
| 5 | S1 | **Company registration (RJSC + trade licence + TIN/BIN)** | $591 | Before grants are paid into a company account, and before billing |
| 6 | S1 | Security contractor review | $407 | Before public billing |
| 7 | S1 | Payment-gateway setup | $122 | Registration complete |
| 8 | S1 | Tier + Brain evals | $250 | Tech-A cost logging live |
| 9 | Launch | Rails, brand check, content, anti-abuse, accountant | $850 | Gate: all Part 22 launch items closed |
| 10 | M1–M6 | Lean infra | $60/mo | — |
| 11 | When paid ≥ 100 | Phase 2 split infra | $205/mo | Gate 10.2 |
| 12 | M7 (or GP ≥ $447/mo) | First junior hire (BDT 35,000 + 10%) | $313/mo + $732 laptop | Governor allows; support/backlog visibly rising |
| 13 | M13 | Tech-C/E contractor | $1,200 | Moderate demand gates cleared (roadmap 3.5/3.6) |
| 14 | M13 | Mid engineer + growth specialist | $671 + $447/mo (+ 2 laptops $1,464) | Governor allows the full rung: team cost ≈ $2,806/mo → GP ≥ ≈ $4,000/mo (single hires earlier if GP allows) |
| 15 | When paid ≥ 500 | Phase 3a infra (E2B Pro $150 included) | $753/mo | Gate 10.2 |
| 16 | M19 | Senior DevOps/security + support associate | $1,252 + $224/mo (+ laptops) | Ultimate gates cleared; daemon-review prerequisites; full rung ≈ $4,282/mo → GP ≥ ≈ $6,100/mo |
| 17 | M28 | Penetration test | $1,500 | Before Ultimate real-time Brain traffic scales |
| 18 | M30 | Security / daemon audit (external) **[A]** | $5,000 | Only if a tier's revenue can fund it (roadmap Part 13) |
| 19 | When paid ≥ 1,500 | Kubernetes migration + Phase 3b infra | $2,000 + $2,600/mo | Gate 10.2 |
| 20 | M25 | Office lease + second mid + junior (17.4) | $488 + $671 + $313/mo | GP ≥ $10k/mo and reserve target met (14.2) |

## 11.6 Year 4+ (S4) capital menu — decisions, not promises
| Option | Cost **[A]** | Do it only if |
|---|---|---|
| Enterprise-readiness work (security questionnaire pack, audit-lite, DPA templates) | $10,000–$30,000 | ≥ 3 named enterprise prospects with budget |
| Team from 8 to 12–15 | +$4,000–$7,000/month | 6-month payroll reserve exists |
| Office fit-out (leased) | BDT 300,000–600,000 ($2.4k–$4.9k) | Team ≥ 8, lease ≥ 3 years, reserve target met |
| Outbound sales hire | $600–$1,200/month | Repeatable inbound conversion proven |
| Equity round to accelerate (Part 13) | Raise $100k–$500k | Year-3 gross profit ≥ $150k, growth engine proven, dilution rules satisfied |

---

# 12. FUNDING SOURCES AND STRATEGY — WHERE THE MONEY COMES FROM

## 12.1 Why prize money and grants come first (the principle behind this Part)
Prize money, grants and credits are **non-dilutive**: they add cash without giving away ownership. Early in a company's life, equity is priced at its lowest (little proof, high risk), so every point of ownership sold early is sold cheaply and can never be sold again at the later, higher price (Part 13 quantifies this). The funding ladder is therefore:

1. **Credits and free programs** (cost nothing, reduce spending)
2. **Small prizes and hackathons** (cash, plus public proof)
3. **Grants and equity-free competitions** (larger cash, competitive)
4. **Revenue** (Part 9; the engine from Plan A onward)
5. **Founder / family funds** (bridge; keep documented, ideally as an unsecured loan you can repay first from profits)
6. **Equity or convertible instruments** — only when a written test in 13.2 is passed

## 12.2 Source catalogue
Probabilities are **[A]** planning guesses, not forecasts. Amounts marked **[V]** come from dated sources (Appendix B); program status can change, so re-verify before applying.

### A. Non-dilutive cash
| Source | Size | Window / timing | Requirements & notes | P(win) per attempt **[A]** |
|---|---|---|---|---|
| **Aspire Seed Fund** | $200–500 | 2026 windows: Apr 17–28 and Aug 21–Sep 2 **[V roadmap]**; your plan: April 2027 | Alumni; 9-week structured program; a quality application matters more than speed (roadmap 5.2) | 12% |
| **Aspire Community Action Award (CAA)** | **$5,000** | Jul 1–15 each year **[V roadmap]** | Needs an MVP / proof of concept "signaling clear readiness for growth"; Branch B → Jul 2027, Branch A → Jul 2028 (= launch month **M7**) | 6% |
| **Aspire Conference Grant** | $500–1,000 | Mar 25–Apr 1 and Aug 3–10 **[V roadmap]** | Requires acceptance to *present* — the FBEBC paper (Part 18) is the route | 25% *once a paper is accepted* |
| **National startup grants (iDEA pre-seed, Bangabandhu Innovation Grant–type)** | **Tk 10 lakh (≈ $8,130)** per grantee; top winner up to Tk 1 crore in the 2023 edition | Annual cycle historically (BIG 2023 applications closed 22 April) | 179 startups had been nominated for Tk 10 lakh pre-seed grants by 2021; BIG 2021 gave Tk 10 lakh each to 36 startups. **Program names and status changed after 2024 — confirm the current ICT Division / Startup Bangladesh scheme before planning on it** **[V historical, U current]** | 8% |
| **Corporate ICT incubator competitions (Huawei-type)** | Tk 5 lakh + $125K cloud credit (champion); Tk 3 lakh / Tk 1 lakh + $80K credit (runners-up) | 2022 edition **[V]** | Idea-stage and early-stage groups; often with ICT Division and Startup Bangladesh | 5% |
| **Entrepreneurship World Cup (GEN + Monsha'at)** | Share of **$1M equity-free** pool; 12 prizes across idea / early / growth / AI tracks | 2026 applications closed May 2026 (annual; watch for 2027) **[V]** | Top 250 get a virtual bootcamp; top 100 finalists compete live | 2% |
| **AI/agent hackathons** (UiPath AgentHack $50K pool, GitLab $20K, USAII $15K…) | $500–$5,000 realistic per win | Continuous | Build in public; each entry produces a demo and press-kit asset | 10% per entry |
| **Startup Bangladesh Ltd / Bangladesh Bank startup funds** | FY2026-27 budget proposes a **Tk 500 crore** startup fund (Tk 200 crore government + Tk 300 crore Bangladesh Bank CSR); an earlier Tk 900 crore fund was announced April 2025 | Follows Finance Act cycle | Mostly equity or bank-intermediated finance, not prizes **[V proposal / U rules]** | see equity table |

### B. In-kind credits (reduce cash spending)
| Program | Size | Gate | Fit for MiniMe |
|---|---|---|---|
| **Microsoft for Startups Founders Hub** | up to **$150K** Azure credits | Milestone path needs no investor referral; reviewed in ~3 business days | Azure Speech (TTS) and Azure OpenAI — check which OpenAI models are available on Azure before relying on it **[U]** |
| **AWS Activate — Founders** | $1,000–$5,000 | Self-serve, no affiliation | Small; useful for non-critical storage/CDN |
| **Google for Startups Cloud — Start tier** | up to **$2,000** | Early stage, not yet equity-funded | Gemini API credit fit is **[U]** — confirm Gemini API vs Vertex coverage |
| Google Scale / AI tier | $200K / $350K | Needs institutional equity funding | Later, after an equity round |
| **Anthropic startup program** | Not published | In practice credits require institutional equity funding; accepted startups get highest rate limits; credits cannot be used on Bedrock/Vertex | Apply after first funding; ask for rate limits early **[V]** |
| **OpenAI for Startups** | Not published | API credits need a VC partner referral | Later |
| **Mistral** | $10/month API credit on the free plan; the "Mistralship" startup program page is defunct | None | Dev only |
| **Cloudflare / Supabase / others** | up to $250K–350K (Cloudflare, partner-gated tiers); Supabase up to $25K **[U]** | Tier-dependent | Infra credits reduce Phase 2/3a hosting costs |
| GitHub Student Pack | Copilot and tools | Student status | Already in your FBEBC plan |

Rule: credits usually **expire in about 12 months with no cash value** — activate them only when you will actually consume them.

### C. Equity and quasi-equity (use only after 13.2's test)
| Source | Size | Dilution | Notes |
|---|---|---|---|
| **Bangladesh Angels Network (BAN)** | $50K–$500K reported (up to $1M via partners) | ≈ 10–20% **[A]** | Pre-seed to seed; wants a passionate team and proof of concept (roadmap 5.4) |
| **Startup Bangladesh Ltd (SBL)** | Sep 2024–Jan 2025: BDT 9.025 crore across nine startups (≈ BDT 1 crore ≈ $81K each) **[V]** | ≈ 10–20% **[A]** | Government-backed. **Governance risk:** under the previous government it reportedly denied funding to founders not close to the government, and cancelled a Tk 5 crore proposal for 10 Minute School in July 2024 **[V]** — never make SBL your only path |
| **BSIC / Onkur, SBK Tech Ventures** | SBK: $1M minimum ticket **[V]**; Onkur: bank-backed VC | 15–25% **[A]** | Traction-proven only; not for the pre-revenue stage |
| **Advisor's company network (Branch B)** | Unknown; needs a written dollar commitment | Negotiable | Convert to a term sheet or named pilot with a start date by the end-2026 checkpoint (roadmap 5.3) |
| **Offshore angels via a Delaware/Singapore holdco (SAFE)** | $50K–$250K | ≈ 3–10% at a sensible cap **[A]** | Needs a legal-structure decision (13.3) |
| **OpenVC** | Free investor database, not a fund | — | Use for targeted outreach |

### D. Debt
Not recommended before Year 2. Bank startup lines typically require collateral; Bangladesh Bank's startup-financing circular (2025) defines which companies qualify **[U]**. Consider only for equipment or a short revenue-backed working-capital gap, never to fund losses.

## 12.3 The Bangladesh market you are raising in (LightCastle / Startup Bangladesh data)
| Metric | Value |
|---|---|
| Total startup funding, H1 2026 | **$6M**, 6 deals, 4 companies (−95% year on year) |
| Average ticket, H1 2026 | **$1M**; top deal $2M (Seed and grant) |
| Share from global investors | **100%** (0% domestic) |
| Early-stage share of H1 2026 capital | 90% |
| Total 2025 | $124M in 12 deals; $110M from one M&A deal; ≈ $1M average excluding it; local investors < $1M across three deals |
| 2013 → H1 2026 | $1.1B total; **80% late-stage**; early stage (grant, seed, pre-A) = $223M across 381 deals ≈ **$0.6M average** |
| Global context | $510B global venture funding in H1 2026; AI = 74% |

**What this means for you:** domestic equity is scarce; ticket sizes are small; the funded companies are mostly beyond seed. A pre-revenue solo founder should expect **grants, credits, revenue and small angel checks**, and should treat a $1M round as a Year-3+ event.

## 12.4 Pipeline math — how many shots to take
Per-cycle expected cash from the five non-dilutive cash sources (Seed Fund, CAA, national grant, global cup, hackathon) is only **≈ $1,400**, and the chance of winning at least one is **≈ 33%**. That is why you run a *portfolio*:

| Applications submitted (avg. 7% each, independent) | P(at least one win) | Expected cash (avg award $5.1k) |
|---|---|---|
| 6 | 35% | ≈ $2,200 |
| 12 | **58%** | **≈ $4,300** |
| 20 | 77% | ≈ $7,200 |

**Rule:** submit at least **12 credible applications per 12 months** before launch (six of them can be small hackathons). Expected cash still falls short of the $6,000 Plan A target, so the funding plan is never "prizes only" — it is **prizes + credits + a founder bridge + revenue** (12.6).

## 12.5 Rolling calendar (adjust to each year's published dates)
| Month | Action |
|---|---|
| Jan | Update application kit (12.7); collect Tech-A cost data; renew credits applications |
| Mar | Aspire Conference Grant window (if a paper is accepted); EWC-type global cups open — check |
| **Apr** | **Aspire Seed Fund application** (roadmap 5.2); national grant cycle usually opens Mar–Apr |
| May | Global cup deadlines; hackathon calendar review |
| **Jul** | **Aspire CAA window (Jul 1–15)** |
| Aug | Aspire Seed Fund round 2 (backup); Conference Grant round 2 |
| Sep–Dec | Hackathons; end-of-year checkpoint (roadmap 5.3): is the BD funding conversation converting into a written dollar commitment? |

## 12.6 The funding stack that gets you to launch (recommended)
| Layer | Target | Source order |
|---|---|---|
| 1 | **$6,000 (Plan A target)** | Founder bridge $1,500–$2,000 **+** any of: Seed Fund $500, national grant $8,130, hackathon prizes, CAA $5,000 |
| 2 | Credits worth $5k–$25k | Founders Hub, AWS Founders, Google Start — applied for in S0 |
| 3 | Revenue | Plan A covers itself after the trough |
| 4 | Optional accelerant $25k–$30k | Only if you choose **Plan B** — see 16.3 for the fallback if it does not arrive |

## 12.7 Application kit (build once, reuse everywhere)
1. **One-page overview** and **2-minute demo video** of the multi-agent build flow.
2. **Traction pack:** pilot metrics; Free→paid conversion; cost per task (Tech-A); gross margin by plan (Part 8).
3. **Use-of-funds table** — copy the relevant rows of the Master Spend Ledger (11.5) so every grant application matches your real plan.
4. **Cap table** and equity rules (Part 13) — funders check for dead equity and control.
5. **FBEBC preprint link** (Part 18) — research credibility.
6. **Risk plan** — Part 16 fallback tree, condensed to one page.

## 12.8 Sponsors, partners and non-cash support
- **Universities** (BUET, DU, NSU, BRAC, SUST, RUET, RU): Free-tier partnerships and hackathon sponsorship in exchange for co-branding and testimonials; cheapest acquisition channel.
- **Rajshahi Hi-Tech Park incubation** (Sheikh Kamal IT Incubator and Training Centre): incubation offered to startups for one year at a listed rent of **Tk 5 + Tk 5 service charge per sq ft per month** (BHTPA page; confirm current rate and eligibility) **[V/U]**; the park lists tax incentives for park companies **[U]**.
- **Telecom and wallet partners** (GP Accelerator-type programs, bKash/Nagad): co-marketing and payment-integration support.
- **Advisor**: warm introductions typically beat cold applications for speed (roadmap 5.4).

---

# 13. EQUITY, DILUTION, VALUATION AND NET WORTH

> **Your instinct is right, and this Part puts numbers on it:** equity sold early is sold at the lowest price it will ever have, and it can never be resold at the later, higher price. A company that sells too much too soon also becomes hard to invest in later (little left for new investors, unclear control, "dead" holders). Prize money, grants and revenue keep ownership whole while the price of your equity climbs.

## 13.1 The price of early equity (computed from the base-case model)
Base-case ARR: **$98.8k at M24** and **$536.4k at M36**. Value of the stake an investor buys, at 3× ARR (bootstrapped-SaaS range 2.5–4× for sub-$1M ARR **[V]**), ignoring later dilution:

| Raise | Post-money valuation | Stake sold | Stake worth at M24 | Stake worth at M36 (3× ARR) | Investor's multiple at M36 | At M36 with 5× ARR |
|---|---|---|---|---|---|---|
| $5,000 | $50,000 | 10.0% | $29.6k | **$160.9k** | **32×** | $268.2k |
| $25,000 | $100,000 | **25.0%** | $74.1k | **$402.3k** | **16×** | $670.5k |
| $25,000 | $250,000 | 10.0% | $29.6k | $160.9k | 6.4× | $268.2k |
| $100,000 | $500,000 | 20.0% | $59.3k | $321.8k | 3.2× | $536.4k |
| $100,000 | $1,000,000 | 10.0% | $29.6k | $160.9k | 1.6× | $268.2k |
| $100,000 | $3,000,000 | 3.3% | $9.9k | $53.6k | 0.5× | $89.4k |
| $100,000 | $5,000,000 (old blueprint cap) | 2.0% | $5.9k | $32.2k | 0.3× | $53.6k |

**Reading it:** selling 25% for $25,000 in the pre-revenue stage would hand the buyer about **$402,000** of your company by Month 36 — sixteen times the cash you received. The same $25,000, won as a prize, costs nothing. At the other extreme, the old blueprint's $5M cap on $100k is a bargain for the founder, but nothing suggests a pre-revenue, solo, Bangladesh-based company will find such a price: Bangladeshi early-stage deals average about **$0.6M in total ticket** (Part 12.3), and global pre-seed medians ($5.87M valuation, $10M SAFE caps) come from US-dominated data and are **not your comparables**. If revenue comes in at half the base case, each stake above is worth half as much — but **you cannot know in advance which case you are in, which is exactly why you sell late, small and priced on proof.**

## 13.2 The Equity Rules (all must hold before you sell any equity)
| # | Rule | Threshold |
|---|---|---|
| E1 | **Need** | Plan A cannot fund a specific growth step, **and** at least 12 non-dilutive applications were submitted over the prior 12 months (12.4) |
| E2 | **Engine** | ≥ 200 paying users **or** MRR ≥ $2,000, with ≥ 6 months of retention data and typical gross margin ≥ 65% |
| E3 | **Dilution caps** | First outside round ≤ **15%**; any later round before Series A ≤ **20%**; cumulative dilution before Series A including the option pool ≤ **35%**; founder(s) ≥ **60%** after the seed round |
| E4 | **Price** | Post-money ≥ max(4× trailing ARR, 40× monthly gross profit). Below that, wait or use Plan A |
| E5 | **Terms** | No board seat or veto over budget/hiring before Series A; liquidation preference ≤ 1× non-participating; broad-based weighted-average anti-dilution only; no redemption or ratchet; information rights limited to quarterly updates |
| E6 | **Use of funds** | A written ledger (like 11.5) with milestones and the KPI that the *next* round will test |
| E7 | **Structure** | Legally enforceable in your structure (13.3) before money moves |
| E8 | **Investor value** | The investor brings named customers, distribution or expertise beyond cash; take two references |
| E9 | **Bundling** | Several small angels come in through **one SPV** (one line on the cap table) |
| E10 | **No Plan B on equity alone** | Never sell equity to fund Plan B without a written Plan A fallback (16.3) |

## 13.3 Legal structure — what a Bangladeshi company can and cannot sign
| Question | Finding (sources in Appendix B) |
|---|---|
| Can a Bangladeshi private limited company issue a **SAFE or convertible note**? | **No statutory recognition** under the Companies Act 1994; such instruments are treated as contracts, with enforcement concerns; most local deals are priced equity, which means lengthy valuation negotiation **[V]** |
| Can it hold a Stripe account? | No; the standard workaround is a foreign entity **[V]** |
| Can a foreign buyer acquire it? | Only with prior Bangladesh Bank approval on transfer of control **[V]** |
| Can you form a foreign entity? | Bangladesh Bank's FEID Circular No. 02 (27 March 2025) gives general permission for startups operating under 10 years, and individuals, to remit up to **USD 10,000** from internal (not borrowed) funds to form one foreign legal entity; share swaps can also be considered **[V]** |
| Startup tax and VAT regime | See 14.6 |

**Structures, in the order you should consider them:**
| Option | When it fits | Trade-off |
|---|---|---|
| **1. Stay a Bangladesh Pvt Ltd; priced ordinary shares to Bangladeshi investors (SBL, BAN)** | Local angel or SBL cheque; no foreign investor yet | Valuation negotiation; slower; no SAFE; limited foreign-investor appetite |
| **2. Offshore holding company (Singapore or Delaware) owning the Bangladesh company (a "flip")** | A foreign investor with a **signed term sheet** requires it, or you need Stripe/merchant access worth more than the cost | Legal, tax and compliance cost **[U: obtain quotes]**; needs Bangladesh Bank permission for outward investment (use the USD 10,000 general permission where it fits); must be done cleanly with IP assignment |
| **3. Hybrid: local company now, flip later** | Default plan | Costs more if delayed until investors appear — but pre-flipping without money on the table wastes cash you do not have |

**Rule:** do **not** flip in advance. Keep IP assigned in writing to the entity that will be flipped, keep a clean cap table, and revisit at Decision Point D3 (16.2).

## 13.4 How to value MiniMe at each stage
Use **revenue multiples appropriate to your size**, not US venture headlines.

| Evidence (2026) | Range |
|---|---|
| Bootstrapped SaaS with **< $1M ARR** (Acquire.com-type data) | **2.5–4× annual revenue**, or 4–6× seller earnings if founder-dependent; the 600+ small-listing average is 2.6× revenue |
| Micro-SaaS under $1M ARR | 2.5–4.5× SDE; $500k–$1M ARR: 2–3.5× ARR |
| $1–5M ARR with healthy retention | 4–6× ARR |
| US median seed post-money (Carta, Q4 2025) | $24M — driven by US/AI outliers; **not applicable** |

**MiniMe valuation ranges (2× / 3× / 5× ARR):**
| Month | Base ARR | Base valuation | Conservative ARR | Conservative valuation |
|---|---|---|---|---|
| M12 | $11.0k | $22k / $33k / $55k | $5.5k | $11k / $17k / $28k |
| M24 | $98.8k | $198k / $296k / $494k | $49.4k | $99k / $148k / $247k |
| M36 | $536.4k | **$1.07M / $1.61M / $2.68M** | $268.2k | $536k / $805k / $1.34M |

Pre-revenue, do not quote a valuation; say what you are raising for and what it lets you prove. **These are planning ranges, not appraisals; they exclude the founder's uncompensated labour.**

## 13.5 Ownership ladders — what each path leaves the founder holding
Today the cap table is **100% founder** (your roadmap assumes a solo founder; the old blueprint assumed a 55/45 co-founder split — decide, and if a co-founder joins, use 4-year vesting with a 1-year cliff and written roles). Typical dilution per priced round (Carta): about **19.5% at seed, 18% at Series A, 14% at B, 10% at C**; software founders end near **37.5% after Series A**, and stacked SAFEs quietly take another 15–25 points before institutions arrive **[V]**.

| Step | **Clean (recommended)** | **BD angel path** | **Offshore SAFE path** | **Early-heavy (avoid)** |
|---|---|---|---|---|
| Start | 100.0% | 100.0% | 100.0% | 100.0% |
| First outside money | — | BD angel 12% at M9 → 88.0% | SAFE 3.3% ($100k @ $3M cap) → 96.7% | 25% sold pre-launch → 75.0% |
| Option pool (10%) at first equity-eligible hire | 90.0% | 79.2% | 87.0% | 67.5% |
| Seed round (~19.5%) | 72.4% | 63.8% | 70.0% | 54.3% |
| Series A (~18% + 3% pool top-up) | **57.2%** | 50.4% | 55.3% | **42.9%** |

**Difference between clean and early-heavy after Series A: 14.3 points of the company** — about **$230k of the M36 base valuation ($1.61M × 14.3%)**, before any Series A step-up.

### The old blueprint's cap table — errors to correct
1. Assumes a **co-founder** (55/45) while the roadmap is solo.
2. Assumes a **SAFE**, which a Bangladeshi Pvt Ltd cannot directly issue (13.3).
3. Uses a **$5M cap for $100k** — a US-median-style price with no basis for a pre-revenue Bangladeshi startup.
4. Series A row: $2.5M at a $25M post-money is **10%**, but the table shows **16%** (and the "voting control" line does not reconcile with the ownership rows).
5. Adds an option pool at the seed stage but no rule for vesting or who may receive options.

## 13.6 Net worth versus paper value
Two different numbers exist; keep both in your head:
- **Book equity** = cash (+ equipment) − liabilities. This is real and shows up in the statements of Part 15.
- **Paper value** = valuation × your ownership. This becomes real only when you sell shares, sell the company, or take dividends.
Neither includes your uncompensated labour. Part 15.3 shows both at each stage.

## 13.7 Cap-table hygiene (so you *can* sell later)
- Keep one clean, current cap table; update after every issuance; store signed share certificates and the RJSC filings.
- Sign IP-assignment and confidentiality agreements with every contributor, contractor and employee from day one.
- Vesting for every equity holder; no unvested promises by email or chat.
- ESOP written rules: eligible roles, vesting, exercise, leaver terms — legality and tax of employee options in Bangladesh **[U]** must be confirmed with counsel; a phantom-share or profit-bonus plan can substitute.
- Avoid dead equity: no advisors with large stakes and no obligations; use small, vesting advisor grants (≤ 0.25–0.5%) only with concrete deliverables **[A]**.

## 13.8 Exit and liquidity paths
| Path | When it makes sense | Note |
|---|---|---|
| **Stay profitable and pay dividends** | Plan A results hold; no need for outside capital | Best for founder ownership; see Part 14 |
| **Acquisition by a strategic buyer** | Year 3+ with real revenue; dev-tool, ed-tech or AI-platform buyers | Foreign buyer needs Bangladesh Bank approval; small-SaaS marketplace multiples 2.5–4× |
| **Priced equity round to scale** | Growth engine proven and E1–E10 satisfied | Expect the ladders in 13.5 |
| **Secondary sale of a small founder stake** | After a priced round | Negotiate at the round; investors often permit 5–10% |

---

# 14. PROFIT, RESERVES AND DISTRIBUTION POLICY — WHEN YOU MAY TAKE MONEY OUT

> In the early phases there is no profit to take, and the first profits must go back into the business. This Part sets **when** you may pay yourself, **how much** to keep in reserve, and **what share of profit goes where** at each stage.

## 14.1 Definitions used in this book
| Term | Meaning |
|---|---|
| **Gross profit (GP)** | Revenue − paid-user COGS − Free-tier cost − payment fees − infrastructure |
| **OpEx** | People, marketing, tools/legal/accounting, one-offs, equipment, office (Part 11.3) |
| **EBITDA** | GP − OpEx |
| **Fixed monthly outflow** | Infrastructure + Free-tier budget + OpEx (the money that leaves even if revenue stalls) |
| **Operating reserve** | Cash you refuse to spend, sized in months of fixed outflow (14.2) |
| **Distributable profit** | EBITDA after the tax reserve, after the reserve target is met (14.4) |

## 14.2 Reserves — what to hold and how big
| Reserve | Target | Purpose |
|---|---|---|
| **Working buffer** | **$1,500 minimum**, always | Covers the launch-year trough and payment delays |
| **Operating reserve** | **3 months** of fixed outflow until M12 · **4 months** M13–M24 · **6 months** M25–M36 · **9 months** from Year 4 or once payroll ≥ 8 people | Survive a revenue stall, a provider shock or a slow-paying rail |
| **Provider float** | ≈ 1 month of forecast paid-user COGS held as prepaid credit, split across at least two providers | Insurance against outages and price changes; never more than one month with a single vendor |
| **Tax reserve** | **15% of positive EBITDA** **[A placeholder]** | Set aside until an accountant fixes the real rate (14.6) |
| **Resilience fund** | 10% of distributable profit once the operating reserve is met | Funds the fallback plans in Part 16 |

**Reserve targets versus the base-case cash path (Plan A, founder capital $5,700):**
| Month | Fixed outflow / month | Reserve target | Cash | Gap to target |
|---|---|---|---|---|
| M12 | $575 | 3 × = $1,726 | $1,975 | met (by $249) |
| M24 | $4,291 | 4 × = $17,162 | $14,798 | **short by $2,364** |
| M36 | $11,506 | 6 × = $69,036 | $142,698 | exceeded by $73,662 |

**Consequence:** until roughly M24 you are at or below target, so **no distributions and no founder dividends**. After M24 the target is crossed and the waterfall (14.4) applies.

## 14.3 The founder pay ladder
Pay comes from the OpEx allowance in the governor (9.6). Each rung requires **both** the profit condition **and** the reserve condition for three consecutive months.

| Rung | Founder stipend (BDT/month) | Condition (GP) | Condition (reserve / cash) | Base-case timing **[A]** |
|---|---|---|---|---|
| R0 | 0 | — | — | until ≈ M19 |
| **R1** | 15,000 (≈ $122) | GP ≥ $1,500 for 3 months | Cash ≥ 2 × monthly fixed outflow | ≈ M19 |
| **R2** | 40,000 (≈ $325) | GP ≥ $4,000 for 3 months | Reserve ≥ 3 months | ≈ M25 |
| **R3** | 100,000 (≈ $813) | GP ≥ $10,000 for 3 months | Reserve ≥ target for the period | ≈ M30 |
| **R4** | 140,000 (senior-engineer level) **+ dividends** | GP ≥ $25,000 for 6 months | Reserve ≥ 6 months, **and** margin gates green | ≈ M40 (Year 4) |

*Plan B* pays R2 from M13 and R3 from M25 on schedule (Part 17.3); that is a cost you accept when you choose Plan B.
**Personal reserve:** separately from company cash, hold personal funds for six months of your own living costs before relying on a company stipend; document the source of any founder bridge loan (16.2).

## 14.4 The profit waterfall
Apply on the 1st of each month to the previous month's EBITDA after the tax reserve.

| Stage | Condition | Reserve | Reinvest (product, hires, marketing, FBEBC, infra step-ups) | Founder / owners | Resilience fund | Provider float |
|---|---|---|---|---|---|---|
| **1. Build the base** | Operating reserve < 3 months | **100%** | 0% | 0% | 0% | 0% |
| **2. Reach target** | 3 months ≤ reserve < period target | **60%** | 30% | 0% | 0% | 10% |
| **3. Distribute** | Reserve ≥ period target; trailing-6-month EBITDA positive; gates green | 25% | **35%** | **30%** | 10% | — |
| **4. Mature** | Year 4+; reserve ≥ 9 months | 15% | 40% | **35%** | 10% | — |

**Illustration (Year 3, base case, Plan A):** EBITDA $127,900 → tax reserve 15% = $19,185 → distributable $108,715. Because the reserve target is crossed late in the year, most of it feeds stages 1–2 (reserve and reinvestment); if the whole amount were in stage 3 it would split $38.1k reinvest · $32.6k founder · $27.2k reserve · $10.9k resilience. In practice the **first meaningful founder distribution is a Year-4 event** in the base case.

**Never distribute when any of these is true:** a margin gate (0.4) is red; runway < 6 months; provider concentration alarm active; unpaid taxes or payables; unresolved grant conditions; **accumulated losses exist** (dividends may only come from profits — confirm the legal rule with your accountant **[U]**).

## 14.5 Cash management
1. **Two currencies, two purposes.** Keep USD receipts in an **ERQ/foreign-currency account** (the old blueprint lists retention of up to 70% of export proceeds in USD **[V old]**) and pay USD vendors from it; keep BDT for payroll and rent.
2. **Three months of BDT payroll stays in BDT** once you have staff.
3. **Two banks**, so one account freeze does not stop payroll or vendor payments.
4. **Virtual or limited cards** per vendor, with monthly spend limits; reconcile provider invoices to the internal cost ledger monthly.
5. **Prepaid provider balances** ≤ 1 month per vendor (the provider float in 14.2 is the deliberate exception).
6. **Grant money is segregated** and tracked against its approved use-of-funds table; never mix it with revenue.
7. **FX:** the taka has been stable at about 121–123 per USD over the last year **[V]**; costs are mostly USD and revenue partly BDT, so a depreciation hurts margins — the stress case (FX 135) shows the effect (8.5).

## 14.6 Tax, VAT and compliance — verify each item with an accountant
| Item | Finding | Effect on this book |
|---|---|---|
| **Startup VAT exemption (SRO 147, gazetted 7 June 2026)** | NBR-registered startups are exempt from VAT on local supplies, **on imported services**, and on premises rent, from **1 July 2026 to 30 June 2035** **[V]** | Register as an NBR startup **before** paying foreign vendors |
| **Imported-service VAT** | Finance Act 2026 brings all imported services into a **15% reverse-charge** net **[V]** | Without startup registration, every foreign API/SaaS invoice (Anthropic, OpenAI, Google, Groq, Tavily, E2B, Azure…) attracts up to 15% VAT |
| **Startup tax regime** | Losses may be carried forward **nine years**; the FY2026-27 budget proposes **zero turnover tax** for startups and technology businesses **[V proposal — confirm enactment]** | Early losses shield later profits; pay no turnover tax while registered |
| **Corporate income tax** | Rate and any ICT/hi-tech-park exemption not verified here | 15% of positive EBITDA is set aside as a placeholder |
| **BIN and banking** | The Finance Act ties the BIN to everyday banking and business activity; VAT returns move from monthly to quarterly **[V]** | Obtain the BIN during company registration; calendar the quarterly filings |
| **Old assumption "software is 100% VAT-exempt"** | Outdated | Removed |

**What happens if you are *not* registered as a startup (imported-service VAT adds 15% to all foreign vendor costs):**
| Plan | COGS at cap | As % of local price (rule ≤ 45%) | Gross margin at cap (local) |
|---|---|---|---|
| Basic | $3.16 | 43.2% ✔ | 54.3% (was 59.9%) |
| Moderate | $12.05 | **49.4% ✘** | 48.1% (was 54.5%) |
| Ultimate | $32.35 | **46.8% ✘** | 50.7% (was 56.8%) |

Two of the three plans would break Golden Rule 5. **Startup registration is therefore a cost-control action, not paperwork.**

## 14.7 Grant, prize and credit accounting
- Record grants as income (or deferred income) **when their conditions are met** **[U: accounting treatment; confirm]**; prize money may be taxable — ask before spending it.
- Keep every receipt against the use-of-funds table; file the grantor's report on time; never spend grant money on items outside the approved list.
- If any funder attaches equity, revenue-share or reporting terms, get them **in writing** before accepting (roadmap Part 11).
- Track credits as non-cash: log the dollar value consumed monthly so the Rulebook's COGS is honest even when credits pay the bill.

## 14.8 "When can I…?" — quick answers (base case, Plan A)
| Question | Answer |
|---|---|
| When can I pay myself? | First stipend ≈ **M19** (BDT 15,000); meaningful pay ≈ **M25–M30** |
| When can I take profit out? | Not before the reserve target is met (≈ M24+) and rung R4 (≈ M40); until then profit is reinvested |
| What share of profit is reserved? | **100%** until 3 months of reserve, then **60%**, then **25%**, then **15%** (14.4) |
| When do I hire? | When the governor allows the cost **and** a measured strain exists (roadmap Part 8) |
| When do I buy or build an office? | Not before Year 4 and the conditions in 17.8 |

---

# 15. FINANCIAL STATEMENTS BY STAGE

*Reference path: **Plan A**, founder capital of $5,700 injected at the start of S0 (the $4,212 base-case gap plus the $1,500 buffer), no outside equity, no grants. Base-case revenue. All figures in USD. Pre-tax except where stated.*

## 15.1 Income statement by stage
| | S0 (10 mo) | S1 + launch one-offs | Year 1 (M1–12) | Year 2 | Year 3 |
|---|---|---|---|---|---|
| Revenue | 0 | 0 | 5,058 | 53,304 | 335,840 |
| Direct costs (paid COGS + Free + fees + infra) | 0 | 0 | (3,203) | (21,348) | (121,064) |
| **Gross profit** | 0 | 0 | **1,855** | **31,956** | **214,776** |
| OpEx (pre-launch spend counted here) | (225) | (3,403) | (1,952) | (19,133) | (86,875) |
| **EBITDA** | **(225)** | **(3,403)** | **(97)** | **12,823** | **127,901** |
| Tax reserve (15% of positive EBITDA) | — | — | — | (1,924) | (19,185) |
| **Cash at end of stage** | **5,475** | **2,072** | **1,975** | **14,798** | **142,698** |

## 15.2 Balance sheet at stage ends
| | End S0 | Launch (M0) | M12 | M24 | M36 |
|---|---|---|---|---|---|
| **Cash** | 5,475 | 2,072 | 1,975 | 14,798 | 142,698 |
| Equipment (laptops expensed) | 0 | 0 | 0 | 0 | 0 |
| **Total assets** | **5,475** | **2,072** | **1,975** | **14,798** | **142,698** |
| Tax payable (provision) | 0 | 0 | 0 | 1,924 | 21,109 |
| Deferred revenue (annual plans) | not modelled | not modelled | not modelled | not modelled | not modelled |
| **Paid-in capital (founder)** | 5,700 | 5,700 | 5,700 | 5,700 | 5,700 |
| Retained earnings after tax provision | (225) | (3,628) | (3,725) | 7,174 | 115,889 |
| **Total equity (book net worth)** | **5,475** | **2,072** | **1,975** | **12,874** | **121,589** |

## 15.3 Book net worth versus paper value
| | M12 | M24 | M36 |
|---|---|---|---|
| Book equity | $2.0k | $12.9k | $121.6k |
| ARR | $11.0k | $98.8k | $536.4k |
| Paper value at 2× / 3× / 5× ARR (100% owned) | $22k / $33k / $55k | $198k / $296k / $494k | **$1.07M / $1.61M / $2.68M** |
| Same at conservative revenue | $11k / $17k / $28k | $99k / $148k / $247k | $536k / $805k / $1.34M |

**Founder paper value at M36 (3× ARR = $1.61M), by ownership path** (option pool included; later rounds not):
| Path | Founder ownership | Founder paper value |
|---|---|---|
| Clean (no outside equity, 10% pool at M13) | 90.0% | **$1.45M** |
| Offshore SAFE ($100k @ $3M cap) | 87.0% | $1.40M |
| BD angel (12% at M9) | 79.2% | $1.27M |
| Early-heavy (25% sold pre-launch) | 67.5% | **$1.09M** |

## 15.4 Plan B (accelerated) — the price of speed
| Cash if **no outside money** arrives | M0 | M12 | M24 | M36 | Deepest deficit |
|---|---|---|---|---|---|
| Plan A | (3,628) | (3,725) | 9,098 | 136,998 | **$4,212** (M6) |
| **Plan B** | (3,628) | **(11,510)** | **(26,207)** | 91,112 | **$27,891** (M25) |
| Plan B funded with $30,000 | 26,372 | 18,490 | 3,793 | 121,112 | — |

**Important caveat:** the model holds the user funnel *constant* across plans. Plan B therefore shows only the **cost** of speed, not its possible **benefit** (more users sooner). Choose Plan B only if you can name the specific growth it buys — for example a measured conversion or user-target uplift from the pilot — and only if the $30,000 is in the bank.

## 15.5 Funding-path outcomes (cash, no other money, base revenue)
| Path | Plan A: deepest deficit → cash at M12 / M24 / M36 | Plan B: deepest deficit → cash at M12 / M24 / M36 |
|---|---|---|
| P0: no outside money | −$4,212 → −$3.7k / $9.1k / $137.0k | −$27,891 → −$11.5k / −$26.2k / $91.1k |
| P1: Seed Fund $500 | −$3,712 → −$3.2k / $9.6k / $137.5k | −$27,391 → −$11.0k / −$25.7k / $91.6k |
| P2: Seed $500 + CAA $5,000 at M7 | −$3,712 → **$1.8k** / $14.6k / $142.5k | −$22,391 → −$6.0k / −$20.7k / $96.6k |
| P3: National grant Tk 10 lakh at S1 + Seed | **−$1,903** → $4.9k / $17.7k / $145.6k | −$19,261 → −$2.9k / −$17.6k / $99.7k |
| P4: BD angel $50k at M9 (≈ 12.5% at $400k post) | −$4,212 → $46.3k / $59.1k / $187.0k | −$9,007 → $38.5k / $23.8k / $141.1k |
| P5: Offshore SAFE $100k at M13 (3.3% at $3M cap) | −$4,212 → −$3.7k / $109.1k / $237.0k | −$11,510 → −$11.5k / $73.8k / $191.1k |
| P6: Founder $1.5k + credits | −$2,712 → −$2.2k / $10.6k / $138.5k | −$26,391 → −$10.0k / −$24.7k / $92.6k |

**Reading:** Plan A is close to self-funding with almost any single small win (P1–P3, P6). Only **Plan B** needs P4/P5-sized money — and those are exactly the equity paths that cost ownership. That is the financial argument for Plan A.

---

# 16. PATHWAYS AND FALLBACK TREES — WHAT TO DO WHEN A PLAN DOES NOT WORK

> **Design rule:** every important thing has a Plan, then Fallback 1, Fallback 2, and a Last resort, each with a **trigger** that tells you when to switch. If a fallback also fails, the next one takes over. Nothing in this book depends on a single source, vendor, person or promise.

## 16.1 The decision points (calendar them)
| # | When | Question | Yes → | No → |
|---|---|---|---|---|
| **D1** | End of 2026 (roadmap checkpoint) | Is the advisor-connected BD funding conversation producing a **written dollar commitment** or a **named pilot customer with a start date**? | **Branch B** (16.2) | **Branch A** |
| **D2** | April 2027 | Seed Fund application submitted **and** ≥ 6 other applications submitted in the last 6 months? | Continue | Fix the pipeline first (12.4) |
| **D3** | Start of S1 (≈ Jul 2027) | Cash in the bank vs the S1 + launch need ($3,628 recommended; $1,900 bare)? | Full budget | Choose a lower level (11.2); run a closed pilot |
| **D4** | Launch gate (≈ Dec 2027) | All launch items in Part 22 closed **and** cash ≥ launch need + $1,500 buffer? | Go live | Extend the pilot; do not launch on an empty account |
| **D5** | M9 | Paid conversion ≥ 1.0% of registered users **or** MRR ≥ $300? | Continue Plan A/B | **Branch C** (16.2) |
| **D6** | M12 | Free-window decision (7.4) and Moderate demand/capacity gates (roadmap 3.5, 3.6) | Build Moderate | Stay on Basic (a valid outcome) |
| **D7** | M24–M30 | E1–E10 satisfied? Ultimate gates cleared? | Consider equity / Ultimate | Keep self-funding |
| **D8** | Year 3 | Scale, harvest, or sell? | 16.10 | — |

## 16.2 The funding branches, with money attached
| Branch | Trigger | What you do | Cash effect (base revenue) | Ownership effect |
|---|---|---|---|---|
| **A — Seed Fund + organic** | No BD funding at D1 | Apply April 2027; pilot funded by Seed ($500) + founder bridge; target **CAA 2028 (≈ M7)** | Plan A needs $4.2k; Seed + CAA leaves a small gap (P2: −$3.7k → +$1.8k at M12) | None |
| **B — BD funding lands** | Written commitment at D1 | Confirm the *instrument* (grant, revenue-share, equity, pilot payment) and its terms **in writing** before accepting (roadmap Part 11); apply to Seed anyway; CAA July 2027 | If ≥ $6k: Plan A fully funded; ≥ $30k: Plan B possible | Depends on terms — run E1–E10 if any equity |
| **C — Lean micro-SaaS** | D5 fails (< 1.0% conversion **or** MRR < $300 at M9) | Freeze all hiring and marketing; single VPS; Free-window shrink; route Free + Basic to Standard open-weight models on Groq; founder maintains the code | **Fixed floor ≈ $164/month** (infra $60 + Free $50 + tools $30 + accounting $24); break-even at ≈ 28 Basic users; 120 Basic users ≈ **$530/month net** | None |
| **D — Prize-led** | ≥ 1 grant/prize ≥ $5k | Follow Plan A; spend only per 11.5; publish the win (drives credits and angel interest) | Removes the launch gap (P3: min −$1.9k at S1 → $4.9k at M12) | None |
| **E — Equity-assisted** | E1–E10 all true | Plan A/B with an angel (P4) or offshore SAFE (P5) | P4: $46k at M12; P5: $109k at M24 | 12–20% (BD angel) or 3–10% (SAFE) |
| **F — Pause / pivot / sell** | Branch C fails for 12 months, or a fatal external event (16.9) | Freeze; preserve IP and cap table; options in 16.10 | Costs drop to the floor | None |

## 16.3 From Plan B back to Plan A (downshift protocol)
Move from the accelerated team plan to the governed plan when **any** of these is true: cash < 3 months of fixed outflow · D5 fails · typical gross margin < 60% for two consecutive months · a provider shock lifts COGS by > 15% · the funded $30,000 is more than 60% spent while KPIs lag plan.
**Steps, in order:** (1) freeze new hires; (2) convert full-time roles to part-time or contract where possible (notice periods per contract); (3) cut marketing to the referral loop; (4) stop the office lease process; (5) suspend founder stipend; (6) shrink the Free window; (7) step infrastructure down one stage if gates allow; (8) publish the Plan A budget and start Branch C if D5 also failed.

## 16.4 Fallback chains by sector
| Sector | Plan | Fallback 1 | Fallback 2 | Last resort | Trigger to switch |
|---|---|---|---|---|---|
| **Launch capital** | Grants/prizes + credits | Founder bridge ($1.5–2k) | **Bare-minimum budget** ($1.9k) | Closed pilot only; delay launch | Cash < need at D3/D4 |
| **Growth capital** | Revenue (Plan A) | Grant or credit-funded hires | Small angel via SPV (E1–E10) | Offshore SAFE | Governor blocks a gate-cleared, demand-proven step |
| **Local payments** | SSLCommerz-type aggregator (bKash, Nagad, cards) | Second aggregator (AamarPay / ShurjoPay-type) | Direct wallet payment links | Manual bank transfer with invoice | Success rate < 92% for a week or account issue |
| **International payments** | Merchant-of-record or Payoneer-type checkout (PayPal is not available to Bangladeshi merchants) | Second rail (2Checkout/Verifone-type) | Offshore entity + Stripe (13.3) | Invoice + bank wire for Ultimate/B2B | Onboarding refused or fees > 6% |
| **Standard LLMs (Class S)** | Groq gpt-oss + OpenAI Luna + Gemini Flash-Lite + Mistral | Shift weights among the four | Cerebras / other US-hosted open-weight host | Answer with fewer agents (Quick mode) | Error rate > 2% for 1 h (6.8) |
| **Advanced / Expert** | Sonnet 5, Gemini Flash, Terra, Opus 5, Gemini 3.1 Pro | Cross-vendor swap | Class S with an explicit quality notice | Disable A/E; keep Free/Basic behaviour | Vendor outage or price +25% |
| **Brain** | Fable 5.1 | GPT-6 Astra | Opus 5 | Panel-only planning (6.5) | Failures or restriction notice |
| **Images** | Google image models | Cheaper Google image tier | Mermaid/SVG diagrams | Disable images | Price or outage |
| **TTS** | Azure neural | Gemini Flash TTS | Text transcript only | Disable audio | Free credits end or price change |
| **Embeddings** | Self-hosted MiniLM | Second self-hosted replica | OpenAI embeddings (re-embed) | Keyword search | Node down |
| **Web search** | Tavily | Exa → Brave | Gemini grounding | Fewer searches per run | 429s or credit exhaustion |
| **Code sandbox** | E2B | Queue and retry | Static checks only | Disable execution for Free | Hobby limits reached |
| **Database / cache** | Supabase Pro + Upstash | Backups and restore drill | Second region replica | Read-only mode | Outage > 15 min |
| **Realtime** | Pusher | Server-sent events / polling | — | — | Connection cap or outage |
| **Hosting** | VPS → split → K8s (gated) | Provider migration runbook | Cloud credits as bridge | Single-node degraded mode | Gate metrics (10.2) |
| **Tax / VAT** | NBR startup registration | Provision 15% reverse-charge VAT | Reprice new subscribers | — | Registration denied or delayed (14.6) |
| **Legal structure** | BD Pvt Ltd | Offshore holdco flip (13.3) | Investor SPV | — | Signed foreign term sheet |
| **Team / key person** | Founder + documentation | Contractor retainer | Second maintainer trained | Feature freeze | Illness, burnout, departure |
| **Free tier cost** | Governor ceiling (7.4) | Daily cap cut | Waitlist | End the window early | Free cost > 25% of MRR |
| **Pricing** | Part 7 | Adjust pools first | New-subscriber price | Existing-subscriber price (30-day notice) | Gate fails 2 months |

## 16.5 Product and tier fallbacks
| Situation | Do this |
|---|---|
| Moderate demand signal is absent (roadmap 3.6) | Do not build it; "not needed" is valid data; improve Basic conversion instead |
| Brain fails its offline eval versus Panel (roadmap Tech-D exit) | Keep Panel; Moderate/Ultimate differentiate on Advanced/Expert models and capability gating |
| Ultimate is not demanded | Cap Ultimate at a private-beta list; keep infra at Phase 3a |
| Daemon security cannot be funded | Keep it deferred (roadmap Part 13); log demand |
| A tier's COGS exceeds gates | Fix ladder (20.3) before adding users |

## 16.6 Pivot triggers (from the old blueprint, kept and extended)
1. **B2B agency retainers > 60% of revenue by M18** → pivot toward white-label agent automation.
2. **Open-weight inference below $0.01 per 1M tokens** → drop paid frontier dependencies for Free/Basic and capture 85%+ gross margin.
3. **Free-cohort 30-day retention < 10% for two quarters** → the value proposition is wrong; shrink Free and interview churned users before spending on acquisition.
4. **Median utilization > 75% of pools** → raise pool price or cut pool size for new subscribers (7.7).
5. **Any single vendor > 60% of COGS** → rebalance immediately (3.4).

## 16.7 Vendor and regulatory shock protocol
1. **Detect** (provider notice, error spike, news). 2. **Contain**: switch class routing to the fallback; freeze marketing spend. 3. **Communicate** to affected paying users within 24 hours. 4. **Cost-check**: rerun Appendix A. 5. **Decide**: stay, swap, or reprice (7.7). Precedent: the 19-day Fable/Mythos suspension (Part 3.5).

## 16.8 Personal and founder-continuity fallback
Because the company has one owner-operator: keep a **runbook** (deploy, rotate keys, restore backups, pay vendors); give a **trusted second person** read-only access to dashboards and a sealed emergency access procedure; hold **six months of personal reserve** (14.3); schedule **one full day off per week** and a monthly review of burnout signs (9% of failed startups cite burnout).

## 16.9 What counts as "fatal" (moves you to Branch F)
Loss of the payment rail with no substitute · a privacy breach involving user content · a sustained vendor/regulatory ban with no substitute · unresolvable legal dispute over IP · founder incapacity with no continuity plan.

## 16.10 Harvest, sell or wind down
| Option | When | Indicative value |
|---|---|---|
| **Harvest** (stop investing, take profit) | Growth stalls but GP is healthy | Free cash flow after the reserve target (14.4) |
| **Sell to a strategic or on a small-SaaS marketplace** | Year 2–3 with clean cap table and books | 2.5–4× annual revenue for sub-$1M ARR (13.4); e.g., $99k ARR at M24 → roughly $250k–$395k **[A]** |
| **Open-source + consulting** | Product loses, know-how has value | Consulting revenue plus reputation |
| **License the tier/profile system or agent modules** | Modules stand alone | Negotiated |
| **Wind down** | Branch F unrecoverable | Refund annual subscribers pro rata; export user data; delete per policy; keep the books for the statutory period |

---

# 17. TEAM, HIRING, COMPENSATION AND OFFICE

## 17.1 Principles
1. **Hire reactively to measured strain**, never proactively "because a real company has a team" (roadmap Part 8).
2. **A hire is a promise of payroll for 12+ months** — approve only if the governor allows it *and* the reserve target is not endangered.
3. **Pay fairly and in writing.** Bangladeshi developers can earn several times local pay from remote foreign employers (remote developer medians of about $41k–$46k a year appear in salary surveys), so retention is a real financial risk **[V]**.
4. **Contractors first, employees second**, for anything not needed every week.

## 17.2 Salary bands (planning; verify locally)
| Role | Gross BDT / month | ≈ USD / month | Basis |
|---|---|---|---|
| Part-time contractor developer | 30,000 | $244 | No on-cost |
| Junior full-stack | 35,000 | $285 (+10% = $313) | Paylab: 80% of software engineers earn BDT 19k–112k gross per month **[V]** |
| Support / community associate | 25,000 | $203 (+10% = $224) | **[A]** |
| Growth / marketing specialist | 50,000 | $407 (+10% = $447) | Old blueprint **[V old]** |
| Mid engineer | 75,000 | $610 (+10% = $671) | Levels.fyi Dhaka: 25th percentile ≈ BDT 601k/year (≈ BDT 50k/month), median ≈ BDT 1.02M/year (≈ BDT 85k/month), 75th ≈ BDT 1.74M/year **[V]** |
| Senior DevOps / security | 140,000 | $1,138 (+10% = $1,252) | Near Levels.fyi Dhaka 75th percentile |
| Founder stipend rungs | 15,000 / 40,000 / 100,000 / 140,000 | $122 / $325 / $813 / $1,138 | 14.3 |
| Employer on-cost | +8–10% | — | Employer contributions **[V]**; the book uses **10%** |

Mid-engineer pay of BDT 75,000 sits below the Dhaka median; expect to raise it toward BDT 85,000–95,000 for a Dhaka-competitive hire. Rajshahi-based hiring may cost less **[A]**. Review bands every year.

## 17.3 The team plan (the OpEx ceiling used in Plan B and by the governor in Plan A)
| Role | Start (M) | Monthly cost (USD, incl. on-cost) | One-off laptop (BDT 90,000 ≈ $732) | Hire when… (measured strain **[A]**) |
|---|---|---|---|---|
| Part-time contractor developer | 1–12 | 244 | — | Founder is the only builder and a backlog > 6 weeks exists |
| Junior full-stack | 7 | 313 | ✔ | > 10 hours/week of support or bug-fixing displaces roadmap work |
| Mid engineer #1 | 13 | 671 | ✔ | Moderate gates cleared (roadmap 3.5/3.6) |
| Growth specialist | 13 | 447 | ✔ | Free→paid conversion plateaus below target for 2 months |
| Support / community associate | 19 | 224 | ✔ | > 30 tickets/week |
| Senior DevOps / security | 19 | 1,252 | ✔ | Ultimate build and the daemon-review prerequisites |
| Mid engineer #2 | 25 | 671 | ✔ | Roadmap items delayed > 1 quarter by capacity |
| Junior full-stack #2 | 25 | 313 | ✔ | Feature and support load |
| Founder stipend R2 / R3 | 13 / 25 | 325 / 813 | — | 14.3 conditions |
| Office lease | 25 | 488 | — | 17.7 conditions |
| Other lines | all | Tools/legal/accounting $200 → $350 → $600 per month; marketing $150 → $700 → $1,500 per month | — | Per stage |

**Total monthly OpEx ceiling:** M1 $594 · M12 $907 · M18 $2,806 · M24 $4,282 · M31 $9,291 (includes $2,000 migration) · M36 $7,291. Headcount: M1 = 1 + contractor · M13 = 4 · M19 = 6 · M25 = 8.

## 17.4 Roles and responsibilities (so a hire never arrives without a job)
| Role | Owns |
|---|---|
| Founder | Architecture, cost dashboards, vendor contracts, funding, final say on gates |
| Mid engineer #1 | Tier system, evals, prompts, tests; deputy for on-call |
| Growth specialist | Community, referral loop, Free→paid funnel, content |
| Senior DevOps / security | Infra gates, secrets, backups, incident response, audits |
| Support associate | Tickets, docs, onboarding, feedback loop |

## 17.5 Equity, retention and culture
- **Option pool: 10%**, created only at the first equity-eligible hire (M13); 4-year vesting, 1-year cliff. Indicative grants **[A]**: mid engineer 0.5%, senior DevOps/security 1–1.5%, growth 0.25–0.5%, junior 0–0.25%. Confirm the legal and tax treatment of employee options in Bangladesh; use phantom shares or a profit bonus if simpler **[U]**.
- **Profit-linked bonus:** 5–10% of monthly gross profit above plan, split by role, paid only when reserves are on target.
- **Written contracts, IP assignment and confidentiality** for everyone before their first commit.
- **Growth path:** documented levels and a yearly pay review.

## 17.6 Office ladder
| Rung | What | Monthly cost **[A]** | Move up when… |
|---|---|---|---|
| **O0 — Home** | Founder works from Rajshahi | $0 | Team ≥ 2 |
| **O1 — Incubator space at Bangabandhu Sheikh Mujib Hi-Tech Park, Rajshahi (Sheikh Kamal IT Incubator)** | One-year incubation offered to startups; listed rent **Tk 5 + Tk 5 service per sq ft per month** — 300–500 sq ft ≈ Tk 3,000–5,000 (≈ $24–41) **[V/U: confirm rate, eligibility, current status]** | ≈ $25–40 | Team ≥ 3 or incubation ends |
| **O2 — Co-working seats** (Rajshahi or Dhaka) | 3–6 desks | BDT 4,000–8,000 per seat ≈ $33–65 **[A]** | Team ≥ 6 |
| **O3 — Leased city office** | 1,200–1,500 sq ft, 8–10 people | BDT 60,000 ≈ $488 + fit-out BDT 300,000–600,000 ($2.4k–$4.9k) + deposit 3–6 months' rent **[A]** | Team ≥ 8 for 6 months **and** conditions in 17.7 |
| **O4 — Dhaka satellite / sales office** | 2–4 desks | BDT 80,000–150,000 ≈ $650–$1,220 **[A]** | Enterprise pipeline ≥ 3 named prospects |
| **O5 — Owned office** | Buy | See 17.7 | Team ≥ 15 for 12 months and the buy rule holds |

Startup VAT exemption covers premises rent while you are NBR-registered (14.6), which lowers the effective cost of O2–O4.

## 17.7 Rent, buy or build — the rule
1. **Move from O1 to O3 only when** team ≥ 8, reserve target met, and GP ≥ $10,000/month for three months.
2. **Buy (O5) only when all are true:** headcount ≥ 15 for 12 months · GP ≥ $25,000/month for 12 months · after purchase the operating reserve is still ≥ 9 months · **purchase price ≤ 7 × the annual rent of an equivalent space** · three independent quotes · lawyer-verified title.
3. **Why that price test:** if owning costs about **13.5% of price a year** (12% opportunity cost + 1.5% maintenance **[A]**), owning is cheaper than renting only when price ≤ ≈ 7× annual rent. Example: a rent of BDT 60,000 a month ($5.9k a year) supports a purchase only up to ≈ $41k (≈ BDT 5.1 million) for the whole space; if local quotes are higher **[U]**, keep renting.
4. **Build a custom office** only at a staff of 30 or more or as part of a strategic campus; never before profit is proven for three straight years.

## 17.8 Equipment, security and HR essentials
- **Laptop:** BDT 90,000 each; full-disk encryption, MFA on every service, password manager, no shared accounts.
- **Contracts:** employment, contractor, IP assignment, NDA, acceptable-use.
- **Labour-law compliance** (notice periods, leave, benefits) — get a lawyer's checklist before the first full-time hire **[U]**.
- **Accounting:** outsourced accountant from launch (BDT 3,000–5,000/month **[A]**); monthly close by the 10th.

---

# 18. THE FBEBC RESEARCH PROGRAM — COST, FUNDING, GATES AND RETURN

*(Source: your `fbebc-research-program-guide.md`. This Part does not redesign the research; it prices it, places it in the money timeline, and ties it to the funding and margin rules.)*

## 18.1 What it is, in one paragraph
A two-stage program. **Stage 1** is a capped four-week, zero-cost proof of concept (toy tasks, correctness-only fitness, Docker sandbox, free-tier LLM on your laptop) that produces an **arXiv preprint and an open-source repo**. **Stage 2** starts only after Basic is live and billing: a ring-fenced, capped, MiniMe-integrated research fork that **evolves role prompt text only** (never Python source), scores candidates with your existing promptfoo suite, and promotes changes only through **human-reviewed pull requests**.

## 18.2 Cost and funding
| | Stage 1 (Preprint) | Stage 2 (MiniMe-integrated) |
|---|---|---|
| **Cash cost** | **$0** — laptop, Docker, GitHub Student Pack, free-tier LLM | **$10–30/month** of LLM calls on *staging* keys; optional **one-off $20–50** for a short rental if you want a real latency validation |
| **Founder time** | ≈ 4 weeks; roughly **100–120 hours** **[A]** | ≈ 5–10 hours/week **[A]** |
| **Funded by** | You (time only) | **Basic's gross profit, ring-fenced** (18.4) |
| **Timing** | S0, ideally **Jan–Feb 2027**, so the preprint exists before the April 2027 Seed Fund and July CAA applications | After the four gates in 18.3 are independently true (not earlier than ≈ M13) |
| **Output** | arXiv preprint; open repo; possible workshop submission | Production case study; better or cheaper prompts; real cost-per-task data for Part 8; possible second paper |

**Rule 1 exception (recorded):** Stage 1 may use a *free-tier* LLM key because it processes **no user data** (toy tasks) and is not production. Before starting, confirm the current free-tier model and limits — the guide names Gemini 2.5 Flash-Lite, and models and limits move (Part 2.3). Stage 2 uses staging keys, **never** the production Upstash URL or production LLM keys.

## 18.3 The gate between the stages (from the guide, mapped to this book)
| Gate | Condition | Check against |
|---|---|---|
| G1 | Basic launched, **live and billing** | Part 22 launch items closed; paid users > 0 |
| G2 | Basic's operational load manageable | Founder support/ops time < 30% of the week for 4 weeks **[A]** |
| G3 | **Written, capped research budget line** ring-fenced from Basic's burn | 18.4 |
| G4 | "Attested" and "promotable" defined in writing in advance | Guide §4.7 template |

## 18.4 The research budget line (ring-fence)
- **Cap:** the smaller of **$50/month** and **5% of last month's gross profit** while GP < $2,000; afterwards **3% of GP, maximum $150/month**.
- **Counts as OpEx** under the governor (9.6) and appears in the Master Spend Ledger.
- **Hard stop** if any margin gate is red, the reserve target is breached, or Basic would fall below break-even because of the research spend.
- Reviewed **quarterly**; unused budget does not roll over.

## 18.5 Expected return (Stage 2, **[A]** — it is optimisation, not a new revenue stream)
Paid-user LLM COGS in the model: **$1,758/month at M24** and **$9,654/month at M36**.

| Prompt/config cost reduction achieved | Saving at M24 | Saving at M36 | Annual saving at M36 |
|---|---|---|---|
| 5% | $88/mo | $483/mo | $5.8k |
| **10%** | **$176/mo** | **$965/mo** | **$11.6k** |
| 20% | $352/mo | $1,931/mo | $23.2k |

Against a Stage 2 spend of about **$30–100/month**, a 10% saving returns **≈ 3.5× at M24 and ≈ 10× at M36**. At a 3× valuation multiple, the 10% saving adds roughly **$35k** of paper value at M36 (about 2% of $1.61M). **Honest reading:** the direct financial effect is modest; the larger value is credibility, learning and optionality.

## 18.6 How it raises your potential
1. **Grant hit-rate.** A public preprint and repo make applications more credible. If the per-application win rate rose from 7% to 9%, the chance of at least one win in 12 applications would rise from **58% to 68%** (12.4) **[A]**.
2. **Conference-grant route.** An accepted workshop paper unlocks the **Aspire Conference Grant ($500–$1,000)** that otherwise "requires acceptance to present" (roadmap 5.1).
3. **Margin defence.** Prompt evolution is a systematic answer to your Part 3.3 question ("run the same task both ways") and directly supports the gross-margin gates (0.4).
4. **A defensible narrative for investors and enterprises.** "A safety-governed evolutionary mechanism running on a live SaaS with zero unreviewed production writes" is a stronger story than "another AI wrapper" — useful at E1–E10 time (13.2) and in enterprise security questionnaires.
5. **Talent and community.** An open-source repo attracts contributors and future hires (17.5).
6. **Optionality.** Later, source-code self-modification could become a separate project — only after the atomic write/verify-then-promote design in `DEFERRED.md` exists; it needs its own gate and budget line.

## 18.7 Stop rules and fallbacks
| Situation | Do this |
|---|---|
| Stage 1 overruns four weeks | **Cut scope, not the cap**: fewer generations or a smaller ablation; ship what exists (guide §1.4) |
| Stage 1 exit checklist fails | Publish the repo and a short technical report; skip the preprint; move on |
| A gate in 18.3 is not met | **Stay at Stage 1**; do not start Stage 2 "on momentum" |
| Research spend threatens a margin gate | Stop Stage 2 for the month |
| Stage 2 produces no measurable gain after two quarters | Fall back to **manual A/B prompt testing** with promptfoo (roadmap 3.3) and end the ring-fenced line |
| A `.env` copy-paste points the fork at production | Treat as an incident: rotate keys, review the ledger, add a startup check that refuses production URLs |

## 18.8 Ledger lines to add
| When | Item | Amount | Trigger |
|---|---|---|---|
| S0 (≈ Jan–Feb 2027) | FBEBC Stage 1 | $0 cash; 4 weeks | Groundwork of Phase 0 done; end-2026 checkpoint reviewed |
| ≥ M13 | FBEBC Stage 2 | ≤ $30/month (18.4 cap) | Gates G1–G4 |
| Optional | Latency-validation rental | $20–50 once | A specific latency claim needs testing |

---

# 19. LESSONS FROM OTHER STARTUPS — HARDSHIPS AND HOW TO SOLVE THEM

## 19.1 What the evidence says (worldwide)
| Finding | Evidence | Meaning for you | Where handled |
|---|---|---|---|
| **Cash is the last symptom of an earlier disease** | CB Insights: 38% of failed startups cite running out of cash or failing to raise; 70% of the 431 VC-backed shutdowns since 2023 ran out of capital; median funded startup holds only 12–15 months of runway; founders with 18+ months raise about 2.4× more successfully **[V]** | Build reserve and a governor; do not fund growth by hope | 9.6, 14.2 |
| **No market need is the #1 stated cause** | 35–42% of post-mortems; poor product-market fit 43% in the 2026 update | Gates and pilot data before building tiers | 16.1, roadmap 3.6 |
| **Unit economics kill AI products** | Replit's gross margin fell from **36% to −14%** in two months after launching a more autonomous agent; in most AI products the **90th-percentile user costs 10–40× the median**; AI-first gross margins run about 20–60% versus 70–90% for classic SaaS **[V]** | Pools, class meters, cost governors, per-run ceilings | 5–8, 6.1 |
| **Repricing hurts trust** | Cursor's switch from request limits to token credits triggered backlash (users burning quota in hours, surprise charges, refunds) **[V]** | Announce limits in advance; never bill by surprise; grandfather | 7.2, 7.7 |
| **"Unlimited" is a trap** | Copilot reportedly lost about $20 per user on average early on; one Claude Code user consumed tens of thousands of dollars on a $200 plan **[V]** | Fixed pools; no unlimited plan | 7.1 |
| **Founder conflict and burnout** | Co-founder conflict appears in roughly 20% (up to ~65% in one study) of failures; burnout 9% | Vesting, written roles, weekly rest, continuity plan | 13.5, 16.8 |
| **The Series A crunch** | Fewer than 30% of seeded startups reach Series A; Series A now expects $5–10M ARR; seed-to-A gap is 18–24 months **[V]** | Do not build the plan around a Series A; plan to be profitable | 13, 16.2 |
| **Dilution accumulates** | Seed ≈ 19.5%, Series A ≈ 18%; founders of software companies end near 37.5% after Series A; stacked SAFEs add 15–25 points **[V]** | Sell late, small, priced on proof | 13.2, 13.5 |

## 19.2 What the evidence says (Bangladesh)
| Finding | Evidence | Meaning for you | Where handled |
|---|---|---|---|
| **A funding drought and a domestic-capital gap** | H1 2026: $6M in 6 deals (−95%), 100% foreign, 0% domestic; 80% of all capital since 2013 went to late-stage, mostly from global investors **[V]** | Non-dilutive first; expect small tickets | 12.3 |
| **A bootstrapped path can work** | **10 Minute School** began as a small bootstrapped operation in **2015**, took its first outside money in 2022 ($2M seed), then $5.5M pre-Series A in 2023; cumulative $7.5M, 650,000+ paid users **[V]** | Seven years of self-funded proof came before institutional money; time is a legitimate strategy | 9, 12.1 |
| **State funds carry governance risk** | Startup Bangladesh Ltd was reported to have denied funding to founders not close to the government, and cancelled a Tk 5 crore proposal for 10 Minute School in July 2024 **[V]** | Never depend on one public source; keep paperwork clean | 12.2 |
| **Legal instruments differ from the US template** | SAFEs and convertible notes are unrecognised; Bangladeshi private companies cannot issue them; founders re-domicile (Singapore, Delaware) to raise **[V]** | Decide structure before term sheets; keep flip option | 13.3 |
| **Payments are a structural obstacle** | Stripe and PayPal are unavailable to Bangladeshi merchants; workarounds include Payoneer, 2Checkout/Verifone and merchant-of-record services **[V]** | Local rails + a second international rail | 3.7, 16.4 |
| **Wallets dominate local payments** | bKash 70M+ users; mobile wallets are more than 60% of online payments; cards about 25%; most consumers lack internationally-enabled cards **[V]** | Price and bill in BDT for local users | 7.1, 3.7 |
| **Tax policy is improving but moves quickly** | FY2026-27 budget and SRO 147: startup VAT exemption to 2035, nine-year loss carry-forward, proposed zero turnover tax; but imported services now face 15% reverse-charge VAT for non-registered firms **[V]** | Register early; verify enactment | 14.6 |
| **Talent leaks to remote foreign jobs** | Remote developer medians ≈ $41k–46k/year against local mid pay near $10k/year | Retention plan, bonuses, ESOP | 17.5 |
| **Government incubation is cheap** | Rajshahi Hi-Tech Park lists incubation rent of Tk 10 per sq ft per month all-in and one-year incubation for startups **[V/U]** | Use O1 before leasing | 17.6 |

## 19.3 The recurring hardships and the specific answer to each
| Hardship you are likely to face | Early warning | Answer |
|---|---|---|
| The account is empty before revenue covers costs | Cash < 3 months of fixed outflow | Plan A, governor, reserve, bare-minimum budget (11.2) |
| A prize or grant does not come | Rejections; no term sheet at D1/D2 | Portfolio of ≥ 12 applications; founder bridge; credits; Branch A |
| A power user or a bug burns money | Per-user cost > 3× median; run ceilings hit | Pool caps, per-run ceilings, class meters, alerting (7.2, 6.1) |
| The Brain vendor is cut off | Provider notice or 3 failures | Astra → Opus 5 → Panel (6.5) |
| Payments fail or a rail is closed | Success rate < 92% | Second rail per region; manual invoice for large accounts |
| An investor offers cheap money for big equity | Dilution > 15% for the first round; post-money below E4 floor | Decline; return to Plan A |
| VAT surprise on foreign invoices | Reverse-charge line appears on statements | Register as startup first; provision 15% until confirmed |
| Founder overload | Missed releases; support backlog | Reactive hiring (17.3); continuity plan (16.8) |
| Best engineer gets a remote offer | Attrition risk conversations | Market-aligned pay, bonus, ESOP, growth path |
| Free tier eats the margin | Free cost > 25% of MRR | Governor ceiling; daily cap; shrink the window |
| A price promotion or model price change breaks a gate | Gate red for 2 months | Fix ladder (20.3) |
| Motivation dips during the long S0–S1 stretch | Slipping milestones | Publish small proofs (FBEBC preprint, demo video); joining hackathons; monthly public build update |

---

# 20. GOVERNANCE — DASHBOARDS, THRESHOLDS, FIX LADDER, RITUALS

## 20.1 What to watch (weekly dashboard)
**Cost and margin:** cost per task by type · pool utilization (median, p90) per plan · COGS as % of revenue per plan (rolling 30 days) · gross margin per plan · Free budget as % of MRR.
**Models and providers:** provider share by class vs targets · failover and error rate · p95 latency · Brain cache-hit rate, calls per run, tokens per run, re-plan rate · escalation rates (S→A, A→E) per role and first-pass success · search, sandbox, image and TTS counts vs allowances.
**Money and business:** cash · **runway** (cash ÷ fixed monthly outflow) · reserve vs target (14.2) · governor headroom (9.6) · MRR, ARR, ARPU, paid conversion, churn · payment success rate per rail · refunds and chargebacks · open grant conditions.

## 20.2 Thresholds (green / amber / red)
| Metric | Green | Amber | Red |
|---|---|---|---|
| COGS % of revenue, per plan | ≤ 35% | 35–45% | > 45% |
| Typical gross margin | ≥ 70% | 60–70% | < 60% |
| Free budget as % of MRR (window) | ≤ 15% | 15–25% | > 25% |
| Runway vs reserve target | ≥ target | 2 months → target | < 2 months |
| Any provider's share of a class | < 50% | 50–60% | > 60% |
| Brain cache-hit rate | ≥ 50% | 30–50% | < 30% |
| Failover rate | < 1% | 1–5% | > 5% |
| Median pool utilization | < 60% | 60–75% | > 75% |
| Payment success rate | > 95% | 92–95% | < 92% |
| Paid conversion of registered users | ≥ 2% | 1–2% | < 1% |
| Monthly paid churn **[A]** | < 5% | 5–8% | > 8% |
| Founder time on support/ops | < 30% | 30–50% | > 50% |

## 20.3 The fix ladder (when a margin or cost gate fails)
| Step | Action | Who decides |
|---|---|---|
| 1 | Reduce Advanced/Expert routing weights | Automatic |
| 2 | Lower reasoning effort and `max_tokens` | Automatic |
| 3 | Fix cache-prefix ordering; raise cache hits | Founder |
| 4 | Move non-interactive work to batch (−50%) | Founder |
| 5 | Shrink non-LLM allowances (search, images, TTS) | Founder |
| 6 | Reduce pool sizes for **new** subscribers | Founder |
| 7 | Raise the price for **new** subscribers | Founder |
| 8 | Change existing subscribers' price/limits (30-day notice, 90-day grandfathering) | Founder, last resort |

## 20.4 Rituals
| When | What |
|---|---|
| **Daily (5 min)** | Provider spend vs forecast; alerts; payment failures |
| **Weekly** | Dashboard review; failover events; support load; pipeline of funding applications |
| **Monthly (by the 10th)** | **Financial close:** reconcile provider invoices, bank and payment-gateway statements to the internal ledger · recompute the OpEx governor (9.6) · check reserve vs target (14.2) · Free-budget ceiling (7.4) · distribution decision (14.4) · update runway · spot-check prices of the top three spend models |
| **Quarterly** | Re-verify Part 4 (**next: 2026-12-15**, then 2027-03-15, 2027-06-15…) · refresh eval sets · sub-processor list and vendor terms · FX check (base 123; stress 135) · tax/VAT registration status · funding calendar (12.5) · risk register review |
| **Yearly** | Full rulebook review · pay-band review · insurance and legal review · cap-table audit |
| **Event-driven** | Any provider announcement, price change, outage, funding offer, or regulatory notice → 16.7 |

## 20.5 Decision log
Record every financial decision (date, rule referenced, alternatives considered, expected result). Review each entry after 90 days. If a decision overrode a rule, mark it and explain (9.6 override rule).

---

# 21. RISK REGISTER (FINANCIAL, FUNDING, MODEL AND STRUCTURAL)

| # | Risk | Likelihood | Impact | Early signal | Mitigation |
|---|---|---|---|---|---|
| R1 | Funding does not arrive (grants, prizes) | High | Medium | No wins after 12 applications | Plan A; founder bridge; bare-minimum budget; Branch A/C (16) |
| R2 | Provider price rise or promo expiry (Gemini Jan 2027) | High | Medium | Provider announcement | Budget at list; multi-vendor; quarterly re-verification (2.3) |
| R3 | Brain vendor suspended (export controls) | Medium | High | Notice, failures | Astra → Opus 5 → Panel (6.5) |
| R4 | Tokens per task far above assumptions | Medium–High | High | Tech-A medians vs 2.4 | Pool caps, per-run ceilings, gates |
| R5 | Power-user cost blow-up (P90 ≫ P50) | Medium | High | Per-user cost > 3× median | Class pools, no unlimited plan, alerts |
| R6 | Free-tier abuse or overspend | Medium–High | Medium | Pool burned in 24 h; MAFU spike | Anti-abuse (7.4), governor ceiling |
| R7 | Imported-service VAT (15%) not avoided | Medium | High | Reverse-charge on invoices | NBR startup registration before vendor payments (14.6) |
| R8 | Payment rail limits (wallet recurring, no PayPal/Stripe) | High | High | Onboarding refusals; failure rate | Two rails per region; MoR; offshore option (13.3) |
| R9 | Legal-instrument mismatch (SAFE in BD) | Medium | Medium | Investor asks for SAFE | Flip decision D3; SPV; priced round |
| R10 | Early equity sold too cheaply | Medium | Very high | Investor pressure before proof | Equity Rules E1–E10 (13.2) |
| R11 | State-fund governance risk | Medium | Medium | Delays, opaque criteria | Diversify; clean paperwork |
| R12 | FX depreciation | Low–Medium | Medium | BDT > 128 | USD reserve (ERQ); stress case; re-price triggers (7.7) |
| R13 | Key-person / burnout | High | High | Missed releases | Runbook, second person, reactive hiring, rest (16.8) |
| R14 | Talent poaching by remote employers | Medium | Medium | Attrition signals | Market pay, bonus, ESOP (17.5) |
| R15 | Cash out while running Plan B | Medium | High | Cash < 3 months | Downshift to Plan A (16.3) |
| R16 | Privacy or vendor-terms breach | Low–Medium | Very high | Free-tier key in production; missing DPA | Rule 1, vendor register, sub-processor list (3.6) |
| R17 | Model deprecation or quality regression | Medium | Medium | Provider notices; eval drop | Model-change protocol (6.7); 90-day buffer |
| R18 | Quality loss from cheaper models | Medium | Medium | Eval pass rate falls | Escalation ladder; canary (6.1, 6.7) |
| R19 | Product-market fit shortfall | Medium | High | D5 fails | Branch C; pivot triggers (16.6) |
| R20 | Chargebacks and refunds on annual plans | Low–Medium | Low–Medium | Rate > 2% | Written policy; monthly billing first 6 months **[A]** |
| R21 | Grant conditions breached | Low | Medium | Unreported use of funds | Segregated funds; reports on time (14.7) |
| R22 | Overreach (office, hires) before profit | Medium | High | Fixed outflow > 50% of GP | 17.7 rules; governor |

---

# 22. OPEN ITEMS — CLOSE THESE BEFORE THE DECISION THEY GATE

## 22.1 Before charging real customers (launch gate D4)
- [ ] **Tech-A** dollar-per-call logging live; replace every **[A]** in 2.4 and 7.1 with measured medians and p90 values
- [ ] **Company registered** (RJSC), trade licence, TIN/BIN, corporate bank account; **NBR startup registration confirmed** (14.6)
- [ ] **Vendor data terms** confirmed in writing for every provider (3.6); vendor register created
- [ ] **Local payments:** aggregator contract and real fees; recurring billing method for bKash/Nagad tested
- [ ] **International payments:** rail chosen and onboarded (PayPal is not available to Bangladeshi merchants; verify Payoneer Checkout, 2Checkout/Verifone, merchant-of-record options); settlement currency, FX spread, KYC
- [ ] **Vendor payments:** two internationally-enabled cards or USD accounts; test billing on each vendor (3.3)
- [ ] **Anthropic/OpenAI access** for a Bangladesh-registered entity; usage-tier thresholds; Fable 5.1 rate limits; Astra availability; Terra price ($2/$12 vs $2.50/$15)
- [ ] **Mistral:** pinned model IDs; Devstral 2 price; what each `-latest` alias resolves to
- [ ] **Google:** image-model IDs and the Gemini 2.5 Flash Image shutdown date; 3.1 Pro preview status; batch API for Flash; cache pricing; whether startup credits cover the Gemini API
- [ ] **Groq:** Developer-plan limits at launch traffic; written data terms
- [ ] **Code:** Anthropic and OpenAI adapters; delete dead models from `QUOTA_CONFIG`; remove HuggingFace chat and `openrouter/free` from production chains; add the `free` tier column; pin IDs; self-hosted embeddings; Azure TTS replacing `edge-tts`; search key plan
- [ ] **Eval sets** (≥ 50 cases per role) and Class A/S weights, especially coding
- [ ] **Sentry, Langfuse, VPS** prices verified
- [ ] **Landing-page edits** (7.8), sub-processor list, Terms of Service and Privacy Policy, Free-tier terms
- [ ] **Anti-abuse stack** for the Free tier (7.4)
- [ ] **Batch API** integration for Moderate's Brain
- [ ] **Refund and chargeback policy** written
- [ ] **Working buffer** ($1,500) and **funding target** ($6,000 Plan A) reached (11.4)

## 22.2 Before applying for funding
- [ ] Application kit built (12.7); rolling calendar set (12.5); ≥ 12 applications planned
- [ ] Current national startup-grant scheme (iDEA / BIG successor), Startup Bangladesh windows, Bangladesh Bank startup-fund rules, and Aspire 2027 windows **confirmed**
- [ ] Credits applications filed: Microsoft Founders Hub, AWS Founders, Google Start (12.2 B)
- [ ] Solo versus co-founder decided; founder agreement, IP assignment, cap table document signed (13.5, 13.7)
- [ ] Legal-counsel quote for an offshore holding company kept on file (13.3)
- [ ] Rajshahi Hi-Tech Park incubation eligibility, current rent and status confirmed (17.6)
- [ ] Personal reserve set aside; any founder bridge loan documented (14.3)
- [ ] FBEBC Stage 1 slot scheduled; free-tier model and limits verified (18.2)

## 22.3 Before accepting equity or hiring
- [ ] Accountant: corporate tax rate and ICT/hi-tech-park exemptions; turnover-tax enactment; VAT quarterly filing; withholding on foreign payments; grant accounting; dividend rules
- [ ] Counsel: employee-option legality and tax; employment and labour-law checklist (17.8)
- [ ] Equity Rules E1–E10 checked in writing (13.2)

---

# 23. CORRECTIONS TO THE OLD BLUEPRINT, AND CHANGE LOG

## 23.1 What was wrong in the old blueprint (and where it is fixed here)
| # | Old blueprint | Problem | Fixed in |
|---|---|---|---|
| 1 | Llama 3.1 / Mixtral / Gemini 1.5 / GPT-4o / Claude 3.5 / DeepSeek-R1 as production models | Deprecated or superseded | Parts 4–5 |
| 2 | Gateway of Groq → Mistral → Gemini → OpenRouter → Anthropic → OpenAI → DeepSeek | Repo has no Anthropic/OpenAI/DeepSeek adapters; includes HuggingFace and Cloudflare instead | 3.1, 5.4 |
| 3 | Limits in TPM/TPD | Landing page uses monthly tokens | 7.1 |
| 4 | Implied API cost per million tokens falls with tier ($0.39 → $0.23) | Impossible | 9.4 |
| 5 | Free-tier compute not costed | Understates COGS | 7.4 |
| 6 | Free-tier keys in production | Privacy conflict with landing-page promise | Rule 1 |
| 7 | Gemini Flash intro price treated as permanent | Doubles on 2027-01-01 | 2.3 |
| 8 | Payments: Stripe assumed | Not available to Bangladeshi merchants; fixed-fee drag on cheap plans | 3.7, 14.6, 16.4 |
| 9 | Pusher $20–40; infra items missing | Cheapest paid plan is $49; E2B and Supabase Pro missing | 10 |
| 10 | Search, sandbox, TTS, embeddings not costed | Understates COGS | 4.2, 8 |
| 11 | Year revenue = year-end ARR | Overstates P&L | 9.3 |
| 12 | Cash breakeven at month 15 | Not supported | 9.5 |
| 13 | Seed deployed Q4 2026; Basic launch Q1 2027 | Contradicts the roadmap (skip 2026 round; Seed application April 2027; launch after pilot) | 0.2, 11.1 |
| 14 | FX 120 | Market ≈ 123 | 2.1 |
| 15 | `agent_tier_map` excerpt with a Free tier | Repo has role rows × basic/moderate/ultimate | 5.4 |
| 16 | Landing prices $9/$29/$79 vs blueprint $6.42/$20.42/$45.83 | Two different products | 7.1 |
| 17 | `-latest` aliases | Silent price/quality drift | Rule 3 |
| 18 | Brave "2,000 free queries" note | Free plan removed | 4.2 |
| 19 | OpEx plan ($7.6k / $41.4k / $175.5k) funded by "grants" | Unaffordable from revenue; no pre-launch costs | 9, 11 |
| 20 | "Software is 100% VAT-exempt" | Outdated; imported services carry 15% VAT unless a registered startup | 14.6 |
| 21 | SAFE for a Bangladeshi Pvt Ltd | Not recognised | 13.3 |
| 22 | Cap table (co-founder; $5M cap; Series A 16%) | Assumptions and arithmetic errors | 13.5 |
| 23 | $500 seed treated as enough for launch | Pre-launch needs $3,628 | 11.2 |
| 24 | No reserve, profit-distribution or founder-pay policy | Missing | 14 |
| 25 | B2B revenue in projections | No defined product or price | 9.1 |
| 26 | No funding-source analysis; no fallback tree | Missing | 12, 16 |
| 27 | Statutory costs at 120 BDT/USD | Recompute at 123 (BDT 72,730 ≈ $591) | 11.2 |

## 23.2 Change log
| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-19 | First edition: providers, price sheet, model roster, escalation rules, plans and prices, unit economics, 36-month model, infrastructure |
| 1.1 | 2026-09-20 | Added: capital plan by stage, funding sources, equity/valuation, profit and reserve policy, statements, fallback trees, team/office plan, FBEBC program, lessons from other startups, governance, risk register, open items, corrections; rebuilt Part 9 around Plan A / Plan B and pre-launch costs |

---

# APPENDIX A — HOW TO RECOMPUTE THIS BOOK

Two Python files accompany this rulebook:
- **`minime_pricing_model.py`** — price sheet, class costs, plan pools, unit economics, the 36-month P&L, the OpEx governor and scenarios. Run `python3 minime_pricing_model.py`.
- **`minime_capital_plan.py`** — stage budgets, funding-source probabilities, team plan, cash paths for Plan A/B and each funding path. Run `python3 minime_capital_plan.py`. It imports the first file.

**To change something:**
| Change | Edit | Then |
|---|---|---|
| A provider price | `PRICE` in the pricing model (and Part 4) | Run both; check the gates (0.4) |
| A plan pool, price or allowance | `PLANS` (and 7.1) | Check COGS at cap ≤ 45% of local price |
| The user funnel | `SNAP` | Re-read 9.2–9.5 and 15 |
| A team role or salary | `ROLES` and `team_opex` in the capital plan | Re-read 11.3–11.4 and 17.3 |
| A stage budget line | `S0`, `S1`, `LAUNCH_ONEOFF` | Re-read 11.2 and 11.4 |
| Funding events | `paths` at the bottom of the capital plan | Re-read 15.5 |
| FX | `FX`, `FX_STRESS` | Re-run everything |

Always append a line to the change log (23.2).

# APPENDIX B — SOURCES AND HOW TO RE-VERIFY
**Model and service prices (consulted 2026-09-19):** official provider pricing pages — Anthropic (API pricing docs), OpenAI (API pricing), Google (`https://ai.google.dev/gemini-api/docs/pricing`), Groq, Mistral, DeepSeek, Cerebras, OpenRouter, E2B, Tavily, Exa, Brave, Pusher, Azure Speech, Supabase, Upstash — plus secondary comparisons for Sonnet 5 versus Terra and Gemini Flash (Akash Network comparison; BenchLM). Re-record exact URLs at the next quarterly check.
**Funding and ecosystem (consulted 2026-09-20):**
- Startup funding H1 2026 and 2025 review — LightCastle Partners / Startup Bangladesh Ltd (`startupbangladesh.vc` reports; Dhaka Tribune 28 Jul 2026; The Financial Express)
- Startup Bangladesh Ltd history and cancelled 10 Minute School proposal — Wikipedia (citing The Daily Star, Dhaka Tribune, bdnews24)
- 10 Minute School funding history — Future Startup articles (2022, 2023)
- Bangabandhu Innovation Grant and iDEA — The Daily Star (BIG 2021), TBS News (BIG 2023 registration; Startup Bangladesh Tk 43 crore), Dhaka Tribune (BIG round 3), UNB (Huawei ICT Incubator 2022)
- Global competitions — GEN (Entrepreneurship World Cup 2026), StartupGrants India (Startup World Cup, hackathon pools)
- Startup credit programs — fin.ai program guides; Deepak Gupta credit comparisons (2026)
- SAFE/instrument recognition and offshore flips — Dhaka Tribune op-ed on company law; IDLC interview (Bangladesh Angels substack); The Financial Express on SAFE; OGR Legal on FEID Circular No. 02 of 27 Mar 2025 and on startup tax provisions
- Startup VAT and tax — LookupTax (SRO 147; VAT guidelines); LightCastle budget analysis; Future Startup (FY2026-27 budget); Rahman Rahman Huq / KPMG Bangladesh Tax 2026
- Dilution and valuation — Carta (pre-seed and SAFE data), EightX (dilution per round), Peony (round guides), Mean CEO (valuation stats), Beancount.io and Livmo (small-SaaS multiples)
- Startup failure and runway — CB Insights via Startups.com/Launchrock, Stealth Agents runway and failure statistics, VC Corner
- AI unit economics — SaaStr, Aakash Gupta (Replit and Cursor), Getmonetizely, yage.ai (Cursor repricing), arnon.dk
- Payments in Bangladesh — PhotonPay (Sep 2026), Dhaka Tribune (Apr 2024), Indie Hackers (Dodo Payments)
- Salaries — Levels.fyi (Dhaka), Paylab (Bangladesh), Arc / Plane (remote), Multiplier
- Rajshahi Hi-Tech Park — Bangladesh Hi-Tech Park Authority (rent listing), The Financial Express, The Daily Star
- FX — market rate ≈ 123 BDT/USD (Pluang, 52-week range 120.94–123.34)

# APPENDIX C — GLOSSARY
**ARR / MRR** annualised / monthly recurring revenue · **CAA** Aspire Community Action Award · **Class S / A / E / B** Standard, Advanced, Expert, Brain model classes · **COGS at cap** cost to serve a user who uses every pool 100% · **EBITDA** gross profit minus OpEx · **ERQ** exporter retention quota account · **GP** gross profit · **Governor** the OpEx rule in 9.6 · **MAFU** monthly-active Free users · **MoR** merchant of record · **NBR** National Board of Revenue · **Plan A / Plan B** governed vs accelerated OpEx · **RJSC** Registrar of Joint Stock Companies · **SAFE** simple agreement for future equity · **SDE** seller's discretionary earnings · **SPV** special-purpose vehicle · **Stage S0–S4** capital stages in Part 11 · **Tech-A…H** stages of your technical roadmap.

---
*END OF RULEBOOK. Edit a price → re-run Appendix A → check the gates → update the change log.*
