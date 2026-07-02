# Kernel · Principles · Explainability

Status: Canonical
Layer: Kernel (Layer 1)

## Statement

Every output the system produces — every score, every decision, every
recommendation — must be explainable back to the specific Evidence objects
that produced it. "The system said so" is never an acceptable answer.
If an output cannot be explained, it is inadmissible.

## What This Means in Practice

**Every score carries its drivers.** Trust and Risk objects include
`evidence_weight.primary_drivers` — the specific Evidence and Knowledge
objects that most influenced the score, with their contribution weights.
This is not optional metadata. It is a required field.

**Every Decision cites its inputs.** A Decision object must reference the
Trust object, Risk object, and Knowledge objects it consumed. A Decision
made without citing its evidential basis is rejected by the Decision Engine.

**Explanations have two levels.** Machine-readable (structured references
to Evidence IDs, contribution weights, dimension scores) for downstream
engines and APIs. Human-readable (natural language summaries derived from
the structured data) for operators, merchants, and counterparties. Both
are required. The human-readable layer is generated from the machine-readable
layer — never written independently.

**Historical explainability is preserved.** Because Evidence is immutable
and the event log is permanent, it is always possible to reconstruct exactly
what the system knew at the time a Decision was made, and why it decided
what it decided. This is not just useful — in regulated contexts, it is
mandatory.

**Confidence is explicit.** When the system has sparse or low-quality
Evidence, it says so. A Trust score of 0.65 with a confidence of 0.30
means something very different from a Trust score of 0.65 with a confidence
of 0.95. Both the score and the confidence are always surfaced together.
Never one without the other.

**Adverse decisions must be explainable to the affected party.** When a
Merchant is declined, suspended, or flagged, they are entitled to understand
why — at a level of detail appropriate to the context. Producing this
explanation is not a product feature; it is a Kernel-level requirement that
every engine must support.

## Explanation Components

Any explanation produced by the system must be reconstructable from these
components:

| Component | Description |
|---|---|
| **Primary drivers** | The specific Evidence or Knowledge objects with the highest contribution to the output. |
| **Dimension breakdown** | For Trust and Risk: what each dimension scored and why. |
| **Evidence quality** | The quality and recency of the underlying Evidence. |
| **Confidence** | How confident the system is in the output, given the evidence volume and quality. |
| **Counterfactual** | What would need to change for the output to be different (optional, but required for adverse decisions). |

## What This Rules Out

- Black-box scoring models whose outputs cannot be traced to specific Evidence.
- Scores produced by models that cannot expose feature importances at the
  Evidence level.
- Decisions that cite only a score without the underlying evidential basis.
- Producing human-readable explanations that are disconnected from the
  actual machine-readable computation — summaries must be derived from
  the structured data, not written separately.

## Note on ML Models

Machine learning models may be used in scoring engines (Trust, Risk, Knowledge
inference). When they are, the model must expose Evidence-level feature
importances. A model that produces a score but cannot attribute it to specific
Evidence objects violates this principle and is inadmissible in the production
stack, regardless of its accuracy. Model selection is an Architecture/
Specification concern — this principle constrains what models are eligible.

## Relationship to Other Principles

- **Evidence-First** is the precondition — you can only explain outputs in
  terms of Evidence if Evidence was the input.
- **Immutability** enables historical explainability — you can explain past
  decisions because the Evidence they relied on still exists unchanged.
- **Event-Driven Architecture** makes the explanation timeline reconstructable —
  the event log shows exactly when each Evidence object arrived and how it
  changed each score.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative.*
