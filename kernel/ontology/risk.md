# Kernel · Ontology · Risk

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Knowledge, Merchant, Organization, Relationship, Graph, Trust
Depended on by: Decision, Commercial Intelligence, Reasoning Engine

## Definition

Risk is a computed, Evidence-backed assessment of the probability and severity
of adverse outcomes associated with a commercial interaction involving a
Merchant or Organization. It answers a single operational question: what is
the likelihood and potential impact of something going wrong in this context?

Risk is not the inverse of Trust. Trust measures reliability of the subject;
Risk measures exposure of the counterparty. A Merchant can be highly trusted
and simultaneously high-risk — for example, a trusted Merchant operating in a
volatile market, handling high-value goods, or connected to flagged entities
in their network. Both assessments are required for a complete Decision.

Risk is always prospective: it is an estimate of future harm, not a record of
past harm. Past adverse Events and Transactions are Evidence inputs into Risk,
but Risk itself is a forward-looking probability estimate.

Like Trust, Risk is context-dependent. The same Merchant may be low-risk for
a $50 domestic transaction and high-risk for a $50,000 cross-border one.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `risk_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `subject_ref` | EntityRef | yes | no | The Merchant or Organization being assessed. |
| `context` | RiskContext | yes | no | The operational context for which this Risk is valid. |
| `score` | float [0,1] | yes | yes (recalculable) | Composite Risk score. 0 = minimal risk, 1 = maximum risk. |
| `dimensions` | RiskDimensions | yes | yes (recalculable) | Scores across individual risk dimensions. |
| `severity` | enum | yes | yes (recalculable) | Derived from score: `low`, `medium`, `high`, `critical`. |
| `confidence` | float [0,1] | yes | yes (recalculable) | Confidence in the Risk score. Low = sparse data. |
| `evidence_weight` | EvidenceWeight | yes | yes (recalculable) | Summary of backing Evidence and Knowledge. |
| `flags` | RiskFlag[] | no | append-only | Active risk signals that contributed to or escalated this assessment. |
| `status` | enum | yes | yes (state machine) | `initializing`, `active`, `stale`, `escalated`, `resolved`. |
| `escalation_reason` | string \| null | no | yes (set once on escalation) | Required if `status: escalated`. |
| `valid_for` | ValidityWindow | yes | yes (recalculable) | Time window this score is considered current. |
| `computed_at` | timestamp | yes | yes | When this score was last computed. |
| `computed_by` | string | yes | yes | Engine version that produced this score. |
| `history` | RiskHistoryEntry[] | no | append-only | Log of prior scores — enables trend and velocity analysis. |
| `version` | integer | yes | no | Monotonically increasing per `risk_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Risk Dimensions (`RiskDimensions`)

Risk is a composite of six dimensions, each independently scored [0,1]:

| Dimension | What it measures |
|---|---|
| `identity` | Risk from uncertain or disputed identity. High when `identity_status` is `unverified` or `disputed`. |
| `behavioral` | Risk from adverse behavioral patterns: dispute history, defaults, inconsistent activity. |
| `financial` | Risk from financial exposure: transaction value relative to observed capacity, payment failure history. |
| `network` | Risk from the entity's commercial network: connections to suspended, flagged, or high-risk entities. Contagion risk. |
| `market` | Risk from the operating environment: market volatility, regulatory environment, conflict, infrastructure. |
| `concentration` | Risk from over-dependence: a single counterparty dominating transaction volume, a single market, a single product category. |

The composite `score` is a weighted combination of these six dimensions.
`severity` is a derived categorical label:
- `low`: score 0.0–0.25
- `medium`: score 0.25–0.50
- `high`: score 0.50–0.75
- `critical`: score 0.75–1.0

Exact dimension weights are a Specification-layer concern.

## Risk Context (`RiskContext`)

| Field | Type | Description |
|---|---|---|
| `transaction_value` | number \| null | Specific transaction value being evaluated, if known. |
| `transaction_value_band` | enum | `micro`, `small`, `medium`, `large` — same bands as Trust. |
| `market` | string | ISO 3166-1 alpha-2 country code. |
| `counterparty_ref` | UUID \| null | The specific counterparty in this transaction, if known. Risk may vary by who the entity is transacting with. |
| `product_type` | string \| null | Product or service category. |
| `payment_method` | string \| null | Payment method, if relevant. |

