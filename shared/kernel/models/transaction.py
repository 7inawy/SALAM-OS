"""
shared/kernel/models/transaction.py

Canonical Pydantic models for the Transaction and Event entities.
Derived from kernel/ontology/transaction.md and event.md.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .base import EntityRef, Flag


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class EventOutcome(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class EventSignificance(str, Enum):
    ROUTINE = "routine"
    NOTABLE = "notable"
    CRITICAL = "critical"


class ParticipantType(str, Enum):
    MERCHANT = "merchant"
    ORGANIZATION = "organization"


class Participant(BaseModel):
    participant_id: UUID
    participant_type: ParticipantType
    role: str = Field(
        description=(
            "e.g. seller, buyer, logistics_provider, guarantor, subject, reporter. "
            "Open string; Specification layer defines valid roles per event_type."
        )
    )


class CommercialEvent(BaseModel):
    """
    A discrete, timestamped occurrence in commercial reality significant
    enough to produce or update Evidence.

    Every Event must have at least one Evidence object at creation.
    Transaction is a financially-settled subtype of Event.
    """

    event_id: UUID
    version: int = Field(ge=1)
    event_type: str

    occurred_at: datetime
    recorded_at: datetime

    participants: list[Participant] = Field(min_length=1)
    evidence_refs: list[UUID] = Field(min_length=1)  # append-only

    outcome: EventOutcome = EventOutcome.PENDING
    outcome_resolved_at: Optional[datetime] = None

    significance: EventSignificance
    market: str = Field(pattern=r"^[A-Z]{2}$")
    channel: Optional[str] = None

    linked_transaction_ref: Optional[UUID] = None

    tags: list[str] = Field(default_factory=list)  # append-only
    flags: list[Flag] = Field(default_factory=list)  # append-only

    created_at: datetime
    archived: bool = False

    @model_validator(mode="after")
    def outcome_resolved_at_required_for_terminal(self) -> "CommercialEvent":
        terminal = {EventOutcome.COMPLETED, EventOutcome.FAILED,
                    EventOutcome.CANCELLED, EventOutcome.UNKNOWN}
        if self.outcome in terminal and self.outcome_resolved_at is None:
            raise ValueError(
                f"outcome_resolved_at required when outcome is {self.outcome}"
            )
        return self


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class TransactionType(str, Enum):
    PURCHASE = "purchase"
    ESCROW_DEPOSIT = "escrow_deposit"
    ESCROW_RELEASE = "escrow_release"
    ESCROW_REFUND = "escrow_refund"
    TRANSFER = "transfer"
    REFUND = "refund"
    REVERSAL = "reversal"
    FEE = "fee"
    SETTLEMENT_BATCH = "settlement_batch"


class TransactionStatus(str, Enum):
    INITIATED = "initiated"
    PROCESSING = "processing"
    HELD = "held"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    DISPUTED = "disputed"


class PartyRole(str, Enum):
    PAYER = "payer"
    PAYEE = "payee"
    ESCROW_AGENT = "escrow_agent"
    GUARANTOR = "guarantor"
    PLATFORM = "platform"


class Party(BaseModel):
    party_id: UUID
    party_type: ParticipantType
    role: PartyRole
    account_ref: Optional[str] = None


class MonetaryValue(BaseModel):
    amount: float = Field(gt=0, description="Must be positive")
    fee_amount: Optional[float] = Field(default=None, ge=0)
    net_amount: Optional[float] = Field(default=None, gt=0)


class Transaction(BaseModel):
    """
    A financially-settled commercial exchange between two or more parties.
    A specific subtype of Event — event_ref is required.

    Transaction is never edited after creation. Status transitions and
    Evidence appends are the only permitted mutations.
    """

    transaction_id: UUID
    version: int = Field(ge=1)

    # Parent Event — required; Transaction cannot exist without an Event
    event_ref: UUID

    transaction_type: TransactionType
    initiated_at: datetime
    settled_at: Optional[datetime] = None

    # Parties — minimum payer + payee
    parties: list[Party] = Field(min_length=2)

    # Value
    value: MonetaryValue
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    settlement_currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    exchange_rate: Optional[float] = Field(default=None, gt=0)

    # Method and routing
    payment_method: str
    platform_ref: Optional[str] = None

    # Status state machine
    status: TransactionStatus = TransactionStatus.INITIATED
    status_reason: Optional[str] = None

    # Evidence (append-only, minimum one)
    evidence_refs: list[UUID] = Field(min_length=1)

    # Escrow and dispute links
    escrow_ref: Optional[UUID] = None
    dispute_ref: Optional[UUID] = None

    flags: list[Flag] = Field(default_factory=list)  # append-only

    market: str = Field(pattern=r"^[A-Z]{2}$")
    created_at: datetime
    archived: bool = False

    @model_validator(mode="after")
    def status_reason_required_for_terminal(self) -> "Transaction":
        requires_reason = {
            TransactionStatus.FAILED,
            TransactionStatus.REVERSED,
            TransactionStatus.DISPUTED,
        }
        if self.status in requires_reason and not self.status_reason:
            raise ValueError(
                f"status_reason required when status is {self.status}"
            )
        return self

    def payer(self) -> Optional[Party]:
        return next((p for p in self.parties if p.role == PartyRole.PAYER), None)

    def payee(self) -> Optional[Party]:
        return next((p for p in self.parties if p.role == PartyRole.PAYEE), None)
