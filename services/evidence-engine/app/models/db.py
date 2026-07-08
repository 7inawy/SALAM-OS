"""
services/evidence-engine/app/models/db.py

SQLAlchemy ORM model for Evidence storage.
Enforces immutability at the database level where possible.
"""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.database.postgres import Base
from shared.kernel.models import Evidence


class EvidenceRecord(Base):
    """
    Persisted representation of a Kernel Evidence object.

    Immutability enforced:
    - No UPDATE is ever issued on this table (application layer).
    - archived is the only field that transitions (False → True).
    - provenance_chain is append-only (new entries appended via supersession).
    - PostgreSQL ROW SECURITY POLICY enforces no-delete at DB level (to be
      added in production migration).
    """

    __tablename__ = "evidence"

    # Identity
    evidence_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Subject
    subject_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    # Claim
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_payload_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Collection
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(500), nullable=False)
    collection_method: Mapped[str] = mapped_column(String(50), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Validation
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Quality
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Provenance (JSONB — append-only at application layer)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Graph links (JSONB array — append-only)
    links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Lifecycle
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Fast lookup by subject — most common query pattern
        Index("ix_evidence_subject", "subject_entity_type", "subject_entity_id"),
        # Fast lookup by claim_type for Knowledge Engine aggregation
        Index("ix_evidence_claim_type", "claim_type"),
        # Fast lookup by validation status for pending review queue
        Index("ix_evidence_validation_status", "validation_status"),
        # Supersession chain traversal
        Index("ix_evidence_supersedes", "supersedes"),
    )

    @classmethod
    def from_domain(
        cls,
        evidence: Evidence,
        raw_payload: dict | str | None = None,
    ) -> "EvidenceRecord":
        """Convert domain Evidence model to ORM record."""
        return cls(
            evidence_id=evidence.evidence_id,
            version=evidence.version,
            supersedes=evidence.supersedes,
            subject_entity_type=evidence.subject_ref.entity_type.value,
            subject_entity_id=evidence.subject_ref.entity_id,
            claim=evidence.claim,
            claim_type=evidence.claim_type,
            raw_payload_ref=evidence.raw_payload_ref,
            source_type=evidence.source.source_type,
            source_identifier=evidence.source.identifier,
            collection_method=evidence.collection_method.value,
            collected_at=evidence.collected_at,
            ingested_at=evidence.ingested_at,
            validation_status=evidence.validation_status.value,
            validated_at=evidence.validated_at,
            confidence=evidence.confidence,
            quality=evidence.quality.model_dump() if evidence.quality else None,
            provenance=evidence.provenance.model_dump(),
            links=[ref.model_dump() for ref in evidence.links],
            archived=evidence.archived,
        )

    def to_domain(self) -> Evidence:
        """Convert ORM record back to domain Evidence model."""
        from shared.kernel.models import (
            CollectionMethod, EntityRef, EntityType, ProvenanceMetadata,
            QualityMetadata, Source, ValidationStatus,
        )
        return Evidence(
            evidence_id=self.evidence_id,
            version=self.version,
            supersedes=self.supersedes,
            subject_ref=EntityRef(
                entity_type=EntityType(self.subject_entity_type),
                entity_id=self.subject_entity_id,
            ),
            claim=self.claim,
            claim_type=self.claim_type,
            raw_payload_ref=self.raw_payload_ref,
            source=Source(
                source_type=self.source_type,
                identifier=self.source_identifier,
            ),
            collection_method=CollectionMethod(self.collection_method),
            collected_at=self.collected_at,
            ingested_at=self.ingested_at,
            validation_status=ValidationStatus(self.validation_status),
            validated_at=self.validated_at,
            confidence=self.confidence,
            quality=QualityMetadata(**self.quality) if self.quality else None,
            provenance=ProvenanceMetadata(**self.provenance),
            links=[EntityRef(**ref) for ref in (self.links or [])],
            archived=self.archived,
        )
