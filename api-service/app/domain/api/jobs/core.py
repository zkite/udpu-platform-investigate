from typing import Optional, List, Union
from uuid import UUID

from services.logging.logger import log as logger

from redis.asyncio.client import Redis
from redis.exceptions import RedisError

from services.redis.exceptions import RedisResponseError
from domain.api.jobs.constants import JOB_PREFIX
from domain.api.jobs.schemas import JobSchema, JobSchemaUpdate
from domain.api.jobs.schemas import JobFrequency


def _is_uid(identifier: str) -> bool:

    try:
        UUID(identifier)
        return True
    except ValueError:
        return False


def _is_job_storage_key(key: str) -> bool:
    return key.startswith(f"{JOB_PREFIX}:") and len(key.split(":")) == 3


class JobRepository:
    """
    Repository for managing Job entities in Redis storage.
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def create(self, job: JobSchema) -> JobSchema:
        try:
            key = job.key
            if await self.redis.exists(key):
                raise RedisResponseError(message=f"Job {job.name} already exists")
            await self.redis.hset(key, mapping=job.serialize())
        except RedisError as e:
            logger.error("Failed to create job %s: %s", job.name, e)
            raise RedisResponseError(message=str(e))
        return await self.get(job.uid)

    async def get(self, identifier: str, scan_count: int = 100) -> Optional[JobSchema]:
        if not identifier:
            return None

        if _is_uid(identifier):
            uid = identifier.lower()
            pattern = f"{JOB_PREFIX}:*:{uid}"
            async for key in self.redis.scan_iter(match=pattern, count=scan_count):
                data = await self.redis.hgetall(key)
                if data:
                    return JobSchema(**data)
            return None

        name = identifier
        uid = JobSchema._generate_uid(name)
        key = f"{JOB_PREFIX}:{name}:{uid}"
        data = await self.redis.hgetall(key)
        if data:
            return JobSchema(**data)
        return None

    async def update(self, identifier: str, update_data: dict) -> Optional[JobSchema]:
        job = await self.get(identifier)
        if not job:
            return None

        old_key = job.key
        patch = JobSchemaUpdate(**update_data)
        for k, v in patch.model_dump(exclude_none=True).items():
            setattr(job, k, v)

        new_key = job.key
        pipe = self.redis.pipeline()
        try:
            if new_key != old_key:
                await pipe.hset(new_key, mapping=job.serialize())
                await pipe.delete(old_key)
            else:
                await pipe.hset(old_key, mapping=job.serialize())
            await pipe.execute()
        except RedisError as e:
            logger.error("Failed to update job %s: %s", job.name, e)
        return await self.get(job.uid)

    async def delete(self, identifier: str, scan_count: int = 100):
        job = await self.get(identifier, scan_count=scan_count)
        if not job:
            logger.warning("Job to delete not found: %s", identifier)
            return

        try:
            await self.redis.delete(job.key)
            return True
        except RedisError as e:
            logger.error("Failed to delete job %s: %s", identifier, e)
            raise RedisResponseError(message=str(e))

    async def get_all(self) -> List[JobSchema]:
        jobs = []
        async for key in self.redis.scan_iter(match=f"{JOB_PREFIX}:*", count=100):
            if not _is_job_storage_key(key):
                continue
            data = await self.redis.hgetall(key)
            if data:
                jobs.append(JobSchema(**data))
        return jobs

    async def filter_by_name(self, entity: str):
        jobs = await self.get_all()
        if not jobs:
            return False
        return entity in {j.name for j in jobs}

    async def get_by_role(self, role_name: str, frequency: JobFrequency = JobFrequency.FIRST_BOOT):
        return [
            j for j in await self.get_all()
            if getattr(j, "role", None) == role_name and getattr(j, "frequency", None) == frequency
        ]

    async def get_by_frequency(self, frequency: Union[JobFrequency, str]) -> List[JobSchema]:
        freq = frequency if isinstance(frequency, JobFrequency) else JobFrequency.parse(frequency)

        result: List[JobSchema] = []
        async for key in self.redis.scan_iter(match=f"{JOB_PREFIX}:*", count=100):
            if not _is_job_storage_key(key):
                continue
            data = await self.redis.hgetall(key)
            if not data:
                continue
            job = JobSchema(**data)
            if getattr(job, "frequency", None) == freq:
                result.append(job)
        return result
