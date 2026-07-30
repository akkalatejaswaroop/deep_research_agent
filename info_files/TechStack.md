# TechStack.md - Technology Stack

## Core Framework
- **LangGraph (LangChain)**: For multi-agent orchestration and stateful graphs.
- **Python 3.11+**: Backend language.

## AI/LLM Layer
- Primary: Grok API / xAI models (or OpenAI GPT-4o, Anthropic Claude).
- Embeddings: Sentence Transformers or OpenAI embeddings.
- Vector Store: ChromaDB or Pinecone.

## Backend
- **FastAPI**: RESTful APIs.
- **LangServe**: For exposing LangGraph as APIs.
- Celery + Redis: For async task queues.

## Database
- PostgreSQL: For structured data (users, sessions, history).
- Vector DB: For research memory.

## Frontend
- Next.js 14+ with App Router.
- React, TypeScript, TailwindCSS.
- Shadcn/UI components.

## Visualization & Tools
- Graph viz: React Flow.
- Markdown rendering: React Markdown.
- Export: pdf-lib or WeasyPrint.

## DevOps & Others
- Docker & Docker Compose for containerization.
- Git for version control.
- Poetry for Python dependency management.
- Testing: Pytest, Playwright.

## Self-Improvement
- Prompt optimization libraries.
- Optional: LangSmith for tracing and evaluation.

This stack ensures modularity, scalability, and alignment with LangGraph best practices.