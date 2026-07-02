# Specifications · Products · Social Commerce Escrow

Status: Draft
Layer: Specifications (Layer 4)
Kernel dependencies: Evidence, Transaction, Event, Merchant, Trust, Risk, Decision
Engine dependencies: Evidence Engine, Trust Engine, Risk Engine, Decision Engine
Market: Egypt (EG)
Version: 1.0

---

## Anchor Scenario

Nour, a Cairo buyer, sees a phone case seller on Facebook Marketplace.
The seller requests EGP 800 upfront via Instapay before shipping.
Nour has no way to verify the seller is real or will deliver.
The seller has no way to prove they are trustworthy to Nour.

SALAM Social Commerce Escrow holds Nour's EGP 800 after payment,
releases it to the seller only on confirmed delivery, and refunds
Nour automatically if delivery is not confirmed within the window.
Every transaction — completed, failed, or disputed — produces Evidence
that builds or erodes the seller's commercial record.

This is the product. Everything below is what it takes to build it precisely.

---

## What This Product Is

A payment protection layer for peer-to-peer commerce on social channels
(Facebook, Instagram, WhatsApp) in Egypt. It protects buyers against
non-delivery and gives sellers a trust signal they can show to future buyers.

It is **not** a payment processor — it integrates with Instapay and mobile
money providers to hold and release funds.
It is **not** a logistics company — it integrates with couriers to receive
delivery confirmation as Evidence.
It is **not** a dispute arbitration service — disputes above EGP 5,000 are
escalated to human review; below that, the Decision Engine rules automatically.

---

## Participants

| Role | Entity Type | Kernel Type |
|---|---|---|
| Buyer (Nour) | Consumer — not a Merchant in SALAM's model | External actor |
| Seller | Informal merchant on social channel | `Merchant` |
| SALAM | Escrow agent | `Organization` (system actor) |
| Payment provider | Instapay / Vodafone Cash / Orange Money | External integration |
| Courier | Bosta, Aramex EG, or seller self-delivery | External integration |

**Buyer is not a Merchant.** Buyers in social commerce are consumers, not
commercial actors. SALAM collects Evidence about sellers, not buyers.
Buyer identity is captured minimally (phone number + Instapay account ref)
for dispute resolution only and is not stored as a Merchant record.

---

## Escrow Record

An Escrow Record is the product-layer object that governs a single protected
transaction. It is distinct from the Kernel `Transaction` object — the
Kernel Transaction records the financial fact; the Escrow Record governs
the business logic around it.

### Fields

| Field | Type | Required | Mutable | Description |
|---|---|---|---|---|
| `escrow_id` | UUID | yes | no | Canonical identifier. Never reused. |
| `transaction_ref` | UUID | yes | no | Kernel Transaction ID for the escrow deposit. |
| `seller_ref` | UUID | yes | no | Merchant ID of the seller. |
| `buyer_phone` | string | yes | no | Buyer's phone number (E.164 format). Primary buyer identifier. |
| `buyer_instapay_ref` | string \| null | no | no | Buyer's Instapay account reference. Used for refunds. |
| `amount` | number | yes | no | Transaction amount in EGP. Must be between 50 and 50,000. |
| `currency` | string | yes | no | Always `EGP` for this product version. |
| `item_description` | string | yes | no | Free-text description of the item, provided by seller at escrow creation. Max 500 chars. |
| `payment_method` | enum | yes | no | `instapay`, `vodafone_cash`, `orange_money`, `etisalat_cash`. |
| `courier_ref` | string \| null | no | yes | Courier integration ID, if a tracked courier is used. Null for self-delivery. |
| `tracking_number` | string \| null | no | yes | Courier tracking number. Set when shipment is created. |
| `status` | enum | yes | yes (state machine) | See State Machine below. |
| `release_condition` | enum | yes | no | `delivery_confirmed`, `buyer_confirmation`. See Release Conditions. |
| `delivery_deadline` | timestamp | yes | no | When delivery must be confirmed by or auto-refund triggers. |
| `created_at` | timestamp | yes | no | When the escrow was created. |
| `funded_at` | timestamp \| null | no | yes (set once) | When payment was confirmed received. |
| `released_at` | timestamp \| null | no | yes (set once) | When funds were released to seller. |
| `refunded_at` | timestamp \| null | no | yes (set once) | When funds were returned to buyer. |
| `dispute_ref` | UUID \| null | no | yes (set once) | Event ID of the dispute, if raised. |
| `decision_ref` | UUID \| null | no | yes | Last Decision Engine decision for this escrow. |
| `evidence_refs` | UUID[] | yes | append-only | All Evidence objects collected during this escrow's lifecycle. |
| `version` | integer | yes | no | Monotonically increasing. |

