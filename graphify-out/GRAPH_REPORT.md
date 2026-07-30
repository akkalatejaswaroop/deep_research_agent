# Graph Report - deep_research_agent  (2026-07-22)

## Corpus Check
- 117 files · ~184,411 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 870 nodes · 1294 edges · 78 communities (64 shown, 14 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 161 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- make_state
- graph.py
- main.py
- dependencies
- MetricsTracker
- compilerOptions
- devDependencies
- page.tsx
- real_quality_scorer.py
- PDFReport
- Core Features
- Database.md - Database Design
- API.md - API Design
- 1. Introduction
- Key Screens
- Research Report: Quantum Computing advances in 2024
- TechStack.md - Technology Stack
- AI_Instructions.md - Agent Instructions and Prompts
- Deep Research Agent (REX) — 7-Slide Presentation
- layout.tsx
- Deployment.md - Deployment Strategy
- Security.md - Security Considerations
- GraphTopology
- Architecture.md - System Architecture
- Deep Research UI Designer
- GraphVisualizer.tsx
- error-context.md
- TraceImports
- e2e_verification.py
- README.md
- page.tsx
- celery_worker.py
- test_e2e.py
- page.tsx
- test_fix.py
- AGENTS.md
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- TestBenchmarkQueries
- build_provenance_report
- generate_sub_questions_tot
- critique_report
- TestSelfConsistencyUtilities
- call_llm
- _score_decomposition
- build_report_autonomously
- _extract_evidence
- search_all_sources
- _e2e_full.py
- db.py
- _e2e_real.py
- _run_query.py
- _auto_research_profile
- _e2e_quick.py
- _check_env.py
- _test_ollama_direct.py

## God Nodes (most connected - your core abstractions)
1. `KnowledgeGraph` - 28 edges
2. `AgentState` - 28 edges
3. `build_report_autonomously()` - 27 edges
4. `make_state()` - 20 edges
5. `planner_node()` - 18 edges
6. `emit_thought()` - 17 edges
7. `MetricsTracker` - 17 edges
8. `generate_sub_questions_tot()` - 17 edges
9. `compilerOptions` - 16 edges
10. `make_llm()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_sub_questions_are_forced_to_be_more_specific()` --calls--> `_coerce_sub_questions()`  [INFERRED]
  backend/tests/test_fast_mode.py → backend/main.py
- `test_evidence_matrix_marks_extraction_failure()` --calls--> `generate_evidence_matrix()`  [INFERRED]
  backend/tests/test_fast_mode.py → backend/main.py
- `fetch_pixelrag()` --calls--> `vlm_read_image()`  [INFERRED]
  backend/agents/graph.py → backend/agents/vlm_client.py
- `kg()` --calls--> `KnowledgeGraph`  [INFERRED]
  backend/tests/test_knowledge_graph.py → backend/agents/knowledge_graph.py
- `build_report_autonomously()` --calls--> `get_global_knowledge_graph()`  [INFERRED]
  backend/main.py → backend/agents/knowledge_graph.py

## Import Cycles
- 1-file cycle: `backend/agents/__init__.py -> backend/agents/__init__.py`

## Communities (78 total, 14 thin omitted)

### Community 0 - "make_state"
Cohesion: 0.06
Nodes (29): make_llm(), make_state(), mock_ext_deps(), MockOllamaEmbeddings, Any, Comprehensive E2E tests for the deep research pipeline.  Tests cover:   - Each i, Tests for memory_retrieval_node (Stage 1b)., Tests for searcher_node — parallel search execution (Stage 2). (+21 more)

### Community 1 - "graph.py"
Cohesion: 0.07
Nodes (56): _build_graph_provenance(), cached_search(), citation_mapper_node(), _classify_topic_type(), _cross_check_numeric_claims(), _cross_section_duplication_check(), emit_source(), emit_thought() (+48 more)

### Community 2 - "main.py"
Cohesion: 0.08
Nodes (17): Quick E2E - measure import vs execution time separately., _cross_check_numeric_claims(), _cross_section_duplication_check(), export_research(), _flag_single_source_claims(), generate_verification_notes(), _keyword_terms(), markdown() (+9 more)

### Community 3 - "dependencies"
Cohesion: 0.05
Nodes (39): @copilotkit/react-core, @copilotkit/react-ui, dagre, framer-motion, dependencies, @copilotkit/react-core, @copilotkit/react-ui, dagre (+31 more)

### Community 4 - "MetricsTracker"
Cohesion: 0.08
Nodes (14): call_api_llm(), _call_claude(), _call_openai_compat(), get_tracker(), MetricsTracker, NodeTiming, Any, QualityScores (+6 more)

### Community 5 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 6 - "devDependencies"
Cohesion: 0.08
Nodes (25): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+17 more)

