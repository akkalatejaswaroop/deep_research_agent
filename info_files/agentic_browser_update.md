# REX Agentic Browser Update — Advanced Implementation Plan

**Document type:** Product + engineering specification  
**Status:** Planning / pre-implementation  
**Applies to:** Deep Research Agent (REX) — Recursive Exploration eXplorer  
**Related docs:** `Architecture.md`, `Features.md`, `TechStack.md`, `Security.md`, `PRD.md`  
**Last updated:** 2026-03-26

---

## 1. Executive summary

REX today is a **multi-agent deep research pipeline**: plan → search → scrape → filter → synthesize → gap-fill → cite → report → evaluate. Web access is mostly **passive** (HTTP fetch + Trafilatura/BS4, with Playwright as a last-resort read-only fallback).

This update converts REX into a **Deep Research Agentic Browser**: agents that **operate a real browser** (tabs, navigation, clicks, typing, extraction, optional form assist) while keeping REX’s research brain (LangGraph orchestration, citations, gap loops, memory, quality scoring).

### One-line product definition

> Query → agents that **operate the web** → evidence trail → cited publication-grade report — local-first, inspectable, budget-controlled.

### Non-goals (v1)

- Full consumer “Operator” that freely logs into banks, shops, or pays
- Unrestricted desktop/computer-use outside the browser
- Captcha solving or paywall bypass
- Always-on high-FPS remote desktop streaming of Chromium

### Goals (v1–v3)

| Horizon | Goal |
|---|---|
| **v1 MVP** | Session browser + action tools + compact page state + hybrid Fast/Standard modes + SSE action stream |
| **v2** | Gap-driven re-browse, evidence notebook, workstation UI, token budgets, model routing |
| **v3** | Task Assist (forms with confirm), playbooks, optional VLM, allowlisted automation |

---

## 2. Current state vs target state

| Dimension | Current REX | Target: Agentic Browser REX |
|---|---|---|
| Web access | Search APIs + one-shot scrape | Live Playwright session the agent controls |
| Playwright role | Tier-3 fallback scraper | Primary **browser runtime** (tabs + actions) |
| Agent loop | Fixed LangGraph path | Outer research DAG + **inner perception–action loop** |
| Page input to LLM | Large text dumps / chunks | Compact outline + preview + numbered element refs |
| Evidence | URLs + scored chunks | Claims + quotes + URL + action provenance |
| UI | Phases, telemetry, report | **Workstation**: viewport \| actions \| evidence \| report |
| Modes | depth / complexity knobs | Fast / Standard / Deep / Local-economy (+ Task Assist later) |
| Forms / automation | None | Level 1 research browse → Level 2 assisted forms (gated) |
| Token control | Caches, some chunking | Hard budgets, model routing, map-reduce, single-flight Ollama |

### Current pipeline (keep the brain)

```text
planner → memory_retrieval → searcher → filter → synthesis
       → gap_detector ⇄ searcher → citation_mapper → report → evaluator
```

### Target pipeline

```text
planner → memory_retrieval → browser_agent → filter → synthesis
       → gap_detector ⇄ browser_agent → citation_mapper → report → evaluator

Optional hybrid:
  depth=1 / Fast mode → legacy searcher+scrape (cheap path)
  depth≥2 / Standard+ → browser_agent
```

**Principle:** Do not rip out LangGraph. Replace the **sensorimotor layer** (searcher/scraper) with a browser agent; keep plan / gap / cite / evaluate.

---

## 3. Capability model (what it can and cannot do)

### 3.1 Capability levels

| Level | Name | Capabilities | Default? |
|---|---|---|---|
| **L0** | Current REX | Search + scrape + report | Today |
| **L1** | Research browser | goto, click, scroll, type (search boxes), extract, multi-tab, note claims | **v1 target** |
| **L2** | Task Assist | Fill known/public forms from user profile; **confirm before submit** | v3 |
| **L3** | Autopilot automation | Multi-step workflows on allowlisted domains; audit log | Optional later |
| **L4** | Computer use | OS + files + non-browser | Out of scope |

### 3.2 What L1–L2 can automate well

| Task type | Examples | Difficulty |
|---|---|---|
| Research navigation | Follow “Next”, open PDF, expand sections | Easy–medium |
| Filters / site search | Date sort, open-access filter, docs search | Medium |
| Evidence collection | Open top N results, extract, note claim | Medium |
| Public forms (L2) | Contact, feedback, RSVP with user-supplied data | Medium |
| Playbook chores (L3) | Paginate, export link, re-check URL weekly | Medium |

### 3.3 What must be restricted or deferred