### Amount Limits

| Band | Min | Max | Decision path |
|---|---|---|---|
| `micro` | EGP 50 | EGP 500 | Auto-decision only. No human review. |
| `small` | EGP 501 | EGP 5,000 | Auto-decision. Human review on dispute. |
| `medium` | EGP 5,001 | EGP 50,000 | Auto-decision with elevated Risk threshold. Human review on dispute. |

Transactions above EGP 50,000 are not accepted by this product version.
They require the B2B Escrow product (future specification).

---

## State Machine

```
CREATED
  │
  ├─[payment received within 2h]──► FUNDED
  │                                    │
  ├─[payment not received in 2h]──► EXPIRED (auto-refund not needed; no funds held)
                                       │
                              ┌────────▼────────┐
                              │    FUNDED        │
                              └────────┬─────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         │             │             │
                [seller ships]  [deadline passes] [buyer disputes]
                         │             │             │
                         ▼             ▼             ▼
                    IN_TRANSIT    AUTO_REFUND     DISPUTED
                         │        PROCESSING         │
                         │             │        [Decision Engine]
                [delivery confirmed]   │             │
                         │             │    ┌────────┴────────┐
                         ▼             │    │                 │
                  PENDING_RELEASE      │  RELEASED         REFUNDED
                         │             │
                [Decision: release]    ▼
                         │         REFUNDED
                         ▼
                      RELEASED
```

### State Definitions

| State | Meaning | Allowed next states |
|---|---|---|
| `CREATED` | Escrow record exists; awaiting buyer payment. | `FUNDED`, `EXPIRED` |
| `EXPIRED` | Payment not received within 2 hours of creation. Terminal. | — |
| `FUNDED` | Payment confirmed held. Awaiting seller shipment. | `IN_TRANSIT`, `AUTO_REFUND_PROCESSING`, `DISPUTED` |
| `IN_TRANSIT` | Seller has shipped; tracking active or self-delivery declared. | `PENDING_RELEASE`, `DISPUTED`, `AUTO_REFUND_PROCESSING` |
| `PENDING_RELEASE` | Delivery confirmed by courier or buyer. Awaiting Decision Engine release approval. | `RELEASED`, `DISPUTED` |
| `AUTO_REFUND_PROCESSING` | Deadline passed with no delivery confirmation. Refund in progress. | `REFUNDED` |
| `DISPUTED` | Buyer or seller raised a dispute. Awaiting Decision Engine or human resolution. | `RELEASED`, `REFUNDED` |
| `RELEASED` | Funds released to seller. Terminal. | — |
| `REFUNDED` | Funds returned to buyer. Terminal. | — |

Every state transition produces:
1. An update to `escrow_record.status`.
2. A Kernel `Event` object (`event_type` mapped per transition — see Events below).
3. An Evidence object documenting the transition.
4. A `decision.*` or `transaction.*` event on the event stream.

---

## Release Conditions

Two release conditions are supported in this product version:

### `delivery_confirmed` (default, recommended)
Funds release when the courier's API confirms delivery to the buyer's address.
SALAM receives a webhook from the courier integration on status change.
Delivery confirmation is ingested as Evidence (`claim_type: delivery_confirmation`,
`collection_method: third_party_attestation`).

If no courier is used (self-delivery), this condition cannot be selected.

### `buyer_confirmation`
Funds release when the buyer explicitly confirms receipt via the SALAM
buyer interface (SMS link or WhatsApp message). Buyer has 24 hours to
confirm after the seller declares shipment. If buyer does not respond
within 24 hours of declared delivery, the Decision Engine evaluates whether
to auto-release based on seller Trust score.

**Auto-release threshold for buyer non-response:**
- Seller `trust_score ≥ 0.70` AND `risk_severity: low | medium` → auto-release after 24h silence.
- Seller `trust_score < 0.70` OR `risk_severity: high | critical` → escalate to human review.
- First-time seller (no Trust score yet) → escalate to human review regardless.

