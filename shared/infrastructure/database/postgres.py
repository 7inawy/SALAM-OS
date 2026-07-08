"""
shared/infrastructure/database/postgres.py

PostgreSQL connection and session management.
Uses asyncpg via SQLAlchemy async — every service imports from here.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ..config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # detect stale connections
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    All tables inherit from this.
    """
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> dict[str, Any]:
    """Health check — called by /health endpoint in every service."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "healthy", "database": "postgresql"}
    except Exception as e:
        return {"status": "unhealthy", "database": "postgresql", "error": str(e)}
