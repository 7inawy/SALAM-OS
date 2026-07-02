# Specifications · Engines · Knowledge Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Evidence, Knowledge, Merchant, Organization
Upstream engines: Evidence Engine (consumes `evidence.validated`, `evidence.superseded`)
Consumed by: Trust Engine, Risk Engine, Reasoning Engine, Commercial Graph

## Purpose

The Knowledge Engine transforms validated Evidence into structured Knowledge
objects. It organizes observations into understanding — recognizing patterns
across Evidence, resolving contradictions, and producing the current best
understanding of each commercial subject.

Where the Evidence Engine captures what was observed, the Knowledge Engine
determines what it means.

## Responsibilities

1. **Derive** Knowledge objects from validated Evidence.
2. **Aggregate** multiple Evidence objects into a single Knowledge statement
   when they collectively support a conclusion.
3. **Resolve contradictions** when Evidence objects conflict.
4. **Maintain validity** — mark Knowledge as stale when underlying Evidence
   decays, and trigger re-evaluation.
5. **Retract** Knowledge when its backing Evidence is rejected or superseded
   without replacement.
6. **Publish events** — emit `knowledge.*` events for downstream engines.

## Derivation Triggers

The Knowledge Engine reacts to the following events:

| Event | Action |
|---|---|
| `evidence.validated` | Evaluate whether new Evidence creates or updates any Knowledge object for the subject. |
| `evidence.superseded` | Re-evaluate all Knowledge objects that referenced the superseded Evidence. |
| `knowledge.stale` (self-emitted) | Re-evaluate the stale Knowledge object against current Evidence. |
| `scheduled.knowledge_decay_check` | Periodic sweep to identify Knowledge objects whose `valid_until` has passed or whose confidence has decayed below `staleness_threshold`. |

## Derivation Methods

Per the Kernel Knowledge definition, five derivation methods are supported:

### `direct_extraction`
A single Evidence object directly supports a Knowledge statement.
Example: a validated identity document Evidence produces
`knowledge_type: identity_verification` for the subject.

```
Evidence(claim_type: identity_document, validation_status: validated)
  → Knowledge(knowledge_type: identity_verification, derivation_method: direct_extraction)
```

Confidence = Evidence confidence × source_trust_multiplier.
`source_trust_multiplier` is defined per `claim_type` in the
Knowledge Confidence ADR (to be written).

### `aggregation`
Multiple Evidence objects of the same `claim_type` are combined to produce
a stronger Knowledge statement.
Example: 47 delivery confirmation Evidence objects produce
`knowledge_type: delivery_pattern` with a completion rate statistic.

```
Evidence[](claim_type: delivery_confirmation, n=47)
  → Knowledge(knowledge_type: delivery_pattern, derivation_method: aggregation,
              statement: "completion_rate: 0.94, sample_size: 47, window: 90d")
```

Confidence = weighted average of contributing Evidence confidences,
discounted by the age distribution of the sample.

### `inference`
A Knowledge statement is derived from multiple Evidence objects of different
`claim_type`s whose combination implies a conclusion not stated in any single
Evidence.
Example: consistent delivery times + consistent payment receipt times →
`knowledge_type: operational_reliability`.

Inference rules are defined in the Knowledge Inference Rule Specification
(child spec, to be written). Inference produces lower base confidence than
direct_extraction or aggregation.

### `corroboration`
Two or more independent Evidence objects of different sources make the same
or equivalent claim, increasing confidence beyond any single source.
Example: a merchant's registration number appears in both a submitted document
(user_submission) and a government registry integration (third_party_attestation).

Confidence = combined confidence using the corroboration formula:
`1 - (1 - c1) × (1 - c2) × ... × (1 - cn)`
where c1..cn are individual Evidence confidences. This is the independence
assumption — it holds only when sources are genuinely independent.

### `contradiction_resolution`
Two Evidence objects make conflicting claims about the same subject and
claim_type. The Knowledge Engine must resolve or flag the contradiction.

Resolution logic:
1. If one Evidence object has significantly higher confidence (delta > 0.3),
   accept the higher-confidence one and flag the other.
2. If confidence is similar, produce Knowledge with `status: forming` and
   set `validation_status: pending` — human or governance review required.
3. Publish `knowledge.contradiction_detected` event with both Evidence IDs.

## Knowledge Type Registry

Core `knowledge_type` values and their derivation rules:

