# Specifications · Engines · Trust Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Trust, Evidence, Knowledge, Merchant, Organization, Relationship, Graph
Upstream engines: Evidence Engine, Knowledge Engine, Graph Engine
Consumed by: Decision Engine, Reasoning Engine, products

## Purpose

The Trust Engine computes and maintains Trust assessments for every Merchant
and Organization in the system. It answers, continuously and in context:
to what degree can a counterparty depend on this entity to fulfill its
commercial obligations?

Trust scores are not computed once — they are living assessments that update
as new Evidence arrives, Knowledge changes, and the commercial network evolves.

## Responsibilities

1. **Initialize** Trust objects when a new Merchant or Organization is created
   and sufficient Evidence exists to begin scoring.
2. **Recompute** Trust scores when triggered by upstream events.
3. **Maintain context variants** — a Merchant may have multiple Trust objects
   for different contexts (`transaction_value_band` × `market`).
4. **Decay** Trust scores as Evidence ages, per the validity window.
5. **Suspend and revoke** Trust when the subject entity is suspended or when
   irrecoverable Evidence failures occur.
6. **Expose explainability** — every Trust object must carry `evidence_weight.
   primary_drivers` sufficient to explain the score.
7. **Publish events** for downstream consumers.

## Trigger Events

| Event | Action |
|---|---|
| `merchant.created` / `organization.created` | Evaluate whether sufficient Evidence exists to initialize Trust. If yes, initialize. If no, defer. |
| `evidence.validated` | Re-evaluate Trust for the Evidence subject across all relevant contexts. |
| `evidence.superseded` | Re-evaluate Trust objects that cited the superseded Evidence. |
| `knowledge.derived` / `knowledge.updated` | Re-evaluate Trust objects that consume this Knowledge type. |
| `knowledge.retracted` | Re-evaluate Trust objects citing the retracted Knowledge. |
| `relationship.strength_updated` | Re-evaluate the `network` dimension for all nodes connected to the updated edge. |
| `merchant.suspended` / `organization.suspended` | Set Trust `status: suspended`. Publish `trust.suspended`. |
| `scheduled.trust_decay_check` | Periodic sweep; decay confidence for aging Evidence windows. |

## Trust Initialization

Trust is initialized when the minimum Evidence threshold is met:

**Minimum threshold** (exact values are ADR-dependent):
- At least 1 validated Evidence object of any `claim_type` for the subject.
- `confidence` at initialization is proportional to evidence volume and quality.
- A Trust object initialized with sparse Evidence will have low `confidence`
  (e.g. 0.15–0.25), signaling to the Decision Engine that the score is
  uncertain.

Initialization produces a Trust object with:
- `status: initializing` while dimensions are being computed.
- `status: active` once all computable dimensions have a score.
- Dimensions with insufficient Evidence are scored at `0.0` with the
  deficiency noted in `evidence_weight`.

## Dimension Scoring

### `identity` dimension
Derived from Knowledge of type `identity_verification` and `business_registration`.

```
identity_score = knowledge_confidence(identity_verification)
                 × identity_verification_weight
               + knowledge_confidence(business_registration)
                 × registration_weight
```

If no identity Knowledge exists: `identity_score = 0.0`.
`identity_verification_weight` and `registration_weight` are defined in
the Trust Scoring ADR.

### `fulfillment` dimension
Derived from Knowledge of type `delivery_pattern` and `payment_behavior`.

```
fulfillment_score = (delivery_completion_rate × delivery_weight)
                  + (payment_completion_rate × payment_weight)
```

If insufficient transaction history: `fulfillment_score = 0.0`.
Minimum sample size for non-zero score: 5 completed transactions.
(Sample size threshold is ADR-dependent.)

### `consistency` dimension
Derived from behavioral variance across Evidence and Knowledge over time.
Low variance in fulfillment metrics over a rolling window = high consistency.

```
consistency_score = 1 - normalized_variance(fulfillment_scores_over_window)
```