---

## Delivery Deadline

The delivery deadline governs auto-refund. It is calculated at escrow creation:

| Courier type | Deadline |
|---|---|
| Tracked courier (Bosta, Aramex EG) | 5 calendar days from `funded_at` |
| Self-delivery declared by seller | 3 calendar days from `funded_at` |
| No courier declared | 3 calendar days from `funded_at` |

Deadline can be extended **once** by the seller, by up to 2 additional days,
if the seller provides a reason and the buyer does not object within 12 hours.
Extension produces an Evidence object (`claim_type: deadline_extension_request`).

If deadline passes with no delivery confirmation: `AUTO_REFUND_PROCESSING` triggers
immediately. No Decision Engine call required for auto-refund — this is a
hard rule, not a scored decision.

---

## Evidence Collected Per Escrow

Every escrow lifecycle event produces Evidence. This is the core value of
the product for SALAM — each transaction is a data point about the seller.

| Lifecycle event | claim_type | collection_method | Mutable fields updated |
|---|---|---|---|
| Escrow created | `escrow_initiated` | `system_inference` | — |
| Payment confirmed | `payment_record` | `third_party_attestation` (payment provider webhook) | `funded_at` |
| Seller declares shipment | `shipment_declaration` | `user_submission` | `tracking_number`, `courier_ref` |
| Courier pickup confirmed | `courier_pickup` | `third_party_attestation` | — |
| Courier delivery confirmed | `delivery_confirmation` | `third_party_attestation` | — |
| Buyer confirms receipt | `buyer_receipt_confirmation` | `user_submission` | — |
| Buyer raises dispute | `dispute_filed` | `user_submission` | `dispute_ref` |
| Seller provides dispute response | `dispute_response` | `user_submission` | — |
| Auto-refund triggered (deadline) | `delivery_failure` | `system_inference` | — |
| Funds released | `escrow_release` | `system_inference` | `released_at` |
| Funds refunded | `escrow_refund` | `system_inference` | `refunded_at` |

All Evidence objects for an escrow are linked to the seller's `merchant_id`
as `subject_ref`. They feed directly into the seller's Trust and Risk
recomputation via `evidence.validated` events.

**This is the compounding mechanism.** A seller who completes 20 escrows
accumulates 20 `delivery_confirmation` Evidence objects. Their Trust score
rises. Their cost of future escrows decreases (lower review thresholds).
A seller who triggers 3 auto-refunds accumulates 3 `delivery_failure`
Evidence objects. Their Risk score rises. Future escrows are flagged.

---

## Decision Engine Integration

The Decision Engine is called at two points in the escrow lifecycle:

### Decision Point 1 — Escrow Approval (at creation)

Before accepting a new escrow, SALAM calls the Decision Engine to determine
whether to proceed, add friction, or decline.

**Request:**
```json
{
  "decision_type": "escrow_approval",
  "subject_ref": { "entity_type": "merchant", "entity_id": "<seller_merchant_id>" },
  "context": {
    "transaction_value": 800,
    "transaction_value_band": "small",
    "market": "EG",
    "counterparty_ref": null,
    "payment_method": "instapay"
  }
}
```

**Decision outcomes and product responses:**

| Decision outcome | Trust score | Risk severity | Product response |
|---|---|---|---|
| `approved` | ≥ 0.50 | low / medium | Escrow created immediately. No friction. |
| `approved` | < 0.50 or no Trust yet | any | Escrow created. Buyer shown seller warning: "This seller has limited history." |
| `escalated` | any | high | Escrow created. Buyer shown strong warning. Seller notified that release requires review. |
| `declined` | any | critical | Escrow refused. Buyer shown: "We cannot protect this transaction." Seller flagged. |

A `declined` at escrow approval is the only point where a transaction is
refused. Once `FUNDED`, the escrow always resolves — either `RELEASED` or
`REFUNDED`. The system never holds funds indefinitely.

### Decision Point 2 — Release Approval (at delivery confirmation)

When delivery is confirmed, SALAM calls the Decision Engine before releasing
funds to the seller.

