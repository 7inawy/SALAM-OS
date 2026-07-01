# Kernel · Ontology · Knowledge

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence
Depended on by: Commercial Graph, Reasoning Engine, Intelligence, Decision

## Definition

Knowledge is validated Evidence, organized and interpreted within a commercial
context. It is the system's current best understanding of a subject, derived
exclusively from one or more Evidence objects and structured for reasoning.

Knowledge is not raw observation (that is Evidence), not a conclusion (that is
Intelligence), and not a recommendation (that is Decision). It is the bridge
between what has been observed and what can be reasoned about.

Every Knowledge object must be traceable to at least one `validated` Evidence
object. Knowledge without an Evidence backing is inadmissible — the system
does not accept assertions, only derived understanding.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `knowledge_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `subject_ref` | EntityRef | yes | no | The entity this knowledge is about (Merchant, Organization, etc.). |
| `knowledge_type` | enum | yes | no | Domain classification. e.g. `merchant_profile`, `delivery_pattern`, `payment_behavior`, `identity_verification`, `risk_indicator`. |
| `statement` | string | yes | no | The interpreted claim, in normalized form. What the system understands to be true about the subject. |
| `evidence_refs` | UUID[] | yes | no | One or more `evidence_id` values this knowledge is derived from. Minimum one. All must have `validation_status: validated`. |
| `derivation_method` | enum | yes | no | How Evidence was turned into Knowledge: `direct_extraction`, `aggregation`, `inference`, `corroboration`, `contradiction_resolution`. |
| `confidence` | float [0,1] | yes | yes (recalculable) | Weighted aggregate of the backing Evidence confidence scores, adjusted for derivation method. |
| `validity` | ValidityWindow | yes | yes (recalculable) | The time window during which this Knowledge is considered current. See Validity below. |
| `status` | enum | yes | yes (state machine) | `forming`, `active`, `stale`, `superseded`, `retracted`. |
| `supersedes` | UUID \| null | no | no | Prior `knowledge_id` this version replaces, if any. |
| `retraction_reason` | string \| null | no | yes (set once) | Required if `status = retracted`. Immutable once set. |
| `provenance` | KnowledgeProvenance | yes | append-only | Derivation chain from Evidence through to this object. |
| `graph_links` | EntityRef[] | no | append-only | Commercial Graph entities this knowledge informs. |
| `version` | integer | yes | no | Monotonically increasing per `knowledge_id` lineage. |
| `created_at` | timestamp | yes | no | When this Knowledge object was first derived. |
| `last_evaluated_at` | timestamp | yes | yes | When confidence and validity were last recomputed. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Derivation Rule

Knowledge is **always derived, never asserted.**

- Every `knowledge_id` must link to at least one Evidence object with `validation_status: validated`.
- If backing Evidence is later `rejected` or `superseded`, any Knowledge derived from it must be re-evaluated — `status` transitions to `stale` pending re-derivation.
- Knowledge derived from a single Evidence source carries that source's confidence directly. Knowledge derived from multiple sources is a weighted combination — exact weighting is a Specification-layer concern.
- New Knowledge never overwrites old Knowledge. Corrections create a new object with `supersedes` pointing to the prior `knowledge_id`.

## Validity Window (`ValidityWindow`)

Knowledge has a temporal dimension Evidence does not. An observation happened
at a point in time; understanding decays or is invalidated as reality changes.

| Field | Type | Description |
|---|---|---|
| `valid_from` | timestamp | When this Knowledge became current (typically when derived). |
| `valid_until` | timestamp \| null | When this Knowledge expires. Null = indefinite until superseded or retracted. |
| `decay_rate` | enum | How fast confidence degrades over time: `none`, `slow`, `moderate`, `fast`. Depends on `knowledge_type` — e.g. identity verification decays slowly, delivery patterns decay fast. |
| `staleness_threshold` | float [0,1] | Confidence floor below which `status` automatically transitions to `stale`. |

## Status State Machine

```
forming → active → stale → superseded
                 ↘ retracted
```

- **forming**: derivation in progress, not yet available for reasoning.
- **active**: current, available for consumption by Reasoning Engine and Graph.
- **stale**: confidence has decayed below `staleness_threshold`, or backing Evidence has been invalidated. Triggers re-evaluation.
- **superseded**: replaced by a newer version via the `supersedes` chain.
- **retracted**: withdrawn because backing Evidence was rejected or a derivation error was found. `retraction_reason` required.

A retracted Knowledge object remains in storage. Retraction is never deletion.

## Knowledge Provenance (`KnowledgeProvenance`)

| Field | Description |
|---|---|
| `derived_by` | Engine or process that produced this Knowledge object (e.g. `knowledge-engine-v1`). |
| `derived_at` | Timestamp of derivation. |
| `evidence_snapshot` | Snapshot of the `evidence_id` list and their `confidence` scores at derivation time. Immutable. Captures the exact evidential state that produced this Knowledge even if Evidence is later updated. |
| `derivation_chain` | Ordered log of every re-evaluation or re-scoring event after initial derivation, each with actor + timestamp + trigger. Append-only. |

The `evidence_snapshot` is critical: it makes Knowledge auditable even after its backing Evidence has been superseded or re-scored. You can always reconstruct exactly why a Knowledge object said what it said at the time it was active.

## Relationship to Other Kernel Entities

- **Evidence** → Knowledge: Knowledge cannot exist without validated Evidence. This is the single most important dependency in the ontology — see Evidence (`kernel/ontology/evidence.md`).
- **Knowledge** → Commercial Graph: active Knowledge informs Graph edges and node attributes via `graph_links`.
- **Knowledge** → Reasoning Engine: the Reasoning Engine consumes active Knowledge to produce Intelligence.
- **Knowledge** → Trust / Risk: Trust and Risk scores are aggregated from Knowledge objects about a subject, weighted by confidence and recency.
- **Knowledge** → Decision: Decisions must be traceable to the active Knowledge objects that informed them (and transitively to the Evidence beneath).

## Explicit Non-Goals

Knowledge is **not**:
- A raw observation — that is Evidence. Knowledge always involves interpretation.
- An assertion without Evidence backing — the system does not accept these.
- A final conclusion or recommendation — that is Intelligence and Decision respectively.
- Permanent — Knowledge degrades, becomes stale, and can be retracted.

## Open Questions (tracked, not yet resolved)

1. **Multi-source confidence weighting**: when Knowledge is derived from N Evidence objects via `aggregation` or `corroboration`, the exact weighting formula is a Specification-layer concern. Needs an ADR.
2. **Decay rate assignment**: who assigns `decay_rate` to a `knowledge_type` — is it hardcoded in the Knowledge Engine spec, or configurable per deployment? Needs an ADR.
3. **Stale re-evaluation trigger**: is re-evaluation of stale Knowledge automatic (event-driven) or manual? Ties into the Event-Driven Architecture principle. Needs an ADR.
4. **Knowledge graph vs. knowledge store**: does Knowledge live in the Commercial Graph directly, or in a separate store that feeds it? Architecture layer concern.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
