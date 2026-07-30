# Deep Research Agent (REX) — 7-Slide Presentation

---

## Slide 1: Title Slide

**Title:** REX — Recursive Exploration eXplorer
**Subtitle:** A Self-Improving Multi-Agent Deep Research Platform
**Tagline:** From Questions to Publication-Quality Reports — Autonomously
**By:** [Your Name / Team Name]
**Logo:** [Optional: REX branding]

---

## Slide 2: The Problem — Why Research Is Broken

**Headline:** Research today is slow, shallow, and unreliable.

**Key Points:**
- **Single-LLM answers lack depth** — One model call cannot thoroughly explore complex, multi-faceted topics.
- **No citation grounding** — AI-generated content often hallucinates; claims are rarely backed by verifiable sources.
- **No iterative refinement** — Traditional tools don't detect knowledge gaps or re-search for missing information.
- **No cross-session learning** — Every query starts from scratch; past insights are wasted.
- **Single-source bias** — Most solutions rely on one search API or knowledge source, limiting perspective.
- **Inconsistent quality** — Output quality is unmeasured and varies widely across queries.

**Impact:** Researchers, analysts, and decision-makers spend hours manually gathering, cross-referencing, and synthesizing information — and still miss critical insights.

---

## Slide 3: The Solution — REX Overview

**Headline:** REX: Autonomous, Multi-Agent Deep Research

**What it is:** A self-improving multi-agent orchestration platform built on LangGraph that takes a user query and autonomously produces a comprehensive, cited, publication-quality report.

**Core Capabilities:**
- **Recursive decomposition** — Breaks complex queries into sub-questions and explores each in depth.
- **Multi-source search** — Queries 5+ search APIs in parallel (Tavily, Firecrawl, SerpAPI, LangSearch, PixelRAG, DuckDuckGo).
- **LLM-as-Judge filtering** — Scores relevance of every source and keeps only high-quality passages.
- **Gap detection & re-search** — Identifies incomplete answers and automatically triggers additional search rounds.
- **Citation mapping** — Every factual claim is cross-validated and linked to a real source URL.
- **Automated quality scoring** — Each report is evaluated on 5 dimensions with explainable metrics.

**Key Differentiator:** Self-improvement loop — lessons from each run are stored in a vector knowledge base and retrieved to improve future research.

---

## Slide 4: Architecture & Agent Pipeline

**Headline:** 9 Specialized Agents in a LangGraph State Machine

**Pipeline (left-to-right flow):**

1. **Planner** → Decomposes query into sub-questions + search queries; retrieves prior lessons.
2. **Memory Retrieval** → Hybrid vector+keyword search in Supabase for past relevant research.
3. **Searcher** → Parallel multi-API web searches across all sub-questions (ThreadPoolExecutor).
4. **Filter** → LLM-as-Judge relevance scoring + MMR-based chunk deduplication.
5. **Synthesis** → Structured multi-paragraph answers per sub-question with inline citations.
6. **Gap Detector** → Evaluates completeness; triggers re-search loop if gaps found.
7. **Citation Mapper** → Cross-validates all `[N]` references; deduplicates sources.
8. **Report Generator** → Assembles executive summary, findings, analysis, references, glossary.
9. **Evaluator** → Scores report (relevance, depth, novelty, coherence, citation accuracy); stores lesson learned.

**Conditional Loop:** Gap Detector → Searcher (up to N passes, configurable depth 1-3).

**Infrastructure:** FastAPI backend, Celery + Redis task queue, Supabase (PostgreSQL + pgvector), Next.js 16 frontend.

---

## Slide 5: Key Features

**Headline:** What REX Delivers

**Research Capabilities:**
- Configurable sub-questions (3-14), paragraphs per track (1-5), complexity levels (1-3)
- Recursive exploration with depth control and automated gap-detection loops
- Real-time SSE streaming of progress, sources, and thought logs
- Multi-format export: JSON, Markdown, HTML (styled), PDF

**Self-Improvement:**
- Vector knowledge base stores lessons learned from every run
- Quality scores tracked over time per normalized topic
- Planner retrieves prior lessons to inform new research (proof of improvement)

**User Experience:**
- Interactive React Flow pipeline visualization (9-node graph with live highlighting)
- Parallel sub-question track status monitoring
- Metrics dashboard: time per stage (bar chart), quality scores (radar chart), LLM calls per stage
- History & Learning pages to browse past sessions and agent memory
- Dark, premium UI with glass-morphism panels and real-time animations

**Platform Modes (6-in-1):**
Research (primary), Chat, Search, Multimodal Analysis, Code Execution, Social Intelligence

---

## Slide 6: Quality & Self-Improvement Results

**Headline:** Measured Quality That Improves Over Time

**5-Dimension Quality Scoring (LLM-as-Judge):**
| Dimension | What It Measures |
|---|---|
| Relevance | How well the report addresses the user query |
| Depth | Thoroughness of sub-topic exploration |
| Novelty | Unique insights beyond obvious sources |
| Coherence | Logical flow and structural clarity |
| Citation Accuracy | Proper grounding of claims to sources |

**Self-Improvement Loop:**
1. Evaluator scores report and extracts a "lesson learned"
2. Lesson is stored in Supabase vector knowledge base
3. On future similar queries, Planner retrieves relevant lessons
4. Lessons are injected as prompt guidance for better planning
5. Quality deltas are tracked over time → proof of improvement

**Graceful Degradation:**
- No Supabase? → Falls back to in-memory storage
- No Ollama? → Heuristic quality scoring
- No API keys configured? → DuckDuckGo fallback search

**Observability:** Metrics dashboard shows quality history, time per stage, and LLM call counts for every session.

---

## Slide 7: Use Cases, Roadmap & Takeaways

**Headline:** Applications & Future Direction

**Use Cases:**
- **Market research** — Competitive landscape analysis with cited sources
- **Academic literature review** — Multi-perspective synthesis of complex topics
- **Policy analysis** — Regulatory history, economic impact, stakeholder positions
- **Technology assessment** — Architecture comparison, commercialization landscape
- **Due diligence** — Company research with cross-referenced sources

**Tech Stack Summary:**
| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Agent Framework | LangGraph |
| LLMs | Ollama (local), OpenAI GPT-4o, Anthropic Claude |
| Search APIs | Tavily, Firecrawl, SerpAPI, LangSearch, PixelRAG |
| Database | Supabase (PostgreSQL + pgvector) |
| Task Queue | Celery + Redis |
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS 4 |

**Future Roadmap:**
- Multi-session comparative analysis
- Custom source inclusion (user-provided PDFs/URLs)
- Fine-tuned small models for specific pipeline stages
- Collaborative research with shared workspaces
- Real-time web monitoring for ongoing topics

**Key Takeaway:** REX transforms open-ended research from a manual, time-intensive process into an autonomous, self-improving pipeline that delivers grounded, comprehensive, publication-quality reports in minutes.
