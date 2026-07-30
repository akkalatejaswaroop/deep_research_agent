# API.md - API Design

## Base URL: /api/v1

### Authentication
- JWT or API Keys.

## Endpoints

### Research Management
- **POST /research/**: Start new research. Body: {query, options}.
- **GET /research/{id}**: Get status and progress.
- **GET /research/{id}/graph**: Get execution graph state.
- **POST /research/{id}/feedback**: Submit user feedback for improvement.

### Agent Control
- **GET /agents/**: List available agents and capabilities.
- **POST /agents/{type}/test**: Test an agent prompt.

### Knowledge
- **POST /knowledge/search**: Vector search in memory.
- **GET /knowledge/**: Browse stored insights.

### System
- **GET /health**: Health check.
- **GET /metrics**: Usage and performance metrics.

## LangGraph Integration
- Use LangServe to expose graphs as runnable APIs.
- Streaming responses for live updates via WebSockets (optional).

## Error Handling
- Standard HTTP codes with detailed JSON errors.
- Rate limiting.

**OpenAPI/Swagger:** Auto-generated with FastAPI.