| Task | Policy |
|---|---|
| Login / signup / 2FA | **Deny by default**; optional later with vault + confirm |
| Payments / checkout | **Hard deny** |
| Password / credit-card fields | **Hard deny** unless explicit vault mode (not v1) |
| Captcha solving | **Skip / fail**; never automate bypass |
| Paywall bypass | **Deny** |
| Arbitrary file upload | Only user-picked path + confirm (L2+) |
| Email confirmation loops | Needs inbox connector — separate feature |

### 3.4 Form filling & task automation (advanced)

Agentic form fill is **not free** with research mode; it is an explicit tier.

**Required loop for forms:**

1. Perception — list fields via a11y/DOM (`list_fields`)
2. Planning — map user profile / goal → fields
3. Actions — `fill_field` / `fill_form` / `click` / `select`
4. Memory — what was filled; validation errors
5. Recovery — fix errors, handle extra steps
6. Gate — **human confirm before submit** (LangGraph `interrupt`)

**Token-optimal form pattern (prefer over pure ReAct):**

```text
1) list_fields (CPU, no LLM)
2) heuristic map profile keys → labels (email → Email, …)
3) LLM only for unmatched / ambiguous fields
4) show fill plan → user confirm
5) execute → optional submit after second confirm
```

**Extra tools for L2+:**

| Tool | Purpose |
|---|---|
| `list_fields` | Enumerate inputs with refs, types, labels, required |
| `fill_field` | Type/select/check by ref |
| `fill_form` | Batch fill from JSON profile |
| `submit` | Click submit **only if policy allows** |
| `wait_for` | Text / URL / selector condition |
| `upload_file` | Explicit user-approved path only |
| `get_validation_errors` | Read inline errors and retry |
| `assert` | Success message / expected state |

---

## 4. Feature plan (complete)

### Phase 0 — Foundations

| Feature | Description |
|---|---|
| Browser session pool | Long-lived Chromium per research session |
| Action / time / tab budgets | Hard caps to stop runaway agents |
| Structured `PageState` | URL, title, outline, links, text preview, interactive refs |
| SSE event types | `browser_action`, `browser_view`, `evidence`, `tab_update` |
| Domain policy engine | Allow/block lists; research-safe defaults |
| Hybrid Fast path | Keep legacy searcher for simple/`depth=1` queries |

### Phase 1 — Agentic browsing core (MVP)

| Feature | Description |
|---|---|
| Core tools | `web_search`, `goto`, `click`, `type`, `scroll`, `back`, `new_tab`, `close_tab`, `extract`, `screenshot`, `note_claim`, `done` |
| Browser agent loop | ReAct / JSON tool-calling per sub-question with budget |
| Evidence notebook | claim + quote + url + confidence + sub_question_idx |
| Extract pipeline | Trafilatura/BS4 on live HTML; Playwright interact only when needed |
| Failure handling | timeout, empty, captcha, 403 → log + skip + alternate URL |
| Limited concurrency | 1–2 browser contexts; queue LLM on local GPU |

### Phase 2 — Deep research quality

| Feature | Description |
|---|---|
| Gap-driven re-browse | `gap_detector` emits targeted browse goals (not full re-scrape) |
| Multi-tab workspace | 3–5 tabs; intentional switch |
| Source tiering | Prefer edu/gov/arxiv/nature; extend junk blocklist |
| Quote-level citations | Exact excerpt spans for `[N]` mapping |
| Dedup | URL normalize + content fingerprint (existing helpers) |
| Human interrupt | Pause on paywall / captcha / ambiguous fork |
| Mode presets | Fast / Standard / Deep / Local-economy |

### Phase 3 — Workstation UX

| Feature | Description |
|---|---|
| Split UI | Viewport \| action log \| evidence \| draft report |
| On-action screenshots | Low cost; optional interval refresh |
| Citation → source jump | Open snapshot / URL from `[N]` |
| Action replay timeline | Scrub agent steps |
| Controls | Pause / resume / cancel / optional take-over |
| Export | Markdown, PDF, HTML, JSON + **research trace** (actions + evidence) |

### Phase 4 — Advanced automation & intelligence

| Feature | Description |
|---|---|
| Task Assist mode | Profile-driven form fill + confirm-before-submit |
| Domain playbooks | arXiv, PubMed, Wikipedia, docs-site skills |
| VLM screenshots | Charts/tables via existing `vlm_client.py` (rare) |
| Persistent projects | Multi-session research memory |
| n8n / Celery playbooks | Scheduled browse jobs |
| Autopilot (optional) | Allowlisted hosts + strict audit |
| Remote live view (optional) | CDP / noVNC — ops-heavy, later |

---

## 5. Architecture

