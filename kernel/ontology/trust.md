# Kernel · Ontology · Trust

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Knowledge, Merchant, Organization, Relationship, Graph
Depended on by: Decision, Commercial Intelligence, Reasoning Engine

## Definition

Trust is a computed, Evidence-backed assessment of the reliability and
commercial integrity of a Merchant or Organization. It answers a single
operational question: to what degree can a counterparty depend on this
entity to fulfill its commercial obligations?

Trust is not a feeling, not a reputation score in the social sense, and not
a binary safe/unsafe verdict. It is a structured, multi-dimensional assessment
derived from the full weight of observed Evidence, Knowledge, and Relationship
history — continuously updated as new information arrives.

Trust is always relative to a context. A Merchant may be highly trusted for
small-value, same-day transactions and low-trust for large-value, cross-border
ones. The Trust object carries this context explicitly.

The core principle: *evidence precedes trust*. A Trust score without
traceable Evidence is inadmissible. Every Trust assessment must be fully
explainable back to the specific Evidence objects that produced it.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `trust_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `subject_ref` | EntityRef | yes | no | The Merchant or Organization being assessed. |
| `context` | TrustContext | yes | no | The operational context for which this Trust score is valid. |
| `score` | float [0,1] | yes | yes (recalculable) | Composite Trust score. 0 = no trust, 1 = full trust. |
| `dimensions` | TrustDimensions | yes | yes (recalculable) | Scores across the individual trust dimensions. |
| `confidence` | float [0,1] | yes | yes (recalculable) | Confidence in the Trust score itself, driven by Evidence volume and quality. Low confidence = sparse data. |
| `evidence_weight` | EvidenceWeight | yes | yes (recalculable) | Summary of the Evidence and Knowledge backing this score. |
| `status` | enum | yes | yes (state machine) | `initializing`, `active`, `stale`, `suspended`, `revoked`. |
| `suspension_reason` | string \| null | no | yes (set once on suspension) | Required if `status: suspended` or `status: revoked`. |
| `valid_for` | ValidityWindow | yes | yes (recalculable) | Time window this score is considered current. |
| `computed_at` | timestamp | yes | yes | When this score was last computed. |
| `computed_by` | string | yes | yes | Engine version that produced this score. |
| `history` | TrustHistoryEntry[] | no | append-only | Log of prior scores — enables trend analysis. |
| `version` | integer | yes | no | Monotonically increasing per `trust_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Trust Dimensions (`TrustDimensions`)

Trust is not a single signal. It is a composite of five dimensions, each
independently scored [0,1]:

| Dimension | What it measures |
|---|---|
| `identity` | How confidently has this entity's identity been verified? Driven by identity Evidence quality. |
| `fulfillment` | How reliably does this entity complete its commitments? Driven by Transaction completion rate. |
| `consistency` | How consistent is this entity's behavior over time? Detects irregular or erratic patterns. |
| `financial` | How sound is this entity's financial behavior? Driven by payment patterns, reversal rate, and dispute rate. |
| `network` | What does this entity's commercial network signal about their trustworthiness? Driven by Graph neighbors' Trust scores — indirect trust. |

The composite `score` is a weighted combination of these five dimensions.
Exact weights are a Specification-layer concern (flagged as open question).

## Trust Context (`TrustContext`)

Trust is always scoped. A Trust object without a context is meaningless.

| Field | Type | Description |
|---|---|---|
| `transaction_value_band` | enum | The value range for which this Trust is valid: `micro` (<$100), `small` ($100–$1k), `medium` ($1k–$10k), `large` (>$10k). |
| `market` | string | ISO 3166-1 alpha-2 country code. |
| `counterparty_type` | string \| null | If Trust is assessed for a specific counterparty type (e.g. `marketplace`, `bank`, `logistics_provider`), that type. Null = general. |
| `product_type` | string \| null | Product or service category, if relevant. |

A Merchant may have multiple Trust objects for different contexts.
The Decision Engine selects the appropriate one based on the transaction
being evaluated.

## Evidence Weight (`EvidenceWeight`)

Explains what drove the score — required for explainability.

