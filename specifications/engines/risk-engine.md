# Specifications · Engines · Risk Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Risk, Evidence, Knowledge, Merchant, Organization, Relationship, Graph, Trust
Upstream engines: Evidence Engine, Knowledge Engine, Graph Engine, Trust Engine
Consumed by: Decision Engine, Reasoning Engine, products

## Purpose

The Risk Engine computes and maintains Risk assessments for every Merchant and
Organization in the system. It answers, continuously and in context: what is
the probability and potential impact of something going wrong in a commercial
interaction involving this entity?

Risk is prospective and independent of Trust. High Trust does not suppress
high Risk. The Decision Engine consumes both, and both are required for a
complete Decision.

## Responsibilities

1. **Initialize** Risk objects when a new Merchant or Organization is created.
2. **Recompute** Risk scores when triggered by upstream events.
3. **Raise and resolve flags** — named risk signals that escalate the
   assessment beyond what the dimension model produces.
4. **Maintain context variants** — Risk is context-scoped like Trust.
5. **Escalate** Risk objects when critical flags are active.
6. **Expose explainability** — every Risk object must carry `primary_drivers`.
7. **Publish events** for downstream consumers.

## Trigger Events

| Event | Action |
|---|---|
| `merchant.created` / `organization.created` | Initialize Risk immediately (unlike Trust, Risk can be initialized with zero transaction Evidence — identity risk exists from the first moment). |
| `evidence.validated` | Re-evaluate Risk for the subject. |
| `evidence.superseded` | Re-evaluate Risk objects that cited the superseded Evidence. |
| `knowledge.derived` / `knowledge.updated` | Re-evaluate Risk objects consuming this Knowledge type. |
| `knowledge.retracted` | Re-evaluate Risk objects citing the retracted Knowledge. |
| `relationship.formed` / `relationship.strength_updated` | Re-evaluate the `network` and `concentration` dimensions. |
| `merchant.suspended` / `organization.suspended` | Raise a `suspension` Risk Flag. Re-evaluate immediately. |
| `transaction.disputed` | Raise `high_dispute_velocity` flag if dispute rate crosses threshold. |
| `transaction.reversed` | Update `behavioral` dimension. |
| `scheduled.risk_decay_check` | Periodic sweep for stale Risk objects. |
| `external.market_risk_update` | Re-evaluate `market` dimension when external market data updates. |

## Risk Initialization

Unlike Trust, Risk is initialized immediately on entity creation — before any
transaction Evidence exists — because identity risk is present from the first
moment. An unverified Merchant with zero transaction history is not zero-risk;
their risk profile is dominated by the `identity` dimension at full weight.

Initial Risk object:
- `identity` dimension: derived from `identity_status` at creation.
  `unverified` → `identity_score = 0.80` (high risk). `verified` → `0.10`.
- All other dimensions: `0.0` initially, increasing as Evidence arrives.
- `confidence`: low at initialization — honest about the data sparsity.
- `severity`: derived from composite `score`.

## Dimension Scoring

### `identity` dimension
Inverse of the Trust `identity` dimension — where Trust rewards verified
identity, Risk penalizes unverified identity.

```
identity_risk = 1 - knowledge_confidence(identity_verification)
```

`identity_status: disputed` applies a penalty multiplier on top of the
base score (multiplier is ADR-dependent).

### `behavioral` dimension
Derived from Knowledge of type `dispute_history`, `payment_behavior`, and
any active fraud indicators.

```
behavioral_risk = (dispute_rate × dispute_weight)
               + (reversal_rate × reversal_weight)
               + (fraud_indicator_confidence × fraud_weight)
               + (default_history_confidence × default_weight)
```

Dispute velocity matters as much as dispute rate — a sudden spike in
disputes over a short window is a stronger signal than a consistent low
dispute rate over time. Velocity scoring formula is ADR-dependent.

### `financial` dimension
Derived from transaction value patterns relative to observed capacity.

```
financial_risk = (transaction_value / estimated_capacity)   ← exposure ratio
               × (1 - payment_reliability_score)            ← reliability discount
```

`estimated_capacity` is derived from Knowledge of type `payment_behavior`
(average transaction value, standard deviation). High-value transactions
relative to observed capacity increase financial risk.

### `network` dimension
Contagion risk from the Commercial Graph. Unlike Trust's network dimension
(which averages neighbor trust), Risk's network dimension specifically
measures proximity to high-risk or flagged entities.

```
network_risk = Σ (neighbor_risk_score × relationship_strength × hop_decay^hop_distance)
               / normalization_factor
```