Window length: 90 days. Minimum data points: 10.
Score is 0.0 if insufficient history.

### `financial` dimension
Derived from Knowledge of type `payment_behavior` and `dispute_history`.

```
financial_score = (1 - dispute_rate) × dispute_weight
               + (1 - reversal_rate) × reversal_weight
               + payment_timeliness_score × timeliness_weight
```

### `network` dimension
Derived from the Commercial Graph. For each neighbor within N hops:

```
network_score = Σ (neighbor_trust_score × relationship_strength × hop_decay^hop_distance)
                / normalization_factor
```

- `hop_decay`: confidence reduction per graph hop (e.g. 0.5 per hop).
- Default depth: 2 hops. Maximum: 3 hops.
- Neighbors with `trust.status: suspended` or `trust.status: revoked`
  contribute negatively to `network_score`.
- Exact formula and hop depth are ADR-dependent.

## Composite Score

```
trust_score = identity_score    × w_identity
            + fulfillment_score × w_fulfillment
            + consistency_score × w_consistency
            + financial_score   × w_financial
            + network_score     × w_network
```

Where `w_identity + w_fulfillment + w_consistency + w_financial + w_network = 1.0`.

Default weights (subject to ADR):
- `w_identity`: 0.25
- `w_fulfillment`: 0.30
- `w_consistency`: 0.15
- `w_financial`: 0.20
- `w_network`: 0.10

Weights may vary by `context.transaction_value_band`:
- `large` band: `w_identity` and `w_financial` increase; `w_network` decreases.
- `micro` band: `w_fulfillment` increases; `w_identity` can be lower.

## Context Variants

A Merchant's Trust score may differ across contexts. The Trust Engine
maintains separate Trust objects for material context differences:

- Separate objects per `transaction_value_band` if the Merchant has
  transaction history across multiple bands.
- Separate objects per `market` if the Merchant operates in multiple markets.
- A `general` Trust object (no specific counterparty type) always exists
  as the baseline.

When the Decision Engine requests Trust for a specific context and no exact
match exists, the Trust Engine returns the closest match with a
`context_match: approximate` flag.

## Explainability Output

Every Trust object must expose `primary_drivers` — the top 5 Evidence or
Knowledge objects that most influenced the composite score, with their
dimension assignment and contribution weight.

Example `primary_drivers` entry:
```json
{
  "ref_id": "uuid-of-knowledge-object",
  "ref_type": "knowledge",
  "dimension": "fulfillment",
  "contribution_weight": 0.28
}
```

This is what operators and counterparties see: "Trust score of 0.74 driven
primarily by 94% delivery completion rate (28%), verified identity document
(21%), and 0% dispute rate (18%)."

## Output Events

| Event | Consumers |
|---|---|
| `trust.initialized` | Decision Engine, Merchant/Organization record updater, monitoring |
| `trust.recomputed` | Decision Engine, monitoring |
| `trust.suspended` | Decision Engine, products, monitoring |
| `trust.revoked` | Decision Engine, products, monitoring, governance |
| `trust.stale` | Re-evaluation queue |

## SLAs

| Operation | Target |
|---|---|
| Trust recomputation from trigger event | < 10s p95 |
| Network dimension graph traversal (2 hops) | < 3s p95 |
| Trust initialization for new subject | < 30s p95 |
| Decay sweep | Every 6 hours |

## Open Questions (ADRs Required)

1. **Dimension weights** — default and context-variant weights for all five
   dimensions. Most critical ADR for this engine.
2. **Minimum evidence thresholds** — per dimension, what Evidence volume is
   required before a non-zero dimension score is produced?
3. **Network dimension depth and decay** — hop limit and per-hop decay factor.
4. **Context interpolation** — when no exact context match exists, how is
   the nearest Trust object selected and how is approximation communicated?
5. **Suspension inheritance** — when a parent Organization is suspended,
   do its Merchant Trust scores automatically suspend? Or only flag?

---
*This file is a Specification. It derives from and is constrained by the Kernel.*
