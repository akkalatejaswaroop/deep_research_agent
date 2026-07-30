# Architecture.md - System Architecture

## High-Level Architecture
- **Layered Design**:
  1. Presentation Layer (Next.js Frontend)
  2. Application Layer (FastAPI + LangGraph)
  3. Data Layer (PostgreSQL + Vector DB)
  4. AI Layer (LLM providers)

## Core: LangGraph Workflow
- **Nodes**: Supervisor (orchestrator), Specialized Agents (Researcher, Critic, etc.), Tool Nodes, Evaluator.
- **Edges**: Conditional routing based on state (e.g., confidence < threshold -> recurse).
- **State**: TypedDict with messages, current_task, history, metrics.
- **Cycles**: For recursive exploration and self-improvement.

## Self-Improvement Loop
- After completion: Evaluator scores output.
- Meta-agent suggests prompt/agent refinements.
- Store in memory for future use.

## Data Flow
1. User submits query -> API -> Supervisor Agent.
2. Decomposition -> Parallel/Sub-graph execution.
3. Tools & LLMs process.
4. Synthesis -> Output + Evaluation.
5. Feedback -> Update agent configs.

## Scalability
- Horizontal scaling with multiple workers.
- Async execution.

**Diagram (Text)**:
```
User -> Frontend -> API Gateway -> Supervisor Graph
                          |
                    +-----+-----+
                    |           |
               Researcher   Explorer
                    |           |
                 Synthesizer  Evaluator -> Self-Improve
```

For visual diagrams, use Mermaid in docs or draw.io.