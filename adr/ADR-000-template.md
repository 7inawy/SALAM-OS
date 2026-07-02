# ADR Template

Use this template for every Architectural Decision Record.
Copy it, rename it `ADR-NNN-short-title.md`, fill it in.

ADRs are immutable once status is `accepted`. If a decision is reversed,
a new ADR supersedes the prior one — the original is never edited.

---

# ADR-NNN: [Title]

Date: YYYY-MM-DD
Status: `draft` | `accepted` | `superseded` | `rejected`
Supersedes: ADR-NNN (if applicable)
Superseded by: ADR-NNN (if applicable)
Layer: `kernel` | `architecture` | `specification` | `product`
Decider: [name or role]

## Context

What is the situation that requires a decision?
What constraints exist? What is at stake?
Be specific. Reference the spec or entity that surfaced this question.

## Decision

State the decision in one sentence. Then explain it.

## Alternatives Considered

### Option A: [name]
What it is. Why it was considered. Why it was not chosen.

### Option B: [name]
What it is. Why it was considered. Why it was not chosen.

## Rationale

Why this decision over the alternatives. What values or constraints it optimizes for.

## Consequences

### Positive
What this decision enables or simplifies.

### Negative / Trade-offs
What this decision costs or constrains. Be honest.

### Risks
What could go wrong. How those risks are mitigated.

## Dependencies

What must be true for this decision to hold.
What other decisions this one blocks or unblocks.

## Review Trigger

Under what conditions should this decision be revisited?