Suspended and flagged neighbors contribute their full risk score.
Terminated relationships contribute at reduced weight (historical signal).
Default depth: 2 hops. Same hop_decay as Trust for consistency.

### `market` dimension
External signal — derived from market-level risk data, not entity-specific
Evidence. Inputs:

| Signal | Source |
|---|---|
| Market volatility index | External data provider (ADR required for source selection) |
| Regulatory environment score | Internally maintained per-market assessment |
| Payment infrastructure reliability | Internal monitoring data |
| Conflict / political stability | External data provider |

`market_risk` is a composite of these signals, normalized to [0,1].
It is the same for all entities operating in the same market.
It is updated on a schedule (frequency is ADR-dependent).

### `concentration` dimension
Risk from over-dependence on a single counterparty, market, or product category.

```
concentration_risk = max(
  herfindahl_index(counterparty_transaction_distribution),
  herfindahl_index(market_transaction_distribution),
  herfindahl_index(product_category_distribution)
)
```

Herfindahl index: `Σ (share_i)^2`. Ranges from 0 (perfectly diversified)
to 1 (total concentration on one counterparty/market/category).

## Composite Score

```
risk_score = identity_risk    × w_identity
           + behavioral_risk  × w_behavioral
           + financial_risk   × w_financial
           + network_risk     × w_network
           + market_risk      × w_market
           + concentration_risk × w_concentration
```

Default weights (subject to ADR):
- `w_identity`: 0.20
- `w_behavioral`: 0.25
- `w_financial`: 0.25
- `w_network`: 0.15
- `w_market`: 0.10
- `w_concentration`: 0.05

Severity bands (from Kernel):
- `low`: 0.00–0.25
- `medium`: 0.25–0.50
- `high`: 0.50–0.75
- `critical`: 0.75–1.00

## Risk Flags

Risk Flags are named escalation signals that supplement the dimension model.
They are raised automatically by the Risk Engine or by upstream engines.

| Flag Type | Trigger | Severity |
|---|---|---|
| `fraud_network_proximity` | A direct neighbor has an active fraud indicator. | `high` |
| `sanctions_list_match` | Subject's identity matches a sanctions list entry. | `critical` |
| `high_dispute_velocity` | Dispute rate has increased >50% over 30-day rolling window. | `high` |
| `identity_conflict` | `identity_status: disputed` on the subject entity. | `high` |
| `abnormal_transaction_pattern` | Transaction volume or value deviates >3σ from 90-day baseline. | `warning` |
| `suspended_network_node` | A direct counterparty has been suspended. | `warning` |
| `unresolved_default` | An unresolved default Event exists for this subject. | `critical` |

A single active `critical` flag triggers `status: escalated` on the Risk
object. Escalated Risk objects require governance acknowledgment before the
Decision Engine can use them in a Decision.

## Output Events

| Event | Consumers |
|---|---|
| `risk.initialized` | Decision Engine, Merchant/Organization record updater, monitoring |
| `risk.recomputed` | Decision Engine, monitoring |
| `risk.escalated` | Decision Engine, governance queue, products, monitoring |
| `risk.flag_raised` | Decision Engine, monitoring, review queue |
| `risk.flag_resolved` | Decision Engine, monitoring |
| `risk.resolved` | Monitoring, governance |
| `risk.stale` | Re-evaluation queue |

## SLAs

| Operation | Target |
|---|---|
| Risk initialization (new entity) | < 5s p95 |
| Risk recomputation from trigger event | < 10s p95 |
| Flag detection and raising | < 3s p95 from triggering event |
| Network dimension traversal (2 hops) | < 3s p95 |
| Market dimension update | Every 24 hours, or on `external.market_risk_update` |

## Open Questions (ADRs Required)

1. **Dimension weights** — default and context-variant weights for all six
   dimensions.
2. **Dispute velocity formula** — rolling window length and threshold for
   `high_dispute_velocity` flag.
3. **Market risk data sources** — which external providers, at what update
   frequency, with what fallback when unavailable?
4. **Sanctions list integration** — which lists, how are they ingested, how
   is a match confirmed (fuzzy vs. exact)? Governance-sensitive. Needs ADR.
5. **Escalation governance** — who de-escalates a `critical` Risk object,
   via what process, and how is it recorded?
6. **Trust/Risk conflict resolution** — when Trust is high and Risk is
   critical, what guidance does the Decision Engine get? Needs ADR.

---
*This file is a Specification. It derives from and is constrained by the Kernel.*
