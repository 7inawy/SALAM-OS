# Kernel · Principles · Event-Driven Architecture

Status: Canonical
Layer: Kernel (Layer 1)

## Statement

Every state change in the system is the result of an event. No component
reaches into another component's state directly. State changes are published
as events, consumed by interested parties, and processed asynchronously.
The event log is the system of record.

## What This Means in Practice

**Events are the source of truth.** The current state of any entity (a
Merchant's Trust score, a Transaction's status, a Relationship's strength)
is derived by replaying the events that affected it. The event log is
permanent and append-only — consistent with the Immutability principle.

**No direct state mutation across components.** The Evidence Engine does not
directly update a Merchant record. It publishes an `evidence.validated` event.
The Knowledge Engine consumes that event and may publish `knowledge.updated`.
The Trust Engine consumes that and publishes `trust.recomputed`. Each engine
owns its own state; no engine writes to another engine's store.

**Every significant occurrence produces an event.** Evidence ingestion,
validation, rejection. Knowledge derivation, staleness, retraction.
Trust recomputation. Risk flag raised or resolved. Transaction status
transitions. All of these are events in the system's event stream —
not side effects of API calls.

**Downstream consumers are decoupled.** When a new Evidence object is
validated, the Trust Engine, the Risk Engine, the Knowledge Engine, and
the Commercial Graph all need to react. None of them are called directly.
They each subscribe to `evidence.validated` and process it independently,
at their own pace, without blocking each other.

**The event log enables temporal queries.** Because state is derived from
events, it is possible (in principle) to reconstruct the state of any entity
at any prior point in time by replaying the event log up to that timestamp.
This is what makes historical Decision explainability possible — you can
show exactly what the system knew at the moment a Decision was made.

## Core Event Categories

These are the event categories the system produces. Specific event types
within each category are defined in the Engine Specifications.

| Category | Examples |
|---|---|
| `evidence.*` | `evidence.ingested`, `evidence.validated`, `evidence.rejected`, `evidence.superseded` |
| `knowledge.*` | `knowledge.derived`, `knowledge.stale`, `knowledge.retracted` |
| `merchant.*` | `merchant.created`, `merchant.identity_status_changed`, `merchant.suspended` |
| `organization.*` | `organization.created`, `organization.suspended`, `organization.dissolved` |
| `transaction.*` | `transaction.initiated`, `transaction.completed`, `transaction.disputed`, `transaction.reversed` |
| `event.*` | `commercial_event.recorded`, `commercial_event.outcome_resolved` |
| `relationship.*` | `relationship.formed`, `relationship.strength_updated`, `relationship.terminated` |
| `trust.*` | `trust.initialized`, `trust.recomputed`, `trust.suspended`, `trust.revoked` |
| `risk.*` | `risk.initialized`, `risk.recomputed`, `risk.escalated`, `risk.resolved` |
| `decision.*` | `decision.requested`, `decision.produced`, `decision.executed`, `decision.outcome_recorded` |
| `graph.*` | `graph.node_added`, `graph.edge_added`, `graph.edge_updated` |

## What This Rules Out

- Synchronous cross-engine calls that create tight coupling or cascade
  failures — engines communicate via events, not direct calls.
- In-place state mutation that bypasses the event log — all state changes
  must produce an event.
- Event retraction — events, like Evidence, are immutable. A corrective
  action produces a new corrective event, not a deletion of the prior one.
- Polling as a primary integration pattern — consumers subscribe to events;
  they do not poll for state changes.

## Implementation Note (Architecture Layer Concern)

The choice of event streaming technology (Kafka, Kinesis, Pulsar, etc.),
event schema format, delivery guarantees (at-least-once vs. exactly-once),
and consumer group design are Architecture layer decisions. This principle
defines the pattern — not the implementation. An ADR is required before
any streaming technology is selected.

## Relationship to Other Principles

- **Immutability** and Event-Driven Architecture are mutually reinforcing:
  immutable records flow as events; events produce immutable records.
- **Evidence-First** is implemented via events — Evidence ingestion is an
  event that triggers the entire downstream processing chain.
- **Explainability** is made possible by the event log — historical state
  reconstruction requires a complete, ordered event record.
- **Dependency Direction** is enforced structurally by event-driven design —
  the Kernel emits events; products consume them. Products cannot publish
  events that mutate Kernel entities.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative.*
