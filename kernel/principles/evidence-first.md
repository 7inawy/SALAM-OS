# Kernel · Principles · Evidence-First

Status: Canonical
Layer: Kernel (Layer 1)

## Statement

Evidence precedes trust. Every assertion about a commercial actor, every score,
every decision, and every recommendation produced by SALAM must be traceable
to at least one validated Evidence object. The system does not accept claims —
it accepts observations.

## What This Means in Practice

**No score without evidence.** Trust scores, Risk scores, and Knowledge objects
cannot be initialized without at least one validated Evidence object backing
them. A Merchant record can be created with zero Evidence (the system must
accommodate discovery), but no computed output — Trust, Risk, Knowledge — can
be produced until Evidence exists.

**No assertion without attribution.** Every piece of information in the system
must carry its source. Who observed it, how, when, and through what method.
Unattributed information is not admitted.

**Confidence tracks evidence quality.** The system's confidence in any
assessment is a function of the quality and volume of the Evidence beneath it.
Sparse evidence → low confidence. High-quality, corroborated evidence → high
confidence. Confidence is not a label applied after the fact; it is computed
from Evidence properties.

**Corrections via supersession, not mutation.** When evidence is wrong, the
correction is a new Evidence object that supersedes the prior one. The original
observation is retained. The system's history is never rewritten.

**Explainability is not optional.** Because every output traces to Evidence,
every output can be explained. "This Merchant's Trust score is 0.72 because
of 47 completed deliveries, 3 verified identity documents, and 0 defaults in
the past 12 months" is not a feature — it is a requirement. A score that
cannot be explained back to Evidence is inadmissible.

## What This Rules Out

- Manually assigned Trust or Risk scores with no Evidence backing.
- "Blacklist" or "whitelist" mechanisms that operate independently of Evidence.
- Importing third-party scores or ratings as authoritative without treating
  them as Evidence (with appropriate confidence and provenance metadata).
- Any engine output that cannot be traced to specific Evidence objects.

## Relationship to Other Principles

This principle is the root. Every other principle either derives from it
or exists to protect it:

- **Immutability** protects the integrity of Evidence once captured.
- **Event-Driven Architecture** ensures Evidence flows through the system
  without loss or mutation.
- **Explainability** is the runtime expression of this principle — the
  ability to answer "why?" for any output.
- **Dependency Direction** ensures that Evidence (Kernel) is never
  contaminated by concerns from lower layers (products, generated artifacts).

---
*This file is Kernel content per Architectural Layer 1. It is authoritative.*
