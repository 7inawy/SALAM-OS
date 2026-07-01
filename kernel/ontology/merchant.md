# Kernel · Ontology · Merchant

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Knowledge
Depended on by: Organization, Transaction, Event, Relationship, Trust, Risk, Decision

## Definition

A Merchant is a commercial actor that sells goods or services within an
emerging market context and is a primary subject of SALAM's intelligence
operations.

Merchants are not users of SALAM — they are subjects. SALAM collects Evidence
about Merchants, derives Knowledge from it, and produces Trust and Risk
assessments that inform Decisions affecting them. A Merchant may also
*participate* in SALAM (e.g. by submitting evidence about themselves), but
participation does not change their ontological role as a subject.

A Merchant is the most granular commercial actor in the system. Groups of
Merchants operating under shared ownership or governance are modeled as
Organizations. A single legal entity may control multiple Merchants.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `merchant_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `display_name` | string | yes | yes | Trading name as presented to counterparties. |
| `legal_name` | string \| null | no | yes | Registered legal name, if known and verified. |
| `identity_status` | enum | yes | yes (state machine) | `unverified`, `partially_verified`, `verified`, `disputed`, `suspended`. |
| `identity_refs` | EvidenceRef[] | yes | append-only | Evidence objects that underpin the current `identity_status`. |
| `registration` | RegistrationMetadata \| null | no | yes | Formal business registration details, if any. |
| `category` | string | yes | yes | Primary commercial category (e.g. `electronics`, `fmcg`, `logistics_provider`). Open enum per Specification layer. |
| `operating_markets` | string[] | yes | yes | ISO 3166-1 alpha-2 country codes where this Merchant operates. |
| `channels` | enum[] | yes | yes | How this Merchant transacts: `marketplace`, `social_commerce`, `direct`, `physical_retail`, `wholesale`. |
| `contact` | ContactMetadata \| null | no | yes | Operational contact information. Not for identity verification. |
| `commercial_profile_ref` | UUID \| null | no | yes | Pointer to the active Knowledge object summarizing this Merchant's commercial behavior. |
| `trust_score_ref` | UUID \| null | no | yes | Pointer to the active Trust object for this Merchant. |
| `risk_score_ref` | UUID \| null | no | yes | Pointer to the active Risk object for this Merchant. |
| `organization_ref` | UUID \| null | no | yes | Parent Organization, if this Merchant operates under one. |
| `linked_merchants` | UUID[] | no | append-only | Other Merchant IDs believed to be operated by the same entity (identity clustering output). |
| `status` | enum | yes | yes (state machine) | `active`, `inactive`, `suspended`, `deregistered`. |
| `flags` | Flag[] | no | append-only | Active compliance, fraud, or quality flags on this Merchant. |
| `created_at` | timestamp | yes | no | When this Merchant record was first created in SALAM. |
| `last_activity_at` | timestamp \| null | no | yes | When the most recent Evidence was collected about this Merchant. |
| `version` | integer | yes | no | Monotonically increasing per `merchant_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Archived, never deleted. |

## Identity Rule

A Merchant record is created when the system first encounters a commercial
actor — even with minimal information. Identity verification is a continuous
process, not a gate.

- `identity_status` starts at `unverified` and transitions as validating
  Evidence is collected and linked via `identity_refs`.
- `identity_status: verified` requires at least one Evidence object of
  `claim_type: identity_document` with `validation_status: validated` and
  confidence above the threshold defined in the Identity Verification
  Specification (Specification layer concern).
- `disputed` means conflicting Evidence exists about this Merchant's identity.
  The system flags it but does not resolve it unilaterally — resolution
  requires a governance decision.
- `linked_merchants` is the output of the Identity Resolution engine, which
  clusters Merchants believed to be the same real-world entity operating under
  different records. This is append-only; de-linking requires a governed
  correction process.

## Status State Machine

```
active ⇄ inactive
active → suspended → active | deregistered
```

- **active**: operating normally, Evidence collection is live.
- **inactive**: no recent activity, but not deliberately stopped.
- **suspended**: flagged by compliance, fraud detection, or governance. All
  downstream Decisions affecting this Merchant must acknowledge the suspension.
- **deregistered**: Merchant has formally exited. Record is retained, archived.

## Flags (`Flag`)

Flags are append-only signals attached to a Merchant by engines or governance
processes. They do not directly alter status but are inputs to Trust, Risk,
and Decision.

| Field | Type | Description |
|---|---|---|
| `flag_id` | UUID | Unique flag identifier. |
| `flag_type` | string | e.g. `fraud_suspicion`, `compliance_hold`, `data_quality`, `identity_conflict`. |
| `raised_by` | string | Engine or governance actor that raised the flag. |
| `raised_at` | timestamp | When the flag was raised. |
| `evidence_ref` | UUID \| null | Supporting Evidence, if applicable. |
| `resolved_at` | timestamp \| null | When the flag was resolved. Null = still active. |
| `resolution_note` | string \| null | How it was resolved. |

## Registration (`RegistrationMetadata`)

| Field | Type | Description |
|---|---|---|
| `country` | string | ISO 3166-1 alpha-2. |
| `registration_number` | string | Official registration number. |
| `registration_type` | string | e.g. `sole_trader`, `llc`, `cooperative`, `informal`. |
| `registered_at` | date | Date of registration. |
| `evidence_ref` | UUID | Evidence object verifying this registration. |

## Relationship to Other Kernel Entities

- **Evidence**: Evidence is collected *about* a Merchant, referenced via `subject_ref`. A Merchant's `identity_refs` are a subset of Evidence objects specifically supporting identity.
- **Knowledge**: The `commercial_profile_ref` points to a Knowledge object that summarizes what is currently understood about this Merchant's behavior, capabilities, and reliability.
- **Organization**: A Merchant may belong to a parent Organization via `organization_ref`. An Organization groups Merchants; Merchants are the leaf nodes.
- **Transaction / Event**: Transactions and Events reference the Merchants involved. Merchants do not directly contain Transaction or Event records.
- **Trust / Risk**: A Merchant is the subject of Trust and Risk assessments, referenced by `trust_score_ref` and `risk_score_ref`. These are computed objects — Merchant does not compute them, it points to them.
- **Relationship**: Merchant-to-Merchant and Merchant-to-Organization connections are modeled in the Relationship entity, not inline here.
- **Decision**: Decisions affecting a Merchant reference the Merchant's `merchant_id`. The Merchant entity does not contain Decisions.

## Explicit Non-Goals

A Merchant is **not**:
- A user account or authentication identity — those are platform/product concerns.
- A container for transactions — Transactions reference Merchants, not the reverse.
- A static record — a Merchant's understanding evolves continuously as Evidence is collected.
- Guaranteed to map 1:1 to a legal entity — one legal entity may operate multiple Merchants; `linked_merchants` handles the clustering.

## Open Questions (tracked, not yet resolved)

1. **Identity verification threshold**: exact confidence threshold for `identity_status: verified` is a Specification-layer concern. Needs an ADR.
2. **Merchant deduplication strategy**: when the Identity Resolution engine detects two Merchant records are the same entity, how is the canonical record chosen and the duplicate archived? Governance layer concern.
3. **Informal/unregistered merchants**: a large share of emerging market merchants have no formal registration. The model accommodates this (`registration` is optional, `registration_type: informal` is valid) but the downstream implications for Trust scoring need an ADR.
4. **Flag lifecycle governance**: who has authority to resolve a `fraud_suspicion` flag vs. a `compliance_hold`? Governance layer concern.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
