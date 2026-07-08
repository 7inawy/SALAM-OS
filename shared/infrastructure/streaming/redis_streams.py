"""
shared/infrastructure/streaming/redis_streams.py

Redis Streams client for the SALAM event stream.
Every service uses this to publish and consume events.

Migration note (ADR-002):
When volume reaches ~50k events/day, this module is replaced with a
Kafka client behind the same interface. Application code does not change.
"""

import json
import logging
from typing import Any, Callable, Coroutine
from uuid import UUID

import redis.asyncio as aioredis

from ..config import settings
from shared.kernel.events.events import SALAMEvent


logger = logging.getLogger(__name__)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class StreamPublisher:
    """
    Publishes SALAM events to Redis Streams.
    One instance per service, shared across requests.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def publish(self, event: SALAMEvent) -> str:
        """
        Publish an event to its domain stream.
        Returns the Redis stream entry ID.
        """
        payload = {
            "event_id": str(event.event_id),
            "event_name": event.event_name.value,
            "occurred_at": event.occurred_at.isoformat(),
            "producer": event.producer,
            "payload": json.dumps(event.payload, cls=UUIDEncoder),
        }
        entry_id = await self._redis.xadd(event.stream_key, payload)
        logger.debug(
            "published event",
            extra={
                "event_name": event.event_name.value,
                "stream": event.stream_key,
                "entry_id": entry_id,
            },
        )
        return entry_id

    async def publish_batch(self, events: list[SALAMEvent]) -> list[str]:
        """Publish multiple events in a pipeline — more efficient than one by one."""
        async with self._redis.pipeline(transaction=False) as pipe:
            for event in events:
                payload = {
                    "event_id": str(event.event_id),
                    "event_name": event.event_name.value,
                    "occurred_at": event.occurred_at.isoformat(),
                    "producer": event.producer,
                    "payload": json.dumps(event.payload, cls=UUIDEncoder),
                }
                pipe.xadd(event.stream_key, payload)
            results = await pipe.execute()
        return results


class StreamConsumer:
    """
    Consumes events from Redis Streams for a specific service.
    Uses consumer groups for reliable at-least-once delivery.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        service_name: str,
        group_name: str,
    ) -> None:
        self._redis = redis_client
        self._service_name = service_name
        self._group_name = group_name

    async def ensure_group(self, stream_key: str) -> None:
        """Create consumer group if it doesn't exist."""
        try:
            await self._redis.xgroup_create(
                stream_key,
                self._group_name,
                id="0",
                mkstream=True,
            )
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def consume(
        self,
        stream_key: str,
        handler: Callable[[dict], Coroutine],
        batch_size: int = 10,
        block_ms: int = 1000,
    ) -> None:
        """
        Consume events from a stream and call handler for each.
        Acknowledges after successful handler execution.
        On handler failure: logs and does not acknowledge — event
        will be redelivered on next poll (at-least-once guarantee).
        """
        await self.ensure_group(stream_key)

        while True:
            messages = await self._redis.xreadgroup(
                groupname=self._group_name,
                consumername=self._service_name,
                streams={stream_key: ">"},
                count=batch_size,
                block=block_ms,
            )

            if not messages:
                continue

            for _stream, entries in messages:
                for entry_id, data in entries:
                    try:
                        payload = json.loads(data[b"payload"])
                        event_data = {
                            "event_id": data[b"event_id"].decode(),
                            "event_name": data[b"event_name"].decode(),
                            "occurred_at": data[b"occurred_at"].decode(),
                            "producer": data[b"producer"].decode(),
                            "payload": payload,
                        }
                        await handler(event_data)
                        await self._redis.xack(stream_key, self._group_name, entry_id)
                    except Exception as e:
                        logger.error(
                            "event handler failed — will redeliver",
                            extra={
                                "entry_id": entry_id,
                                "event_name": data.get(b"event_name", b"unknown").decode(),
                                "error": str(e),
                            },
                        )


async def get_redis() -> aioredis.Redis:
    """Create and return a Redis client. Call once at service startup."""
    return await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False,
    )