### 5.1 High-level diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js) — Research Workstation                      │
│  [Sub-Q / phases] [Live viewport] [Action log] [Evidence/Report]│
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST + SSE
┌───────────────────────────────▼─────────────────────────────────┐
│  FastAPI (main.py) — sessions, budgets, event_queue, cancel     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  LangGraph app_graph                                            │
│  planner → memory → browser_agent → filter → synthesis          │
│           → gap ⇄ browser_agent → cite → report → evaluator     │
└───────────────────────────────┬─────────────────────────────────┘
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   Search tools          Browser Runtime         Memory / KG
   (DDG, Tavily, …)      (Playwright pool)       (pgvector / local)
          │                     │
          │              ┌──────┴──────┐
          │              │ Tabs        │
          │              │ PageState   │
          │              │ Actions     │
          │              │ Policy      │
          │              └─────────────┘
          ▼
   Ollama (local) — routed models + semaphore
   Optional cloud LLM via llm_client.py
   Caches: page / search / LLM / negative (optimization.py + SQLite)
```

### 5.2 New / changed modules

| Path | Role |
|---|---|
| `backend/agents/browser_runtime.py` | **NEW** — Playwright session, tabs, low-level actions |
| `backend/agents/browser_tools.py` | **NEW** — tool definitions + execution + validation |
| `backend/agents/browser_agent.py` | **NEW** — inner ReAct/tool loop, budgets, compression |
| `backend/agents/browser_policy.py` | **NEW** — domain/action allow-deny, risk classes |
| `backend/agents/graph.py` | Wire `browser_agent_node`; hybrid Fast path |
| `backend/agents/state.py` | Tabs, actions, evidence, budgets |
| `backend/agents/scraper.py` | Keep as extract helper inside runtime |
| `backend/agents/optimization.py` | Extend caches (page, negative, tool decision) |
| `backend/agents/llm_client.py` / graph LLM helpers | Model routing, num_ctx/num_predict |
| `backend/main.py` | SSE event types; mode presets; interrupt resume |
| `frontend/src/app/page.tsx` | Workstation layout integration |
| `frontend/src/components/BrowserViewport.tsx` | **NEW** |
| `frontend/src/components/ActionLog.tsx` | **NEW** |
| `frontend/src/components/EvidenceDrawer.tsx` | **NEW** |

### 5.3 AgentState extensions

```text
browser_session_id: str
browser_tabs: List[{tab_id, url, title, last_hash}]
browser_actions: List[{step, tool, args, result_summary, ts, tokens_est}]
evidence_notes: List[{id, claim, quote, url, sub_question_idx, confidence}]
page_outlines: List[{url, headings[]}]
action_budget_remaining: int
token_budget_remaining: int
browse_failures: List[{url, reason, ts}]
browse_mode: fast | standard | deep | local_economy | task_assist
pending_interrupt: Optional[{type, payload}]   # submit confirm, captcha, etc.
```

### 5.4 PageState contract (compact observation)

Never send raw HTML to the LLM. Emit:

```text
URL, Title
Outline: H1–H3 only
Preview: first ~1500–2000 chars of main content
Links: top 15–20
Interactive: [1] link "…", [2] button "…", [3] textbox "Search" …
Notes so far: N12, N14 (one-line claims)
Budget: actions left / tokens left
Last 3 actions: compressed
```

**Element refs** are numbered interactive controls from the accessibility tree — not model-invented CSS selectors.

### 5.5 Core tool contract (L1)

| Tool | Inputs | Output (compact) |
|---|---|---|
| `web_search` | query, k | `[{title, url, snippet}]` |
| `goto` | url or tab_id | PageState |
| `click` | element_ref | PageState delta |
| `type` | ref, text, submit? | PageState delta |
| `scroll` | direction, amount | New visible text chunk |
| `extract` | mode=main\|selection | `{text, word_count, hash}` |
| `note_claim` | claim, quote, url | note_id |
| `screenshot` | full_page? | path or small thumb (rare) |
| `new_tab` / `close_tab` / `back` | … | tab list + state |
| `done` | summary | ends inner loop |

All tool args validated with **Pydantic** before execution.

---

## 6. End-to-end workflows

### 6.1 User journey

```text
1. User enters query + mode (Fast / Standard / Deep / Local-economy)
2. UI opens workstation (phases + viewport + evidence)
3. Backend creates session_id, BrowserSession, action+token budgets
4. SSE streams: thoughts, phase, browser_action, evidence, metrics
5. User may Pause / Cancel (existing cancel_event pattern)
6. Final report + optional research-trace export
```

### 6.2 Outer LangGraph workflow

```text
[1] planner_node
    - Decompose into sub-questions (capped LLM)
    - Emit plan

[2] memory_retrieval_node
    - Lessons / vector memory for similar topics

[3] browser_agent_node  (or legacy searcher if Fast)
    - Per sub-question (or batched) inner tool loop
    - Output: evidence_notes, subset raw_pages, source_urls

[4] filter_node
    - Lexical/embed score; blocklist; scored_chunks