**Request:**
```json
{
  "decision_type": "escrow_release",
  "subject_ref": { "entity_type": "merchant", "entity_id": "<seller_merchant_id>" },
  "context": {
    "transaction_value": 800,
    "transaction_value_band": "small",
    "market": "EG",
    "payment_method": "instapay"
  }
}
```

**Decision outcomes and product responses:**

| Decision outcome | Condition | Product response |
|---|---|---|
| `approved` | Standard case | Immediate release. `escrow_release` Evidence produced. |
| `approved` | Seller Trust improved during escrow | Release + Trust recomputation triggered. |
| `escalated` | New critical Risk flag raised since escrow creation | Hold release. Human review. Max 4 business hours. |
| `declined` | Seller suspended during escrow | Refund to buyer. `escrow_refund` Evidence produced. |

A `declined` at release always results in a **refund**, never a hold.
Funds are never held beyond 4 business hours of human review.

---

## Dispute Handling

Disputes are raised by the buyer via the buyer interface. A dispute is only
valid while the escrow is in `FUNDED` or `IN_TRANSIT` state.

### Dispute triggers

- Buyer claims non-delivery after seller declared shipment.
- Buyer claims item received is not as described.
- Buyer claims item arrived damaged.

### Dispute Evidence collected

On dispute filing, the following are collected:
- `dispute_filed` Evidence from buyer (required: dispute reason, timestamp).
- Buyer may optionally submit photo Evidence (`claim_type: dispute_evidence_photo`,
  `collection_method: user_submission`).
- Seller has 24 hours to respond (`dispute_response` Evidence).

### Dispute Decision rules

| Amount band | Seller has delivery proof | Buyer has photo evidence | Decision |
|---|---|---|---|
| `micro` (≤ EGP 500) | yes (courier confirmed) | any | Release to seller |
| `micro` (≤ EGP 500) | no | any | Refund to buyer |
| `small` (EGP 501–5,000) | yes | no | Release to seller |
| `small` (EGP 501–5,000) | yes | yes (damage/wrong item) | Human review — max 8 business hours |
| `small` (EGP 501–5,000) | no | any | Refund to buyer |
| `medium` (EGP 5,001–50,000) | any | any | Human review — max 24 business hours |

"Delivery proof" = a `delivery_confirmation` Evidence object from a courier
integration with `validation_status: validated` and `confidence ≥ 0.85`.
Self-declared delivery by seller does not count as proof.

All dispute resolutions produce Evidence regardless of outcome:
- `dispute_resolved_release` or `dispute_resolved_refund`.
- These are strong Evidence objects — dispute outcomes are high-signal
  inputs to the seller's Trust and Risk scores.

---

## API Contract

### POST /escrow

Create a new escrow. Called by the seller after agreeing terms with buyer.

**Request:**
```json
{
  "seller_merchant_id": "uuid",
  "buyer_phone": "+201XXXXXXXXX",
  "amount": 800,
  "item_description": "iPhone 14 Pro Max case, black, genuine leather",
  "payment_method": "instapay",
  "release_condition": "delivery_confirmed",
  "courier": "bosta" | "aramex_eg" | "self_delivery" | null
}
```

**Response (201 Created):**
```json
{
  "escrow_id": "uuid",
  "status": "CREATED",
  "payment_instructions": {
    "method": "instapay",
    "recipient_alias": "salam-escrow@instapay",
    "amount": 800,
    "reference": "<escrow_id>",
    "expires_at": "<created_at + 2h>"
  },
  "buyer_link": "https://pay.salam.eg/e/<escrow_id>",
  "delivery_deadline": "<ISO 8601 timestamp>",
  "seller_warning": null | "string"
}
```

`buyer_link` is shared by the seller with Nour (the buyer) via WhatsApp/DM.
Nour opens the link, sees the escrow terms, and pays via Instapay to the
SALAM escrow alias with the `escrow_id` as the payment reference.

---

### POST /escrow/:id/shipment

Seller declares shipment. Transitions `FUNDED` → `IN_TRANSIT`.

**Request:**
```json
{
  "courier": "bosta" | "aramex_eg" | "self_delivery",
  "tracking_number": "string | null",
  "estimated_delivery_date": "date | null"
}
```

**Response (200 OK):**
```json
{
  "escrow_id": "uuid",
  "status": "IN_TRANSIT",
  "tracking_url": "string | null",
  "delivery_deadline": "<ISO 8601 timestamp>"
}
```

