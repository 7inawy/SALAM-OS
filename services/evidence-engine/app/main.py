"""
services/evidence-engine/app/main.py

Evidence Engine service entry point.
The gateway between raw reality and SALAM's intelligence pipeline.
Every observation entering the system passes through here.
"""

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.infrastructure.config import settings
from shared.infrastructure.streaming.redis_streams import StreamPublisher, get_redis
from .api.ingest import router as ingest_router
from .api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown — initialise shared resources once."""
    redis_client: aioredis.Redis = await get_redis()
    app.state.redis = redis_client
    app.state.publisher = StreamPublisher(redis_client)
    yield
    await redis_client.aclose()


app = FastAPI(
    title="SALAM Evidence Engine",
    description=(
        "Entry point of the SALAM intelligence pipeline. "
        "Ingests, normalises, validates, and scores Evidence objects. "
        "Publishes evidence.* events for downstream engines."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened per environment in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ingest_router, prefix="/api/v1")