[5] synthesis_node
    - Map-reduce over top-K only; ground in note_ids / [N]

[6] gap_detector_node
    - If gaps && iterations left → targeted browser_agent goals
    - Else → citation path

[7] citation_mapper_node
    - Bind [N] to url/quote; drop dead links

[8] report_node
    - Assemble structure; limited polish LLM

[9] evaluator_node
    - Rubric scores; persist lessons
```

### 6.3 Inner browser step loop

```text
goal + compact observation + last actions + notes + budget
        │
        ▼
  small tool model → JSON {"tool":"...","args":{...}}
        │
        ▼
  policy check → execute Playwright/search/extract
        │
        ▼
  update state, emit SSE, compress history every N steps
        │
        ▼
  if extract quality high → note_claim
  if budget empty or done → exit to filter
```

### 6.4 Failure workflow

```text
timeout | 403 | captcha | empty main text
  → browse_failures entry
  → force next options: web_search | next SERP url | done
  → negative cache URL (TTL) — never infinite retry
```

### 6.5 Task Assist workflow (L2)

```text
User goal + profile JSON + target URL
  → goto → list_fields
  → heuristic + LLM map → fill plan
  → interrupt: "Approve fill?" 
  → execute fills
  → interrupt: "Approve submit?" (if submit requested)
  → wait_for success / capture errors
  → return structured result + action trace
```

### 6.6 Token-aware data flow

```text
Web HTML
  → extract text (CPU: Trafilatura/BS4)
  → chunk + score (CPU/embed)
  → top-K only
  → map summary (small LLM)
  → section synth (medium LLM)
  → report (medium LLM)
  → eval (small LLM)

Browser pixels
  → discarded by default
  → screenshot only on tool call or slow UI refresh
```

---

## 7. Tech stack

### 7.1 Keep (current strengths)

| Layer | Tech | Role |
|---|---|---|
| API | FastAPI + SSE | Sessions, streaming |
| Orchestration | LangGraph + MemorySaver checkpointer | Multi-node DAG + interrupt |
| Local LLM | Ollama + langchain-ollama | Private inference |
| Cloud LLM (optional) | `llm_client.py` (OpenAI-compat / Claude) | Escape hatch |
| Extract | trafilatura, BeautifulSoup4, Jina fallback | Clean text |
| Browser engine | Playwright Chromium | Already in `requirements.txt` |
| Search | DuckDuckGo + multi-provider graph logic | Discovery |
| Memory | Supabase/pgvector or local JSON/SQLite | Lessons |
| Cache | `optimization.py`, `scraper_cache.db` | Cost/latency |
| Frontend | Next.js, Framer Motion, ReactMarkdown | UI |
| Jobs (optional) | Celery + Redis | Long / scheduled runs |
| Automation bridge | n8n client (existing) | Batch / external triggers |

### 7.2 Add

| Component | Choice | Why |
|---|---|---|
| Browser runtime | Playwright session pool | Tabs + actions across steps |
| Perception | Accessibility snapshot / ARIA refs | Cheap vs raw DOM/pixels |
| Tool protocol | Strict JSON tools + Pydantic | Local models need constraints |
| Token accounting | Ollama `eval_count` + heuristic | Budgets & metrics |
| Ranking | Existing lexical score + small embeddings | Pre-LLM filter |
| UI panels | BrowserViewport, ActionLog, EvidenceDrawer | Agentic UX |
| Optional VLM | Existing `vlm_client` | Rare visual pages |
| Policy engine | `browser_policy.py` | Safety classes for actions |

### 7.3 Local model routing (token-optimal)

| Role | Suggested size | Job | `num_ctx` | `num_predict` |
|---|---|---|---|---|
| Tool picker | 1.5–3B (Qwen2.5-1.5B / Phi-3-mini) | Next action JSON only | 2k–4k | 64–128 |
| Browser reasoner | 7–8B | Harder browse decisions | 8k | 128–256 |
| Map summarizer | 3–7B | Chunk → bullets | 4k | ~256 |
| Synthesizer / writer | 8–14B best available | Sections + report | 8k–16k | 1k–4k |
| Judge | small–medium | Evaluator rubric JSON | 4k | 256–512 |
| Embeddings | nomic-embed-text (or current) | Memory + chunk rank | n/a | n/a |
| VLM (optional) | small vision | Screenshots only | minimal | minimal |

**Rule:** never use the writer model for “should I click Next?”.

### 7.4 Runtime topology

```text
[Next.js :3000] ↔ [FastAPI :8000] ↔ [LangGraph]
                                      ├─ browser_agent → Playwright Chromium
                                      └─ Ollama :11434 (LLMSemaphore=1 on weak GPU)
                                      └─ SQLite/Redis caches
