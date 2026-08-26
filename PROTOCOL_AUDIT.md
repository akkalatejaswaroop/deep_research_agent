# Agent Communication Protocol Audit

## Overview

The REX (Recursive Exploration eXplorer) system uses four distinct communication protocols for agent-to-agent and agent-to-frontend interaction. This document audits each protocol for correctness, reliability, and security.

---

## Protocol 1: LangGraph State Passing (AgentState TypedDict)

**File:** `backend/agents/graph.py`  
**Layer:** In-process (Python in-memory)  
**Scope:** Between LangGraph nodes within a single pipeline execution

### Mechanism
- `AgentState` is a `TypedDict` with fields: `query`, `sub_questions`, `search_queries`, `source_urls`, `retrieved_memory`, `synthesis_results`, `report`, `feedback`, `gap_iteration`.
- List fields use `operator.add` annotation for automatic merging from node return dicts.
- Each node receives `(state: AgentState, config: RunnableConfig)` and returns a partial dict merged into the state.

### Data Flow
```
planner_node() -> {sub_questions, search_queries}
memory_retrieval_node() -> {retrieved_memory}
searcher_node() -> {source_urls}
filter_node() -> {} (side-effect: filters track_sources in closure)
synthesis_node() -> {synthesis_results}
gap_detector_node() -> {gap_iteration}
citation_mapper_node() -> {} (side-effect: formats refs)
report_node() -> {report}
evaluator_node() -> {feedback}
```

### Audit Findings
- [OK] TypedDict provides type safety at runtime
- [OK] `operator.add` ensures list concatenation (not replacement)
- [WARN] `filter_node` uses closure variable `track_sources` instead of state — breaks LangGraph checkpoint/replay
- [INFO] `MemorySaver` checkpointing is configured but not actively used for branching

**Risk:** Low. The state-passing is well-typed and predictable. The closure side-effect in `filter_node` is the only state inconsistency.

---

## Protocol 2: Event Queue (threading.Queue)

**File:** `backend/agents/graph.py` (created in `AgentNodeFactory`)  
**Layer:** In-process (thread-safe queue)  
**Scope:** Between LangGraph nodes and the SSE output generator

### Mechanism
- A shared `queue.Queue()` is created per session in the SSE generator and passed via `RunnableConfig["configurable"]["event_queue"]`.
- Nodes push structured events:
  - `{"node": "planner"}` — node transition
  - `{"type": "thought", "message": "..."}` — reasoning trace
  - `{"track_id": 1, "track_text": "...", "track_status": "searching"}` — sub-track status
  - `{"source_urls": [...]}` — discovered URLs
- The SSE generator reads from the same queue in a polling loop.

### Data Flow
```
Node → event_queue.put(event) → SSE generator → event_queue.get_nowait() → yield f"data: {json.dumps(event)}\n\n"
```

### Audit Findings
- [OK] Thread-safe queue prevents race conditions
- [OK] Non-blocking `get_nowait()` with `Empty` exception handling
- [WARN] No backpressure — a fast producer could queue thousands of events before the SSE consumer reads them
- [WARN] No queue size limit — unbounded memory growth if consumer is slow
- [INFO] Events are JSON-serialized before writing to the queue (double serialization: json.dumps in generator)

**Risk:** Low-Medium. The unbounded queue could cause OOM under extreme conditions, but in practice the pipeline is single-threaded per session.

---

## Protocol 3: SSE Streaming (Server-Sent Events)

**Endpoint:** `POST /api/v1/research/` and `GET /api/v1/learning-history/stream`  
**Transport:** HTTP long-lived connection, `text/event-stream` media type  
**Scope:** Backend → Frontend real-time telemetry

### Mechanism
- FastAPI `StreamingResponse` with a Python async generator
- Events formatted as `data: {json}\n\n` per SSE spec
- Written from a background thread via `run_in_executor`
- Frontend reads with `EventSource` API

