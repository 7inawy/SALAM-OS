# Specifications · Engines · Decision Engine

Status: Draft
Layer: Specifications (Layer 3)
Kernel dependencies: Trust, Risk, Knowledge, Evidence, Merchant, Organization
Upstream engines: Trust Engine, Risk Engine, Knowledge Engine, Graph Engine
Consumed by: Products (Escrow, Verification, Lending, Logistics)

## Purpose

The Decision Engine is the system's output layer. It consumes Trust, Risk,
and Knowledge assessments and produces structured, explainable Decisions in
response to product requests. It is the point where intelligence becomes action.

The Decision Engine does not generate intelligence — it consumes it. It does
not hold commercial data — it queries the engines above it. Its single
responsibility is: given a context and a question, produce the best available
Decision, explain it fully, and record it immutably.

## Responsibilities

1. **Receive** Decision requests from products.
2. **Resolve context** — determine which Trust, Risk, and Knowledge objects
   apply to the request.
3. **Apply decision rules** — evaluate the resolved assessments against
   the applicable Policy rules for the decision type.
4. **Produce** a structured Decision object with full evidential citation.
5. **Escalate** when Risk is critical or Trust/Risk conflict is unresolvable.
6. **Record** every Decision immutably, regardless of outcome.
7. **Accept outcome feedback** — when a Decision's real-world outcome is
   known, record it for the Learning Engine.

## Decision Request (Input Contract)

Products submit Decision requests via the Decision Engine API:

```json
{
  "request_id": "uuid",
  "decision_type": "string",
  "requestor": {
    "product": "string",
    "requestor_id": "string"
  },
  "subject_ref": {
    "entity_type": "merchant | organization",
    "entity_id": "uuid"
  },
  "context": {
    "transaction_value": "number | null",
    "transaction_value_band": "micro | small | medium | large",
    "market": "ISO 3166-1 alpha-2",
    "counterparty_ref": "uuid | null",
    "payment_method": "string | null",
    "product_type": "string | null"
  },
  "required_by": "ISO 8601 timestamp | null",
  "metadata": "object | null"
}
```

`required_by` signals urgency. Requests with a near `required_by` are
prioritized in the processing queue. If a Decision cannot be produced
before `required_by`, the engine returns a `timeout` Decision with the
best available partial assessment.

## Decision Types

| decision_type | Question answered | Primary consumers |
|---|---|---|
| `escrow_release` | Should escrowed funds be released to the merchant? | Escrow product |
| `escrow_refund` | Should escrowed funds be returned to the buyer? | Escrow product |
| `merchant_verification` | Should this merchant be marked as verified? | Verification product, platforms |
| `transaction_approval` | Should this transaction proceed? | Payment / marketplace integrations |
| `credit_eligibility` | Is this merchant eligible for credit / BNPL? | Lending product |
| `onboarding_approval` | Should this merchant be onboarded to a platform? | Platform integrations |
| `suspension_recommendation` | Should this merchant be suspended? | Governance queue |

Additional decision types are added via the Specification update process.

## Decision Resolution Pipeline

### Step 1 — Retrieve Assessments
For the given `subject_ref` and `context`, retrieve:
- Trust object (context-matched; fallback to closest match if exact unavailable)
- Risk object (context-matched)
- Relevant Knowledge objects for the `decision_type`

If Trust or Risk objects are `stale`, the engine proceeds but flags
`data_freshness: stale` in the Decision output.

If Trust or Risk objects are `suspended` / `revoked` / `escalated`:
- `escalated` Risk: produce an `escalated` Decision. Do not auto-approve.
  Route to governance queue.
- `revoked` Trust: produce a `declined` Decision automatically.
- `suspended` entities: produce a `declined` Decision automatically.

### Step 2 — Apply Policy Rules
Evaluate the retrieved assessments against the Policy rules for the
`decision_type`. Policy rules are defined per product in the Product
Specification layer (not in this engine spec).

The Decision Engine evaluates rules in the following sequence:

1. **Hard blocks** — automatic `declined` regardless of scores.
   Examples: entity `status: suspended`, Trust `status: revoked`,
   active `critical` Risk flag of type `sanctions_list_match`.

2. **Hard approvals** — automatic `approved` for clearly safe scenarios.
   Examples: `trust_score > 0.90` AND `risk_score < 0.10` AND no active
   Risk flags for `micro` value band.

