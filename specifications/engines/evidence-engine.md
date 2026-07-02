# Specifications · Engines · Evidence Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Evidence, Event, Merchant, Organization
Consumed by: Knowledge Engine, Trust Engine, Risk Engine, Commercial Graph

## Purpose

The Evidence Engine is the entry point of the system. It is responsible for
ingesting raw observations from all sources, normalizing them into canonical
Evidence objects, validating them, scoring their quality, and publishing them
to the event stream for downstream consumption.

Nothing enters SALAM's reasoning pipeline without passing through the Evidence
Engine first. It is the gatekeeper between raw reality and structured knowledge.

## Responsibilities

1. **Ingest** raw observations from all collection channels.
2. **Normalize** raw payloads into canonical `claim` format per `claim_type`.
3. **Validate** normalized claims — syntactic validity, source authentication,
   business rule checks.
4. **Score quality** across all seven Evidence quality dimensions.
5. **Detect duplicates** — prevent the same real-world observation from
   producing multiple Evidence objects.
6. **Publish events** — emit `evidence.*` events for downstream engines.
7. **Handle supersession** — when a correction arrives, create the superseding
   Evidence object and link it to the prior one.

## Ingestion Channels

The Evidence Engine accepts input from the following channels:

| Channel | collection_method | Description |
|---|---|---|
| Webhook / API push | `direct_observation` | Partners push events (delivery confirmations, payment records) in real time. |
| Platform integration | `third_party_attestation` | Marketplace or logistics platform data pulled on schedule or event-triggered. |
| Merchant portal | `user_submission` | Merchants submit documents (ID, registration, invoices) via product UI. |
| Internal engine | `system_inference` | Another engine produces Evidence (e.g. anomaly detection flags a transaction pattern). |
| Document processing | `document_extraction` | OCR/NLP pipeline extracts structured claims from uploaded documents. |

Each channel has its own ingestion adapter. Adapters are responsible for
authentication and format translation; the Evidence Engine core is format-
agnostic and operates only on the normalized ingestion payload.

## Ingestion Payload (Input Contract)

```json
{
  "source": {
    "source_type": "string",
    "identifier": "string"
  },
  "collection_method": "direct_observation | third_party_attestation | user_submission | system_inference | document_extraction",
  "subject_ref": {
    "entity_type": "merchant | organization",
    "entity_id": "uuid"
  },
  "claim_type": "string",
  "raw_payload": "object | string | base64",
  "raw_payload_format": "json | text | base64_pdf | base64_image",
  "collected_at": "ISO 8601 timestamp",
  "idempotency_key": "string"
}
```

`idempotency_key` is required. The same key submitted twice produces one
Evidence object, not two. This is the primary deduplication mechanism at the
ingestion boundary.

## Processing Pipeline

Each ingested payload moves through the following stages in order:

### Stage 1 — Authenticate Source
Verify that the source is a known, authorized submitter. Unknown sources are
rejected with `rejection_reason: unknown_source`. Source authentication
details are Architecture layer concerns (API keys, mTLS, OAuth tokens).

### Stage 2 — Deduplicate
Check `idempotency_key` against the deduplication store (TTL: 30 days).
If key exists, return the existing `evidence_id` with `status: duplicate`.
Do not create a new Evidence object.

### Stage 3 — Normalize
Transform `raw_payload` into a canonical `claim` string for the given
`claim_type`. Normalization rules per `claim_type` are defined in the
Claim Normalization Specification (child spec, to be written). If
normalization fails, reject with `rejection_reason: normalization_failed`.

### Stage 4 — Validate
Apply validation rules for the given `claim_type`:
- **Syntactic**: required fields present, types correct.
- **Semantic**: claim values are plausible (e.g. delivery date not in future,
  amount is positive).
- **Business rule**: claim-type-specific rules (e.g. an identity document must
  include issuing country and expiry date).

Validation result sets `validation_status`:
- All rules pass → `validated`
- Correctable issues → `pending` (flagged for review)
- Fatal issues → `rejected` with `rejection_reason`

### Stage 5 — Score Quality
Compute all seven quality dimensions for the Evidence object:

