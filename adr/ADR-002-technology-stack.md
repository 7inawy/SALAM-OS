# ADR-002: Core Technology Stack

Date: 2025-06-30
Status: accepted
Supersedes: —
Superseded by: —
Layer: architecture
Decider: 7inawy (founder)

## Context

SALAM requires a technology stack capable of supporting:
- Event-driven, multi-engine architecture (Evidence, Knowledge, Graph,
  Trust, Risk, Reasoning, Decision engines)
- Immutable, append-only evidence storage with strict schema enforcement
- Native graph traversal for the Commercial Graph
- Statistical scoring and future ML model integration
- Financial-grade reliability for escrow fund release operations
- Long-term institutional software — not a rewrite every 2 years
- AWS MENA region (me-south-1) for proximity to Paymob/Fawry
  payment partners (per ADR-001)

## Decision

The following stack is adopted for all SALAM services:

| Concern | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| API framework | FastAPI | latest stable |
| Primary database | PostgreSQL | 16 (AWS RDS) |
| Graph database | Neo4j | AuraDB (managed) or self-hosted on EC2 |
| Event streaming | Redis Streams (now) → Kafka (at scale) | — |
| Cache | Redis | AWS ElastiCache |
| Infrastructure | AWS | me-south-1 (Bahrain) |
| Containers | Docker / AWS ECS Fargate | — |
| Raw payload storage | AWS S3 | — |
| Secrets management | AWS Secrets Manager | — |
| Repository structure | Monorepo | — |

## Alternatives Considered

### Language: Node.js
Strong async I/O performance. Rejected because SALAM's scoring engines,
reasoning layer, and eventual ML integration are data-heavy operations
where Python's ecosystem (NumPy, pandas, scikit-learn, PyTorch) has no
equivalent. Switching languages mid-project as ML requirements emerge
is a worse trade-off than Python's marginally lower raw I/O throughput.

### Language: Go
Excellent performance and concurrency model. Rejected because Go's data
science and ML ecosystem is thin. SALAM will need ML-grade tooling for
Trust/Risk scoring refinement. Hiring data engineers in Egypt who know Go
is significantly harder than hiring Python engineers.

### Database: MongoDB
Document model is flexible. Rejected because SALAM spent significant effort
defining precise, validated schemas for every Kernel entity. Schema
flexibility is a liability here — we want the database to enforce the
schemas we defined, not allow drift. PostgreSQL's JSONB handles the
genuinely flexible fields (provenance chains, metadata) without sacrificing
schema integrity elsewhere.

### Graph on PostgreSQL (recursive CTEs)
Avoids a second database. Rejected because graph traversal operations
required by the Reasoning Engine (neighbors at depth N, cluster detection,
trust path) become unacceptably complex and slow as SQL recursive queries
at scale. Neo4j's Cypher maps directly onto the Graph Engine spec's
six required operations.

### Event Streaming: Kafka from day one
Kafka is the right long-term answer. Rejected for initial deployment because
it introduces significant operational complexity (ZooKeeper or KRaft,
partition management, consumer group coordination) before SALAM has any
transaction volume. Redis Streams handles the early load and the migration
to Kafka is a well-understood operation with no application logic changes —
only infrastructure changes.

### Infrastructure: GCP
Technically sound. Rejected because Paymob and Fawry (ADR-001 target
partners) operate on AWS in me-south-1. Same-region deployment minimizes
latency on the payment webhook → fund release pipeline, which is the
most latency-sensitive operation in the escrow product.

## Rationale

**Python + FastAPI:** The only stack where rule-based scoring today and
production ML tomorrow are handled by the same language, same team, and
same ecosystem. FastAPI provides the performance and API ergonomics
needed without sacrificing the data layer. Pydantic schema validation
in FastAPI maps directly onto the JSON Schemas defined in the Kernel.

**PostgreSQL:** Financial data requires ACID guarantees. Immutability
is enforced at the application layer (no DELETE, no UPDATE on immutable
fields). PostgreSQL's JSONB handles flexible fields without sacrificing
integrity on structured fields. Scales to hundreds of millions of rows
with proper indexing and read replicas — sufficient for Phase 5.

**Neo4j:** The Commercial Graph's six required operations (neighbors,
path, subgraph, cluster, risk_neighbors, trust_path) are native Cypher
queries. Attempting these as SQL joins produces unmaintainable code and
degrades to full table scans at graph scale. Neo4j AuraDB removes
operational overhead.

**Redis Streams → Kafka:** Redis Streams is operationally trivial and
handles SALAM's early event volume. The migration to Kafka is triggered
at ~50,000 events/day — at that point, Kafka's partition model, consumer
group management, and log compaction become necessary. The migration
requires no application logic changes, only infrastructure reconfiguration.

**AWS me-south-1:** Payment partner proximity, strongest compliance
posture for financial data in MENA, ECS Fargate for independent
per-service horizontal scaling as required by SALAM's architecture
principles.

**Monorepo:** All services share Kernel schemas and Pydantic models.
A monorepo enforces that no service can silently redefine a Kernel entity.
One CI pipeline. One place for shared types. Microservices in separate
repos at this stage creates coordination overhead with zero benefit.

## Consequences

### Positive
- Single language across all services — one hiring profile, one code
  review standard, one deployment pipeline.
- Pydantic models generated from Kernel JSON Schemas enforce schema
  consistency at runtime across all services.
- FastAPI's automatic OpenAPI documentation satisfies the API philosophy
  (§40 of SALAM_CONTEXT): APIs expose capabilities with stable, versioned,
  documented contracts.
- Neo4j AuraDB eliminates graph database operations overhead.
- AWS ECS Fargate enables per-service independent horizontal scaling
  with no server management.

### Negative / Trade-offs
- Two databases (PostgreSQL + Neo4j) require two operational concerns,
  two backup strategies, two monitoring setups.
- Redis Streams migration to Kafka at scale requires a planned migration
  sprint. If deferred past ~50k events/day it becomes painful.
- Python is slower than Go or Rust for pure computation. Acceptable
  given that SALAM's bottlenecks are I/O and graph traversal, not CPU.

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Redis Streams migration deferred too long | Medium | Hard trigger: 50k events/day. ADR-002a will be written at that point. |
| Neo4j AuraDB pricing at scale | Low | Self-hosted Neo4j on EC2 is a viable fallback with no application changes. |
| Python GIL limits concurrency under load | Low | FastAPI is async; GIL impact on async I/O workloads is minimal. CPU-bound scoring moves to worker processes (Celery/RQ). |

## Dependencies

- ADR-001 (licensed payment partner) determines AWS region selection.
  me-south-1 is the correct region given Paymob/Fawry infrastructure.
- All Kernel JSON Schemas must be converted to Pydantic models before
  any service is written. This is the first engineering task.

## Review Trigger

- Redis Streams → Kafka migration: at 50,000 events/day sustained.
- Language reconsideration: not triggered by performance alone; only
  if a Kernel-level capability cannot be implemented in Python.
- Database reconsideration: not before Phase 5 (multi-industry ecosystem).
