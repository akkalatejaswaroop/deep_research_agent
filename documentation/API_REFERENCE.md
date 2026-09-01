# Deep Research Agent (REX) - API Reference Documentation

## Overview
This document provides comprehensive API reference information for the Deep Research Agent (REX) system. It covers all REST endpoints, WebSocket connections, Server-Sent Events (SSE) streams, and internal agent communication protocols.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
For secured endpoints, include the JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting
- Default limit: 100 requests per minute per IP
- Headers returned:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Seconds until limit reset

## Error Responses
All errors follow this format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional error-specific information
    }
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Input validation failed
- `AUTHENTICATION_REQUIRED`: Missing or invalid credentials
- `AUTHORIZATION_FAILED`: Insufficient permissions
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `INTERNAL_ERROR`: Unexpected server error
- `SERVICE_UNAVAILABLE`: Dependency service unavailable

## Research Endpoints

### Start Research Job
```http
POST /research
Content-Type: application/json

{
  "query": "string (required)",
  "options": {
    "max_depth": "integer (default: 3)",
    "paragraphs_per_section": "integer (default: 3)",
    "tracks": "integer (default: 5)",
    "timeout_seconds": "integer (default: 300)",
    "stream": "boolean (default: true)",
    "format": "markdown|html|json|pdf (default: markdown)"
  }
}
```

**Response (when stream=false):**
```json
{
  "job_id": "string (UUID)",
  "status": "pending|processing|completed|failed|cancelled",
  "created_at": "ISO 8601 datetime",
  "estimated_completion": "ISO 8601 datetime (optional)",
  "progress": {
    "percentage": "integer (0-100)",
    "current_stage": "string",
    "message": "string (optional)"
  }
}
```

**Response (when stream=true):** Returns SSE stream

### Server-Sent Events Stream
When `stream=true` in the request, the endpoint returns an SSE stream with the following event types:

#### Event Types
```json
{
  "event_type": "NODE_TRANSITION",
  "data": {
    "node": "planner|searcher|filter|synthesis|gap_detector|citation_mapper|report_generator|evaluator",
    "timestamp": "ISO 8601 datetime"
  }
}
```

```json
{
  "event_type": "THOUGHT_TRACE",
  "data": {
    "message": "string (LLM reasoning trace)",
    "agent_type": "string",
    "agent_id": "string (optional)",
    "timestamp": "ISO 8601 datetime"
  }
}
```

```json
{
  "event_type": "TRACK_STATUS",
  "data": {
    "track_id": "integer",
    "track_text": "string (sub-question)",
    "track_status": "pending|searching|filtering|synthesizing|completed|failed",
    "progress": "integer (0-100) (optional)",
    "sources_found": "integer (optional)",
    "timestamp": "ISO 8601 datetime"
  }
}
```

```json
{
  "event_type": "SOURCES_UPDATE",
  "data": {
    "source_urls": ["string"],
    "new_sources": ["string"] (optional),
    "timestamp": "ISO 8601 datetime"
  }
}
```

```json
{
  "event_type": "COMPLETION",
  "data": {
    "report": "string (final report in requested format)",
    "format": "markdown|html|json|pdf",
    "metrics": {
      "total_time_seconds": "float",
      "llm_calls": "integer",
      "tokens_used": "integer",
      "search_api_calls": "integer",
      "sources_processed": "integer",
      "cache_hits": "integer",
      "recursion_depth": "integer"
    },
    "timestamp": "ISO 8601 datetime"
  }
}
```

```json
{
  "event_type": "ERROR",
  "data": {
    "error": {
      "code": "string",
      "message": "string",
      "details": "object (optional)"
    },
    "timestamp": "ISO 8601 datetime"
  }
}
```

```json
{
  "event_type": "LEARNING_EVENT",
  "data": {
    "content_hash": "string (SHA-256 of learned content)",
    "content": "string (lesson learned)",
    "relevance_score": "float (0.0-1.0)",
    "agent_type": "string",
    "timestamp": "ISO 8601 datetime"
  }
}
```

### Get Research Status
```http
GET /research/{job_id}
```