```

---

## 8. Local LLM token optimization (advanced)

Local tokens are “free” in dollars but expensive in **time, VRAM, and latency**. Naive agentic browsing can use **5–20×** more tokens than current REX.

### 8.1 Architectural wins (largest)

1. **Two-loop design** — outer graph (few heavy calls) + inner browse (tiny model, tiny context)
2. **Search-first, browse-second** — snippets pick URLs; only goto top 3–5
3. **Extract without LLM** — Trafilatura/BS4 first; LLM ranks survivors only
4. **Hard action budgets** — e.g. Standard: 12 actions/sub-Q, ~40 global
5. **Early exit** — coverage threshold → `done`
6. **Hybrid Fast path** — `depth=1` keeps today’s scrape pipeline
7. **Deterministic form mapping** — LLM only for ambiguous fields (L2)

### 8.2 Context hygiene

| Do | Don’t |
|---|---|
| Outline + 1.5–2k preview | Full HTML/DOM every step |
| Top 15–25 interactive refs | Entire a11y tree |
| Rolling summary (last 5 detailed + older compressed) | Full transcript forever |
| Pass note IDs + one-line claims to synthesizer | Re-send all page text to every node |
| Cap extract at 3–6k before any LLM | 50k-char pages into Ollama |
| Dedup by content hash | Re-process same article |

### 8.3 Ollama decoding settings

| Setting | Recommendation |
|---|---|
| `num_ctx` | Tool loop 4096; synth 8192; avoid huge default ctx |
| `num_predict` | Tools 64–128; plan ~512; section 1–2k; report 2–4k |
| `temperature` | Tools 0–0.2; writing 0.3–0.5 |
| System prompts | Short, role-specific |
| Output | Strict JSON for tools |
| Stop sequences | Cap runaway tool prose |
| Concurrency | `LLMSemaphore(1)` in local mode |

### 8.4 Caching strategy (extend `optimization.py`)

| Cache | Key | Saves |
|---|---|---|
| Search | query + provider | Gap loops / retries |
| Page extract | normalized URL + hash | Revisits |
| LLM response | model + prompt hash | Identical subcalls |
| Tool decision | url_hash + goal + outline_hash | Same page/intent |
| Embeddings | chunk hash | Rerank |
| Negative | url → fail reason + TTL | Skip paywalls/captchas |

### 8.5 Map-reduce synthesis

```text
Map:   each top chunk → 5–8 bullet facts + source ids   (small predict)
Reduce: bullets only → section paragraph               (no raw chunks)
```

Expected cut: **~50–80%** synthesis tokens vs stuffing all chunks.

### 8.6 Session token budget example

```text
budget_tokens_total: 80_000   # soft cap Local-economy / Standard
spend allocation:
  plan:           ~5%
  browse_tools:  ~25%
  map_summaries: ~25%
  synth+report:  ~35%
  eval:          ~10%
```

When a bucket empties → degrade gracefully (stop browsing; synthesize with notes on hand).

### 8.7 Local-economy defaults

```text
browser:
  max_actions_global: 25
  max_actions_per_subq: 8
  max_tabs: 3
  goto_timeout_ms: 8000
  block_images: true
  block_fonts: true

llm:
  tool_model: qwen2.5:1.5b-instruct   # or phi3:mini
  reason_model: qwen2.5:7b | llama3.1:8b
  write_model: same or one tier up
  tool_num_ctx: 4096
  tool_num_predict: 96
  map_num_predict: 256
  section_num_predict: 1200
  llm_concurrency: 1

retrieval:
  search_results_per_q: 5
  max_gotos_per_q: 3
  chunk_size: 1200
  top_k_chunks_per_section: 4
  preview_chars: 1500

cache:
  enabled: true
  page_ttl: 24h
  search_ttl: 12h
  negative_ttl: 6h
