# Specifications · Engines · Reasoning Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Knowledge, Graph, Trust, Risk, Evidence, Merchant, Organization
Upstream engines: Knowledge Engine, Graph Engine, Trust Engine, Risk Engine
Consumed by: Decision Engine, products (advanced queries)

## Purpose

The Reasoning Engine sits between the Knowledge and Graph layers and the
Decision Engine. It handles queries that cannot be answered by a single
entity lookup — queries that require traversing the Graph, combining Knowledge
across multiple subjects, or producing inferences that span the network.

Where the Trust and Risk Engines score individual entities, the Reasoning
Engine answers network-level questions: What is the indirect exposure of
merchant A through their supply chain? Is there a cluster of merchants
exhibiting coordinated fraud patterns? What does merchant A's network say
about a counterparty they have never directly transacted with?

The Reasoning Engine does not produce Trust or Risk scores — those belong to
their dedicated engines. It produces **Intelligence Queries** — structured
answers to complex, multi-entity questions, with full evidential citation.

## Responsibilities

1. **Execute network queries** against the Commercial Graph on behalf of
   the Decision Engine and products.
2. **Produce indirect assessments** — infer properties about a subject
   from their network neighbors when direct Evidence is sparse.
3. **Detect patterns** — identify coordinated behaviors, anomalies, or
   emerging risk clusters across the graph.
4. **Compose multi-entity answers** — combine Knowledge and Trust/Risk
   objects from multiple entities into a coherent, cited response.
5. **Cache results** — reasoning queries can be expensive; results are
   cached with explicit TTLs and invalidated on relevant upstream events.

## Query Types

### Type 1 — Network Trust Inference
*"What can we infer about merchant X's trustworthiness from their network,
when X has sparse direct Evidence?"*

Used by the Trust Engine's `network` dimension, and directly by products
for new merchants with limited history.

**Input**: `subject_ref`, `depth` (1–3 hops), `context`

**Process**:
1. Call `Graph.neighbors(subject_ref, depth)`.
2. Retrieve Trust objects for each neighbor.
3. Weight each neighbor's Trust by `relationship_strength × hop_decay^hop_distance`.
4. Produce a weighted network trust score with full neighbor citation.

**Output**:
```json
{
  "query_type": "network_trust_inference",
  "subject_ref": { ... },
  "inferred_trust_signal": "float [0,1]",
  "confidence": "float",
  "data_points": [
    {
      "neighbor_ref": { ... },
      "neighbor_trust_score": "float",
      "relationship_strength": "float",
      "hop_distance": "integer",
      "contribution_weight": "float"
    }
  ],
  "computed_at": "ISO 8601 timestamp"
}
```

### Type 2 — Contagion Risk Analysis
*"If merchant X is high-risk or suspended, what is the blast radius across
the network?"*

Used by the Risk Engine's `network` dimension, governance, and products
considering exposure to a counterparty's supply chain.

**Input**: `source_ref`, `risk_threshold` (minimum risk score to propagate),
`depth`, `context`

**Process**:
1. Call `Graph.risk_neighbors(source_ref, severity_threshold)`.
2. For each neighbor, compute contagion exposure:
   `exposure = source_risk_score × relationship_strength × hop_decay^distance`.
3. Return ranked list of affected entities with their exposure scores.

**Output**:
```json
{
  "query_type": "contagion_risk_analysis",
  "source_ref": { ... },
  "source_risk_score": "float",
  "affected_entities": [
    {
      "entity_ref": { ... },
      "contagion_exposure": "float",
      "relationship_strength": "float",
      "hop_distance": "integer",
      "direct_relationship": "boolean"
    }
  ],
  "total_affected": "integer",
  "computed_at": "ISO 8601 timestamp"
}
```

### Type 3 — Counterparty Assessment
*"Merchant A wants to transact with merchant B, but B has no Trust/Risk
history with us. What can we infer about B from A's network and B's own
sparse Evidence?"*

Used by the Decision Engine for first-time counterparty transactions.

**Input**: `subject_ref` (merchant A), `counterparty_ref` (merchant B), `context`

**Process**:
1. Check if A and B are already connected in the Graph (direct relationship).
   If yes: return their Relationship's `outcome_summary` directly.
2. If no direct relationship: call `Graph.trust_path(A, B)`.
3. If a path exists: compute path-decayed trust signal.
4. If no path: return `no_network_signal` with B's direct Evidence/Trust only.
5. Combine network signal with B's own Trust (if it exists) weighted by
   relative confidence.

**Output**:
```json
{
  "query_type": "counterparty_assessment",
  "subject_ref": { ... },
  "counterparty_ref": { ... },
  "direct_relationship": "boolean",
  "direct_outcome_summary": { ... },
  "network_trust_signal": "float | null",
  "network_path": ["uuid", ...],
  "counterparty_direct_trust": "float | null",
  "composite_signal": "float",
  "confidence": "float",
  "recommendation": "proceed | proceed_with_caution | escalate | insufficient_data",
  "computed_at": "ISO 8601 timestamp"
}
```

