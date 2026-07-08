"""
shared/kernel/models/__init__.py

Single import point for all Kernel entity models.
Services import from here, not from individual files.

    from shared.kernel.models import Evidence, Merchant, Trust, Risk
"""

from .base import (
    CollectionMethod,
    ContactMetadata,
    DecayModel,
    DecayRate,
    EntityRef,
    EntityType,
    EvidenceRef,
    Flag,
    ProvenanceChainEntry,
    ProvenanceMetadata,
    QualityMetadata,
    RegistrationMetadata,
    RiskSeverity,
    Source,
    TransactionValueBand,
    ValidityWindow,
)
from .evidence import (
    Evidence,
    EvidenceIngestionRequest,
    EvidenceIngestionResponse,
    ValidationStatus,
)
from .merchant import (
    CommercialChannel,
    IdentityStatus,
    Merchant,
    MerchantCreateRequest,
    MerchantResponse,
    MerchantStatus,
)
from .transaction import (
    CommercialEvent,
    EventOutcome,
    EventSignificance,
    MonetaryValue,
    Participant,
    ParticipantType,
    Party,
    PartyRole,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from .trust_risk import (
    Driver,
    EvidenceWeight,
    Risk,
    RiskContext,
    RiskDimensions,
    RiskFlag,
    RiskHistoryEntry,
    RiskStatus,
    Trust,
    TrustContext,
    TrustDimensions,
    TrustHistoryEntry,
    TrustRiskStatus,
)

__all__ = [
    # Base types
    "CollectionMethod", "ContactMetadata", "DecayModel", "DecayRate",
    "EntityRef", "EntityType", "EvidenceRef", "Flag",
    "ProvenanceChainEntry", "ProvenanceMetadata", "QualityMetadata",
    "RegistrationMetadata", "RiskSeverity", "Source",
    "TransactionValueBand", "ValidityWindow",
    # Evidence
    "Evidence", "EvidenceIngestionRequest", "EvidenceIngestionResponse",
    "ValidationStatus",
    # Merchant
    "CommercialChannel", "IdentityStatus", "Merchant",
    "MerchantCreateRequest", "MerchantResponse", "MerchantStatus",
    # Event + Transaction
    "CommercialEvent", "EventOutcome", "EventSignificance", "MonetaryValue",
    "Participant", "ParticipantType", "Party", "PartyRole",
    "Transaction", "TransactionStatus", "TransactionType",
    # Trust + Risk
    "Driver", "EvidenceWeight", "Risk", "RiskContext", "RiskDimensions",
    "RiskFlag", "RiskHistoryEntry", "RiskStatus", "Trust", "TrustContext",
    "TrustDimensions", "TrustHistoryEntry", "TrustRiskStatus",
]
