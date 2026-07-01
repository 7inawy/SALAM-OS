# Kernel · Ontology · Organization

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Knowledge, Merchant
Depended on by: Relationship, Trust, Risk, Decision

## Definition

An Organization is a legal, commercial, or institutional entity that owns,
controls, or governs one or more Merchants within SALAM's operating context.
It is the structural layer above the Merchant — where a Merchant is a single
commercial actor at the point of trade, an Organization is the entity behind
it.

Organizations include: registered companies, holding groups, cooperatives,
NGOs, government bodies, financial institutions, logistics operators, and any
other non-individual actor that participates in or is subject to commercial
intelligence operations.

An Organization does not trade directly in SALAM's model — it owns or governs
Merchants that do. However, Organizations are themselves subjects of Evidence
collection and Knowledge derivation, particularly for group-level risk,
compliance, and ownership intelligence.

A single Organization may control many Merchants. A single Merchant belongs to
at most one Organization (or none, if it is an independent operator).

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `organization_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `display_name` | string | yes | yes | Common operating name. |
| `legal_name` | string \| null | no | yes | Registered legal name. |
| `organization_type` | enum | yes | yes | `company`, `holding_group`, `cooperative`, `financial_institution`, `logistics_operator`, `government_body`, `ngo`, `other`. |
| `identity_status` | enum | yes | yes (state machine) | `unverified`, `partially_verified`, `verified`, `disputed`, `suspended`. |
| `identity_refs` | EvidenceRef[] | yes | append-only | Evidence underpinning `identity_status`. |
| `registration` | RegistrationMetadata \| null | no | yes | Formal registration details. |
| `operating_markets` | string[] | yes | yes | ISO 3166-1 alpha-2 country codes. |
| `merchant_refs` | UUID[] | no | append-only | Merchant IDs owned or controlled by this Organization. |
| `parent_organization_ref` | UUID \| null | no | yes | Parent Organization, for hierarchical group structures. |
| `subsidiary_refs` | UUID[] | no | append-only | Child Organization IDs, if any. |
| `commercial_profile_ref` | UUID \| null | no | yes | Active Knowledge object summarizing this Organization's group-level commercial behavior. |
| `trust_score_ref` | UUID \| null | no | yes | Active Trust object for this Organization. |
| `risk_score_ref` | UUID \| null | no | yes | Active Risk object for this Organization. |
| `beneficial_owners` | BeneficialOwner[] | no | yes | Known beneficial owners (natural persons or entities). Governance-sensitive. |
| `flags` | Flag[] | no | append-only | Compliance, fraud, or quality flags at the organization level. |
| `status` | enum | yes | yes (state machine) | `active`, `inactive`, `suspended`, `dissolved`. |
| `created_at` | timestamp | yes | no | When this Organization record was first created. |
| `last_activity_at` | timestamp \| null | no | yes | When the most recent Evidence was collected about this Organization. |
| `version` | integer | yes | no | Monotonically increasing per `organization_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Ownership and Hierarchy Rule

An Organization can be part of a hierarchy:

```
Organization (parent / holding group)
  └── Organization (subsidiary)
        └── Merchant
        └── Merchant
  └── Merchant (direct)
```

- `parent_organization_ref` and `subsidiary_refs` model the hierarchy.
  Both are maintained together — adding a child sets both ends of the link.
- Circular hierarchies are prohibited. The graph must remain a DAG.
- Risk and Trust propagate up and down the hierarchy per rules defined in the
  Risk and Trust Specification layers — the Kernel does not specify the
  propagation function, only that the structure exists.
- A Merchant's `organization_ref` and the parent Organization's
  `merchant_refs` must be kept consistent. This is an integrity constraint,
  enforced at the engine layer.

## Beneficial Ownership (`BeneficialOwner`)

Beneficial ownership is the relationship between an Organization and the
natural persons or entities that ultimately own or control it. It is
governance-sensitive: incomplete or falsified beneficial ownership data is
itself a risk signal.

| Field | Type | Description |
|---|---|---|
| `owner_id` | UUID | Unique identifier for this ownership record. |
| `owner_type` | enum | `natural_person`, `legal_entity`. |
| `display_name` | string | Name of the owner. |
| `ownership_percentage` | float \| null | Percentage ownership, if known. |
| `control_type` | string | e.g. `direct_shareholder`, `beneficial_owner`, `director`, `authorized_signatory`. |
| `evidence_ref` | UUID \| null | Evidence supporting this ownership record. |
| `verified` | boolean | Whether this ownership claim has been verified via Evidence. |

## Status State Machine

```
active ⇄ inactive
active → suspended → active | dissolved
```

- **active**: organization is operating, Evidence collection is live.
- **inactive**: no recent commercial activity.
- **suspended**: governance or compliance hold. All Merchants under this
  Organization inherit a suspension signal — they are not automatically
  suspended, but their risk profile must reflect it.
- **dissolved**: formally wound up. Record retained and archived.

## Identity Rule

Identical to Merchant, but at the organizational level:

- `identity_status` begins at `unverified`.
- `verified` requires at least one Evidence object of a qualifying
  `claim_type` (e.g. `company_registration`, `regulatory_filing`) with
  `validation_status: validated` above the threshold defined in the
  Identity Verification Specification.
- `disputed` means conflicting Evidence about ownership or legal status exists.
- Suspension at the Organization level does not automatically cascade to
  `identity_status: suspended` — these are independent state machines.

## Relationship to Other Kernel Entities

- **Evidence**: Evidence is collected about Organizations, referencing
  `organization_id` as `subject_ref`. `identity_refs` are the subset
  specifically supporting identity.
- **Knowledge**: `commercial_profile_ref` points to the active Knowledge
  object for this Organization's group-level behavior.
- **Merchant**: An Organization owns or controls Merchants via `merchant_refs`.
  Merchants are the leaf actors; Organizations are their structural containers.
- **Trust / Risk**: Organizations have their own Trust and Risk scores,
  distinct from (but influenced by) the scores of the Merchants they control.
- **Relationship**: Inter-organizational relationships (partnerships, supplier
  links, financial exposure) are modeled in the Relationship entity.
- **Decision**: Decisions may target an Organization directly (e.g. a
  compliance hold on a group) or propagate to it from Merchant-level Decisions.

## Explicit Non-Goals

An Organization is **not**:
- A user account or authentication identity.
- A direct trading entity — Merchants trade, Organizations own or govern.
- A flat record — Organizations can be deeply hierarchical; the model
  explicitly supports multi-level group structures.
- Always formally registered — `registration` is optional; informal
  organizational structures are accommodated.

## Open Questions (tracked, not yet resolved)

1. **Risk and Trust propagation across hierarchy**: how do Organization-level
   scores aggregate from Merchant scores, and how do they propagate downward?
   Specification layer concern. Needs an ADR.
2. **Beneficial ownership verification threshold**: what Evidence is sufficient
   to mark a beneficial ownership claim as `verified`? Governance-sensitive.
   Needs an ADR.
3. **Circular hierarchy detection**: enforcing DAG integrity on the
   Organization hierarchy is an engine constraint. How is it enforced at
   ingestion time vs. query time? Architecture layer concern.
4. **Suspension cascade**: when an Organization is suspended, what signals
   (not automatic state changes) propagate to its Merchants? Needs an ADR.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