3. **Scoring band evaluation** — for cases not caught by hard rules,
   evaluate Trust and Risk scores against the applicable band thresholds
   defined in the Product Specification.

4. **Conflict resolution** — when Trust is high and Risk is high:
   Risk takes precedence for `declined` decisions.
   The Decision cites both scores and explains the conflict.
   (Conflict resolution ADR required.)

5. **Escalation** — when the engine cannot produce a confident Decision
   (insufficient data, conflicting signals, critical escalated Risk),
   produce an `escalated` Decision and route to the governance queue.

### Step 3 — Produce Decision Object

```json
{
  "decision_id": "uuid",
  "request_id": "uuid",
  "decision_type": "string",
  "subject_ref": { "entity_type": "...", "entity_id": "uuid" },
  "outcome": "approved | declined | escalated | timeout",
  "confidence": "float [0,1]",
  "produced_at": "ISO 8601 timestamp",
  "context": { ... },
  "evidence": {
    "trust_ref": "uuid",
    "trust_score": "float",
    "trust_confidence": "float",
    "risk_ref": "uuid",
    "risk_score": "float",
    "risk_severity": "low | medium | high | critical",
    "knowledge_refs": ["uuid", ...],
    "active_risk_flags": ["flag_type", ...]
  },
  "explanation": {
    "summary": "string",
    "primary_drivers": [...],
    "rules_applied": ["rule_id", ...],
    "hard_block_triggered": "string | null",
    "conflict_noted": "boolean"
  },
  "policy_ref": "uuid",
  "outcome_recorded_at": "null",
  "outcome_feedback": "null"
}
```

### Step 4 — Persist and Publish
Every Decision is persisted immediately on production, regardless of outcome.
Decisions are immutable after creation. The `outcome_feedback` field is
populated later via the Outcome Feedback API.

Publish `decision.produced` to the event stream.

## Outcome Feedback API

When the real-world outcome of a Decision is known, products submit feedback:

```json
{
  "decision_id": "uuid",
  "outcome_type": "confirmed_correct | confirmed_incorrect | partial | unknown",
  "actual_outcome": "string",
  "feedback_at": "ISO 8601 timestamp",
  "feedback_source": "string"
}
```

This feedback is consumed by the Learning Engine (future specification)
to improve scoring models over time.

## Escalation Flow

When a Decision is `escalated`:
1. The Decision object is created with `outcome: escalated`.
2. `decision.escalated` event is published.
3. The governance queue receives the escalation with full Decision context.
4. A human operator reviews and produces a manual override Decision,
   referencing the original `decision_id`.
5. The manual Decision is recorded as a separate Decision object with
   `requestor.product: governance_console`.

Manual overrides are not silent — they are first-class Decision objects
in the immutable record.

## Output Events

| Event | Consumers |
|---|---|
| `decision.produced` | Product that requested it, Learning Engine, monitoring |
| `decision.escalated` | Governance queue, monitoring |
| `decision.outcome_recorded` | Learning Engine, monitoring |

## SLAs

| Operation | Target |
|---|---|
| Decision production (hard block / hard approval) | < 500ms p99 |
| Decision production (full scoring band evaluation) | < 2s p95, < 5s p99 |
| Decision production (escalated path) | < 3s p95 (to produce the escalated Decision; human review time excluded) |
| Outcome feedback recording | < 1s p99 |

## Open Questions (ADRs Required)

1. **Trust/Risk conflict resolution** — when both are high, how exactly does
   the engine decide? Risk-always-wins is a starting position; needs ADR.
2. **Policy rule format and storage** — are policy rules code, configuration,
   or a rules engine DSL? Who can edit them and how are changes governed?
3. **Scoring band thresholds** — what Trust/Risk score ranges map to
   `approved` / `escalated` / `declined` per `decision_type`? Defined in
   Product Specifications; this engine only enforces them.
4. **Timeout handling** — when `required_by` is breached, what partial
   Decision is safe to return? Needs explicit rules per `decision_type`.
5. **Manual override audit** — beyond recording as a Decision object, are
   manual overrides subject to additional governance review? Governance concern.

---
*This file is a Specification. It derives from and is constrained by the Kernel.*
