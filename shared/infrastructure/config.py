"""
shared/infrastructure/config.py

Centralised settings for all SALAM services.
Each service overrides only what it needs via environment variables.
Secrets come from AWS Secrets Manager — never hardcoded.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service identity
    service_name: str = "salam-service"
    environment: str = "development"  # development | staging | production

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://salam:salam@localhost:5432/salam"
    db_echo: bool = False  # set True in development only

    # Redis (Streams + Cache)
    redis_url: str = "redis://localhost:6379"
    redis_stream_prefix: str = "salam"
    redis_cache_ttl_seconds: int = 3600

    # AWS
    aws_region: str = "me-south-1"
    aws_s3_bucket_evidence: str = "salam-evidence-payloads"

    # Kernel constraints (from spec — not magic numbers)
    escrow_max_amount_egp: float = 50_000.0
    escrow_min_amount_egp: float = 50.0
    escrow_delivery_deadline_tracked_days: int = 5
    escrow_delivery_deadline_self_days: int = 3
    escrow_extension_max_days: int = 2
    escrow_payment_expiry_hours: int = 2
    escrow_buyer_confirmation_window_hours: int = 24
    trust_auto_release_threshold: float = 0.70

    # Evidence Engine
    evidence_deduplication_ttl_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
