# Graph Report - deep_research_agent  (2026-07-19)

## Corpus Check
- 80 files · ~150,205 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 582 nodes · 827 edges · 57 communities (48 shown, 9 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 59 edges (avg confidence: 0.7)
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
- README.md
- page.tsx
- test_e2e.py
- page.tsx
- test_fix.py
- AGENTS.md
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs

## God Nodes (most connected - your core abstractions)
1. `AgentState` - 28 edges
2. `make_state()` - 20 edges
3. `emit_thought()` - 17 edges
4. `MetricsTracker` - 17 edges
5. `build_report_autonomously()` - 16 edges
6. `compilerOptions` - 16 edges
7. `planner_node()` - 15 edges
8. `make_llm()` - 15 edges
9. `evaluator_node()` - 12 edges
10. `record_node_entry()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `fetch_pixelrag()` --calls--> `vlm_read_image()`  [INFERRED]
  backend/agents/graph.py → backend/agents/vlm_client.py
- `MockOllamaEmbeddings` --uses--> `AgentState`  [INFERRED]
  backend/tests/test_pipeline.py → backend/agents/state.py
- `TestCacheIntegration` --uses--> `AgentState`  [INFERRED]
  backend/tests/test_pipeline.py → backend/agents/state.py
- `TestCitationMapper` --uses--> `AgentState`  [INFERRED]
  backend/tests/test_pipeline.py → backend/agents/state.py
- `TestEvaluatorNode` --uses--> `AgentState`  [INFERRED]
  backend/tests/test_pipeline.py → backend/agents/state.py

## Import Cycles
- 1-file cycle: `backend/agents/__init__.py -> backend/agents/__init__.py`

## Communities (57 total, 9 thin omitted)

### Community 0 - "make_state"
Cohesion: 0.06
Nodes (33): make_llm(), make_state(), mock_ext_deps(), MockOllamaEmbeddings, Any, Comprehensive E2E tests for the deep research pipeline.  Tests cover:   - Each i, Tests for memory_retrieval_node (Stage 1b)., Tests for searcher_node — parallel search execution (Stage 2). (+25 more)

### Community 1 - "graph.py"
Cohesion: 0.11
Nodes (44): cached_search(), citation_mapper_node(), emit_source(), emit_thought(), evaluator_node(), extract_json(), fetch_duckduckgo(), fetch_pixelrag() (+36 more)

### Community 2 - "main.py"
Cohesion: 0.06
Nodes (56): _auto_research_profile(), build_report_autonomously(), _call_external_llm(), call_llm(), _coerce_sub_questions(), compute_overall(), _dedupe_sources(), export_research() (+48 more)

### Community 3 - "dependencies"
Cohesion: 0.05
Nodes (37): @copilotkit/react-core, @copilotkit/react-ui, dagre, framer-motion, dependencies, @copilotkit/react-core, @copilotkit/react-ui, dagre (+29 more)

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
Cohesion: 0.10
Nodes (16): react, GRAPH_NODES, LandingPage(), NODE_COPY, DashboardMetrics, Home(), normalizeHost(), PROGRESS_FLOORS (+8 more)

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

## Knowledge Gaps
- **194 isolated node(s):** `QualityScores`, `Task`, `eslintConfig`, `nextConfig`, `name` (+189 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentState` connect `graph.py` to `make_state`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `dependencies` connect `dependencies` to `devDependencies`, `page.tsx`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `AgentState` (e.g. with `LLMWrapper` and `MockOllamaEmbeddings`) actually correct?**
  _`AgentState` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `QualityScores`, `Task`, `eslintConfig` to the rest of the system?**
  _194 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `make_state` be split into smaller, more focused modules?**
  _Cohesion score 0.055051421657592255 - nodes in this community are weakly interconnected._
- **Should `graph.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11233766233766233 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.060764587525150904 - nodes in this community are weakly interconnected._