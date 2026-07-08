"""
services/evidence-engine/app/engines/pipeline.py

The 7-stage Evidence ingestion pipeline.
Implements specifications/engines/evidence-engine.md exactly.

Stages:
  1. Authenticate source
  2. Deduplicate (idempotency key)
  3. Normalize claim
  4. Validate claim
  5. Score quality (7 dimensions)
  6. Persist
  7. Publish events
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.kernel.models import (
    CollectionMethod,
    Evidence,
    EvidenceIngestionRequest,
    EvidenceIngestionResponse,
    ProvenanceChainEntry,
    ProvenanceMetadata,
    QualityMetadata,
    Source,
    ValidationStatus,
)
from shared.kernel.events.events import (
    EventName,
    SALAMEvent,
    EvidenceValidatedPayload,
    EvidenceRejectedPayload,
)
from shared.infrastructure.config import settings
from shared.infrastructure.streaming.redis_streams import StreamPublisher
from ..models.db import EvidenceRecord


logger = logging.getLogger(__name__)

# Verifiability scores by collection method (from spec)
VERIFIABILITY_BY_METHOD = {
    CollectionMethod.DIRECT_OBSERVATION: 0.95,
    CollectionMethod.THIRD_PARTY_ATTESTATION: 0.80,
    CollectionMethod.USER_SUBMISSION: 0.50,
    CollectionMethod.SYSTEM_INFERENCE: 0.60,
    CollectionMethod.DOCUMENT_EXTRACTION: 0.70,
}

# Deduplication TTL matches spec: 30 days
DEDUP_TTL_SECONDS = settings.evidence_deduplication_ttl_days * 86_400


class EvidencePipeline:
    """
    Orchestrates the 7-stage ingestion pipeline.
    One instance per service, stateless between requests.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis: aioredis.Redis,
        publisher: StreamPublisher,
    ) -> None:
        self._session = session
        self._redis = redis
        self._publisher = publisher

    async def ingest(
        self,
        request: EvidenceIngestionRequest,
        authenticated_source: str,
    ) -> EvidenceIngestionResponse:
        """
        Run all 7 stages. Returns the ingestion response.
        Stage failures return a response with appropriate status —
        they do not raise HTTP exceptions (caller handles that).
        """

        # Stage 1: Source already authenticated by the API layer
        # (authenticated_source carries the verified source identifier)

        # Stage 2: Deduplicate
        dedup_result = await self._deduplicate(request.idempotency_key)
        if dedup_result:
            logger.info("duplicate evidence submission", extra={"idempotency_key": request.idempotency_key})
            return EvidenceIngestionResponse(
                evidence_id=dedup_result,
                status="duplicate",
                validation_status=ValidationStatus.VALIDATED,
            )

        # Stage 3: Normalize
        normalized_claim = self._normalize(request)
        if normalized_claim is None:
            return EvidenceIngestionResponse(
                evidence_id=uuid4(),
                status="rejected",
                validation_status=ValidationStatus.REJECTED,
                rejection_reason="normalization_failed",
            )

        # Stage 4: Validate
        validation_status, rejection_reason = self._validate(request, normalized_claim)

        # Stage 5: Score quality
        quality = self._score_quality(request, normalized_claim)
        confidence = self._compute_confidence(quality)

        # Stage 6: Build and persist Evidence object
        evidence_id = uuid4()
        evidence = Evidence(
            evidence_id=evidence_id,
            version=1,
            subject_ref=request.subject_ref,
            claim=normalized_claim,
            claim_type=request.claim_type,
            source=Source(
                source_type=authenticated_source,
                identifier=authenticated_source,
            ),
            collection_method=request.collection_method,
            collected_at=request.collected_at,
            ingested_at=datetime.now(tz=timezone.utc),
            validation_status=validation_status,
            validated_at=datetime.now(tz=timezone.utc) if validation_status == ValidationStatus.VALIDATED else None,
            confidence=confidence,
            quality=quality,
            provenance=ProvenanceMetadata(
                origin=authenticated_source,
                collection_method=request.collection_method,
                chain=[
                    ProvenanceChainEntry(
                        step="ingest",
                        actor="evidence-engine",
                        timestamp=datetime.now(tz=timezone.utc),
                    ),
                    ProvenanceChainEntry(
                        step="normalize",
                        actor="evidence-engine",
                        timestamp=datetime.now(tz=timezone.utc),
                    ),
                    ProvenanceChainEntry(
                        step="validate",
                        actor="evidence-engine",
                        timestamp=datetime.now(tz=timezone.utc),
                    ),
                    ProvenanceChainEntry(
                        step="score",
                        actor="evidence-engine",
                        timestamp=datetime.now(tz=timezone.utc),
                    ),
                ],
                ownership=authenticated_source,
                verification_confidence=quality.provenance_score,
            ),
        )

        await self._persist(evidence, request.raw_payload)

        # Register idempotency key
        await self._register_dedup_key(request.idempotency_key, evidence_id)

        # Stage 7: Publish events
        await self._publish(evidence, rejection_reason)

        return EvidenceIngestionResponse(
            evidence_id=evidence_id,
            status="ingested",
            validation_status=validation_status,
            confidence=confidence,
            rejection_reason=rejection_reason,
        )

    # ------------------------------------------------------------------
    # Stage 2: Deduplication
    # ------------------------------------------------------------------

    async def _deduplicate(self, idempotency_key: str) -> UUID | None:
        """
        Returns existing evidence_id if key seen within TTL, else None.
        Key is hashed before storage — idempotency keys may contain PII.
        """
        hashed = hashlib.sha256(idempotency_key.encode()).hexdigest()
        redis_key = f"salam:evidence:dedup:{hashed}"
        existing = await self._redis.get(redis_key)
        if existing:
            return UUID(existing.decode())
        return None

    async def _register_dedup_key(
        self, idempotency_key: str, evidence_id: UUID
    ) -> None:
        hashed = hashlib.sha256(idempotency_key.encode()).hexdigest()
        redis_key = f"salam:evidence:dedup:{hashed}"
        await self._redis.setex(redis_key, DEDUP_TTL_SECONDS, str(evidence_id))

    # ------------------------------------------------------------------
    # Stage 3: Normalize
    # ------------------------------------------------------------------

    def _normalize(self, request: EvidenceIngestionRequest) -> str | None:
        """
        Transforms raw_payload into a canonical claim string.
        Returns None if normalization fails.

        v1: basic normalization — claim_type-specific rules are
        expanded in the Claim Normalization Specification (child spec).
        """
        try:
            if isinstance(request.raw_payload, dict):
                # For structured payloads, produce a canonical JSON string
                import json
                return json.dumps(request.raw_payload, sort_keys=True, ensure_ascii=False)
            elif isinstance(request.raw_payload, str):
                normalized = request.raw_payload.strip()
                if not normalized:
                    return None
                return normalized
            else:
                # System inference or minimal payloads — use claim_type as claim
                return f"{request.claim_type}:{request.subject_ref.entity_id}"
        except Exception as e:
            logger.error("normalization failed", extra={"error": str(e)})
            return None

    # ------------------------------------------------------------------
    # Stage 4: Validate
    # ------------------------------------------------------------------

    def _validate(
        self,
        request: EvidenceIngestionRequest,
        normalized_claim: str,
    ) -> tuple[ValidationStatus, str | None]:
        """
        Returns (validation_status, rejection_reason).
        Syntactic and semantic validation only in v1.
        Business rule validation per claim_type is a child spec.
        """
        # Syntactic: claim must be non-empty
        if not normalized_claim or len(normalized_claim.strip()) == 0:
            return ValidationStatus.REJECTED, "empty_claim"

        # Semantic: collected_at must not be in the future
        now = datetime.now(tz=timezone.utc)
        collected_at = request.collected_at
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=timezone.utc)
        if collected_at > now + timedelta(minutes=5):
            return ValidationStatus.REJECTED, "future_collection_timestamp"

        # Semantic: collected_at must not be more than 2 years ago
        if collected_at < now - timedelta(days=730):
            return ValidationStatus.PENDING, None  # flag for review, not reject

        return ValidationStatus.VALIDATED, None

    # ------------------------------------------------------------------
    # Stage 5: Score quality
    # ------------------------------------------------------------------

    def _score_quality(
        self,
        request: EvidenceIngestionRequest,
        normalized_claim: str,
    ) -> QualityMetadata:
        """
        Score all seven quality dimensions.
        Weights and exact formulas are ADR-dependent (open question).
        These are v1 heuristic implementations.
        """
        now = datetime.now(tz=timezone.utc)
        collected_at = request.collected_at
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=timezone.utc)

        # Authenticity: based on collection method
        authenticity = VERIFIABILITY_BY_METHOD.get(request.collection_method, 0.5)

        # Integrity: 1.0 if we received it directly; lower for document extraction
        integrity = (
            0.75
            if request.collection_method == CollectionMethod.DOCUMENT_EXTRACTION
            else 1.0
        )

        # Freshness: decays linearly over 90 days from collection
        age_days = (now - collected_at).days
        freshness = max(0.0, 1.0 - (age_days / 90))

        # Completeness: 1.0 if payload present, 0.5 if minimal
        completeness = 1.0 if request.raw_payload else 0.5

        # Verifiability: same as authenticity (v1 — more nuanced in child spec)
        verifiability = VERIFIABILITY_BY_METHOD.get(request.collection_method, 0.5)

        # Provenance: 1.0 if we have a clear source, lower otherwise
        provenance_score = 0.9 if request.source else 0.4

        # Consistency: 0.5 on first submission (no corroboration yet)
        # Updated by Knowledge Engine as corroborating Evidence arrives
        consistency = 0.5

        return QualityMetadata(
            authenticity=round(authenticity, 4),
            integrity=round(integrity, 4),
            freshness=round(freshness, 4),
            completeness=round(completeness, 4),
            verifiability=round(verifiability, 4),
            provenance_score=round(provenance_score, 4),
            consistency=round(consistency, 4),
        )

    def _compute_confidence(self, quality: QualityMetadata) -> float:
        """
        Weighted average of seven quality dimensions.
        Weights are v1 defaults — ADR required for final values.
        """
        weights = {
            "authenticity": 0.20,
            "integrity": 0.15,
            "freshness": 0.15,
            "completeness": 0.10,
            "verifiability": 0.20,
            "provenance_score": 0.10,
            "consistency": 0.10,
        }
        score = (
            quality.authenticity * weights["authenticity"]
            + quality.integrity * weights["integrity"]
            + quality.freshness * weights["freshness"]
            + quality.completeness * weights["completeness"]
            + quality.verifiability * weights["verifiability"]
            + quality.provenance_score * weights["provenance_score"]
            + quality.consistency * weights["consistency"]
        )
        return round(score, 4)

    # ------------------------------------------------------------------
    # Stage 6: Persist
    # ------------------------------------------------------------------

    async def _persist(
        self, evidence: Evidence, raw_payload: dict | str | None
    ) -> None:
        """Write Evidence to PostgreSQL. Immutable after this point."""
        record = EvidenceRecord.from_domain(evidence, raw_payload)
        self._session.add(record)
        await self._session.flush()
        logger.info(
            "evidence persisted",
            extra={
                "evidence_id": str(evidence.evidence_id),
                "claim_type": evidence.claim_type,
                "validation_status": evidence.validation_status,
            },
        )

    # ------------------------------------------------------------------
    # Stage 7: Publish events
    # ------------------------------------------------------------------

    async def _publish(
        self, evidence: Evidence, rejection_reason: str | None
    ) -> None:
        """Publish evidence.* events to the stream."""
        events_to_publish = []

        # Always publish evidence.ingested
        events_to_publish.append(SALAMEvent(
            event_name=EventName.EVIDENCE_INGESTED,
            producer="evidence-engine",
            payload={
                "evidence_id": str(evidence.evidence_id),
                "subject_ref_type": evidence.subject_ref.entity_type.value,
                "subject_ref_id": str(evidence.subject_ref.entity_id),
                "claim_type": evidence.claim_type,
                "collection_method": evidence.collection_method.value,
                "ingested_at": evidence.ingested_at.isoformat(),
            },
        ))

        # Publish status-specific event
        if evidence.validation_status == ValidationStatus.VALIDATED:
            events_to_publish.append(SALAMEvent(
                event_name=EventName.EVIDENCE_VALIDATED,
                producer="evidence-engine",
                payload=EvidenceValidatedPayload(
                    evidence_id=evidence.evidence_id,
                    subject_ref_type=evidence.subject_ref.entity_type.value,
                    subject_ref_id=evidence.subject_ref.entity_id,
                    claim_type=evidence.claim_type,
                    confidence=evidence.confidence,
                    collection_method=evidence.collection_method.value,
                ).model_dump(),
            ))
        elif evidence.validation_status == ValidationStatus.REJECTED:
            events_to_publish.append(SALAMEvent(
                event_name=EventName.EVIDENCE_REJECTED,
                producer="evidence-engine",
                payload=EvidenceRejectedPayload(
                    evidence_id=evidence.evidence_id,
                    subject_ref_type=evidence.subject_ref.entity_type.value,
                    subject_ref_id=evidence.subject_ref.entity_id,
                    claim_type=evidence.claim_type,
                    rejection_reason=rejection_reason or "unknown",
                    source_identifier=evidence.source.identifier,
                ).model_dump(),
            ))
        elif evidence.validation_status == ValidationStatus.PENDING:
            events_to_publish.append(SALAMEvent(
                event_name=EventName.EVIDENCE_PENDING,
                producer="evidence-engine",
                payload={
                    "evidence_id": str(evidence.evidence_id),
                    "subject_ref_id": str(evidence.subject_ref.entity_id),
                    "claim_type": evidence.claim_type,
                },
            ))

        await self._publisher.publish_batch(events_to_publish)
