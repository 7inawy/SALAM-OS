"""
shared/kernel/models/evidence.py

Canonical Pydantic model for the Evidence entity.
Derived from kernel/ontology/evidence.md and evidence.schema.json.
This is the single authoritative Python representation of Evidence.
No service defines its own Evidence model — they import this.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import (
    CollectionMethod,
    EntityRef,
    ProvenanceMetadata,
    QualityMetadata,
    Source,
    ValidationStatus,
)


class Evidence(BaseModel):
    """
    An immutable, attributable observation about commercial reality.
    The root entity of the SALAM Kernel ontology.

    Immutability rules:
    - Once validation_status reaches validated or rejected, claim,
      source, and collection metadata are frozen.
    - Corrections create a new Evidence object with supersedes set.
    - archived transitions one-way: False → True. Never deleted.
    """

    # Identity
    evidence_id: UUID
    version: int = Field(ge=1)
    supersedes: Optional[UUID] = None

    # What was observed
    subject_ref: EntityRef
    claim: str = Field(min_length=1)
    claim_type: str
    raw_payload_ref: Optional[str] = None  # URI to S3

    # How it was collected
    source: Source
    collection_method: CollectionMethod
    collected_at: datetime
    ingested_at: datetime

    # Validation state (mutable via state machine only)
    validation_status: ValidationStatus = ValidationStatus.UNVALIDATED
    validated_at: Optional[datetime] = None

    # Quality (recalculable)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    quality: Optional[QualityMetadata] = None

    # Provenance (append-only)
    provenance: ProvenanceMetadata

    # Graph links (append-only)
    links: list[EntityRef] = Field(default_factory=list)

    # Lifecycle
    archived: bool = False

    model_config = {"frozen": False}  # fields mutate via engine only

    def is_admissible_for_knowledge(self) -> bool:
        """
        Evidence is admissible as Knowledge input only when validated
        with a non-null confidence score.
        """
        return (
            self.validation_status == ValidationStatus.VALIDATED
            and self.confidence is not None
        )

    def can_supersede(self) -> bool:
        """
        Only validated or rejected Evidence can be superseded.
        Unvalidated Evidence is corrected by rejection, not supersession.
        """
        return self.validation_status in (
            ValidationStatus.VALIDATED,
            ValidationStatus.REJECTED,
        )


class EvidenceIngestionRequest(BaseModel):
    """
    Input payload for the Evidence Engine ingestion API.
    Mirrors the ingestion contract in specifications/engines/evidence-engine.md.
    """

    source: Source
    collection_method: CollectionMethod
    subject_ref: EntityRef
    claim_type: str
    raw_payload: dict | str | None = None
    raw_payload_format: str = Field(
        default="json",
        description="json | text | base64_pdf | base64_image"
    )
    collected_at: datetime
    idempotency_key: str = Field(
        min_length=1,
        description="Required. Same key submitted twice produces one Evidence object."
    )


class EvidenceIngestionResponse(BaseModel):
    """Response from the Evidence Engine on successful ingestion."""
    evidence_id: UUID
    status: str = Field(description="ingested | duplicate | rejected")
    validation_status: ValidationStatus
    confidence: Optional[float] = None
    rejection_reason: Optional[str] = None
