# Kernel · Principles · Immutability

Status: Canonical
Layer: Kernel (Layer 1)

## Statement

Commercial reality, once observed and recorded, is never erased. Evidence is
immutable. Events are immutable. Transactions are immutable. The system's
record of what happened is permanent — corrections happen by adding new
information, not by removing old information.

## What This Means in Practice

**Append-only observation records.** Evidence, Events, and Transactions are
written once and never edited. Fields that must change over time (status,
confidence, quality scores) are explicitly marked mutable in the Kernel
definitions. Everything else is frozen at creation.

**Supersession over mutation.** When an observation is wrong, a new object
is created with `supersedes` pointing to the prior one. The original is
retained with `archived: true`. Both exist permanently. The history of
corrections is part of the record.

**Deletion is not a system operation.** No engine, product, or governance
process deletes Evidence, Events, Transactions, or Relationships. `archived`
is the terminal state. Archived objects remain in storage and are queryable
for audit, regulatory, and dispute-resolution purposes.

**Provenance chains are append-only.** Every transformation applied to an
Evidence object — normalization, enrichment, re-scoring — appends an entry
to the provenance chain. Nothing is removed from it. The chain is the audit
trail of how raw observation became system knowledge.

**Flags are resolved, not removed.** When a compliance or fraud flag on a
Merchant is resolved, `resolved_at` and `resolution_note` are set. The flag
remains in the record. The history of flags and their resolutions is part of
the entity's permanent commercial record.

## Why This Matters for Emerging Markets

In contexts where documentation is sparse, institutions are weak, and trust
must be built from scratch, the integrity of the historical record is the
foundation of everything. A system that can silently edit or delete its own
history cannot be trusted. A counterparty cannot rely on a track record that
could be modified after the fact.

Immutability is not a technical constraint — it is a commercial integrity
guarantee. It is what makes SALAM's outputs defensible in a dispute, auditable
by a regulator, and trustworthy to a counterparty.

## What This Rules Out

- Editing any Evidence, Event, or Transaction field after creation (except
  explicitly mutable fields per the Kernel definitions).
- Deleting any record for any reason, including GDPR-style right-to-erasure
  requests — these require a governance process that adds a redaction marker,
  not a deletion. (Redaction mechanics are a governance layer concern and
  require an ADR.)
- Retroactively adjusting scores or outcomes without creating a new superseding
  object with a full provenance trail.
- Removing items from any append-only list (provenance chains, evidence_refs,
  flag lists, link lists).

## Relationship to Other Principles

- **Evidence-First** establishes what gets recorded. Immutability governs how
  it is kept.
- **Event-Driven Architecture** is the mechanism by which immutable records
  flow through the system — events are published, consumed, and stored;
  they are never retracted.
- **Explainability** depends on immutability — you can only explain a past
  decision if the Evidence that informed it still exists exactly as it was
  at the time of the decision.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative.*
