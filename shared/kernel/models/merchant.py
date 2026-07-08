"""
shared/kernel/models/merchant.py

Canonical Pydantic model for the Merchant entity.
Derived from kernel/ontology/merchant.md and merchant.schema.json.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import (
    ContactMetadata,
    EntityRef,
    EvidenceRef,
    Flag,
    RegistrationMetadata,
)


class IdentityStatus(str, Enum):
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    SUSPENDED = "suspended"


class MerchantStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DEREGISTERED = "deregistered"


class CommercialChannel(str, Enum):
    MARKETPLACE = "marketplace"
    SOCIAL_COMMERCE = "social_commerce"
    DIRECT = "direct"
    PHYSICAL_RETAIL = "physical_retail"
    WHOLESALE = "wholesale"


class Merchant(BaseModel):
    """
    A commercial actor that sells goods or services within an emerging
    market context. Primary subject of SALAM's intelligence operations.

    Merchants are subjects, not users.
    Identity verification is continuous, not a gate.
    One legal entity may map to multiple Merchant records (linked_merchants).
    """

    # Identity
    merchant_id: UUID
    version: int = Field(ge=1)

    # Names
    display_name: str = Field(min_length=1)
    legal_name: Optional[str] = None

    # Identity verification (continuous process)
    identity_status: IdentityStatus = IdentityStatus.UNVERIFIED
    identity_refs: list[EvidenceRef] = Field(default_factory=list)  # append-only

    # Registration (optional — informal merchants are first-class)
    registration: Optional[RegistrationMetadata] = None

    # Commercial profile
    category: str
    operating_markets: list[str] = Field(
        min_length=1,
        description="ISO 3166-1 alpha-2 country codes"
    )
    channels: list[CommercialChannel] = Field(min_length=1)

    # Contact (operational only, not for identity verification)
    contact: Optional[ContactMetadata] = None

    # Intelligence pointers (refs to computed objects, not the objects themselves)
    commercial_profile_ref: Optional[UUID] = None  # active Knowledge object
    trust_score_ref: Optional[UUID] = None          # active Trust object
    risk_score_ref: Optional[UUID] = None           # active Risk object

    # Organizational structure
    organization_ref: Optional[UUID] = None

    # Identity clustering (append-only)
    linked_merchants: list[UUID] = Field(default_factory=list)

    # Lifecycle
    status: MerchantStatus = MerchantStatus.ACTIVE
    flags: list[Flag] = Field(default_factory=list)  # append-only
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    archived: bool = False

    def is_eligible_for_escrow(self) -> bool:
        """
        A merchant is eligible to create escrow transactions if active
        and not suspended. Identity verification is not a gate —
        it affects the Trust signal shown to the buyer, not eligibility.
        """
        return self.status == MerchantStatus.ACTIVE

    def has_active_critical_flags(self) -> bool:
        return any(
            f.resolved_at is None and "critical" in f.flag_type.lower()
            for f in self.flags
        )

    def trust_signal(self, trust_score: Optional[float]) -> str:
        """
        Simplified three-tier trust signal for buyer-facing display.
        Never exposes the numeric score externally.
        """
        if trust_score is None or trust_score < 0.40:
            return "limited"
        elif trust_score < 0.70:
            return "moderate"
        return "established"


class MerchantCreateRequest(BaseModel):
    """Payload to register a new Merchant in the system."""
    display_name: str = Field(min_length=1)
    phone: str = Field(description="E.164 format, e.g. +201XXXXXXXXX")
    category: str
    operating_markets: list[str] = Field(min_length=1)
    channels: list[CommercialChannel] = Field(min_length=1)
    legal_name: Optional[str] = None
    social_profile_url: Optional[str] = None


class MerchantResponse(BaseModel):
    """Public-facing Merchant representation. Excludes internal refs."""
    merchant_id: UUID
    display_name: str
    identity_status: IdentityStatus
    status: MerchantStatus
    category: str
    operating_markets: list[str]
    channels: list[CommercialChannel]
    created_at: datetime
    last_activity_at: Optional[datetime] = None
