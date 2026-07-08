"""
shared/kernel/models/base.py

Base types shared across all Kernel entity models.
These mirror the $defs in the Kernel JSON Schemas exactly.
No service defines its own versions of these — they import from here.
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class CollectionMethod(str, Enum):
    DIRECT_OBSERVATION = "direct_observation"
    THIRD_PARTY_ATTESTATION = "third_party_attestation"
    USER_SUBMISSION = "user_submission"
    SYSTEM_INFERENCE = "system_inference"
    DOCUMENT_EXTRACTION = "document_extraction"


class ValidationStatus(str, Enum):
    UNVALIDATED = "unvalidated"
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EntityType(str, Enum):
    MERCHANT = "merchant"
    ORGANIZATION = "organization"


class DecayRate(str, Enum):
    NONE = "none"
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"


class DecayModel(str, Enum):
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class TransactionValueBand(str, Enum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Shared composite types
# ---------------------------------------------------------------------------

class EntityRef(BaseModel):
    """Reference to any Kernel entity by type and ID."""
    entity_type: EntityType
    entity_id: UUID

    model_config = {"frozen": True}


class Source(BaseModel):
    """Origin of an Evidence object."""
    source_type: str = Field(
        description="e.g. api_integration, human_submission, sensor, document_scan"
    )
    identifier: str = Field(
        description="Identifier of the specific source instance"
    )

    model_config = {"frozen": True}


class QualityMetadata(BaseModel):
    """Seven-dimension quality scoring for Evidence objects."""
    authenticity: float = Field(ge=0.0, le=1.0)
    integrity: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    verifiability: float = Field(ge=0.0, le=1.0)
    provenance_score: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)


class ProvenanceChainEntry(BaseModel):
    """Single entry in an Evidence provenance chain. Append-only."""
    step: str = Field(description="e.g. normalize, enrich, re-score, validate")
    actor: str = Field(description="System component or identity that performed the step")
    timestamp: datetime


class ProvenanceMetadata(BaseModel):
    """Append-only provenance chain for Evidence objects."""
    origin: str
    collection_method: CollectionMethod
    chain: list[ProvenanceChainEntry] = Field(default_factory=list)
    ownership: str
    verification_confidence: float = Field(ge=0.0, le=1.0)


class Flag(BaseModel):
    """Compliance, fraud, or quality flag. Append-only on entities."""
    flag_id: UUID
    flag_type: str
    raised_by: str
    raised_at: datetime
    evidence_ref: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class EvidenceRef(BaseModel):
    """Lightweight reference to an Evidence object."""
    evidence_id: UUID
    claim_type: str


class ValidityWindow(BaseModel):
    """Time window during which a Knowledge or Trust/Risk object is current."""
    valid_from: datetime
    valid_until: Optional[datetime] = None
    decay_rate: DecayRate


class RegistrationMetadata(BaseModel):
    """Formal business registration details."""
    country: str = Field(pattern=r"^[A-Z]{2}$")
    registration_number: str
    registration_type: str
    registered_at: date
    evidence_ref: UUID


class ContactMetadata(BaseModel):
    """Operational contact information."""
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    whatsapp: Optional[str] = None
