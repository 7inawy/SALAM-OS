"""
shared/kernel/events/events.py

Canonical event definitions for the SALAM event stream.
Every event published by any engine must use these types.
No service defines its own event schema — they import from here.

Event naming convention: <domain>.<action>
e.g. evidence.validated, merchant.created, trust.recomputed
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventName(str, Enum):
    # Evidence events
    EVIDENCE_INGESTED = "evidence.ingested"
    EVIDENCE_VALIDATED = "evidence.validated"
    EVIDENCE_REJECTED = "evidence.rejected"
    EVIDENCE_PENDING = "evidence.pending"
    EVIDENCE_SUPERSEDED = "evidence.superseded"

    # Merchant events
    MERCHANT_CREATED = "merchant.created"
    MERCHANT_IDENTITY_STATUS_CHANGED = "merchant.identity_status_changed"
    MERCHANT_SUSPENDED = "merchant.suspended"
    MERCHANT_REINSTATED = "merchant.reinstated"

    # Transaction events
    TRANSACTION_INITIATED = "transaction.initiated"
    TRANSACTION_COMPLETED = "transaction.completed"
    TRANSACTION_FAILED = "transaction.failed"
    TRANSACTION_DISPUTED = "transaction.disputed"
    TRANSACTION_REVERSED = "transaction.reversed"

    # Commercial event events
    COMMERCIAL_EVENT_RECORDED = "commercial_event.recorded"
    COMMERCIAL_EVENT_OUTCOME_RESOLVED = "commercial_event.outcome_resolved"

    # Trust events
    TRUST_INITIALIZED = "trust.initialized"
    TRUST_RECOMPUTED = "trust.recomputed"
    TRUST_SUSPENDED = "trust.suspended"
    TRUST_REVOKED = "trust.revoked"
    TRUST_STALE = "trust.stale"

    # Risk events
    RISK_INITIALIZED = "risk.initialized"
    RISK_RECOMPUTED = "risk.recomputed"
    RISK_ESCALATED = "risk.escalated"
    RISK_FLAG_RAISED = "risk.flag_raised"
    RISK_FLAG_RESOLVED = "risk.flag_resolved"
    RISK_RESOLVED = "risk.resolved"
    RISK_STALE = "risk.stale"

    # Decision events
    DECISION_PRODUCED = "decision.produced"
    DECISION_ESCALATED = "decision.escalated"
    DECISION_OUTCOME_RECORDED = "decision.outcome_recorded"

    # Graph events
    GRAPH_NODE_ADDED = "graph.node_added"
    GRAPH_NODE_UPDATED = "graph.node_updated"
    GRAPH_EDGE_ADDED = "graph.edge_added"
    GRAPH_EDGE_UPDATED = "graph.edge_updated"

    # Escrow events (product layer — published by escrow service)
    ESCROW_CREATED = "escrow.created"
    ESCROW_FUNDED = "escrow.funded"
    ESCROW_IN_TRANSIT = "escrow.in_transit"
    ESCROW_RELEASED = "escrow.released"
    ESCROW_REFUNDED = "escrow.refunded"
    ESCROW_DISPUTED = "escrow.disputed"
    ESCROW_EXPIRED = "escrow.expired"


class SALAMEvent(BaseModel):
    """
    Base class for all SALAM events.
    Every event on the stream is an instance of this or a subclass.

    event_id:    Unique per event — not the same as the entity ID.
    stream_key:  The Redis Stream key this event is published to.
                 Format: salam:<domain> e.g. salam:evidence, salam:merchant
    """
    event_id: UUID = Field(default_factory=uuid4)
    event_name: EventName
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    producer: str = Field(description="Service name that produced this event")
    payload: dict[str, Any]

    @property
    def stream_key(self) -> str:
        domain = self.event_name.value.split(".")[0]
        return f"salam:{domain}"


# ---------------------------------------------------------------------------
# Typed event payloads — used by producers for type safety
# ---------------------------------------------------------------------------

class EvidenceValidatedPayload(BaseModel):
    evidence_id: UUID
    subject_ref_type: str
    subject_ref_id: UUID
    claim_type: str
    confidence: float
    collection_method: str


class EvidenceRejectedPayload(BaseModel):
    evidence_id: UUID
    subject_ref_type: str
    subject_ref_id: UUID
    claim_type: str
    rejection_reason: str
    source_identifier: str


class EvidenceSupersededPayload(BaseModel):
    old_evidence_id: UUID
    new_evidence_id: UUID
    subject_ref_type: str
    subject_ref_id: UUID
    claim_type: str


class MerchantCreatedPayload(BaseModel):
    merchant_id: UUID
    display_name: str
    operating_markets: list[str]
    channels: list[str]
    identity_status: str


class MerchantSuspendedPayload(BaseModel):
    merchant_id: UUID
    reason: str
    flag_type: str


class TrustRecomputedPayload(BaseModel):
    trust_id: UUID
    merchant_id: UUID
    score: float
    confidence: float
    trigger: str
    market: str
    transaction_value_band: str


class RiskRecomputedPayload(BaseModel):
    risk_id: UUID
    merchant_id: UUID
    score: float
    severity: str
    confidence: float
    trigger: str
    market: str
    transaction_value_band: str


class RiskFlagRaisedPayload(BaseModel):
    risk_id: UUID
    merchant_id: UUID
    flag_id: UUID
    flag_type: str
    severity: str
    raised_by: str


class DecisionProducedPayload(BaseModel):
    decision_id: UUID
    request_id: UUID
    decision_type: str
    merchant_id: UUID
    outcome: str
    confidence: float
    trust_score: Optional[float]
    risk_score: Optional[float]
    risk_severity: Optional[str]


class EscrowFundedPayload(BaseModel):
    escrow_id: UUID
    merchant_id: UUID
    amount: float
    currency: str
    payment_method: str
    transaction_id: UUID


class EscrowReleasedPayload(BaseModel):
    escrow_id: UUID
    merchant_id: UUID
    amount: float
    currency: str
    decision_id: UUID


class EscrowRefundedPayload(BaseModel):
    escrow_id: UUID
    merchant_id: UUID
    amount: float
    currency: str
    reason: str  # deadline_exceeded | dispute_resolved | seller_suspended
