from services.logging.logger import log as logger
from typing import List, Optional
from uuid import UUID

from redis.asyncio.client import Redis
from redis.exceptions import RedisError

from services.redis.exceptions import RedisResponseError
from domain.api.jobs.queues.constants import QUEUE_PREFIX
from domain.api.jobs.queues.schemas import JobQueueSchema
from domain.api.jobs.core import JobRepository



def _is_uid(identifier: str) -> bool:

    try:
        UUID(identifier)
        return True
    except ValueError:
        return False


class QueueRepository:
    """
    CRUD operations for job queues in Redis with decode_responses=True.
    """
    def __init__(self, redis: Redis):
        self.redis = redis
        self.pattern = f"{QUEUE_PREFIX}:*"
        self.jobs = JobRepository(redis)

    async def get_all(self) -> List[JobQueueSchema]:
        queues = []
        async for key in self.redis.scan_iter(match=f"{QUEUE_PREFIX}:*", count=100):
            data = await self.redis.hgetall(key)
            if data:
                queues.append(JobQueueSchema(**data))
        return queues

    async def get(self, identifier: str, scan_count: int = 100) -> Optional[JobQueueSchema]:
        if not identifier:
            return None

        if _is_uid(identifier):
            uid = identifier.lower()
            pattern = f"{QUEUE_PREFIX}:*:{uid}"
            async for key in self.redis.scan_iter(match=pattern, count=scan_count):
                data = await self.redis.hgetall(key)
                if data:
                    return JobQueueSchema(**data)
            return None

        name = identifier
        uid = JobQueueSchema._generate_uid(name)
        key = f"{QUEUE_PREFIX}:{name}:{uid}"
        data = await self.redis.hgetall(key)
        if data:
            return JobQueueSchema(**data)
        return None

    async def create(self, queue: JobQueueSchema) -> JobQueueSchema:
        jobs = queue.get("queue", "").split(",")
        for j in jobs:
            if not self.jobs.get(j):
                raise Exception(f"Job {j} does not exist")
        try:
            await self.redis.hset(queue.key, mapping=queue.serialize())
        except RedisError as e:
            logger.error("Failed to create queue %s: %s", queue.name, e)
            raise RedisResponseError(message=str(e))
        return await self.get(queue.uid)

    async def update(self, identifier: str, update_data: dict) -> Optional[JobQueueSchema]:
        queue = await self.get(identifier)
        if not queue:
            raise Exception(f"Queue {identifier} not found")

        jobs = queue.get("queue", "").split(",")
        for j in jobs:
            if not self.jobs.get(j):
                raise Exception(f"Job {j} does not exist")

        for k, v in update_data.items():
            if hasattr(queue, k):
                setattr(queue, k, v)

        try:
            await self.redis.hset(queue.key, mapping=queue.serialize())
        except RedisError as e:
            logger.error("Failed to update job %s: %s", queue.key, e)
            raise RedisResponseError(message=str(e))
        return await self.get(identifier)

    async def delete(self, identifier: str, scan_count: int = 100) -> None:
        queue = await self.get(identifier, scan_count=scan_count)
        if not queue:
            logger.warning("Job to delete not found: %s", identifier)
            return
        try:
            await self.redis.delete(queue.key)
        except RedisError as e:
            logger.error("Failed to delete job %s: %s", identifier, e)
            raise RedisResponseError(message=str(e))
