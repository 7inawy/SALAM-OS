# SALAM-OS

SALAM Operating System.

This repository is the single source of truth for the architecture of SALAM, a Commercial Decision Intelligence Network.

## Kernel
The kernel contains the immutable architectural foundations. All specifications, products, and implementation artifacts derive from the kernel.

Kernel modules:
- `kernel/principles/` — first principles, founder philosophy, governance philosophy
- `kernel/ontology/` — canonical entity definitions
- `kernel/system-model/` — engines, lifecycles, conceptual flow
- `kernel/architecture-map/` — layer dependencies, build order

Each entity in `kernel/ontology/` is defined twice, intentionally:
- `<entity>.md` — canonical human-readable definition (authoritative)
- `<entity>.schema.json` — machine-parseable JSON Schema mirroring the `.md` (must stay in sync)

### Ontology Status

| Entity | Status |
|---|---|
| Evidence | ✅ [`kernel/ontology/evidence.md`](kernel/ontology/evidence.md) |
| Knowledge | ✅ [`kernel/ontology/knowledge.md`](kernel/ontology/knowledge.md) |
| Merchant | ✅ [`kernel/ontology/merchant.md`](kernel/ontology/merchant.md) |
| Organization | ✅ [`kernel/ontology/organization.md`](kernel/ontology/organization.md) |
| Event | ✅ [`kernel/ontology/event.md`](kernel/ontology/event.md) |
| Transaction | ✅ [`kernel/ontology/transaction.md`](kernel/ontology/transaction.md) |
| Relationship | ✅ [`kernel/ontology/relationship.md`](kernel/ontology/relationship.md) |
| Graph | ✅ [`kernel/ontology/graph.md`](kernel/ontology/graph.md) |
| Trust | ✅ [`kernel/ontology/trust.md`](kernel/ontology/trust.md) |
| Risk | ✅ [`kernel/ontology/risk.md`](kernel/ontology/risk.md) |
| Commercial Intelligence | deferred |
| Decision | deferred |
| Outcome | deferred |
| Objective | deferred |
| Policy | deferred |

## Repository Layout

```
kernel/                 canonical models — authoritative
  principles/
  ontology/
  system-model/
  architecture-map/
adr/                    Architectural Decision Records
specifications/         APIs, schemas, business rules derived from kernel
products/               applications
docs/                   generated documentation — disposable, never authoritative
```

## Working Rules

- Dependencies flow downward only: `kernel` → `specifications` → `products` → `docs`
- No generated artifact is ever a source of truth
- Every irreversible architectural decision gets an ADR before implementation
- Evidence is immutable and append-only — the pattern all other ontology entities follow

### Principles Status

| Principle | Status |
|---|---|
| Evidence-First | ✅ [`kernel/principles/evidence-first.md`](kernel/principles/evidence-first.md) |
| Immutability | ✅ [`kernel/principles/immutability.md`](kernel/principles/immutability.md) |
| Event-Driven Architecture | ✅ [`kernel/principles/event-driven-architecture.md`](kernel/principles/event-driven-architecture.md) |
| Explainability | ✅ [`kernel/principles/explainability.md`](kernel/principles/explainability.md) |
| Dependency Direction | ✅ [`kernel/principles/dependency-direction.md`](kernel/principles/dependency-direction.md) |

### Engine Specifications Status

| Engine | Status |
|---|---|
| Evidence Engine | ✅ [`specifications/engines/evidence-engine.md`](specifications/engines/evidence-engine.md) |
| Knowledge Engine | ✅ [`specifications/engines/knowledge-engine.md`](specifications/engines/knowledge-engine.md) |
| Graph Engine | ✅ [`specifications/engines/graph-engine.md`](specifications/engines/graph-engine.md) |
| Trust Engine | ✅ [`specifications/engines/trust-engine.md`](specifications/engines/trust-engine.md) |
| Risk Engine | ✅ [`specifications/engines/risk-engine.md`](specifications/engines/risk-engine.md) |
| Reasoning Engine | ✅ [`specifications/engines/reasoning-engine.md`](specifications/engines/reasoning-engine.md) |
| Decision Engine | ✅ [`specifications/engines/decision-engine.md`](specifications/engines/decision-engine.md) |
