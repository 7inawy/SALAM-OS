# Specifications · Engines · Graph Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Graph, Merchant, Organization, Relationship, Trust, Risk
Upstream engines: Evidence Engine, Knowledge Engine
Consumed by: Trust Engine, Risk Engine, Reasoning Engine, Decision Engine

## Purpose

The Graph Engine maintains the Commercial Graph — the indexed, queryable
network of all Merchants, Organizations, and Relationships in the system.
It keeps the Graph consistent with its source entities, exposes traversal
operations to downstream engines, and publishes structural change events.

The Graph Engine does not own commercial data. It indexes it. When a
Relationship is updated, the Graph Engine updates the corresponding edge.
When Trust or Risk scores are recomputed, Graph Engine updates node attributes.
Source entities remain authoritative.

## Responsibilities

1. **Maintain nodes** — add, update, and flag Merchant and Organization nodes.
2. **Maintain edges** — add, update, and terminate Relationship edges.
3. **Keep node attributes current** — sync Trust and Risk scores onto nodes.
4. **Serve traversal queries** — expose the six Kernel-defined graph operations.
5. **Publish structural events** — emit `graph.*` events on structural changes.
6. **Manage scope instances** — maintain separate Graph instances per scope
   (global, market, platform, segment) where configured.

## Trigger Events

| Event | Action |
|---|---|
| `merchant.created` | Add node to Graph. `node_type: merchant`. |
| `organization.created` | Add node to Graph. `node_type: organization`. |
| `merchant.suspended` / `organization.suspended` | Update node `status` and `flags`. Publish `graph.node_updated`. |
| `merchant.deregistered` / `organization.dissolved` | Update node `status`. Retain node — historical edges still matter. |
| `relationship.formed` | Add edge to Graph. |
| `relationship.strength_updated` | Update edge `weight`. |
| `relationship.terminated` | Set edge `status: terminated`, `weight: 0`. Retain edge. |
| `relationship.dormant` | Set edge `status: dormant`. Reduce weight proportionally. |
| `trust.recomputed` | Update `trust_score` on node. |
| `risk.recomputed` | Update `risk_score` on node. |
| `risk.escalated` | Update `risk_score` and add `escalated` to node `flags`. |

## Graph Operations (Implementation Contract)

The Kernel defines six required operations. This spec defines their interface:

### `neighbors(node_id, depth, filters?)`
Returns all nodes reachable from `node_id` within `depth` hops.

```
Input:
  node_id: uuid
  depth: integer (1–3, default 1)
  filters?: {
    relationship_types?: string[]
    min_edge_weight?: float
    node_status?: string[]
  }

Output:
  nodes: GraphNode[]
  edges: GraphEdge[]      ← edges traversed to reach each node
  hop_distances: {node_id: integer}
```

### `path(node_a, node_b, weight_mode?)`
Returns the shortest path between two nodes, weighted by edge weight.

```
Input:
  node_a: uuid
  node_b: uuid
  weight_mode?: "strength" | "trust" | "risk"   ← which edge attribute to optimize

Output:
  path: uuid[]            ← ordered node IDs from a to b
  edges: GraphEdge[]      ← edges in the path
  total_weight: float
  found: boolean
```

### `subgraph(node_ids[])`
Returns the induced subgraph for a set of nodes.

```
Input:
  node_ids: uuid[]

Output:
  nodes: GraphNode[]
  edges: GraphEdge[]      ← only edges where both endpoints are in node_ids
```

### `cluster(node_id)`
Returns the connected component (cluster) a node belongs to.

```
Input:
  node_id: uuid

Output:
  cluster_id: string      ← stable identifier for this connected component
  nodes: GraphNode[]
  edges: GraphEdge[]
  size: integer
```

### `risk_neighbors(node_id, severity_threshold?)`
Returns neighbors with elevated Risk scores — for contagion analysis.

```
Input:
  node_id: uuid
  severity_threshold?: "low" | "medium" | "high" | "critical" (default: "high")

Output:
  neighbors: {
    node: GraphNode,
    risk_score: float,
    severity: string,
    relationship_strength: float,
    hop_distance: integer
  }[]
```

### `trust_path(node_a, node_b)`
Returns the trust-weighted path between two nodes — for indirect trust inference.

```
Input:
  node_a: uuid
  node_b: uuid

Output:
  path: uuid[]
  path_trust_score: float   ← decayed trust along the path
  direct_relationship: boolean
  hop_count: integer
```

## Consistency Model

The Graph is **eventually consistent** with source entities.

- Target consistency lag: < 5 seconds from source event to Graph update (p95).
- During lag window, Graph may return stale Trust/Risk scores on nodes.
  Consumers must be aware of this and use `last_updated_at` on nodes for
  time-sensitive queries.
- If the Graph is unavailable, the Trust and Risk Engines fall back to
  direct entity queries (slower but always consistent).

## Scope Management

Multiple Graph instances are maintained per configured scope:

| Scope | When Created | Update Strategy |
|---|---|---|
| `global` | Always exists | Receives all events from all markets |
| `market` | Created when first Merchant/Org in that market appears | Receives events filtered by market |
| `platform` | Created when a platform integration is configured | Receives events filtered by platform_ref |

Queries to the Trust and Risk engines specify which scope to use. Default
is `global`. Market-scoped queries are faster and more relevant for
single-market Decisions.

## Output Events

| Event | Payload | Consumers |
|---|---|---|
| `graph.node_added` | `node_id`, `node_type`, `scope` | Trust Engine, Risk Engine, monitoring |
| `graph.node_updated` | `node_id`, changed fields | Trust Engine (network dim), Risk Engine (network dim) |
| `graph.edge_added` | `edge_id`, `party_a`, `party_b`, `relationship_type` | Trust Engine, Risk Engine, monitoring |
| `graph.edge_updated` | `edge_id`, `weight`, `status` | Trust Engine, Risk Engine |

## SLAs

| Operation | Target |
|---|---|
| Node add / update from trigger event | < 3s p95 |
| Edge add / update from trigger event | < 3s p95 |
| `neighbors()` query (depth 1) | < 100ms p99 |
| `neighbors()` query (depth 2) | < 500ms p99 |
| `neighbors()` query (depth 3) | < 2s p99 |
| `cluster()` query | < 1s p99 |
| `risk_neighbors()` query | < 500ms p99 |

## Open Questions (ADRs Required)

1. **Graph database technology** — the single most consequential Architecture
   decision for this engine. Candidates: Neo4j, Amazon Neptune, TigerGraph,
   or a purpose-built adjacency store. Must be decided before implementation.
2. **Scope isolation vs. shared store** — are market-scoped graphs separate
   databases or views over a global store? Architecture decision.
3. **Temporal queries** — can the Graph be queried as it existed at a prior
   timestamp? Required for historical Decision explainability. Significant
   storage and complexity implications. Needs ADR.
4. **Consistency lag SLA** — 5s p95 is a starting target. Actual achievable
   lag depends on graph database technology choice. Validate after ADR 1.

---
*This file is a Specification. It derives from and is constrained by the Kernel.*