```

### 8.8 Mode comparison

| Mode | Browser depth | LLM load | When |
|---|---|---|---|
| **Fast** | Search + extract top 5; no click loop | Low | Simple factual |
| **Standard** | ≤15 actions/sub-Q; focused tab | Medium | Default research |
| **Deep** | ≤40 actions; multi-tab; gap re-browse | High | Publication-style |
| **Local-economy** | Strict budgets; small models; heavy cache | Lowest | Laptop / weak GPU |
| **Task Assist** | Form-centric tools; dual confirm | Medium | User-driven automation |

---

## 9. Safety, policy, and compliance

### 9.1 Action risk classes

| Class | Examples | Default policy |
|---|---|---|
| **Safe** | goto public URL, scroll, extract, note_claim | Allow |
| **Interactive** | click, type in search, open tab | Allow in research mode with budget |
| **Mutating** | submit form, post comment, upload | Confirm or deny |
| **Auth** | login, password, OAuth | Deny (v1) |
| **Financial** | checkout, wire, crypto send | Hard deny |
| **Evasion** | captcha solve, paywall bypass | Hard deny |

### 9.2 Runtime safeguards

- Sandboxed headless Chromium (no host file access by default)
- Per-session action + wall-clock timeouts
- Rate limiting / politeness delay between gotos
- Robots-aware best effort + hard blocklist (extend existing `SOURCE_BLOCKLIST` patterns)
- Clear UI disclosure: “Agent is browsing on your behalf”
- Full action audit trail in session export
- Credential isolation: never log passwords into SSE or reports

### 9.3 Human-in-the-loop

Use LangGraph `interrupt` for:

- Submit confirmation (Task Assist)
- Captcha / login wall encountered
- Ambiguous high-impact click (optional Deep mode)
- Budget exhaustion with partial results (offer continue)

---

## 10. Drawbacks and risks

### 10.1 Technical

| Drawback | Impact | Mitigation |
|---|---|---|
| Higher latency | Minutes → tens of minutes | Budgets, Fast mode, 1–2 browsers max |
| Flaky web / anti-bot | Failed gotos | Fail-soft, negative cache, alternate sources |
| Chromium RAM/CPU | Resource spikes | Session pool, block images/fonts, close tabs |
| SPA / shadow DOM | Weak a11y refs | VLM sparingly; prefer static scholarly sources |
| Non-determinism | Hard to reproduce | Trace logs, seed policies, cache search |

### 10.2 Local LLM

| Drawback | Impact | Mitigation |
|---|---|---|
| Tool-call token burn | Slow runs | Compact state, small tool model |
| Small models mis-click | Loops | Schema validation, max repair 1, no-progress detector |
| Context blow-up | OOM / thrash | Never raw HTML; hard preview caps |
| Vision tokens | Huge cost | Screenshots off by default |
| Single GPU contention | Queue stalls | LLM semaphore; parallelize extract not generate |

### 10.3 Product / legal / UX

| Drawback | Impact | Mitigation |
|---|---|---|
| Users expect full Operator | Scope creep | Clear modes + research-first framing |
| ToS / scraping norms | Compliance | Allowlists, politeness, user-owned deployment |
| Live UI complexity | Slow frontend delivery | Ship ActionLog first; viewport second |
| Bad citations | Trust loss | Quote-level notes + citation mapper |
| Privacy | Local page cache | TTL purge; local-only default |

### 10.4 Explicit non-goals early

- Full DOM every step to the LLM  
- Unbounded parallel agents on one Ollama  
- Autologin / password vault in MVP  
- Always-on video stream of the browser  
- Replacing synthesis/report with infinite browse loop  

---

## 11. Implementation work packages

| WP | Deliverable | Depends | Est. effort |
|---|---|---|---|
| **WP1** | `BrowserSession` runtime + unit tests | — | 3–5 days |
| **WP2** | Compact `PageState` builder (outline, refs, preview) | WP1 | 2–3 days |
| **WP3** | Tools + policy + budgets + SSE events | WP1–2 | 4–6 days |
| **WP4** | `browser_agent` loop + graph hybrid Fast path | WP3 | 3–5 days |
| **WP5** | Model router, semaphores, num_ctx/predict presets | WP3 | 2–3 days |
| **WP6** | Cache expansion (page, negative, tool) | WP1 | 2 days |
| **WP7** | Frontend ActionLog + EvidenceDrawer | WP3 SSE | 3–5 days |
| **WP8** | BrowserViewport screenshots | WP7 | 2–4 days |
| **WP9** | Gap re-browse integration + e2e | WP4 | 3 days |
| **WP10** | Metrics: tokens, actions, cache hits, fail rate | WP5–9 | 2–3 days |
| **WP11** | Task Assist (list_fields, fill, dual confirm) | WP4, policy | 5–7 days |
| **WP12** | Playbooks + hardening + docs | WP9–11 | 3–5 days |

### MVP ship line

**WP1–WP6 + ActionLog UI (WP7 partial)** — agentic research without full live viewport or form autopilot.

### Suggested build order

1. Session browser + extract (better than one-shot scrape)  
2. Scripted tools without LLM (search → open top 3 → extract → notes)  
3. LLM chooses next action (ReAct + budget)  
4. Action log UI + evidence drawer  
5. Gap-driven re-browse  
6. Screenshots / viewport  
7. Task Assist with confirmations  
8. VLM + playbooks  

---

## 12. API / SSE contract (additions)

### 12.1 Research request options (illustrative)

```json
{
  "query": "…",
  "depth": 2,
  "complexity": 2,
  "paragraphs": 3,
  "subQuestions": 8,
  "options": {
    "browse_mode": "standard",
    "max_actions": 40,
    "max_tabs": 3,
    "enable_screenshots": false,
    "task_assist": false,
    "profile": {}
  }
}
```

### 12.2 New SSE / event_queue types

| type | payload (summary) |
|---|---|
| `browser_action` | `{step, tool, args, result_summary, tab_id}` |
| `browser_view` | `{url, title, screenshot_b64?}` |
| `tab_update` | `{tabs: [...]}` |
| `evidence` | `{note_id, claim, url, confidence}` |
| `budget` | `{actions_left, tokens_est_used, tokens_left}` |
| `interrupt_required` | `{interrupt_id, kind, message, payload}` |
| `thought` | existing |
| `source` | existing |

---

## 13. Frontend workstation UX

```text
┌────────────────┬─────────────────────────┬──────────────────┐
│ Sub-questions  │ Live browser frame      │ Evidence notes   │
│ Phase graph    │ (screenshot / preview)  │ Citations        │
│ Mode + budgets │ Action log (live)       │ Draft report     │
│ Pause/Cancel   │                         │ Export           │
└────────────────┴─────────────────────────┴──────────────────┘
```

**MVP UI minimum:** action log + evidence list + existing report/metrics (viewport optional).

Reuse existing patterns in `frontend/src/app/page.tsx`: `RESEARCH_PHASES`, telemetry logs, SSE consumption, metrics dashboard.

New phase id suggestion: `browser_agent` (label: **Browsing**) between Recall and Analyzing — or replace Searching.

---

## 14. Success metrics

| Metric | Target (Standard, local ~8B) |
|---|---|
| Actions per successful sub-question | ≤ 12 median |
| Sub-questions resolved without gap loop | ≥ 60% |
| Token use vs naive agentic baseline | ≤ 0.5–0.7×; ideally ≤ current REX + 20–40% |
| Empty extracts / goto | ≤ 15% |
| Citation URL validity + quote overlap | ≥ 90% |
| Time to first evidence event | &lt; 30–60s |
| Hung/crashed Chromium sessions | &lt; 2% |
| Cache hit rate (repeat entities) | Track; improve over time |
| Task Assist: successful fill without extra LLM loops | ≥ 70% heuristic-mapped fields |

Dashboard additions (alongside existing metrics):

- `actions_used` / `actions_budget`
- `tokens_in` / `tokens_out` (est.)
- `cache_hit_rate`
- `browse_fail_rate`
- `notes_count`
- `tabs_peak`

---

## 15. Testing strategy

| Layer | What |
|---|---|
| Unit | PageState builder; policy allow/deny; tool arg validation; budget decrement |
| Runtime | Playwright goto/click/extract on static fixture HTML server |
| Agent | Mock tools — ensure loop stops on `done` / empty budget / no-progress |
| Graph | Hybrid Fast vs Standard path selection; gap re-entry |
| E2E | One live query Standard mode; assert evidence events + report citations |
| Token | Fixture run counts approx tokens; regression cap in CI (optional) |
| Safety | Attempts to submit/login are denied or interrupted in tests |
| Frontend | SSE fixtures render ActionLog + evidence |

---

## 16. Rollout plan

| Stage | Audience | Flags |
|---|---|---|
| Dev | Local only | `BROWSER_AGENT_ENABLED=true` |
| Internal dogfood | Standard mode default off | Per-session option |
| Beta | Standard + Local-economy | Fast remains default for depth=1 |
| GA research | Standard default for depth≥2 | Deep opt-in |
| Task Assist beta | Explicit mode + confirms | Off by default |

Feature flags (env):

```text
BROWSER_AGENT_ENABLED=true
BROWSER_AGENT_DEFAULT_MODE=standard
BROWSER_MAX_ACTIONS=40
BROWSER_MAX_TABS=3
BROWSER_BLOCK_IMAGES=true
BROWSER_ALLOW_TASK_ASSIST=false
BROWSER_ALLOW_SUBMIT=false
LLM_LOCAL_CONCURRENCY=1
```

---

## 17. Benefits vs tradeoffs (summary)

| Benefits | Tradeoffs |
|---|---|
| Deeper multi-page evidence | Slower than pure search APIs |
| Transparent research trace | More engineering & ops surface |
| Differentiated vs chat+search wrappers | Local GPU bottleneck |
| Same LangGraph brain reused | Easy to explode cost if unconstrained |
| Path to forms/task automation | Safety & ToS complexity |
| Better docs/PDF link trails | Anti-bot dead ends |

---

## 18. Decision record

**Adopt: Hybrid Agentic Research Browser**

1. Keep **Fast** = current searcher/scrape (cheap, reliable baseline).  
2. **Standard/Deep** = browser agent with strict budgets, compact observations, model routing.  
3. UI ships **ActionLog + Evidence** first; live screenshots second.  
4. Optimize local tokens via extract-before-LLM, map-reduce, tiny tool model, caches, single-flight Ollama, hard `num_ctx` / `num_predict`.  
5. **Task Assist** is a separate gated mode with dual confirmation — not default research behavior.  
6. No login/pay/captcha bypass in v1–v2.

---

## 19. File checklist for implementers

### Backend create

- [ ] `backend/agents/browser_runtime.py`
- [ ] `backend/agents/browser_tools.py`
- [ ] `backend/agents/browser_agent.py`
- [ ] `backend/agents/browser_policy.py`
- [ ] `backend/tests/test_browser_runtime.py`
- [ ] `backend/tests/test_browser_agent.py`
- [ ] `backend/tests/test_browser_policy.py`

### Backend modify

- [ ] `backend/agents/state.py` — new fields
- [ ] `backend/agents/graph.py` — node + edges + hybrid path
- [ ] `backend/agents/scraper.py` — extract-from-HTML helper reuse
- [ ] `backend/agents/optimization.py` — negative/page/tool caches
- [ ] `backend/main.py` — events, options, interrupts
- [ ] `backend/requirements.txt` — pin playwright if needed; no heavy extras required

### Frontend create/modify

- [ ] `frontend/src/components/BrowserViewport.tsx`
- [ ] `frontend/src/components/ActionLog.tsx`
- [ ] `frontend/src/components/EvidenceDrawer.tsx`
- [ ] `frontend/src/app/page.tsx` — phases, SSE handlers, layout
- [ ] E2E specs for action stream rendering

### Docs

- [x] `info_files/agentic_browser_update.md` (this file)
- [ ] Update `Architecture.md`, `Features.md`, `API.md`, `Security.md` when implementing
- [ ] Update `UIUX.md` for workstation layout

---

## 20. Appendix A — Example compact tool turn

**Observation sent to tool model (~400–800 tokens):**

```text
GOAL: Find 2024 efficacy statistics for vaccine X
URL: https://example.edu/article
Title: Efficacy Update 2024
Outline: 1 Abstract 2 Methods 3 Results 4 Limitations
Preview: In a double-blind trial (n=12040), efficacy was 94.1% (95% CI …)
Links: [PDF] [Dataset] [References]
Actions:
  [1] link "Download PDF"
  [2] link "References"
  [3] button "Expand methods"
