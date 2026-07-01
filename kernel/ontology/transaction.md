# Kernel · Ontology · Transaction

Status: Canonical
Layer: Kernel (Layer 1)
Depends on: Evidence, Event, Merchant, Organization
Depended on by: Relationship, Knowledge, Trust, Risk, Commercial Graph

## Definition

A Transaction is a financially-settled commercial exchange between two or
more parties, documented by Evidence and modeled as a specific subtype of
Event. It represents the moment where commercial commitment becomes financial
reality — money moves, goods change hands, or an obligation is formally
discharged.

Transactions are the highest-density Evidence generators in the system. A
single transaction typically produces multiple Evidence objects: payment
confirmation, delivery receipt, counterparty acknowledgement, and so on.
Cumulatively, Transactions form the evidential backbone of Trust and Risk
assessments.

A Transaction is not every Event — it is specifically the subset where
financial settlement occurs or is explicitly attempted. A dispute, a
registration, a fraud report — these are Events but not Transactions. A
payment, an escrow release, a goods purchase — these are Transactions.

Every Transaction must reference a parent Event. Transactions do not exist
independently of Events.

## Properties

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `transaction_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `event_ref` | UUID | yes | no | The parent Event this Transaction is part of. Required. |
| `transaction_type` | enum | yes | no | Classification. See Transaction Types below. |
| `initiated_at` | timestamp | yes | no | When the transaction was initiated by a participant. |
| `settled_at` | timestamp \| null | no | yes (set once) | When financial settlement occurred. Null until settled. |
| `parties` | Party[] | yes | no | Payer and payee (or equivalent). Minimum two. |
| `value` | MonetaryValue | yes | no | The financial value of the transaction. |
| `currency` | string | yes | no | ISO 4217 currency code. |
| `settlement_currency` | string \| null | no | no | Currency in which settlement actually occurred, if different from `currency`. |
| `exchange_rate` | float \| null | no | no | Exchange rate applied at settlement, if currencies differ. |
| `payment_method` | string | yes | no | e.g. `mobile_money`, `bank_transfer`, `cash_on_delivery`, `escrow`, `bnpl`, `card`. |
| `platform_ref` | string \| null | no | no | The marketplace or platform through which this transaction was routed, if any. |
| `status` | enum | yes | yes (state machine) | `initiated`, `processing`, `held`, `completed`, `failed`, `reversed`, `disputed`. |
| `status_reason` | string \| null | no | yes | Reason for the current status, required for `failed`, `reversed`, `disputed`. |
| `evidence_refs` | UUID[] | yes | append-only | Evidence objects documenting this Transaction. Minimum one. |
| `escrow_ref` | UUID \| null | no | no | Escrow record ID if this transaction is under escrow governance. |
| `dispute_ref` | UUID \| null | no | yes (set once) | Event ID of the dispute, if this Transaction is disputed. |
| `flags` | Flag[] | no | append-only | Compliance, fraud, or quality flags. |
| `market` | string | yes | no | ISO 3166-1 alpha-2 country code where the Transaction originated. |
| `created_at` | timestamp | yes | no | When this Transaction record was created. |
| `version` | integer | yes | no | Monotonically increasing per `transaction_id` lineage. |
| `archived` | boolean | yes | yes (one-way: false→true) | Never deleted. |

## Transaction Types

| Type | Description |
|---|---|
| `purchase` | Buyer pays seller for goods or services. |
| `escrow_deposit` | Funds deposited into escrow pending condition fulfillment. |
| `escrow_release` | Escrow funds released to beneficiary on condition fulfillment. |
| `escrow_refund` | Escrow funds returned to depositor on condition failure. |
| `transfer` | Direct value transfer between parties without escrow. |
| `refund` | Return of funds from seller to buyer after a completed purchase. |
| `reversal` | System-initiated unwinding of a prior transaction. |
| `fee` | Platform or service fee charged to a participant. |
| `settlement_batch` | Aggregated settlement of multiple sub-transactions. |

Additional types are Specification-layer extensions.

## Parties (`Party`)

| Field | Type | Description |
|---|---|---|
| `party_id` | UUID | Merchant ID or Organization ID. |
| `party_type` | enum | `merchant`, `organization`. |
| `role` | enum | `payer`, `payee`, `escrow_agent`, `guarantor`, `platform`. |
| `account_ref` | string \| null | Payment account or wallet identifier, if known. |

Minimum two parties per Transaction (payer + payee). Escrow transactions will
have a third party: the `escrow_agent`.

## Monetary Value (`MonetaryValue`)

| Field | Type | Description |
|---|---|---|
| `amount` | number | Transaction amount in `currency`. Must be positive. |
| `fee_amount` | number \| null | Platform or processing fee, if separately tracked. |
| `net_amount` | number \| null | Amount after fees. |

All monetary values are stored as numbers in the declared `currency`. Floating-
point precision rules are a Specification-layer concern — the Kernel requires
only that amounts are positive and currency is declared.

## Status State Machine

```
initiated → processing → completed
                       → failed
                       → reversed
          → held       → completed (hold lifted, settlement proceeds)
                       → failed    (hold results in failure)
                       → reversed
          → disputed   → completed (dispute resolved in payee's favour)
                       → reversed  (dispute resolved in payer's favour)
```

- **initiated**: transaction created, settlement not yet started.
- **processing**: settlement in progress.
- **held**: funds or obligation held pending a condition (e.g. escrow, compliance check).
- **completed**: settlement confirmed.
- **failed**: settlement did not complete.
- **reversed**: a completed transaction was unwound.
- **disputed**: a participant has raised a dispute; outcome pending.

`status_reason` is required whenever `status` is `failed`, `reversed`, or
`disputed`. It is immutable once set for terminal states.

## Relationship to Other Kernel Entities

- **Event**: Every Transaction references a parent Event via `event_ref`.
  Transaction is a financially-settled subtype of Event. A Transaction cannot
  exist without a parent Event.
- **Evidence**: Transactions require at least one Evidence object at creation.
  Evidence is appended as the transaction progresses (e.g. payment confirmation
  arrives after initiation). Evidence refs are never removed.
- **Merchant / Organization**: Transactions involve Merchants and Organizations
  as `parties`. They are the commercial actors exchanging value.
- **Knowledge**: Cumulative Transaction patterns (volume, frequency, completion
  rate, dispute rate) are aggregated into Knowledge objects about Merchants
  and Organizations.
- **Trust / Risk**: Transaction history is the primary evidential input into
  Trust and Risk scoring. Completion rates, reversal rates, dispute frequency,
  and payment method patterns all feed directly into these assessments.
- **Relationship**: Recurring Transactions between the same parties establish
  and update the Relationship entity between them.
- **Commercial Graph**: Transaction parties become nodes; transactions become
  weighted edges in the Commercial Graph.

## Explicit Non-Goals

A Transaction is **not**:
- A general Event — all Transactions are Events, but not all Events are
  Transactions. Disputes, registrations, and verifications are Events,
  not Transactions.
- An accounting ledger entry — Transactions are commercial intelligence
  records, not a double-entry bookkeeping system.
- A real-time payment processor — SALAM records and reasons about Transactions;
  it does not execute them.
- Editable after creation — status transitions and Evidence appends are the
  only permitted mutations.

## Open Questions (tracked, not yet resolved)

1. **Monetary precision**: integer (smallest currency unit, e.g. piastres) vs.
   decimal representation — financial precision requirements vary by market.
   Specification layer concern. Needs an ADR.
2. **Multi-currency settlement tracking**: for cross-border transactions with
   intermediary currencies, a single `exchange_rate` field is insufficient.
   Specification layer concern. Needs an ADR.
3. **Escrow integration depth**: how tightly coupled is the escrow lifecycle
   to the Transaction status state machine? The `escrow_ref` field acknowledges
   the relationship but does not model it. Architecture concern. Needs an ADR.
4. **Batch transactions**: `settlement_batch` type implies sub-transactions.
   The parent/child relationship between batch and constituent transactions is
   not modeled in the Kernel. Needs an ADR.

---
*This file is Kernel content per Architectural Layer 1. It is authoritative. Specifications, products, and generated documentation derive from it — never the reverse.*
