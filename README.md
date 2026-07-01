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
| Commercial Intelligence | not started |
| Trust | not started |
| Risk | not started |
| Decision | not started |
| Outcome | not started |
| Merchant | not started |
| Organization | not started |
| Event | not started |
| Relationship | not started |
| Graph | not started |
| Policy | not started |
| Objective | not started |

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