| Field | Type | Description |
|---|---|---|
| `evidence_count` | integer | Total Evidence objects that contributed to this score. |
| `knowledge_count` | integer | Total Knowledge objects that contributed. |
| `oldest_evidence_at` | timestamp | Age of the oldest Evidence in the assessment window. |
| `newest_evidence_at` | timestamp | Recency of the most recent Evidence. |
| `primary_drivers` | Driver[] | Top N Evidence or Knowledge objects that most influenced the score, with their contribution weight. |

`primary_drivers` is what the explainability layer surfaces to operators and
counterparties: "this Trust score is primarily driven by X delivery completions,
Y payment records, and Z identity verifications."

## Status State Machine

```
initializing → active → stale → active (re-evaluated)
                       → suspended → active (suspension lifted)
                                   → revoked
             → revoked
```

- **initializing**: first computation in progress, not yet available.
- **active**: current, available for consumption by Decision Engine.
- **stale**: evidence has aged beyond the validity window; score requires recomputation before use.
- **suspended**: subject entity has been suspended; Trust is frozen pending resolution.
- **revoked**: Trust has been withdrawn due to fraud, governance decision, or irrecoverable evidence failure. Revocation is permanent — a new Trust object must be initialized.

## Validity Window (`ValidityWindow`)

| Field | Type | Description |
|---|---|---|
| `valid_from` | timestamp | When this score became current. |
| `valid_until` | timestamp \| null | When this score expires. Null = recomputed event-driven. |
| `decay_model` | enum | `none`, `linear`, `exponential`. How confidence degrades as evidence ages. |

## History (`TrustHistoryEntry`)

| Field | Type | Description |
|---|---|---|
| `score` | float [0,1] | Score at that point in time. |
| `dimensions` | TrustDimensions | Dimension breakdown at that point. |
| `computed_at` | timestamp | When this historical entry was recorded. |
| `trigger` | string | What caused recomputation: `new_evidence`, `evidence_decay`, `relationship_update`, `scheduled`, `manual`. |

History is append-only and retained indefinitely — it enables Trust trend
analysis and is required for regulatory explainability.

## Relationship to Other Kernel Entities

- **Evidence**: The ultimate source of all Trust scores. Every dimension is
  traceable to specific Evidence objects via `evidence_weight.primary_drivers`.
- **Knowledge**: Aggregated Knowledge about a subject's behavior (fulfillment
  patterns, financial history) is the primary input into dimension scoring.
- **Merchant / Organization**: Trust is computed *about* these entities.
  They reference their active Trust object via `trust_score_ref`.
- **Graph**: The `network` dimension of Trust is derived from the Commercial
  Graph — a Merchant's Trust is partially a function of their neighbors' Trust.
- **Relationship**: Relationship strength and outcome history feed directly
  into the `fulfillment` and `financial` dimensions.
- **Decision**: The Decision Engine consumes Trust scores (with context
  matching) as primary inputs. A Decision must cite the Trust object it used.
- **Risk**: Trust and Risk are computed independently and consumed together
  by the Decision Engine. They are complementary, not inverses — a Merchant
  can have high Trust and high Risk simultaneously (e.g. trusted but operating
  in a volatile market).

## Explicit Non-Goals

Trust is **not**:
- A binary verdict — it is a scored, multi-dimensional assessment.
- A permanent label — Trust is continuously recomputed as Evidence arrives.
- A social reputation score — it models commercial reliability only.
- An inverse of Risk — they are independent assessments. See Risk.
- Assertable without Evidence — a Trust score must be fully traceable.

## Open Questions (tracked, not yet resolved)

1. **Dimension weighting formula**: the exact weights for combining the five
   dimensions into the composite `score` — and whether weights vary by
   `context` — is a Specification layer concern. Needs an ADR.
2. **Network trust propagation depth**: how many hops into the Graph does the
   `network` dimension reach? Deeper propagation increases accuracy but
   increases computational cost. Architecture concern. Needs an ADR.
3. **Minimum evidence threshold**: what is the minimum Evidence volume below
   which a Trust score should not be issued (or should be issued with a
   `confidence` floor)? Specification concern. Needs an ADR.
4. **Multi-context Trust aggregation**: when a Decision context doesn't exactly
   match any existing Trust object's context, how is the nearest applicable
   Trust score selected or interpolated? Decision Engine concern. Needs an ADR.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
