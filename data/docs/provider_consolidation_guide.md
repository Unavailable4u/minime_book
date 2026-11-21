# Provider Consolidation Guide: Four Paid Models, Key Pools, One Search Key

*MiniMe: replace the free-tier key pool with paid Groq, Google and Anthropic accounts (each model lane is a pool you can grow by adding accounts), keep Perplexity Search as the only search provider, make reasoning effort follow the run's mode, manage every provider rate limit in one place, and delete the machinery that only existed to manage free keys, without touching anything that protects money, safety or history.*

**Version 2026-11-18.** Verified against MiniMe `3727ae3` (the `HEAD` of `Unavailable4u/MiniMe` when I cloned it; every count in section 3 was re-measured) and `Unavailable4u/minime_book` `91705bb`. This is the only document you need: it contains every decision, every patch, every test and every check. Where the repo's own docs (`MiniMe_Financial_Strategy_Rulebook.md`, `migration_guide.md`) disagree with this guide about which models Basic uses or which search provider it uses, **this guide wins** and PV-06 / PV-18 tell you which lines of those docs to update.

> **Evidence basis, read this first.**
> - **Read from the repo:** structure, docstrings, definitions, grep counts, config files.
> - **Checked on the web on 2026-11-18:** model prices, Haiku 5.5 API rules, the reasoning-effort options of Groq, Anthropic and Google, each provider's rate-limit rules and the Groq limits table, Perplexity Search API shape and price.
> - **Run:** a `pip install --dry-run` of the new Python packages against all 136 pinned lines in `backend/requirements.txt` (resolves cleanly; nothing installed).
> - **Not done:** no test suite was run, nothing was built, no live API call was made. Section 12 lists every claim I could not verify. Counts and line numbers drift, so **every patch starts with a grep** that measures the real code.

---

## 0. Hazards this guide is built around

Reading the code showed that "delete the free keys" is not safe as a single step. Each hazard below is real in the current code and each is handled by the patch named.