**Response:**
```json
{
  "job_id": "string (UUID)",
  "status": "pending|processing|completed|failed|cancelled",
  "created_at": "ISO 8601 datetime",
  "started_at": "ISO 8601 datetime (optional)",
  "completed_at": "ISO 8601 datetime (optional)",
  "query": "string",
  "options": {
    // Echo of request options
  },
  "progress": {
    "percentage": "integer (0-100)",
    "current_stage": "string",
    "message": "string (optional)",
    "estimated_time_remaining": "integer (seconds, optional)"
  },
  "result": {
    // Present only when status is completed or failed
    "report": "string (when completed)",
    "format": "string (when completed)",
    "metrics": {
      // Same as completion event metrics
    },
    "error": {
      // Present only when status is failed
      "code": "string",
      "message": "string",
      "details": "object (optional)"
    }
  }
}
```

### Cancel Research Job
```http
POST /research/{job_id}/cancel
```

**Response:**
```json
{
  "success": "boolean",
  "message": "string",
  "job_id": "string (UUID)",
  "status": "cancelled"
}
```

### Get Research Metrics
```http
GET /research/{job_id}/metrics
```

**Response:**
```json
{
  "job_id": "string (UUID)",
  "metrics": {
    "total_time_seconds": "float",
    "stage_timings": {
      "planner": "float",
      "memory_retrieval": "float",
      "searcher": "float",
      "filter": "float",
      "synthesis": "float",
      "gap_detector": "float",
      "citation_mapper": "float",
      "report_generator": "float",
      "evaluator": "float"
    },
    "llm_usage": {
      "calls": "integer",
      "tokens": {
        "input": "integer",
        "output": "integer",
        "total": "integer"
      },
      "models": {
        "planner_model": "string",
        "report_model": "string"
      }
    },
    "search_statistics": {
      "total_queries": "integer",
      "successful_searches": "integer",
      "failed_searches": "integer",
      "api_breakdown": {
        "tavily": "integer",
        "firecrawl": "integer",
        "serpapi": "integer",
        "duckduckgo": "integer",
        "other": "integer"
      },
      "average_response_time": "float",
      "timeout_count": "integer"
    },
    "cache_performance": {
      "llm_cache_hits": "integer",
      "llm_cache_misses": "integer",
      "search_cache_hits": "integer",
      "search_cache_misses": "integer",
      "hit_rate": "float (0.0-1.0)"
    },
    "recursion_info": {
      "max_depth_reached": "integer",
      "gaps_detected": "integer",
      "re_search_triggered": "integer"
    },
    "quality_scores": {
      "relevance": "float (0.0-10.0)",
      "depth": "float (0.0-10.0)",
      "novelty": "float (0.0-10.0)",
      "coherence": "float (0.0-10.0)",
      "citation_accuracy": "float (0.0-10.0)",
      "overall": "float (0.0-10.0)"
    }
  },
  "timestamp": "ISO 8601 datetime"
}
```

### Export Research Report
```http
GET /research/{job_id}/export?format=markdown|html|json|pdf
```

**Response:**
- For `format=markdown`: `text/plain` with markdown content
- For `format=html`: `text/html` with HTML content
- For `format=json`: `application/json` with structured report data
- For `format=pdf`: `application/pdf` with PDF binary

**Query Parameters:**
- `format`: Required, one of `markdown`, `html`, `json`, `pdf`
- `include_metadata`: Boolean (default: false) - include metadata in export
- `include_sources`: Boolean (default: true) - include source URLs in export
- `styled`: Boolean (default: false for HTML/MD, true for PDF) - apply styling

## Agent Management Endpoints

### List All Agents
```http
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "agent_id": "string (UUID)",
      "agent_type": "string (planner|searcher|filter|synthesis|gap_detector|citation_mapper|report_generator|evaluator|memory_manager|orchestrator|monitor)",
      "status": "active|inactive|maintenance|error",
      "endpoint": "string (URL)",
      "registered_at": "ISO 8601 datetime",
      "last_heartbeat": "ISO 8601 datetime",
      "load": "float (0.0-1.0)",
      "capabilities": ["string"],
      "metadata": {
        // Agent-specific configuration
      }
    }
  ],
  "pagination": {
    "total": "integer",
    "page": "integer",
    "per_page": "integer",
    "pages": "integer"
  }
}
```