### Event Types
| Event | Fields | Purpose |
|---|---|---|
| Node transition | `{"node": "planner"}` | Pipeline stage indicator |
| Thought trace | `{"type": "thought", "message": "..."}` | LLM reasoning visible to user |
| Track status | `{"track_id": 1, "track_text": "...", "track_status": "searching"}` | Per-sub-question progress |
| Sources | `{"source_urls": [...]}` | Accumulated source URLs |
| Completion | `{"node": "end", "report": "...", "metrics": {...}}` | Final report + metrics |
| Error | `{"node": "end", "error": "..."}` | Pipeline failure |
| Learning event | `{"content_hash": "...", "content": "...", ...}` | Real-time lesson delivery |

### Audit Findings
- [OK] `StreamingResponse` with async generator is idiomatic FastAPI
- [OK] Thread-safe queue prevents cross-thread data corruption
- [OK] Cancellation via `threading.Event` allows user to abort mid-request
- [WARN] No SSE event `type` field used — frontend infers type from field presence (`"track_id" in evt`, `"node" in evt`)
- [WARN] `EventSource` in the browser reconnects automatically, but the old session context is lost (no session_id on reconnect)
- [INFO] Some events are double-serialized (json.dumps in generator after already being serialized in the queue)

**Risk:** Low. SSE is well-suited for this use case. The inferred event type is fragile but functional.

---

## Protocol 4: HTTP REST API

**Base URL:** `/api/v1/`  
**Transport:** HTTP/1.1 JSON  
**Scope:** Frontend ↔ Backend for CRUD operations

### Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/research` | Start research (returns SSE stream) |
| POST | `/api/v1/research/{id}/cancel` | Cancel running research |
| GET | `/api/v1/sessions` | List past research sessions |
| GET | `/api/v1/research/{id}/metrics` | Get session metrics |
| GET | `/api/v1/research/{id}/export` | Export report (json/html/md) |
| GET | `/api/v1/learning-history` | List all lessons |
| GET | `/api/v1/learning-history/stream` | SSE stream for new lessons |
| GET | `/api/v1/learning-history/kpi` | Aggregate KPIs |
| GET | `/api/n8n/health` | n8n connectivity check |

### Audit Findings
- [OK] Consistent `/api/v1/` prefix
- [OK] CORS configured for frontend origin
- [OK] No authentication required (intentional — local-only tool)
- [WARN] No request rate limiting
- [WARN] No input validation beyond Pydantic model type checks
- [INFO] Sessions stored in-memory — lost on server restart (Supabase is optional persistence)

**Risk:** Low (local-only deployment). Would need auth, rate limiting, and input sanitization for production deployment.

---

## Protocol 5: n8n Webhook Integration (External Orchestrator)

**File:** `backend/agents/n8n_client.py`  
**Transport:** HTTP POST to `http://localhost:5678/webhook/deep-research-v3`  
**Scope:** Backend → n8n → Ollama for parallel sub-question processing

### Mechanism
- n8n workflow receives sub-questions via POST
- Runs each through local Ollama models in parallel
- Returns `{"results": [{"sub_question": "...", "insight": "..."}]}` via HTTP response

### Audit Findings
- [OK] HTTP timeout (30s) prevents hanging
- [OK] Graceful degradation — if n8n is offline, pipeline proceeds with web search only
- [WARN] No TLS — plain HTTP to localhost (acceptable for local deployment)
- [WARN] No authentication on webhook endpoint
- [WARN] Response size not limited — large n8n responses could consume memory

**Risk:** Low (local-only). Would need TLS, auth, and payload limits for production.

---

## Summary

| Protocol | Layer | Reliability | Security | Maintainability |
|---|---|---|---|---|
| LangGraph State | In-process | High | N/A (local) | Medium |
| Event Queue | In-process | Medium | N/A (local) | Medium |
| SSE Streaming | HTTP | High | N/A (local) | High |
| REST API | HTTP | High | Low | High |
| n8n Webhook | HTTP | Medium | Low | Medium |

### Recommendations
1. Add SSE event `type` field for structured event dispatch
2. Bound the event queue size to prevent OOM
3. Add request validation and rate limiting to REST endpoints
4. Document the AgentState schema explicitly for LangGraph nodes