---

### POST /escrow/:id/dispute

Buyer raises a dispute. Requires buyer authentication via OTP to their
registered phone number.

**Request:**
```json
{
  "buyer_phone": "+201XXXXXXXXX",
  "otp": "string",
  "dispute_reason": "non_delivery | wrong_item | damaged_item | other",
  "description": "string",
  "photo_evidence_refs": ["base64_or_upload_ref"]
}
```

**Response (200 OK):**
```json
{
  "escrow_id": "uuid",
  "status": "DISPUTED",
  "dispute_ref": "uuid",
  "expected_resolution_by": "<ISO 8601 timestamp>",
  "message": "Your dispute has been received. The seller has 24 hours to respond."
}
```

---

### GET /escrow/:id

Status check. Accessible by seller (authenticated) and buyer (via phone OTP).

**Response (200 OK):**
```json
{
  "escrow_id": "uuid",
  "status": "string",
  "amount": 800,
  "currency": "EGP",
  "item_description": "string",
  "delivery_deadline": "timestamp",
  "seller_trust_signal": "limited | moderate | established",
  "created_at": "timestamp",
  "funded_at": "timestamp | null",
  "released_at": "timestamp | null",
  "refunded_at": "timestamp | null"
}
```

`seller_trust_signal` is a simplified Trust signal shown to the buyer:
- `limited`: seller Trust score < 0.40 or no Trust score yet.
- `moderate`: seller Trust score 0.40–0.70.
- `established`: seller Trust score > 0.70.

This is the only Trust signal exposed to the buyer — the numeric score
is never shown externally.

---

### Webhook: Courier Delivery Confirmation

SALAM receives webhooks from courier integrations on shipment status changes.

**Inbound payload (Bosta example):**
```json
{
  "tracking_number": "string",
  "status": "DELIVERED | FAILED | RETURNED",
  "timestamp": "ISO 8601",
  "signature": "HMAC-SHA256"
}
```

On `status: DELIVERED`:
1. Ingest as Evidence (`claim_type: delivery_confirmation`,
   `collection_method: third_party_attestation`).
2. Match to escrow via `tracking_number`.
3. Transition escrow to `PENDING_RELEASE`.
4. Call Decision Engine (`decision_type: escrow_release`).
5. On `approved`: transition to `RELEASED`, trigger payment release.

On `status: FAILED | RETURNED`:
1. Ingest as Evidence (`claim_type: delivery_failure`).
2. Notify buyer and seller.
3. Seller may reattempt delivery before deadline. If deadline passed:
   transition to `AUTO_REFUND_PROCESSING`.

---

### Webhook: Payment Provider Confirmation

SALAM receives payment confirmation from Instapay/mobile money on receipt
of funds to the escrow account.

**Inbound payload:**
```json
{
  "reference": "<escrow_id>",
  "amount": 800,
  "currency": "EGP",
  "sender_account": "string",
  "received_at": "ISO 8601",
  "signature": "HMAC-SHA256"
}
```

On receipt:
1. Match `reference` to `escrow_id`.
2. Validate `amount` matches escrow `amount` exactly. If mismatch: reject,
   return funds, notify seller.
3. Ingest as Evidence (`claim_type: payment_record`).
4. Transition escrow to `FUNDED`.
5. Notify seller that funds are held and they may ship.

---

## Events Produced

| Escrow state transition | Kernel Event type | Kernel Transaction type |
|---|---|---|
| `CREATED` | `commercial_event.recorded` (event_type: `escrow_initiated`) | — |
| `FUNDED` | `commercial_event.recorded` (event_type: `payment`) | `escrow_deposit` |
| `IN_TRANSIT` | `commercial_event.recorded` (event_type: `delivery`) | — |
| `PENDING_RELEASE` | — | — |
| `RELEASED` | `commercial_event.outcome_resolved` | `escrow_release` |
| `REFUNDED` | `commercial_event.outcome_resolved` | `escrow_refund` |
| `DISPUTED` | `commercial_event.recorded` (event_type: `dispute`) | — |
| `AUTO_REFUND_PROCESSING` | `commercial_event.recorded` (event_type: `default`) | — |
| `EXPIRED` | — | — |

Every terminal state (`RELEASED`, `REFUNDED`, `EXPIRED`) also triggers
`trust.recomputed` and `risk.recomputed` for the seller `merchant_id`.