| # | Hazard (what would break) | Handled in |
| --- | --- | --- |
| H1 | **Search fails silently.** `utils/web_search.search()` swallows every failure and returns `[]`; its three callers (`agents/web_researcher.py`, `agents/part_price_finder.py`, `agents/component_spec_lookup.py`) treat `[]` as a normal answer. Removing Tavily/Exa keys without a replacement makes research and price lookups quietly return nothing. | **PV-05** puts Perplexity behind the same function first; the old keys go in PV-18 (names) and PV-20 (code and revocation). |
| H2 | **`eo/quota_sentinel.py` is not only key juggling.** It also holds `get_usage_history` and `get_usage_history_scoped` (the Token Usage tab), `get_ledger_event_counts` (read by `api/task_runner.py` at the end of every run) and `get_quota_snapshot` (15 call sites, the Panel, the frontend). Deleting the file breaks all of them. | **PV-15** slims it; it is never deleted. |
| H3 | **`eo/concurrency_gate.run_gated()` is called by `eo/executor.py` (parallel groups) and `agents/hardware_speccer.py` (price fan-out).** | **PV-15** keeps `GatedTask` and `run_gated()` with the same signature; only what is inside changes. |
| H4 | **The `anthropic` package is not one package.** Every current release needs `httpx2`, `httpcore2`, `docstring_parser`, `opentelemetry-api` and `truststore`; none is pinned in `requirements.txt`, and `httpx2` is not `httpx`. | **PV-02** gives six exact pins, verified to resolve against all 136 existing pins. |
| H5 | **Haiku 5.5 rejects some parameters the generic call path sends** (`temperature`, `top_p`, `top_k`, assistant prefill) and bills 5x above 100,000 prompt tokens. A generic step would return HTTP 400 or cost 5x. | **PV-02**. |
| H6 | **Embeddings go through HuggingFace with up to six keys** (`utils/embedding.py`, 16 non-test callers). Removing the keys without a replacement silently breaks memory search, the semantic cache, the knowledge graph and routing memory. | **PV-04**: a local model, no new package (the image already has `torch` and `transformers`). |
| H7 | **Old key names are stored inside in-flight state.** `key_overrides` appears in `eo/executor.py`, `eo/router.py`, `eo/loop_v4.py`, `eo/loop_controller.py` and `api/task_runner.py`. After the registry shrinks, a resumed run or an old Panel plan naming `GROQ_API_KEY_7` would raise `KeyError`. | **PV-01** adds a pure alias function; **PV-09** and **PV-10** call it. |
| H8 | **Cost numbers are wrong for the new models.** `config/credits.json` has Gemini 3.1 Flash-Lite cached input at 0.075 (Google's cache read is 0.025); the price table has gpt-oss-120b output at 0.75 (Groq charges 0.60); Haiku's long-prompt threshold counts cached tokens. | **PV-06**. |
| H9 | **`GROQ_API_KEY` and every other old key name hold free-tier keys today.** Reusing an old name for a paid key would put a free key into production by accident. | **PD-5**: production names are new (`PROD_*`); old names are retired in PV-18 and PV-20. |
| H10 | **DigiKey and Mouser are part-dimension lookups, not search.** Deleting the code removes a feature; removing only the keys does not. | Decision PD-9; **PV-18**. |
| H11 | **Non-Python places name the old keys:** `TokenUsageTab.jsx` has no colour for `anthropic` or `perplexity`; CI uses `CI_GROQ_API_KEY_1/2`; `config/mcp_servers.json` runs a Brave search server; `.gitleaks.toml` names old keys. | **PV-16**, **PV-18**. |
| H12 | **Worker pools assume many distinct accounts.** `eo/worker_pool._select_workers` returns at most as many workers as there are accounts, and `build_fallback_chain_excluding` removes the keys of sibling workers from a chain. With a handful of accounts the first silently cuts parallel workers in Expert and Beast modes and the second can return an empty chain. | **PV-09** and **PV-10**. |
| H13 | **The cooldown helpers are used outside `llm_client.py`:** `codeagent/adapters/openai_compat.py` calls `_is_cooling_down`, `_set_cooldown`, `_set_ledger_cooldown`, `_model_cooldown_id`; `eo/panel.py`, `agents/generic_worker.py` and `agents/code_writers.py` import `_is_cooling_down` and `_sorted_by_quota`. Deleting them breaks the code agent and the Panel. | **PV-14** keeps the names and rewrites them as a small in-process circuit breaker. |
| H14 | **Rate limits belong to the organisation (Groq, Anthropic) or the project (Google), not to the key.** A second key in the same organisation adds no capacity. The old pool of free keys only worked because every key came from a different free account. Limits are per minute, per day and (Anthropic, Google) also spend-based. | **PD-13**, **PV-07** (balancer), **PV-14**, **PV-19**. |
| H15 | **Reasoning effort ignores the run's mode.** `_GROQ_REASONING_EFFORT_BY_MODEL` in `llm_client.py` fixes gpt-oss at `low` for every call; Gemini and Haiku would run at their own defaults. The modes (`fast`, `simple`, `auto`, `expert`, `beast`; `eo/router.py` `MODE_CEILINGS`) never reach `llm_client`, and context variables do not cross into the worker threads that fan out most calls (`eo/usage_context.py` documents this). Reasoning tokens are billed as output. | **PD-12**, **PV-08**. |
| H16 | **An agent pinned to one key or model fails with it.** `eo/registry.py` itself records the earlier crash: `hardware_speccer` and `architecture_diagrammer` each had a one-entry chain pointed at one key, with no fallback. | **PD-11**, **PV-10**, **PV-12**. |

---

## 1. How to use this guide

- Work in order. A patch starts only when its dependencies are done and the test suite is as green as your PV-00 baseline.
- **One patch is one commit, tests first**, logged in `PATCHES.md`. Always write the `PV-` prefix so patch names never collide with other numbering in the repo (`MG-*`, `B03`, `D04`). `PATCHES.md` does not exist today; create it at the MiniMe repo root in PV-00.
- **Shared files, one writer at a time:** `backend/utils/llm_client.py`, `backend/eo/model_catalog.py`, `backend/utils/key_balancer.py`, `backend/config/provider_limits.json`, `backend/eo/registry.py`, `backend/eo/dynamic_chain.py`, `backend/agents/generic_worker.py`, `backend/utils/web_search.py`, `backend/requirements.txt`, `backend/.env.example`, `backend/config/*.json`, `.github/workflows/ci.yml`.
- **If you are also running the async-migration packages (`MG-B*` in `data/docs/migration_guide.md`):** `utils/llm_client.py` has six `time.sleep` calls (verified) and PV-14 rewrites that retry loop. **Finish PV-14 before any `MG-B` package touches `llm_client.py`**, otherwise you fix code this guide deletes.
- Each patch has **Do**, **Test**, **Done when**, **Rollback**. If a patch is wrong against the real code, stop and correct the assumption instead of forcing the change.
- **Nothing is lost.** Everything deleted stays in git: tag `pre-provider-consolidation` (PV-00). Every deletion is listed by file in `PATCHES.md`.

---

## 2. Decisions

| ID | Decision | Why |
| --- | --- | --- |
| **PD-1** | Four models, pinned exactly: `openai/gpt-oss-120b` and `openai/gpt-oss-20b` (Groq), `claude-haiku-5-5` (Anthropic), `gemini-3.1-flash-lite` (Google). No aliases, no `-latest`, no `openrouter/free`. | Cheapest set that covers every role; three model families for committee votes; a cross-vendor fallback for every role. |
| **PD-2** | Anthropic is called through the **native** `anthropic` SDK, not its OpenAI-compatible endpoint. | The compatibility endpoint is a testing layer: it ignores prompt caching and effort and returns no thinking. Haiku 5.5 is cheap only if you control effort and output, and caching matters for the code agent. |
| **PD-3** | Embeddings move off HuggingFace to a **local** `all-MiniLM-L6-v2` (same 384 dimensions), loaded with the `torch` + `transformers` already in the image. | `utils/embedding.py` calls HuggingFace with up to six keys. Deleting them without a replacement silently breaks memory search, the semantic cache, the knowledge graph and routing memory. A local model needs no key and keeps the Upstash Vector index valid (if the parity gate in PV-04 passes). |
| **PD-4** | **Strangler, not big bang.** Keep every public function name and signature callers use; change what is behind them; delete only when grep shows zero callers. | 51 non-test files contain a retired key name as code and 32 use the chain builders. Editing them all at once cannot be reviewed. |
| **PD-5** | **Keys are pools, one key per organisation.** Production: `PROD_GROQ_120B_KEY_1` (gpt-oss-120b), `PROD_GROQ_20B_KEY_1` (gpt-oss-20b), `PROD_GEMINI_KEY_1`, `PROD_ANTHROPIC_KEY_1`, plus `PERPLEXITY_API_KEY`. To grow, add `..._KEY_2`, `..._KEY_3` to the same pool, each from a **separate** organisation or project. **Dev, eval and CI use free-tier keys:** `DEV_GROQ_API_KEY`, `DEV_GEMINI_API_KEY`, optionally `DEV_ANTHROPIC_API_KEY`. | Capacity only grows with more accounts (section 4.6). New `PROD_` names cannot collide with the old names that hold free keys. CI does not need much, so free keys are enough. |
| **PD-6** | Scope is **Basic and Free**. Moderate and Ultimate are not live (their tier-map columns are `None`) and need models outside these four. Do not launch them on this stack. `eo/product_tier_map.py` and the Moderate/Ultimate rows in `config/plans.json` are **kept untouched**. | Their pools were costed on models this guide removes. Keeping the files keeps the future open. |
| **PD-7** | **Search = Perplexity Search API only.** One key, `PERPLEXITY_API_KEY`, called from the existing `utils/web_search.search()` seam. Tavily (10 keys), Exa and Brave are removed. No dev key: tests never call real search (the autouse stub in `tests/conftest.py`). | Perplexity's search endpoint returns ranked web results as data, takes a domain allow-list, and costs a flat $5 per 1,000 requests (a $1 fast mode exists; not used by default). One provider replaces a 10-key rotation plus its cooldown code. |
| **PD-8** | **Removed key list is exact** (section 2.1). Non-LLM infrastructure keys stay. | You asked to remove free keys and search extras, not infrastructure. |
| **PD-9** | **DigiKey keys are removed. `MOUSER_API_KEY` is left as is** (it is optional, free, not in your removal list, and is the only structured part-spec source once DigiKey goes). The DigiKey code path in `agents/component_spec_lookup.py` is **kept dormant** (it already returns `None` when its keys are unset). | These are part-dimension APIs, not search. Removing the keys costs nothing; deleting the code would remove a feature you may want back. Delete Mouser's key too if you do not want it; nothing else changes. |
| **PD-10** | The generic OpenAI-compatible call path (`_get_groq`, `_get_gemini`, `_call_step`) **stays**. Only the Cloudflare REST dialect, HuggingFace/Mistral/OpenRouter getters, and the pool/ledger machinery go. | Adding a future provider that speaks the OpenAI dialect is then one catalog row plus one client getter. Future Moderate/Ultimate models (larger Gemini, Sonnet/Opus) need only a new catalog row on code that stays. |
| **PD-11** | **No agent is pinned to a model or a key.** A role has a *preferred order* of models (its slot, section 4.1). The balancer chooses the key at call time. The Panel's account choices and `key_overrides` are **hints**, not pins. If the preferred model or key is busy, rate limited or failing, the call moves on to the next model, and after the slot's own models to every other model in the catalog. An unknown role runs on the `work` slot with a warning and never raises. | If an agent cannot run, another model does the job. |
| **PD-12** | **Reasoning effort follows the run's mode.** One table in the catalog (section 4.5) maps run mode × role class → effort, then to each provider's own parameter. `fast` and `simple` use the lowest effort the model allows for most roles; `beast` uses the highest. The mode reaches `llm_client` through a session-bound setting. | Reasoning tokens cost output prices; a simple task should not think as hard as a Beast build. |
| **PD-13** | **One balancer owns every rate limit** (PV-07). Per key it tracks in-flight calls, requests and tokens over the last 60 seconds, adaptive concurrency, `Retry-After` and health. Waiting is bounded (4 s for a non-final step, 20 s for the last); past that the call goes to the next step instead of hanging. Spend caps and budget alerts are set in each provider console. | Limits are measured, not guessed, and no call waits for ever. |

**Do not delete (these protect money and safety, they are not key juggling):** the credit and plan system (`eo/plans.py`, `eo/credits.py`, `eo/usage_ledger.py`, `eo/usage_context.py`, `config/plans.json`, `config/credits.json`), per-run cancel and loop guards (`eo/run_guard.py`, `eo/tool_budget.py`), user-facing auth and request limits in `api/server.py`, injection and output guards (`eo/injection_guard.py`, `eo/output_guard.py`, `eo/laya_gate.py`), retry on transient errors, continuation when output is cut off by length, the prompt-shrink path for 413, and the shutdown and pause hooks in `llm_client.py` (`request_shutdown`, `shutdown_requested`, `ShutdownRequested`, `RunStopped`, `PauseRequestedMidRetry`, `_interruptible_sleep`). Also kept: `log_usage` and its three storage keys (`usage:{provider}:{key_id}:{date}`, `usage_by_domain:*`, `usage_by_workspace:*`), the Upstash/Supabase/E2B/Pusher/Langfuse/Sentry integrations, and `eo/mcp_*` (only the Brave server entry is disabled).

### 2.1 Final key inventory

**Production (5):** `PROD_GROQ_120B_KEY_1`, `PROD_GROQ_20B_KEY_1`, `PROD_GEMINI_KEY_1`, `PROD_ANTHROPIC_KEY_1`, `PERPLEXITY_API_KEY`. **To add capacity later:** `PROD_GROQ_120B_KEY_2`, `_3`, and so on (same for the other pools). **One key per separate organisation or project; two keys from the same organisation share limits and add nothing.**
**Dev/eval/CI (free tier, never used in production):** `DEV_GROQ_API_KEY`, `DEV_GEMINI_API_KEY`, and optionally `DEV_ANTHROPIC_API_KEY` (to my knowledge Anthropic's API has no free tier; check its current terms; without this key, tests and evals that need Haiku are skipped). `MINIME_USE_DEV_KEYS=1` switches every pool to its dev key. You may copy the **value** of one of your existing free keys into a `DEV_*` name; do not keep the old name.

**Kept unchanged (non-LLM):** `ENVIRONMENT`, `ALLOWED_ORIGINS`, `FRONTEND_URL`, `SUPABASE_*`, `DATABASE_URL`, `DB_POOL_*`, `APP_THREAD_POOL_SIZE`, `UPSTASH_REDIS_REST_*`, `UPSTASH_REDIS_CACHE_*`, `UPSTASH_VECTOR_REST_*`, `CHAT_PAGE_CACHE_SIMPLE_HEURISTIC`, `E2B_API_KEY`, `PUSHER_*`, `GOOGLE_OAUTH_*`, `INTEGRATIONS_ENCRYPTION_KEY`, `GITHUB_MCP_TOKEN`, `CONTEXT7_API_KEY`, `SENTRY_DSN`, `LANGFUSE_*`, `DEVICE_JWT_SECRET`, `RUN_BUFFER_SECRET`, `MOUSER_API_KEY`, `GUARDRAILS_API_KEY` (referenced nowhere in code; leave it, harmless).

**Retired names (106, all verified present in `.env.example` at `3727ae3`; the bare `GROQ_API_KEY` is retired too, see the note below). 85 are removed from `.env.example` in PV-18; the 21 that a rollback path still needs (Tavily 10, Exa 1, HuggingFace 10) are removed in PV-20, and every old key is revoked at its provider in PV-20:**

| Group | Names |
| --- | --- |
| Groq (17) | `GROQ_API_KEY`, `GROQ_API_KEY_6` to `_14`, `GROQ_RESERVE_1`, `_2`, `SGA_GROQ_1` to `_3`, `EO_INSPECTOR_GROQ_KEY_1`, `_2` |
| Gemini (18) | `GEMINI_API_KEY_1` to `_18` |
| OpenRouter (13) | `OPENROUTER_API_KEY_1` to `_9`, `OPENROUTER_RESERVE_1` to `_3`, `EO_PANEL_OPENROUTER_KEY` |
| Cloudflare (24) | `CLOUDFLARE_API_KEY_1` to `_8`, `CLOUDFLARE_ACCOUNT_ID_1` to `_8`, `CF_SCANNER_RESERVE_1` to `_3` (each `_ACCOUNT_ID` and `_API_TOKEN`), `EO_PANEL_CLOUDFLARE_ACCOUNT_ID`, `EO_PANEL_CLOUDFLARE_API_TOKEN` |
| Mistral (10) | `MISTRAL_API_KEY`, `MISTRAL_API_KEY_2` to `_10` |
| HuggingFace (10) | `HUGGINGFACE_API_KEY`, `HUGGINGFACE_API_KEY_2` to `_10` |
| Search (12) | `TAVILY_API_KEY`, `TAVILY_API_KEY_2` to `_10`, `EXA_API_KEY`, `BRAVE_API_KEY` |
| Part lookup (2) | `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET` |

**Important:** every old name above holds a free-account key today, including the bare `GROQ_API_KEY` (and `HUGGINGFACE_API_KEY`). The production names are new on purpose (`PROD_*`), so an old free key can never be picked up by name. `HUGGINGFACE_API_KEY` and the Tavily and Exa names are removed only in PV-20, after the soak.

---
## 3. What the code does today (measured at `3727ae3`)

Re-run the commands in Appendix A before you start; if a number differs, trust your run.

| Area | Fact |
| --- | --- |
| Keys | `backend/.env.example` is 496 lines. 106 names are retired by this guide (section 2.1). Gemini has 18 numbered keys and no bare name; Groq has `GROQ_API_KEY` plus `_6` to `_14` plus reserve and intake keys; the repo has no Anthropic or Perplexity key. Every old key is a free-tier key. |
| Calls | `utils/llm_client.py` (4,294 lines) has one retry/rotation engine for every provider: `_walk_chain_once`, `_run_chain_step`, `_handle_transient_error`, `_ledger_gate`, `_call_step`, `generate_text`, `stream_completion`. Six `time.sleep` calls. Cloudflare has its own REST dialect (`_call_cloudflare_step`, branches near lines 2611 and 3595; PV-14 greps for all of them). Groq, Gemini, Mistral, HuggingFace and OpenRouter go through OpenAI-shaped clients (`_get_groq`, `_get_gemini`, `_get_mistral`, `_get_huggingface`, `_get_openrouter`). |
| Prices | `_TOKEN_PRICES_PER_MILLION` (near line 1964) feeds `_compute_cost_usd`. `config/credits.json` adds only the cached-input price for models already in that table. |
| Accounts | `eo/registry.py` (2,183 lines) holds `AGENT_CAPABILITIES`, about 50 account entries (PV-09 prints the exact list), keyed by env-var name. The Panel hires from it; `source_manager`, `worker_pool`, `generic_worker` and `dynamic_chain` read it. |
| Chains | 32 non-test files and 16 test files use the chain builders (`build_fallback_chain`, `build_fallback_chain_excluding`, `chain_step_for` and their private twins). `eo/dynamic_chain.py` is 458 lines; `agents/generic_worker.py` is 1,178. |
| Hardcoded names | 51 non-test files contain a retired key name **as code** (a string literal or identifier, not a comment or docstring): 270 hits, measured by the helper in Appendix A.2. |
| Pool machinery | `utils/rate_ledger.py` (1,401 lines), `eo/quota_sentinel.py` (531), `eo/concurrency_gate.py` (385), `eo/worker_pool.py` (86). `eo/product_tier_map.py` is imported by nothing at runtime. |
| Embeddings | `utils/embedding.py` calls HuggingFace with `HUGGINGFACE_API_KEY` and `_6` to `_10`; `embed_text*` has 16 non-test callers. `torch`, `transformers`, `tokenizers`, `onnxruntime`, `huggingface_hub` and `numpy` are already pinned in `requirements.txt` (the local `laya` guard uses them). |
| Anthropic | The `anthropic` package is **not** in `requirements.txt`. The word appears only in the `eo/credits.py` docstring (cache reads reported separately) and the `codeagent/adapters/__init__.py` docstring (an Anthropic adapter is planned second, after the OpenAI-compatible one). |
| Search | `utils/web_search.search(query, domains, max_results, agent_name)` tries Tavily (up to 10 keys, rotating) then Exa. It never raises. Callers: `web_researcher`, `part_price_finder`, `component_spec_lookup`. `config/mcp_servers.json` also runs a Brave MCP server. `eo/quota_sentinel.py` tracks Tavily usage per month. |
| Part lookup | `component_spec_lookup` tries DigiKey, then Mouser, and returns `None` when neither key is set. |
| Credits | `config/plans.json`: `credits_per_usd` 1000, Basic `credit_pool` 1690, Free 81. `config/credits.json` default price for an unknown model is 1.0 input / 1.0 cached / 3.0 output per million, and a unit test requires it to be at least as expensive as every priced model. |
| Tests | `tests/conftest.py` has an autouse fixture that replaces `search` in every module that binds it, so unit and integration tests never hit a real search API. |
| Frontend | `TokenUsageTab.jsx` has a `PROVIDER_COLOR` table (groq, openrouter, cloudflare, mistral, github, huggingface, gemini) and guesses a row's provider from its key name. |
| Secrets scan | On the clone at `3727ae3`, a regex scan of the working tree and of all history for `gsk_`, `AIza`, `sk-ant-`, `hf_`, `tvly-` found nothing. Re-run it in PV-00 and add the other patterns listed there. |

---

## 4. Target state

### 4.1 The four models, their key pools, the slots and the preferred agents

**Pools (one key per organisation; the pool grows by adding keys):**

| Pool | Serves | Production key names | Dev key (free tier) |
| --- | --- | --- | --- |
| `groq-120b` | `openai/gpt-oss-120b` | `PROD_GROQ_120B_KEY_1`, `_2`, ... | `DEV_GROQ_API_KEY` |
| `groq-20b` | `openai/gpt-oss-20b` | `PROD_GROQ_20B_KEY_1`, `_2`, ... | `DEV_GROQ_API_KEY` |
| `gemini` | `gemini-3.1-flash-lite` | `PROD_GEMINI_KEY_1`, `_2`, ... | `DEV_GEMINI_API_KEY` |
| `anthropic` | `claude-haiku-5-5` | `PROD_ANTHROPIC_KEY_1`, `_2`, ... | `DEV_ANTHROPIC_API_KEY` (optional) |

**Slots are a preferred order, never a pin.** Each role runs on the first model in its slot that has a free key; if that model is busy, rate limited or failing, the call moves to the next one, and **after the slot's own models every other model in the catalog follows as a last resort** (the tail rule), so no role ever depends on one model.

| Slot | Used for | Preferred order | Preferred agents (a recommendation, not a pin) |
| --- | --- | --- | --- |
| `fast` | Intake, classification, formatting, summaries, lookups | gpt-oss-20b → gemini-3.1-flash-lite → gpt-oss-120b | `eo/sga.py`, `eo/inspector.py`, `agents/responder.py`, `agents/output_organizer.py`, `eo/fact_summarizer.py`, `agents/source_quality_flagger.py`, `agents/overlapping_checker.py`, `agents/part_price_finder.py`, `agents/component_spec_lookup.py`, `eo/knowledge_graph.py` |
| `work` | Research, writing, analysis, planning, generic workers | gpt-oss-120b → claude-haiku-5-5 → gemini-3.1-flash-lite | `eo/panel.py`, `agents/idea_planner.py`, `agents/prompt_writer_lean.py`, `agents/report_writer.py`, `agents/documentation_agent.py`, `agents/dataset_analyst.py`, `agents/structure_architect.py`, `eo/hw_reference.py`, `eo/skill_library.py`, `agents/generic_worker.py` roles |
| `code` | Writing, fixing, reviewing, scanning code | claude-haiku-5-5 → gpt-oss-120b → gemini-3.1-flash-lite | `agents/code_writer_lean.py`, `agents/code_writers.py`, `agents/fixer_pool.py`, `agents/deploy_config_writer.py`, `agents/reviewer.py`, `agents/reviewer_fixer_lean.py`, `agents/security_scanner.py`, `agents/performance_reviewer.py`, `agents/dependency_mapper.py`, the code agent |
| `long` | Any call whose estimated prompt is over `LONG_PROMPT_EST_TOKENS` (4.3), whatever the role | gemini-3.1-flash-lite → gpt-oss-120b (only if it fits) | none: chosen by size |
| `vote-a`, `vote-b`, `vote-c` | Committee voters, one model **family** each | gpt-oss-120b, claude-haiku-5-5, gemini-3.1-flash-lite (each first for its own letter) | the reviewer committees |

You change this table in one file (`backend/eo/model_catalog.py`, created in PV-01). After PV-11 no other file names a model or a key.

### 4.2 Retry, waiting and concurrency (replaces cooldowns, ledgers and quota waits)

- **The balancer (PV-07) chooses the key for every call** (4.6). Waiting for a free key is bounded: **4 s** for a step that has a next step, **20 s** for the last step. Beyond that the call moves to the next step; it never hangs.
- **On HTTP 429:** if another key in the same pool is free, retry on it at once with no sleep. Otherwise wait the provider's `Retry-After` if it is at most **8 s** (`LLM_RETRY_AFTER_MAX_S`), and retry once on the same key; if it asks for longer, go to the next step. The 429 halves that key's concurrency and blocks it until the `Retry-After` time.
- **On 5xx, timeout or connection error:** retry after 1 s, then 2 s (plus up to 25% jitter), then go to the next step. At most 3 attempts per step.
- **On 401/403 or "credit exhausted":** mark that key unhealthy for 5 minutes (in the balancer) and go to the next key or step. When every key of every step is unhealthy, try them anyway in order: a run never fails without a real call.
- **Unchanged:** the continuation path when output is cut by length, the prompt-shrink retry on 413, the structured-list shrink, `_EmptyReasoningBudgetError`, and all shutdown, pause and cancel handling. If every step fails, raise `ChainExhaustedError`.
- **Spend protection is provider-side and in the credit system**, not in a free-tier ledger: spend limits and budget alerts in each provider console (PV-19), plus the existing credit pools and `run_guard`/`tool_budget`.

### 4.3 Anthropic call rules (Haiku 5.5, checked 2026-11-18)

- Price: **$0.10 input / $0.50 output** per million tokens for prompts up to 100,000 tokens; **$0.50 / $2.50** when a request's prompt is over 100,000 tokens (the higher rate applies to the whole request). Cache read $0.01 (up to 100K) or $0.05 (over). **Cache reads and writes count toward the 100,000.**
- Do not send `temperature`, `top_p` or `top_k` (not accepted). No assistant-message prefill. Effort goes in `output_config={"effort": "low" | "medium" | "high"}`; thinking is `adaptive` (disabling is allowed only at effort `high` or below). Thinking blocks come back empty unless you ask for a summary, so **read only blocks whose type is `text`**. Leave room in `max_tokens` for thinking.
- The tokenizer counts about **30% more tokens** than earlier Claude models for the same text, and the repo's own token estimator is a rough character ratio. Therefore **set the long-prompt limit to 75,000 estimated tokens** (`LONG_PROMPT_EST_TOKENS = 75_000` in the catalog) and re-calibrate it in PV-19 from logged `input_tokens` versus the estimate.

### 4.4 Search

`utils/web_search.search()` keeps its name, signature and "never raises" contract. Behind it: **Perplexity Search API only** (`POST https://api.perplexity.ai/search`). PV-05 builds it; PV-18 flips the default; PV-20 deletes the Tavily/Exa code and revokes their keys.

### 4.5 Reasoning effort by run mode

The modes in the code are `fast`, `simple`, `auto`, `expert`, `beast` (`eo/router.py` `MODE_CEILINGS`, `eo/modes.py`); today they only bound how many agents are hired. PV-08 makes them also set how hard each model thinks. **Roles have a class:** `light` (slot `fast`: intake, classification, formatting, lookups), `standard` (slots `work` and `long`: research, writing, analysis), `heavy` (slot `code` and the `vote-*` slots: code, review, security, committees). Overrides live in `ROLE_EFFORT_CLASS` in the catalog (recommended: `eo/panel.py` is `heavy`, because plan quality decides the whole run).

| Mode | `light` | `standard` | `heavy` |
| --- | --- | --- | --- |
| `fast` | min | min | low |
| `simple` | min | low | low |
| `auto` | low | low | medium |
| `expert` | low | medium | high |
| `beast` | medium | high | high |

These are **starting values to tune with the evals** (PV-19). The abstract level becomes each provider's own parameter:

| Level | gpt-oss on Groq (`reasoning_effort`) | Haiku 5.5 (`output_config={"effort": ...}`) | Gemini 3.1 Flash-Lite (`reasoning_effort` on the OpenAI-compatible endpoint) |
| --- | --- | --- | --- |
| min | `low` | `low` | `minimal` |
| low | `low` | `low` | `low` |
| medium | `medium` | `medium` | `medium` |
| high | `high` | `high` | `high` |

Facts behind the table: Groq's gpt-oss models accept only `low`, `medium` and `high` (there is no `none`; the repo's own comment on `_GROQ_REASONING_EFFORT_BY_MODEL` says so, and sending an unsupported value is an error, not a no-op); Gemini 3.x cannot switch thinking off, its lowest level is `minimal`, and `reasoning_effort` cannot be sent together with `thinking_level` (Google's OpenAI-compatibility page, 2026-11-18); Haiku 5.5 takes `low`, `medium` or `high` and does adaptive thinking. Reasoning tokens are billed as output tokens, so a lower level is a direct saving.

### 4.6 Rate limits and capacity

**What each provider limits (read on 2026-11-18; the numbers on your own Console pages win):**

| Provider | Limits apply to | What I found |
| --- | --- | --- |
| Groq (pay-as-you-go Developer plan) | the **organisation** (not the key); the docs table lists a row **per model** | `openai/gpt-oss-120b` and `openai/gpt-oss-20b`: 1K requests/min, 500K requests/day, 250K tokens/min each (one third-party page says 300K; use 250K). Free plan, for comparison: 30 requests/min, 1K requests/day, 8K tokens/min, 200K tokens/day. Cached tokens do not count. A 429 carries `retry-after`; `x-ratelimit-*` headers report the daily request limit and the per-minute token limit |
| Anthropic | the **organisation**, per model class: requests/min, input tokens/min, output tokens/min | The Haiku 5.5 figures are not in an Anthropic page I could read. One third-party page says they equal Haiku 4.5 (1,000 requests, 2M input and 400K output tokens per minute on the lowest tier; tier names unclear): **read Console → Limits**. For most models cached input tokens do not count toward the input limit. Bursts are smoothed (60 requests/min is enforced as about 1 per second). There is also a **monthly spend limit by tier** that rises automatically as you spend, and you can set your own lower limit in Console → Limits (one third-party page says daily: check) |
| Google (Gemini) | the **project** (not the key); daily request limits reset at midnight Pacific time | Per-model requests/min and tokens/min are shown only in AI Studio (I did not find Flash-Lite's). Tier 1 starts when billing is linked, with a $250 billing cap; Tier 2 needs $100 paid plus 3 days and has a $2,000 cap. A **spend-based limit per 10 minutes** ($10 Tier 1, $200 Tier 2 and 3) returns 429 `RESOURCE_EXHAUSTED` |
| Perplexity Search | not published | measure in PV-19 |

**Consequences for the design**

1. **More keys add capacity only if each key is a separate organisation (Groq, Anthropic) or Google Cloud project (Gemini).** The balancer treats every key as its own account; two keys from one organisation would be double-counted.
2. **Groq: your plan to use one account for gpt-oss-20b and another for gpt-oss-120b is supported** (two pools, section 4.1). Be aware that Groq's table lists limits per model, so inside one organisation each model already seems to have its own bucket; if that is right, the second account gives you separate spend tracking and a separate failure domain but **no extra capacity**. Confirm on `console.groq.com/settings/limits`. What does add capacity is more accounts in the **same** pool.
3. **Spend caps and tier rules bite before rate limits at small scale.** Capacity estimate (my assumptions, not facts: every user at the Basic cap of 4M tokens a month; the token mix of PV-06, 45% gpt-oss-120b, 15% gpt-oss-20b, 25% Haiku, 15% Gemini; a 70/30 input/output split, which makes the blended price per million tokens $0.285 for gpt-oss-120b, $0.1425 for gpt-oss-20b, $0.22 for Haiku, $0.625 for Gemini): a user at the cap costs about $0.22 on Haiku and $0.375 on Gemini (text only). A $100 monthly Anthropic spend limit then covers about **450** users at the cap and a $250 Google billing cap about **670** (fewer once image generation is counted). Both tier caps rise as you spend; check your current caps in each Console.
4. **Groq's per-minute tokens are the first limit to bind on a busy day.** Same assumptions plus: all usage inside 8 active hours a day and a peak of 3 times the average, which is 833 tokens a minute per user at the cap, of which 45% (375) go to gpt-oss-120b. With the balancer holding each key to 70% of 250K = 175K tokens a minute, one gpt-oss-120b key serves about **470** users at the cap (about 850 at 55% average utilisation); one gpt-oss-20b key about **1,400**. Plan to add a second gpt-oss-120b account before you reach roughly 400 active heavy users, and verify with PV-19's measurements.
5. **Pace, do not burst.** The balancer paces dispatches per key (Anthropic enforces limits over short intervals) and holds each key under `LLM_TARGET_FRACTION` (default 0.7) of its published limits.
6. **Unknown limits are learned.** Where a limit is not in `config/provider_limits.json` (Gemini, Anthropic, Perplexity until you fill them in), the balancer starts from a small concurrency, halves it on every 429 and raises it by one after 20 quiet seconds, so it finds the real ceiling without hanging.
7. **One process per container** (`backend.Dockerfile` runs one `uvicorn`, no `--workers`), so in-process accounting is exact for one container. If you run N containers, set `LLM_PROCESS_SHARE=1/N` so the containers together stay under the organisation's limits.

---

## 5. Safety matrix: what is kept, rewritten, slimmed, deleted

| File or thing | Decision | Patch | Why |
| --- | --- | --- | --- |
| `eo/plans.py`, `eo/credits.py`, `eo/usage_ledger.py`, `eo/usage_context.py` | **Keep** (data fixes only) | PV-06 | The meter that protects your money. |
| `eo/run_guard.py`, `eo/tool_budget.py` | **Keep** | none | Per-run cancel, loop and tool limits. |
| `eo/product_tier_map.py`, Moderate/Ultimate rows in `config/plans.json` | **Keep untouched** | none | Future tiers. |
| `eo/injection_guard.py`, `eo/output_guard.py`, `eo/laya_gate.py` | **Keep** (comment-only edit in `output_guard.py`) | PV-11a | Safety. |
| `eo/mcp_client.py`, `eo/mcp_registry.py`, `config/mcp_servers.json` | **Keep**, Brave entry set to `"enabled": false` | PV-18 | Only the keyless-dead server is switched off. |
| `agents/component_spec_lookup.py` (DigiKey/Mouser code) | **Keep dormant** | PV-18 | Returns `None` without keys. |
| `eo/model_catalog.py` | **New** | PV-01 | The only place a model or key name is written. |
| `utils/key_balancer.py`, `config/provider_limits.json` | **New** (per-key in-flight, request and token windows, adaptive concurrency, `Retry-After`, health, bounded waits) | PV-07 (module), PV-14 (wired in) | Replaces the ledger gate, the Redis cooldowns and the free-tier key rotation. |
| `eo/run_settings.py` | **New** (run mode bound to a session id) | PV-08 | Carries the mode to `llm_client` across worker threads. |
| `_is_cooling_down`, `_set_cooldown`, `_set_ledger_cooldown`, `_model_cooldown_id` (in `llm_client.py`), `_is_cooling_down`, `_sorted_by_quota` (in `eo/panel.py`) | **Keep the names, rewrite the bodies** | PV-14, PV-15 | The code agent adapter, the Panel, `generic_worker` and `code_writers` call them. |
| `utils/llm_client.py` | **Rewrite internals** (public names stay) | PV-02, PV-06, PV-08, PV-14 | One engine, four pools. |
| `eo/registry.py`, `eo/dynamic_chain.py`, `agents/generic_worker.py` | **Rewrite internals** (public names stay) | PV-09, PV-10 | Registry becomes a view of the catalog. |
| `utils/embedding.py` | **Rewrite internals** | PV-04 | Local model. |
| `utils/web_search.py` | **Rewrite internals**, then delete Tavily/Exa code | PV-05, PV-20 | Perplexity. |
| `eo/concurrency_gate.py` | **Rewrite internals** (`GatedTask`, `run_gated` stay) | PV-15 | Two live callers. |
| `eo/worker_pool.py` | **Simplify** | PV-09/PV-15 | Pick by role and slot. |
| `eo/quota_sentinel.py` | **Slim** to usage history, ledger event counts and a minimal snapshot; **never delete** | PV-15 | The Token Usage tab and `task_runner` read it. |
| `utils/rate_ledger.py` | **Delete** after zero imports | PV-15 | Free-tier window bookkeeping. |
| `_get_cloudflare_creds`, `_call_cloudflare_step`, `_CloudflareTransientError`, `_get_mistral`, `_get_huggingface`, `_get_openrouter`, `QUOTA_CONFIG`, cooldown helpers, headroom parsing | **Delete** after zero callers | PV-14 | Dead after the swap. |
| `check_hf_embedding.py` (in `backend/`) | **Delete** after the soak | PV-20 | Needs a HuggingFace key. |
| `.env.example`, `ci.yml`, `.gitleaks.toml`, `config/mcp_servers.json`, `TokenUsageTab.jsx` | **Edit** | PV-16, PV-18 | Names, colours, Brave server disabled. |
| Provider accounts and old keys | **Revoke last**, 14 days after go-live | PV-20 | They are your rollback. |

---

## 6. Rules (every patch obeys these)

1. **No production key is a free-tier key.** Check the console of each provider before the key goes into a deployment.
2. **Key values never enter git, logs, tests or chat.** `.env.example` holds names only. Log the key's *name*, never its value or a prefix.
3. **Exact model IDs.** No aliases, no `-latest`, no `openrouter/free`.
4. **Public names and signatures stay stable** until grep shows zero callers (PD-4).
5. **A deletion needs two proofs in the same commit:** `grep` shows zero callers outside the file, and the full test suite passes.
6. **Tests never call real providers.** Use the existing mocks; mark any real-call test `live` and keep it out of CI.
7. **Prices and API rules come from the provider's own page, dated in the file.** A third-party summary is marked `UNVERIFIED` in the file.
8. **Pin Python packages exactly, with their full dependency closure, and each at least 14 days old** at the time you pin. Re-run the age check in PV-02 on the day you apply it.
9. **Every read of a key goes through the catalog** (`pool_keys()`, `api_key()`, `perplexity_key()`, PV-01); no module calls `os.getenv` on a production key name after PV-11.
10. **Keep the rollback until the soak ends** (PV-20): old keys stay valid, the git tag stays, the `SEARCH_BACKEND` and `EMBEDDING_BACKEND` flags stay.
11. **No model ID and no key name appears outside the catalog** (and the price tables). Agents name a role, never a model.
12. **No agent is pinned.** A role, a Panel choice or a `key_overrides` entry may *prefer* a model or key; it may never *require* one (PD-11).
13. **Every wait is bounded** (4.2) and goes through an interruptible sleep, so a stop or shutdown always works.

---

## 7. Patch index

Sizes: S under half a day, M about a day, L two or more. "Needs" are hard dependencies.

| ID | Title | Size | Needs | Phase |
| --- | --- | --- | --- | --- |
| PV-00 | Baseline, tag, leak scan, counts | S | none | 1 Additive |
| PV-01 | Model catalog and legacy alias function | M | PV-00 | 1 |
| PV-02 | Anthropic native step in `llm_client.py` (and the six pins) | L | PV-01 | 1 |
| PV-03 | Anthropic adapter for the code agent | M | PV-02 | 1 |
| PV-04 | Local embeddings behind `utils/embedding.py` | M | PV-00 | 1 |
| PV-05 | Perplexity search behind `utils/web_search.search()` | M | PV-00 | 1 |
| PV-06 | Prices, credits, credit pools | M | PV-02 | 1 |
| PV-07 | Key balancer: the rate-limit manager (new module, not wired yet) | L | PV-01 | 1 |
| PV-08 | Reasoning effort by run mode (`run_settings`, effort table, provider parameters) | M | PV-01, PV-02 | 1 |
| PV-09 | Registry becomes a view of the catalog | L | PV-01 | 2 Swap |
| PV-10 | Chain builders on the catalog | L | PV-09, PV-08 | 2 |
| PV-11a to PV-11e | Replace hardcoded chains, five batches | L (x5) | PV-10 | 2 |
| PV-12 | Committees and reviewers by model family | M | PV-11e | 2 |
| PV-13 | Code agent endpoints | M | PV-03, PV-11c | 2 |
| PV-14 | Gut the retry engine in `llm_client.py` and wire in the balancer and the effort | L | PV-07, PV-08, PV-12, PV-13 | 3 Remove |
| PV-15 | Retire the pool machinery (slim `quota_sentinel`, keep `run_gated`) | L | PV-14 | 3 |
| PV-16 | API routes, Token Usage tab, frontend | M | PV-15 | 3 |
| PV-17 | Residue gate and test cleanup | M | PV-15 | 3 |
| PV-18 | Env, CI, MCP, docs; flip defaults; remove every key except the rollback ones | M | PV-05, PV-17 | 4 Cutover |
| PV-19 | Staging soak, canary, failure drills, spend limits, go-live | M | PV-18 | 4 |
| PV-20 | Remove rollback paths, delete the last keys, revoke old keys (14 days after go-live) | S | PV-19 | 4 |

Parallel-safe pairs: PV-04 and PV-05 may run beside PV-01 to PV-03 (they touch different files); PV-07 and PV-08 may run in parallel once PV-01 is merged. PV-11a to PV-11e are independent of each other once PV-10 is merged.

**What may reach production when.** PV-00 to PV-07 are additive and may be merged to `main` as you go; PV-08 changes live reasoning effort and is merged after its staging check. **Phases 2, 3 and 4 (PV-09 onward) stay on the `provider-consolidation` branch and run on staging only**; the first production deploy of the new stack is PV-19.

---
## 8. Phase 1: Additive patches (nothing is removed, nothing is switched yet)

### PV-00: Baseline, tag, leak scan, counts (S)

**Do**
1. From the MiniMe repo root: `git switch -c provider-consolidation` then `git tag pre-provider-consolidation`. Create `PATCHES.md` at the repo root with one line per patch: `PV-xx | date | commit | tests passed/failed`.
2. Run the suite exactly as CI does and record the numbers: `cd backend && pytest tests/unit tests/integration -q`. Some tests may already fail; write the exact failing test names in `PATCHES.md`. **No later patch may add a failure.**
3. Run every command in Appendix A and paste the output under "Baseline" in `PATCHES.md` (key-name file counts, `time.sleep` count, importers of each module this guide changes).
4. Secrets scan, working tree and full history, key-shaped strings (empty output = clean):
   ```bash
   git grep -nE '(gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-or-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{25,}|tvly-[A-Za-z0-9_-]{15,}|pplx-[A-Za-z0-9]{20,})' | sed -E 's/[A-Za-z0-9_-]{12,}$/<redacted>/'
   git log --all --oneline -G'(gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-or-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{25,}|tvly-[A-Za-z0-9_-]{15,}|pplx-[A-Za-z0-9]{20,})'
   git log --all --oneline -G'^(MISTRAL|CLOUDFLARE|OPENROUTER|EXA|DIGIKEY|MOUSER)_[A-Z_0-9]+=[A-Za-z0-9._-]{16,}'
   git log --all --diff-filter=A --name-only --format= -- '*.env' '.env' '.env.*' | grep -v '\.example$'
   ```
   Mistral, Cloudflare and Exa keys have no fixed prefix, which is why the third command looks for `NAME=value` assignments. **If anything prints, stop: that key is leaked. Revoke it at the provider first, then continue.** (A scan of the clone at `3727ae3` printed nothing for the first two patterns.)
5. Write down in `PATCHES.md`, for each provider console, **which keys are free-tier and which are paid**, without writing the key values. Every old key name holds a free-tier key today (including the bare `GROQ_API_KEY`). The paid production keys get **new names** (`PROD_*`, section 2.1) in PV-19, so an old free key can never be picked up by name. Dev, eval and CI keep using free keys under the `DEV_*` names.

**Test:** the suite equals the recorded baseline. **Done when:** tag, branch, `PATCHES.md`, baseline, scan results committed. **Rollback:** `git switch -` and delete the branch.

---

### PV-01: Model catalog, key pools and legacy alias function (M)

**Why:** after this patch there is exactly one place that names a model, a provider, a key pool or a preferred order, and one function that turns an old key name into a pool key (so a resumed run or an old Panel plan never raises `KeyError`).

**Do**
1. Create `backend/eo/model_catalog.py` (pure data and pure functions, no imports from `llm_client`, `registry` or `dynamic_chain`, to avoid circular imports):
   - `PROVIDERS`: `groq` and `gemini` (kind `openai_compat`, with `base_url`), `anthropic` (kind `anthropic`), `perplexity` (kind `search`). **Copy each `base_url` from the existing `_get_groq` and `_get_gemini` in `llm_client.py` (lines near 968 and 994); do not retype them.**
   - `POOLS` (section 4.1): `groq-120b`, `groq-20b`, `gemini`, `anthropic`; each `{provider, key_prefix, dev_key_env}` with prefixes `PROD_GROQ_120B_KEY_`, `PROD_GROQ_20B_KEY_`, `PROD_GEMINI_KEY_`, `PROD_ANTHROPIC_KEY_` and dev keys `DEV_GROQ_API_KEY` (both Groq pools), `DEV_GEMINI_API_KEY`, `DEV_ANTHROPIC_API_KEY`.
   - `MODELS`: four entries keyed by a short name, each `{provider, pool, id, max_output_tokens, supports_json_mode}`: `gpt-oss-120b` (`openai/gpt-oss-120b`, pool `groq-120b`), `gpt-oss-20b` (`openai/gpt-oss-20b`, pool `groq-20b`), `haiku-5-5` (`claude-haiku-5-5`, pool `anthropic`), `gemini-3-1-flash-lite` (`gemini-3.1-flash-lite`, pool `gemini`). Take `max_output_tokens` from each provider's model page; where you cannot verify a number, write `# UNVERIFIED` beside it.
   - `SLOTS`: the preferred orders of section 4.1 as ordered lists of `MODELS` keys. `tail_models(slot)`: every other model in the catalog, in a fixed order (the tail rule of PD-11).
   - `LONG_PROMPT_EST_TOKENS = 75_000` and `ANTHROPIC_PROMPT_BILLING_THRESHOLD = 100_000`.
   - `ROLE_TO_SLOT` (starts empty; PV-11 fills it) and `slot_for_role(role)`: **an unknown role returns `work` and logs one warning; it never raises** (PD-11).
   - `EFFORT_TABLE`, `ROLE_EFFORT_CLASS` and `effort_level(mode, role_class)`, `effort_value(level, model_key)`: the tables of section 4.5, as data only. PV-08 uses them.
   - `use_dev_keys() -> bool`: true only if the env var `MINIME_USE_DEV_KEYS` is `1`. CI, evals and local dev set it; production never does.
   - `pool_keys(pool) -> list[str]`: the **names** of the configured keys of a pool, sorted by number: in production every env var matching `^<key_prefix>(\d+)$` with a non-empty value; with `use_dev_keys()` only `[dev_key_env]` if it is set. `api_key(key_env) -> str | None` returns the value. `primary_key(pool) -> str`: the first configured key, or the name `<key_prefix>1` when none is set (so registries and tests always have a name). `perplexity_key() -> str | None`.
   - `slot_chain(slot, role=None) -> list[dict]`: the slot's preferred models, then `tail_models(slot)`; each step `{"provider", "model", "pool", "key_env", "effort_class"}`, where `key_env` is `primary_key(pool)` and is only a **hint** (the balancer picks the key at call time, PV-14). Read `eo/dynamic_chain.py` and keep every field the current steps carry.
   - `resolve_legacy_key_env(name, slot=None) -> str` (Appendix B). A new key name returns unchanged; an old Groq, Gemini, Mistral, OpenRouter, Cloudflare or HuggingFace name returns `primary_key` of the pool for `slot` (Gemini names: the `gemini` pool); an unrecognised name raises `KeyError`, so typos are not hidden.
   - `resolve_legacy_step(step, slot=None) -> dict`: if a stored chain step names a provider or model that is not in the catalog (for example `qwen/qwen3.6-27b`, `mistral-medium-latest`, `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, `openrouter/free`), return the primary step of `slot` instead and log one warning.
2. Add `backend/tests/unit/test_model_catalog.py`: every `SLOTS` entry references a real `MODELS` key and every model's pool exists; `slot_chain` for every slot ends with every catalog model exactly once (nothing missing, nothing duplicated); `slot_for_role("nope")` returns `work`; `pool_keys` finds `PROD_GROQ_120B_KEY_1` and `_2` in numeric order (monkeypatch env), ignores empty values, and with `MINIME_USE_DEV_KEYS=1` returns only the dev key; `primary_key` returns a name when nothing is set; every example in Appendix B maps as listed; the file contains **no key value** and no `os.getenv` of a literal production key name outside this module.
3. Add the names in Appendix C to `.env.example` **as names only, appended after the existing block**. Do not remove old names yet.

**Test:** the new unit tests plus the baseline suite. **Done when:** nothing imports the catalog yet except its test, suite equals baseline. **Rollback:** delete the file and the appended lines.

---

### PV-02: Anthropic native step in `llm_client.py`, and the six pins (L)

**Why:** `claude-haiku-5-5` cannot go through the OpenAI-shaped path (section 4.3 lists what it rejects), and the SDK's dependency chain is not in `requirements.txt`.

**Do**
1. **Pins.** On the day you apply this patch, confirm each version below is at least 14 days old and still the newest eligible; if not, pick the newest that is, and re-run step 2. Add to `backend/requirements.txt`, keeping its alphabetical style:
   ```
   anthropic==2.4.0
   docstring_parser==0.18.0
   httpcore2==2.16.0
   httpx2==2.16.0
   opentelemetry-api==1.45.2
   truststore==0.10.5
   ```
   (`annotated-types==0.7.0` and `typing-inspection==0.4.2` are already pinned. A dry run on 2026-11-18 against all 136 existing `==` pins resolved cleanly with `anyio 4.14.1`, `idna 3.18`, `jiter 0.16.0`, `pydantic 2.13.4`, `typing_extensions 4.16.0` unchanged. Release dates seen that day: anthropic 2.4.0 on 2026-11-02, httpx2 2.16.0 and httpcore2 2.16.0 on 2026-10-21, opentelemetry-api 1.45.2 on 2026-10-29, truststore 0.10.5 on 2026-10-12, docstring_parser 0.18.0 on 2026-04-14. `httpx2` 2.16.1 and 2.16.2 were two days old and must **not** be used.)
2. **Verify in a clean Python 3.12 venv** (the Dockerfile's Python):
   ```bash
   python3 -m venv /tmp/v && /tmp/v/bin/pip install -r backend/requirements.txt && /tmp/v/bin/pip check
   ```
   `pip check` must print "No broken requirements found". Then build the backend image once.
3. **Client getter.** In `llm_client.py` next to `_get_gemini`, add `_get_anthropic(key_env, timeout=None)` returning `anthropic.Anthropic(api_key=api_key(key_env), timeout=<timeout>, max_retries=0)` (`api_key` is the catalog's reader; PV-14 passes whichever key the balancer leased). **`max_retries=0` is required**: `llm_client` already retries; the SDK's own retries would multiply attempts and cost. For the streaming path mirror whichever client style the existing Gemini stream path uses.
4. **Step function.** Add `_call_anthropic_step(client, model, system_prompt, user_content, max_tokens, effort, json_mode, ...)` returning the same 4-tuple every step function returns: `(text, usage, finish_reason, headroom_headers)` (return `None` for headroom). Rules:
   - Call `client.messages.create(model=..., max_tokens=..., system=system_prompt, messages=[{"role": "user", "content": user_content}], output_config={"effort": effort})`, where `effort` is the step's `effort` field (`low`, `medium` or `high`; PV-08 sets it from the run mode; until then use `medium`). **Never pass `temperature`, `top_p`, `top_k`, or an assistant prefill.**
   - `text` = the concatenation of content blocks whose `type == "text"`. Ignore every other block type.
   - `json_mode`: add "Respond with one JSON object and nothing else." to the system prompt; do not prefill. Parse the way existing JSON callers already do.
   - `finish_reason`: map `end_turn` → `"stop"`, `max_tokens` → `"length"` (so the existing continuation logic works unchanged), `tool_use` → `"tool_calls"`, anything else → `"stop"`; log unknown stop reasons once.
   - `usage`: wrap the SDK usage in a small object shaped like what `_usage_details_from_usage` and `_log_usage` already read: `prompt_tokens = input_tokens + cache_creation_input_tokens + cache_read_input_tokens`, `completion_tokens = output_tokens`, cached tokens = `cache_read_input_tokens`. **Read `_usage_details_from_usage` (near line 1129) and the `eo/credits.py` docstring before writing it and match the field names exactly.** Check the field names against the Messages API usage object in Anthropic's docs.
5. **Dispatch.** Wherever the Cloudflare branch chooses its call function in `generate_text` and in the streaming path (`_walk_chain_once_stream`/`stream_completion`), add `provider == "anthropic"` → `_get_anthropic` + `_call_anthropic_step` (or its streaming twin via `client.messages.stream`), passed into `_run_chain_step` as `call_fn`. Teach `_status_code_from_exc` and `_retry_after_seconds` to read `anthropic.APIStatusError.status_code` and `response.headers["retry-after"]`.
6. **Output cap.** Extend `_max_tokens_for(provider, model, step)` (near line 2291) to return the catalog's `max_output_tokens` for Anthropic and to add room for thinking at effort `medium` and `high`.
7. **Do not add any chain that uses Anthropic yet**, and do not enable it for any role. Usage is priced in PV-06 first.

**Test**
- New `tests/unit/test_llm_client_anthropic.py` with a fake client: only `text` blocks are returned; a response with an empty thinking block and a text block returns the text; `temperature`/`top_p`/`top_k`/`prefill` are absent from the kwargs (`assert "temperature" not in kwargs`); `stop_reason` mapping; usage object maps cache tokens; a fake `RateLimitError` (status 429 with `retry-after: 3`) goes through the existing transient-error path and waits 3 s; `max_retries=0` is set.
- The whole suite equals baseline.
- One `manual`-marked test under `tests/manual/` makes one real call at each effort with `DEV_ANTHROPIC_API_KEY` (skip the test when it is unset), prints the stop reason and the usage object, and is run by hand once.

**Done when:** the unit tests pass, `pip check` is clean, the image builds, and no chain references Anthropic. **Rollback:** revert the commit (the six pins go with it).

---

### PV-03: Anthropic adapter for the code agent (M)

**Why:** `codeagent/adapters/__init__.py` says an Anthropic adapter was planned second after the OpenAI-compatible one. The code slot's primary is Haiku, so the agent needs it.

**Do**
1. Read `codeagent/adapters/openai_compat.py` and `toolcalls.py`. Create `codeagent/adapters/anthropic_native.py` implementing **the same interface** (same class shape, same events and tool-call representation the rest of `codeagent/` consumes). Map: internal tool definitions → Anthropic `tools`; Anthropic `tool_use` blocks → the internal tool-call format; internal tool results → `tool_result` blocks in the next user turn; streaming events → the internal stream events; cancel (`RunStopped`) must close the stream.
2. **Replay rule:** when you send an earlier assistant turn back (tool loops), send its content blocks **exactly as received** (including any thinking blocks), never rebuilt from text. Check this against the Messages API tool-use guidance for Haiku 5.5.
3. **Caching:** mark the system prompt, the tool definitions and the last stable user message with `cache_control` so repeated turns read from cache (cache read is 10x cheaper than input; a 5-minute cache write costs 1.25x input). Cached and written tokens still count toward the 100,000-token billing threshold (4.3), so keep the code agent's context under about 75,000 estimated tokens or route to the `long` slot.
4. Register it in `adapters/__init__.py`. Do not change `codeagent/wiring.py` yet (PV-13).

**Test:** golden-transcript tests that replay recorded Anthropic event streams (hand-written fixtures, no network) through the adapter and compare to the same internal events the OpenAI-compatible adapter yields for the equivalent run; a tool round trip; a cancel mid-stream; a 429. **Done when:** adapter tests pass and nothing selects the adapter yet. **Rollback:** delete the file and its registration.

---

### PV-04: Local embeddings behind `utils/embedding.py` (M)

**Why:** `embed_text()` (16 non-test callers) posts to HuggingFace with `HUGGINGFACE_API_KEY` or `_6` to `_10`. After this patch no key is needed, and the vectors stay compatible with the existing Upstash Vector index **if the parity gate passes**.

**Do**
1. **Find out what the old endpoint really returns before you replace it.** With one HuggingFace key still valid, embed five of your real stored texts with `embed_text()` and print each vector's length and L2 norm. The current code mean-pools an unpooled token matrix when that is what the endpoint returns, which would give **unnormalised** vectors; a pooled and normalised response gives norm about 1.0. Also check the **distance metric of your Upstash Vector index** (cosine vs dot product vs Euclidean). If the metric is not cosine, normalisation changes results: replicate exactly what the old vectors were (mean-pooled only, or mean-pooled and normalised).
2. In `utils/embedding.py` add `_local_embed(texts: list[str]) -> list[list[float]]` using the `torch` and `transformers` already installed: lazy singleton loaded under a lock; `AutoTokenizer` and `AutoModel` from `EMBEDDING_MODEL` (`sentence-transformers/all-MiniLM-L6-v2`) at a **pinned commit** (`EMBEDDING_REVISION`, copy the current `main` commit hash from the model page; do not use `main`); `max_length=256` (the model's own limit); mean pooling over the attention mask; L2 normalise **only if step 1 showed normalised vectors**; `torch.inference_mode()`; `torch.set_num_threads(int(os.getenv("EMBED_THREADS", "2")))`.
3. Add `EMBEDDING_BACKEND` (`local` or `hf`). `embed_text(text, key_env=...)` keeps its signature and, when the backend is `local`, ignores `key_env`. `embed_text_with_fallback(text, key_envs=None)` keeps returning a tuple and returns `(vector, "local")`. The `hf` path stays for now as the rollback. Default stays `hf` until the gate passes in staging.
4. **Download at image build, not at run time.** In `backend.Dockerfile` add one `RUN` that calls `huggingface_hub.snapshot_download(EMBEDDING_MODEL, revision=EMBEDDING_REVISION, allow_patterns=[config.json, tokenizer files, vocab.txt, special_tokens_map.json, model.safetensors])` into a baked `HF_HOME`, and set `HF_HUB_OFFLINE=1` at run time. An anonymous download needs no HuggingFace key.
5. **Parity gate** `backend/scripts/embedding_parity.py` (needs one HuggingFace key and a local model; run it by hand): take 200 real stored texts and 20 real queries; compute old and new vectors; report the minimum and mean cosine similarity per pair, the norm ratio, and, for the 20 queries, the overlap of the top-5 neighbours returned from the real index. **Gate (my engineering threshold, adjust only with a reason written in `PATCHES.md`): minimum cosine at least 0.98, mean at least 0.995, top-5 overlap at least 0.9.** If the gate fails, do **not** switch; the alternative is re-embedding the index into a new namespace, which is a separate decision.
6. Measure latency (one text, batch of 16) on your server and write p50/p95 in `PATCHES.md`; compare with the timeouts the 16 callers use. Optional: warm the model in a background thread at start-up, the same way the `laya` guard preloads.

**Test:** unit tests for shape 384; deterministic output; batch result equals single results; empty string behaves like the old function (read what the old one did and copy it); a text over 256 tokens is truncated and not an error; `EMBEDDING_BACKEND=hf` still uses the old path (mocked HTTP). **Done when:** the gate passes with numbers recorded, staging runs with `EMBEDDING_BACKEND=local`. **Rollback:** `EMBEDDING_BACKEND=hf` (the HuggingFace keys stay valid until PV-20).

---

### PV-05: Perplexity search behind `utils/web_search.search()` (M)

**Why:** `search()` is the single seam all three callers use. Its contract (never raises, returns `[{"url","snippet","title"}]`, empty list is a normal outcome) stays. Only what is behind it changes.

**API facts (Perplexity docs, 2026-11-18):** `POST https://api.perplexity.ai/search`, bearer key, JSON body with `query` (a string, or an array of up to five), `max_results` 1 to 20 (default 10), optional `search_domain_filter` (an allow-list, or a deny-list when entries start with `-`; up to 20 entries; one mode per request), `search_recency_filter`, `max_tokens_per_page`, and `search_type: "fast"`. Response `{"results": [{"title","url","snippet","date",...}]}`. Price: **$5 per 1,000 successful requests** (standard), **$1 per 1,000** for fast; no token charges; a multi-query request bills as one. Perplexity does not publish a default rate limit for this endpoint, so measure it in staging.

**Do**
1. Add `_search_perplexity(query, domains, max_results, agent_name) -> list[dict]` to `utils/web_search.py`:
   - Read the key with `perplexity_key()` from the catalog; no key → log once, return `[]`.
   - Body: `{"query": query, "max_results": clamp(max_results, 1, 20)}`; if `domains`, `"search_domain_filter": [bare lowercase domains, at most 20]` (allow-list only; callers pass domains to include).
   - Header `Authorization: Bearer <key>`; `timeout=REQUEST_TIMEOUT` (existing constant).
   - Up to 3 attempts: on `requests.RequestException`, 429 or 5xx wait 1 s, 2 s, 4 s (use `Retry-After` if present, capped at 10 s); on 400/401/402/403 log the status and the first 300 characters of the body, **do not retry**, return `[]`. A 401/402/403 is logged at error level because it means the key is dead or out of credit.
   - Map each result to `{"url": r["url"], "snippet": r.get("snippet",""), "title": r.get("title","")}`; skip results without a `url`; return at most `max_results`.
   - On success call `log_usage("perplexity", "PERPLEXITY_API_KEY", tokens=None, agent_name=agent_name)` (same call shape as the Tavily path today).
2. Add `SEARCH_BACKEND` (`perplexity` or `legacy`). `search()` keeps its first lines (`query = (query or "").strip()[:MAX_QUERY_CHARS]`) and then: `perplexity` → `_search_perplexity` only; `legacy` → today's Tavily then Exa. Default stays `legacy` until staging passes.
3. Do not touch `quota_sentinel` yet (it still reads Tavily usage; PV-15 removes that).

**Test** (all with a fake `requests.post`; the autouse fixture in `tests/conftest.py` already stops real search in other tests): result mapping; domains forwarded and truncated to 20; `max_results` clamped; 429 then 200 succeeds; 500 three times returns `[]`; 400/401 return `[]` without retry and the 401 logs at error level; missing key returns `[]` and logs once; `SEARCH_BACKEND=legacy` still reaches the Tavily mock. One `manual` test makes a real call with `PERPLEXITY_API_KEY`.
**Staging check:** run one real research task and one price lookup with `SEARCH_BACKEND=perplexity`; confirm non-empty results with plausible domains; log how many Perplexity requests one user-visible "search" costs (needed in PV-06).
**Done when:** unit tests pass and staging shows real results. **Rollback:** `SEARCH_BACKEND=legacy`.

---

### PV-06: Prices, credits, credit pools (M)

**Why:** the meter must charge the real rates of the four models before any chain uses them.

**Facts (provider pages and summaries read on 2026-11-18; re-open each provider's own pricing page when you apply this and write the date in the file, because prices change):**

| Model | Input $/M | Output $/M | Cached input $/M | Notes |
| --- | --- | --- | --- | --- |
| `openai/gpt-oss-120b` (Groq) | 0.15 | 0.60 | 0.075 | Groq prompt caching applies to the gpt-oss models |
| `openai/gpt-oss-20b` (Groq) | 0.075 | 0.30 | 0.0375 | |
| `claude-haiku-5-5` | 0.10 | 0.50 | 0.01 | Over 100,000 prompt tokens: 0.50 / 2.50 / 0.05, for the whole request. Cache reads and writes count toward the 100,000 |
| `gemini-3.1-flash-lite` | 0.25 | 1.50 | 0.025 | One third-party page still showed older, lower prices: use Google's own page |

**Do**
1. `utils/llm_client.py`, `_TOKEN_PRICES_PER_MILLION` (near line 1964): set the four rows above (gpt-oss-120b output currently reads 0.75 and Gemini Flash-Lite currently reads 0.075 / 0.30; both are wrong). Add `openai/gpt-oss-20b`, which today only exists as a full entry in `config/credits.json`. Remove nothing else yet (old rows are harmless; PV-14 removes them).
2. `_compute_cost_usd` and the `eo/credits.py` price lookup: support an optional **long-prompt tier** for a model: when the request's total prompt tokens (`input + cache_read + cache_write`) exceed the model's `threshold`, use the long row for the whole request. Put it in `config/credits.json` as `"claude-haiku-5-5": {"cached_input": 0.01, "long_prompt": {"threshold_prompt_tokens": 100000, "input": 0.50, "cached_input": 0.05, "output": 2.50}}` and give the table row the short-tier numbers. Read `eo/credits.py` first and extend it in the style it already uses.
3. `config/credits.json`: Gemini Flash-Lite `cached_input` 0.075 → **0.025**; delete the full `openai/gpt-oss-20b` entry (now in the table, where input and output are taken from); set the notes' "UNVERIFIED Gemini" sentence to the date and source of the new figures. Leave the unknown-model `default_prices_usd_per_million` at 1.0 / 1.0 / 3.0 (it is already at least as expensive as every row above, long tier included; the existing unit test must still pass).
4. **Credit pools** (the monthly credit allowance in `config/plans.json`, not key pools). Recompute, do not guess. Basic is 4.0M Standard-class tokens per month. With a 70% input / 30% output split (the rulebook's worker split) and an assumed token mix of 45% gpt-oss-120b, 15% gpt-oss-20b, 25% Haiku (up to 100K), 15% Gemini Flash-Lite, no cache discount (conservative): blended cost is **$0.298 per million tokens**, so 4.0M tokens cost about **$1.19**, which is **1,194 credits** at `credits_per_usd` 1000. The **mix is an assumption**; re-run with your real routing mix from PV-19's canary. Set Basic `credit_pool` to 1,194 in `config/plans.json` and update its `_notes`. **Free:** 81 credits buys about 272K tokens at this blended rate, not the 300K the plan promises; either set Free to 90 (recommended, costs $0.009 more per user) or leave 81 and accept 272K. Moderate and Ultimate rows: **leave untouched** (PD-6).
5. **Existing accounts.** `user_plans` rows store their own `credit_pool`. Run `SELECT plan, credit_pool, count(*) FROM user_plans GROUP BY 1, 2;`. If no paying users exist, change nothing else. If rows exist, change only new subscriptions (rulebook rule: pool sizes change for new subscribers first) and note the decision in `PATCHES.md`.
6. **Gate recompute (write the results in `PATCHES.md`):** Basic cost at cap = LLM $1.19 + search + images $0.27 + TTS $0.32 + sandbox $0.07. Search at Perplexity is $0.005 per request: if one user "search" is one request, 50 searches cost $0.25 and the total is **$2.10 (28.7% of the $7.31 local price)**; if measured PV-05 staging shows three requests per search, 50 searches cost $0.75 and the total is $2.60 (35.6%). Both pass the 45% limit. Re-run the rulebook's pricing script for the other three gates and update the rulebook's Basic LLM line, its search line ($0.008 per search is the old provider's price) and its model names.

**Test:** the price tables unit tests; a new test that a 60K-token Haiku call is charged at the short rate and a 110K-token call (or 60K plus 50K cache reads) at the long rate; the "default is at least as expensive as every row" test; `plans` tests for the new pools. **Done when:** tests pass and the four rows match the dated provider pages. **Rollback:** revert the commit.

---
### PV-07: Key balancer, the rate-limit manager (L)

**Why:** every provider limits per organisation or project, so capacity comes from the number of accounts, and the code must use each account's capacity fully without ever exceeding it and without ever making a user wait for long. This patch builds the manager as a new, tested module. **It is not wired into `llm_client.py` yet** (PV-14 does that), so it changes no behaviour.

**Do**
1. **`backend/config/provider_limits.json`** (data, not code). Per pool, the limits **of one key** (one key = one organisation):
   ```json
   {
     "_note": "Read from each provider's Console Limits page; null means unknown (the balancer then learns it from 429s). Groq figures: Groq docs 2026-11-18 (one third-party page lists 300K tokens/min).",
     "target_fraction": 0.7,
     "pools": {
       "groq-120b": {"rpm": 1000, "tpm": 250000, "rpd": 500000, "initial_concurrency": 6, "max_concurrency": 24},
       "groq-20b":  {"rpm": 1000, "tpm": 250000, "rpd": 500000, "initial_concurrency": 8, "max_concurrency": 32},
       "gemini":    {"rpm": null, "tpm": null, "rpd": null, "initial_concurrency": 8, "max_concurrency": 32},
       "anthropic": {"rpm": null, "itpm": null, "otpm": null, "initial_concurrency": 6, "max_concurrency": 24}
     },
     "dev": {
       "groq-120b": {"rpm": 30, "tpm": 8000, "initial_concurrency": 1, "max_concurrency": 2},
       "groq-20b":  {"rpm": 30, "tpm": 8000, "initial_concurrency": 1, "max_concurrency": 2},
       "gemini":    {"rpm": null, "tpm": null, "initial_concurrency": 1, "max_concurrency": 2},
       "anthropic": {"rpm": null, "itpm": null, "otpm": null, "initial_concurrency": 1, "max_concurrency": 2}
     }
   }
   ```
   **Before you rely on it, open each Console's Limits page and fill in the real numbers** (Anthropic: requests, input tokens and output tokens per minute for Haiku 5.5; Google: AI Studio's rate-limit page for Flash-Lite). The `dev` section is used when `MINIME_USE_DEV_KEYS=1` (free tiers are tiny: Groq's free plan is 30 requests and 8K tokens a minute per model, so a single prompt over 8K tokens can never succeed there).
2. **`backend/utils/key_balancer.py`** (imports only the catalog and the standard library; no import from `llm_client`). Public API:
   ```python
   class PoolBusy(Exception): ...          # carries .wait_hint_s
   class Lease:                            # pool, key_env, est_tokens, started_at
       ...
   def acquire(pool, est_tokens, *, preferred=None, session_id=None, max_wait_s=4.0) -> Lease
   def release(lease, *, actual_tokens=None, outcome="ok", retry_after_s=None) -> None
       # outcome: ok | rate_limited | server_error | timeout | auth | billing | cancelled
   def is_blocked(key_env) -> bool
   def snapshot() -> dict                  # per key: in-flight, concurrency limit, requests and tokens in the last 60 s, blocked_until, unhealthy_until, 429 count, average wait; per pool totals
   ```
   Behaviour:
   - **Keys** come from `pool_keys(pool)` and are re-read every few seconds, so adding `PROD_GROQ_120B_KEY_2` and restarting (or even only setting it) adds capacity with no code change.
   - **State per key:** in-flight calls; a 60-second sliding window of requests and tokens; an adaptive concurrency limit starting at `initial_concurrency`; `blocked_until` (set by a 429); `unhealthy_until` (set by an authentication or billing failure, 5 minutes).
   - **`acquire` picks the best key.** A key is *free* when it is not unhealthy, not blocked, its in-flight count is under its concurrency limit, and adding this call keeps requests and tokens in the window under `target_fraction` of the pool's limits (a `null` limit is ignored). Among free keys choose the lowest load score, `max(in_flight / concurrency_limit, tokens_in_window / tpm, requests_in_window / rpm)`; if `preferred` is free and its score is within 0.15 of the best, choose `preferred` (a hint, never a pin). The call's `est_tokens` is added to the window at once and replaced by `actual_tokens` in `release`.
   - **If no key is free** wait in slices of at most 0.25 s (through the same interruptible wait the rest of the code uses, so `request_shutdown()` and run cancellation end it at once) until one is, **at most `max_wait_s` in total**; then raise `PoolBusy(wait_hint_s)`. The caller moves to the next step; it does not retry the same pool.
   - **Pacing:** per key, no more than `target_fraction * rpm / 60` dispatches a second sustained, with a burst of up to 10% of `rpm` (needed for Anthropic, which enforces limits over short intervals). Without a known `rpm`, no pacing.
   - **`release` learns.** `rate_limited`: halve the key's concurrency limit (minimum 1) and block the key until `now + clamp(retry_after_s, 1, 20)`. `ok`: after 20 quiet seconds without a 429 raise the limit by 1, up to `max_concurrency`. `auth` or `billing`: mark the key unhealthy for 5 minutes. If **every** key of a pool is unhealthy, `acquire` still hands out the least recently failed one rather than failing.
   - **Config knobs (environment):** `LLM_TARGET_FRACTION` (default 0.7), `LLM_ACQUIRE_WAIT_S` (4), `LLM_ACQUIRE_WAIT_LAST_S` (20), `LLM_RETRY_AFTER_MAX_S` (8), `LLM_PROCESS_SHARE` (default 1.0; with N containers set 1/N so together they stay inside the organisation's limits; it scales `rpm`, `tpm` and concurrency).
   - Thread-safe (one lock per pool); no network calls, no Redis, no database.
3. **Do not edit `llm_client.py`, the registry or any agent in this patch.**

**Test** (`tests/unit/test_key_balancer.py`, with a fake clock and fake sleep; no real time):
- With one key at concurrency 2, eight threads calling `acquire` hold at most 2 leases at a time; the third waits and gets a lease when one is released.
- With a 4 s budget and every key busy, `acquire` raises `PoolBusy` after 4 s of fake time, not before and not after.
- Two keys, equal load: calls alternate. One key loaded: the other is chosen. `preferred` is chosen only when its score is within 0.15 of the best.
- A key whose token window is full is skipped until the window slides; `null` limits are ignored.
- `release(outcome="rate_limited", retry_after_s=3)` halves concurrency, blocks the key for 3 s, and the next `acquire` uses the other key at once; with a single key it waits 3 s (within budget) or raises `PoolBusy` when the budget is shorter. `retry_after_s=60` blocks for 20 s (the clamp).
- Concurrency grows by 1 after 20 quiet seconds and never above `max_concurrency`.
- `auth` marks a key unhealthy for 5 minutes; with all keys unhealthy `acquire` still returns one.
- `request_shutdown()` during a wait raises `ShutdownRequested`; a stopped run raises `RunStopped`.
- Adding a second env key makes `snapshot()` show two keys without a restart of the test process.
- `LLM_PROCESS_SHARE=0.5` halves the effective limits.
- `snapshot()` never contains a key value, only key names.

**Done when:** the tests pass, the module has no import from `llm_client`, and `provider_limits.json` has your real numbers (or `null` with a note in `PATCHES.md`). **Rollback:** delete the module and the config file.

---

### PV-08: Reasoning effort by run mode (M)

**Why:** `llm_client.py` fixes gpt-oss at `low` and does not set anything for Gemini or Haiku, and the run's mode never reaches it. After this patch every call's effort comes from one table (section 4.5) and the run's mode, and works inside worker threads.

**Do**
1. **`backend/eo/run_settings.py`** (imports nothing from the codebase). `bind(session_id, mode)`, `unbind(session_id)`, `scope(session_id, mode)` (a context manager that binds and always unbinds), `mode_for(session_id) -> str` (returns `auto` when nothing is bound or the mode is not one of `auto`, `simple`, `fast`, `expert`, `beast`; case-insensitive). **Copy the design of `eo/usage_context.py`**: a context variable as the fast path and a session binding as the fallback, because context variables do not cross into `ThreadPoolExecutor` workers and `llm_client` calls already carry a `session_id`. Bindings must not leak: they end with their scope; if two live scopes share a session id, the later one wins and one warning is logged.
2. **Bind where a run starts, in a `with`/`finally`:** in `api/task_runner.py`: `run_task` (near line 986), `preview_task` (1154), `confirm_task` (1188), `run_task_from_template` (1256), right after the session id is known (some of them generate it; bind after that, the way `usage_context.attach_session` is used); in `api/routes/tasks.py` next to the `usage_context.scope(...)` that opens a resumed run (near line 583); and in `eo/executor.py`'s `execute_graph` (it already receives `mode`) as a second binding. The Inspector, SGA and Panel run **before** the executor, which is why `task_runner` must bind too. A mode value that is not one of the five is treated as `auto`.
3. **Resolve the effort once per call** in `llm_client._run_chain_step` (blocking and streaming): `level = effort_level(mode_for(session_id), step["effort_class"])`, then `effort_value(level, model_key)` per provider (section 4.5), and put it on a copy of the step as `step["effort"]`. A step without `effort_class` (a caller that built its own chain) uses class `standard`.
4. **Apply it where the request is built:**
   - Groq gpt-oss (`_call_step`, the `provider == "groq"` branch): replace the `_GROQ_REASONING_EFFORT_BY_MODEL` lookup by `reasoning_effort = step["effort"]` (`low`, `medium` or `high`, never `none`); keep `include_reasoning=False`.
   - Gemini (OpenAI-compatible client): add `reasoning_effort = step["effort"]` (`minimal`, `low`, `medium`, `high`). **Never send `thinking_level` or `thinking_config` in the same request** (they cannot be combined).
   - Haiku (`_call_anthropic_step`): `output_config={"effort": step["effort"]}` (`low`, `medium` or `high`).
5. **Make room for thinking.** Reasoning tokens count as output and come out of `max_tokens`, which is the cause of `_EmptyReasoningBudgetError`. Add `REASONING_HEADROOM = {min: 0, low: 512, medium: 2048, high: 6144}` tokens to the caller's `max_tokens` for these three models (capped at the model's `max_output_tokens`). **These four numbers are starting guesses**; PV-19 measures the real reasoning tokens per level and corrects them.
6. **Record what was used:** log one line per call at debug level (`mode`, `class`, `level`, `model`) and count calls per (mode, level) in memory so PV-16 can expose it next to the balancer snapshot.
7. The code agent gets the same effort (`codeagent/model_adapter.py` already takes `provider_options` such as `{"reasoning_effort": ...}`): wired in PV-13.

**Test** (`tests/unit/test_run_settings.py`, `tests/unit/test_effort.py`):
- For every mode × class × model the value is in the provider's allowed set: Groq only `low`, `medium`, `high`; Haiku only `low`, `medium`, `high`; Gemini only `minimal`, `low`, `medium`, `high`.
- A fake Groq client in a `fast` run receives `reasoning_effort="low"` on every call; a fake Gemini client receives `minimal` for `light` roles; in a `beast` run `standard` and `heavy` roles receive `high` and `light` roles `medium`.
- A call made **from a `ThreadPoolExecutor` worker** that has only the `session_id` still sees the run's mode.
- Two runs with different modes executing at the same time do not see each other's mode; after `scope` exits the binding is gone.
- A resumed run binds its mode again.
- An unknown mode behaves as `auto`.
- A Gemini request never contains both `reasoning_effort` and `thinking_level`/`thinking_config`; a Groq request never contains `reasoning_effort="none"`.
- `max_tokens` grows by the headroom and never exceeds the model's maximum output.
- One `manual`-marked test under `tests/manual/` makes one real call per provider (free `DEV_*` keys; skip Anthropic when unset) at the lowest and the highest level and prints the effort parameter sent, the reasoning tokens and the finish reason; it confirms Google's endpoint accepts `reasoning_effort` for `gemini-3.1-flash-lite`.

**Done when:** the unit tests pass and a staging run in `fast` mode and one in `beast` mode, on the same task, show clearly different reasoning-token counts in the usage log. **This patch changes live behaviour** (gpt-oss no longer runs at a fixed `low`; Gemini and Haiku calls now carry an explicit effort), so merge it to `main` only after that staging check. Chains built before PV-10 have no `effort_class` and use `standard`. **Rollback:** revert the commit.

---

## 9. Phase 2: The swap (callers move to the catalog; the old machinery is still present but unused)

### PV-09: Registry becomes a view of the catalog (L)

**Why:** the Panel, `source_manager`, `worker_pool`, `generic_worker` and about 20 agents read `AGENT_CAPABILITIES` (about 50 entries today, each with only three fields: `provider`, `strengths`, `natural_roles`). It must be rebuilt from the key pools without losing a single role tag and without changing how many parallel workers a mode gets.

**Do**
1. **Snapshot first.** From `backend/`, save what exists now as a fixture (commit it):
   ```bash
   python - <<'EOF'
   import json, eo.registry as r
   snap = {k: {"provider": v["provider"], "natural_roles": sorted(v["natural_roles"])} for k, v in r.AGENT_CAPABILITIES.items()}
   json.dump(snap, open("tests/fixtures/registry_before.json", "w"), indent=1)
   print(len(snap), "accounts;", len({t for v in snap.values() for t in v["natural_roles"]}), "distinct role tags")
   EOF
   ```
2. In `eo/registry.py` replace the literal `AGENT_CAPABILITIES = {...}` by `AGENT_CAPABILITIES = build_agent_capabilities()`: **one entry per configured production key** (every name `pool_keys(pool)` returns for the four pools; a pool with no key set gets one placeholder entry named `primary_key(pool)`, so the registry is never empty, for example in tests), each with exactly the same three fields (`provider`, `strengths`, `natural_roles`). `natural_roles` of **every** entry is the **full union** of the tags in the snapshot (every model can serve every role; the preference lives in the slot chains, PV-10). `strengths` come from a `strengths` field per pool in the catalog (start from your own measured results; mark anything unmeasured `UNVERIFIED`). Adding `PROD_GROQ_120B_KEY_2` to the environment therefore adds an account with no code change. Add `refresh_agent_capabilities()` for tests that change the environment. Leave `REAL_ACTION_ROLES`, `ROLE_ALIASES`, `get_role_prompt` and every other name in `registry.py` untouched.
3. **`eo/worker_pool.py::_select_workers(role_tag, worker_count, key_override=None, session_id=None, agent_name=None)`**: keep the signature, the `key_override` precedence, the "no accounts tagged" `RuntimeError` and the `worker_pool_selection` event. Replace the quota ranking with: return **exactly `worker_count` entries** by cycling through the configured keys, those of the role's preferred pool first. Today it returns at most as many entries as there are accounts, which would silently cut the parallel workers of Expert and Beast modes. The returned keys are **hints** (PD-11): the balancer decides at call time, and repeated keys are fine.
4. **`eo/panel.py`** (7 reads of the registry): wherever the Panel's output or a stored plan carries account names (`key_overrides`), pass every name through `resolve_legacy_key_env(name, slot=...)` **before** validating it, and treat the result as a **hint** (PD-11), never as a requirement. The Panel's prompt now lists the configured keys; read how it builds that list, make it say that a choice is a preference, and confirm it still reads well.
5. Do not touch `eo/product_tier_map.py` (kept for future tiers). Run `tests/unit/test_eo_product_tier_map.py` and `tests/unit/test_agent_code_editor.py`; if either asserts an old provider or account name, change that **test expectation** and list it in `PATCHES.md`.

**Test:** the union of `natural_roles` over the new entries equals the union in `registry_before.json`; every old tag still has at least one candidate; `_select_workers("implementer", 5)` returns five entries even when only four keys are configured, and `("implementer", 1)` returns one; with `PROD_GROQ_120B_KEY_2` added to the environment (and `refresh_agent_capabilities()` called) the registry has one more entry; `key_override` still wins; a plan containing `key_overrides={"report_writer": "GEMINI_API_KEY_14"}` resolves to `GEMINI_API_KEY`; the Panel hiring tests pass against three accounts.
**Done when:** the suite equals baseline except test expectations listed in `PATCHES.md`. **Rollback:** revert the commit (the old dict is in git).

---

### PV-10: Chain builders on the catalog (L)

**Why:** 32 non-test files call `build_fallback_chain`, `build_fallback_chain_excluding` or `chain_step_for` (or the private twins in `generic_worker.py`). Keep every name and signature; change only what is behind them. Steps now carry a **pool** and a **key hint**, never a pinned key.

**Do**
1. `eo/dynamic_chain.py`:
   - `PROVIDER_DEFAULT_MODEL` becomes `{groq: gpt-oss-120b, gemini: gemini-3.1-flash-lite, anthropic: claude-haiku-5-5}` read from the catalog.
   - `chain_step_for(agent_key)`: `resolve_legacy_key_env(agent_key)`, then the default step of that key's pool: `{"provider", "model", "pool", "key_env" (the hint), "effort_class"}`. A retired-provider name returns the default slot's primary step and logs a warning. An unknown name raises `KeyError` as today.
   - `build_fallback_chain(role, quota_status=None, max_steps=None)`: `slot_chain(slot_for_role(role), role)[:max_steps]`, which is the slot's preferred models **followed by every other catalog model** (the tail rule). The step's `effort_class` is `ROLE_EFFORT_CLASS[role]` if present, else the class of the slot (`fast` → `light`, `work` and `long` → `standard`, `code` and `vote-*` → `heavy`). `quota_status` is accepted and ignored. **An unknown role runs on `work` with one warning; it never raises.**
   - `build_fallback_chain_excluding(role, exclude_keys, quota_status=None)`: resolve legacy names in `exclude_keys`, build the same chain, and for every step whose key hint is in `exclude_keys` **clear the hint** so the balancer picks another key of that pool. **It never removes a step and never returns an empty chain** (with a few accounts, excluding sibling workers' keys would otherwise exclude everything; `agents/hardware_speccer.py::_populate_prices` relies on this function). Read the current docstring and keep its wording true or update it.
   - Leave `_rank_accounts`, `_candidate_pool`, `_ensure_cross_org_redundancy`, `_dynamic_max_chain_steps`, `_rank_by_live_headroom`, `_headroom_score`, `_org_for`, `_cloudflare_token_env_for` in place but unused. PV-15 deletes them after grep proves zero callers.
2. `agents/generic_worker.py` (1,178 lines; its private `_chain_step_for` near line 652 and `_build_fallback_chain` near line 710): make both thin wrappers over the `dynamic_chain` functions. At the one place where a Panel `key_overrides` entry is applied to a role, call `resolve_legacy_key_env(name, slot=slot_for_role(role))` and pass the result on **as the step's key hint** (PD-11). Review the ten places it reads `AGENT_CAPABILITIES`: each must still work when the registry has one entry per configured key.
3. **Resumed runs and stored plans.** Find where a chain or a plan is loaded back from storage: `grep -rn "resume" eo api | head` and read how the stored steps are used. Pass each stored step through `resolve_legacy_step(step, slot)` at that single loading point. If there is no such loading point, state that in `PATCHES.md` (nothing to do).
4. Existing chain tests (16 files, among them `test_dynamic_chain_cross_org_redundancy.py`, `test_dynamic_chain_headroom_score.py`, `test_dynamic_chain_redundancy_gate.py`, `test_key_override.py`) assert behaviour of the old ranking. Rewrite their **expectations** to the invariants below; never weaken an assertion about errors, cancellation or `ChainExhaustedError`, and list every changed test in `PATCHES.md`. Tests for deleted helpers (`_headroom_score`, cross-org redundancy) are removed in PV-17 together with the helpers, not here.

**Invariants to assert (one parametrised test over every tag in `registry_before.json`):** the chain is not empty; it ends with every catalog model exactly once (the tail rule); the first step is the slot's preferred model; the chain spans at least two providers (the old "cross-org redundancy" intent, now cross-provider); `build_fallback_chain_excluding(role, every configured key)` is not empty, has the same steps, and has no key hints left; `chain_step_for("GROQ_API_KEY_9")` is a `groq-120b` step whose hint is `primary_key("groq-120b")`; `chain_step_for("CLOUDFLARE_API_KEY_3")` returns the default step and warns; `chain_step_for("NOT_A_KEY")` raises; a stored step with model `qwen/qwen3.6-27b` resolves to its slot's preferred step; an unknown role yields the `work` chain and does not raise; with `MINIME_USE_DEV_KEYS=1` every hint is the dev key.
**Done when:** invariants pass, the suite equals baseline except listed test expectations, and a staging run of one Balanced build works end to end. **Rollback:** revert the commit.

---

### PV-11: Replace hardcoded chains and key names, five batches (L each)

**Why:** 51 non-test files contain a retired key name as code (a string literal or an identifier; docstrings and comments do not count). Measured at `3727ae3`: 270 hits. The bare old names `GROQ_API_KEY` and `GEMINI_API_KEY` count as retired, because the production names are new.

**The lint helper (create once, in the first batch).** `backend/tests/unit/_legacy_key_lint.py`:
```python
import ast, pathlib, re
LEGACY = re.compile(
    r"(MISTRAL|HUGGINGFACE|OPENROUTER|CLOUDFLARE|CEREBRAS)_(API_KEY|ACCOUNT_ID)"
    r"|(?<![A-Z_])GROQ_API_KEY(_\d+)?(?![A-Z_])|(?<![A-Z_])GEMINI_API_KEY(_\d+)?(?![A-Z_])|(?<![A-Z_])ANTHROPIC_API_KEY(?![A-Z_])"
    r"|EO_INSPECTOR_GROQ_KEY|EO_PANEL_|CF_SCANNER_|SGA_GROQ|GROQ_RESERVE|OPENROUTER_RESERVE"
    r"|TAVILY|EXA_API_KEY|BRAVE_API_KEY|DIGIKEY")

def code_hits(path):
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings and LEGACY.search(node.value):
            hits.append((node.lineno, node.value[:60]))
        elif isinstance(node, ast.Name) and LEGACY.search(node.id):
            hits.append((node.lineno, node.id))
    return hits
```
The new names (`PROD_*`, `DEV_*`, `PERPLEXITY_API_KEY`) are not matched, on purpose; the bare old names are, and so is `ANTHROPIC_API_KEY` (the SDK would read it from the environment by default, and this code always passes a key explicitly). `tests/unit/test_no_legacy_keys.py` holds a list `CLEAN_FILES` and asserts `code_hits(f) == []` for each; every batch appends its files.

**What each batch does to each file**
1. Replace module-level chain constants and hardcoded `{"provider": ..., "key_env": ...}` steps with a call made **at call time, not at import time** (import-time calls cause the circular imports `dynamic_chain.py` documents, and break tests that monkeypatch): `build_fallback_chain("<role>")` for a role-based call, or `slot_chain("<slot>")` for a fixed slot.
2. Add the file's roles to `ROLE_TO_SLOT` in the catalog in the same commit (the slot column below is the recommendation; confirm by reading the file's docstring).
3. **Keep every `agent_name=` string unchanged.** It is a usage label and a Token Usage key.
4. Remove calls such as `log_usage("huggingface", ...)` that belong to embeddings; the local model has no cost or quota.
5. Update that file's tests: change expectations that name old keys; never weaken what a test proves; list them in `PATCHES.md`.
6. Append the batch's files to `CLEAN_FILES`; the test must pass.

**Batches** (the 51 files; "also reads the registry" means the file reads `AGENT_CAPABILITIES` or has a private worker picker and must still work with whatever keys are configured: read its selection logic, and where it assumed more than three distinct accounts, call `worker_pool._select_workers`):

| Batch | Files with removed names in code | Recommended slot | Also reads the registry (check, even without a name hit) |
| --- | --- | --- | --- |
| **PV-11a** intake and routing | `eo/sga.py`, `eo/inspector.py`, `eo/panel.py`, `agents/responder.py`, `agents/idea_planner.py`, `agents/prompt_writer.py`, `agents/prompt_writer_lean.py`, `agents/output_organizer.py`, `eo/fact_summarizer.py` | `fast` (Panel and `idea_planner`: `work`) | `agents/idea_planner.py`, `agents/output_organizer.py`. Also edit the comment-only mention in `eo/output_guard.py`. The Panel's own chain used `EO_PANEL_OPENROUTER_KEY` and `EO_PANEL_CLOUDFLARE_*`: replace with `slot_chain("work")`. The inspector used `EO_INSPECTOR_GROQ_KEY_1/2`: replace with `slot_chain("fast")` |
| **PV-11b** research, writing, analysis | `agents/report_writer.py`, `agents/documentation_agent.py`, `agents/dataset_analyst.py`, `agents/structure_architect.py`, `agents/source_quality_flagger.py`, `agents/overlapping_checker.py`, `agents/content_adapter_pool.py` | `work` (`source_quality_flagger`, `overlapping_checker`: `fast`) | `agents/extraction_table_builder.py`, `agents/note_table_builder.py`, `agents/content_adapter_pool.py`, `agents/correction_locator.py`, `agents/source_manager.py`, `agents/source_planner_lean.py` |
| **PV-11c** code | `agents/code_writer_lean.py`, `agents/code_writers.py`, `agents/test_writer.py`, `agents/fixer_pool.py`, `agents/deploy_config_writer.py`, `agents/reviewer.py`, `agents/reviewer_fixer_lean.py`, `agents/security_scanner.py`, `agents/performance_reviewer.py`, `agents/dependency_mapper.py` | `code` | `agents/code_writers.py`. `security_scanner.py` had its own Cloudflare reserve accounts (`CF_SCANNER_RESERVE_*`): it now uses `slot_chain("code")` |
| **PV-11d** hardware | `agents/part_price_finder.py`, `eo/hw_reference.py`, `agents/component_spec_lookup.py`, `agents/hardware_speccer.py`, `eo/mech_mass.py`, `eo/mech_motion.py`, `eo/mech_thermal.py` | `fast` (`hw_reference`: `work`) | `agents/hardware_speccer.py`, `agents/mech_primitive_pool.py`, `agents/mech_section_pool.py`, `agents/mech_subsection_pool.py`. **`component_spec_lookup.py` keeps its DigiKey and Mouser code (PD-9); allowlist `DIGIKEY` for that one file in the lint and in PV-17** |
| **PV-11e** memory, graph, skills, diagrams | `eo/knowledge_graph.py`, `eo/skill_library.py`, `agents/architecture_diagrammer.py`, `agents/schema_diagrammer.py` | `fast` (`knowledge_graph`), `work` (`skill_library`, the diagrammers: they once crashed on a one-entry chain, so give them the full tail chain) | `agents/memory_search.py`, `agents/duplication_checker.py` (both call `embed_text`; confirm they need no change after PV-04) |

**Files with retired names that belong to other patches (do not edit them in PV-11):** `utils/llm_client.py` (PV-02, PV-14), `evals/promptfoo/providers/output_organizer_provider.py` (PV-18), `eo/registry.py` (PV-09), `eo/dynamic_chain.py` and `agents/generic_worker.py` (PV-10), `eo/quota_sentinel.py` (PV-15), `utils/embedding.py` (PV-04, PV-18), `utils/web_search.py` (PV-05, PV-20), `codeagent/wiring.py and `codeagent/hello.py` (PV-13), `evals/promptfoo/providers/role_provider.py`, `check_hf_embedding.py`, `scripts/test_all_keys.py`, `scripts/test_digikey_debug_fix.py` (PV-18).

**Roles that never carry a key name** (they already use the builders) need no edit, but **every role string they pass must appear in `ROLE_TO_SLOT`** when PV-12 turns strict mode on. List them with:
```bash
grep -rhoE 'build_fallback_chain(_excluding)?\(\s*"[^"]+"' --include=*.py backend | sed -E 's/.*"([^"]+)"/\1/' | sort -u
```
**Done when** (each batch): its files pass the lint, its tests pass, a staging run of a task that uses them returns a normal result, and the suite equals baseline except listed expectations. **Rollback:** revert the batch commit; batches are independent.

---

### PV-12: Committees, reviewers and the role-coverage test (M)

**Why:** the point of a committee is independent opinions: with three model families, voters must not all be the same model. And since no agent is pinned (PD-11), a new role must not need a code change to run, only a line in the catalog to run on its preferred model.

**Do**
1. Read the committee logic in `agents/reviewer.py` and `agents/reviewer_fixer_lean.py` (and any private `_select_workers` in `agents/extraction_table_builder.py` or `agents/fixer_pool.py`). Keep committee sizes and the consensus rule unchanged.
2. Give voter `i` the chain `slot_chain("vote-" + "abc"[i % 3])` so voters rotate through gpt-oss-120b, Haiku and Gemini as their *first* choice (each chain still ends with every other model, so a busy or failing voter model is replaced, not skipped). Replace each private picker by `worker_pool._select_workers` plus this rotation.
3. Add `tests/unit/test_role_coverage.py`: it runs the `grep` at the end of PV-11 (or imports each module's role strings) and **fails CI when a role passed to a chain builder is missing from `ROLE_TO_SLOT`**. At run time an unknown role still runs on `work` with a warning and never raises; the test exists so a new agent gets a deliberate preferred model.

**Test:** a committee of size 2 or more uses at least two model families; sizes and quorum are unchanged; if the first voter model is unhealthy the voter still answers through the rest of its chain; `slot_for_role("brand_new_role")` returns `work`; the coverage test passes on the current code and fails when a role is removed from `ROLE_TO_SLOT` in a scratch copy; the suite equals baseline. **Rollback:** revert the commit.

---

### PV-13: Code agent endpoints, leases and effort (M)

**Why:** `codeagent/wiring.py` and `codeagent/hello.py` name Groq, Mistral and OpenRouter keys. The code agent's adapters also make their own HTTP calls outside `generate_text`, so they must take part in the same rate-limit management and effort policy.

**Do**
1. `codeagent/wiring.py`: build the provider settings from `slot_chain("code")` and `PROVIDERS`: Anthropic through the native adapter (PV-03), Groq and Gemini through the OpenAI-compatible adapter. The "at least one provider key present" check uses `pool_keys(pool)` and its error message names the key families (`PROD_ANTHROPIC_KEY_1`, `PROD_GROQ_120B_KEY_1`, `PROD_GEMINI_KEY_1`).
2. **Leases.** Every request an adapter makes does `lease = key_balancer.acquire(pool, est_tokens, preferred=hint, session_id=..., max_wait_s=...)` first, uses `lease.key_env`'s key, and calls `key_balancer.release(lease, actual_tokens=..., outcome=<from the HTTP status>, retry_after_s=<header>)` in a `finally`. On `PoolBusy` the adapter goes to the next provider in `slot_chain("code")`. The cooldown helpers that `adapters/openai_compat.py` calls (`_is_cooling_down`, `_set_cooldown`, `_set_ledger_cooldown`, `_model_cooldown_id`) keep working because PV-14 rewrites them on top of the balancer.
3. **Effort.** Pass `provider_options` built from `effort_value(effort_level(mode_for(session_id), "heavy"), model_key)` (`reasoning_effort` for the OpenAI-compatible providers, `output_config.effort` for Anthropic).
4. `codeagent/hello.py`: advertise the same providers. **If `protocol/` or `daemon/` defines an enum or schema of provider names, add `anthropic` additively and keep every old value accepted**, so devices already paired with an older build do not break.
5. Update `tests/unit/test_codeagent_wiring.py`, `test_codeagent_hello.py`, `test_codeagent_adapter.py` expectations only.

**Test:** the three test files; a recorded code-agent run through each of the three providers using the fake transports the existing tests use; a 429 on the first provider moves the run to the next provider without sleeping longer than `LLM_RETRY_AFTER_MAX_S`; `PoolBusy` moves on. **Done when:** with `MINIME_USE_DEV_KEYS=1` the code agent starts with only `DEV_ANTHROPIC_API_KEY` set and with only `DEV_GROQ_API_KEY` set. **Rollback:** revert the commit.

---

## 10. Phase 3: Removal (the old machinery is deleted, one proven piece at a time)

### PV-14: Gut the retry engine in `llm_client.py`; wire in the balancer and the effort (L)

**Why:** `_walk_chain_once` → `_run_chain_step` → `_ledger_gate` / `_record_ledger_bookkeeping` / `_handle_transient_error` is a retry engine built around free-tier windows (reserve tokens in `rate_ledger`, wait for a window, rotate across dozens of keys, write 6-hour cooldowns to Redis). With paid accounts the engine needs exactly what PV-07 built: pick the least-loaded key of the model's pool, stay under the limits, wait a bounded time, reroute instead of hanging, and learn from 429s. This patch connects it, together with the effort of PV-08, and deletes the old engine. Everything that protects a run stays.

**Keep, by name (do not rename or change signature):** `generate_text`, `stream_completion`, `_walk_chain_once`, `_walk_chain_once_stream`, `_run_chain_step`, `_call_step`, `_call_anthropic_step`, `_get_groq`, `_get_gemini`, `_get_anthropic`, `_handle_finish_reason` and the continuation path, `_shrink_prompt_for_retry`, `_shrink_structured_list_prompt`, `_shrink_max_tokens_for_retry`, `_EmptyReasoningBudgetError`, `ChainExhaustedError`, `_StepUnwinnableError`, `classify_tool_intent`, `request_shutdown`, `shutdown_requested`, `ShutdownRequested`, `RunStopped`, `PauseRequestedMidRetry`, `_interruptible_sleep`, `log_usage` and its helpers (`_log_usage`, `_read_usage_record`, `_compute_cost_usd`, `_record_call_log`, `_record_usage_ledger`, `_probe_usage_shape`), `_record_ledger_event` and `get_ledger_event_stats` (they now count `provider_failure` and reroutes; the `/api/system/ledger-event-stats` route and `api/task_runner.py` read them), `_traced_generation` and `_end_traced_generation` (Langfuse).

**Do**
1. **Wire the balancer (PV-07) into `_run_chain_step`, blocking and streaming.** For each step: estimate the call's tokens (reuse `_estimate_tokens_for_call` or the prompt-size estimate the `long`-slot routing uses, plus `max_tokens`); `lease = key_balancer.acquire(step["pool"], est_tokens, preferred=step.get("key_env"), session_id=session_id, max_wait_s=<LLM_ACQUIRE_WAIT_S if another step follows, else LLM_ACQUIRE_WAIT_LAST_S>)`; build the client with `lease.key_env`'s key (`api_key(lease.key_env)`); make the traced call; in a `finally` call `key_balancer.release(lease, actual_tokens=<usage>, outcome=..., retry_after_s=<Retry-After header>)` with the outcome taken from the result (`ok`, `rate_limited` for 429, `server_error`, `timeout`, `auth` for 401/403, `billing` for a credit-exhausted error, `cancelled` when the run stops). Log which key was used under that key's **name** (`log_usage(provider, lease.key_env, ...)`), never its value. **`PoolBusy` means: go to the next step now** (record a `reroute` ledger event with `_record_ledger_event`). A step whose pool has no configured key is skipped with one warning. Steps with no `pool` (a caller that built its own chain from old code) get the pool of their provider and model from the catalog.
2. **Apply the effort of PV-08 in the same place** (already described there); nothing more to do here except make sure the balancer lease and the effort resolution both happen once per attempt.
3. **Rewrite the cooldown helpers with the same names and signatures** so the code agent's adapter (`codeagent/adapters/openai_compat.py` calls `_is_cooling_down`, `_set_cooldown`, `_set_ledger_cooldown`, `_model_cooldown_id`) and `eo/panel.py`/`agents/generic_worker.py`/`agents/code_writers.py` (they import `_is_cooling_down`, `_sorted_by_quota` from `eo/panel.py`) keep working, now on top of the balancer: `_set_cooldown(provider, key_id, exc)` → `release` semantics for `auth`/`billing` only (the balancer already marks the key unhealthy); `_set_ledger_cooldown(provider, key_id, wait_seconds)` → no-op; `_is_cooling_down(provider, key_id, model=None)` → `key_balancer.is_blocked(key_id)`; `_model_cooldown_id(key_id, model)` unchanged. **They no longer write to Redis**: with several containers each learns on its own (set `LLM_PROCESS_SHARE`, section 4.6).
4. **Replace the ledger gate.** Remove every `rate_ledger.*` call from `llm_client.py` (`reserve`, `release_reservation`, `record_usage`, `record_headroom`, `can_proceed`, `exceeds_tpm_ceiling`, `clamp_max_output_tokens`, `_tpm_limit_for`) and the functions that only existed to feed them (`_ledger_gate`, `_decide_ledger_action`, `_remaining_chain_headroom`, `_chain_exhaustion_wait`, `_record_ledger_bookkeeping`, `_extract_headroom_from_headers`, `_parse_reset_seconds`, and `_estimate_tokens_for_call` only if nothing else uses it). The `headroom_headers` slot in the 4-tuple stays (always `None`) so no step function changes signature.
5. **Rewrite `_handle_transient_error` to the policy in section 4.2**: keep its error classes (context length exceeded → shrink path; permanent authentication → the balancer marks the key unhealthy, next key or step; rate limit → another free key of the pool at once, else wait `Retry-After` if it is at most `LLM_RETRY_AFTER_MAX_S` (8 s) and retry once, else the next step; server error, timeout, connection → retry after 1 s and 2 s plus jitter, then the next step; at most 3 attempts per step). Waiting always goes through `_interruptible_sleep`. Remove the code that waited for a free-tier window to reset. The match for "credit exhausted" and authentication errors must be checked against each provider's real error body (for Anthropic a depleted balance is an HTTP 400 with a credit message); unit-test with a captured body.
6. **Replace `time.sleep` (six sites) with `_interruptible_sleep`.** Afterwards `grep -c 'time.sleep' utils/llm_client.py` prints 0.
7. **Delete the dead provider code:** `_CloudflareTransientError`, `_get_cloudflare_creds`, `_call_cloudflare_step`, every `provider == "cloudflare"` branch (near lines 2611 and 3595 and any others `grep -n cloudflare utils/llm_client.py` finds), `_get_mistral`, `_get_huggingface`, `_get_openrouter`, and the `openrouter`-only branches in `_call_step` and the stream path (the Groq-specific branch in `_call_step` stays). In `_TOKEN_PRICES_PER_MILLION` delete rows for models no chain uses any more (historical usage rows already store their cost, so nothing is lost). **Leave `QUOTA_CONFIG` and `get_quota_snapshot`'s imports for PV-15**; `eo/quota_sentinel.py` still imports `QUOTA_CONFIG`.
8. Tests: first list every test file that targets what you delete: `grep -rlE 'rate_ledger|_ledger_gate|_decide_ledger_action|cloudflare|_get_mistral|_get_huggingface|_get_openrouter|headroom' backend/tests`. Delete a test only if it tests a function you deleted; rewrite the rest. Add tests for the new behaviour:
   - with one key per pool, the call after the concurrency limit waits (fake clock) and then proceeds; with the wait budget exhausted it moves to the **next step** at once and a `reroute` event is recorded; with two keys in the pool it uses the second key without waiting;
   - `request_shutdown()` while waiting for a key raises `ShutdownRequested`; a stopped run raises `RunStopped`;
   - 429 with `Retry-After: 3` and a second free key: the call is retried on the second key with no sleep; with no second key it waits 3 s and retries once; `Retry-After: 60` goes to the next step without waiting; all steps failing raises `ChainExhaustedError` with the same message shape as before;
   - a 401 marks that key unhealthy, the next call skips it (using another key or step), and it is tried again after expiry (fake clock); when every key is unhealthy a call is still attempted;
   - the 413 shrink path, the empty-reasoning path and the continuation path still pass their existing tests;
   - `_set_cooldown` on a 429 does **not** mark the key unhealthy;
   - the lease is **always** released (success, exception, cancellation): after each test `key_balancer.snapshot()` shows zero in-flight calls;
   - the streaming path does the same as the blocking path for each of the above;
   - the usage log names the leased key (`PROD_GROQ_120B_KEY_2`), never a value.

**Gate (all must print nothing):**
```bash
cd backend
grep -nE 'rate_ledger\.|time\.sleep|_call_cloudflare_step|_get_cloudflare_creds|_get_mistral|_get_huggingface|_get_openrouter|_CloudflareTransientError' utils/llm_client.py
python - <<'EOF'
import ast, sys
src = open("utils/llm_client.py", encoding="utf-8").read()
tree = ast.parse(src)
bad = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "utils" and any(a.name == "rate_ledger" for a in n.names)]
sys.exit(1 if bad else 0)
EOF
```
**Done when:** gate clean, suite equals baseline except listed deletions and rewrites, and a staging run with each pool's key blanked in turn still completes tasks through the fallback, and a 20-way fan-out run never hangs longer than the wait budgets (PV-19 repeats both as drills). **Rollback:** revert the commit (the helper names kept the old callers working, so nothing else changed).

---

### PV-15: Retire the pool machinery (L)

**Do, in this order, one commit per step**

**13a. `eo/concurrency_gate.py` (385 lines).** `eo/executor.py` (parallel groups) and `agents/hardware_speccer.py` (price fan-out) call `run_gated(tasks, session_id)`; both depend on its result ordering and error handling.
- **First** write characterization tests against the current file using fake tasks: result order equals task order; one failing task does not cancel the others and its exception is reported the way callers expect; `session_id` events (if any) fire as today; usage logged inside a task is attributed to the **parent's** session and user (the file imports `eo.usage_context` to carry context into worker threads; the credit ledger depends on this).
- **Then** rewrite the internals: keep `GatedTask` (same fields) and `run_gated` (same signature, return type and error behaviour); each task runs in a thread pool bounded by the number of tasks and the size cap the current file already uses; the task's own LLM call goes through `generate_text`, which takes a balancer lease (PV-14), so the gate itself no longer needs to limit anything. Delete the reservation, admission-loop and `rate_ledger` code. The characterization tests must stay green unchanged except the ones that tested reservations.

**13b. `eo/quota_sentinel.py` (531 lines): slim, never delete.** Read its callers first (15 call sites of `get_quota_snapshot`, the Token Usage tab, `api/task_runner.py`).
- **Keep as is:** `get_usage_history`, `get_usage_history_scoped`, `get_ledger_event_counts`.
- **Keep the name and the shape of `get_quota_snapshot()`**, but compute it without `rate_ledger`: for each account in `AGENT_CAPABILITIES` (one per configured key) plus one extra entry for `PERPLEXITY_API_KEY` (unit `requests`), return **every field the current snapshot returns** (`used`, `quota`, `pct`, `unit`, `unmetered`, `cooling_down`, …) with `quota` = `None`, `pct` = `None`, `unmetered` = `True`, `cooling_down` = `_is_cooling_down(...)`, and `used` read from the existing per-day usage counters. (The module's own docstring already says `quota`/`pct` are `None` where no verified figure exists, so every consumer already handles that.)
- **Also include Perplexity in the usage history**: add `("perplexity", "PERPLEXITY_API_KEY")` to the list of metered keys `get_usage_history` walks, otherwise search usage vanishes from the Token Usage tab (Tavily had its own special case).
- **Delete:** `check_and_alert`, `get_rate_window_snapshot`, `_tavily_usage_this_month` and the Tavily account special case, the Cloudflare neuron code, and the import of `rate_ledger` and `QUOTA_CONFIG`.

**13c. Dead helpers.** In `eo/dynamic_chain.py` delete `_rank_accounts`, `_candidate_pool`, `_ensure_cross_org_redundancy`, `_dynamic_max_chain_steps`, `_rank_by_live_headroom`, `_headroom_score`, `_org_for`, `_cloudflare_token_env_for` **only after** `grep -rn "<name>" backend --include=*.py` shows no caller outside tests. In `eo/panel.py` keep `_is_cooling_down` and `_sorted_by_quota` (three files import them) and make them trivial (`_is_cooling_down` reads `key_balancer.is_blocked`; `_sorted_by_quota` returns its input in the given order). In `eo/worker_pool.py` remove the `get_quota_snapshot` import if nothing uses it.

**13d. Delete `utils/rate_ledger.py` (1,401 lines)** when this prints nothing:
```bash
grep -rnE '(from|import) .*rate_ledger' backend --include=*.py | grep -v '^backend/tests/'
```
and delete the headroom helpers and `QUOTA_CONFIG` from `llm_client.py` once `grep -rn QUOTA_CONFIG backend --include=*.py` shows only tests. Delete the tests that targeted the deleted module (`grep -rl rate_ledger backend/tests`), after listing each in `PATCHES.md` with the reason.

**Test:** the characterization tests; `run_gated` end to end through an executor fixture; the snapshot returns the same field names as before for every configured key plus Perplexity; the usage-history route returns the same JSON shape with one row per configured key and a Perplexity row; `api/task_runner.py`'s ledger-event summary still works.
**Done when:** the importer gate prints nothing and the suite equals baseline except listed deletions. **Rollback:** revert the last step's commit only (each step is separate).

---

### PV-16: API routes, Token Usage tab, frontend (M)

**Do**
1. `api/routes/system.py`: keep every route and its JSON shape (`/api/quota`, `/api/usage/history`, `/api/system/ledger-event-stats`). In `/api/quota` (near line 245) drop only the part that merged live rate-window headroom (it came from `rate_ledger`); leave the keys present with `null` values if the frontend reads them. Read `AppShell.jsx`, `SessionContext.jsx` and `NotebooksTab.jsx` (they also touch the quota/usage routes) to confirm nothing breaks on `null`.
2. `frontend/app/components/tabs/TokenUsageTab.jsx`: add `anthropic` and `perplexity` to `PROVIDER_COLOR` (pick two colours not used there; the file says they are data-series colours and must stay distinct). **Do not remove** the old provider colours (history from before the switch may still be shown). The provider is guessed from the key name by upper-case substring, so `PROD_ANTHROPIC_KEY_1`, `PROD_GROQ_120B_KEY_2` and `PERPLEXITY_API_KEY` match once the entries exist. Remove the Cloudflare "neurons" branch only if the backend no longer sends that unit.
3. Update `frontend/app/lib/__tests__/usage.test.mjs` fixtures to the new snapshot (one row per configured key and Perplexity).
4. **Measurement route.** Add `GET /api/system/key-balancer-stats` next to the other system routes (same authentication): it returns `key_balancer.snapshot()` (per key: in-flight, concurrency limit, requests and tokens in the last minute, 429 count, average wait, blocked and unhealthy state; key **names** only) plus the effort counters of PV-08 (calls per mode and level) and the `reroute`/`wait` counts from `get_ledger_event_stats`. This is how PV-19 measures whether the limits are being hit.
5. **Visual check in staging:** open the Token Usage tab; confirm one row per configured production key (four at the start) plus Perplexity, with correct colours, no "NaN", and a seven-day history chart that includes Perplexity.

**Test:** frontend unit tests; backend route tests, including that the stats route returns no key value. **Done when:** the tab renders in staging with real usage and the stats route shows live numbers. **Rollback:** revert the commit.

---

### PV-17: Residue gate and test cleanup (M)

**Do**
1. Finish `backend/tests/unit/test_no_legacy_keys.py`: scan **every non-test `.py` file under `backend/`** with `code_hits`, with an explicit allowlist and nothing else:
   - `eo/model_catalog.py`: everything (it holds the legacy alias rules);
   - `agents/component_spec_lookup.py`: `DIGIKEY` only (PD-9);
   - until PV-20: `utils/web_search.py` (`TAVILY`, `EXA_API_KEY`) and `utils/embedding.py` (`HUGGINGFACE`); `check_hf_embedding.py`.
   The test fails when a hit is outside the allowlist **and** when an allowlist entry no longer has a hit (so the list shrinks).
2. Review the test files the lint listed. At `3727ae3` these had removed names in code: `tests/integration/test_dynamic_chain_redundancy_gate.py`, `test_eo_inspector.py`, `test_key_override.py`, `test_openrouter_regression.py` (30 hits), `test_usage_logging.py`; `tests/unit/test_dynamic_chain_cross_org_redundancy.py`, `test_dynamic_chain_headroom_score.py`, `test_eo_quota_sentinel.py`, `test_codeagent_*`, `test_agent_*` for the files in PV-11, `test_eval_output_organizer_provider.py`; `tests/manual/smoke_tool_calling.py`, `test_groq2.py`, `test_openrouter.py`. **Rewrite tests that protect behaviour you kept; delete only tests of deleted functions** (the headroom-score and cross-org-redundancy tests belong to helpers deleted in PV-15). Every deleted test file gets a line in `PATCHES.md`: file, what it tested, why it is obsolete.
3. Run the full suite and compare with the PV-00 baseline: the number of **passing** tests may drop only by the tests you listed as deleted.

**Done when:** the residue test passes and `PATCHES.md` accounts for every removed test. **Rollback:** revert the commit.

---
## 11. Phase 4: Cutover and go-live

### PV-18: Env, CI, MCP, docs; flip defaults; remove every key except the rollback ones (M)

**Why:** after PV-17 no code needs the retired keys, except the two rollback paths that are kept for the soak: Tavily/Exa search code and the HuggingFace embedding path. This patch makes the configuration say the same thing the code says.

**Do**
1. **Flip the defaults** in code: `SEARCH_BACKEND` default `perplexity`, `EMBEDDING_BACKEND` default `local` (both flags and both old paths stay until PV-20).
2. **`backend/.env.example`** (names only, never values). Replace the LLM, search and part-lookup blocks by the block in Appendix C and delete the **85** retired names that have no rollback role: every Groq name (**including the bare `GROQ_API_KEY`**, which holds a free key), `GEMINI_API_KEY_1` to `_18`, every OpenRouter and Cloudflare name, `MISTRAL_API_KEY` and `_2` to `_10`, `BRAVE_API_KEY`, `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`. **Keep for now** the 21 rollback names (`TAVILY_API_KEY` and `_2` to `_10`, `EXA_API_KEY`, `HUGGINGFACE_API_KEY` and `_2` to `_10`) in a block headed `# RETIRED, delete in PV-20`. Leave every non-LLM line alone (section 2.1).
3. **`config/mcp_servers.json`:** set the `web_search` (Brave) entry to `"enabled": false`. **Do not delete the entry.** Update the one sentence in `eo/capability_entries.py` (near line 110) that lists "github, context7, and web_search" so it says the web search server is disabled; update any test that asserts that sentence. `github` and `context7` stay enabled.
4. **CI (`.github/workflows/ci.yml`, the `promptfoo` job near lines 494 to 600, and `backend/evals/promptfoo/`):** the evals use a Groq key for generation and a separate `GROQ_API_KEY_GRADING` for grading (`promptfooconfig.yaml` and `output_organizer.promptfooconfig.yaml` say why the two are split). Read the job and both configs, then: create the GitHub secrets `CI_DEV_GROQ_API_KEY`, `CI_DEV_GEMINI_API_KEY` and (optional) `CI_DEV_ANTHROPIC_API_KEY` first, holding **free-tier** keys; set `MINIME_USE_DEV_KEYS=1` and `DEV_GROQ_API_KEY`, `DEV_GEMINI_API_KEY`, `DEV_ANTHROPIC_API_KEY` in the job's `env:`; keep generation and grading on **different model families** (for example generate with Groq and grade with Gemini) and edit the grader `provider:` block in both configs to match. **Free tiers are small** (Groq's free plan is 30 requests and 8K tokens a minute per model, so a prompt over 8K tokens can never pass there): run the evals with concurrency 1, let the dev limits in `provider_limits.json` apply, and make eval prompts short; where Haiku is needed and `DEV_ANTHROPIC_API_KEY` is unset, skip that case. Update `backend/evals/promptfoo/providers/role_provider.py` (7 reads of the registry, 3 retired names) and `output_organizer_provider.py` to `slot_chain`. Leave the old `CI_GROQ_API_KEY_1/2` secrets in GitHub until PV-20.
5. **`.gitleaks.toml`:** the comment and allowlist name old keys (`CLOUDFLARE_API_KEY_4..8`, `CF_SCANNER_RESERVE_N_API_TOKEN`). Keep every existing entry, **add** a rule for Perplexity keys (`pplx-[A-Za-z0-9]{20,}`) and for `sk-ant-` keys if the default rules do not already catch them, and test the rule on a fake string.
6. **`m2c/src/m2c/secrets/env.py`** names removed keys. Read what it is for. If it is a redaction or recognition list, **add the new names and keep the old ones** (a leaked old key must still be recognised).
7. **Scripts:** rewrite `backend/scripts/test_all_keys.py` to check every key `pool_keys()` finds in all four pools, `PERPLEXITY_API_KEY` and the three `DEV_*` keys with one tiny call each, printing `OK` or `FAIL <http status>` per key **name** and never a value or a prefix (this is your go-live check in PV-19). Leave `scripts/test_digikey_debug_fix.py` and `check_hf_embedding.py` as they are (DigiKey code is dormant by design; the HF script goes in PV-20). Grep `scripts/` for anything else that names a retired key.
8. **Docs and book:** grep `README.md`, `docs/`, `DEFERRED.md`, `MOBILE_PLAN.md` for the retired names and fix the text. In `minime_book/data/docs/MiniMe_Financial_Strategy_Rulebook.md` update: the models Basic runs on, the Basic LLM line in section 8.2 (1.69 → 1.19), the search line ($0.008 per search → the measured Perplexity cost), and the search provider wherever Tavily or Exa is named. Edit the `.md` source and then rebuild the book's HTML and JSON versions with whatever build the book repo uses; **do not hand-edit generated files** (how the book builds is not verified here).
9. `frontend/app/components/LandingPage.jsx`: the copy on line 45 names Fable 5/5.1 for higher plans. Basic must not claim a model it does not run. **Do not edit or launch Moderate and Ultimate** (PD-6).
10. `docker-compose.yml` and `docker-compose.dev.yml` use `env_file` and name no keys; only the comment mentioning `GROQ_API_KEY` is accurate and needs no change.

**Test:** the full suite; a clean checkout with only the new `.env.example` names set starts the backend; the promptfoo job runs green on a branch with the new secrets; `scripts/test_all_keys.py` prints `OK` for each key in staging. **Done when:** CI is green with only dev keys, and `.env.example` shows exactly the names in Appendix C plus the 21 rollback names. **Rollback:** revert the commit (secrets you created are harmless).

---

### PV-19: Staging soak, canary, rate-limit measurement, spend limits, go-live (M)

**Pre-flight (all must be true)**

| Check | How |
| --- | --- |
| Every production key is a **paid-tier** key and **its own organisation or project** | Open each provider console. Groq: the `PROD_GROQ_120B_KEY_*` and `PROD_GROQ_20B_KEY_*` keys come from the accounts you set up for them; Anthropic: the organisation; Google: a Google Cloud project with billing linked. **No two keys of the same pool may belong to one organisation or project** (they share limits, section 4.6). Never print a key value; compare the key's label or ID in the console |
| Dev keys are free-tier keys, separate from production | Console |
| `MINIME_USE_DEV_KEYS` is **unset** in production | Deployment config |
| `config/provider_limits.json` holds your real numbers | Groq: Console → Settings → Limits (check whether gpt-oss-20b and gpt-oss-120b have separate limits in your organisation); Anthropic: Console → Limits (requests, input tokens, output tokens per minute for Haiku 5.5, and the monthly spend limit of your tier); Google: AI Studio's rate-limit page for Gemini 3.1 Flash-Lite and your tier's spend limits |
| Spend limits and alerts are set in every console | Anthropic: your own monthly limit below the tier cap (Console → Limits); Google: a Cloud Billing budget with alerts; Groq and Perplexity: spend limit or balance alerts. Alert at 50%, 80% and 100% of the monthly budget from PV-06. Which of these is a hard stop differs by provider and is not verified here; **where a console only alerts, rely on the daily check below** |
| Old keys still valid | They are your rollback until PV-20 |
| Tag `pre-provider-consolidation` exists | `git tag -l` |

**Do**
1. Deploy to staging with the production-shaped config (paid keys, `MINIME_USE_DEV_KEYS` unset, small spend limits).
2. **Canary of 20 tasks** covering: a chat turn, a research run, a Balanced build that uses the code agent, a hardware price lookup, a committee review, a memory search, a task that resumes after a restart. Record for each: success, cost from `usage_ledger`, models and keys used. Compare with the rulebook's per-task costs (section 8.1: chat turn about $0.0034, research run about $0.025, Balanced build about $0.106). **Investigate anything above 2x.**
3. **Effort by mode (tunes PV-08).** Run the same three tasks (a chat question, a research task, a code task) once in each mode: `fast`, `simple`, `auto`, `expert`, `beast`. For each run record cost, wall time, reasoning tokens per call (from the usage log) and have a person judge quality. Expected: cost, reasoning tokens and time rise from `fast` to `beast`; quality of `simple` stays acceptable for simple tasks. Where a lower level is visibly worse, raise that cell of `EFFORT_TABLE`; where a higher level costs more and gives nothing, lower it. Replace the four guessed `REASONING_HEADROOM` numbers by measured ones, and confirm `_EmptyReasoningBudgetError` does not occur at any level. Write the final table in `PATCHES.md`.
4. **Calibrate the long-prompt limit:** from the logged `input_tokens` of Haiku calls versus the repo's token estimate, compute the median ratio; set `LONG_PROMPT_EST_TOKENS` so the real count stays below 100,000 with margin. Confirm no Haiku call was billed at the long rate unintentionally.
5. **Measure search cost:** Perplexity requests per user-visible search; update the PV-06 gate numbers and the rulebook line if it differs from your assumption.
6. **Rate-limit measurement (the balancer's acceptance test).**
   - *Ramp:* start runs with 1, 5, 10, 20 and 40 concurrent simulated users, five minutes at each level. At every level read `GET /api/system/key-balancer-stats` once a minute and record per key: 429 count, reroute and wait counts, average and p95 wait, in-flight, tokens a minute against the key's limit. **Acceptance:** fewer than 1% of calls get a 429; p95 wait for a key is at most the 4 s budget; no call waits longer than `LLM_ACQUIRE_WAIT_LAST_S`; no run hangs; task success rate does not fall as load rises (a busy pool reroutes to another model instead).
   - *Tune:* adjust `initial_concurrency`, `max_concurrency` and `LLM_TARGET_FRACTION` in `provider_limits.json`/env until the acceptance holds with the least rerouting; write the final values and your tiers' real limits in `PATCHES.md`.
   - *Add-capacity drill:* create a second test account for one pool, set `PROD_GROQ_120B_KEY_2`, and confirm (within a few seconds, or after the restart if you restart) that the stats show two keys sharing the load and the reroute count falls. Remove it afterwards if it was only a test.
   - *Capacity plan:* from the canary, compute the real peak tokens a minute per active user and apply the formula of section 4.6 to get users per key for each pool. Write the rule you will follow, for example "add a key to a pool when its peak tokens-a-minute utilisation stays above 60% on three consecutive days".
7. **Failure drills (every one must end with a completed task or a clean, understandable error):** (a) blank `PROD_GROQ_120B_KEY_1`: the task completes on the other models, the log shows one authentication error and the key then skipped; (b) blank `PROD_ANTHROPIC_KEY_1`: the code agent falls back; (c) blank `PERPLEXITY_API_KEY`: research runs without a crash and logs the missing key once; (d) point one provider at an unroutable address: fallback within the timeout; (e) cancel a run mid-call: it stops (`RunStopped`), the lease is released (stats show zero in-flight) and nothing keeps running; (f) restart mid-run with an old plan containing `GROQ_API_KEY_7` in `key_overrides`: it resumes on `PROD_GROQ_120B_KEY_1`; (g) block every key of one pool (set tiny concurrency and send a burst): calls move to the next model within the wait budget, none hangs; (h) shut the server down while calls wait for a key: it exits promptly.
8. **Go-live:** deploy production. For 48 hours watch: the stats route (429s, reroutes, waits), the Token Usage tab, the provider consoles' spend, and the daily cost per active user against the Basic pool.
9. **Daily check for 14 days:** compare each console's spend with the Token Usage total. A gap means something calls a provider outside `log_usage`.

**Scale-out playbook (use it whenever the capacity rule fires):** (1) create a new account for the pool's provider (a new organisation or project, never a second key in an existing one); (2) put its key in the secret store as the next number, for example `PROD_GROQ_120B_KEY_2`; (3) set that account's spend limit and alerts; (4) deploy or refresh; (5) run `scripts/test_all_keys.py`; (6) confirm in the stats route that the new key takes load. No code change is needed.

**Done when:** all pre-flight rows are true, the canary, the mode comparison, the ramp and the drills pass, and 48 hours pass without an unexplained cost or error spike. **Rollback:** redeploy tag `pre-provider-consolidation` with the old environment (no database migration is part of this guide, vectors are unchanged if PV-04's gate passed; `usage:*` keys written for the new providers are inert).

---

### PV-20: Remove the rollback paths and revoke the old keys (S; start at least 14 days after go-live)

**Do**
1. `utils/web_search.py`: delete `_search_tavily`, `_search_exa`, the Tavily key and cooldown helpers, `TAVILY_URL`, `EXA_URL` and the `SEARCH_BACKEND` flag. `search()` calls only `_search_perplexity`.
2. `utils/embedding.py`: delete the HuggingFace path, `HF_EMBEDDING_KEY_ENVS`, `HF_FEATURE_EXTRACTION_URL` and the `EMBEDDING_BACKEND` flag; `embed_text_with_fallback` keeps returning `(vector, "local")`. Delete `check_hf_embedding.py`.
3. `.env.example`: delete the 21 rollback names. In `tests/unit/test_no_legacy_keys.py` delete the remaining allowlist entries except `eo/model_catalog.py` and the `DIGIKEY` entry for `agents/component_spec_lookup.py`.
4. **Revoke at each provider** (not before): all Tavily keys, Exa, HuggingFace, Brave, DigiKey, every old Groq key (the ones whose values you did not copy into a `DEV_*` name), Gemini keys 1 to 18, Mistral, OpenRouter, Cloudflare (including the scanner reserve tokens). Delete the old GitHub secrets `CI_GROQ_API_KEY_1/2`. Remove the retired names from every deployment secret store.
5. Decide on `MOUSER_API_KEY` (PD-9): keep, or delete the key and leave the dormant code.
6. Run the secrets scan from PV-00 once more, the full suite, and Appendix A's gates. Add a final line to `PATCHES.md` with the date.

**Done when:** the gates in Appendix A all pass and the provider consoles show only the keys in section 2.1's first two lines. **Rollback:** from here the tag `pre-provider-consolidation` is the only way back; keep it forever.

---

## 12. What I could not verify (decide or measure these yourself)

1. **No test suite was run and nothing was built.** I read the code and ran only a `pip` dry-run of the six new packages against the 136 existing `==` pins. Line numbers and counts drift: every patch starts with a grep.
2. **Prices and API rules** come from provider pages and third-party summaries found by web search on 2026-11-18 (Haiku 5.5 price tiers, the cache-counts-toward-100K rule, the Haiku 5.5 parameter limits, Groq gpt-oss prices, Gemini Flash-Lite prices, Perplexity's price and parameters). One third-party page still listed older, lower Gemini Flash-Lite prices. **Re-open each provider's own pricing and API page when you apply PV-02 and PV-06.**
3. **Rate limits.** I read Groq's published Developer-plan limits (1K requests/min, 500K requests/day, 250K tokens/min for each of the two gpt-oss models; one third-party page says 300K) and Google's and Anthropic's rules (per project / per organisation, spend-based limits, tiers). I did **not** find Haiku 5.5's per-minute limits in an Anthropic page, nor Gemini 3.1 Flash-Lite's per-model limits (AI Studio only), and Perplexity does not publish a default for its Search endpoint. That Groq's limits are **per model** inside one organisation is read from its table, not tested. Anthropic's spend limit is monthly in its docs and daily on one third-party page. All of this is for you to confirm on the Console pages in PV-19 and write into `config/provider_limits.json`.
3a. **Effort and capacity numbers are starting values.** The mode × class effort table (4.5), the four `REASONING_HEADROOM` numbers (PV-08) and the capacity estimates in 4.6 (8 active hours, a peak of 3 times the average, the 45/15/25/15 token mix, 70/30 input/output) are my assumptions; PV-19 replaces them with measurements. The claim that Anthropic's API has no free tier (so `DEV_ANTHROPIC_API_KEY` is optional) is from memory; check Anthropic's current terms. Google's compatibility page lists `reasoning_effort` for the Gemini 3.x family and for 3.1 Flash-Lite; PV-08's manual test confirms it with one real call to `gemini-3.1-flash-lite`.
4. **Exact SDK details** for `anthropic==2.4.0` (the `output_config` parameter, the usage field names, the exception classes' attributes) and the exact text of each provider's "credit exhausted" error. PV-02 and PV-14 say to check them against the SDK and docs and to unit-test with real error bodies.
5. **Perplexity's authentication header** is shown as a bearer token in its examples; I did not make a call.
6. **PV-04 unknowns:** what the HuggingFace endpoint returns today (pooled or unpooled, normalised or not) and the distance metric of your Upstash Vector index. The parity gate and step 1 exist to settle both; the thresholds are my judgment.
7. **Persistence of old key names:** I confirmed `key_overrides` appears in five files, but did not trace where stored plans or in-flight chains are saved and reloaded. PV-10 step 3 tells you to find that point.
8. **Model facts not checked:** context windows and maximum outputs of the gpt-oss models and Gemini Flash-Lite (marked `UNVERIFIED` in the catalog), and the quality of each slot assignment (the slot table is a recommendation; run the evals in PV-19).
9. **The pool recompute assumes** a 70/30 input/output split (the rulebook's worker split) and a 45/15/25/15 token mix across the four models. The real mix and the number of Perplexity requests per user search are unknown until staging.
10. **Partly read files:** the `promptfoo` job in `ci.yml`, `m2c/src/m2c/secrets/env.py`, the `protocol/` and `daemon/` provider enums, and how the book repo builds its generated HTML. PV-13 and PV-18 say what to check in each.

---

## Appendix A: Commands

Run from the MiniMe repo root; `cd backend` where shown. Output of A.1 and A.2 goes into `PATCHES.md` at PV-00 and again after PV-20.

**A.1 Measurements**
```bash
cd backend
git rev-parse --short HEAD
wc -l .env.example utils/llm_client.py eo/registry.py eo/dynamic_chain.py agents/generic_worker.py \
      utils/rate_ledger.py eo/quota_sentinel.py eo/concurrency_gate.py eo/worker_pool.py
grep -c 'time.sleep' utils/llm_client.py
grep -rlE 'build_fallback_chain|build_fallback_chain_excluding|chain_step_for|_build_fallback_chain|_chain_step_for' --include=*.py . | grep -v -E '/tests?/|test_' | wc -l
grep -rlE 'embed_text' --include=*.py . | grep -v -E '/tests?/|test_' | wc -l
grep -rnE '(from|import) .*rate_ledger' --include=*.py . | grep -v -E '/tests?/|test_|^./utils/rate_ledger.py'
grep -rn 'product_tier_map' --include=*.py . | grep -v -E '/tests?/|test_|^./eo/product_tier_map.py'
grep -rn 'quota_sentinel' --include=*.py . | grep -v -E '/tests?/|test_' | awk -F: '{print $1}' | sort | uniq -c
```
At `3727ae3` these gave: 6 sleeps; 32 chain-builder files; 16 `embed_text` files; `rate_ledger` imported by `llm_client.py`, `eo/concurrency_gate.py`, `eo/quota_sentinel.py` and (deferred) `eo/dynamic_chain.py`; `product_tier_map` imported by nothing outside tests.

**A.2 Code-level count of retired names (one-off version of the PV-11 helper; save as `/tmp/legacy_key_lint.py`)**
```python
import ast, pathlib, re, sys
LEGACY = re.compile(
    r"(MISTRAL|HUGGINGFACE|OPENROUTER|CLOUDFLARE|CEREBRAS)_(API_KEY|ACCOUNT_ID)"
    r"|(?<![A-Z_])GROQ_API_KEY(_\d+)?(?![A-Z_])|(?<![A-Z_])GEMINI_API_KEY(_\d+)?(?![A-Z_])|(?<![A-Z_])ANTHROPIC_API_KEY(?![A-Z_])"
    r"|EO_INSPECTOR_GROQ_KEY|EO_PANEL_|CF_SCANNER_|SGA_GROQ|GROQ_RESERVE|OPENROUTER_RESERVE"
    r"|TAVILY|EXA_API_KEY|BRAVE_API_KEY|DIGIKEY")

def code_hits(path):
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings and LEGACY.search(node.value):
            hits.append((node.lineno, node.value[:60]))
        elif isinstance(node, ast.Name) and LEGACY.search(node.id):
            hits.append((node.lineno, node.id))
    return hits

root = pathlib.Path(sys.argv[1]).resolve()
files = []
for p in sorted(root.rglob("*.py")):
    s = str(p)
    if "/tests/" in s or "/node_modules/" in s or "/data/" in s:
        continue
    try:
        h = code_hits(p)
    except SyntaxError:
        continue
    if h:
        files.append((s[len(str(root)) + 1:], len(h)))
print(len(files), "non-test files with code-level hits;", sum(c for _, c in files), "hits")
for f, c in files:
    print(f"{c:4d} {f}")
```
Run `python /tmp/legacy_key_lint.py backend`. At `3727ae3`: **51 files, 270 hits**.

**A.3 Final gates (run after PV-20; every line must hold)**
```bash
cd backend
pytest tests/unit tests/integration -q                                   # equals baseline minus listed deletions
python /tmp/legacy_key_lint.py .                                          # only eo/model_catalog.py and agents/component_spec_lookup.py (DIGIKEY)
grep -c 'time.sleep' utils/llm_client.py                                  # 0
grep -rnE '(from|import) .*rate_ledger' --include=*.py . | grep -v '^./tests/'   # nothing
test ! -e utils/rate_ledger.py && echo "rate_ledger gone"
grep -rnE 'getenv\("(GROQ|GEMINI|ANTHROPIC)_API_KEY' --include=*.py . | grep -v -E 'tests?/|model_catalog|test_all_keys'   # nothing (rule 9)
python - <<'EOF'
import re, pathlib
expected = {"PROD_GROQ_120B_KEY_1","PROD_GROQ_20B_KEY_1","PROD_GEMINI_KEY_1","PROD_ANTHROPIC_KEY_1","PERPLEXITY_API_KEY",
            "MINIME_USE_DEV_KEYS","DEV_GROQ_API_KEY","DEV_GEMINI_API_KEY","DEV_ANTHROPIC_API_KEY",
            "LLM_TARGET_FRACTION","LLM_ACQUIRE_WAIT_S","LLM_ACQUIRE_WAIT_LAST_S","LLM_RETRY_AFTER_MAX_S","LLM_PROCESS_SHARE",
            "EMBED_THREADS","MOUSER_API_KEY","GUARDRAILS_API_KEY"}
names = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", pathlib.Path(".env.example").read_text(), re.M))
retired = re.compile(r"^(GROQ_API_KEY(_\d+)?|GEMINI_API_KEY(_\d+)?|ANTHROPIC_API_KEY|MISTRAL_API_KEY(_\d+)?|OPENROUTER_.*|CLOUDFLARE_.*|CF_SCANNER_.*|HUGGINGFACE_.*|TAVILY_.*|EXA_.*|BRAVE_.*|DIGIKEY_.*|EO_PANEL_.*|EO_INSPECTOR_.*|SGA_GROQ_.*|GROQ_RESERVE_.*)$")
print("retired names still present:", sorted(n for n in names if retired.match(n)) or "none")
print("expected names missing:", sorted(expected - names) or "none")
EOF
grep -rnE '(gpt-oss-(120|20)b|claude-haiku-5|gemini-3\.1-flash)' --include=*.py . | grep -v -E 'tests?/|test_|eo/model_catalog.py|llm_client.py|credits.py'   # nothing: no agent names a model (rule 11)
cd .. && git grep -nE '(gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|pplx-[A-Za-z0-9]{20,})' | sed -E 's/[A-Za-z0-9_-]{12,}$/<redacted>/'   # nothing
/tmp/v/bin/pip check                                                       # No broken requirements found
```

## Appendix B: Legacy key-name aliases (`resolve_legacy_key_env(name, slot=None)`)

The function returns the name of a **configured key of the right pool** (`primary_key(pool)`), never an old name.

| Old name pattern | Returns | Example |
| --- | --- | --- |
| `GROQ_API_KEY`, `GROQ_API_KEY_<n>`, `GROQ_RESERVE_<n>`, `SGA_GROQ_<n>`, `EO_INSPECTOR_GROQ_KEY_<n>` | `primary_key` of the Groq pool that holds the first Groq model of the slot's preferred order (`groq-20b` for slot `fast`, otherwise `groq-120b`; `groq-120b` when no slot is given) | `GROQ_API_KEY_7` with slot `fast` → `PROD_GROQ_20B_KEY_1` |
| `GEMINI_API_KEY`, `GEMINI_API_KEY_<n>` | `primary_key("gemini")` | `GEMINI_API_KEY_14` → `PROD_GEMINI_KEY_1` |
| `ANTHROPIC_API_KEY` | `primary_key("anthropic")` | |
| `MISTRAL_API_KEY`, `MISTRAL_API_KEY_<n>`, `OPENROUTER_API_KEY_<n>`, `OPENROUTER_RESERVE_<n>`, `EO_PANEL_OPENROUTER_KEY`, `CLOUDFLARE_API_KEY_<n>`, `CLOUDFLARE_ACCOUNT_ID_<n>`, `CF_SCANNER_RESERVE_<n>_API_TOKEN`, `CF_SCANNER_RESERVE_<n>_ACCOUNT_ID`, `EO_PANEL_CLOUDFLARE_API_TOKEN`, `EO_PANEL_CLOUDFLARE_ACCOUNT_ID`, `HUGGINGFACE_API_KEY`, `HUGGINGFACE_API_KEY_<n>` | `primary_key` of the pool of the first model of the slot's preferred order (`groq-120b` if no slot), and one warning log | `CLOUDFLARE_API_KEY_3` with slot `code` → `PROD_ANTHROPIC_KEY_1` |
| New names: `PROD_<POOL>_KEY_<n>`, `DEV_GROQ_API_KEY`, `DEV_GEMINI_API_KEY`, `DEV_ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY` | unchanged | |
| any other string | raises `KeyError` | `GROQ_APY_KEY` raises |

`<n>` is one or more digits.

## Appendix C: Final `.env.example` LLM, search and tuning block (names only)

```
# --- LLM key pools. Production keys must be PAID-tier keys, ONE KEY PER ORGANISATION OR PROJECT. ---
# To add capacity later, add the next number (for example PROD_GROQ_120B_KEY_2); no code change.
PROD_GROQ_120B_KEY_1=
PROD_GROQ_20B_KEY_1=
PROD_GEMINI_KEY_1=
PROD_ANTHROPIC_KEY_1=

# --- Web search (the only search provider) ---
PERPLEXITY_API_KEY=

# --- Dev / eval / CI only (FREE-tier keys). Never set MINIME_USE_DEV_KEYS in production ---
MINIME_USE_DEV_KEYS=
DEV_GROQ_API_KEY=
DEV_GEMINI_API_KEY=
DEV_ANTHROPIC_API_KEY=

# --- Rate-limit balancer tuning (not secrets) ---
LLM_TARGET_FRACTION=0.7
LLM_ACQUIRE_WAIT_S=4
LLM_ACQUIRE_WAIT_LAST_S=20
LLM_RETRY_AFTER_MAX_S=8
LLM_PROCESS_SHARE=1.0

# --- Other tuning (not secrets) ---
EMBED_THREADS=2
EMBEDDING_BACKEND=local
SEARCH_BACKEND=perplexity
```
`EMBEDDING_BACKEND` and `SEARCH_BACKEND` are deleted in PV-20. `MOUSER_API_KEY` and `GUARDRAILS_API_KEY` stay in their existing blocks.

*End of guide.*