**Query Parameters:**
- `agent_type`: Filter by agent type
- `status`: Filter by status
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50)
- `sort_by`: Field to sort by (default: registered_at)
- `sort_order`: asc|desc (default: desc)

### Get Specific Agent
```http
GET /agents/{agent_id}
```

**Response:**
```json
{
  "agent_id": "string (UUID)",
  "agent_type": "string",
  "status": "active|inactive|maintenance|error",
  "endpoint": "string (URL)",
  "registered_at": "ISO 8601 datetime",
  "last_heartbeat": "ISO 8601 datetime",
  "load": "float (0.0-1.0)",
  "capabilities": ["string"],
  "metadata": {
    // Agent-specific configuration
  },
  "health": {
    "status": "healthy|degraded|unhealthy",
    "checks": [
      {
        "name": "string",
        "status": "passed|failed|warning",
        "message": "string (optional)",
        "timestamp": "ISO 8601 datetime"
      }
    ],
    "last_check": "ISO 8601 datetime"
  },
  "performance": {
    "avg_response_time": "float (seconds)",
    "request_count": "integer",
    "error_count": "integer",
    "success_rate": "float (0.0-1.0)"
  }
}
```

### Update Agent Status
```http
PATCH /agents/{agent_id}/status
Content-Type: application/json

{
  "status": "active|inactive|maintenance|error",
  "message": "string (optional)"
}
```

**Response:**
```json
{
  "success": "boolean",
  "message": "string",
  "agent_id": "string (UUID)",
  "previous_status": "string",
  "new_status": "string",
  "timestamp": "ISO 8601 datetime"
}
```

### Agent Heartbeat
```http
POST /agents/{agent_id}/heartbeat
```

**Response:**
```json
{
  "success": "boolean",
  "message": "string",
  "agent_id": "string (UUID)",
  "timestamp": "ISO 8601 datetime"
}
```

### Get Agent Metrics
```http
GET /agents/{agent_id}/metrics
```

**Response:**
```json
{
  "agent_id": "string (UUID)",
  "agent_type": "string",
  "metrics": {
    "request_count": "integer",
    "error_count": "integer",
    "success_rate": "float (0.0-1.0)",
    "avg_response_time": "float (seconds)",
    "p95_response_time": "float (seconds)",
    "p99_response_time": "float (seconds)",
    "throughput": "float (requests/second)",
    "resource_usage": {
      "cpu_percent": "float",
      "memory_mb": "float",
      "disk_io": "float"
    }
  },
  "timestamp": "ISO 8601 datetime"
}
```

## Learning & Memory Endpoints

### Get Learning History
```http
GET /learning-history
```

**Response:**
```json
{
  "lessons": [
    {
      "lesson_id": "string (UUID)",
      "content_hash": "string (SHA-256)",
      "content": "string",
      "relevance_score": "float (0.0-1.0)",
      "source_query": "string (original query that generated this lesson)",
      "agent_type": "string",
      "agent_id": "string (UUID)",
      "created_at": "ISO 8601 datetime",
      "metadata": {
        // Additional lesson metadata
      }
    }
  ],
  "pagination": {
    "total": "integer",
    "page": "integer",
    "per_page": "integer",
    "pages": "integer"
  }
}
```

**Query Parameters:**
- `agent_type`: Filter by agent type that generated the lesson
- `min_relevance`: Minimum relevance score (0.0-1.0)
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50)
- `sort_by`: Field to sort by (default: created_at)
- `sort_order`: asc|desc (default: desc)

### Get Specific Lesson
```http
GET /learning-history/{lesson_id}
```

**Response:**
```json
{
  "lesson_id": "string (UUID)",
  "content_hash": "string (SHA-256)",
  "content": "string",
  "relevance_score": "float (0.0-1.0)",
  "source_query": "string",
  "agent_type": "string",
  "agent_id": "string (UUID)",
  "created_at": "ISO 8601 datetime",
  "metadata": {
    // Additional lesson metadata
  },
  "usage": {
    "times_applied": "integer",
    "last_applied": "ISO 8601 datetime (optional)",
    "queries_improved": ["string"] (optional)
  }
}
```

