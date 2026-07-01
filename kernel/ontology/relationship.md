# Kernel · Ontology · Relationship

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Event, Transaction, Merchant, Organization
Depended on by: Commercial Graph, Trust, Risk, Knowledge

## Definition

A Relationship is a persistent, Evidence-backed commercial connection between
two entities (Merchants or Organizations) that has been observed across one or
more Events or Transactions. It is the system's model of ongoing commercial
bonds — not a one-time interaction, but a pattern of interaction that has
sufficient weight to be named and tracked.

Relationships are not asserted — they are derived. The system does not accept
"these two merchants have a relationship" as an input. A Relationship is
recognized when the weight of observed Events and Transactions between two
entities crosses a significance threshold. It is a conclusion, not a claim.

A Relationship is the edge primitive of the Commercial Graph. The Graph is
built from Relationships; Relationships are built from Events and Transactions.
A Relationship without at least one supporting Event is inadmissible.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `relationship_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `party_a` | EntityRef | yes | no | First entity in the relationship. |
| `party_b` | EntityRef | yes | no | Second entity in the relationship. The pair (party_a, party_b) is ordered by `entity_id` lexicographic sort — always smaller ID first — to prevent duplicate edges. |
| `relationship_type` | string | yes | yes | The nature of the connection. See Relationship Types below. |
| `direction` | enum | yes | yes | `unidirectional_a_to_b`, `unidirectional_b_to_a`, `bidirectional`. |
| `strength` | float [0,1] | yes | yes (recalculable) | Current strength of the relationship, derived from Event/Transaction volume, recency, and outcome quality. |
| `event_refs` | UUID[] | yes | append-only | Events that established or reinforce this Relationship. Minimum one. |
| `transaction_refs` | UUID[] | no | append-only | Transactions between these parties. |
| `evidence_refs` | UUID[] | no | append-only | Direct Evidence supporting the existence or nature of this Relationship. |
| `status` | enum | yes | yes (state machine) | `forming`, `active`, `dormant`, `terminated`. |
| `formed_at` | timestamp | yes | no | When this Relationship was first recognized by the system. |
| `last_interaction_at` | timestamp \| null | no | yes | Timestamp of the most recent Event or Transaction between these parties. |
| `interaction_count` | integer | yes | yes | Total count of Events and Transactions between these parties. Monotonically increasing. |
| `outcome_summary` | OutcomeSummary | yes | yes (recalculable) | Aggregate outcome statistics across all interactions. |
| `flags` | Flag[] | no | append-only | Compliance, fraud, or quality flags on this Relationship. |
| `version` | integer | yes | no | Monotonically increasing per `relationship_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Relationship Types

`relationship_type` is an open string extended at the Specification layer.
Core types at the Kernel level:

| Type | Description |
|---|---|
| `buyer_seller` | Recurring purchase relationship between buyer and seller. |
| `supplier` | Upstream supply relationship (B2B goods or materials). |
| `logistics_partner` | Logistics or delivery service relationship. |
| `financial_guarantor` | One party guarantees obligations of the other. |
| `platform_merchant` | Merchant operates through a platform/marketplace (Organization). |
| `co_ownership` | Two entities share ownership of a third or operate jointly. |
| `referral` | One party consistently refers business to the other. |
| `dispute_history` | Parties have a documented history of disputes. |

A single pair of entities may have multiple active Relationship objects of
different types (e.g. a `buyer_seller` and a `logistics_partner` between the
same two Merchants). Each is a distinct Relationship entity.

## Derivation Rule

A Relationship is derived, not asserted:

1. A first Event or Transaction between two entities does not create a
   Relationship automatically — it creates a candidate.
2. A Relationship is recognized when interaction count and/or Event significance
   crosses the threshold defined in the Relationship Recognition Specification
   (Specification layer concern).
3. Once recognized, the Relationship is backfilled with all prior Events and
   Transactions between the same pair.