## Risk Flags (`RiskFlag`)

Risk Flags are specific, named signals that elevate Risk above what the
dimension model would produce alone. They are append-only.

| Field | Type | Description |
|---|---|---|
| `flag_id` | UUID | Unique flag identifier. |
| `flag_type` | string | e.g. `fraud_network_proximity`, `sanctions_list_match`, `high_dispute_velocity`, `identity_conflict`, `abnormal_transaction_pattern`. |
| `severity` | enum | `warning`, `high`, `critical`. |
| `raised_by` | string | Engine or governance actor. |
| `raised_at` | timestamp | When raised. |
| `evidence_ref` | UUID \| null | Supporting Evidence, if applicable. |
| `resolved_at` | timestamp \| null | When resolved. Null = active. |
| `resolution_note` | string \| null | How it was resolved. |

## Evidence Weight (`EvidenceWeight`)

Same structure as Trust — required for explainability:

| Field | Type | Description |
|---|---|---|
| `evidence_count` | integer | Total Evidence objects contributing to this score. |
| `knowledge_count` | integer | Total Knowledge objects contributing. |
| `oldest_evidence_at` | timestamp | Age of oldest Evidence in the assessment window. |
| `newest_evidence_at` | timestamp | Recency of most recent Evidence. |
| `primary_drivers` | Driver[] | Top N Evidence or Knowledge objects that most influenced the score. |

## Status State Machine

```
initializing → active → stale → active (re-evaluated)
                       → escalated → active (de-escalated)
                                   → resolved
             → resolved
```

- **initializing**: first computation in progress.
- **active**: current, available for Decision Engine.
- **stale**: evidence has aged; score requires recomputation.
- **escalated**: one or more `critical` Risk Flags are active; requires
  governance attention before the score can be used in a Decision.
- **resolved**: the risk has been formally resolved (e.g. a suspended entity
  reinstated with clean Evidence). Record retained.

## Relationship to Other Kernel Entities

- **Evidence**: All Risk scores are traceable to specific Evidence objects.
  Adverse Evidence (disputes, defaults, fraud reports) are the primary
  behavioral and financial dimension inputs.
- **Knowledge**: Aggregated behavioral and financial patterns (dispute rate,
  default history, transaction velocity anomalies) feed into dimension scoring.
- **Merchant / Organization**: Risk is computed *about* these entities.
  They reference their active Risk object via `risk_score_ref`.
- **Graph**: The `network` dimension is derived from Graph proximity to
  high-risk or flagged nodes. Risk is contagious — a Merchant's risk is
  partially a function of who they transact with.
- **Trust**: Trust and Risk are complementary. The Decision Engine uses both.
  High Trust does not offset high Risk; they address different questions.
- **Relationship**: Relationship outcome history (dispute rate, failure rate)
  feeds directly into the `behavioral` and `financial` dimensions.
- **Decision**: Every Decision that exposes the system to potential loss
  must reference the applicable Risk object and acknowledge its `severity`.

## Explicit Non-Goals

Risk is **not**:
- The inverse of Trust — they are independent assessments.
- A permanent label — Risk is continuously recomputed.
- A guarantee of loss — it is a probability estimate, not a certainty.
- Assertable without Evidence — every Risk score must be fully traceable.
- A single number — the dimension breakdown is as important as the composite
  score for Decision-making and explainability.

## Open Questions (tracked, not yet resolved)

1. **Dimension weighting formula**: exact weights for compositing six
   dimensions into a score — and whether weights vary by context — is a
   Specification layer concern. Needs an ADR.
2. **Network contagion depth**: how many hops into the Graph does the
   `network` dimension propagate? Same question as Trust's network dimension,
   but Risk contagion logic may differ. Needs an ADR.
3. **Market risk data source**: the `market` dimension requires external
   data (market volatility indices, regulatory environment scores). Who
   provides this, how often is it updated, and how is it represented as
   Evidence? Architecture concern. Needs an ADR.
4. **Escalation governance**: when `status: escalated`, who has authority
   to de-escalate and under what conditions? Governance layer concern.
   Needs an ADR.
5. **Risk vs. Trust conflict handling**: when Trust is high and Risk is
   critical (or vice versa), how does the Decision Engine resolve the
   conflict? Decision Engine / Specification concern. Needs an ADR.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