| knowledge_type | Derivation Method | Primary claim_types |
|---|---|---|
| `identity_verification` | direct_extraction | `identity_document`, `biometric_verification` |
| `business_registration` | direct_extraction / corroboration | `company_registration`, `regulatory_filing` |
| `delivery_pattern` | aggregation | `delivery_confirmation`, `delivery_failure` |
| `payment_behavior` | aggregation | `payment_record`, `payment_failure`, `reversal_record` |
| `dispute_history` | aggregation | `dispute_filed`, `dispute_resolution` |
| `operational_reliability` | inference | `delivery_pattern` + `payment_behavior` |
| `network_association` | inference | `transaction_record` (repeated counterparties) |
| `fraud_indicator` | corroboration / inference | `fraud_report`, `abnormal_pattern_flag` |
| `compliance_status` | direct_extraction / corroboration | `regulatory_filing`, `compliance_certificate` |

Additional types are added as products require them — via the Specification
update process, not ad hoc.

## Validity and Decay

Each Knowledge object has a `ValidityWindow` with a `decay_rate` assigned per
`knowledge_type`:

| knowledge_type | decay_rate | Rationale |
|---|---|---|
| `identity_verification` | `slow` | Documents expire over years, not days. |
| `business_registration` | `slow` | Registration status changes infrequently. |
| `delivery_pattern` | `moderate` | Patterns shift seasonally or with business changes. |
| `payment_behavior` | `moderate` | Payment behavior can change in weeks. |
| `dispute_history` | `none` | History doesn't decay — it is historical record. |
| `fraud_indicator` | `fast` | Active fraud patterns must be re-evaluated frequently. |
| `operational_reliability` | `moderate` | Composite metric follows its components. |
| `compliance_status` | `slow` | Regulatory status changes infrequently. |

`staleness_threshold` defaults:
- `slow` decay types: 0.40
- `moderate` decay types: 0.50
- `fast` decay types: 0.65
- `none` decay types: N/A (never stale from decay; only retracted)

When `confidence` drops below `staleness_threshold`, the Knowledge Engine
emits `knowledge.stale` and the object's `status` transitions to `stale`.
Re-evaluation is triggered immediately if new Evidence is available; otherwise
it remains stale until new Evidence arrives.

## Contradiction and Retraction

**Retraction** occurs when:
- All backing Evidence objects for a Knowledge object have been rejected
  or superseded with no replacement.
- A governance process issues a retraction instruction.

On retraction:
1. Set Knowledge `status: retracted`, `retraction_reason` required.
2. Publish `knowledge.retracted` with `knowledge_id` and `retraction_reason`.
3. Downstream engines (Trust, Risk) re-evaluate assessments that cited
   this Knowledge object.

Retracted Knowledge is never deleted.

## Output Events

| Event | Payload | Consumers |
|---|---|---|
| `knowledge.derived` | Full Knowledge object | Trust Engine, Risk Engine, Graph Engine, Reasoning Engine |
| `knowledge.updated` | `knowledge_id`, changed fields, `last_evaluated_at` | Trust Engine, Risk Engine |
| `knowledge.stale` | `knowledge_id`, `subject_ref`, `knowledge_type` | Re-evaluation queue, monitoring |
| `knowledge.retracted` | `knowledge_id`, `retraction_reason`, `subject_ref` | Trust Engine, Risk Engine, monitoring |
| `knowledge.contradiction_detected` | `knowledge_id`, `evidence_id_a`, `evidence_id_b` | Review queue, monitoring |

## SLAs

| Operation | Target |
|---|---|
| Knowledge derivation from `evidence.validated` event | < 5s p95 |
| Aggregation update (new Evidence added to existing pattern) | < 10s p95 |
| Decay check sweep | Every 1 hour |
| Contradiction detection | < 5s from conflicting Evidence arrival |

## Failure Modes

| Failure | Behaviour |
|---|---|
| Evidence store unavailable | Buffer incoming events. Retry with backoff. Do not drop events. |
| Inference rule engine unavailable | Defer inference derivations. Direct extraction and aggregation proceed normally. |
| Event stream publish failure | Persist Knowledge. Buffer event. Replay when stream recovers. |
| Contradiction unresolvable | Set `status: forming`. Publish `contradiction_detected`. Await governance resolution. |

## Open Questions (ADRs Required)

1. **Knowledge confidence formula per derivation method** — exact formulas
   for aggregation confidence weighting and inference confidence discounting.
2. **Inference rule authoring** — who writes inference rules, in what format,
   and how are they versioned and deployed? Governance concern.
3. **Staleness threshold configuration** — are thresholds global or per-market?
   Configurable per deployment or Kernel-fixed?
4. **Contradiction resolution authority** — when automated resolution fails,
   who has authority to resolve a contradiction and how is it recorded?

---
*This file is a Specification. It derives from and is constrained by the Kernel.*