### Search Learning History
```http
POST /learning-history/search
Content-Type: application/json

{
  "query": "string (required)",
  "options": {
    "limit": "integer (default: 10)",
    "similarity_threshold": "float (default: 0.7)",
    "agent_type": "string (optional)",
    "min_relevance": "float (default: 0.0)"
  }
}
```

**Response:**
```json
{
  "query": "string",
  "results": [
    {
      "lesson_id": "string (UUID)",
      "content": "string",
      "similarity_score": "float (0.0-1.0)",
      "relevance_score": "float (0.0-1.0)",
      "combined_score": "float (0.0-1.0)",
      "agent_type": "string",
      "agent_id": "string (UUID)",
      "created_at": "ISO 8601 datetime"
    }
  ],
  "total_results": "integer",
  "search_time_ms": "integer"
}
```

## System Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "ISO 8601 datetime",
  "version": "string",
  "services": {
    "api": "healthy|degraded|unhealthy",
    "database": "healthy|degraded|unhealthy",
    "cache": "healthy|degraded|unhealthy",
    "ollama": "healthy|degraded|unhealthy",
    "agent_registry": "healthy|degraded|unhealthy"
  },
  "checks": [
    {
      "name": "string",
      "status": "passed|failed|warning",
      "message": "string (optional)",
      "response_time_ms": "integer (optional)"
    }
  ]
}
```

### System Metrics (Prometheus Format)
```http
GET /metrics
```

**Response:** Prometheus exposition format text/plain

### System Information
```http
GET /info
```

**Response:**
```json
{
  "name": "Deep Research Agent (REX)",
  "version": "string (semver)",
  "build": {
    "timestamp": "ISO 8601 datetime",
    "commit": "string (git hash)",
    "branch": "string"
  },
  "environment": "development|staging|production",
  "features": {
    "agent_registry": "boolean",
    "distributed_tracing": "boolean",
    "metrics_enabled": "boolean",
    "rate_limiting": "boolean",
    "authentication_required": "boolean"
  },
  "limits": {
    "max_concurrent_research_jobs": "integer",
    "max_agents_per_type": "integer",
    "default_timeout_seconds": "integer",
    "max_query_length": "integer"
  },
  "links": {
    "documentation": "string (URL)",
    "repository": "string (URL)",
    "changelog": "string (URL)"
  }
}
```

## Internal Agent Communication Protocol

### Message Format
All agent-to-agent communication uses this JSON format:
```json
{
  "message_id": "string (UUID)",
  "correlation_id": "string (UUID)",
  "timestamp": "ISO 8601 datetime",
  "sender": {
    "agent_id": "string (UUID)",
    "agent_type": "string"
  },
  "recipient": {
    "agent_id": "string (UUID) (optional for broadcast)",
    "agent_type": "string (optional for broadcast)"
  },
  "message_type": "string",
  "payload": {
    // Message-type specific data
  },
  "metadata": {
    "priority": "low|normal|high|critical",
    "timeout_seconds": "integer",
    "retry_count": "integer",
    "routing_key": "string (optional)"
  }
}
```

### Message Types

#### Research Task Assignment
```json
{
  "message_type": "RESEARCH_TASK_ASSIGN",
  "payload": {
    "job_id": "string (UUID)",
    "task_type": "planner|searcher|filter|synthesis|gap_detector|citation_mapper|report_generator|evaluator",
    "input_data": {
      // Task-specific input
    },
    "deadline": "ISO 8601 datetime (optional)"
  }
}
```

#### Research Task Result
```json
{
  "message_type": "RESEARCH_TASK_RESULT",
  "payload": {
    "job_id": "string (UUID)",
    "task_type": "string",
    "result_data": {
      // Task-specific output
    },
    "success": "boolean",
    "error": {
      "code": "string (optional)",
      "message": "string (optional)"
    },
    "execution_time_ms": "integer",
    "resource_usage": {
      "tokens_used": "integer (optional)",
      "api_calls": "integer (optional)"
    }
  }
}
```

#### Knowledge Update
```json
{
  "message_type": "KNOWLEDGE_UPDATE",
  "payload": {
    "update_type": "lesson|fact|source|memory",
    "content": "string",
    "content_hash": "string (SHA-256)",
    "source": "string (optional)",
    "confidence": "float (0.0-1.0)",
    "tags": ["string"] (optional)
  }
}
```

#### Agent Status Update
```json
{
  "message_type": "AGENT_STATUS_UPDATE",
  "payload": {
    "status": "active|inactive|maintenance|error",
    "load": "float (0.0-1.0)",
    "health": {
      "status": "healthy|degraded|unhealthy",
      "details": "string (optional)"
    }
  }
}
```

#### Heartbeat
```json
{
  "message_type": "HEARTBEAT",
  "payload": {
    "timestamp": "ISO 8601 datetime",
    "sequence_number": "integer"
  }
}
```

### Communication Channels
1. **Direct Messaging:** Point-to-point via message queue (RabbitMQ/Kafka)
2. **Broadcast:** Publish-subscribe for system-wide notifications
3. **Request-Response:** Synchronous calls via HTTP/gRPC for immediate feedback
4. **Event Streaming:** Real-time updates via WebSocket or SSE for UI updates

## WebSocket Connection (Alternative to SSE)

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/research/{job_id}');
```

