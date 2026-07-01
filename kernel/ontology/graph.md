# Kernel · Ontology · Graph

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Knowledge, Merchant, Organization, Relationship
Depended on by: Trust, Risk, Reasoning Engine, Decision, Commercial Intelligence

## Definition

The Commercial Graph is the indexed, queryable structure that organizes all
Merchants, Organizations, and Relationships into a navigable network. It is
not a separate data store — it is the runtime view of the Relationship layer,
maintained continuously as new Relationships are formed and updated.

The Graph is the system's model of the commercial world as a network. Where
Merchants and Organizations are nodes and Relationships are edges, the Graph
is the structure that makes the network traversable: who is connected to whom,
how strongly, through what type of relationship, and with what outcome history.

The Graph does not own data. Every node and edge it exposes is authoritative
in its source entity (Merchant, Organization, Relationship). The Graph is a
derived index — a lens, not a store. If the Graph and a source entity
disagree, the source entity is correct.

## Properties

A Graph object represents the current state of the commercial network for a
given scope (market, platform, or global).

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `graph_id` | UUID | yes | no | Canonical identifier for this Graph scope. |
| `scope` | GraphScope | yes | no | The boundary this Graph covers. |
| `node_count` | integer | yes | yes | Current number of nodes (Merchants + Organizations). |
| `edge_count` | integer | yes | yes | Current number of active Relationship edges. |
| `last_updated_at` | timestamp | yes | yes | When the Graph index was last updated. |
| `version` | integer | yes | yes | Monotonically increasing on every structural update. |

## Graph Nodes

Every Merchant and Organization with `status: active` or `status: inactive`
is a node in the Graph. Suspended and deregistered/dissolved entities remain
as nodes but are flagged — they are not removed, because their historical
connections still matter for Risk reasoning.

| Field | Type | Description |
|---|---|---|
| `node_id` | UUID | The `merchant_id` or `organization_id`. |
| `node_type` | enum | `merchant`, `organization`. |
| `identity_status` | enum | Carried from the source entity. |
| `status` | enum | Carried from the source entity. |
| `trust_score` | float [0,1] \| null | Current Trust score, if computed. |
| `risk_score` | float [0,1] \| null | Current Risk score, if computed. |
| `degree` | integer | Number of active Relationship edges connected to this node. |
| `flags` | string[] | Active flag types from the source entity. |

## Graph Edges

Every active Relationship with `status: active` is an edge. Dormant
Relationships are included with reduced weight. Terminated Relationships
are retained as historical edges with zero weight.

| Field | Type | Description |
|---|---|---|
| `edge_id` | UUID | The `relationship_id`. |
| `party_a` | UUID | Source node ID. |
| `party_b` | UUID | Target node ID. |
| `relationship_type` | string | Carried from Relationship. |
| `direction` | enum | Carried from Relationship. |
| `weight` | float [0,1] | The Relationship `strength`. Used for graph traversal and scoring. |
| `outcome_summary` | OutcomeSummaryRef | Reference to the Relationship's OutcomeSummary. |
| `status` | enum | Relationship status: `active`, `dormant`, `terminated`. |

## Graph Scope (`GraphScope`)

| Field | Type | Description |
|---|---|---|
| `scope_type` | enum | `global`, `market`, `platform`, `segment`. |
| `market` | string \| null | ISO 3166-1 alpha-2 if `scope_type: market`. |
| `platform_ref` | string \| null | Platform identifier if `scope_type: platform`. |
| `segment` | string \| null | Segment identifier if `scope_type: segment` (e.g. a merchant category). |

Multiple Graph instances may coexist for different scopes. A global Graph
covers all markets; a market-scoped Graph covers one country. The Reasoning
Engine chooses which scope to query based on the Decision context.

## Graph Operations (Kernel-level)

The Kernel defines the operations the Graph must support. Implementation is
an Architecture/Specification concern.

| Operation | Description |
|---|---|
| `neighbors(node_id, depth)` | Return all nodes reachable from a given node within N hops. |
| `path(node_a, node_b)` | Return shortest path(s) between two nodes, weighted by Relationship strength. |
| `subgraph(node_ids[])` | Return the induced subgraph for a set of nodes. |
| `cluster(node_id)` | Return the connected cluster a node belongs to. |
| `risk_neighbors(node_id)` | Return neighbors with elevated Risk scores — for contagion analysis. |
| `trust_path(node_a, node_b)` | Return the trust-weighted path between two nodes — for indirect trust inference. |

These operations are what the Reasoning Engine calls. They must be available;
how they are implemented (graph database, adjacency list, etc.) is an
Architecture layer decision.

## Consistency Rule

The Graph is eventually consistent with its source entities. It is updated
event-driven — when a Relationship is created, updated, or terminated, the
Graph index is updated accordingly. Between update events, the Graph may lag
the source entities by a bounded window (defined in the Architecture layer).

The Graph never overrides source entities. Read the source entity for
authoritative current state; query the Graph for network traversal and
aggregate analysis.

## Relationship to Other Kernel Entities

- **Merchant / Organization**: These are the nodes. The Graph does not own
  their data — it indexes it.
- **Relationship**: These are the edges. The Graph is the queryable index of
  all Relationships.
- **Evidence / Knowledge**: Not directly in the Graph, but Trust and Risk
  scores on nodes are derived from Evidence and Knowledge.
- **Trust / Risk**: Trust and Risk scores are properties of Graph nodes,
  updated as the underlying Evidence and Knowledge change.
- **Reasoning Engine**: The primary consumer of the Graph. It traverses the
  Graph to answer questions like "what is the indirect trust exposure of
  merchant X through their supplier network?"
- **Decision**: Decisions may trigger Graph updates (e.g. a suspension
  propagating to connected nodes as a risk signal).

## Explicit Non-Goals

The Graph is **not**:
- A data store — it is an index. Source entities are authoritative.
- A social graph — it models commercial relationships only.
- Static — it is continuously updated as Relationships change.
- A single global object — multiple scoped Graph instances coexist.

## Open Questions (tracked, not yet resolved)

1. **Graph database technology**: which graph database or engine backs the
   Graph index? Architecture layer decision. Needs an ADR.
2. **Consistency window**: what is the maximum acceptable lag between a
   Relationship update and its reflection in the Graph? Architecture concern.
   Needs an ADR.
3. **Graph scope isolation**: when a Decision is made in a market-scoped
   Graph, does it propagate to the global Graph automatically? Governance
   concern. Needs an ADR.
4. **Historical graph queries**: can the Reasoning Engine query the Graph
   as it existed at a prior point in time (temporal queries)? Architecture
   concern with significant implementation implications. Needs an ADR.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