| Dimension | Scoring Approach |
|---|---|
| `authenticity` | Based on source trust level and authentication method. |
| `integrity` | Hash verification of raw payload against stored raw_payload_ref. |
| `freshness` | Function of `collected_at` age relative to now and claim_type decay rate. |
| `completeness` | Ratio of required claim_type fields present to total required. |
| `verifiability` | Based on collection_method: `direct_observation` > `third_party_attestation` > `user_submission` > `system_inference`. |
| `provenance_score` | Completeness and depth of the provenance chain. |
| `consistency` | Comparison against existing Evidence about the same subject and claim_type. Low on first submission; improves with corroboration. |

`confidence` = weighted combination of seven dimensions. Weights are defined
in the Evidence Scoring ADR (to be written; open question from Kernel).

### Stage 6 — Persist
Write the Evidence object to the Evidence Store. The object is immutable
from this point.

### Stage 7 — Publish Events
Emit the appropriate event to the event stream:
- `evidence.ingested` — always, on successful ingestion
- `evidence.validated` — when `validation_status: validated`
- `evidence.rejected` — when `validation_status: rejected`
- `evidence.pending` — when `validation_status: pending`

## Supersession Flow

When an operator or source submits a correction to an existing Evidence object:

1. Ingest the corrective payload normally through Stages 1–5.
2. Set `supersedes` to the prior `evidence_id`.
3. Set the prior Evidence object's `validation_status` to `superseded`.
4. Publish `evidence.superseded` (referencing both old and new IDs) and
   `evidence.validated` (for the new object).
5. Downstream engines react to `evidence.superseded` and re-evaluate any
   Knowledge, Trust, or Risk derived from the prior Evidence.

## Output Events

| Event | Payload | Consumers |
|---|---|---|
| `evidence.ingested` | `evidence_id`, `subject_ref`, `claim_type`, `source`, `ingested_at` | Audit log, monitoring |
| `evidence.validated` | Full Evidence object | Knowledge Engine, Trust Engine, Risk Engine, Graph Engine |
| `evidence.rejected` | `evidence_id`, `rejection_reason`, `source` | Monitoring, source notification |
| `evidence.pending` | `evidence_id`, `pending_reasons[]` | Review queue, monitoring |
| `evidence.superseded` | `old_evidence_id`, `new_evidence_id`, `subject_ref` | Knowledge Engine, Trust Engine, Risk Engine |

## SLAs

| Operation | Target |
|---|---|
| Ingestion acknowledgement (idempotency check + auth) | < 200ms p99 |
| Full pipeline to `evidence.validated` event | < 2s p95, < 5s p99 |
| Document extraction pipeline (OCR/NLP) | < 30s p95 |
| Deduplication TTL | 30 days |

SLA targets are indicative. Final values require load testing and are confirmed
in the Architecture layer.

## Failure Modes

| Failure | Behaviour |
|---|---|
| Source authentication failure | Reject immediately. Do not store. Log attempt. |
| Normalization failure | Reject with reason. Store raw payload for debugging if source is authenticated. |
| Quality scoring unavailable | Accept with `confidence: null`. Publish `evidence.ingested`. Trigger re-score when scoring recovers. |
| Event stream unavailable | Accept and persist Evidence. Buffer events locally. Replay when stream recovers. Do not block ingestion. |
| Duplicate store unavailable | Fail open: process as new. Flag as potentially duplicate. Resolve async. |

## Open Questions (ADRs Required)

1. **Evidence confidence weighting formula** — exact weights for combining
   seven quality dimensions into `confidence`. Must be decided before
   the engine can be implemented.
2. **Claim normalization rules** — per-claim_type normalization is a large
   surface area. A child specification is needed.
3. **Document extraction pipeline** — OCR/NLP toolchain selection is an
   Architecture decision.
4. **Deduplication store technology** — Redis, DynamoDB, or equivalent.
   Architecture decision.
5. **Pending review queue** — what triggers promotion from `pending` to
   `validated` or `rejected`? Human review? Automated re-evaluation?
   Governance concern.

---
*This file is a Specification. It derives from and is constrained by the Kernel.
It does not redefine Kernel concepts — it operationalises them.*