---

## Seller Onboarding

A seller must have a Merchant record in SALAM before creating an escrow.
Onboarding is lightweight and does not block the first transaction:

1. Seller provides phone number → Merchant record created with
   `identity_status: unverified`.
2. Seller provides name and Facebook/Instagram profile URL → ingested as
   Evidence (`claim_type: social_profile`, `collection_method: user_submission`).
3. Seller may optionally provide National ID → ingested as Evidence
   (`claim_type: identity_document`). Not required for first escrow.
4. Merchant record created. Trust and Risk initialized (sparse — low
   confidence, `trust_score` not yet computable from zero transactions).

The first escrow a seller creates will show `seller_trust_signal: limited`
to the buyer regardless. This is accurate and honest — it is not a penalty,
it is the truth about the data available. The signal improves as transactions
complete.

---

## Egypt-Specific Constraints

| Constraint | Detail |
|---|---|
| Currency | EGP only. No USD or cross-currency in v1. |
| Payment methods | Instapay, Vodafone Cash, Orange Money, Etisalat Cash. No card payments in v1. |
| Couriers | Bosta and Aramex EG have webhook APIs. Other couriers: seller manual tracking number entry; no auto-confirmation available. |
| Maximum hold period | Egyptian Central Bank e-money regulations require funds not be held more than 7 calendar days without explicit extension approval. Delivery deadline (5 days max + 2 day extension) respects this constraint. |
| Dispute resolution SLA | All disputes must resolve within 5 business days per CBE consumer protection guidelines. |
| Language | Arabic primary. All buyer-facing communications in Arabic. Seller interface: Arabic and English. |

---

## What This Product Produces for SALAM (Network Value)

Every escrow transaction — regardless of outcome — is a data contribution:

| Outcome | Evidence produced | Network effect |
|---|---|---|
| Clean delivery, seller released | `payment_record` + `delivery_confirmation` + `escrow_release` | Trust score ↑. Seller's future escrows cheaper, less friction. |
| Deadline missed, buyer refunded | `delivery_failure` + `escrow_refund` | Risk score ↑. Seller's future escrows require more scrutiny. |
| Dispute, seller wins (courier proof) | `dispute_filed` + `delivery_confirmation` + `dispute_resolved_release` | Trust score maintained. Dispute patterns tracked. |
| Dispute, buyer wins (no proof) | `dispute_filed` + `dispute_resolved_refund` | Risk score ↑. Repeated pattern → seller flag. |
| Escrow declined at creation | Seller flagged | `critical` Risk flag. |

After 10 completed transactions with clean delivery: seller is no longer
`limited` — they are `established`. This is the graduation path from
informal unverified seller to evidence-backed commercial actor.

This is how SALAM acquires its first dataset on Egypt's informal merchant
population — not by asking them to fill in a form, but by being the
infrastructure that protects their transactions.

---

## Open Questions (ADRs Required)

1. **Instapay integration** — does SALAM hold a registered Instapay alias
   (`salam-escrow@instapay`) and receive payments directly, or does it
   integrate with an acquirer (e.g. Fawry, Paymob) to hold funds?
   Regulatory and architecture concern. Needs ADR before any payment code
   is written.
2. **CBE e-money license** — holding customer funds requires either a
   CBE-issued e-money license or a partnership with a licensed e-money
   institution. Which path? This is the single most consequential legal
   decision for this product. Needs ADR.
3. **Buyer OTP authentication** — SMS OTP via which provider? (Vonage,
   Twilio, local Egyptian SMS gateway). Architecture concern.
4. **Self-delivery confirmation** — when no courier is used, delivery
   confirmation relies on `buyer_confirmation` release condition. But a
   buyer may not respond. The 24-hour auto-release rule (Trust ≥ 0.70)
   needs formal validation as a policy decision. Needs ADR.
5. **National ID verification** — optional at onboarding, but what is
   the Evidence quality uplift of providing it vs. not? If a seller
   with National ID defaults, what is the enforcement path? Legal concern.
   Needs ADR before making ID verification a meaningful Trust signal.

---

*This file is a Product Specification. It derives from and is constrained
by the Kernel and Engine Specifications. It does not redefine Kernel
concepts — it operationalises them for a specific product in a specific market.*
