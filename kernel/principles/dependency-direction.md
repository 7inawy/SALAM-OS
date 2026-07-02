# Kernel · Principles · Dependency Direction

Status: Canonical
Layer: Kernel (Layer 1)

## Statement

Dependencies flow in one direction only: downward. The Kernel defines
concepts that everything else depends on. Nothing in the Kernel depends
on anything outside it. A layer may only depend on layers above it in
the stack — never on layers below it, and never on its own layer peers
in ways that create cycles.

## The Stack

```
Kernel                    ← depends on nothing
  └── Architecture        ← depends on Kernel only
        └── Specifications ← depends on Kernel + Architecture
              └── Products  ← depends on Kernel + Architecture + Specifications
                    └── Generated Artifacts ← depend on everything above; authoritative over nothing
```

## What Each Layer Is Responsible For

**Kernel**: Canonical entity definitions, first principles, system model.
What things are, what they mean, what invariants must hold everywhere.
The Kernel is the single source of truth for concepts.

**Architecture**: Technology choices, engine designs, infrastructure patterns,
event streaming topology, database selection. How the system is built.
Architecture decisions are recorded as ADRs before implementation.

**Specifications**: Concrete APIs, business rules, scoring formulas, SLAs,
product flows. What each engine accepts as input and produces as output,
in enough detail that a developer can implement it without interpretation.

**Products**: User-facing applications, integrations, dashboards, SDKs.
Products implement Specifications; they do not define their own concepts
or override Kernel definitions.

**Generated Artifacts**: Documentation, client libraries, API references,
reports. Produced from the layers above. Disposable — they can always be
regenerated. Never authoritative. Never a source of truth.

## The Critical Constraint

**Generated documents do not constrain models.** If a product document,
API reference, or generated report says one thing and the Kernel says
another, the Kernel is correct and the generated document is stale.
The fix is to regenerate the document — not to update the Kernel to
match the document.

This is the most commonly violated constraint in systems that start with
documentation and work backward to models. SALAM starts with models and
generates documentation from them.

## Enforcement Rules

**No upward imports.** A Specification file may not define a concept that
contradicts or overrides a Kernel definition. If a Specification needs
a concept that doesn't exist in the Kernel, it either (a) proposes a
Kernel addition via the governance process, or (b) defines a
Specification-local extension that explicitly defers to the Kernel for
the core concept.

**No cross-layer peer dependencies.** Product A may not depend on the
internal implementation of Product B. Products depend on Specifications;
if two products share behavior, that behavior belongs in a Specification,
not in one product that the other imports.

**ADRs govern Architecture decisions.** Architecture choices that affect
multiple Specifications or that are difficult to reverse require an ADR.
ADRs reference Kernel concepts; Kernel concepts do not reference ADRs.

**Extensions are always additive.** Lower layers may add fields, add
event types, add API endpoints. They may never remove or redefine what
the Kernel has established. A Specification may say "in addition to the
Kernel Evidence fields, this API also accepts X" — it may not say "this
API uses a different definition of Evidence."

## Practical Test

For any file in the repository, ask: if I deleted everything in this file's
layer and below, would the layers above still be valid and complete?

- If yes: the dependency direction is correct.
- If no: something in a higher layer is depending on something in a lower
  layer, which is a violation.

The Kernel must pass this test against the empty set — it depends on nothing.

## Relationship to Other Principles

This principle governs the structure of the repository and the system.
The other four principles govern the behavior of the system at runtime.
Both matter equally — a system with correct runtime behavior but a corrupt
dependency structure will drift and become unmaintainable. A system with
correct structure but wrong runtime principles will produce untrustworthy
outputs.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative.*