### Message Format
Same as internal agent communication protocol, but simplified for client use:
```json
{
  "type": "string",
  "data": {
    // Event-specific data
  },
  "timestamp": "ISO 8601 datetime"
}
```

### Message Types (Client-Facing)
- `node_transition`
- `thought_trace`
- `track_status`
- `sources_update`
- `completion`
- `error`
- `learning_event`

### Connection Events
- `onopen`: Connection established
- `onmessage`: Message received from server
- `onerror`: Connection error
- `onclose`: Connection closed

## Data Models

### Job Status Enum
- `pending`: Job queued, not yet started
- `processing`: Job actively being processed
- `completed`: Job finished successfully
- `failed`: Job encountered an error
- `cancelled`: Job was cancelled by user or system

### Agent Status Enum
- `active`: Agent is operational and accepting tasks
- `inactive`: Agent is temporarily disabled
- `maintenance`: Agent is undergoing maintenance
- `error`: Agent has encountered a persistent error

### Health Check Status Enum
- `healthy`: All checks passing
- `degraded`: Some checks warning, but service operational
- `unhealthy`: Critical checks failing, service degraded or down

### Priority Levels
- `low`: Background tasks, can be delayed
- `normal`: Standard priority
- `high`: Important tasks, should be processed promptly
- `critical`: System-critical tasks, must be processed immediately

## Pagination Format
For endpoints that support pagination:
```json
{
  "items": [
    // Array of items
  ],
  "pagination": {
    "total": "integer (total items)",
    "page": "integer (current page, 1-based)",
    "per_page": "integer (items per page)",
    "pages": "integer (total pages)",
    "has_next": "boolean",
    "has_previous": "boolean"
  }
}
```

## Filtering and Sorting
Common query parameters for list endpoints:
- `filters[field_name]=value`: Exact match filter
- `filters[field_name][min]=value`: Minimum value filter (numeric)
- `filters[field_name][max]=value`: Maximum value filter (numeric)
- `filters[field_name][in]=value1,value2,...`: In-list filter
- `sort_by=field_name`: Field to sort by
- `sort_order=asc|desc`: Sort order (default: asc)
- `search=term`: Full-text search across relevant fields

## HTTP Status Codes
- `200`: Success
- `201`: Created
- `202`: Accepted (async operation started)
- `204`: No Content
- `400`: Bad Request (validation error)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `405`: Method Not Allowed
- `409`: Conflict
- `422`: Unprocessable Entity
- `429`: Too Many Requests (rate limiting)
- `500`: Internal Server Error
- `502`: Bad Gateway
- `503`: Service Unavailable
- `504`: Gateway Timeout

## Versioning
API version is indicated in the URL path: `/api/v1/`
- Breaking changes increment the version number (v1 → v2)
- Non-breaking changes are added within the same version
- Deprecation notices are provided in API responses for upcoming removals

## SDK Examples