Notes: (none yet)
Budget: 7 actions left
Last: web_search → goto this url
```

**Model output:**

```json
{"tool": "extract", "args": {"mode": "main"}}
```

**Then:**

```json
{"tool": "note_claim", "args": {
  "claim": "Trial reported 94.1% efficacy (n=12040).",
  "quote": "efficacy was 94.1% (95% CI",
  "url": "https://example.edu/article"
}}
```

```json
{"tool": "done", "args": {"summary": "Primary efficacy figure captured from edu source."}}
```

---

## 21. Appendix B — Mapping to existing REX code

| Existing | Agentic use |
|---|---|
| `searcher_node` / `search_and_scrape` | Replaced or wrapped by `browser_agent` in Standard+ |
| `scrape_with_playwright` | Becomes session method, not one-shot launch/teardown |
| `emit_thought` / `emit_source` | Extended with browser/evidence events |
| `gap_detector_node` | Emits browse goals instead of only new search queries |
| `filter_node` / `chunk_text` / lexical score | Unchanged role; consume evidence + extracts |
| `citation_mapper_node` | Prefer quote-backed `evidence_notes` |
| `optimization.llm_response_cache` | Keep; add page/negative/tool caches |
| `interrupt` (LangGraph) | Task Assist + safety confirms |
| Frontend `RESEARCH_PHASES` | Add/replace Searching with Browsing |
| `vlm_client.py` | Optional screenshot understanding |
| n8n batch hooks | Later: scheduled browse playbooks |

---

## 22. Appendix C — Glossary

| Term | Meaning |
|---|---|
| **Agentic browser** | LLM chooses browser actions from observations in a loop |
| **PageState** | Compact structured page observation for the model |
| **Evidence note** | Atomic claim + quote + URL stored for synthesis/citation |
| **Action budget** | Max tool executions per sub-Q / session |
| **Hybrid Fast path** | Legacy non-agentic search+scrape for cheap runs |
| **Task Assist** | Gated form-fill mode with human confirmation |
| **Negative cache** | Remember failed URLs/reasons to avoid retry burn |
| **Model routing** | Different local models for tool vs write vs judge |

---

## 23. Next step for engineering

Start **WP1–WP3**: implement `BrowserSession`, compact `PageState`, policy-gated tools, and SSE `browser_action` events; keep graph on Fast/legacy searcher until the agent loop is stable, then flip Standard mode behind `BROWSER_AGENT_ENABLED`.

---

*End of document — REX Agentic Browser Update*
