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


def _split_queue_jobs(queue_value):
    return [item.strip() for item in str(queue_value or "").split(",") if item.strip()]


class QueueRepository:
    """
    CRUD operations for job queues in Redis with decode_responses=True.
    """
    def __init__(self, redis: Redis):
        self.redis = redis
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

    async def validate_jobs(self, queue_jobs):
        invalid_jobs = []
        for job_identifier in _split_queue_jobs(queue_jobs):
            if not await self.jobs.get(job_identifier):
                invalid_jobs.append(job_identifier)
        return invalid_jobs

    async def is_role_unique(self, role_name, exclude_identifier=None):
        role_name = str(role_name or "").strip()
        if not role_name:
            return True

        exclude_uid = None
        if exclude_identifier:
            existing = await self.get(exclude_identifier)
            if existing:
                exclude_uid = existing.uid

        queues = await self.get_all()
        for queue in queues:
            if queue.role == role_name and queue.uid != exclude_uid:
                return False
        return True

    async def get_by_role(self, role_name):
        role_name = str(role_name or "").strip()
        return [queue for queue in await self.get_all() if queue.role == role_name]

    async def create(self, queue: JobQueueSchema) -> JobQueueSchema:
        invalid_jobs = await self.validate_jobs(queue.queue)
        if invalid_jobs:
            raise Exception(f"Job(s) '{', '.join(invalid_jobs)}' do not exist")
        try:
            await self.redis.hset(queue.key, mapping=queue.serialize())
        except RedisError as e:
            logger.error("Failed to create queue %s: %s", queue.name, e)
            raise RedisResponseError(message=str(e))
        return await self.get(queue.uid)

    async def update(self, identifier: str, update_data: dict) -> Optional[JobQueueSchema]:
        existing = await self.get(identifier)
        if not existing:
            return None
        queue = existing
        old_key = existing.key

        for k, v in update_data.items():
            if k == "uid":
                continue
            if hasattr(queue, k) and v is not None:
                setattr(queue, k, v)

        invalid_jobs = await self.validate_jobs(queue.queue)
        if invalid_jobs:
            raise Exception(f"Job(s) '{', '.join(invalid_jobs)}' do not exist")

        new_key = queue.key
        pipe = self.redis.pipeline()
        try:
            if new_key != old_key:
                await pipe.hset(new_key, mapping=queue.serialize())
                await pipe.delete(old_key)
            else:
                await pipe.hset(old_key, mapping=queue.serialize())
            await pipe.execute()
        except RedisError as e:
            logger.error("Failed to update job %s: %s", queue.key, e)
            raise RedisResponseError(message=str(e))
        return await self.get(queue.uid)

    async def delete(self, identifier: str, scan_count: int = 100) -> None:
        queue = await self.get(identifier, scan_count=scan_count)
        if not queue:
            logger.warning("Job to delete not found: %s", identifier)
            return False
        try:
            await self.redis.delete(queue.key)
            return True
        except RedisError as e:
            logger.error("Failed to delete job %s: %s", identifier, e)
            raise RedisResponseError(message=str(e))
