"""
services/evidence-engine/app/api/health.py

Health check endpoint. Every service exposes this.
Used by ECS Fargate for container health checks and by monitoring.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from shared.infrastructure.database.postgres import check_database_health


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    checks: dict


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
async def health(request: Request) -> HealthResponse:
    db_health = await check_database_health()

    try:
        await request.app.state.redis.ping()
        redis_health = {"status": "healthy", "store": "redis"}
    except Exception as e:
        redis_health = {"status": "unhealthy", "store": "redis", "error": str(e)}

    overall = (
        "healthy"
        if db_health["status"] == "healthy" and redis_health["status"] == "healthy"
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        service="evidence-engine",
        checks={
            "database": db_health,
            "stream_store": redis_health,
        },
    )
