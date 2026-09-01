# Test A — Single Research Run, Core Correctness

## Executions

| v | Wall | Outcome |
|---|------|---------|
| v1 | 465s | 11/11 nodes correct order; filter crashed per-SQ ('list' has no .lower); ALL vault writes failed (NameError time); RUN create failed (No module named backend) |
| v2 | >30m killed | Filter fixed (21 chunks); synthesis/report hit 300s stage timeouts (CPU-only qwen2.5:3b, ctx 4096) |
| v3 | 566s | Writes fixed: RUN/CLM/SRC/LSN/QST created + FCT updated in place; filter 0 chunks (LLM-judge gate unsatisfiable) |
| v4 | 944s | Best run: 19 chunks, refs=7, RUN-01J8Y22E8F916C11D6A441CEE3 + 7 linked notes; syntheses discarded by stage timeout -> report without inline citations |
| v5 | 517s | Judge JSON unparseable -> fallback int(6*quality)<=6 < THRESHOLD 7 -> 0 chunks by construction |
| v6 | 515s | Planner LLM fell back to template SQs; only 5 pages fetched; filter 0 chunks |

## Verdict per criterion

1. Node order — PASS (v1,v3,v4,v5,v6): exact sequence memory_retrieval -> planner ->
   searcher -> filter -> synthesis -> gap_detector -> citation_mapper -> report_node_id
   -> evaluator -> memory_update -> evolution_analysis. Matches implemented topology
   graph.py edges (:2834-2850). Spec-mapping note: no separate "Knowledge Retrieval"
   node (folded into memory_retrieval buckets); Final Report sits BEFORE Evaluation.
2. Claims traceable to citations — FAIL (environment-bound): CPU-only Ollama ~10 tok/s;
   synthesis stage timeouts discarded results; report built from fallbacks with 0 [n] markers.
3. Citations resolve to real 03_Sources notes — PARTIAL: SRC notes ARE created and
   dedup-updated across runs (SRC-01J8Y379BF62AB5F967F184B4D create->update "add evidence";
   SRC-01J8Y70386244CC3F572E96403 same), but only ~2 source candidates extracted/run vs 7 URLs in refs.
4. No silently swallowed errors — FAIL (and this criterion caught 6 real defects, see below).
   Residual: TimeoutHandler degrades to fallback text w/ stdout print only; "[INSUFFICIENT EVIDENCE]"
   answers flow on as success.
5. Wall-clock/cost logged — PASS for latency (evidence.json wall_clock_seconds).
   Token cost NOT tracked anywhere (pipeline or ChatOllama) — gap.

## Defects found & fixed during Test A

| # | Location | Bug | Fix |
|---|----------|-----|-----|
| 1 | graph.py memory_update_node | bare time.gmtime() vs _time alias -> NameError killed EVERY classification write | use _time.gmtime() |
| 2 | filter_node | nested search_queries from planner crash lexical_score (.lower on list) | _flatten_queries normalization |
| 3 | graph.py:2584 | absolute import backend.agents.memory_agent fails outside FastAPI process | relative-import fallback |
| 4 | state.py | AgentState lacked run_id/classification_table/linked_notes -> node returns silently dropped | added fields |
| 5 | synthesis_node | prompt = N chunks x 1200 chars exceeds local ctx/speed -> guaranteed stage timeouts | cap top-8 chunks x 800 chars, quality-weighted ranking preserved |
| 6 | filter_node else-branch | judge-parse-failure fallback score int(6*quality) <= 6 can never clear THRESHOLD=7 | lexical-score fallback gate |

## Evidence

- rex_test_evidence/A_core_run_v1..v6/{evidence.json, report.md, cited_report.md,
  structured_refs.json, classification_table.json, run_stdout.log}
- Sandbox vault git log (rex_test_vault): one commit per write, e.g. v4 run produced
  8c00f41 RUN, dad1ba5 QST update, 92a2c4e LSN, a08129c+87d7c3c SRC update/create,
  030e33e CTR (auditor), 015ee55 CLM update, 5049608 FCT update:v3.

## RESULT: PARTIAL PASS

Mechanism layer verified (topology, order, memory write path, git-per-write, run record).
Answer-citation integrity FAILS under local-model latency; would require GPU-sized models
or remote API LLM to pass criterion 2 deterministically.