### Community 7 - "page.tsx"
Cohesion: 0.11
Nodes (13): DEMO_TOPICS, GRAPH_NODES, LandingPage(), DashboardMetrics, DYNAMIC_EMERGING_TOPICS, getRandomEmergingTopics(), Home(), PROGRESS_FLOORS (+5 more)

### Community 8 - "real_quality_scorer.py"
Cohesion: 0.16
Nodes (14): compute_overall(), compute_quality_scores(), _ollama_available(), real_quality_scorer.py ----------------------- Computes REAL quality scores for, Compute quality scores using measurable heuristics when LLM is unavailable., Compute real quality scores for a research report.      1. Tries LLM-as-Judge (p, Compute overall quality as weighted average (half-up to 1 decimal)., Quick check if Ollama is running (2s timeout). (+6 more)

### Community 9 - "PDFReport"
Cohesion: 0.23
Nodes (4): markdown_to_pdf(), PDFReport, PDF Export Generator for REX — Recursive Exploration eXplorer.  Converts markdow, FPDF

### Community 10 - "Core Features"
Cohesion: 0.15
Nodes (12): 1. Multi-Agent Orchestration, 2. Recursive Exploration, 3. Self-Improving Mechanisms, 4. User Interface, 5. Research Output Generation, 6. Tool Integration, 7. Evaluation and Benchmarking, 8. Security and Privacy (+4 more)

### Community 11 - "Database.md - Database Design"
Cohesion: 0.17
Nodes (11): AgentInteractions, Data Flow, Database Choice, Database.md - Database Design, FeedbackLogs, Indexing, KnowledgeBase, Relationships (+3 more)

### Community 12 - "API.md - API Design"
Cohesion: 0.18
Nodes (10): Agent Control, API.md - API Design, Authentication, Base URL: /api/v1, Endpoints, Error Handling, Knowledge, LangGraph Integration (+2 more)

### Community 13 - "1. Introduction"
Cohesion: 0.18
Nodes (10): 1.1 Project Overview, 1.2 Objectives, 1.3 Target Audience, 1.4 Scope, 1.5 Assumptions and Dependencies, 1. Introduction, 2. Functional Requirements, 3. Non-Functional Requirements (+2 more)

### Community 14 - "Key Screens"
Cohesion: 0.18
Nodes (10): 1. Dashboard/Home, 2. New Research Session, 3. Live Execution View, 4. Results Page, 5. History & Library, Key Screens, Overall Design Philosophy, Tech for UI (+2 more)

### Community 15 - "Research Report: Quantum Computing advances in 2024"
Cohesion: 0.20
Nodes (9): Confidence Level, Conflicting Evidence, Executive Summary, Key Findings, References, Research Report: Quantum Computing advances in 2024, What are the fundamental concepts and principles behind Quantum Computing advances in 2024?, What are the latest breakthroughs and developments in Quantum Computing advances in 2024? (+1 more)

### Community 16 - "TechStack.md - Technology Stack"
Cohesion: 0.20
Nodes (9): AI/LLM Layer, Backend, Core Framework, Database, DevOps & Others, Frontend, Self-Improvement, TechStack.md - Technology Stack (+1 more)

### Community 17 - "AI_Instructions.md - Agent Instructions and Prompts"
Cohesion: 0.22
Nodes (8): AI_Instructions.md - Agent Instructions and Prompts, Critic Agent, Evaluator Agent (Self-Improvement), Explorer Agent, General Guidelines for All Agents, Researcher Agent, Supervisor Agent, Synthesizer Agent

### Community 18 - "Deep Research Agent (REX) — 7-Slide Presentation"
Cohesion: 0.22
Nodes (8): Deep Research Agent (REX) — 7-Slide Presentation, Slide 1: Title Slide, Slide 2: The Problem — Why Research Is Broken, Slide 3: The Solution — REX Overview, Slide 4: Architecture & Agent Pipeline, Slide 5: Key Features, Slide 6: Quality & Self-Improvement Results, Slide 7: Use Cases, Roadmap & Takeaways

### Community 19 - "layout.tsx"
Cohesion: 0.25
Nodes (4): jetbrainsMono, metadata, outfit, syne

### Community 20 - "Deployment.md - Deployment Strategy"
Cohesion: 0.25
Nodes (7): Containerization, Deployment.md - Deployment Strategy, Development, Environment Variables, Monitoring, Scaling, Staging/Production

### Community 21 - "Security.md - Security Considerations"
Cohesion: 0.25
Nodes (7): Agent Security, Authentication & Authorization, Compliance, Data Protection, Privacy, Security.md - Security Considerations, Vulnerability Management

### Community 22 - "GraphTopology"
Cohesion: 0.29
Nodes (3): GraphTopology, Quick smoke test of core simulation logic., Task

### Community 23 - "Architecture.md - System Architecture"
Cohesion: 0.29
Nodes (6): Architecture.md - System Architecture, Core: LangGraph Workflow, Data Flow, High-Level Architecture, Scalability, Self-Improvement Loop

### Community 24 - "Deep Research UI Designer"
Cohesion: 0.33
Nodes (5): Deep Research UI Designer, Preferences, Role, Scope, When to use this agent

### Community 25 - "GraphVisualizer.tsx"
Cohesion: 0.40
Nodes (5): dagreGraph, getLayoutedElements(), GraphVisualizer(), initialEdges, initialNodes

### Community 26 - "error-context.md"
Cohesion: 0.11
Nodes (18): Deep Research Report: Generative Artificial Intelligence In 2026 Architectures Global Economy Ecosystems And Legal Regulation, Evidence Matrix, Executive Summary, Future Outlook, How does Generative artificial intelligence in 2026 architectures global economy ecosystems and legal regulation compare with alternative approaches, competing technologies, or prior methods?, Introduction / Context, Key Findings & Analysis, Limitations and Open Questions (+10 more)

### Community 30 - "README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 32 - "celery_worker.py"
Cohesion: 0.05
Nodes (18): _extract_triples_from_text(), get_global_knowledge_graph(), KnowledgeGraph, Extract triples from text and add them to the graph. Returns count., Extract triples from each synthesis result. Returns total count., Get all triples where entity is the subject., Get all triples where entity is the object (i.e., who points to it)., BFS from entity to find related entities up to max_hops away. (+10 more)

### Community 58 - "TestBenchmarkQueries"
Cohesion: 0.09
Nodes (13): compare_runs(), _get_main(), main(), print_report(), run_benchmark.py ---------------- Benchmark runner for REX deep research agent., run_benchmark(), run_single(), make_mock_result() (+5 more)

### Community 59 - "build_provenance_report"
Cohesion: 0.08
Nodes (16): build_provenance_report(), _extract_claims_from_section(), _format_provenance_section(), _parse_citations(), Extract all [N] citation numbers from text, preserving order of first appearance, Split section into sentences and keep only those with citations., Map citation numbers in a claim to actual source metadata using a lookup dict., Build a structured provenance map linking every cited claim to its source URLs. (+8 more)

### Community 60 - "generate_sub_questions_tot"
Cohesion: 0.13
Nodes (15): _classify_topic_type(), _coerce_sub_questions(), extract_json(), generate_sub_questions(), generate_sub_questions_tot(), _is_stable_technical_topic(), Generate one decomposition from a specific perspective., Tree of Thoughts: generate multiple alternative decompositions, score, pick best (+7 more)

### Community 61 - "critique_report"
Cohesion: 0.12
Nodes (12): critique_report(), Generate specific, actionable critique items for improving the report., Improve the report by addressing each critique item., refine_report(), test_reflection.py Tests for Phase 3: Reflection & Critique Loops. Verifies that, Test reflection in the graph path's report_node., Test the critique_report function., Test the refine_report function. (+4 more)

### Community 62 - "TestSelfConsistencyUtilities"
Cohesion: 0.13
Nodes (9): _aggregate_json_via_voting(), _aggregate_text_via_voting(), Parse each response as JSON, collect values for the given key, vote for most com, Pick the response with the most citations; fallback to longest., test_self_consistency.py Tests for Phase 2: Self-Consistency Reasoning. Verifies, Test that the graph path planner uses self-consistency., Test the _self_consistent_call_llm, _aggregate_json_via_voting, _aggregate_text_, TestGraphPathSelfConsistency (+1 more)

### Community 63 - "call_llm"
Cohesion: 0.16
Nodes (16): _call_external_llm(), call_llm(), _call_llm_with_temp(), generate_executive_summary(), generate_future_outlook(), generate_gap_analysis(), generate_implications_section(), generate_report_introduction() (+8 more)

### Community 64 - "_score_decomposition"
Cohesion: 0.15
Nodes (9): Score a decomposition based on query term coverage and question distinctness., _score_decomposition(), test_tree_of_thoughts.py Tests for Phase 4: Tree of Thoughts for Planning., Test ToT in the graph path's planner_node., Test the _score_decomposition function., Test ToT integration into the pipeline., TestGraphPathToT, TestScoreDecomposition (+1 more)

### Community 65 - "build_report_autonomously"
Cohesion: 0.16
Nodes (11): build_report_autonomously(), compute_overall(), generate_methodology_section(), generate_quality_scores(), _normalize_topic(), Score report quality using LLM-as-Judge when possible, falling back to heuristic, test_build_fast_report_avoids_canned_generic_language(), test_build_fast_report_returns_complete_report() (+3 more)

### Community 66 - "_extract_evidence"
Cohesion: 0.31
Nodes (11): _extract_evidence(), _extraction_failure_marker(), _fallback_section(), _generate_data_highlights(), generate_evidence_matrix(), _is_blocked_source(), _numeric_claim_note(), _score_sentence() (+3 more)

### Community 67 - "search_all_sources"
Cohesion: 0.24
Nodes (10): _classify_source_tier(), _dedupe_sources(), _extract_domain(), search_all_sources(), search_serpapi(), search_tavily(), search_web_duckduckgo(), search_wikipedia() (+2 more)

### Community 68 - "_e2e_full.py"
Cohesion: 0.33
Nodes (3): on_thought(), on_track_status(), Full end-to-end user query test with mocked network.

### Community 70 - "_e2e_real.py"
Cohesion: 0.40
Nodes (3): on_thought(), on_track_status(), Full end-to-end with REAL LLM (Ollama) + REAL search (Wikipedia + DuckDuckGo).

### Community 71 - "_run_query.py"
Cohesion: 0.40
Nodes (3): on_thought(), on_track_status(), Full end-to-end user query test with detailed output.

### Community 72 - "_auto_research_profile"
Cohesion: 0.40
Nodes (5): _auto_research_profile(), ResearchQuery, start_research(), test_auto_research_profile_sets_parameters_from_query(), BaseModel

## Knowledge Gaps
- **192 isolated node(s):** `QualityScores`, `Task`, `eslintConfig`, `nextConfig`, `name` (+187 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_global_knowledge_graph()` connect `celery_worker.py` to `build_report_autonomously`, `graph.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `AgentState` connect `graph.py` to `make_state`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `KnowledgeGraph` (e.g. with `kg()` and `TestAddFromSynthesis`) actually correct?**
  _`KnowledgeGraph` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `AgentState` (e.g. with `LLMWrapper` and `MockOllamaEmbeddings`) actually correct?**
  _`AgentState` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `build_report_autonomously()` (e.g. with `main.py` and `get_global_knowledge_graph()`) actually correct?**
  _`build_report_autonomously()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `QualityScores`, `Task`, `eslintConfig` to the rest of the system?**
  _192 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `make_state` be split into smaller, more focused modules?**
  _Cohesion score 0.0641025641025641 - nodes in this community are weakly interconnected._