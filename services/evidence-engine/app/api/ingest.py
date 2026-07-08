"""
services/evidence-engine/app/api/ingest.py

Evidence ingestion API endpoints.
Implements the ingestion contract from specifications/engines/evidence-engine.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.database.postgres import get_session
from shared.kernel.models import EvidenceIngestionRequest, EvidenceIngestionResponse
from ..engines.pipeline import EvidencePipeline


logger = logging.getLogger(__name__)
router = APIRouter(tags=["evidence"])

# Authorised source identifiers — in production, fetched from Secrets Manager
# and validated against API keys / mTLS certificates
AUTHORISED_SOURCES = {
    "bosta-webhook": "bosta",
    "aramex-eg-webhook": "aramex_eg",
    "paymob-webhook": "paymob",
    "fawry-webhook": "fawry",
    "merchant-portal": "merchant_portal",
    "internal-escrow": "escrow_service",
    "internal-system": "system",
}


def _authenticate_source(x_source_key: str | None) -> str:
    """
    Stage 1 of the pipeline: authenticate the source.
    Returns the canonical source identifier if valid.
    Raises 401 if unknown.
    """
    if not x_source_key or x_source_key not in AUTHORISED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown or missing source key",
        )
    return AUTHORISED_SOURCES[x_source_key]


@router.post(
    "/evidence",
    response_model=EvidenceIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a new Evidence observation",
    description=(
        "Entry point for all Evidence entering the SALAM system. "
        "Runs the 7-stage pipeline: authenticate → deduplicate → normalize → "
        "validate → score → persist → publish. "
        "Idempotent: same idempotency_key returns the existing evidence_id."
    ),
)
async def ingest_evidence(
    request: Request,
    payload: EvidenceIngestionRequest,
    x_source_key: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> EvidenceIngestionResponse:
    """Ingest a single Evidence observation through the full pipeline."""

    authenticated_source = _authenticate_source(x_source_key)

    pipeline = EvidencePipeline(
        session=session,
        redis=request.app.state.redis,
        publisher=request.app.state.publisher,
    )

    result = await pipeline.ingest(payload, authenticated_source)

    logger.info(
        "evidence ingestion complete",
        extra={
            "evidence_id": str(result.evidence_id),
            "status": result.status,
            "validation_status": result.validation_status,
            "source": authenticated_source,
        },
    )

    return result


@router.post(
    "/evidence/batch",
    response_model=list[EvidenceIngestionResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a batch of Evidence observations",
    description=(
        "Batch ingestion for logistics partner data pipelines. "
        "Each item in the batch is processed independently. "
        "Partial success is possible — check status per item."
    ),
)
async def ingest_evidence_batch(
    request: Request,
    payloads: list[EvidenceIngestionRequest],
    x_source_key: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[EvidenceIngestionResponse]:
    """Ingest a batch of Evidence observations. Max 100 per request."""

    if len(payloads) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Batch size exceeds maximum of 100",
        )

    authenticated_source = _authenticate_source(x_source_key)

    pipeline = EvidencePipeline(
        session=session,
        redis=request.app.state.redis,
        publisher=request.app.state.publisher,
    )

    results = []
    for payload in payloads:
        result = await pipeline.ingest(payload, authenticated_source)
        results.append(result)

    return results