### Type 4 — Cluster Fraud Detection
*"Are there clusters of merchants exhibiting coordinated suspicious behavior?"*

Background process — not triggered by a product request but by scheduled
analysis or by a `risk.flag_raised` event with type `abnormal_transaction_pattern`.

**Process**:
1. Identify all merchants with active `abnormal_transaction_pattern` flags
   within a rolling 30-day window.
2. For each flagged merchant, retrieve their cluster via `Graph.cluster()`.
3. Compute cluster-level statistics: what percentage of the cluster is flagged?
   What is the average time delta between flags?
4. If cluster fraud signal exceeds threshold: raise a `fraud_cluster_detected`
   event referencing all affected `merchant_id`s and the cluster ID.

**Output** (event payload):
```json
{
  "event": "fraud_cluster_detected",
  "cluster_id": "string",
  "affected_merchants": ["uuid", ...],
  "cluster_fraud_signal": "float",
  "flag_density": "float",
  "detection_window_days": "integer",
  "detected_at": "ISO 8601 timestamp"
}
```

### Type 5 — Supply Chain Exposure
*"What is merchant X's total exposure through their supplier network?"*

Used for credit eligibility decisions and large-value escrow releases.

**Input**: `subject_ref`, `depth`

**Process**:
1. Call `Graph.neighbors(subject_ref, depth, { relationship_types: ["supplier"] })`.
2. For each supplier node, retrieve Risk object.
3. Aggregate exposure: total transaction value flowing through each supplier
   × supplier risk score.
4. Return ranked exposure list with aggregate exposure score.

## Caching Policy

Reasoning queries are expensive. Results are cached with TTLs based on
query type:

| Query Type | Cache TTL | Invalidation Trigger |
|---|---|---|
| `network_trust_inference` | 1 hour | `trust.recomputed` for any node in the result set |
| `contagion_risk_analysis` | 30 minutes | `risk.recomputed` or `risk.escalated` for source or affected entities |
| `counterparty_assessment` | 2 hours | `relationship.formed` between subject and counterparty, or Trust/Risk recompute for either |
| `cluster_fraud_detection` | Not cached (background process) | — |
| `supply_chain_exposure` | 1 hour | `risk.recomputed` for any supplier node |

Cache is invalidated on the relevant upstream events listed above.
Stale cache entries are never served for `escalated` or `critical` severity
contexts — the engine always recomputes fresh for high-stakes Decisions.

## Output Events

| Event | Payload | Consumers |
|---|---|---|
| `fraud_cluster_detected` | Cluster ID, affected merchants, signal strength | Risk Engine (flag raising), governance queue, monitoring |
| `reasoning.query_completed` | Query type, subject, latency, cache_hit | Monitoring |

## SLAs

| Query Type | Target |
|---|---|
| `network_trust_inference` (cache hit) | < 50ms p99 |
| `network_trust_inference` (cache miss, depth 2) | < 1s p95 |
| `contagion_risk_analysis` (depth 2) | < 2s p95 |
| `counterparty_assessment` | < 1s p95 |
| `cluster_fraud_detection` (background) | Completes within 5 minutes of trigger |
| `supply_chain_exposure` (depth 2) | < 2s p95 |

## Failure Modes

| Failure | Behaviour |
|---|---|
| Graph Engine unavailable | Return cached result if available and TTL not expired. If no cache: return `insufficient_data` with `degraded_mode: true` flag. Never block the Decision Engine. |
| Trust/Risk Engine unavailable | Return network signals only, flag `partial_data: true`. |
| Cache unavailable | Recompute all queries fresh. Log cache unavailability. |
| Query timeout | Return best partial result available at timeout, flagged `partial: true`. |

## Open Questions (ADRs Required)

1. **Hop decay factor** — the per-hop trust/risk decay multiplier is used
   across multiple query types and must be consistent with the Trust and Risk
   Engine network dimension formulas. Single ADR should govern all three.
2. **Cluster fraud threshold** — what percentage of a cluster must be flagged,
   and within what time window, to trigger `fraud_cluster_detected`? Needs ADR.
3. **Cache technology** — Redis, Memcached, or in-process. Architecture
   decision with consistency implications.
4. **Background process scheduling** — cluster fraud detection runs on
   schedule or on trigger. Frequency and trigger conditions need ADR.
5. **Inference confidence floor** — what is the minimum confidence below
   which a Reasoning Engine result should not be used in a Decision?
   Needs ADR; currently left to the Decision Engine's judgment.

---
*This file is a Specification. It derives from and is constrained by the Kernel.*
