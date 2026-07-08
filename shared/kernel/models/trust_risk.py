"""
shared/kernel/models/trust_risk.py

Canonical Pydantic models for Trust and Risk entities.
Derived from kernel/ontology/trust.md and risk.md.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .base import (
    DecayModel,
    EntityRef,
    RiskSeverity,
    TransactionValueBand,
)


# ---------------------------------------------------------------------------
# Shared between Trust and Risk
# ---------------------------------------------------------------------------

class TrustRiskStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    STALE = "stale"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class RiskStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    STALE = "stale"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class ValidityWindow(BaseModel):
    valid_from: datetime
    valid_until: Optional[datetime] = None
    decay_model: DecayModel


class Driver(BaseModel):
    """Single primary driver entry for explainability."""
    ref_id: UUID
    ref_type: str = Field(description="evidence | knowledge")
    dimension: str
    contribution_weight: float = Field(ge=0.0, le=1.0)


class EvidenceWeight(BaseModel):
    """
    Explains what drove the Trust or Risk score.
    Required for explainability — not optional metadata.
    """
    evidence_count: int = Field(ge=0)
    knowledge_count: int = Field(ge=0)
    oldest_evidence_at: datetime
    newest_evidence_at: datetime
    primary_drivers: list[Driver]


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------

class TrustContext(BaseModel):
    """
    Trust is always context-scoped. A Trust object without context
    is meaningless — a merchant trusted for EGP 500 may not be
    trusted for EGP 50,000.
    """
    transaction_value_band: TransactionValueBand
    market: str = Field(pattern=r"^[A-Z]{2}$")
    counterparty_type: Optional[str] = None
    product_type: Optional[str] = None


class TrustDimensions(BaseModel):
    """Five trust dimensions, each independently scored [0, 1]."""
    identity: float = Field(ge=0.0, le=1.0)
    fulfillment: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)
    financial: float = Field(ge=0.0, le=1.0)
    network: float = Field(ge=0.0, le=1.0)


class TrustHistoryEntry(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    dimensions: TrustDimensions
    computed_at: datetime
    trigger: str = Field(
        description=(
            "new_evidence | evidence_decay | relationship_update | "
            "scheduled | manual"
        )
    )


class Trust(BaseModel):
    """
    A computed, Evidence-backed assessment of reliability and commercial
    integrity. Multi-dimensional, context-scoped, continuously updated.

    Trust is not the inverse of Risk — they are independent assessments.
    Evidence precedes trust: a score without traceable Evidence is inadmissible.
    History is append-only and retained indefinitely.
    """

    trust_id: UUID
    version: int = Field(ge=1)

    subject_ref: EntityRef
    context: TrustContext

    # Score (recalculable)
    score: float = Field(ge=0.0, le=1.0)
    dimensions: TrustDimensions
    confidence: float = Field(ge=0.0, le=1.0)

    # Explainability (required, not optional)
    evidence_weight: EvidenceWeight

    # Status
    status: TrustRiskStatus = TrustRiskStatus.INITIALIZING
    suspension_reason: Optional[str] = None

    # Validity
    valid_for: ValidityWindow
    computed_at: datetime
    computed_by: str

    # History (append-only)
    history: list[TrustHistoryEntry] = Field(default_factory=list)

    archived: bool = False

    @model_validator(mode="after")
    def suspension_reason_required(self) -> "Trust":
        if self.status in (TrustRiskStatus.SUSPENDED, TrustRiskStatus.REVOKED):
            if not self.suspension_reason:
                raise ValueError(
                    "suspension_reason required when status is suspended or revoked"
                )
        return self

    def buyer_signal(self) -> str:
        """
        Simplified three-tier signal for buyer-facing display.
        The numeric score is never exposed externally.
        """
        if self.score < 0.40:
            return "limited"
        elif self.score < 0.70:
            return "moderate"
        return "established"

    def is_usable_for_decision(self) -> bool:
        return self.status == TrustRiskStatus.ACTIVE


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class RiskContext(BaseModel):
    """Risk is context-scoped — same entity, different exposure by context."""
    transaction_value: Optional[float] = Field(default=None, gt=0)
    transaction_value_band: TransactionValueBand
    market: str = Field(pattern=r"^[A-Z]{2}$")
    counterparty_ref: Optional[UUID] = None
    product_type: Optional[str] = None
    payment_method: Optional[str] = None


class RiskDimensions(BaseModel):
    """Six risk dimensions, each independently scored [0, 1]."""
    identity: float = Field(ge=0.0, le=1.0)
    behavioral: float = Field(ge=0.0, le=1.0)
    financial: float = Field(ge=0.0, le=1.0)
    network: float = Field(ge=0.0, le=1.0)
    market: float = Field(ge=0.0, le=1.0)
    concentration: float = Field(ge=0.0, le=1.0)


class RiskFlag(BaseModel):
    """Named escalation signal. Append-only."""
    flag_id: UUID
    flag_type: str
    severity: str = Field(description="warning | high | critical")
    raised_by: str
    raised_at: datetime
    evidence_ref: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None

    def is_active(self) -> bool:
        return self.resolved_at is None

    def is_critical(self) -> bool:
        return self.severity == "critical" and self.is_active()


class RiskHistoryEntry(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    severity: RiskSeverity
    dimensions: RiskDimensions
    computed_at: datetime
    trigger: str = Field(
        description=(
            "new_evidence | evidence_decay | relationship_update | "
            "flag_raised | flag_resolved | scheduled | manual"
        )
    )


class Risk(BaseModel):
    """
    A computed, Evidence-backed assessment of the probability and severity
    of adverse outcomes. Prospective — a forward-looking estimate.

    Risk is not the inverse of Trust. A merchant can be high-Trust and
    high-Risk simultaneously. Both are required for a complete Decision.
    """

    risk_id: UUID
    version: int = Field(ge=1)

    subject_ref: EntityRef
    context: RiskContext

    # Score (recalculable)
    score: float = Field(ge=0.0, le=1.0)
    dimensions: RiskDimensions
    severity: RiskSeverity
    confidence: float = Field(ge=0.0, le=1.0)

    # Explainability (required)
    evidence_weight: EvidenceWeight

    # Flags (append-only)
    flags: list[RiskFlag] = Field(default_factory=list)

    # Status
    status: RiskStatus = RiskStatus.INITIALIZING
    escalation_reason: Optional[str] = None

    # Validity
    valid_for: ValidityWindow
    computed_at: datetime
    computed_by: str

    # History (append-only)
    history: list[RiskHistoryEntry] = Field(default_factory=list)

    archived: bool = False

    @model_validator(mode="after")
    def escalation_reason_required(self) -> "Risk":
        if self.status == RiskStatus.ESCALATED and not self.escalation_reason:
            raise ValueError("escalation_reason required when status is escalated")
        return self

    @model_validator(mode="after")
    def severity_matches_score(self) -> "Risk":
        bands = {
            RiskSeverity.LOW: (0.0, 0.25),
            RiskSeverity.MEDIUM: (0.25, 0.50),
            RiskSeverity.HIGH: (0.50, 0.75),
            RiskSeverity.CRITICAL: (0.75, 1.01),
        }
        low, high = bands[self.severity]
        if not (low <= self.score < high):
            raise ValueError(
                f"severity {self.severity} does not match score {self.score}"
            )
        return self

    def has_active_critical_flags(self) -> bool:
        return any(f.is_critical() for f in self.flags)

    def is_usable_for_decision(self) -> bool:
        return self.status == RiskStatus.ACTIVE

    def blocks_escrow_creation(self) -> bool:
        return (
            self.status == RiskStatus.ESCALATED
            or self.has_active_critical_flags()
        )
