# Kernel · Ontology · Evidence

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: nothing (Evidence is the root entity)
Depended on by: Knowledge, Trust, Risk, Commercial Graph, Decision

## Definition

Evidence is an immutable, attributable observation about commercial reality.
It is the smallest unit of input the system accepts. Nothing enters SALAM's
reasoning without first existing as Evidence.

Evidence is not knowledge, not intelligence, and not truth. It is a claim
about reality, carrying its own quality and provenance metadata, which
downstream engines may validate, weight, link, or discard.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `evidence_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `subject_ref` | EntityRef | yes | no | The entity (Merchant, Transaction, etc.) this evidence is about. |
| `claim` | string | yes | no | The observation itself, in normalized form. |
| `claim_type` | enum | yes | no | Domain-specific classification (e.g. `delivery_confirmation`, `payment_record`, `identity_document`). |
| `raw_payload_ref` | URI | no | no | Pointer to the original unprocessed source artifact, if one exists. |
| `source` | Source | yes | no | Who/what produced this evidence. See Provenance. |
| `collection_method` | enum | yes | no | `direct_observation`, `third_party_attestation`, `user_submission`, `system_inference`, `document_extraction`. |
| `collected_at` | timestamp | yes | no | When the observation occurred (not when it was ingested). |
| `ingested_at` | timestamp | yes | no | When SALAM received it. |
| `validation_status` | enum | yes | yes (state machine) | `unvalidated`, `pending`, `validated`, `rejected`, `superseded`. |
| `validated_at` | timestamp | no | yes (set once) | When validation completed. |
| `confidence` | float [0,1] | yes | yes (recalculable) | System's current confidence in the claim's truth. |
| `quality` | QualityMetadata | yes | yes (recalculable) | See Quality Dimensions below. |
| `provenance` | ProvenanceMetadata | yes | append-only | See Provenance below. |
| `version` | integer | yes | no (new version = new object) | Monotonically increasing per `evidence_id` lineage. |
| `supersedes` | UUID \| null | no | no | Prior version this replaces, if any. |
| `links` | EntityRef[] | no | append-only | Other graph entities this evidence touches or strengthens/weakens. |
| `archived` | boolean | yes | yes (one-way: false→true) | Evidence is archived, never deleted. |

## Immutability Rule

Evidence is **never edited and never deleted.**

- Once `validation_status` reaches `validated` or `rejected`, the claim, source, and collection metadata are frozen.
- Corrections happen by creating a **new** Evidence object with `supersedes` pointing to the prior `evidence_id`, never by mutating the original.
- "Removing" evidence means setting `archived = true`. The object remains in storage for audit and historical reconstruction (see Kernel · Principles · Event-Driven Architecture).

This is a hard invariant, not a default. Any engine or product that needs to "change" evidence must go through supersession.

## Quality Dimensions (`QualityMetadata`)

Each evidence object carries a score across seven dimensions, as defined in
Kernel · Principles · Evidence Quality:

| Dimension | Question it answers |
|---|---|
| `authenticity` | Is the source genuinely who/what it claims to be? |
| `integrity` | Has the payload been altered since capture? |
| `freshness` | How recent is the observation relative to now? |
| `completeness` | Are required fields for this `claim_type` present? |
| `verifiability` | Can this claim be independently corroborated? |
| `provenance` | Is the origin chain fully documented? |
| `consistency` | Does this claim agree with other evidence about the same subject? |

`confidence` is a derived scalar computed from these seven dimensions by the
Evidence Engine. The exact weighting function is a Specification-layer
concern, not a Kernel concern — the Kernel only guarantees the dimensions
exist and are scored.

## Provenance (`ProvenanceMetadata`)

Per Kernel · Principles · Evidence Provenance, every evidence object must carry:

| Field | Description |
|---|---|
| `origin` | The original system, person, or process that generated the observation. |
| `collection_method` | Duplicated from top-level field for convenience in provenance queries. |
| `chain` | Ordered list of every transformation step applied since capture (normalize, enrich, re-score, etc.), each with actor + timestamp. |
| `ownership` | Which participant/organization is accountable for this evidence's accuracy. |
| `verification_confidence` | Confidence specifically in the provenance chain itself, separate from claim confidence. |

Provenance is append-only. Each transformation adds an entry to `chain`; nothing is ever removed from it.

## Lifecycle

Evidence moves through a fixed state sequence (Kernel · Principles · Evidence Lifecycle):

```
Capture → Normalize → Validate → Store → Link → Score → Consume → Archive
```

- **Capture**: raw observation enters the system via `collection_method`.
- **Normalize**: payload is transformed into the canonical `claim` representation.
- **Validate**: `validation_status` transitions from `unvalidated`/`pending` to `validated` or `rejected`.
- **Store**: persisted with full provenance; immutability begins.
- **Link**: connected to relevant entities in the Commercial Graph via `links`.
- **Score**: `quality` and `confidence` computed/recomputed.
- **Consume**: read by Knowledge Engine, Reasoning Engine, or products. Consumption never mutates the object.
- **Archive**: `archived = true`. Retained, not deleted.

Re-scoring may happen many times across an object's life (e.g. as corroborating or contradicting evidence arrives elsewhere in the graph) — this updates `quality`/`confidence` in place, since these are explicitly mutable fields, while the claim itself remains frozen.

## Relationship to Other Kernel Entities

- **Knowledge** = validated Evidence, organized. Knowledge cannot exist without at least one Evidence object backing it.
- **Trust** and **Risk** are computed *from* aggregated Evidence quality and outcomes — they never exist independent of Evidence (Kernel · Principles, §06).
- **Commercial Graph** edges are strengthened or weakened by Evidence via the `links` field.
- **Decision** recommendations must be traceable back to the specific Evidence objects that support them (explainability requirement).

## Explicit Non-Goals

Evidence is **not**:
- A guarantee of truth — it is a claim, scored for confidence.
- A transaction record in the accounting sense — transactions may *produce* evidence, but Evidence is the broader, generalized observation type.
- Editable, summarizable-in-place, or deletable.

## Open Questions (tracked, not yet resolved)

These are flagged here rather than silently decided, per the "models are authoritative, decisions need ADRs" principle:

1. Exact confidence-scoring formula (weighting of the seven quality dimensions) — Specification layer, needs an ADR once a methodology is chosen.
2. Storage backend for `raw_payload_ref` (object store vs. inline) — Architecture layer concern.
3. Retention policy for archived evidence (indefinite vs. tiered cold storage) — Governance layer concern, references Kernel · Principles · Evidence Governance (§67).

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