4. Subsequent interactions append to `event_refs` / `transaction_refs` and
   update `strength`, `last_interaction_at`, and `outcome_summary`.

The exact recognition threshold is a Specification-layer concern (flagged as
an open question below).

## Deduplication Rule

To prevent duplicate edges in the Commercial Graph:

- `(party_a.entity_id, party_b.entity_id)` is a normalized pair: always
  ordered with the lexicographically smaller UUID first.
- `relationship_type` is part of the uniqueness key — two entities can have
  multiple Relationships of different types.
- Attempting to create a duplicate `(party_a, party_b, relationship_type)`
  Relationship must be rejected at the engine layer; the existing one is
  updated instead.

## Outcome Summary (`OutcomeSummary`)

| Field | Type | Description |
|---|---|---|
| `total_events` | integer | Total Events between these parties. |
| `total_transactions` | integer | Total Transactions between these parties. |
| `completed_transactions` | integer | Transactions with `status: completed`. |
| `failed_transactions` | integer | Transactions with `status: failed`. |
| `disputed_transactions` | integer | Transactions that entered `status: disputed`. |
| `completion_rate` | float [0,1] | `completed_transactions / total_transactions`. |
| `dispute_rate` | float [0,1] | `disputed_transactions / total_transactions`. |
| `total_value` | number \| null | Cumulative value of all Transactions (in a normalized currency, Specification concern). |
| `last_calculated_at` | timestamp | When this summary was last recomputed. |

## Status State Machine

```
forming → active → dormant → active (resumed)
                           → terminated
        → terminated
```

- **forming**: Relationship candidate recognized, not yet above recognition threshold.
- **active**: recognized Relationship, interactions are ongoing.
- **dormant**: no interactions above the recency threshold. Strength decays.
- **terminated**: Relationship has formally ended (e.g. a platform offboarding,
  a contract termination with supporting Evidence). Record retained.

## Relationship to Other Kernel Entities

- **Event / Transaction**: Events and Transactions are the raw material of
  Relationships. Every Relationship references the Events and Transactions that
  produced it via `event_refs` and `transaction_refs`.
- **Merchant / Organization**: Relationships connect exactly two entities,
  each of which is a Merchant or Organization.
- **Evidence**: Direct Evidence (e.g. a signed contract) can support a
  Relationship via `evidence_refs`, independent of Events.
- **Commercial Graph**: Relationships are the edges of the Commercial Graph.
  The Graph is the indexed, queryable structure built from Relationships;
  Relationship is the primitive.
- **Trust / Risk**: Relationship strength, completion rate, and dispute rate
  are direct inputs into Trust and Risk scoring for both parties.
- **Knowledge**: Relationship patterns (e.g. a Merchant's supplier network,
  a buyer's preferred sellers) are aggregated into Knowledge objects.

## Explicit Non-Goals

A Relationship is **not**:
- An assertion — it is derived from observed Events and Transactions.
- A social graph connection — it models commercial bonds, not personal ones.
- A contract — contracts may be Evidence that supports a Relationship, but
  the Relationship itself is the pattern of behavior, not the legal agreement.
- Bidirectional by default — direction is explicit (`direction` field) because
  commercial relationships are often asymmetric (e.g. buyer→seller).

## Open Questions (tracked, not yet resolved)

1. **Recognition threshold**: how many Events / what significance level is
   required to promote a candidate to a recognized Relationship? Specification
   layer concern. Needs an ADR.
2. **Strength decay function**: how fast does `strength` decay during dormancy,
   and what triggers the `dormant` transition? Specification layer concern.
   Needs an ADR.
3. **Cross-type relationship aggregation**: when a pair of entities has multiple
   Relationship types, how are their individual strengths aggregated for Trust
   and Risk input? Specification layer concern. Needs an ADR.
4. **Total value normalization**: `OutcomeSummary.total_value` requires a
   normalized currency. Which currency, and who controls the exchange rates
   used for normalization? Architecture / governance concern. Needs an ADR.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
