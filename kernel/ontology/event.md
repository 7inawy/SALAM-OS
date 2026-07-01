# Kernel · Ontology · Event

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Merchant, Organization
Depended on by: Transaction, Relationship, Knowledge, Commercial Graph

## Definition

An Event is a discrete, timestamped occurrence in commercial reality that is
significant enough to produce or update Evidence. It is the unit of commercial
activity that SALAM observes and records — the thing that happened, as
distinct from the observation about it (Evidence) or the understanding derived
from it (Knowledge).

Events are the system's model of commercial reality in motion. Where Merchants
and Organizations are the actors and Evidence is the observation record, Events
are what actually happens between actors: a delivery, a payment, a dispute, a
registration, a failure.

Not every occurrence in the world is an Event in SALAM's sense. An Event is
only created when the occurrence is (a) commercially significant, (b) involves
at least one known Merchant or Organization, and (c) is supported by at least
one Evidence object. Events without Evidence backing are not admitted.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `event_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `event_type` | string | yes | no | Classification of the occurrence. See Event Types below. |
| `occurred_at` | timestamp | yes | no | When the event happened in reality (not when it was recorded). |
| `recorded_at` | timestamp | yes | no | When SALAM recorded this Event. |
| `participants` | Participant[] | yes | no | The Merchants and Organizations involved. Minimum one. |
| `evidence_refs` | UUID[] | yes | append-only | Evidence objects that document this Event. Minimum one at creation. |
| `outcome` | enum | yes | yes (state machine) | `pending`, `completed`, `failed`, `disputed`, `cancelled`, `unknown`. |
| `outcome_resolved_at` | timestamp \| null | no | yes (set once) | When `outcome` reached a terminal state. |
| `significance` | enum | yes | no | `routine`, `notable`, `critical`. Drives downstream processing priority. |
| `market` | string | yes | no | ISO 3166-1 alpha-2 country code where the Event occurred. |
| `channel` | string \| null | no | no | Commercial channel in which this Event took place, if applicable. |
| `linked_transaction_ref` | UUID \| null | no | no | If this Event produced or is directly tied to a Transaction, that Transaction ID. |
| `tags` | string[] | no | append-only | Free-form classification tags for filtering and routing. |
| `flags` | Flag[] | no | append-only | Compliance, fraud, or quality flags raised on this Event. |
| `created_at` | timestamp | yes | no | When this Event record was created. |
| `version` | integer | yes | no | Monotonically increasing per `event_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Event Types

`event_type` is an open enum extended at the Specification layer for each
domain. Core event types at the Kernel level:

| Type | Description |
|---|---|
| `delivery` | A goods delivery between merchant and counterparty. |
| `payment` | A payment transfer between parties. |
| `dispute` | A formal dispute raised between participants. |
| `dispute_resolution` | Resolution of a prior dispute. |
| `identity_submission` | A Merchant or Organization submitted identity documentation. |
| `registration` | A Merchant or Organization registered with a platform or authority. |
| `suspension` | A Merchant or Organization was suspended by a platform or authority. |
| `reinstatement` | A suspension was lifted. |
| `contract` | A commercial agreement was formed between participants. |
| `default` | A Merchant or Organization failed to fulfill a commercial obligation. |
| `fraud_report` | A fraud allegation was raised against a participant. |
| `verification` | A verification check was performed on a participant. |

Additional types (e.g. `inventory_update`, `price_change`, `review_submitted`)
are Specification-layer extensions — they do not belong in the Kernel.

## Participants (`Participant`)

Every Event involves at least one known actor:

| Field | Type | Description |
|---|---|---|
| `participant_id` | UUID | The Merchant ID or Organization ID. |
| `participant_type` | enum | `merchant`, `organization`. |
| `role` | string | The role this participant played in the Event, e.g. `seller`, `buyer`, `logistics_provider`, `guarantor`, `subject`, `reporter`. |

Roles are open strings — the Specification layer defines valid roles per
`event_type`. The Kernel only requires that at least one participant is
present and their role is named.

## Outcome State Machine

```
pending → completed
        → failed
        → disputed → completed (resolved in favour)
                   → failed    (resolved against)
        → cancelled
        → unknown
```

- **pending**: the event has occurred but its outcome is not yet known.
- **completed**: the event resolved successfully.
- **failed**: the event did not complete as intended.
- **disputed**: a participant has raised a dispute about the outcome.
- **cancelled**: the event was voided before completion.
- **unknown**: outcome cannot be determined from available Evidence.

`outcome_resolved_at` is set when `outcome` reaches a terminal state
(`completed`, `failed`, `cancelled`, `unknown`). It is immutable once set.

## Evidence Invariant

An Event must have at least one Evidence object at creation (`evidence_refs`
is required and non-empty). Additional Evidence can be appended as it arrives
(e.g. a delivery photo arriving after the delivery is logged). Evidence refs
are append-only — they are never removed from an Event.

If new Evidence contradicts the current `outcome`, the Event transitions to
`disputed` or has its `outcome` corrected via a governed process, not by
silently updating the existing Event. The original record and its Evidence
links are preserved.

## Relationship to Other Kernel Entities

- **Evidence**: Every Event is documented by one or more Evidence objects.
  The Event is what happened; Evidence is the observation about it. Events
  cannot exist without Evidence.
- **Merchant / Organization**: Events involve Merchants and Organizations as
  `participants`. An Event without a known participant is not admissible.
- **Transaction**: Transactions are a specific, financially-significant subtype
  of Event. Not all Events are Transactions; all Transactions are Events.
  `linked_transaction_ref` links an Event to its Transaction if one exists.
- **Knowledge**: The Knowledge Engine derives Knowledge from the pattern of
  Events about a subject (e.g. a Merchant's delivery completion rate is
  derived from `delivery` Events).
- **Commercial Graph**: Events create or strengthen edges in the Commercial
  Graph between participating actors.
- **Relationship**: Recurring Events between the same participants establish
  and update Relationships in the Relationship entity.

## Explicit Non-Goals

An Event is **not**:
- A raw observation — that is Evidence. An Event is the occurrence itself,
  documented by Evidence.
- A Transaction — Transactions are financially settled Events. Event is the
  broader, generalized occurrence type.
- Retroactively editable — corrections are append-only (new Evidence, outcome
  transitions) or governed dispute processes.
- A log entry or audit trail — Events are commercially significant occurrences,
  not system logs.

## Open Questions (tracked, not yet resolved)

1. **Event significance assignment**: who or what assigns `significance`
   (`routine` / `notable` / `critical`) — is it rule-based, ML-based, or
   configurable per `event_type`? Specification layer concern. Needs an ADR.
2. **Event deduplication**: if two Evidence objects describe the same real-world
   occurrence, how does the system detect and prevent duplicate Event creation?
   Architecture/engine concern. Needs an ADR.
3. **Retroactive Evidence**: if Evidence for an Event arrives significantly
   after the Event is recorded (e.g. a delivery photo uploaded weeks late),
   how is this handled without invalidating the original timeline? Needs an ADR.
4. **Cross-market events**: for Events that span multiple markets (e.g.
   cross-border logistics), the single `market` field is insufficient. Needs
   an ADR at the Specification layer.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
