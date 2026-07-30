# Database.md - Database Design

## Database Choice
- **Primary DB**: PostgreSQL 16.
- **Vector DB**: Chroma (local) or PGVector extension for unified storage.

## Schema Overview

### Users Table
- id, email, hashed_password, role, created_at.

### ResearchSessions
- id, user_id, query, status (pending/running/completed), depth, created_at, completed_at.
- JSONB for configuration and metrics.

### AgentInteractions
- id, session_id, agent_type, input, output, timestamp, confidence_score, tokens_used.

### KnowledgeBase
- id, content_hash, embedding_vector, source, relevance_tags.
- For persistent memory across sessions.

### FeedbackLogs
- id, session_id, user_feedback, auto_eval_score, improvements_applied.

## Relationships
- Sessions 1:N Interactions.
- Users 1:N Sessions.

## Indexing
- Full-text search on queries.
- Vector indexes for similarity search.

## Data Flow
- On task start: Store session.
- During execution: Log agent states.
- Post-completion: Store synthesized knowledge, trigger self-improvement.

**Migrations:** Use Alembic for schema management.

**Backup & Privacy:** Encrypted at rest, GDPR compliant.