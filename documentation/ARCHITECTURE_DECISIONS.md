# Deep Research Agent (REX) - Architecture Decision Records

## Overview
This document captures key architectural decisions made for the Deep Research Agent (REX) system, particularly focusing on the evolution from a 9-agent prototype to a production-ready 21-agent orchestration system. Each decision record follows the ADR (Architecture Decision Record) format: context, decision, consequences, and status.

## Table of Contents
1. [ADR-001: Agent Orchestration Approach](#adr-001-agent-orchestration-approach)
2. [ADR-002: Communication Protocols](#adr-002-communication-protocols)
3. [ADR-003: State Management Strategy](#adr-003-state-management-strategy)
4. [ADR-004: Security Model](#adr-004-security-model)
5. [ADR-005: Observability Framework](#adr-005-observability-framework)
6. [ADR-006: Deployment Architecture](#adr-006-deployment-architecture)
7. [ADR-007: Data Storage Strategy](#adr-007-data-storage-strategy)
8. [ADR-008: API Design Approach](#adr-008-api-design-approach)
9. [ADR-009: Testing Strategy](#adr-009-testing-strategy)
10. [ADR-010: Extensibility and Plugin System](#adr-010-extensibility-and-plugin-system)

---

### ADR-001: Agent Orchestration Approach
**Status**: Accepted  
**Date**: 2026-08-20  
**Context**: The original REX implementation used a fixed 9-agent LangGraph pipeline hardcoded in `backend/agents/graph.py`. To scale to 21 specialized agents with independent lifecycles, we needed a more flexible orchestration approach that could handle dynamic agent registration, load balancing, and failure recovery.

**Decision**: Implement a decentralized agent orchestration model using:
1. **Agent Registry Service**: Central service for agent discovery, registration, and health monitoring
2. **Dynamic Service Discovery**: Agents register themselves on startup and send periodic heartbeats
3. **Load Balancing**: Built-in load balancer with multiple strategies (round_robin, least_loaded, weighted)
4. **Message-Based Communication**: Asynchronous messaging via Redis Streams or RabbitMQ for agent-to-agent communication
5. **Circuit Breaker Pattern**: For handling unhealthy agents and preventing cascade failures
6. **Graceful Degradation**: System continues operating with reduced functionality when agents are unavailable

**Consequences**:
- **Positive**:
  - Enables horizontal scaling of agent types (e.g., 5 searcher agents instead of 1)
  - Allows independent versioning and deployment of agent types
  - Improves fault tolerance through health checking and failover
  - Enables A/B testing and canary deployments of agent implementations
  - Supports heterogeneous agent implementations (different languages/frameworks)
  - Facilitates maintenance windows without system downtime
- **Negative**:
  - Increased system complexity compared to monolithic LangGraph approach
  - Potential for eventual consistency issues in distributed state
  - Additional network overhead for agent communication
  - Need for sophisticated monitoring and debugging tools
  - More complex failure modes to consider and handle
- **Neutral**:
  - Requires investment in observability tooling (tracing, metrics, logging)
  - Necessitates robust testing strategies for distributed systems
  - Requires clear service contracts and versioning policies

**Alternatives Considered**:
1. **Extended LangGraph Pipeline**: Simply adding more nodes to the existing graph
   - Rejected because: Doesn't solve independent scaling, versioning, or deployment needs
2. **Centralized Orchestrator (Airflow/Prefect)**: Single orchestrator controlling all agents
   - Rejected because: Creates single point of failure and bottlenecks
3. **Pure Peer-to-Peer Mesh**: Agents discover and communicate directly
   - Rejected because: Doesn't provide central visibility, load balancing, or easy management
4. **Kubernetes Native Only**: Relying solely on K8s for orchestration
   - Rejected because: Doesn't provide application-level agent semantics and communication patterns

**Implementation Notes**:
- Agent Registry service implemented in `backend/services/agent_registry.py`
- Heartbeat mechanism with configurable timeout
- Load balancer supports pluggable strategies
- Agents self-register on startup via health check endpoint
- Unhealthy agents are automatically removed from load balancer pool
- Message queues use Redis Streams for simplicity and performance
- Circuit breaker implemented using `pybreaker` library

---

### ADR-002: Communication Protocols
**Status**: Accepted  
**Date**: 2026-08-21  
**Context**: The original REX system used four communication protocols: LangGraph state passing, internal event queue, Server-Sent Events (SSE), and HTTP REST API. For a 21-agent system, we needed to evaluate whether these protocols were sufficient or if new communication patterns were needed to handle increased complexity and scale.

**Decision**: Enhance and standardize communication protocols as follows:
1. **Internal Agent Communication**: 
   - Primary: Asynchronous messaging via Redis Streams with consumer groups
   - Secondary: gRPC for low-latency, strongly-typed synchronous calls
   - Tertiary: HTTP/REST for administrative operations and webhooks
2. **Agent-to-Frontend Communication**:
   - Primary: Server-Sent Events (SSE) with explicit event types for real-time updates
   - Secondary: WebSocket alternative for bidirectional communication (feature flagged)
   - Tertiary: Polling fallback for environments where SSE/WebSocket not supported
3. **External Communication**:
   - REST/JSON for public API
   - Webhooks for third-party integrations (n8n, CI/CD, etc.)
   - GraphQL option for flexible querying (feature flagged)
4. **Observability Communication**:
   - OpenTelemetry for distributed tracing
   - Prometheus exposition format for metrics
   - Structured JSON logging for log aggregation

**Consequences**:
- **Positive**:
  - Clear separation of concerns between different communication types
  - Improved performance through appropriate protocol selection
  - Better scalability with asynchronous messaging as primary pattern
  - Enhanced observability through standardized instrumentation
  - Flexibility to adapt protocols based on use case and environment
  - Backward compatibility maintained for existing integrations
- **Negative**:
  - Increased complexity in choosing and configuring appropriate protocols
  - Need for protocol translation layers in some cases
  - Potential for inconsistent implementation across agent types
  - Additional dependencies (Redis, gRPC, OpenTelemetry libraries)
  - More complex testing matrix due to multiple protocol combinations
- **Neutral**:
  - Requires documentation and training on when to use each protocol
  - Necessitates versioning and deprecation policies for protocols
  - Requires investment in protocol-specific tooling and expertise

**Alternatives Considered**:
1. **Uniform gRPC Everywhere**: Use gRPC for all internal and external communication
   - Rejected because: Overkill for simple request/response, poor browser support, complex setup
2. **Pure Event-Driven Architecture**: All communication via events/message queues
   - Rejected because: Poor fit for request/response patterns, increased latency for simple calls
3. **Service Mesh Only (Istio/Linkerd)**: Rely entirely on service mesh for communication
   - Rejected because: Doesn't eliminate need for application-level protocols, adds complexity
4. **GraphQL as Primary API**: Use GraphQL for all external and internal APIs
   - Rejected because: Over-engineering for many use cases, caching complexity, learning curve

**Implementation Notes**:
- Redis Streams implementation in `backend/services/message_bus.py`
- Consumer groups used for scalable message processing
- Dead letter queues for handling repeatedly failed messages
- Message serialization using JSON with schema validation
- gRPC service definitions in `backend/proto/` directory
- SSE implementation with explicit event types in `backend/agents/graph.py`
- WebSocket alternative in `backend/services/websocket_service.py`
- OpenTelemetry instrumentation in `backend/services/telemetry.py`
- Structured logging using `python-json-logger` library

---

### ADR-003: State Management Strategy
**Status**: Accepted  
**Date**: 2026-08-22  
**Context**: The original REX system used LangGraph's TypedDict state with `operator.add` for list fields, plus an internal event queue for SSE communication. For a 21-agent system with distributed agents, we needed a state management strategy that could handle distributed state, persistence, and consistency guarantees.

**Decision**: Implement a hierarchical state management approach:
1. **Workflow State**: Persistent storage of research job state using PostgreSQL
2. **Agent State**: Ephemeral in-memory state per agent instance with periodic snapshots
3. **Shared State**: Distributed caching using Redis for frequently accessed data
4. **Immutable Event Log**: Append-only log of all state changes for audit and replay
5. **Consistency Model**: Eventual consistency with conflict resolution strategies
6. **State Versioning**: Vector clocks or version vectors for detecting conflicts
7. **Snapshotting**: Periodic snapshots of state for faster recovery

**Consequences**:
- **Positive**:
  - Enables horizontal scaling and fault tolerance
  - Provides persistence for long-running workflows
  - Allows state recovery after agent failures
  - Supports audit trails and compliance requirements
  - Enables debugging through state replay
  - Separates concerns between workflow, agent, and shared state
- **Negative**:
  - Increased complexity in managing consistency boundaries
  - Potential for conflicts requiring resolution strategies
  - Additional storage overhead for event logging and snapshots
  - Need for sophisticated conflict detection and resolution
  - Possible performance impact from serialization and storage operations
- **Neutral**:
  - Requires careful design of state partitioning and sharding
  - Necessitates clear definitions of what belongs in each state layer
  - Requires investment in state management tooling and expertise
  - Necessitates monitoring of state growth and cleanup strategies

**Alternatives Considered**:
1. **Centralized State Store**: Single source of truth (e.g., Redis or database) for all state
   - Rejected because: Creates bottleneck and single point of failure
2. **Pure Event Sourcing**: Rebuild state entirely from event log on demand
   - Rejected because: Poor performance for frequent state access, complex snapshotting
3. **Shared Nothing Architecture**: No shared state between agents
   - Rejected because: Doesn't support cooperative workflows requiring shared context
4. **In-Memory Data Grid**: Use Hazelcast or similar for distributed state
   - Rejected because: Adds dependency, may not fit consistency requirements, operational overhead

**Implementation Notes**:
- Workflow state stored in PostgreSQL with JSONB columns for flexibility
- Agent state snapshots saved to Redis with TTL-based expiration
- Event log implemented using PostgreSQL with sequential IDs
- Conflict resolution uses "last write wins" with timestamps for most data
- Critical data uses application-specific conflict resolution (e.g., merging lessons learned)
- State versioning uses simple incrementing version numbers per entity
- Snapshotting occurs every 5 minutes or on significant state changes
- Garbage collection removes old snapshots and event logs based on retention policy
- State transfer between agents uses secure serialization with validation

---

### ADR-004: Security Model
**Status**: Accepted  
**Date**: 2026-08-23  
**Context**: The original REX system assumed a local-only deployment with no authentication or authorization. For a production 21-agent system that may be exposed to networks or used in multi-tenant environments, we needed a comprehensive security model addressing authentication, authorization, encryption, and auditability.

**Decision**: Implement a defense-in-depth security model with:
1. **Zero Trust Networking**: 
   - Mutual TLS (mTLS) for all service-to-service communication
   - Service mesh (Istio/Linkerd) for policy enforcement and traffic management
   - Network policies restricting communication to least privilege
2. **Strong Authentication**:
   - JWT-based authentication with short-lived access tokens (15-30 min)
   - Refresh token rotation with one-time use
   - Optional API key authentication for service-to-service communication
   - Multi-factor authentication (MFA) for administrative access
   - Integration with enterprise identity providers (LDAP, Active Directory, SAML, OIDC)
3. **Fine-Grained Authorization**:
   - Role-Based Access Control (RBAC) with predefined roles
   - Attribute-Based Access Control (ABAC) for dynamic policies
   - Resource-based permissions (read, write, execute, delete)
   - Policy as code using Open Policy Agent (OPA) or similar
4. **Data Protection**:
   - Encryption at rest using AES-256 for databases and storage
   - Encryption in transit using TLS 1.3 for all communication
   - Field-level encryption for sensitive data (PII, API keys, etc.)
   - Key management using HashiCorp Vault or cloud KMS
   - Data minimization and pseudonymization where appropriate
5. **Audit and Monitoring**:
   - Comprehensive audit logging of all security-relevant events
   - Immutable audit trail with cryptographic hashing
   - Real-time security monitoring and anomaly detection
   - Regular security scanning and penetration testing
   - Compliance reporting for standards like SOC 2, ISO 27001, GDPR
6. **Application Security**:
   - Input validation and sanitization at all trust boundaries
   - Output encoding to prevent injection attacks
   - Secure coding practices and regular code reviews
   - Dependency scanning and vulnerability management
   - Container image scanning and signed images
   - Runtime application self-protection (RASP) where appropriate

**Consequences**:
- **Positive**:
  - Significantly reduced attack surface and vulnerability exposure
  - Improved compliance with industry standards and regulations
  - Enhanced trust and security posture for enterprise customers
  - Better protection against both external and internal threats
  - Improved ability to detect and respond to security incidents
  - Foundation for secure multi-tenant deployment
- **Negative**:
  - Increased complexity in configuration, deployment, and operations
  - Performance overhead from encryption, authentication, and authorization checks
  - Potential for user experience impact from additional security steps
  - Need for specialized security expertise and tooling
  - Possible compatibility issues with legacy systems or integrations
  - Increased operational overhead for certificate and key management
- **Neutral**:
  - Requires investment in security training and awareness programs
  - Necessitates regular security assessments and penetration testing
  - Requires clear security policies and procedures
  - Necessitates incident response planning and testing
  - Requires investment in security monitoring and SIEM solutions

**Alternatives Considered**:
1. **Perimeter Security Only**: Rely on firewalls and network segmentation
   - Rejected because: Inadequate for cloud-native, microservices architectures; assumes trusted internal networks
2. **Authentication Only, No Authorization**: Identify users but don't enforce fine-grained permissions
   - Rejected because: Insufficient for multi-tenant or privileged access scenarios
3. **Security Through Obscurity**: Hope that complexity deters attackers
   - Rejected because: Fundamentally flawed approach that provides no real security
4. **Delegate Security to Cloud Provider**: Rely entirely on provider's security services
   - Rejected because: Creates vendor lock-in, doesn't cover application-level security, shared responsibility model

**Implementation Notes**:
- mTLS implemented using Istio service mesh in Kubernetes deployment
- JWT implementation using `PyJWT` library with HS256/RSA256 algorithms
- Refresh tokens stored in Redis with single-use constraint and expiration
- RBAC implemented with roles: admin, operator, analyst, viewer, service
- ABAC implemented using `python-abo` library for attribute-based decisions
- Audit logging using structured JSON logs with immutable storage via WORM
- Key management using HashiCorp Vault integration via `hvac` library
- Input validation using Pydantic models with custom validators
- Output escaping using Jinja2 autoescape and context-appropriate escaping
- Dependency scanning using `safety` and `bandit` in CI pipeline
- Container scanning using `Trivy` in build pipeline
- Image signing using `cosign` or `notary` for supply chain security

---

### ADR-005: Observability Framework
**Status**: Accepted  
**Date**: 2026-08-24  
**Context**: The original REX system provided basic observability through SSE telemetry and logging. For a 21-agent production system, we needed a comprehensive observability framework capable of providing insights into system behavior, performance, and health at scale.

**Decision**: Implement a four-pillar observability framework:
1. **Metrics**:
   - Prometheus-compatible exposition format
   - Automatic instrumentation of framework components (FastAPI, database clients, etc.)
   - Custom business metrics for key operations (job completion rates, agent utilization, etc.)
   - Resource utilization metrics (CPU, memory, disk, network, file descriptors)
   - Queue depth and processing time metrics
   - Error and exception metrics by type and component
   - SLA and SLI tracking (availability, latency, throughput, error rates)
2. **Distributed Tracing**:
   - OpenTelemetry instrumentation across all services
   - Automatic context propagation for HTTP/gRPC/Redis/RabbitMQ
   - Manual spans for complex operations and business logic
   - Baggage for carrying user/request context across service boundaries
   - Integration with Jaeger or Zipkin backend
   - Sampling strategies (adaptive, probabilistic, rate-limiting)
3. **Structured Logging**:
   - JSON-formatted logs for machine parsing
   - Standardized fields (timestamp, level, message, service, trace_id, span_id, etc.)
   - Correlation IDs for request tracing across services
   - Contextual logging with relevant operational data
   - Configurable log levels per component
   - Integration with ELK/EFK or similar log aggregation stack
4. **Health Checking**:
   - Liveness probes for container orchestration restart decisions
   - Readiness probes for traffic routing decisions
   - Startup probes for slow-starting applications
   - Deep health checks for dependency validation
   - Synthetic transaction monitoring for end-to-end validation
   - Canary analysis for safe deployment validation

**Consequences**:
- **Positive**:
  - Comprehensive visibility into system behavior and performance
  - Ability to detect issues before they impact users
  - Faster mean time to detect (MTTD) and mean time to resolve (MTTR)
  - Data-driven capacity planning and optimization
  - Improved understanding of system dependencies and interactions
  - Support for SLA monitoring and reporting
  - Enables experimentation and A/B testing with clear metrics
- **Negative**:
  - Increased complexity in instrumentation and configuration
  - Performance overhead from tracing, metrics collection, and logging
  - Storage costs for metrics, traces, and logs over time
  - Need for expertise in observability tooling and practices
  - Potential for information overload without proper filtering and alerting
  - Requires investment in observability infrastructure and maintenance
- **Neutral**:
  - Requires clear definition of what to measure and why
  - Necessitates establishment of baselines and normal operating ranges
  - Requires investment in dashboard creation and maintenance
  - Necessitates alerting policies and fatigue prevention strategies
  - Requires training for teams on interpreting observability data

**Alternatives Considered**:
1. **Logs-Only Observability**: Rely solely on structured logging for all observability needs
   - Rejected because: Poor for performance analysis, distributed tracing, and real-time alerting
2. **Metrics-Only Observability**: Rely solely on metrics for observability
   - Rejected because: Lacks context for debugging, unable to trace requests across services
3. **Tracing-Only Observability**: Rely solely on distributed tracing
   - Rejected because: Overwhelming volume of data, poor for aggregation and trend analysis
4. **Depend on Monitoring Platform**: Use proprietary monitoring solution (Datadog, New Relic, etc.)
   - Rejected because: Creates vendor lock-in, may not fit specific needs, ongoing licensing costs

**Implementation Notes**:
- Metrics collection using `prometheus_client` library with automatic Flask/FastAPI instrumentation
- Custom metrics defined in `backend/services/metrics.py` for business operations
- OpenTelemetry instrumentation in `backend/services/telemetry.py` with auto-instrumentation
- Tracing configuration uses Jaeger exporter with adaptive sampling
- Structured logging using `python-json-logger` with standardized fields
- Health check endpoints implemented in `backend/services/health.py`
- Liveness/readiness/startup probes configured in Kubernetes manifests
- Synthetic monitoring using scheduled jobs that perform end-to-end research queries
- Canary analysis using Flagger or similar for Kubernetes deployments
- Dashboard provisioning using Grafana's JSON model and Kubernetes ConfigMaps
- Alerting rules defined in Prometheus Alertmanager with multiple notification channels
- Log retention and indexing policies configured in Elasticsearch ILM
- Metrics retention and downsampling configured in Prometheus

---

### ADR-006: Deployment Architecture
**Status**: Accepted  
**Date**: 2026-08-25  
**Context**: The original REX system used a simple Docker Compose setup for local development. For a production 21-agent system, we needed a deployment architecture that could support high availability, scalability, and operational excellence across different environments (on-premises, cloud, hybrid).

**Decision**: Implement a cloud-native deployment architecture with:
1. **Containerization**: 
   - All services packaged as Docker images
   - Multi-stage builds for minimal image size
   - Base images hardened and regularly updated
   - Image scanning and signing for supply chain security
2. **Orchestration Platform**:
   - Primary: Kubernetes for production deployments
   - Secondary: Docker Compose for local development and testing
   - Tertiary: Docker Swarm or Nomad for specific use cases
3. **Infrastructure as Code**:
   - Terraform for provisioning underlying infrastructure
   - Helm charts for Kubernetes application deployment
   - Kustomize for environment-specific overlays
   - Version-controlled configuration files
4. **Service Mesh**:
   - Istio for traffic management, security, and observability
   - Mutual TLS encryption for service-to-service communication
   - Fine-grained traffic control and fault injection
   - Telemetry collection and policy enforcement
5. **Observability Stack**:
   - Prometheus + Grafana for metrics and dashboards
   - Jaeger or Zipkin for distributed tracing
   - ELK/EFK stack for log aggregation and analysis
   - Alertmanager for alert routing and suppression
6. **CI/CD Pipeline**:
   - GitHub Actions or GitLab CI for automated testing and deployment
   - Blue-green or canary deployment strategies
   - Automated rollback on health check failures
   - Environment promotion (dev → staging → prod)
   - Security scanning integrated into pipeline
7. **Disaster Recovery**:
   - Multi-region or multi-zone deployment for high availability
   - Automated backup and restore procedures
   - Failover mechanisms for critical services
   - Regular disaster recovery testing

**Consequences**:
- **Positive**:
  - High availability and fault tolerance through redundancy
  - Horizontal scalability to handle increased load
  - Consistent deployments across environments
  - Improved security through containerization and service mesh
  - Enhanced observability and debugging capabilities
  - Faster recovery from failures through automation
  - Reduced operational overhead through IaC and CI/CD
  - Vendor flexibility and avoidance of lock-in
- **Negative**:
  - Increased initial complexity in setup and configuration
  - Steeper learning curve for teams unfamiliar with cloud-native technologies
  - Potential for over-engineering simple use cases
  - Dependence on external services (cloud provider, Kubernetes distribution)
  - Need for investment in tooling, training, and expertise
  - Possible performance overhead from abstraction layers
- **Neutral**:
  - Requires clear definition of production vs non-production environments
  - Necessitates environment-specific configuration management
  - Requires investment in training and skill development
  - Necessitates clear ownership and responsibility definitions
  - Requires documentation of deployment procedures and runbooks
  - Necessitates regular review and update of infrastructure as code

**Alternatives Considered**:
1. **Platform-as-a-Service (PaaS)**: Deploy to Heroku, Google App Engine, or similar
   - Rejected because: Limited control over infrastructure, scaling constraints, vendor lock-in
2. **Virtual Machines**: Deploy to traditional VMs with configuration management
   - Rejected because: Less efficient resource utilization, slower provisioning, less cloud-native
3. **Bare Metal**: Deploy directly to physical servers
   - Rejected because: High operational overhead, poor scalability, limited elasticity
4. **Serverless Functions**: Use AWS Lambda, Azure Functions, or similar
   - Rejected because: Poor fit for long-running processes, cold start issues, vendor lock-in, debugging challenges
5. **Platform-Specific Kubernetes**: Use EKS, AKS, or GKE without cloud-agnostic approach
   - Rejected because: Creates vendor lock-in at infrastructure level, reduces portability

**Implementation Notes**:
- Dockerfiles use multi-stage builds with distroless or scratch bases where possible
- Base images updated regularly using Dependabot or similar
- Image scanning using Trivy in CI pipeline
- Image signing using cosign for supply chain security
- Helm charts use semantic versioning and follow chart best practices
- Kubernetes manifests follow Kubernetes API conventions and best practices
- Istio installed using official Helm charts with minimal profile for resource efficiency
- Terraform modules versioned and tested in isolation
- CI pipeline includes unit, integration, security, and performance tests
- Blue-green deployment implemented using Kubernetes services and ingress
- Canary deployment using Flagger or Istio traffic splitting
- Disaster recovery uses regional failover with active-passive or active-active setup
- Backup procedures include database dumps, snapshots, and configuration backups
- Regular chaos engineering experiments using LitmusChaos or similar

---

### ADR-007: Data Storage Strategy
**Status**: Accepted  
**Date**: 2026-08-26  
**Context**: The original REX system used a combination of in-memory state, file-based caching (`backend_cache.json`), and optional Supabase for vector storage. For a 21-agent system with persistence, scalability, and performance requirements, we needed a comprehensive data storage strategy.

**Decision**: Implement a polyglot persistence strategy with:
1. **Primary Relational Database**:
   - PostgreSQL 15+ for structured data, workflow state, and metadata
   - JSONB columns for flexible schema where needed
   - Proper indexing and partitioning for performance
   - Connection pooling using PgBouncer
   - Read replicas for scaling read-heavy workloads
   - Point-in-time recovery and logical backups
2. **Distributed Cache**:
   - Redis 7+ for caching, session storage, and ephemeral state
   - Redis Cluster for horizontal scaling and high availability
   - Appropriate eviction policies (LRU/LFU) based on data type
   - Cache warming strategies for predictable workloads
   - Persistence configured based on use case (RDB/AOF)
3. **Vector Database**:
   - Supabase (pgvector) or self-hosted pgvector for similarity search and storage
   - Proper indexing (IVFFlat, HNSW) for performance
   - Metadata filtering capabilities
   - Backup and restore procedures
   - Integration with embedding models for vector generation
4. **Object Storage**:
   - Amazon S3, Google Cloud Storage, or MinIO for blob storage
   - Storage of exports, uploads, and large binary objects
   - Lifecycle policies for automatic transitions and expiration
   - Versioning and replication for durability
   - Access control and encryption at rest
5. **Time-Series Database**:
   - Prometheus for metrics storage (already in observability stack)
   - Consider InfluxDB or TimescaleDB for application-specific time-series data
6. **Search Engine**:
   - Elasticsearch for log storage and search (already in observability stack)
   - Consider for application search if needed beyond current capabilities
7. **Graph Database**:
   - Neo4j or Amazon Neptune for relationship-intensive data (future consideration)
   - For knowledge graphs, social networks, or complex dependencies
8. **File System**:
   - Local storage for temporary files and scratch space
   - Network-attached storage (NAS) for shared file systems if needed
   - Proper cleanup and retention policies

**Consequences**:
- **Positive**:
  - Optimal storage solution for each data type and access pattern
  - Improved performance through appropriate technology selection
  - Better scalability through horizontal scaling options
  - Enhanced durability and availability through replication and backup
  - Improved cost efficiency through right-sizing storage solutions
  - Flexibility to evolve storage choices as requirements change
  - Support for various consistency models based on needs
- **Negative**:
  - Increased complexity in managing multiple storage systems
  - Potential for data silos and inconsistent views of data
  - Additional operational overhead for backup, maintenance, and monitoring
  - Need for expertise in multiple storage technologies
  - Possible licensing costs for commercial storage solutions
  - Increased complexity in data migration and integration
- **Neutral**:
  - Requires clear data ownership and stewardship definitions
  - Necessitates data governance policies and procedures
  - Requires investment in data modeling and schema design
  - Necessitates monitoring of storage growth and utilization
  - Necessitates planning for data archival and purging
  - Requires clear data retention and disposal policies

**Alternatives Considered**:
1. **Single Database for Everything**: Use PostgreSQL or MongoDB for all storage needs
   - Rejected because: Poor fit for caching, blobs, time-series, and search workloads
2. **Pure Cloud-Native Managed Services**: Use only managed services from cloud provider
   - Rejected because: Creates vendor lock-in, may not be cost-optimal, less control
3. **Everything in Memory/Distributed Cache**: Use Redis or similar for all storage
   - Rejected because: Poor durability, limited capacity, expensive for large datasets
4. **Event Sourcing with Materialized Views**: Rebuild state from event log with projections
   - Rejected because: Poor performance for frequent state access, complex implementation
5. **File System Hierarchy**: Use traditional file system with careful organization
   - Rejected because: Poor scalability, concurrency issues, limited performance for many workloads

**Implementation Notes**:
- PostgreSQL deployed using Bitnami Helm chart with replication and persistence
- Connection pooling using PgBouncer sidecar or separate deployment
- Indexing strategy includes primary keys, foreign keys, and application-specific indexes
- Partitioning implemented for large tables using declarative partitioning
- Redis deployed using Bitnami Redis chart with clustering and persistence
- Cache policies defined per use case (e.g., LRU for sessions, LFU for frequent data)
- Vector storage using Supabase pgvector with proper indexing and connection pooling
- Object storage using MinIO for self-hosted or cloud provider services
- Lifecycle policies configured for automatic transitions (hot/warm/cold) and expiration
- Encryption at rest enabled for all storage services where available
- Regular backup procedures implemented for all critical storage systems
- Backup validation performed regularly to ensure recoverability
- Storage utilization monitored with alerts for approaching capacity limits
- Data migration procedures documented for storage technology changes
- Data quality monitoring implemented to detect corruption or degradation

---

### ADR-008: API Design Approach
**Status**: Accepted  
**Date**: 2026-08-27  
**Context**: The original REX API evolved organically based on immediate needs. For a production 21-agent system serving multiple clients (web UI, mobile apps, third-party integrations, internal services), we needed a consistent, scalable, and maintainable API design approach.

**Decision**: Implement a design-first, contract-driven API approach with:
1. **API-First Design**:
   - Define API contracts using OpenAPI/Specification before implementation
   - Use contract testing to ensure implementation matches specification
   - Generate client SDKs and documentation from specifications
   - Version APIs explicitly in the URL path (`/api/v1/`, `/api/v2/`)
2. **RESTful Principles**:
   - Use standard HTTP methods (GET, POST, PUT, PATCH, DELETE)
   - Leverage HTTP status codes appropriately
   - Design resources around nouns, not verbs
   - Implement proper content negotiation (JSON as primary, others as needed)
   - Use HATEOAS principles where beneficial for discoverability
   - Implement idempotency where appropriate (PUT, DELETE, etc.)
3. **Resource-Oriented Design**:
   - Clear resource hierarchy (e.g., `/jobs/{job_id}/agents/{agent_type}/instances/{instance_id}`)
   - Consistent naming conventions (snake_case for paths, camelCase for JSON)
   - Proper use of query parameters for filtering, sorting, and pagination
   - Standardized error responses with machine-readable codes
   - Consistent timestamp formats (ISO 8601 UTC)
   - UUIDs for resource identifiers
4. **Security and Privacy**:
   - Authentication and authorization enforced at API gateway level
   - Input validation and sanitization for all parameters
   - Rate limiting and quotas to prevent abuse
   - Data minimization in responses (don't overshare)
   - Privacy considerations for personal data
   - Secure transmission via HTTPS only
5. **Evolvability and Compatibility**:
   - Backward compatibility maintained within major versions
   - Clear deprecation policy with sunset dates
   - Non-breaking changes additive only within version
   - Breaking changes only between major versions
   - Feature flags for risky or experimental changes
6. **Developer Experience**:
   - Comprehensive, interactive documentation (Swagger UI/Redoc)
   - Client SDKs generated for popular languages (JavaScript/TS, Python, Go, Java)
   - Mock servers for frontend development and testing
   - Example code and tutorials in documentation
   - Error messages that are helpful and actionable
   - Support for common HTTP features (caching, compression, etc.)

**Consequences**:
- **Positive**:
  - Consistent, predictable API behavior across versions and implementations
  - Improved developer experience and reduced integration time
  - Better documentation and self-service capabilities
  - Enhanced reliability through contract testing and validation
  - Easier evolution and versioning of APIs over time
  - Improved security through standardized practices
  - Better support for monitoring, analytics, and usage analytics
  - Enables third-party ecosystem and integrations
- **Negative**:
  - Initial overhead in defining specifications and contracts
  - Potential for over-engineering simple endpoints
  - Need for investment in tooling for SDK generation and documentation
  - Possible tension between ideal design and practical constraints
  - Requires discipline to maintain consistency as system grows
  - Need for processes to handle specification changes and versioning
- **Neutral**:
  - Requires clear API ownership and governance processes
  - Necestitates investment in API management tooling (if used)
  - Requires regular review of API usage and performance
  - Necessitates deprecation and sunset procedures for old versions
  - Requires documentation of known issues and limitations
  - Necessitates handling of edge cases and edgy scenarios in specification

**Alternatives Considered**:
1. **Code-First Approach**: Define API through implementation and extract documentation
   - Rejected because: Leads to inconsistent APIs, poor documentation, difficult evolution
2. **Pure GraphQL API**: Use GraphQL as the sole API interface
   - Rejected because: Overkill for many use cases, caching complexity, learning curve
   - Also rejected because: Poor fit for file uploads, streaming, and some operational APIs
3. **RPC-Style API**: Use gRPC or similar for all communication
   - Rejected because: Poor browser support, complex setup, not ideal for public APIs
4. **Hypermedia-Driven API**: Strict adherence to HATEOAS principles
   - Rejected because: Adds complexity without proportional benefit for many use cases
   - Also rejected because: Poor tool support and client library availability
5. **Vendor-Specific API**: Tailor API to specific known clients only
   - Rejected because: Limits reusability, creates tight coupling, poor for ecosystem growth

**Implementation Notes**:
- OpenAPI 3.0 specifications in `docs/openapi/` directory
- Specification-driven development using tools like `openapi-generator`
- Contract testing using `pact` or `dredd` to validate implementation
- SDK generation for JavaScript/TypeScript, Python, and Go
- Documentation hosted using Redoc or Swagger UI
- API versioning in URL path with `/api/v1/` prefix
- Resource naming follows REST conventions (plural nouns, hyphenated for multi-word)
- HTTP status codes used according to RFC 7231 and WebDAV extensions
- Error responses follow RFC 7807 Problem Details for HTTP APIs
- Timestamp format is ISO 8601 UTC with timezone indicator
- UUIDs generated using UUID version 4 (random) for public identifiers
- Pagination uses limit/offset with standardized response format
- Filtering uses standardized query parameter syntax
- Sorting uses `sort_by` and `sort_order` parameters
- Search uses `q` parameter for full-text search across relevant fields
- Rate limiting implemented using `slowapi` or similar with Redis backend
- Authentication using JWT with HS256 algorithm and refresh token rotation
- Authorization using RBAC with roles defined in OpenAPI security schemes
- Content negotiation supports JSON as primary, with CSV and XML options for exports
- Compression supported via gzip for appropriate content types
- Caching headers provided where appropriate (ETag, Last-Modified, Cache-Control)
- API gateway (Kong, Traefik, or similar) handles cross-cutting concerns
- Webhook delivery with retry mechanisms and idempotency keys
- Deprecation warnings included in API responses for deprecated endpoints
- Sunset dates provided for deprecated endpoints in roadmap documentation
- API consortium or working group for governance of public APIs

---

### ADR-009: Testing Strategy
**Status**: Accepted  
**Date**: 2026-08-28  
**Context**: The original REX system had limited automated testing, relying mostly on manual verification. For a production 21-agent system where reliability, security, and performance are critical, we needed a comprehensive testing strategy that could provide confidence in the system's correctness and readiness for production.

**Decision**: Implement a comprehensive testing strategy based on the testing pyramid:
1. **Unit Tests** (70% of tests):
   - Target: Individual functions, classes, and components
   - Tools: pytest (Python), Jest (JavaScript/TS), JUnit (Java)
   - Coverage goal: >90% for critical components
   - Isolation: Mock external dependencies (databases, APIs, services)
   - Speed: Fast execution (seconds to minutes)
   - Frequency: Run on every commit, pre-merge
2. **Integration Tests** (20% of tests):
   - Target: Service interactions, API endpoints, database interactions
   - Tools: pytest, requests, Testcontainers, Docker Compose
   - Scope: Vertical slicing through multiple layers
   - External dependencies: Use test doubles or test containers
   - Speed: Moderate execution (minutes to tens of minutes)
   - Frequency: Run on push to main/staging branches, nightly
3. **End-to-End Tests** (10% of tests):
   - Target: Complete user workflows and system behaviors
   - Tools: pytest, Playwright, Cypress, Selenium
   - Environment: Production-like staging environment
   - Scope: Horizontal slicing across multiple services and systems
   - Speed: Slow execution (tens of minutes to hours)
   - Frequency: Run nightly, pre-release, weekly in staging
4. **Performance Tests**:
   - Target: Load, stress, scalability, and endurance
   - Tools: locust, k6, JMeter, Gatling
   - Metrics: Response time, throughput, resource utilization, error rates
   - Frequency: Weekly, pre-release, before major scaling events
5. **Security Tests**:
   - Target: Vulnerabilities, compliance, and threat resistance
   - Tools: OWASP ZAP, Bandit, Trivy, Snyk, Nessus
   - Scope: SAST, DAST, dependency scanning, configuration analysis
   - Frequency: Weekly, pre-release, after dependency updates
6. **Chaos Engineering Tests**:
   - Target: System resilience and failure handling
   - Tools: LitmusChaos, Gremlin, Chaos Mesh
   - Experiments: Network partitions, pod failures, resource exhaustion, latency injection
   - Frequency: Bi-weekly, monthly in production-like environments
7. **Acceptance Tests**:
   - Target: Business requirements and user satisfaction
   - Tools: Cucumber, Robot Framework, Gherkin
   - Stakeholders: Product, UX, QA, business representatives
   - Frequency: Pre-release, after significant feature changes

**Consequences**:
- **Positive**:
  - High confidence in system correctness and reliability
  - Early detection of defects and regressions
  - Improved code quality and maintainability
  - Better estimation of release readiness and risk
  - Enhanced security posture through proactive vulnerability detection
  - Improved performance through systematic testing and optimization
  - Increased ability to make changes with confidence
  - Better alignment between technical implementation and business needs
- **Negative**:
  - Increased time and resource investment in testing activities
  - Potential for testing to become a bottleneck in delivery process
  - Need for investment in test infrastructure and maintenance
  - Possible test fragility and maintenance overhead
  - Risk of false sense of security if testing is not comprehensive
  - Requires cultural shift to value testing as integral to development
- **Neutral**:
  - Requires clear definition of what constitutes a "unit", "integration", and "e2e" test
  - Necessitates investment in test data management and generation
  - Requires regular review and update of test suites
  - Necessitates handling of flaky tests and test instability
  - Requires balancing of test coverage with test usefulness and relevance
  - Necessitates investment in test environment provisioning and teardown

**Alternatives Considered**:
1. **Testing Ice Cone**: More emphasis on UI and E2E tests than unit tests
   - Rejected because: Poor fault isolation, slow feedback, high maintenance cost
2. **Testing Trophy**: More emphasis on integration tests than unit tests
   - Rejected because: Still lacks sufficient unit test coverage for confidence
3. **No Automated Testing**: Rely entirely on manual testing and QA
   - Rejected because: Doesn't scale, inconsistent, prone to human error, slow feedback
4. **Testing Based Solely on Code Coverage**: Aim for high percentage without regard to test quality
   - Rejected because: Can lead to meaningless tests that don't actually validate behavior
5. **Testing Only What's Easy to Test**: Avoid complex or difficult-to-test scenarios
   - Rejected because: Leaves critical paths untested, increases production risk

**Implementation Notes**:
- Unit test structure mirrors source code structure in `tests/unit/` directory
- Integration tests in `tests/integration/` with markers for external dependencies
- End-to-end tests in `tests/e2e/` using Playwright for browser automation
- Performance tests in `tests/performance/` using locust for load testing
- Security tests in `tests/security/` using Bandit for SAST and OWASP ZAP for DAST
- Chaos engineering experiments in `tests/chaos/` using LitmusChaos for K8s experiments
- Test data generation using factories (Factory Boy for Python, FakerJS for JS)
- Mocking framework: unittest.mock for Python, jest.mock for JavaScript/TS
- Test containers for databases and services: Testcontainers (Python/Java), dockertest (Go)
- CI pipeline runs unit tests on every commit
- Integration and e2e tests run on push to main/staging branches
- Nightly runs full test suite in staging environment
- Pre-release runs comprehensive test battery including performance and security
- Test coverage enforced with minimum thresholds (e.g., 90% for critical modules)
- Test flakiness detected and quarantined for investigation
- Test effectiveness measured using mutation testing (mutmut for Python)
- Test documentation includes purpose, scope, and assumptions for each test
- Test data isolation ensures tests don't interfere with each other
- Test environment parity aims to match production as closely as possible
- Test reporting includes JUnit XML, HTML reports, and coverage information
- Test retention and archiving policies for historical test data and reports

---

### ADR-010: Extensibility and Plugin System
**Status**: Accepted  
**Date**: 2026-08-29  
**Context**: The original REX system had limited extensibility, with functionality tightly coupled to the core implementation. For a production 21-agent system that needs to adapt to evolving requirements, support custom integrations, and enable third-party extensions, we needed a well-designed extensibility and plugin system.

**Decision**: Implement a layered extensibility approach with:
1. **Plugin Architecture**:
   - Well-defined plugin interfaces and contracts
   - Plugin discovery mechanism (automatic loading from designated directories)
   - Version compatibility checking between plugins and core
   - Dependency management for plugins
   - Isolation and sandboxing where appropriate
   - Hot reloading for development (disabled in production)
   - Plugin lifecycle management (load, initialize, start, stop, unload)
2. **Extension Points**:
   - Clearly documented and stable extension points in core system
   - Versioned extension point interfaces
   - Backward compatibility maintained for extension points
   - Clear deprecation policy for extension points
3. **Configuration-Driven Behavior**:
   - Feature flags for enabling/disabling functionality
   - Strategy patterns for swapping algorithms and implementations
   - Template method patterns for customizable workflows
   - Dependency injection for swapping implementations
   - External configuration for behavior customization
4. **API Extensibility**:
   - Webhooks for asynchronous notifications and integrations
   - Custom endpoints for extending API functionality
   - GraphQL schema stitching for combining schemas
   - API gateway plugins for cross-cutting concerns
   - WebSocket extensions for custom real-time communication
5. **Data Extensibility**:
   - Schema evolution strategies for databases
   - Extension tables or JSONB columns for flexible data
   - Custom data types and functions where supported
   - Migration scripts for schema changes
   - Data transformation pipelines for import/export
6. **UI Extensibility**:
   - Component libraries for building custom interfaces
   - Slot-based layout for inserting custom components
   - Themeability for visual customization
   - Custom views and dashboards
   - Plugin registration for UI components
7. **Scripting and Automation**:
   - Support for custom scripts (Python, JavaScript, Shell)
   - Hook system for executing code at specific lifecycle events
   - Template engine for generating documents and reports
   - Workflow engine for defining custom processes
   - Integration with automation platforms (Zapier, n8n, Microsoft Power Automate)

**Consequences**:
- **Positive**:
  - Enables adaptation to changing requirements without core modifications
  - Allows third-party developers to extend functionality safely
  - Reduces time-to-market for new features and integrations
  - Improves maintainability by separating core concerns from extensions
  - Enables A/B testing and experimentation through feature flags
  - Supports white-labeling and customization for different customers
  - Facilitates technology adoption through well-defined integration points
  - Encourages ecosystem growth and community contributions
- **Negative**:
  - Increased complexity in defining and maintaining extension points
  - Potential for plugin conflicts and compatibility issues
  - Risk of security vulnerabilities through poorly implemented plugins
  - Possible performance impact from abstraction layers and indirection
  - Need for investment in plugin management infrastructure and tooling
  - Requires discipline to maintain backward compatibility for extensions
  - Possible support complexity for wide variety of plugins and versions
- **Neutral**:
  - Requires clear documentation and examples for plugin development
  - Necessitates investment in plugin registry or marketplace (if desired)
  - Requires regular review and update of extension point interfaces
  - Necessitates handling of plugin lifecycle and dependency conflicts
  - Requires investment in testing strategies for plugins and extensions
  - Necessitates clear policies for plugin approval, rejection, and removal

**Alternatives Considered**:
1. **Monolithic Extension**: Allow direct modification of core source code
   - Rejected because: Uncontrolled, unsafe, unsupportable, violates encapsulation
2. **Pure Configuration Approach**: Extend solely through configuration files
   - Rejected because: Limited expressiveness, cannot add new behavior or logic
3. **Inversion of Control Container**: Heavy reliance on DI framework for everything
   - Rejected because: Over-engineering for simple cases, adds complexity and overhead
4. **Event-Driven Extensions Only**: All extensions via event subscription/publishing
   - Rejected because: Poor fit for synchronous operations, request/response patterns
5. **Platform-Specific Extensions**: Tie extensions to specific runtime or platform
   - Rejected because: Creates vendor lock-in, limits portability and flexibility
6. **No Extensibility**: Assume requirements are static and well-understood upfront
   - Rejected because: Unrealistic for software systems, prevents adaptation and growth

**Implementation Notes**:
- Plugin interface defined using abstract base classes in Python
- Plugin discovery uses entry points (`setuptools.entry_points`) or directory scanning
- Version compatibility checked using semantic versioning rules
- Plugin isolation uses separate Python namespaces or subprocesses where needed
- Hot reloading uses file system watchers (disabled in production for stability)
- Plugin lifecycle managed through explicit load/initialize/start/stop/unload methods
- Extension points documented in `docs/extension_points/` with version history
- Feature flags implemented using `launchdarkly` client or similar
- Strategy pattern used for swappable algorithms (search strategies, LLMs, etc.)
- Dependency injection using `dependency-injector` or similar framework
- External configuration supports JSON, YAML, and environment variables
- Webhooks implemented with retry mechanisms, idempotency keys, and delivery guarantees
- Custom endpoints registered through plugin system with proper validation
- GraphQL schema stitching using `graphql-tools` or similar
- API gateway plugins implemented using Kong plugins or similar
- UI components built using React with proper prop types and documentation
- Component library published as npm package for sharing
- Theming supported using CSS variables and theme context
- Custom views implemented as React routes with proper authentication
- Plugin registration UI for administrators to manage installed plugins
- Scripting support allows Python and JavaScript scripts with sandboxing
- Hook system uses decorator pattern for lifecycle events (before_start, after_stop, etc.)
- Template engine uses Jinja2 for document and report generation
- Workflow engine uses Camunda or similar for defining and executing processes
- Integration with n8n, Zapier, and Power Automate through webhooks and APIs
- Plugin registry implemented as optional service for discovering and installing plugins
- Security scanning of plugins using same tools as core (Bandit, Trivy, etc.)
- Plugin signing and verification for supply chain security
- Clear policies for plugin approval based on functionality, security, and performance
- Deprecation warnings for extension points with clear migration paths
- Sunset dates for deprecated extension points in plugin compatibility matrix
- Plugin compatibility matrix tested against multiple versions of core system
- Regular plugin compatibility testing as part of release process