### JavaScript/TypeScript
```javascript
import { RexClient } from '@rex-agent/sdk';

const client = new RexClient({
  baseUrl: 'http://localhost:8000/api/v1',
  token: 'your-jwt-token' // Optional for local development
});

// Start research job
const job = await client.startResearch({
  query: "What are the latest advancements in quantum computing?",
  options: {
    max_depth: 3,
    tracks: 5,
    format: 'markdown'
  }
});

// Subscribe to progress updates
const subscription = client.subscribeToJob(job.job_id, (update) => {
  console.log(`Progress: ${update.progress.percentage}% - ${update.progress.message}`);
  
  if (update.status === 'completed') {
    console.log('Research completed!');
    console.log(report);
    subscription.unsubscribe();
  }
});

// Get final result
const result = await client.getJobResult(job.job_id);
console.log(result.report);

// Cancel job if needed
// await client.cancelJob(job.job_id);
```

### Python
```python
import rex_client

# Initialize client
client = rex_client.Client(
    base_url="http://localhost:8000/api/v1",
    token="your-jwt-token"
)

# Start research
job = client.start_research(
    query="What are the latest advancements in quantum computing?",
    options={
        "max_depth": 3,
        "tracks": 5,
        "format": "markdown"
    }
)

# Subscribe to updates
def progress_callback(update):
    print(f"Progress: {update.progress['percentage']}% - {update.progress['message']}")
    if update.status == "completed":
        print("Research completed!")
        print(update.result["report"])
        return False  # Stop subscription
    return True  # Continue subscription

client.subscribe_to_job(job.job_id, progress_callback)

# Get result
result = client.get_job_result(job.job_id)
print(result["report"])

# Cancel job
# client.cancel_job(job.job_id)
```

### cURL Examples
```bash
# Start research job
curl -X POST "http://localhost:8000/api/v1/research" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "query": "What are the latest advancements in quantum computing?",
    "options": {
      "max_depth": 3,
      "tracks": 5,
      "format": "markdown"
    }
  }'

# Get job status
curl -X GET "http://localhost:8000/api/v1/research/{job_id}" \
  -H "Authorization: Bearer your-jwt-token"

# Cancel job
curl -X POST "http://localhost:8000/api/v1/research/{job_id}/cancel" \
  -H "Authorization: Bearer your-jwt-token"

# Get metrics
curl -X GET "http://localhost:8000/api/v1/research/{job_id}/metrics" \
  -H "Authorization: Bearer your-jwt-token"
```

## Webhook Integration

### n8n Webhook Format
When n8n integration is enabled, the system sends webhooks to the configured URL with this format:

```http
POST https://your-n8n-instance.com/webhook/rex-research-completed
Content-Type: application/json

{
  "event": "research_completed",
  "timestamp": "ISO 8601 datetime",
  "job_id": "string (UUID)",
  "query": "string",
  "report": {
    "content": "string",
    "format": "markdown|html|json|pdf",
    "metrics": {
      // Same as completion event metrics
    }
  },
  "lessons_learned": [
    {
      "content": "string",
      "relevance_score": "float",
      "agent_type": "string"
    }
  ],
  "metadata": {
    // Additional metadata
  }
}
```

### Webhook Security
To secure webhooks, configure:
1. **Shared Secret:** Set `N8N_WEBHOOK_SECRET` environment variable
2. **Signature Verification:** The webhook includes an `X-Rex-Signature` header
3. **IP Whitelisting:** Limit incoming webhook calls to known IPs

Signature verification:
```
signature = HMAC-SHA256(secret, request_body)
Header: X-Rex-Signature: <signature>
```

## Change Log

### Version 2.1.0 (In Development)
- Added agent registry and orchestration capabilities
- Implemented bounded event queue with backpressure
- Enhanced SSE with explicit event types
- Added JWT authentication and rate limiting
- Implemented distributed tracing and Prometheus metrics
- Added Kubernetes deployment manifests
- Enhanced security with input validation and CORS refinement

### Version 2.0.0
- Initial public API release
- Core research functionality
- SSE-based real-time updates
- Basic agent management
- Learning history and vector memory
- Export capabilities (markdown, html, json, pdf)
- Health check and basic metrics

## Contact & Support
For API-related questions or issues:
- Documentation: https://docs.rex-agent.com
- Issues: https://github.com/rex-agent/rex-agent/issues
- Security: security@rex-agent.com
- General: support@rex-agent.com

## License
This API documentation is part of the Deep Research Agent (REX) project.
See the LICENSE file in the repository for licensing information.