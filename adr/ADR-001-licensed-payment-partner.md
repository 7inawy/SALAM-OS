# ADR-001: Use a Licensed E-Money Partner for Escrow Fund Holding

Date: 2025-06-30
Status: accepted
Supersedes: —
Superseded by: —
Layer: architecture
Decider: 7inawy (founder)

## Context

The Social Commerce Escrow product (Egypt v1) requires SALAM to hold buyer
funds after payment and release them to the seller on delivery confirmation.
Holding customer funds in Egypt is regulated by the Central Bank of Egypt
(CBE) under the Payment Services and Payment Systems Law No. 18 of 2019
and its executive regulations.

Two paths exist to legally hold funds:

1. Obtain a CBE e-money or payment service provider license directly.
2. Partner with an existing CBE-licensed e-money institution that holds
   funds on SALAM's behalf under their license.

This ADR records the decision between those two paths.

The question was surfaced as an open item in:
`specifications/products/social-commerce-escrow-eg.md` — Open Question 2.

## Decision

SALAM will use a licensed Egyptian e-money partner to hold escrow funds.
SALAM does not hold customer funds directly and will not seek a CBE
e-money or payment service provider license in the v1 product phase.

The partner holds funds under their CBE license. SALAM instructs the
partner to release or refund via API based on Decision Engine output.
SALAM is the escrow logic layer; the partner is the regulated fund custodian.

**Target partners (in priority order for outreach):**
1. Paymob — largest Egyptian payment infrastructure provider; has existing
   e-money and acquiring licenses; documented API; active B2B partnerships.
2. Fawry — nationwide network; CBE-licensed; strong brand trust with
   Egyptian consumers; Instapay integration native.
3. ValU / vPay — CBE-licensed fintech; strong in social commerce adjacent
   use cases.

Partner selection requires a commercial agreement. The technical integration
architecture below holds regardless of which partner is selected.

## Alternatives Considered

### Option A: Obtain CBE E-Money License Directly

SALAM applies for and obtains its own CBE payment service provider license,
allowing it to hold customer funds directly.

**Why not chosen:**
- CBE licensing process takes 12–24 months minimum.
- Requires minimum paid-in capital of EGP 20 million for a payment service
  provider license.
- Requires physical presence in Egypt, Egyptian entity incorporation,
  CBE-approved compliance officers, and AML/KYC infrastructure at license
  standard.
- Blocks product launch entirely until license is granted.
- The escrow logic — which is SALAM's actual value — does not require
  owning the regulated fund custody layer.

### Option B: Licensed E-Money Partner (chosen)

SALAM integrates with a CBE-licensed partner who holds funds under their
license. SALAM provides the escrow logic; the partner provides the regulated
custody.

**Why chosen:** see Rationale below.

### Option C: Structure as a Non-Regulated Intermediary

Argue that SALAM is a technology provider, not a payment service provider,
and does not require a CBE license because it does not technically hold
funds — the funds flow directly between buyer and seller with SALAM as
a non-custodial intermediary.

**Why not chosen:**
- CBE regulations are broad in their definition of payment service activities.
- A "non-custodial" structure in which SALAM controls the release instruction
  is likely to be treated as regulated activity regardless of the technical
  architecture.
- Legal risk is unacceptable for a product whose core value proposition is
  trust. If SALAM's escrow product is found to be operating without a
  required license, the reputational damage is fatal to the Trust use case.
- This option was rejected on risk grounds without detailed evaluation.

## Rationale

SALAM's competitive advantage is the intelligence layer — evidence collection,
trust scoring, decision engine, and the commercial graph. The fund custody
layer is regulated infrastructure, not a source of differentiation.

Partnering with a licensed institution separates SALAM's moat (intelligence)
from regulated infrastructure (custody). This is the correct architectural
boundary: SALAM tells the partner what to do with the money; the partner
holds and moves it under their license.

This decision optimizes for speed to market and risk management over margin.
A partner will take a fee per transaction. That fee is the cost of not
spending 18+ months and EGP 20M+ on a license before proving the product.

The decision is reversible at the cost of the licensing process. If SALAM
achieves sufficient scale, obtaining a direct license becomes rational.
That is a future ADR.

## Consequences

### Positive
- Product can launch within weeks of a signed partner agreement, not years.
- No CBE capital requirements at this stage.
- Partner's existing Instapay, Vodafone Cash, and Orange Money integrations
  are reused — no need to build payment provider integrations independently.
- Partner's existing CBE AML/KYC compliance infrastructure covers the fund
  custody layer.
- Risk of regulatory action is borne by the partner for the custody layer.

### Negative / Trade-offs
- Partner takes a per-transaction fee. Estimated 0.5%–1.5% per transaction
  depending on partner and volume tier. This compresses escrow product margin.
- SALAM's fund release instructions depend on partner API reliability.
  Partner downtime = escrow release delays. Requires SLA in commercial agreement.
- SALAM does not control the customer payment experience end-to-end. The
  partner's payment UI/flow is part of the buyer journey.
- Commercial negotiation with partner is required before technical integration
  can be finalized. This is a dependency on a business process, not just
  an engineering task.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Partner rejects commercial terms | Medium | High | Outreach to all three target partners in parallel. Fawry as fallback if Paymob declines. |
| Partner API reliability below SLA | Low | High | Require 99.9% uptime SLA in agreement. Implement retry logic and queue for release instructions. |
| CBE changes regulations to require license even for technology intermediaries | Low | Critical | Monitor CBE regulatory communications. Structure agreement so partner is unambiguously the regulated entity. Engage Egyptian fintech legal counsel before signing. |
| Partner is acquired or exits market | Very low | High | Ensure agreement includes data portability and 90-day termination notice. Design integration layer to be partner-agnostic (see Dependencies). |

## Dependencies

**Technical dependency:** The escrow product integration layer must be
designed as partner-agnostic from day one. A `PaymentPartnerAdapter` interface
must abstract all partner-specific API calls. Switching partners must require
only a new adapter implementation, not changes to escrow logic.

This is an architectural constraint on the first code written for this product.
It is not optional.

**Business dependency:** A signed commercial agreement with at least one
target partner must exist before escrow fund-holding functionality is built.
The integration can be developed against a partner sandbox environment before
the agreement is signed, but production deployment requires a signed agreement.

**Legal dependency:** Egyptian fintech legal counsel must review the commercial
agreement structure before signing to confirm SALAM's role is correctly
characterized as a technology intermediary, not a payment service provider
under CBE regulations.

## Review Trigger

This decision should be revisited when any of the following occur:
- SALAM processes more than EGP 10 million/month in escrow volume.
  At that scale, partner fees may exceed the cost of a direct license.
- CBE issues new regulations that materially change the definition of
  regulated payment service activity.
- A partner agreement cannot be reached within 90 days of active outreach,
  requiring evaluation of Option C or a different market entry sequence.
